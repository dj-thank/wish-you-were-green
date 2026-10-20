"""Run the unit-aware two-archive screen into a separate output directory.

Frozen inputs are used exactly. Raw downloads are a separate explicit command.
The legacy option exists only to reproduce the known-flawed historical screen.
"""
from pathlib import Path
import os
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
os.environ.setdefault('OMP_NUM_THREADS','1')
from project_io import load_json
import argparse, json, time
from functools import partial
from concurrent.futures import ProcessPoolExecutor
import numpy as np
import pandas as pd
from astropy.coordinates import SkyCoord
from astropy import units as u
from colour_pipeline import analyze_record
from rank_candidates import annotate, summarize
ROOT=Path(__file__).resolve().parent

def mwdd_records():
    return [r for r in load_json(ROOT/'mwdd/manifest_enriched.json') if r.get('parsed_path')]

def sdss_records(mw):
    data=load_json(ROOT/'sdss/manifest_with_photometry.json')
    unique={r['wdid']:r for r in mw}
    base=[r for r in unique.values() if r.get('ra_deg') is not None and r.get('dec_deg') is not None and np.isfinite(r['ra_deg']) and np.isfinite(r['dec_deg'])]
    mc=SkyCoord([r['ra_deg'] for r in base]*u.deg,[r['dec_deg'] for r in base]*u.deg)
    sc=SkyCoord([r['ra'] for r in data]*u.deg,[r['dec'] for r in data]*u.deg)
    ix,sep,_=sc.match_to_catalog_sky(mc)
    out=[]
    for j,r in enumerate(data):
        match=base[ix[j]] if sep.arcsec[j]<5 else None
        p={}
        # Positive matched PSF fluxes are converted to AB magnitudes. This avoids
        # the low-S/N asinh magnitude convention and transcription errors.
        if r.get('photometry_available'):
            for b in 'gri':
                flux=r.get(b+'_psf_flux_nanomaggies');ivar=r.get(b+'_psf_flux_ivar')
                if flux is not None and flux>0:
                    p['s'+b]=float(22.5-2.5*np.log10(flux))
                    if ivar is not None and ivar>0:p['Ds'+b]=float(2.5/np.log(10)/flux/np.sqrt(ivar))
                else:
                    p['s'+b]=r.get(b+'_psf_mag');p['Ds'+b]=r.get(b+'_psf_mag_err')
        out.append({'wdid':match['wdid'] if match else r['name'],
                    'source_id':match.get('source_id') if match else '',
                    'spectype':r['type'],'teff':match.get('teff') if match else None,
                    'ra_deg':r['ra'],'dec_deg':r['dec'],'kind':'SDSS',
                    'source_url':r['url'],'star_page_url':match.get('star_page_url') if match else r['catalogue_url'],
                    'parsed_path':r['array_path'],'raw_path':r['path'],'sha256':r['sha256'],
                    'photometry':p,'photometry_clean':r.get('photometry_clean'),
                    'spectrum_id':r['spectrum_id'],'selection_group':r['selection_group'],
                    'mwdd_match_sep_arcsec':float(sep.arcsec[j]),'archive_origin':'SDSS_DR17_direct'})
    return out

def run(records,label,output_dir=None,legacy_unverified_units=False):
    output_dir=Path(output_dir) if output_dir is not None else ROOT/'results/validated_screen'
    output_dir.mkdir(parents=True,exist_ok=True)
    start=time.time();rows=[]
    with ProcessPoolExecutor(max_workers=4) as pool:
        for i,(r,result) in enumerate(zip(records,pool.map(partial(analyze_record,legacy_unverified_units=legacy_unverified_units),records,chunksize=8)),1):
            result['archive_origin']=r.get('archive_origin','MWDD')
            rows.append(result)
            if i%500==0:print(label,i,'/',len(records),'elapsed_s',round(time.time()-start),flush=True)
    t=pd.DataFrame(rows)
    t=annotate(t,legacy_unverified_units=legacy_unverified_units)
    t.to_csv(output_dir/f'{label}_screen_annotated.csv',index=False)
    t.to_csv(output_dir/f'{label}_screen.csv',index=False)
    summarize(t).to_csv(output_dir/f'{label}_object_candidates.csv',index=False)
    print(label,'DONE',len(t),'records',t.wdid.nunique(),'identifiers',round(time.time()-start),'s',flush=True)
    return t

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,default=ROOT/'results/validated_screen')
    parser.add_argument('--legacy-reproduction',action='store_true',help='Reproduce historical mixed-unit assumptions; not valid current discovery evidence')
    args=parser.parse_args()
    destination=args.output_dir.resolve()
    if destination==(ROOT/'results').resolve():
        parser.error('Choose a separate output directory; frozen research inputs/results must be preserved')
    destination.mkdir(parents=True,exist_ok=True)
    mw=load_json(ROOT/'results/screen_input_mwdd.json')
    ss=load_json(ROOT/'results/screen_input_sdss.json')
    tables=[run(mw,'mwdd',destination,args.legacy_reproduction),run(ss,'sdss',destination,args.legacy_reproduction)]
    combined=pd.concat(tables,ignore_index=True)
    combined.to_csv(destination/'all_spectra_screen.csv.gz',index=False,compression={'method':'gzip','mtime':0})
    summarize(combined).to_csv(destination/'all_object_candidates.csv',index=False)
    summary={'input_mwdd_spectra':len(mw),'input_sdss_spectra':len(ss),
             'combined_spectrum_records':len(combined),
             'screen_eligible_records':int(combined.usable_screen.sum()),
             'status_counts':combined.status.value_counts().to_dict(),
             'legacy_reproduction_only':args.legacy_reproduction,
             'flux_convention_policy':'Require source-format evidence; mixed MWDD SDSS requires raw-SHA native-pixel matching. F_nu is converted before integration and recalibration.',
             'identity_caution':'Frozen epoch-unpropagated 5 arcsec assignments are retained, not newly validated identities. Repeated archives are not independent observations.',
             'screen_caution':'Exploratory colour eligibility, not global discovery significance or complete systematic-error control.'}
    (destination/'screen_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2),flush=True)
