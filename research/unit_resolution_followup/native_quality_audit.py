#!/usr/bin/env python3
"""Separate unit identity from support and noise in the same original SDSS data.

The displayed MWDD expression often omits IVAR. A strict flux match enables a
quality audit using the corresponding native errors and masks, without making
it an additional independent observation or changing frozen screen counts.
"""
from __future__ import annotations
import json
import hashlib
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(OUT))
import numpy as np
import pandas as pd
import colour_pipeline as c
from compact_inputs import CompactInputs

SKY_WINDOWS_A=[(5577.34,8),(5890,6),(5896,6),(6300.30,8),(6363.78,8)]
GRID_TOLERANCE_A=.02
COLOUR_FIELDS=['x','y','u1960','v1960','r_linear','g_linear','b_linear','r','g','b',
    'hex','in_srgb_gamut','green_dominant','green_channel_margin','duv','distance_planck_uv',
    'nearest_planck_temperature_K','nearest_planck_u','nearest_planck_v','nearest_is_RJ_limit',
    'u1960_stat_error','v1960_stat_error','uv_stat_error_max']


def corresponding_native_pixels(mwdd,reference):
    """Only use native pixels that have a finite export sample within 0.02 A.

    Unit evidence covers 3600--8300 A. Outside that window no new support
    assertion is made. Negative flux is finite evidence and remains included.
    """
    w=reference['wave'];mw=mwdd['wave']
    if np.any(np.diff(mw)<=0):raise ValueError('Non-increasing MWDD wavelengths')
    index=np.searchsorted(mw,w).clip(1,len(mw)-1)
    index=np.where(abs(mw[index-1]-w)<abs(mw[index]-w),index-1,index)
    visible=(w>=3600)&(w<=8300)
    keep=visible&np.isfinite(mwdd['flux'][index])&(abs(mw[index]-w)<=GRID_TOLERANCE_A)
    return keep,{'native_visible_samples':int(visible.sum()),
        'native_visible_samples_with_export_correspondence':int(keep.sum()),
        'native_visible_samples_without_export_correspondence':int((visible&~keep).sum()),
        'max_native_to_export_wavelength_difference_A':float(abs(mw[index][keep]-w[keep]).max())}


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def compute(root=ROOT):
    root=Path(root);folder=root/'research/unit_resolution_followup'
    store=CompactInputs(root)
    overlay=json.loads((folder/'overlay_registry.json').read_text())
    table=pd.read_csv(folder/'newly_resolved_record_screen.csv.gz',dtype={'source_id':'string'},low_memory=False).set_index('row_index')
    results=[]
    for entry in overlay['records']:
        i=entry['mwdd_row_index'];baseline=table.loc[i]
        ref=store.load(entry['external_reference_id']);w,f,iv=ref['wave'],ref['flux'],ref['ivar']
        corresponding,correspondence=corresponding_native_pixels(store.load('mwdd_'+str(i)),ref)
        scale=entry['selected_identity_evidence'][entry['convention']+'_constant_scale']
        factor=np.full_like(w,scale)
        if baseline.calibrated:
            factor*=10**(-.4*(baseline.cal_offset_mag+baseline.cal_tilt_mag_per_1000A*(w-6200)/1000))
        f=f*factor;iv=iv/factor**2
        for mode,keep in [('native_positive_ivar',corresponding),
                          ('native_positive_ivar_AND_zero',corresponding&(ref['and_mask']==0))]:
            row={'row_index':i,'entity_id':entry['entity_id'],'source_id':entry['source_id'],
                'mode':mode,'external_reference_id':entry['external_reference_id'],
                'same_original_observation':True,'original_mwdd_sha256':entry['mwdd_sha256'],
                'direct_original_sha256':entry['direct_sha256'],'same_existing_calibration':bool(baseline.calibrated),
                'baseline_recipe_eligible':bool(baseline.usable_screen),'baseline_recipe_duv':baseline.duv,
                'baseline_green_dominant':bool(baseline.green_dominant) if pd.notna(baseline.green_dominant) else False,
                'baseline_largest_gap_A':baseline.largest_visible_gap_A,'constant_representation_scale':scale,
                'native_reference_snr':baseline.reference_native_median_pixel_snr,
                'support_mask_policy':'finite native IVAR > 0; 3600-8300 A corresponding pixels; fixed narrow sky windows'+
                    ('; AND mask == 0 sensitivity' if mode.endswith('AND_zero') else '; no blanket AND/OR rejection'),
                **correspondence}
            try:
                metrics=c.integrate_colour(w[keep],f[keep],iv[keep],mask_sky=True)
                gate=bool(metrics['coverage_eligible'] and metrics['cmf_min_coverage']>.995 and metrics['largest_visible_gap_A']<150)
                row.update(metrics,status='ok',same_numeric_coverage_gate=gate)
                row['delta_uv_from_MWDD_recipe']=float(np.hypot(metrics['u1960']-baseline.u1960,metrics['v1960']-baseline.v1960))
            except Exception as exc:
                row.update(status='error',same_numeric_coverage_gate=False,error=str(exc))
            results.append(row)
    return pd.DataFrame(results)


