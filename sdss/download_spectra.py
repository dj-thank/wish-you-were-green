#!/usr/bin/env python3
"""Bounded, resumable download of catalogue-identified public SDSS spectra."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import argparse
import hashlib
import io
import json
import threading
import time
import urllib.error
import urllib.request
import numpy as np
from astropy.io import fits
import requests

BASE = Path(__file__).resolve().parent
LOCK = threading.Lock()
THREAD = threading.local()
PER_FILE_LIMIT = 2_000_000

def urls(row):
    plate = row['plate']
    suffix = f'{plate:04d}/spec-{row["spectrum_id"]}.fits'
    base = 'https://data.sdss.org/sas/dr17/'
    if plate >= 3500:
        return [base+'eboss/spectro/redux/v5_13_2/spectra/lite/'+suffix]
    return [base+f'sdss/spectro/redux/{run}/spectra/lite/'+suffix for run in ['26','104','103']]

def summarize(data, row, url, path):
    result = row.copy()
    result.update(path=str(path),url=url,bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),
                  retrieved_utc=datetime.now(timezone.utc).isoformat(), status='ok')
    with fits.open(io.BytesIO(data), memmap=False) as hdus:
        coadd = hdus[1].data
        names = [n.lower() for n in coadd.names]
        wavelength = 10.0**np.asarray(coadd['loglam'], dtype=np.float64)
        flux = np.asarray(coadd['flux'], dtype=np.float64)
        ivar = np.asarray(coadd['ivar'], dtype=np.float64)
        result.update(npix=len(flux), wave_min_angstrom=float(wavelength.min()),
                      wave_max_angstrom=float(wavelength.max()),
                      usable_fraction=float(np.mean(np.isfinite(flux) & (ivar > 0))),
                      flux_unit='1e-17 erg s^-1 cm^-2 Angstrom^-1',
                      wavelength_medium='vacuum',data_release='SDSS DR17')
        # Preserve raw flux units, errors and masks for the parent analysis.
        array_path = BASE/'arrays'/f'spec-{row["spectrum_id"]}.npz'
        arrays = dict(wavelength_angstrom=wavelength, flux_flam=flux*1e-17,
                      ivar=ivar/1e-34, flux_sdss=flux, ivar_sdss=ivar)
        for key in ['and_mask','or_mask','wdisp','sky','model']:
            if key in names:
                arrays[key] = np.asarray(coadd[key])
        np.savez_compressed(array_path, **arrays)
        result['array_path'] = str(array_path)
        if len(hdus) > 2 and hdus[2].data is not None:
            meta = hdus[2].data
            for key in ['PLUG_RA','PLUG_DEC','RUN2D','CLASS','SUBCLASS','SN_MEDIAN_ALL','ZWARNING']:
                if key in meta.names:
                    val = meta[key][0]
                    if isinstance(val, bytes):val=val.decode().strip()
                    elif isinstance(val, np.generic):val=val.item()
                    result['sdss_'+key.lower()] = val
    return result

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--workers',type=int,default=4)
    parser.add_argument('--max-spectra',type=int,default=1600)
    parser.add_argument('--max-bytes',type=int,default=900_000_000)
    args=parser.parse_args()
    if not 1 <= args.workers <= 4:raise ValueError('workers must be 1..4')
    for folder in ['raw','arrays']:(BASE/folder).mkdir(exist_ok=True)
    rows=json.loads((BASE/'targets.json').read_text())[:args.max_spectra]
    prior={}
    log=BASE/'download_manifest.jsonl'
    if log.exists():
        for line in log.read_text().splitlines():
            record=json.loads(line)
            if record.get('status')=='ok':prior[record['spectrum_id']]=record
    state={'bytes':sum(p.stat().st_size for p in (BASE/'raw').glob('*.fits')),
           'reserved':0,'ok':0,'failed':0}
    def work(row):
        path=BASE/'raw'/f'spec-{row["spectrum_id"]}.fits'
        if path.exists():
            old=prior.get(row['spectrum_id'],{})
            try:
                result=summarize(path.read_bytes(),row,old.get('url',urls(row)[0]),path)
                if old.get('retrieved_utc'):result['retrieved_utc']=old['retrieved_utc']
                result['cached']=True
                return result
            except Exception as exc:return dict(row,status='invalid_cached_file',error=str(exc))
        with LOCK:
            if state['bytes']+state['reserved']+PER_FILE_LIMIT>args.max_bytes:
                return dict(row,status='byte_limit')
            state['reserved']+=PER_FILE_LIMIT
        errors=[]
        try:
            for url in urls(row):
                try:
                    if not hasattr(THREAD,'session'):
                        THREAD.session=requests.Session()
                        THREAD.session.headers['User-Agent']='OpenAI-research-public-data/1.0'
                    with THREAD.session.get(url,timeout=(15,35),stream=True) as response:
                        if response.status_code in [404,410]:
                            errors.append(dict(url=url,error=f'HTTP {response.status_code}'))
                            continue
                        response.raise_for_status()
                        chunks=[]
                        count=0
                        for chunk in response.iter_content(chunk_size=131072):
                            count+=len(chunk)
                            if count>PER_FILE_LIMIT:raise ValueError('Spectrum exceeds 2 MB per-file limit')
                            chunks.append(chunk)
                        data=b''.join(chunks)
                    if len(data)>PER_FILE_LIMIT:raise ValueError('Spectrum exceeds 2 MB per-file limit')
                    if not data.startswith(b'SIMPLE  ='):raise ValueError('Response is not a FITS file')
                    result=summarize(data,row,url,path)
                    path.write_bytes(data)
                    with LOCK:state['bytes']+=len(data)
                    return result
                except urllib.error.HTTPError as exc:
                    errors.append(dict(url=url,error=f'HTTP {exc.code}'))
                    if exc.code not in [404,410]:break
                except Exception as exc:
                    errors.append(dict(url=url,error=str(exc)))
                    break
            return dict(row,status='failed',errors=errors)
        finally:
            with LOCK:state['reserved']-=PER_FILE_LIMIT
    start=time.monotonic()
    with ThreadPoolExecutor(max_workers=args.workers) as executor,log.open('a') as manifest:
        futures=[executor.submit(work,row) for row in rows]
        for i,future in enumerate(as_completed(futures),1):
            record=future.result()
            manifest.write(json.dumps(record,allow_nan=False)+'\n')
            manifest.flush()
            state['ok' if record['status']=='ok' else 'failed']+=1
            if i%25==0 or i<=4 or i==len(rows):
                print(json.dumps(dict(done=i,total=len(rows),ok=state['ok'],failed=state['failed'],
                                      raw_bytes=state['bytes'],elapsed_s=round(time.monotonic()-start,1))),flush=True)
    complete={}
    for line in log.read_text().splitlines():
        record=json.loads(line)
        complete[record['spectrum_id']]=record
    records=list(complete.values())
    (BASE/'manifest.json').write_text(json.dumps(records,indent=2,allow_nan=False))
    import pandas as pd
    pd.DataFrame(records).to_csv(BASE/'manifest.csv',index=False)
    print(json.dumps(dict(finished=True,**state)),flush=True)

if __name__=='__main__':main()
