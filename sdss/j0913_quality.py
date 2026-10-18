#!/usr/bin/env python3
"""Independent read-only catalogue checks around J0913+4434."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from hashlib import sha256
import json
import requests

BASE=Path(__file__).resolve().parent/'j0913_quality'
RA=138.4015417
DEC=44.5681725

def fetch(job):
    name,url,params=job
    suffix='json' if name.startswith('sdss') else 'csv'
    path=BASE/f'{name}.{suffix}'
    if path.exists():return dict(name=name,cached=True,path=str(path))
    with requests.get(url,params=params,timeout=(15,50)) as response:
        response.raise_for_status()
        data=response.content
        if len(data)>2_000_000:raise RuntimeError('Unexpectedly large cone response')
        path.write_bytes(data)
        meta=dict(name=name,url=response.url,parameters=params,path=str(path),bytes=len(data),
                  sha256=sha256(data).hexdigest(),retrieved_utc=datetime.now(timezone.utc).isoformat())
        (BASE/f'{name}_provenance.json').write_text(json.dumps(meta,indent=2))
        return meta

def main():
    BASE.mkdir(exist_ok=True)
    cols=['p.objID','p.ra','p.dec','n.distance','p.clean','p.mode','p.type','p.nChild','p.parentID']
    for band in 'ugriz':
        cols.extend([f'p.psfMag_{band}',f'p.psfMagErr_{band}',f'p.psfFlux_{band}',
                     f'p.psfFluxIvar_{band}',f'p.extinction_{band}',f'p.flags_{band}'])
    sdss=('SELECT '+','.join(cols)+
          f' FROM dbo.fGetNearbyObjEq({RA},{DEC},0.166666667) n '+
          'JOIN PhotoObjAll p ON p.objID=n.objID ORDER BY n.distance')
    gaia_cols=['source_id','ra','dec','ref_epoch','parallax','parallax_error','pmra','pmdec',
               'ruwe','duplicated_source','ipd_frac_multi_peak','phot_bp_rp_excess_factor',
               'phot_g_mean_mag','phot_bp_mean_mag','phot_rp_mean_mag','phot_bp_n_obs','phot_rp_n_obs',
               'phot_bp_n_contaminated_transits','phot_bp_n_blended_transits',
               'phot_rp_n_contaminated_transits','phot_rp_n_blended_transits',
               'phot_variable_flag','has_xp_continuous','has_xp_sampled']
    gaia=('SELECT '+','.join(gaia_cols)+
          f",DISTANCE(POINT('ICRS',ra,dec),POINT('ICRS',{RA},{DEC}))*3600 AS separation_arcsec "+
          'FROM gaiadr3.gaia_source '+
          f"WHERE 1=CONTAINS(POINT('ICRS',ra,dec),CIRCLE('ICRS',{RA},{DEC},0.00277777778)) "+
          'ORDER BY separation_arcsec')
    jobs=[('sdss_neighbours','https://skyserver.sdss.org/dr17/SkyServerWS/SearchTools/SqlSearch',
           dict(cmd=sdss,format='json')),
          ('gaia_neighbours','https://gea.esac.esa.int/tap-server/tap/sync',
           dict(REQUEST='doQuery',LANG='ADQL',FORMAT='csv',QUERY=gaia))]
    flag_columns=['objID','dbo.fPhotoFlagsN(flags) AS flags_named']
    flag_columns += [f'dbo.fPhotoFlagsN(flags_{b}) AS flags_{b}_named' for b in 'ugriz']
    flag_query=('SELECT '+','.join(flag_columns)+
                ' FROM PhotoObjAll WHERE objID IN (1237657242969702641,1237657242969702640)')
    jobs.append(('sdss_flags','https://skyserver.sdss.org/dr17/SkyServerWS/SearchTools/SqlSearch',
                 dict(cmd=flag_query,format='json')))
    ps1_columns=['objID','raMean','decMean','nDetections','ng','nr','ni','nz','ny']
    for b in 'grizy':
        ps1_columns.extend([b+'MeanPSFMag',b+'MeanPSFMagErr',b+'MeanPSFMagStd',
                            b+'MeanPSFMagNpt',b+'Flags'])
    jobs.append(('ps1_neighbours','https://catalogs.mast.stsci.edu/api/v0.1/panstarrs/dr2/mean.csv',
                 dict(ra=RA,dec=DEC,radius=10/3600,columns='['+','.join(ps1_columns)+']',
                      **{'nDetections.gt':1})))
    with ThreadPoolExecutor(max_workers=2) as pool:
        for job,result in zip(jobs,pool.map(fetch,jobs)):
            print(json.dumps(result),flush=True)

if __name__=='__main__':main()
