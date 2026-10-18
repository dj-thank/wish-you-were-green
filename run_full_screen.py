"""Run the frozen two-archive colour screen. No network access is required."""
from pathlib import Path
import os
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
os.environ.setdefault('OMP_NUM_THREADS','1')
from project_io import load_json
import json, time
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

def run(records,label):
    start=time.time();rows=[]
    with ProcessPoolExecutor(max_workers=4) as pool:
        for i,(r,result) in enumerate(zip(records,pool.map(analyze_record,records,chunksize=8)),1):
            result['archive_origin']=r.get('archive_origin','MWDD')
            rows.append(result)
            if i%500==0:print(label,i,'/',len(records),'elapsed_s',round(time.time()-start),flush=True)
    t=pd.DataFrame(rows)
    t=annotate(t)
    t.to_csv(ROOT/'results'/f'{label}_screen_annotated.csv',index=False)
    t.to_csv(ROOT/'results'/f'{label}_screen.csv',index=False)
    summarize(t).to_csv(ROOT/'results'/f'{label}_object_candidates.csv',index=False)
    print(label,'DONE',len(t),'records',t.wdid.nunique(),'identifiers',round(time.time()-start),'s',flush=True)
    return t

if __name__=='__main__':
    mw=mwdd_records()
    ss=sdss_records(mw)
    # Freeze inputs independently of any subsequent database update.
    (ROOT/'results/screen_input_mwdd.json').write_text(json.dumps(mw,ensure_ascii=False,indent=2))
    (ROOT/'results/screen_input_sdss.json').write_text(json.dumps(ss,ensure_ascii=False,indent=2))
    tables=[run(mw,'mwdd'),run(ss,'sdss')]
    combined=pd.concat(tables,ignore_index=True)
    combined.to_csv(ROOT/'results/all_spectra_screen.csv',index=False)
    summ=summarize(combined)
    summ.to_csv(ROOT/'results/all_object_candidates.csv',index=False)
    summary={'input_mwdd_spectra':len(mw),'input_mwdd_identifiers':len(set(r['wdid'] for r in mw)),
             'input_sdss_spectra':len(ss),'input_sdss_identifiers':len(set(r['wdid'] for r in ss)),
             'combined_spectrum_records':len(combined),'combined_identifiers_after_5arcsec_match':combined.wdid.nunique(),
             'screen_eligible_records':int(combined.usable_screen.sum()),
             'not_in_hollands2026_identifiers_eligible':len(summ),
             'known_hollands_matched_records':int(combined.known_hollands_colour.sum()),
             'calibrated_records':int(combined.calibrated.fillna(False).sum()),
             'verified_source_format_records':int(combined.source_format_screen_ok.sum()),
             'screen_definition':'SDSS/DESI/GaiaXP F_lambda source convention; CMF coverage>99.5%, wavelength gap<150A; valid gri tilt if available. This is not a quality-assured discovery catalogue.',
             'id_count_caution':'5 arcsec cross-match may leave high-proper-motion duplicates; SDSS and MWDD may contain the same SDSS observation.'}
    (ROOT/'results/screen_summary.json').write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary,indent=2),flush=True)
