#!/usr/bin/env python3
"""Current numerical view using only explicit, independently replayable evidence.

No historical lookup, row, colour, figure, or reviewer note is overwritten.
The frozen 9902 row identities and 6003 entity keys stay fixed. Eligibility
follows the existing policy; source identity and native quality are distinct.
"""
from __future__ import annotations
import argparse
import base64
import gzip
import hashlib
import html
import json
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(OUT))
os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'mpl-cache'))
import numpy as np
import pandas as pd
import colour_pipeline as c
from rank_candidates import annotate
from compact_inputs import CompactInputs
from overlay import UnitOverlay,create


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def frozen():
    rows=[]
    for name in ['mwdd','sdss']:
        with gzip.open(ROOT/f'results/screen_input_{name}.json.gz','rt') as stream:rows.extend(json.load(stream))
    return rows


def analyze_arrays(record,raw,overlay):
    w=raw['wave'];f,iv,meta=overlay.as_flux_lambda(w,raw['flux'],raw['ivar'],record)
    row={k:record.get(k) for k in ['wdid','source_id','spectype','teff','ra_deg','dec_deg','kind','source_url','star_page_url','parsed_path','raw_path','sha256']}
    row.update(meta);row.update(calibrated=False,calibration_notes=None,error=None)
    try:
        m=c.integrate_colour(w,f,iv,mask_sky=True)
        row.update({'raw_'+k:v for k,v in m.items()});row.update(m)
        p=record.get('photometry',{});notes=[]
        def num(key):
            try:return float(p.get(key,np.nan))
            except (TypeError,ValueError):return np.nan
        for system,prefix,eprefix in [('sdss','s','Ds'),('panstarrs','PS_','DPS_')]:
            obs=[num(prefix+b) for b in 'gri'];err=[num(eprefix+b) for b in 'gri']
            if not all(np.isfinite(obs)):continue
            try:
                fc,cal=c.recalibrate_gri(w,f,obs,err,system)
                if cal['cal_max_residual_mag']>=.15 or abs(cal['cal_tilt_mag_per_1000A'])>=.25:
                    raise ValueError('Rejected calibration: residual >=0.15 mag or |tilt| >=0.25 mag/1000 A')
                corr=10**(-.4*(cal['cal_offset_mag']+cal['cal_tilt_mag_per_1000A']*(w-6200)/1000))
                ivc=None if iv is None else iv/corr**2
                mc=c.integrate_colour(w,fc,ivc,mask_sky=True)
                row.update(mc);row.update(cal);row['calibrated']=True
                uv0=np.array([mc['u1960'],mc['v1960']]);shifts=[]
                for shift in [-max(2*cal['cal_tilt_error'],.03),max(2*cal['cal_tilt_error'],.03)]:
                    stress=c.integrate_colour(w,fc*10**(-.4*shift*(w-6200)/1000),ivc,mask_sky=True)
                    shifts.append(float(np.hypot(stress['u1960']-uv0[0],stress['v1960']-uv0[1])))
                row['uv_tilt_stress_max']=max(shifts)
                break
            except Exception as exc:notes.append(system+': '+str(exc))
        row['calibration_notes']='; '.join(notes) if notes else None
        if iv is not None:
            keep=np.isfinite(iv)&(iv>0)&(w>4000)&(w<7500)
            row['visible_median_pixel_snr']=float(np.median(f[keep]*np.sqrt(iv[keep]))) if keep.any() else np.nan
        row['status']='ok'
    except Exception as exc:row.update(status='error',error=str(exc))
    return row