def main():
    results=compute();results.to_csv(OUT/'native_quality_metrics.csv.gz',index=False,compression={'method':'gzip','mtime':0})
    before=results[results['mode'].eq('native_positive_ivar')]
    after=results[results['mode'].eq('native_positive_ivar_AND_zero')]
    comparable=before.baseline_recipe_eligible.eq(True)
    failed=before[comparable&~before.same_numeric_coverage_gate.eq(True)]
    changed=before[comparable&before.same_numeric_coverage_gate.eq(True)&before.delta_uv_from_MWDD_recipe.ge(.001)]
    summary={'newly_resolved_records':before.row_index.nunique(),
        'baseline_recipe_eligible':int(comparable.sum()),
        'native_IVAR_support_gate_pass':int(before.same_numeric_coverage_gate.eq(True).sum()),
        'baseline_eligible_but_native_IVAR_support_gate_fails':len(failed),
        'failed_native_support_row_indices':failed.row_index.astype(int).tolist(),
        'native_IVAR_supported_colour_change_ge_0p001':len(changed),
        'colour_change_ge_0p001_row_indices':changed.row_index.astype(int).tolist(),
        'native_IVAR_AND_zero_support_gate_pass':int(after.same_numeric_coverage_gate.eq(True).sum()),
        'all_native_visible_samples_correspond_to_finite_MWDD_pixels':bool(before.native_visible_samples_without_export_correspondence.eq(0).all()),
        'native_pixel_correspondence_tolerance_A':GRID_TOLERANCE_A,
        'default_sky_mask_windows_A':SKY_WINDOWS_A,
        'baseline_green_records':int((comparable&before.baseline_green_dominant.eq(True)).sum()),
        'native_IVAR_support_pass_green_records':int((before.same_numeric_coverage_gate.eq(True)&before.green_dominant.eq(True)).sum()),
        'interpretation':'A numerical support/error audit of the same observation, not new independent spectra. Positive native IVAR is required for usable original SDSS pixels. Removing all AND flags is an additional stated sensitivity test and is not assumed to be a universal recommended flag policy.',
        'scope_limits':'The frozen/current recipe counts are retained for comparability. This audit is a separate layer for only the 613 newly resolved MWDD SDSS inputs. It does not certify S/N, calibration, atmospheric interpretation, Gaia association or the quality of all other records.',
        'statistical_error_limits':'Analytic pixel errors assume diagonal covariance; calibration, resampling covariance and target-centering uncertainty are absent.',
        'input_sha256':{str(p.relative_to(ROOT)):sha(p) for p in [OUT/'overlay_registry.json',OUT/'compact_manifest.json',OUT/'newly_resolved_record_screen.csv.gz']},
        'output_sha256':sha(OUT/'native_quality_metrics.csv.gz')}
    (OUT/'native_quality_summary.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
