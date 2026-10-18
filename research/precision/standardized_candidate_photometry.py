#!/usr/bin/env python3
"""Supplement the frozen screen with source-attributed Pan-STARRS calibration.

One DESI record per shortlisted source is selected before recalculation, by
pixel S/N and record ID, never by the resulting colour. The Swan external
photometry table supplies observed gri AB magnitudes, not atmosphere fits.
The frozen screen and original headline numbers remain versioned baselines.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
os.environ.setdefault('OMP_NUM_THREADS','1')
import numpy as np
import pandas as pd
import colour_pipeline as c
import validate_candidates as validation
from research.outlier_audit.audit import inputs

OUT=Path(__file__).resolve().parent/'candidate_recalibration'
OUT.mkdir(exist_ok=True)

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def run():
    objects=pd.read_csv(ROOT/'research/outlier_audit/object_audit.csv',dtype={'source_id':'string'})
    targets=objects[objects.review_status.eq('multiple_instrument_colour_candidate')]
    records=pd.read_csv(ROOT/'research/outlier_audit/record_audit.csv.gz',dtype={'source_id':'string'},low_memory=False)
    input_path=ROOT/'research/literature/sources/candidate27_prior_rows.json'
    prior=json.loads(input_path.read_text())['candidates']
    frozen=inputs();rows=[];manifest=[]
    quality=pd.read_csv(ROOT/'research/external_validation/results/gaia_extended_quality.csv',dtype={'source_id':'string'}).set_index('source_id')
    for target in targets.sort_values('source_id').itertuples():
        sid=target.source_id
        common={'source_id':sid,'names':target.names,'old_calibrated_records':target.calibrated_records,
            'photometry_source':'Swan et al. 2026 externalData_1.0, observed Pan-STARRS gri AB magnitudes',
            'photometry_table_rows_sha256':sha(input_path),'reddening_treatment':'Observed colour at Earth; no extinction correction applied',
            'photometric_error_floor_mag':.02}
        phot=prior.get(sid,{}).get('swan_external',[])
        if len(phot)!=1:
            rows.append({**common,'status':'external_photometry_unavailable'});continue
        data=phot[0]
        common['swan_WDJname']=data.get('WDJname','')
        try:
            mags=np.array([float(data[f'Pan-STARRS.{b}']) for b in 'gri'])
            errors=np.array([float(data[f'Pan-STARRS.{b}_error']) for b in 'gri'])
            if not (np.all(np.isfinite(mags)) and np.all(np.isfinite(errors)) and np.all(errors>0) and np.all(errors<=.1)):
                raise ValueError('Missing, non-positive or >0.10-mag photometric uncertainty')
            for b,m,e in zip('gri',mags,errors):common.update({f'anchor_{b}_mag':float(m),f'anchor_{b}_error':float(e)})
            eligible=records[records.source_id.eq(sid)&records.kind.eq('DESI')&records.usable_screen.eq(True)]
            if not len(eligible):
                rows.append({**common,'status':'eligible_DESI_unavailable'});continue
            selected=eligible.sort_values(['visible_median_pixel_snr','record_id'],ascending=[False,True],na_position='last').iloc[0]
            index=int(selected.row_index);rec=frozen[index][1]
            raw=c.data_path(rec['raw_path']);parsed=c.data_path(rec['parsed_path'])
            if sha(raw)!=rec['sha256']:raise ValueError('Original spectrum SHA256 differs')
            sp=np.load(parsed);w=sp['wavelength_angstrom'];f=sp['flux_original'] if 'flux_original' in sp else sp['flux_flam']
            iv=None
            if 'sigma' in sp:
                s=sp['sigma'];iv=np.divide(1,s*s,out=np.zeros_like(s),where=np.isfinite(s)&(s>0))
            elif 'ivar' in sp:iv=sp['ivar']
            common.update(selected_row_index=index,raw_sha256=rec['sha256'],source_url=rec['source_url'],
                old_screen_duv=float(selected.duv),old_screen_hex=selected.hex,old_screen_calibrated=bool(selected.calibrated))
            fc,cal=c.recalibrate_gri(w,f,mags,errors,'panstarrs')
            gate=bool(cal['cal_max_residual_mag']<.15 and abs(cal['cal_tilt_mag_per_1000A'])<.25)
            common.update(cal)
            if not gate:
                rows.append({**common,'status':'calibration_quality_gate_failed'});continue
            correction=10**(-.4*(cal['cal_offset_mag']+cal['cal_tilt_mag_per_1000A']*(w-6200)/1000))
            ivc=None if iv is None else iv/correction**2
            metric=c.integrate_colour(w,fc,ivc,mask_sky=True)
            uncertainty,draws=validation.mc(w,fc,ivc,'panstarrs',errors,n=6000,mask_sky=True)
            if not np.all(np.isfinite(draws)):raise ValueError('Nonfinite conditional Monte Carlo draw')
            common.update(status='calibrated_conditional',**metric,**uncertainty)
            common['old_to_standardized_uv_shift']=float(np.hypot(metric['u1960']-selected.u1960,metric['v1960']-selected.v1960))
            common['mean_outside_001']=metric['distance_planck_uv']>.01
            common['conditional_95_interval_beyond_001']=bool(uncertainty['duv_mc_p025']>.01 or uncertainty['duv_mc_p975']<-.01)
            field=quality.loc[sid]
            common['gaia_variable_flag']=field.phot_variable_flag
            common['catalogued_neighbour_count_10arcsec']=int(field.gaia_neighbour_count_10arcsec)
            common['interpretation']='Conditional spectrum+photometry noise and two-parameter recalibration only; inter-pixel covariance, non-simultaneity, spectral shape systematics and selection are not fully modelled.'
            npz=OUT/f'{sid}_DESI_PS1.npz'
            np.savez_compressed(npz,wavelength_angstrom=w,flux_original=f,flux_calibrated=fc,
                inverse_variance_original=np.array([]) if iv is None else iv,
                inverse_variance_calibrated=np.array([]) if ivc is None else ivc)
            manifest.append({'source_id':sid,'path':npz.name,'sha256':sha(npz),'original_record':rec,'photometry_row':data,
                'selection_rule':'Highest visible median pixel S/N among eligible DESI records, record_id as deterministic tiebreak; no computed-colour selection'})
            print(sid,common['swan_WDJname'],metric['hex'],round(metric['duv'],6),
                  '95%',round(uncertainty['duv_mc_p025'],6),round(uncertainty['duv_mc_p975'],6),flush=True)
            rows.append(common)
        except Exception as exc:
            rows.append({**common,'status':'error','error':str(exc)})
            print('ERROR',sid,str(exc),flush=True)
    table=pd.DataFrame(rows);table.to_csv(OUT/'standardized_colours.csv',index=False)
    (OUT/'derivative_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    passed=table.status.eq('calibrated_conditional')
    summary={'targets':len(table),'status_counts':table.status.value_counts().to_dict(),
        'newly_anchored_entities':int((passed&table.old_calibrated_records.eq(0)).sum()),
        'mean_outside_001':int(table.loc[passed,'mean_outside_001'].sum()),
        'conditional_interval_beyond_001':int(table.loc[passed,'conditional_95_interval_beyond_001'].sum()),
        'input_photometry_rows_sha256':sha(input_path),'pipeline_sha256':sha(ROOT/'colour_pipeline.py'),
        'conditional_mc_sha256':sha(ROOT/'validate_candidates.py'),
        'precision_caution':'Formal conditional intervals are not total uncertainties or discovery probabilities. The shared PS1 anchors are not independent new observations.',
        'baseline_caution':'Original 0.1 results retained. This separately attributed PS1 calibration need not equal the old screen (which preferred SDSS when available).'}
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))

if __name__=='__main__':run()
