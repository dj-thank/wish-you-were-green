#!/usr/bin/env python3
"""Read-only official PS1 neighbourhood check for the secondary green candidate."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from hashlib import sha256
import json
import requests

BASE=Path(__file__).resolve().parent/'secondary_quality'
CANDIDATES={
    'J0429-0354':(67.436292,-3.906506,'3204436719718449280'),
}

def fetch(job):
    label,service,url,params=job
    path=BASE/f'{label}_{service}.csv'
    if path.exists():return {'label':label,'service':service,'cached':True,'path':str(path)}
    response=requests.get(url,params=params,timeout=(15,50))
    response.raise_for_status()
    data=response.content
    if len(data)>2_000_000:raise RuntimeError('Unexpectedly large cone response')
    path.write_bytes(data)
    meta={'label':label,'service':service,'url':response.url,'parameters':params,
          'path':str(path),'bytes':len(data),'sha256':sha256(data).hexdigest(),
          'retrieved_utc':datetime.now(timezone.utc).isoformat()}
    (BASE/f'{label}_{service}_provenance.json').write_text(json.dumps(meta,indent=2))
    return meta

def main():
    BASE.mkdir(exist_ok=True)
    jobs=[]
    gaia_cols=['source_id','ra','dec','ref_epoch','parallax','parallax_error','pmra','pmdec',
               'ruwe','duplicated_source','ipd_frac_multi_peak','phot_bp_rp_excess_factor',
               'phot_g_mean_mag','phot_bp_mean_mag','phot_rp_mean_mag','phot_bp_n_obs','phot_rp_n_obs',
               'phot_bp_n_contaminated_transits','phot_bp_n_blended_transits',
               'phot_rp_n_contaminated_transits','phot_rp_n_blended_transits',
               'phot_variable_flag','has_xp_continuous','has_xp_sampled']
    ps1_cols=['objID','raMean','decMean','nDetections','ng','nr','ni','nz','ny']
    for b in 'grizy':
        ps1_cols.extend([b+'MeanPSFMag',b+'MeanPSFMagErr',b+'MeanPSFMagStd',b+'MeanPSFMagNpt',b+'Flags'])
    for label,(ra,dec,source_id) in CANDIDATES.items():
        gaia=('SELECT '+','.join(gaia_cols)+
              f",DISTANCE(POINT('ICRS',ra,dec),POINT('ICRS',{ra},{dec}))*3600 AS separation_arcsec "+
              'FROM gaiadr3.gaia_source '+
              f"WHERE 1=CONTAINS(POINT('ICRS',ra,dec),CIRCLE('ICRS',{ra},{dec},0.00277777778)) "+
              'ORDER BY separation_arcsec')
        jobs.append((label,'ps1','https://catalogs.mast.stsci.edu/api/v0.1/panstarrs/dr2/mean.csv',
                     dict(ra=ra,dec=dec,radius=10/3600,columns='['+','.join(ps1_cols)+']',
                          **{'nDetections.gt':1})))
    with ThreadPoolExecutor(max_workers=2) as pool:
        for result in pool.map(fetch,jobs):print(json.dumps(result),flush=True)

if __name__=='__main__':main()
