#!/usr/bin/env python3
"""A record-by-record, provenance-preserving audit of the frozen colour screen.

The review triggers are descriptive, exploratory triage rules, not significance
tests. No point is moved towards the stellar locus or silently discarded.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed, ProcessPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
os.environ.setdefault('OMP_NUM_THREADS', '1')
import numpy as np
import pandas as pd
from project_io import load_json

OUT = Path(__file__).resolve().parent
MILD = 0.006
STRONG = 0.01
DISAGREEMENT = 0.005
CALIBRATION_SHIFT = 0.003


def utc():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def is_true(series):
    return series.eq(True)


def canonical_id(source_id, wdid):
    # A provisional SDSS-to-MWDD positional match in the old input is retained
    # and explicitly recorded below, never promoted to an independent identity.
    return 'gaia:' + str(source_id) if pd.notna(source_id) and str(source_id) else 'name:' + str(wdid).strip()


def inputs():
    records = []
    for origin in ['mwdd', 'sdss']:
        records.extend((origin, r) for r in load_json(ROOT / f'results/screen_input_{origin}.json'))
    return records


def census():
    original = ROOT / 'results/all_spectra_screen.csv.gz'
    tab = pd.read_csv(original, dtype={'source_id': 'string'}, low_memory=False)
    frozen = inputs()
    assert len(tab) == len(frozen), 'Frozen input/output length differs'
    for i, (_, r) in enumerate(frozen):
        assert tab.iloc[i].source_url == r['source_url'], f'Input row order differs: {i}'
        assert tab.iloc[i].sha256 == r['sha256'], f'Input identity differs: {i}'
    tab.insert(0, 'row_index', np.arange(len(tab)))
    tab['entity_id'] = [canonical_id(r.source_id, r.wdid) for r in tab.itertuples()]
    tab['record_id'] = [hashlib.sha256((o + '\n' + r['source_url'] + '\n' + r['sha256']).encode()).hexdigest()[:20] for o, r in frozen]
    tab['identity_basis'] = [
        'legacy_5arcsec_positional_match_unpropagated' if o == 'sdss' and r.get('source_id')
        else 'catalogue_gaia_identifier' if r.get('source_id') else 'catalogue_name_only'
        for o, r in frozen]
    tab['legacy_match_sep_arcsec'] = [r.get('mwdd_match_sep_arcsec', np.nan) for _, r in frozen]
    tab['same_raw_sha_records'] = tab.groupby('sha256').sha256.transform('size')
    tab['calibration_uv_shift'] = np.hypot(tab.u1960-tab.raw_u1960, tab.v1960-tab.raw_v1960)
    usable = is_true(tab.usable_screen) & tab.status.eq('ok')
    tab['mild_colour_review'] = usable & tab.distance_planck_uv.ge(MILD)
    tab['strong_colour_review'] = usable & tab.distance_planck_uv.ge(STRONG)
    tab['calibration_review'] = usable & tab.calibration_uv_shift.ge(CALIBRATION_SHIFT)
    tab['endpoint_review'] = usable & is_true(tab.nearest_is_RJ_limit)
    tab['gap_review'] = usable & tab.largest_visible_gap_A.gt(50)
    tab['negative_flux_review'] = usable & tab.visible_negative_fraction.gt(.1)
    tab['boundary_colour_review'] = usable & is_true(tab.green_dominant)

    objects = []
    for key, group in tab.groupby('entity_id', sort=True):
        good = group[is_true(group.usable_screen) & group.status.eq('ok')]
        uv = good[['u1960','v1960']].to_numpy(float)
        spread = float(np.sqrt(((uv[:, None, :] - uv[None, :, :])**2).sum(axis=2)).max()) if len(uv) else np.nan
        kinds = sorted(set(good.kind))
        reasons = []
        for field, label in [('mild_colour_review','colour_distance_ge_0.006'),
                             ('calibration_review','calibration_shift_ge_0.003'),
                             ('endpoint_review','rayleigh_jeans_endpoint'),
                             ('gap_review','interpolated_gap_gt_50A'),
                             ('negative_flux_review','negative_pixel_fraction_gt_0.1'),
                             ('boundary_colour_review','green_channel_boundary')]:
            if group[field].any(): reasons.append(label)
        if spread >= DISAGREEMENT: reasons.append('between_records_uv_ge_0.005')
        if group.status.ne('ok').any(): reasons.append('processing_error')
        raw_extreme = (group.distance_planck_uv.ge(STRONG) | group.raw_distance_planck_uv.ge(STRONG)) & ~is_true(group.usable_screen)
        if raw_extreme.any(): reasons.append('ineligible_record_with_large_distance')
        calibrated = good[is_true(good.calibrated)]
        ground = good[good.kind.isin(['DESI','SDSS'])]
        strong = good[good.distance_planck_uv.ge(STRONG)]
        # A same-instrument record in two repositories is not replication.
        independent = len(kinds)
        if not len(good): status = 'not_colour_eligible'
        elif is_true(group.known_hollands_colour).any(): status = 'published_comparison_target'
        elif raw_extreme.any() and not len(strong): status = 'unsupported_extreme_record'
        elif spread >= DISAGREEMENT: status = 'discordant_records_require_review'
        elif not len(ground): status = 'gaia_only_requires_spectrum'
        elif len(strong) and independent >= 2: status = 'multiple_instrument_colour_candidate'
        elif len(strong): status = 'single_instrument_colour_candidate'
        elif reasons: status = 'borderline_or_quality_review'
        else: status = 'no_current_review_trigger'
        if len(good):
            # Selection uses quality and instrument preference, never extremeness.
            ranked = good.assign(_cal=is_true(good.calibrated).astype(int),
                _ground=good.kind.map({'DESI':2,'SDSS':1,'Gaia_XP':0}).fillna(-1),
                _snr=good.visible_median_pixel_snr.fillna(-1),
                _res=good.cal_max_residual_mag.fillna(1))
            representative = ranked.sort_values(['_cal','_ground','_snr','_res','record_id'], ascending=[False,False,False,True,True]).iloc[0]
            rep = {f'representative_{k}': representative[k] for k in ['record_id','row_index','kind','x','y','u1960','v1960','duv','hex','calibrated']}
        else:
            rep = {}
        objects.append(dict(entity_id=key,source_id=next((str(x) for x in group.source_id if pd.notna(x)),''),
            names=' | '.join(sorted(set(group.wdid.astype(str)))),
            spectral_types=' | '.join(sorted(set(group.spectype.dropna().astype(str)))),
            ra_deg=group.ra_deg.iloc[0],dec_deg=group.dec_deg.iloc[0],
            records=len(group),unique_raw_sha=group.sha256.nunique(),eligible_records=len(good),
            calibrated_records=len(calibrated),ground_records=len(ground),instrument_kinds='|'.join(kinds),
            instrument_count=independent,strong_records=len(strong),
            min_distance=float(good.distance_planck_uv.min()) if len(good) else np.nan,
            max_distance=float(good.distance_planck_uv.max()) if len(good) else np.nan,
            median_duv=float(good.duv.median()) if len(good) else np.nan,
            between_records_uv=spread,max_calibration_uv_shift=float(good.calibration_uv_shift.max()) if len(good) else np.nan,
            has_positional_identity=group.identity_basis.eq('legacy_5arcsec_positional_match_unpropagated').any(),
            known_hollands_colour=is_true(group.known_hollands_colour).any(),
            review_required=bool(reasons),review_reasons='|'.join(reasons),review_status=status,**rep))
    obj = pd.DataFrame(objects)
    tab['review_required'] = tab.entity_id.map(obj.set_index('entity_id').review_required)
    OUT.mkdir(parents=True, exist_ok=True)
    tab.to_csv(OUT/'record_audit.csv.gz',index=False,compression={'method':'gzip','mtime':0})
    obj.to_csv(OUT/'object_audit.csv',index=False)
    obj[obj.review_required].to_csv(OUT/'review_queue.csv',index=False)
    counts = {k:int(v) for k,v in obj.review_status.value_counts().items()}
    summary = dict(created_utc=utc(),input_sha256=sha(original),records=len(tab),
        catalogue_entity_keys=len(obj),entity_key_caution='Gaia ID where supplied; existing epoch-unpropagated positional assignments retained and flagged. Not a new confirmed unique-star census.',
        eligible_records=int(usable.sum()),strong_outlier_records=int(tab.strong_colour_review.sum()),
        strong_outlier_entities=int(tab.loc[tab.strong_colour_review,'entity_id'].nunique()),
        review_entities=int(obj.review_required.sum()),review_records=int(tab.review_required.sum()),
        review_status_counts=counts,thresholds={'mild_distance':MILD,'strong_distance':STRONG,
            'between_records_uv':DISAGREEMENT,'calibration_shift_uv':CALIBRATION_SHIFT},
        interpretation='Exploratory triage thresholds, not p-values, confidence levels, or false discovery control.',
        records_outside_legacy_axes=int((usable & (~tab.u1960.between(.15,.34) | ~tab.v1960.between(.23,.385))).sum()))
    (OUT/'census_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2),flush=True)
    return tab,obj


def fetch():
    from download_frozen_spectra import acquire
    tab = pd.read_csv(OUT/'record_audit.csv.gz', dtype={'source_id':'string'},low_memory=False)
    frozen = inputs()
    selected = tab[is_true(tab.review_required) & tab.kind.isin(['SDSS','DESI','Gaia_XP'])]
    jobs = [(int(i), frozen[int(i)]) for i in selected.row_index]
    checkpoint = OUT/'retrieval.jsonl'
    old = {}
    if checkpoint.exists():
        for line in checkpoint.read_text().splitlines():
            r=json.loads(line);old[r['row_index']]=r
    jobs=[x for x in jobs if old.get(x[0],{}).get('status')!='verified']
    print('Public raw-spectrum retrieval:',len(jobs),'remaining of',len(selected),flush=True)
    def one(job):
        i,item=job
        for attempt in range(2):
            try:
                result=acquire(item)
                # Absolute paths are runtime details; provenance stores repo-relative inputs.
                return dict(row_index=i,status='verified',source_url=item[1]['source_url'],
                    sha256=result['sha256'],raw_path=item[1]['raw_path'],parsed_path=item[1]['parsed_path'],checked_utc=utc())
            except Exception as exc:
                error=str(exc)
        return dict(row_index=i,status='retrieval_failed',source_url=item[1]['source_url'],error=error,checked_utc=utc())
    with checkpoint.open('a') as stream, ThreadPoolExecutor(max_workers=4) as pool:
        pending=[pool.submit(one,job) for job in jobs]
        for count,future in enumerate(as_completed(pending),1):
            result=future.result();old[result['row_index']]=result
            stream.write(json.dumps(result)+'\n');stream.flush()
            if count%100==0 or result['status']!='verified':
                print(count,'/',len(jobs),'verified',sum(x['status']=='verified' for x in old.values()),
                      'last',result['status'],flush=True)
    summary={'created_utc':utc(),'requested_records':len(selected),'verified_records':sum(x['status']=='verified' for x in old.values()),
             'failed_records':sum(x['status']!='verified' for x in old.values()),'raw_bytes_retained_in_ignored_cache':True,
             'reproduction':'Use audit.py fetch to recover exact public inputs. SHA256 mismatch is a failure, never substituted.'}
    (OUT/'retrieval_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(summary,flush=True)


def recompute_one(item):
    import colour_pipeline as c
    i,origin,rec=item
    out={'row_index':i,'source_url':rec['source_url'],'raw_sha256':rec['sha256']}
    try:
        p=c.data_path(rec['parsed_path'])
        raw=c.data_path(rec['raw_path'])
        if not raw.exists() or sha(raw)!=rec['sha256']:
            raise ValueError('Missing or mismatched original spectrum')
        data=np.load(p)
        w=data['wavelength_angstrom'];f=data['flux_original'] if 'flux_original' in data else data['flux_flam']
        iv=None
        if 'sigma' in data:
            sigma=data['sigma'];iv=np.divide(1,sigma**2,out=np.zeros_like(sigma),where=np.isfinite(sigma)&(sigma>0))
        elif 'ivar' in data:iv=data['ivar']
        # Deliberately reproduce the frozen 0.1 values, including its known
        # ambiguous-unit assumption. Corrected scientific results are separate.
        nominal=c.analyze_record(rec,legacy_unverified_units=True)
        out['recompute_status']=nominal['status']
        for key in ['u1960','v1960','duv','hex','green_channel_margin','calibrated','cal_system','cal_max_residual_mag',
                    'raw_u1960','raw_v1960','raw_duv','raw_hex','uv_stat_error_max']:
            out['recomputed_'+key]=nominal.get(key)
        if nominal['status']!='ok':
            out['error']=nominal.get('error');return out
        no_mask=c.integrate_colour(w,f,iv,mask_sky=False)
        baseline=c.integrate_colour(w,f,iv,mask_sky=rec['kind']!='Gaia_XP')
        out['raw_sky_mask_uv_shift']=float(np.hypot(no_mask['u1960']-baseline['u1960'],no_mask['v1960']-baseline['v1960']))
        cw,cf,ci=c.clean_spectrum(w,f,iv,mask_sky=rec['kind']!='Gaia_XP')
        visible=(cw>=3600)&(cw<=8300);cw,cf=cw[visible],cf[visible]
        cmf=np.column_stack([np.interp(cw/10,c.CMF_W,c.CMF_V[:,j],left=0,right=0) for j in range(3)])
        coeff=cmf*c.trapezoid_weights(cw/10)[:,None]
        terms=cf[:,None]*coeff
        absolute=np.abs(terms).sum(axis=0)
        out['negative_CIE_Y_absolute_fraction']=float(np.abs(terms[cf<0,1]).sum()/absolute[1])
        out['largest_single_pixel_CIE_Y_absolute_fraction']=float(np.max(np.abs(terms[:,1]))/absolute[1])
        out['supplied_pixel_uncertainty']=iv is not None
        out['n_gaps_gt_50A']=int((np.diff(cw)>50).sum())
        clipped=c.xyz_to_metrics(coeff.T@np.maximum(cf,0))
        out['invalid_negative_clipping_uv_shift']=float(np.hypot(clipped['u1960']-baseline['u1960'],clipped['v1960']-baseline['v1960']))
        out['negative_clipping_note']='Diagnostic of an invalid noise treatment only; signed flux retained in all measurements.'
    except Exception as exc:
        out['recompute_status']='error';out['error']=str(exc)
    return out


def recompute():
    tab=pd.read_csv(OUT/'record_audit.csv.gz',dtype={'source_id':'string'},low_memory=False)
    selected=tab[is_true(tab.review_required)&tab.kind.isin(['SDSS','DESI','Gaia_XP'])]
    frozen=inputs();items=[(int(i),*frozen[int(i)]) for i in selected.row_index]
    results=[]
    with ProcessPoolExecutor(max_workers=4) as pool:
        for j,result in enumerate(pool.map(recompute_one,items,chunksize=4),1):
            results.append(result)
            if j%100==0:print('Recomputed',j,'/',len(items),flush=True)
    result=pd.DataFrame(results)
    old=tab.set_index('row_index')
    result['frozen_to_recomputed_uv']=np.hypot(
        result.recomputed_u1960-pd.Series(result.row_index.map(old.u1960)),
        result.recomputed_v1960-pd.Series(result.row_index.map(old.v1960)))
    result.to_csv(OUT/'recomputed_review_records.csv.gz',index=False,compression={'method':'gzip','mtime':0})
    summary=dict(created_utc=utc(),requested=len(result),status_counts=result.recompute_status.value_counts().to_dict(),
        max_frozen_to_recomputed_uv=float(result.frozen_to_recomputed_uv.max()),
        sky_mask_shift_gt_0002=int(result.raw_sky_mask_uv_shift.gt(.002).sum()),
        invalid_clipping_shift_gt_0002=int(result.invalid_negative_clipping_uv_shift.gt(.002).sum()),
        negative_Y_fraction_gt_001=int(result.negative_CIE_Y_absolute_fraction.gt(.01).sum()))
    (OUT/'recompute_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=['census','fetch','recompute'])
    args=p.parse_args()
    globals()[args.action]()