def native_quality(entry,raw,metadata):
    w,f,iv=raw['wave'],raw['flux'],raw['ivar']
    visible=(w>=3600)&(w<=8300)
    snrsel=(w>4000)&(w<7500)&np.isfinite(f)&np.isfinite(iv)&(iv>0)
    header=entry['selected_identity_evidence']['direct_fits_header']
    quality=metadata.get('hdu2_quality',{})
    result={'reference_native_visible_samples':int(visible.sum()),
        'reference_native_nonpositive_ivar_visible':int((visible&(iv<=0)).sum()),
        'reference_native_negative_fraction_visible':float((f[visible]<0).mean()),
        'reference_native_median_pixel_snr':float(np.median(f[snrsel]*np.sqrt(iv[snrsel]))) if snrsel.any() else np.nan,
        'reference_native_and_flag_fraction_visible':float((raw['and_mask'][visible]!=0).mean()),
        'reference_native_or_flag_fraction_visible':float((raw['or_mask'][visible]!=0).mean()),
        'reference_automatic_class':quality.get('CLASS'),'reference_automatic_zwarning':quality.get('ZWARNING'),
        'reference_observation_plate':header['PLATEID'],'reference_observation_mjd':header['MJD'],
        'reference_observation_fiber':header['FIBERID'],'reference_observation_run2d':header['RUN2D'],
        'reference_plug_ra_deg':header.get('PLUG_RA'),'reference_plug_dec_deg':header.get('PLUG_DEC'),
        'reference_cone_separation_arcsec':entry['selected_identity_evidence']['cone_distance_arcsec'],
        'astrophysical_association_status':'candidate_reference_position_only_not_epoch_validated',
        'flux_quality_status':'native_reference_quality_available_not_a_blanket_acceptance'}
    if entry['mwdd_row_index']==13:
        result.update(astrophysical_association_status='J1323_epoch_audit_fibre_offset_1.1383_arcsec',
            science_assessment='Positive-Duv qualitative SDSS/DESI support restored; precise corroboration held for low SNR, fibre centering and calibration uncertainty.')
    return result


def aggregate(tab):
    rows=[]
    for entity,g in tab.groupby('entity_id',sort=True):
        q=g[g.usable_screen.eq(True)&g.status.eq('ok')&g.flux_units_validated.eq(True)].copy()
        best=None
        if len(q):
            q['_kind_order']=q.kind.map({'DESI':0,'SDSS':1,'Gaia_XP':2}).fillna(9)
            best=q.sort_values(['calibrated','_kind_order','visible_median_pixel_snr','source_url'],ascending=[False,True,False,True],na_position='last').iloc[0]
        uv=q[['u1960','v1960']].to_numpy(float)
        spread=float(np.sqrt(((uv[:,None,:]-uv[None,:,:])**2).sum(axis=2)).max()) if len(q) else np.nan
        rows.append({'entity_id':entity,'source_id':str(g.source_id.dropna().iloc[0]) if g.source_id.notna().any() else None,
            'names':' | '.join(sorted(set(g.wdid.dropna().astype(str)))),'records':len(g),'record_rows':'|'.join(str(int(i)) for i in g.row_index),
            'eligible_records':len(q),'strong_records':int(q.distance_planck_uv.ge(.01).sum()),
            'eligible_instruments':'|'.join(sorted(set(q.kind))),'eligible_instrument_count':q.kind.nunique(),
            'newly_resolved_records':int(g.flux_unit_overlay_version.notna().sum()),
            'remaining_unit_unverified_records':int(g.status.eq('unit_unverified').sum()),
            'max_between_records_uv':spread,'calibrated_records':int(q.calibrated.eq(True).sum()),
            'representative_row_index':None if best is None else int(best.row_index),
            'representative_kind':None if best is None else best.kind,
            'representative_u1960':None if best is None else best.u1960,
            'representative_v1960':None if best is None else best.v1960,
            'representative_duv':None if best is None else best.duv,
            'representative_hex':None if best is None else best.hex,
            'assessment':('J1323: unit ambiguity resolved; qualitative SDSS/DESI positive-Duv support, with precision held for low SNR, fibre offset and calibration.' if entity=='gaia:3638333660492606976' else
                'No eligible current colour; retained for audit.' if not len(q) else
                'Descriptive current screen; unit identity alone does not establish clean association, calibration or novelty.')})
    return pd.DataFrame(rows)


