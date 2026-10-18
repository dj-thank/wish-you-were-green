#!/usr/bin/env python3
"""Create an explicitly unit-aware screen, preserving the historical rows.

Every SDSS record is evaluated with the current input guard. For other
instruments, the frozen numerical results are reused because their F_lambda
math is unchanged; that origin is recorded rather than called a recomputation.
Unresolved units are retained as rows with no current physical colour.
"""
from __future__ import annotations
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
os.environ.setdefault('OMP_NUM_THREADS','1')
os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'mpl-cache'))
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import colour_pipeline as c
from flux_conventions import resolve_flux_convention
from rank_candidates import annotate
from research.outlier_audit.audit import inputs

OUT=Path(__file__).resolve().parent

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def evaluate(task):
    i,rec=task
    row=c.analyze_record(rec)
    row.update(row_index=i,result_origin='recomputed_from_verified_SDSS_archive_bytes')
    return row

def build():
    records=inputs()
    path=ROOT/'results/all_spectra_screen.csv.gz'
    old=pd.read_csv(path,dtype={'source_id':'string'},low_memory=False)
    census=pd.read_csv(ROOT/'research/outlier_audit/record_audit.csv.gz',dtype={'source_id':'string'},low_memory=False)
    jobs=[(i,r) for i,(o,r) in enumerate(records) if r['kind']=='SDSS']
    updated={}
    with ProcessPoolExecutor(max_workers=4) as pool:
        for n,row in enumerate(pool.map(evaluate,jobs,chunksize=8),1):
            updated[row['row_index']]=row
            if n%400==0:print('SDSS evaluated',n,'/',len(jobs),flush=True)
    rows=[]
    for i,(origin,rec) in enumerate(records):
        previous=old.iloc[i].to_dict()
        if i in updated:
            row=updated[i]
        else:
            row={**previous,**resolve_flux_convention(rec),'row_index':i,
                'result_origin':'frozen_result_reused_under_unchanged_Flambda_math'}
            if not row['flux_units_validated']:
                row['status']='unit_unverified'
        row.update(archive_origin=rec.get('archive_origin','MWDD'),entity_id=census.iloc[i].entity_id,
            identity_basis=census.iloc[i].identity_basis,record_id=census.iloc[i].record_id,
            legacy_usable_screen=bool(previous['usable_screen']))
        for k in ['status','hex','u1960','v1960','duv','distance_planck_uv','raw_hex','raw_duv','calibrated']:
            row['legacy_'+k]=previous.get(k)
        if not row['flux_units_validated']:
            # Numerical historical values remain named legacy_*. Unknown
            # conventions cannot appear as current physical chromaticities.
            colour_keys=['x','y','u1960','v1960','duv','distance_planck_uv','hex',
                'r_linear','g_linear','b_linear','r','g','b','in_srgb_gamut','green_dominant','green_channel_margin',
                'nearest_planck_temperature_K','nearest_planck_u','nearest_planck_v','nearest_is_RJ_limit',
                'u1960_stat_error','v1960_stat_error','uv_stat_error_max','uv_tilt_stress_max']
            dependent=colour_keys+[k for k in row if (k.startswith('raw_') and k not in ('raw_path','raw_sha256')) or k.startswith('cal_')]
            for k in set(dependent):
                if k in row:
                    row.setdefault('legacy_'+k,row[k])
                    row[k]=None
            row['calibrated']=False
        rows.append(row)
    table=annotate(pd.DataFrame(rows))
    table['current_minus_legacy_uv']=np.hypot(table.u1960-table.legacy_u1960,table.v1960-table.legacy_v1960)
    table.to_csv(OUT/'corrected_record_screen.csv.gz',index=False,compression={'method':'gzip','mtime':0})
    entities=[]
    for key,g in table.groupby('entity_id',sort=True):
        good=g[g.usable_screen.eq(True)&g.status.eq('ok')]
        q={'entity_id':key,'source_id':next((x for x in g.source_id if pd.notna(x)),''),
           'names':' | '.join(sorted(set(g.wdid.dropna().astype(str)))),
           'records':len(g),'current_eligible_records':len(good),
           'unit_unverified_records':int(g.status.eq('unit_unverified').sum()),
           'converted_fnu_records':int(g.flux_conversion_applied.eq(True).sum()),
           'legacy_eligible_records':int(g.legacy_usable_screen.sum()),
           'current_instruments':'|'.join(sorted(good.kind.unique())),
           'legacy_strong_records':int((g.legacy_usable_screen&g.legacy_duv.abs().ge(.01)).sum()),
           'current_strong_records':int(good.distance_planck_uv.ge(.01).sum()),
           'known_hollands_colour':bool(g.known_hollands_colour.any()),
           'identity_caution':bool(g.identity_basis.str.contains('positional').any())}
        if len(good):
            good=good.copy();good['_preference']=good.kind.map({'DESI':0,'SDSS':1,'Gaia_XP':2})
            best=good.sort_values(['calibrated','_preference','visible_median_pixel_snr','record_id'],
                ascending=[False,True,False,True],na_position='last').iloc[0]
            q.update(max_current_distance=float(good.distance_planck_uv.max()),min_current_distance=float(good.distance_planck_uv.min()),
                representative_row_index=int(best.row_index),representative_hex=best.hex,representative_duv=float(best.duv))
        entities.append(q)
    objects=pd.DataFrame(entities);objects.to_csv(OUT/'corrected_object_screen.csv',index=False)
    converted=table[table.flux_conversion_applied.eq(True)]
    summary={'frozen_baseline_sha256':sha(path),'unit_registry_sha256':sha(ROOT/'research/precision/flux_convention_evidence.json'),
        'total_records':len(table),'catalogue_entity_keys':len(objects),'SDSS_records_recomputed':len(jobs),
        'non_SDSS_results_reused_or_withheld':len(table)-len(jobs),
        'current_status_counts':table.status.value_counts().to_dict(),
        'current_eligible_records':int(table.usable_screen.sum()),'legacy_eligible_records':int(old.usable_screen.sum()),
        'current_strong_records':int((table.usable_screen&table.distance_planck_uv.ge(.01)).sum()),
        'current_strong_entity_keys':int(objects.current_strong_records.gt(0).sum()),
        'legacy_strong_entity_keys':int(objects.legacy_strong_records.gt(0).sum()),
        'converted_fnu_records':len(converted),'converted_colour_shift_median_uv':float(converted.current_minus_legacy_uv.median()),
        'converted_colour_shift_max_uv':float(converted.current_minus_legacy_uv.max()),
        'converted_raw_duv_shift_max':float((converted.raw_duv-converted.legacy_raw_duv).abs().max()),
        'new_strong_entity_keys_from_conversion':int(((objects.current_strong_records>0)&(objects.legacy_strong_records==0)&(objects.converted_fnu_records>0)).sum()),
        'interpretation':'Updated eligibility is a source-convention correction, not a discovery significance or uniform-quality sample. Exact Gaia keys and legacy positional assignments are retained and flagged.',
        'unsupported_units':'Unresolved MWDD SDSS and other unverified archive formats are retained, but current physical colours are blank and excluded. Withholding does not imply that all such spectra are F_nu.',
        'principal_yellow_update':'J1323-0129 MWDD SDSS row13 has unresolved units and no direct reference in this dataset. Its independent-SDSS corroboration is withdrawn; DESI colour estimate remains.'}
    (OUT/'corrected_screen_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    current=table[table.usable_screen]
    fig,axes=plt.subplots(1,2,figsize=(12,5.1),layout='constrained')
    original=old[old.usable_screen]
    axes[0].scatter(original.u1960,original.v1960,s=8,c='#87919b',alpha=.35,edgecolors='none')
    axes[0].set_title(f'Historical screen: {len(original):,} eligible records\nIncludes unresolved/mixed MWDD SDSS flux conventions',fontsize=11)
    palette={'DESI':'#277fa5','Gaia_XP':'#bb7432','SDSS':'#8664a0'}
    for kind,g in current.groupby('kind'):
        axes[1].scatter(g.u1960,g.v1960,s=8,alpha=.4,edgecolors='none',color=palette[kind],label=f'{kind} ({len(g):,})')
    axes[1].set_title(f'Unit-aware screen: {len(current):,} eligible records\nFν converted only with native-pixel evidence',fontsize=11)
    for ax in axes:
        locus=c._BB_UV[c._BB_T>=2300];ax.plot(locus[:,0],locus[:,1],c='#1f303d',lw=1.1)
        ax.set(xlim=(.14,max(.315,float(current.u1960.max())+.005)),ylim=(.247,max(.367,float(current.v1960.max())+.005)),xlabel='CIE 1960 u',ylabel='CIE 1960 v')
        ax.set_aspect('equal',adjustable='box');ax.grid(alpha=.13)
    axes[1].legend(fontsize=8,loc='lower right')
    fig.suptitle('Correcting flux conventions changes the evidence admitted to the colour plane',fontsize=13)
    fig.savefig(OUT/'corrected_colour_plane.png',dpi=190);fig.savefig(OUT/'corrected_colour_plane.svg');plt.close(fig)
    print(json.dumps(summary,indent=2))

if __name__=='__main__':build()
