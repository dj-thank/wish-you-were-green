"""Reacquire the exact public files used in the full screen, with SHA256 checks.

This optional command downloads approximately 2 GB of public raw data. It is
not needed to read the notebook or reproduce its selected-candidate colours.
"""
from pathlib import Path
from project_io import load_json
import argparse,csv,hashlib,io,json,time
from concurrent.futures import ThreadPoolExecutor
from threading import local
import numpy as np
import requests
from astropy.io import fits
ROOT=Path(__file__).resolve().parent
STATE=local()

def relative(value):
    marker='wd-colour-research/'
    return ROOT/(str(value).split(marker,1)[1] if marker in str(value) else str(value))

def acquire(item):
    origin,r=item
    raw=relative(r['raw_path']);parsed=relative(r['parsed_path'])
    if raw.exists():data=raw.read_bytes()
    else:
        if not hasattr(STATE,'session'):STATE.session=requests.Session()
        response=STATE.session.get(r['source_url'],timeout=90);response.raise_for_status();data=response.content
    actual=hashlib.sha256(data).hexdigest()
    if actual!=r['sha256']:raise RuntimeError('Public file changed; SHA256 mismatch: '+r['source_url'])
    raw.parent.mkdir(parents=True,exist_ok=True);parsed.parent.mkdir(parents=True,exist_ok=True)
    if not raw.exists():raw.write_bytes(data)
    if not parsed.exists():
        if origin=='mwdd':
            lines=data.decode('utf-8','replace').splitlines();names=next(csv.reader([lines[1]]))
            arr=np.loadtxt(io.StringIO('\n'.join(lines[2:])),delimiter=',',ndmin=2)
            values={('wavelength_angstrom' if k.strip()=='wavelength' else 'flux_original' if k.strip()=='flux' else k.strip()):arr[:,j] for j,k in enumerate(names)}
        else:
            with fits.open(io.BytesIO(data)) as hd:
                a=hd[1].data;flux=np.asarray(a['flux'],float);iv=np.asarray(a['ivar'],float)
                values={'wavelength_angstrom':10**np.asarray(a['loglam'],float),'flux_flam':flux*1e-17,'ivar':iv/1e-34,'flux_sdss':flux,'ivar_sdss':iv}
                for k in ['and_mask','or_mask','wdisp','sky','model']:
                    if k in a.names:values[k]=np.asarray(a[k])
        np.savez_compressed(parsed,**values)
    return {'source_url':r['source_url'],'sha256':actual,'status':'verified','raw_path':str(raw)}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workers',type=int,default=4,choices=range(1,5));args=parser.parse_args()
    inputs=[]
    for origin in ['mwdd','sdss']:
        inputs.extend((origin,r) for r in load_json(ROOT/f'results/screen_input_{origin}.json'))
    results=[]
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for i,r in enumerate(pool.map(acquire,inputs),1):
            results.append(r)
            if i%250==0:print(i,'/',len(inputs),'files verified',flush=True)
    (ROOT/'results/redownload_verification.json').write_text(json.dumps(results,indent=2))
    print('All public source files verified; run python run_full_screen.py next.')