def screen():
    create();overlay=UnitOverlay();store=CompactInputs();source=frozen()
    basepath=ROOT/'research/precision/flux_units/corrected_record_screen.csv.gz'
    base=pd.read_csv(basepath,dtype={'source_id':'string'},low_memory=False)
    assert len(base)==9902 and np.array_equal(base.row_index.to_numpy(),np.arange(9902))
    additions=[]
    for n,entry in enumerate(overlay.payload['records'],1):
        i=entry['mwdd_row_index'];original=source[i]
        raw=store.load('mwdd_'+str(i));new=analyze_arrays(original,raw,overlay)
        new.update(row_index=i,entity_id=entry['entity_id'],record_id=base.iloc[i].record_id,
            result_origin='new_unit_resolution_overlay_2026-10-19',archive_origin=base.iloc[i].archive_origin,
            previous_current_status=base.iloc[i].status,previous_current_usable_screen=bool(base.iloc[i].usable_screen),
            previously_unavailable_panel=entry['previously_unavailable_panel'])
        new.update(native_quality(entry,store.load(entry['external_reference_id']),store.entries[entry['external_reference_id']]))
        additions.append(new)
        if n%50==0:print('new current rows',n,'/',len(overlay.payload['records']),flush=True)
    changed=annotate(pd.DataFrame(additions))
    rows=base.to_dict('records')
    for row in changed.to_dict('records'):
        i=int(row['row_index']);assert rows[i]['sha256']==row['sha256'] and rows[i]['entity_id']==row['entity_id']
        rows[i].update(row)
    current=pd.DataFrame(rows)
    current['current_minus_legacy_uv']=np.hypot(current.u1960-current.legacy_u1960,current.v1960-current.legacy_v1960)
    current['current_vs_frozen_unit_snapshot']='unchanged'
    current.loc[current.row_index.isin(changed.row_index),'current_vs_frozen_unit_snapshot']='newly_unit_resolved'
    current.to_csv(OUT/'current_record_screen.csv.gz',index=False,compression={'method':'gzip','mtime':0})
    changed.to_csv(OUT/'newly_resolved_record_screen.csv.gz',index=False,compression={'method':'gzip','mtime':0})
    objects=aggregate(current);objects.to_csv(OUT/'current_object_screen.csv',index=False)
    eligible=current.usable_screen.eq(True)&current.status.eq('ok')&current.flux_units_validated.eq(True)
    before=base.usable_screen.eq(True)&base.status.eq('ok')&base.flux_units_validated.eq(True)
    is_strong=eligible&current.distance_planck_uv.ge(.01)
    summary={'input_records':len(current),'entity_keys':current.entity_id.nunique(),
        'newly_resolved_records':len(changed),'newly_resolved_entities':changed.entity_id.nunique(),
        'newly_eligible_records':int(changed.usable_screen.eq(True).sum()),
        'newly_resolved_eligible_previous_unavailable_entities':changed[changed.usable_screen.eq(True)&changed.previously_unavailable_panel.eq(True)].entity_id.nunique(),
        'current_eligible_records':int(eligible.sum()),'prior_eligible_records':int(before.sum()),
        'current_strong_records':int(is_strong.sum()),'current_strong_entities':current[is_strong].entity_id.nunique(),
        'newly_resolved_strong_records':int((changed.usable_screen.eq(True)&changed.distance_planck_uv.ge(.01)).sum()),
        'newly_resolved_green_records':int((changed.usable_screen.eq(True)&changed.green_dominant.eq(True)).sum()),
        'remaining_MWDD_SDSS_unresolved_records':966,
        'new_reference_quality':{'median_pixel_snr_below_5_records':int(changed.reference_native_median_pixel_snr.lt(5).sum()),
            'native_and_flag_fraction_visible_above_0p1_records':int(changed.reference_native_and_flag_fraction_visible.gt(.1).sum())},
        'definitions':{'eligible':'Existing rank_candidates.annotate usable_screen rules; no additional source-quality claims.',
            'strong':'Eligible record distance_planck_uv >= 0.01; exploratory threshold, no false-discovery probability.',
            'representative':'Calibration, instrument preference, S/N and source URL; no selection by anomaly magnitude.',
            'calibration':'Existing full-original-grid SDSS gri then PS1 gri fallback. Floor 0.02 mag; reject residual >=0.15 mag or absolute tilt >=0.25 mag/1000 A. Sky masking follows the fit for colour integration.',
            'new_units':'Strict native-pixel comparison; astrophysical association, native quality and calibration have separate fields.'},
        'input_sha256':{str(p.relative_to(ROOT)):sha(p) for p in [basepath,OUT/'overlay_registry.json',OUT/'compact_manifest.json',ROOT/'results/screen_input_mwdd.json.gz']},
        'output_sha256':{p.name:sha(p) for p in [OUT/'current_record_screen.csv.gz',OUT/'newly_resolved_record_screen.csv.gz',OUT/'current_object_screen.csv']},
        'frozen_artifacts_modified':False}
    (OUT/'current_summary.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n')
    print(json.dumps(summary,indent=2),flush=True)


