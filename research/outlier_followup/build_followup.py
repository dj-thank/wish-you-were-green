#!/usr/bin/env python3
"""Complete the bounded, previously unviewed historical review queue.

Only current eligible, unit-validated F_lambda spectra are plotted. Every
historical record remains in the ledger, including unavailable spectra.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
from datetime import datetime, timezone
import gzip
import hashlib
import io
import json
import math
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
os.environ.setdefault('OMP_NUM_THREADS','1')
os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'mpl-cache'))
import numpy as np
import pandas as pd
from project_io import load_json


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def utc():
    return datetime.now(timezone.utc).isoformat()


def relative(value):
    marker='wd-colour-research/'
    return ROOT/(str(value).split(marker,1)[1] if marker in str(value) else str(value))


def frozen_inputs():
    return [(origin,r) for origin in ['mwdd','sdss']
            for r in load_json(ROOT/f'results/screen_input_{origin}.json')]


def census():
    historical=ROOT/'research/outlier_audit/review_queue.csv'
    prior=ROOT/'research/outlier_audit/contact_sheet_index.csv'
    corrected=ROOT/'research/precision/flux_units/corrected_record_screen.csv.gz'
    h=pd.read_csv(historical,dtype={'source_id':'string'})
    seen=pd.read_csv(prior,dtype={'source_id':'string'})
    objects=pd.read_csv(ROOT/'research/outlier_audit/object_review.csv',dtype={'source_id':'string'})
    keys=set(h.entity_id)-set(seen.entity_id)
    queue=objects[objects.entity_id.isin(keys)].sort_values('entity_id').copy()
    queue.insert(0,'followup_index',np.arange(len(queue)))
    current=pd.read_csv(corrected,dtype={'source_id':'string'},low_memory=False)
    records=current[current.entity_id.isin(keys)].copy()
    inputs=frozen_inputs()
    for r in records.itertuples():
        original=inputs[r.row_index][1]
        assert r.sha256==original['sha256'] and r.source_url==original['source_url']
    eligible=(records.usable_screen.eq(True)&records.status.eq('ok')&
              records.flux_units_validated.eq(True)&np.isfinite(records.u1960)&np.isfinite(records.v1960))
    records['eligible_for_plot']=eligible
    records['initial_disposition']=np.where(eligible,'eligible_exact_raw_retrieval_required',
        np.where(records.status.eq('unit_unverified'),'withheld_unverified_flux_units',
        np.where(records.status.eq('error'),'withheld_processing_error','withheld_current_eligibility_gate')))
    columns=['row_index','entity_id','source_id','wdid','kind','archive_origin','source_url','sha256',
        'raw_path','parsed_path','record_id','identity_basis','status','usable_screen','eligible_for_plot',
        'initial_disposition','flux_units_validated','flux_input_convention','flux_conversion_applied',
        'flux_unit_evidence','calibrated','cal_system','cal_offset_mag','cal_tilt_mag_per_1000A',
        'cal_max_residual_mag','u1960','v1960','duv','distance_planck_uv','hex',
        'visible_median_pixel_snr','largest_visible_gap_A','visible_negative_fraction','error']
    records=records[[k for k in columns if k in records]].sort_values('row_index')
    OUT.mkdir(parents=True,exist_ok=True)
    queue.to_csv(OUT/'queue_entities.csv',index=False,float_format='%.17g')
    records.to_csv(OUT/'queue_records.csv.gz',index=False,float_format='%.17g',compression={'method':'gzip','mtime':0})
    jobs=[]
    for digest,g in records[eligible].groupby('sha256'):
        i=int(g.row_index.iloc[0]);origin,rec=inputs[i]
        raw=relative(rec['raw_path'])
        cached=raw.is_file() and sha(raw)==digest
        jobs.append({'row_index':i,'row_indices':[int(x) for x in g.row_index],
                     'origin':origin,'source_url':rec['source_url'],'sha256':digest,
                     'cached_raw_verified':cached,'raw_path':str(raw.relative_to(ROOT))})
    plan={'created_utc':utc(),'historical_queue_entities':len(h),'previously_reviewed_entities':len(seen),
        'new_entities':len(queue),'all_records':len(records),'eligible_records':int(eligible.sum()),
        'eligible_entity_keys':int(records.loc[eligible,'entity_id'].nunique()),
        'unique_raw_inputs':len(jobs),'cached_exact_raw_inputs':sum(x['cached_raw_verified'] for x in jobs),
        'new_raw_inputs_needed':sum(not x['cached_raw_verified'] for x in jobs),
        'eligible_by_instrument':records[eligible].kind.value_counts().to_dict(),
        'dispositions':records.initial_disposition.value_counts().to_dict(),
        'input_sha256':{str(p.relative_to(ROOT)):sha(p) for p in [historical,prior,corrected]},
        'selection':'Exact set difference: historical review_queue.entity_id minus all 337 prior contact_sheet_index.entity_id.',
        'jobs':jobs}
    (OUT/'retrieval_plan.json').write_text(json.dumps(plan,indent=2)+'\n')
    print(json.dumps({k:v for k,v in plan.items() if k!='jobs'},indent=2),flush=True)
    return queue,records,plan


def fetch(workers=4):
    from download_frozen_spectra import acquire
    _,_,plan=census()
    inputs=frozen_inputs()
    def one(job):
        item=inputs[job['row_index']]
        for attempt in range(2):
            try:
                r=acquire(item)
                return {**job,'status':'verified','raw_size_bytes':relative(item[1]['raw_path']).stat().st_size,
                        'checked_utc':utc(),'attempts':attempt+1}
            except Exception as exc:error=str(exc)
        return {**job,'status':'retrieval_failed','error':error,'checked_utc':utc(),'attempts':2}
    results=[]
    with (OUT/'retrieval.jsonl').open('w') as stream,ThreadPoolExecutor(max_workers=workers) as pool:
        for n,future in enumerate(as_completed([pool.submit(one,j) for j in plan['jobs']]),1):
            r=future.result();results.append(r);stream.write(json.dumps(r)+'\n');stream.flush()
            if n%100==0 or r['status']!='verified':print('Retrieved',n,'/',len(plan['jobs']),'failed',sum(x['status']!='verified' for x in results),flush=True)
    summary={'created_utc':utc(),'requested_unique_inputs':len(results),
        'verified':sum(r['status']=='verified' for r in results),'failed':sum(r['status']!='verified' for r in results),
        'verified_raw_bytes':sum(r.get('raw_size_bytes',0) for r in results),
        'concurrency':workers,'unverified_flux_units_downloaded':0,
        'raw_data_location':'Existing ignored survey cache; source URLs and exact SHA256 retained in retrieval_plan.json.'}
    (OUT/'retrieval_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2),flush=True)


def verified_arrays(item):
    """Parse original bytes again, never trust an unrelated cached derivative."""
    origin,rec=item
    path=relative(rec['raw_path'])
    data=path.read_bytes()
    if hashlib.sha256(data).hexdigest()!=rec['sha256']:
        raise ValueError('Original raw SHA256 mismatch')
    if origin=='mwdd':
        lines=data.decode('utf-8','replace').splitlines()
        names=[x.strip() for x in next(csv.reader([lines[1]]))]
        array=np.loadtxt(io.StringIO('\n'.join(lines[2:])),delimiter=',',ndmin=2)
        values={k:array[:,j] for j,k in enumerate(names)}
        w=values['wavelength'];f=values['flux'];iv=None
        if 'sigma' in values:
            s=values['sigma'];iv=np.divide(1,s*s,out=np.zeros_like(s),where=np.isfinite(s)&(s>0))
        elif 'ivar' in values:iv=values['ivar']
    else:
        from astropy.io import fits
        with fits.open(io.BytesIO(data)) as hd:
            a=hd[1].data
            w=10**np.asarray(a['loglam'],float)
            f=np.asarray(a['flux'],float)*1e-17
            iv=np.asarray(a['ivar'],float)/1e-34
    from flux_conventions import as_flux_lambda
    f,iv,meta=as_flux_lambda(w,f,iv,rec)
    return w,f,iv,meta


def spectrum_for_panel(item,row):
    import colour_pipeline as c
    w,f,iv,meta=verified_arrays(item)
    if meta['flux_input_convention']!=row.flux_input_convention:
        raise ValueError('Current registry convention differs from the corrected snapshot')
    if row.calibrated is True or row.calibrated==True:
        a=float(row.cal_offset_mag);b=float(row.cal_tilt_mag_per_1000A)
        if not np.isfinite(a+b):raise ValueError('Current calibration parameters are unavailable')
        factor=10**(-.4*(a+b*(w-6200)/1000))
        f=f*factor
        if iv is not None:iv=iv/factor**2
    current=c.integrate_colour(w,f,iv,mask_sky=row.kind!='Gaia_XP')
    delta=float(np.hypot(current['u1960']-row.u1960,current['v1960']-row.v1960))
    if delta>1e-7:raise ValueError(f'Current colour reproduction mismatch: delta_uv={delta:.9g}')
    w,f,iv=c.clean_spectrum(w,f,iv,mask_sky=row.kind!='Gaia_XP')
    sel=(w>=3600)&(w<=8300);w,f=w[sel],f[sel]
    if iv is not None:iv=iv[sel]
    region=(w>=5200)&(w<=5500)
    norm=float(np.median(f[region])) if region.any() else np.nan
    normalizer='median_5200_5500_A'
    if not np.isfinite(norm) or norm<=0:
        region=(w>=4500)&(w<=7500)
        norm=float(np.median(f[region])) if region.any() else np.nan
        normalizer='fallback_median_4500_7500_A'
    if not np.isfinite(norm) or norm<=0:raise ValueError('No positive finite continuum normalizer')
    f=f/norm
    sigma=None if iv is None else 1/np.sqrt(iv)/norm
    edges=np.arange(3600,8320,20)
    centres=(edges[:-1]+edges[1:])/2/10
    mean=np.full(len(centres),np.nan);minimum=mean.copy();maximum=mean.copy();noise=mean.copy()
    # Include a pixel exactly at the closed 8300 A endpoint in the final bin.
    indices=np.minimum(np.digitize(w,edges)-1,len(centres)-1)
    for k in range(len(centres)):
        selected=indices==k
        if selected.any():
            v=f[selected];mean[k]=np.mean(v);minimum[k]=np.min(v);maximum[k]=np.max(v)
            if sigma is not None:noise[k]=np.sqrt(np.sum(sigma[selected]**2))/selected.sum()
    diagnostics={'row_index':int(row.row_index),'plot_status':'plotted_verified_flambda',
        'current_recomputed_delta_uv':delta,'normalizer':normalizer,'normalizer_flam':norm,
        'plotted_native_pixels':len(w),'native_negative_fraction':float(np.mean(f<0)),
        'native_normalized_min':float(np.min(f)),'native_normalized_max':float(np.max(f)),
        'supplied_pixel_uncertainty':iv is not None,'display_bin_A':20,
        'display_error_model':'independent-pixel standard error of bin mean; covariance and calibration uncertainty omitted' if iv is not None else 'not supplied; no uncertainty band inferred',
        'unit_conversion_applied':meta['flux_conversion_applied']}
    return (centres,mean,minimum,maximum,noise),diagnostics


def generate():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.ticker import MaxNLocator
    queue=pd.read_csv(OUT/'queue_entities.csv',dtype={'source_id':'string'})
    records=pd.read_csv(OUT/'queue_records.csv.gz',dtype={'source_id':'string'},low_memory=False)
    plan=json.loads((OUT/'retrieval_plan.json').read_text())
    for file,digest in plan['input_sha256'].items():
        if sha(ROOT/file)!=digest:raise ValueError('A pinned review input changed: '+file)
    current=pd.read_csv(ROOT/'research/precision/flux_units/corrected_record_screen.csv.gz',dtype={'source_id':'string'},low_memory=False)
    # Preserve the exact reasons for a current eligibility failure as well as
    # every input row, including rows which deliberately are not downloaded.
    additional=['coverage_eligible','cmf_min_coverage','wave_min_A','wave_max_A','ra_deg','dec_deg','error']
    for key in additional:
        if key in current and key not in records:
            records[key]=records.row_index.map(current.set_index('row_index')[key])
    inputs=frozen_inputs()
    groups={key:g for key,g in records.groupby('entity_id',sort=False)}
    folder=OUT/'spectrum_contact_sheets';folder.mkdir(exist_ok=True)
    entries=[];diagnostics=[];page_meta=[]
    total_pages=math.ceil(len(queue)/16)
    colours={'DESI':'#166b8c','SDSS':'#9252a0','Gaia_XP':'#c47919'}
    short={'DESI':'D','SDSS':'S','Gaia_XP':'XP'}
    plt.rcParams.update({'font.size':8,'axes.titlesize':8,'axes.labelsize':8,'xtick.labelsize':7,'ytick.labelsize':7})
    for page in range(total_pages):
        block=queue.iloc[page*16:(page+1)*16]
        fig,axes=plt.subplots(4,4,figsize=(20,15),layout='constrained')
        block_entries=[]
        for panel,(ax,obj) in enumerate(zip(axes.flat,block.itertuples()),1):
            group=groups[obj.entity_id]
            eligible=group[group.eligible_for_plot.eq(True)].sort_values(['kind','archive_origin','row_index'])
            unit_withheld=group.status.eq('unit_unverified').sum()
            other_withheld=len(group)-len(eligible)-unit_withheld
            plotted=[];failed=[];extent=[0.,1.]
            for number,row in enumerate(eligible.itertuples()):
                try:
                    bins,diag=spectrum_for_panel(inputs[row.row_index],row)
                    wave,mean,low,high,error=bins
                    color=colours[row.kind]
                    linestyle='--' if row.archive_origin=='SDSS_DR17_direct' else '-'
                    label=f'{short[row.kind]}:{row.row_index}'+(' cal' if row.calibrated==True else ' raw')
                    if diag['unit_conversion_applied']:label+=' nu->lambda'
                    if not diag['supplied_pixel_uncertainty']:label+=' no sigma'
                    ax.vlines(wave,low,high,color=color,alpha=.18,lw=.5)
                    ax.plot(wave,mean,color=color,lw=.8,ls=linestyle,label=label)
                    if np.isfinite(error).any():
                        ax.fill_between(wave,mean-error,mean+error,color=color,alpha=.12,lw=0)
                    for values in [low,high,mean-error,mean+error]:
                        if np.isfinite(values).any():extent.extend([float(np.nanmin(values)),float(np.nanmax(values))])
                    plotted.append(int(row.row_index));diagnostics.append(diag)
                except Exception as exc:
                    failed.append(int(row.row_index))
                    diagnostics.append({'row_index':int(row.row_index),'plot_status':'unavailable_current_spectrum','plot_error':str(exc)})
            for row in group[~group.eligible_for_plot.eq(True)].itertuples():
                diagnostics.append({'row_index':int(row.row_index),'plot_status':row.initial_disposition})
            label=str(obj.source_id) if pd.notna(obj.source_id) else str(obj.names)[:28]
            distance=f'{obj.current_max_distance:.4f}' if pd.notna(obj.current_max_distance) else 'unavailable'
            ax.set_title(f'{int(obj.followup_index)+1:04d}  {label}\nd={distance}; {str(obj.spectral_types)[:28]}',fontsize=9)
            if plotted:
                lo,hi=min(extent),max(extent);margin=max((hi-lo)*.06,.08)
                ax.set(xlim=(360,830),ylim=(lo-margin,hi+margin))
                ax.axhline(0,color='#888888',lw=.45)
                ax.legend(fontsize=6.5,loc='upper right',framealpha=.8)
                ax.grid(alpha=.13)
                ax.xaxis.set_major_locator(MaxNLocator(5));ax.yaxis.set_major_locator(MaxNLocator(5))
                if unit_withheld or other_withheld or failed:
                    ax.text(.02,.025,f'Not drawn: units {unit_withheld}; gates {other_withheld}; raw/recheck {len(failed)}',transform=ax.transAxes,fontsize=6.5,bbox={'facecolor':'white','edgecolor':'none','alpha':.85})
            else:
                ax.set(xlim=(360,830),ylim=(0,1));ax.set_yticks([])
                reason=f'No current eligible F-lambda curve\nUnits unresolved: {unit_withheld}; other gates: {other_withheld}\nRaw/recheck unavailable: {len(failed)}\nRows: '+', '.join(map(str,group.row_index))
                ax.text(.5,.5,reason,ha='center',va='center',transform=ax.transAxes,fontsize=9)
            ax.set_xlabel('Wavelength (nm)')
            ax.set_ylabel('Relative F-lambda')
            block_entries.append({'followup_index':int(obj.followup_index),'page':page+1,'panel':panel,
                'entity_id':obj.entity_id,'source_id':obj.source_id,'names':obj.names,
                'all_row_indices':'|'.join(map(str,group.row_index)),
                'plotted_row_indices':'|'.join(map(str,plotted)),
                'unavailable_eligible_row_indices':'|'.join(map(str,failed)),
                'all_records':len(group),'eligible_records':len(eligible),'plotted_records':len(plotted),
                'unit_withheld_records':int(unit_withheld),'other_withheld_records':int(other_withheld),
                'current_max_distance':obj.current_max_distance,
                'current_between_records_uv':obj.current_between_records_uv,
                'current_instrument_kinds':obj.current_instrument_kinds,
                'historical_review_reasons':obj.review_reasons,'current_assessment':obj.assessment,
                'contact_sheet':f'spectrum_contact_sheets/page_{page+1:03d}.png',
                'review_state':'awaiting_individual_visual_review'})
        for ax in axes.flat[len(block):]:ax.axis('off')
        fig.suptitle(f'Remaining historical review queue — current verified F-lambda, page {page+1}/{total_pages}\n20 A mean lines; vertical strokes retain native min/max; shading = supplied independent-pixel error only. Stored accepted calibration applied; normalized near 5350 A. All y extrema shown.',fontsize=12)
        path=folder/f'page_{page+1:03d}.png'
        fig.savefig(path,dpi=120)
        plt.close(fig)
        digest=sha(path)
        for entry in block_entries:entry['contact_sheet_sha256']=digest
        entries.extend(block_entries)
        page_meta.append({'page':page+1,'path':str(path.relative_to(OUT)),'sha256':digest,
                          'entity_count':len(block),'first_followup_index':int(block.followup_index.iloc[0]),
                          'last_followup_index':int(block.followup_index.iloc[-1]),
                          'review_assignment':'first_half' if page<63 else 'second_half'})
        pd.DataFrame(entries).to_csv(OUT/'contact_sheet_index.csv',index=False,float_format='%.17g')
        print('Generated page',page+1,'/',total_pages,'records inspected',len(diagnostics),flush=True)
    details=pd.DataFrame(diagnostics)
    assert details.row_index.is_unique and set(details.row_index)==set(records.row_index)
    records=records.merge(details,on='row_index',validate='one_to_one')
    records.to_csv(OUT/'record_review.csv.gz',index=False,float_format='%.17g',compression={'method':'gzip','mtime':0})
    index=pd.DataFrame(entries)
    summary={'created_utc':utc(),'entities':len(queue),'records':len(records),'pages':len(page_meta),
        'plotted_records':int(records.plot_status.eq('plotted_verified_flambda').sum()),
        'entities_with_plotted_spectra':int(index.plotted_records.gt(0).sum()),
        'plot_status_counts':records.plot_status.value_counts().to_dict(),
        'largest_reproduction_uv_difference':float(records.current_recomputed_delta_uv.max()),
        'binning':'20 Angstrom arithmetic means for display only; numerical colours use unbinned signed pixels.',
        'pixel_range':'Every cleaned native visible flux pixel lies inside its displayed bin min/max stroke and vertical plot limits.',
        'uncertainty':'Supplied independent-pixel error only. Gaia XP export covariance, calibration uncertainty and shared observation dependence are not reconstructed here.',
        'input_sha256':plan['input_sha256'],'pages_manifest':page_meta}
    (OUT/'generation_manifest.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps({k:v for k,v in summary.items() if k!='pages_manifest'},indent=2),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['census','fetch','generate'])
    parser.add_argument('--workers',type=int,choices=range(1,5),default=4)
    args=parser.parse_args()
    if args.command=='census':census()
    elif args.command=='fetch':fetch(args.workers)
    else:generate()
