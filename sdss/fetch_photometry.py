#!/usr/bin/env python3
"""Query official DR17 PSF photometry by the public FITS BESTOBJID match."""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import json
import numpy as np
import pandas as pd
import requests
from astropy.io import fits

BASE=Path(__file__).resolve().parent
SERVICE='https://skyserver.sdss.org/dr17/SkyServerWS/SearchTools/SqlSearch'

def get_identifiers():
    records={}
    for line in (BASE/'download_manifest.jsonl').read_text().splitlines():
        r=json.loads(line)
        if r.get('status')=='ok':records[r['spectrum_id']]=r
    identifiers={}
    embedded=[]
    for r in records.values():
        with fits.open(r['path'],memmap=False) as h:
            d=h[2].data
            key='BESTOBJID' if 'BESTOBJID' in d.names else 'OBJID'
            if key not in d.names:continue
            objid=str(d[key][0]).strip()
            if objid.isdigit() and int(objid)>0:
                identifiers.setdefault(objid,[]).append(r['spectrum_id'])
                if all(k in d.names for k in ['PSFFLUX','PSFFLUX_IVAR','PSFMAG','PSFMAGERR']):
                    out=dict(objID=objid,spectrum_id=r['spectrum_id'],source='SDSS_DR17_FITS_HDU2',
                             source_url=r['url'],source_path=r['path'],source_sha256=r['sha256'])
                    for source,target in [('RA','ra'),('DEC','dec'),('CLEAN','clean'),('OBJC_TYPE','type')]:
                        if source in d.names:out[target]=d[source][0].item()
                    for i,band in enumerate('ugriz'):
                        for source,target in [('PSFFLUX','psfFlux'),('PSFFLUX_IVAR','psfFluxIvar'),
                                              ('PSFMAG','psfMag'),('PSFMAGERR','psfMagErr'),
                                              ('EXTINCTION','extinction'),('FLAGS','flags'),('FLAGS2','flags2')]:
                            if source in d.names:
                                val=d[source][0][i].item()
                                out[target+'_'+band]=val if not isinstance(val,float) or np.isfinite(val) else None
                    embedded.append(out)
    templates={r['objID']:r for r in embedded}
    covered={r['spectrum_id'] for r in embedded}
    for objid,spectrum_ids in identifiers.items():
        if objid not in templates:continue
        for spectrum_id in spectrum_ids:
            if spectrum_id in covered:continue
            template=templates[objid]
            embedded.append(dict(template,spectrum_id=spectrum_id,
                                  source_spectrum_id=template['spectrum_id']))
    return identifiers,embedded

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--max-objects',type=int,default=2000)
    p.add_argument('--batch-size',type=int,default=40)
    args=p.parse_args()
    folder=BASE/'photometry'
    folder.mkdir(exist_ok=True)
    ids,embedded=get_identifiers()
    (folder/'bestobjid_match.json').write_text(json.dumps(ids,indent=2))
    (folder/'embedded_photometry.json').write_text(json.dumps(embedded,indent=2))
    embedded_ids={r['objID'] for r in embedded}
    keys=sorted(set(ids)-embedded_ids,key=int)[:args.max_objects]
    cols=['objID','ra','dec','clean','type']
    for band in 'ugriz':
        cols.extend([f'psfMag_{band}',f'psfMagErr_{band}',f'psfFlux_{band}',
                     f'psfFluxIvar_{band}',f'extinction_{band}'])
    output=[]
    with requests.Session() as session:
        for start in range(0,len(keys),args.batch_size):
            batch=keys[start:start+args.batch_size]
            query='SELECT '+','.join(cols)+' FROM PhotoObjAll WHERE objID IN ('+','.join(batch)+')'
            tag=hashlib.sha256(query.encode()).hexdigest()[:16]
            path=folder/f'query-{tag}.json'
            if not path.exists():
                response=session.get(SERVICE,params={'cmd':query,'format':'json'},timeout=(15,50))
                response.raise_for_status()
                path.write_bytes(response.content)
                meta=dict(url=response.url,query=query,path=str(path),
                          bytes=len(response.content),sha256=hashlib.sha256(response.content).hexdigest(),
                          retrieved_utc=datetime.now(timezone.utc).isoformat())
                (folder/f'query-{tag}-provenance.json').write_text(json.dumps(meta,indent=2))
            result=json.loads(path.read_text())
            print(json.dumps(dict(batch=start,requested=len(batch),response_type=type(result).__name__,
                                  preview=str(result)[:500])),flush=True)
            if isinstance(result,list):
                for table in result:
                    if isinstance(table,dict) and 'Rows' in table:
                        output.extend(r for r in table['Rows'] if isinstance(r,dict) and 'objID' in r)
            elif isinstance(result,dict) and 'Rows' in result:
                output.extend(r for r in result['Rows'] if isinstance(r,dict) and 'objID' in r)
            else:
                raise RuntimeError('Unexpected response schema; raw response retained')
    (folder/'photometry_raw_rows.json').write_text(json.dumps(output,indent=2))
    combined=embedded.copy()
    for r in output:
        if not isinstance(r,dict):raise RuntimeError('Column-based response not yet supported')
        objid=str(r['objID'])
        for spectrum_id in ids.get(objid,[]):
            rr=r.copy()
            rr.update(objID=objid,spectrum_id=spectrum_id,source='SDSS_DR17_SkyServer_PhotoObjAll')
            combined.append(rr)
    (folder/'photometry.json').write_text(json.dumps(combined,indent=2))
    if combined:pd.DataFrame(combined).to_csv(folder/'photometry.csv',index=False)
    print(json.dumps(dict(objects_requested=len(keys),query_rows=len(output),embedded_rows=len(embedded),
                          combined_spectra=len(combined))),flush=True)

if __name__=='__main__':main()