def panel_arrays(raw,row,overlay,record):
    w=raw['wave'];f,iv,_=overlay.as_flux_lambda(w,raw['flux'],raw['ivar'],record)
    original_f=f.copy()
    if bool(row.calibrated):
        factor=10**(-.4*(row.cal_offset_mag+row.cal_tilt_mag_per_1000A*(w-6200)/1000))
        f=f*factor
        if iv is not None:iv=iv/factor**2
    w,f,iv=c.clean_spectrum(w,f,iv,mask_sky=True)
    sel=(w>=3600)&(w<=8300);w,f=w[sel],f[sel]
    a=f[(w>=5200)&(w<=5500)];norm=float(np.median(a)) if len(a) else np.nan
    method='median F_lambda at 5200–5500 A'
    if not np.isfinite(norm) or norm<=0:
        norm=float(np.median(abs(f)));method='median absolute visible F_lambda (nonpositive/missing anchor)'
    if not np.isfinite(norm) or norm<=0:raise ValueError('No positive display scale')
    f=f/norm
    bins=[]
    for lo in np.arange(3600,8300,40):
        s=(w>=lo)&(w<lo+40)
        bins.append(((lo+20)/10,float(f[s].mean()) if s.any() else np.nan,
            float(f[s].min()) if s.any() else np.nan,float(f[s].max()) if s.any() else np.nan,int(s.sum())))
    return np.array(bins),{'normalizer':norm,'normalization':method,'visible_native_samples':len(w),
        'native_negative_samples':int((f<0).sum()),'native_min_normalized':float(f.min()),'native_max_normalized':float(f.max())}


def sheets():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    table=pd.read_csv(OUT/'newly_resolved_record_screen.csv.gz',dtype={'source_id':'string'},low_memory=False).sort_values('row_index')
    assert table.entity_id.nunique()==len(table), 'Group newly shared entity rows explicitly before plotting'
    store=CompactInputs();overlay=UnitOverlay();source=frozen();folder=OUT/'contact_sheets';folder.mkdir(exist_ok=True)
    index=[];plot_records=[]
    for start in range(0,len(table),16):
        subset=table.iloc[start:start+16];page=start//16+1
        fig,axes=plt.subplots(4,4,figsize=(18,14.8),layout='constrained')
        page_rows=[]
        for panel,(ax,row) in enumerate(zip(axes.flat,subset.itertuples()),1):
            raw=store.load('mwdd_'+str(row.row_index))
            curve,meta=panel_arrays(raw,row,overlay,source[row.row_index])
            color='#9c477a' if row.flux_conversion_applied else '#215b87'
            ax.fill_between(curve[:,0],curve[:,2],curve[:,3],color='#adb7c1',alpha=.38,lw=0,label='Native min–max in each bin')
            ax.plot(curve[:,0],curve[:,1],color=color,lw=.9,label='40 A mean')
            ax.axhline(0,color='.45',lw=.55)
            for nm in [557.734,589.,589.6,630.03,636.378]:ax.axvline(nm,color='#b18958',lw=.4,alpha=.55)
            label=('Fnu → Flambda' if row.flux_conversion_applied else 'Flambda verified')
            sid=str(row.source_id) if pd.notna(row.source_id) else str(row.entity_id)
            colour_label=f'Duv={row.duv:+.4f}' if np.isfinite(row.duv) else 'colour unavailable'
            cal=f'{row.cal_system} gri' if row.calibrated else 'unanchored'
            ax.set_title(f'{panel:02d} | {sid}\nrow {row.row_index} | {label} | {cal}\n{colour_label} | ref S/N={row.reference_native_median_pixel_snr:.1f}'+
                (' | recovered unavailable' if row.previously_unavailable_panel else '')+(' | ineligible' if not row.usable_screen else ''),fontsize=7.1,loc='left')
            ax.set_xlim(360,830);ax.tick_params(labelsize=6);ax.grid(alpha=.12)
            if panel>12:ax.set_xlabel('Vacuum wavelength (nm)',fontsize=7)
            if (panel-1)%4==0:ax.set_ylabel('Normalized F_lambda; full native range',fontsize=7)
            record={'page':page,'panel':panel,'review_index':start+panel-1,'entity_id':row.entity_id,
                'source_id':sid,'row_index':int(row.row_index),'record_id':row.record_id,
                'flux_convention':row.flux_input_convention,'conversion_applied':bool(row.flux_conversion_applied),
                'current_eligible':bool(row.usable_screen),'previously_unavailable_panel':bool(row.previously_unavailable_panel),
                'external_reference_id':row.flux_evidence_external_reference_id,
                'raw_sha256':row.sha256,'contact_sheet':f'contact_sheets/page_{page:02d}.png',**meta}
            page_rows.append(record)
            for x in curve:plot_records.append({'row_index':int(row.row_index),'wavelength_nm':x[0],
                'mean_normalized_flux':x[1],'native_min':x[2],'native_max':x[3],'native_samples':int(x[4])})
        for ax in list(axes.flat)[len(subset):]:ax.axis('off')
        fig.suptitle(f'New strict unit evidence: page {page:02d}/39 | records {start+1}–{start+len(subset)} of 613\n'
            '40 A display means + full native min/max (negative flux retained). Existing gri recipe where accepted.\n'
            'Reference S/N belongs to the matched original observation. Unit identity, sky flags and astrophysical association remain separate.',fontsize=11)
        path=folder/f'page_{page:02d}.png';fig.savefig(path,dpi=130);plt.close(fig)
        digest=sha(path)
        for r in page_rows:r['contact_sheet_sha256']=digest
        index.extend(page_rows)
        print('contact page',page,'entities',len(index),flush=True)
    pd.DataFrame(index).to_csv(OUT/'contact_sheet_index.csv',index=False)
    pd.DataFrame(plot_records).to_csv(OUT/'contact_sheet_curves.csv.gz',index=False,compression={'method':'gzip','mtime':0})
    report={'pages':39,'entities':613,'newly_resolved_records':613,
        'previously_unavailable_entities':int(table.previously_unavailable_panel.sum()),
        'display_bin_width_A':40,'negative_native_flux_retained':True,'native_range_shown':True,
        'visual_review_claim':'Image generation is not visual inspection. Only separately authored, SHA-bound reviewer notes count as viewed.',
        'input_sha256':{str(p.relative_to(ROOT)):sha(p) for p in [OUT/'newly_resolved_record_screen.csv.gz',OUT/'compact_manifest.json',OUT/'overlay_registry.json']},
        'index_sha256':sha(OUT/'contact_sheet_index.csv'),'curves_sha256':sha(OUT/'contact_sheet_curves.csv.gz'),
        'files':[{'file':r['contact_sheet'],'sha256':r['contact_sheet_sha256']} for r in index if r['panel']==1]}
    (OUT/'contact_sheet_manifest.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=['screen','sheets'])
    args=parser.parse_args();screen() if args.command=='screen' else sheets()
