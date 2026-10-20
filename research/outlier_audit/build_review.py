#!/usr/bin/env python3
"""Build inspectable object dossiers and honest plots; never correct a colour by fiat."""
from __future__ import annotations
import os
from pathlib import Path
import sys
import json
import math
import html
import gzip
import hashlib
import base64

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
os.environ.setdefault('OMP_NUM_THREADS','1')
os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'mpl-cache'))
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
import colour_pipeline as c
from project_io import load_json

OUT=Path(__file__).resolve().parent
CURRENT=ROOT/'research/precision/flux_units/corrected_record_screen.csv.gz'


def current_eligible(tab):
    """Use one explicit current-snapshot gate for dossiers and comparisons."""
    return (tab.current_usable_screen.eq(True)&tab.current_status.eq('ok')&
            tab.current_flux_units_validated.eq(True)&
            np.isfinite(tab.current_u1960)&np.isfinite(tab.current_v1960))


def read():
    tab=pd.read_csv(OUT/'record_audit.csv.gz',dtype={'source_id':'string'},low_memory=False)
    obj=pd.read_csv(OUT/'object_audit.csv',dtype={'source_id':'string'},low_memory=False)
    audit=pd.read_csv(OUT/'recomputed_review_records.csv.gz',low_memory=False)
    tab=tab.merge(audit,on='row_index',how='left',validate='one_to_one',suffixes=('','_audit'))
    precision=ROOT/'research/precision/planckian_projection_audit.csv'
    if precision.exists():
        p=pd.read_csv(precision).rename(columns={'duv_continuous_tangent_sign':'continuous_duv','distance_continuous':'continuous_distance'})
        keep=[k for k in ['row_index','continuous_duv','continuous_distance','projection_class'] if k in p]
        if len(keep)>1:tab=tab.merge(p[keep],on='row_index',how='left',validate='one_to_one')
    cur=pd.read_csv(CURRENT,dtype={'source_id':'string'},low_memory=False)
    # A current result must describe exactly the same frozen records. Never
    # silently fall back to mixed-unit historical colours or a positional join.
    keys=['row_index','entity_id','source_id','sha256','kind']
    if not tab[keys].sort_values('row_index').reset_index(drop=True).equals(
            cur[keys].sort_values('row_index').reset_index(drop=True)):
        raise ValueError('Current screen identity/provenance does not match the frozen audit.')
    cur['calibration_uv_shift']=np.hypot(cur.u1960-cur.raw_u1960,cur.v1960-cur.raw_v1960)
    cols=['row_index','u1960','v1960','duv','hex','distance_planck_uv','usable_screen','status',
          'flux_units_validated','flux_input_convention','flux_conversion_applied','flux_unit_evidence',
          'calibrated','raw_hex','raw_u1960','raw_v1960','raw_duv','calibration_uv_shift',
          'cal_system','cal_max_residual_mag','cal_tilt_mag_per_1000A','largest_visible_gap_A',
          'visible_negative_fraction','visible_median_pixel_snr','result_origin']
    cur=cur[cols].rename(columns={k:'current_'+k for k in cols if k!='row_index'})
    tab=tab.merge(cur,on='row_index',how='left',validate='one_to_one')
    return tab,obj


def adjudicate(tab,obj):
    gaia_path=ROOT/'research/external_validation/results/gaia_extended_quality.csv'
    neighbours_path=ROOT/'research/external_validation/results/gaia_extended_neighbours.csv'
    gaia=pd.read_csv(gaia_path,dtype={'source_id':'string'}).set_index('source_id') if gaia_path.exists() else pd.DataFrame()
    neighbours=pd.read_csv(neighbours_path,dtype={'target_source_id':'string'}) if neighbours_path.exists() else pd.DataFrame()
    rows=[]
    for r in obj.itertuples():
        g=tab[tab.entity_id.eq(r.entity_id)]
        flags=[]
        current=g[current_eligible(g)]
        uv=current[['current_u1960','current_v1960']].to_numpy(float)
        spread=float(np.sqrt(((uv[:,None,:]-uv[None,:,:])**2).sum(axis=2)).max()) if len(uv) else np.nan
        kinds=sorted(set(current.kind))
        strong=int(current.current_distance_planck_uv.ge(.01).sum())
        if g.current_flux_conversion_applied.eq(True).any():
            flags.append('Fnu_to_Flambda_converted_with_native_pixel_evidence')
        if g.current_status.eq('unit_unverified').any():
            flags.append('unverified_flux_units_withheld_from_current_colour')
        if g.recompute_status.eq('error').any():flags.append('historical_raw_recomputation_failed')
        if g.frozen_to_recomputed_uv.gt(1e-7).any():flags.append('historical_frozen_result_mismatch')
        if g.raw_sky_mask_uv_shift.gt(.002).any():flags.append('historical_sky_mask_sensitive')
        if g.negative_CIE_Y_absolute_fraction.gt(.01).any():flags.append('historical_negative_flux_in_visual_response')
        if current.current_largest_visible_gap_A.gt(50).any():flags.append('wide_spectral_gap')
        if current.current_visible_negative_fraction.gt(.1).any():flags.append('negative_visible_pixels_above_10pct')
        if current.current_calibration_uv_shift.ge(.003).any():flags.append('calibration_sensitive')
        if spread>=.005:flags.append('discordant_records')
        if not len(current[current.current_calibrated.eq(True)&current.kind.isin(['DESI','SDSS'])]):
            flags.append('no_calibrated_ground_spectrum')
        if r.has_positional_identity:flags.append('legacy_positional_identity_needs_epoch_check')
        if r.known_hollands_colour:flags.append('published_comparison_target')
        if pd.notna(r.source_id) and r.source_id in gaia.index:
            field=gaia.loc[r.source_id]
            if field.phot_variable_flag=='VARIABLE':flags.append('published_gaia_variable_requires_epoch_resolved_colour')
            if field.gaia_neighbour_count_10arcsec>0:flags.append('catalogued_neighbour_within_10arcsec')
            if not neighbours.empty:
                nearby=neighbours[neighbours.target_source_id.eq(r.source_id)]
                if nearby.relative_G_flux.gt(10).any():flags.append('bright_neighbour_wings_require_image_review')
        usable_rechecks=g.recompute_status.eq('ok').sum()
        if not len(current):assessment='No current spectrum meeting the unit-validation and colour-eligibility rules; no current colour claim.'
        elif 'published_gaia_variable_requires_epoch_resolved_colour' in flags:
            assessment='Published Gaia variable. Do not treat non-simultaneous photometry as a fixed isolated-atmosphere colour. Consult its individual variability and classification evidence.'
        elif r.known_hollands_colour:assessment='Published comparison target; retain discrepancy and method/observation differences.'
        elif 'negative_visible_pixels_above_10pct' in flags or 'wide_spectral_gap' in flags:
            assessment='At least one record is sensitive to missing/noisy spectral information; retain as a quality review, not a discovery.'
        elif 'discordant_records' in flags:
            assessment='Records disagree. Test calibration, identity, shared observations, contamination and variability before a physical interpretation.'
        elif strong and len(kinds)>=2:
            assessment='Current eligible mean colours agree within the exploratory delta-uv = 0.005 criterion in more than one instrument. Observation independence, complete uncertainties, contamination and prior art still require review.'
        elif strong:
            assessment='Outlying colour in a single instrument; a second independent measurement is required.'
        elif kinds==['Gaia_XP']:
            assessment='Gaia XP only. A full coefficient-covariance reconstruction and independent spectrum are required.'
        elif flags or r.review_required:assessment='No current strong colour outlier; inspect the current quality flags and separately labelled historical review evidence.'
        else:assessment='No current review trigger under the stated exploratory rules.'
        if 'unverified_flux_units_withheld_from_current_colour' in flags:
            assessment='One or more records have unresolved flux units and are excluded from current physical colours. '+assessment
        if 'Fnu_to_Flambda_converted_with_native_pixel_evidence' in flags:
            assessment='Verified F_nu data have been converted to F_lambda; compare current and historical values. '+assessment
        if pd.notna(r.source_id) and r.source_id=='3638333660492606976':
            assessment='J1323-0129: retain DESI colour candidate; withdraw independent SDSS corroboration because the MWDD SDSS flux convention is unresolved. Gaia XP is unavailable.'
        rows.append({'entity_id':r.entity_id,'recomputed_records':int(usable_rechecks),
            'current_eligible_records':len(current),
            'current_strong_records':strong,
            'current_max_distance':float(current.current_distance_planck_uv.max()) if len(current) else None,
            'current_instrument_kinds':'|'.join(kinds),'current_instrument_count':len(kinds),
            'current_between_records_uv':spread,
            'current_calibrated_records':int(current.current_calibrated.eq(True).sum()),
            'current_calibration_uv_shift_max':float(current.current_calibration_uv_shift.max()) if len(current) else None,
            'evidence_flags':'|'.join(flags),'assessment':assessment})
    refined=obj.merge(pd.DataFrame(rows),on='entity_id',validate='one_to_one')
    refined.to_csv(OUT/'object_review.csv',index=False)
    # Keep every spectrum, including invalid or unavailable observations, in its dossier.
    record_keys=['row_index','record_id','kind','archive_origin','source_url','sha256','identity_basis',
        'usable_screen','status','raw_hex','hex','raw_duv','duv','continuous_duv','calibrated','cal_system',
        'cal_max_residual_mag','cal_tilt_mag_per_1000A','calibration_uv_shift','largest_visible_gap_A',
        'visible_negative_fraction','visible_median_pixel_snr','recompute_status','frozen_to_recomputed_uv',
        'raw_sky_mask_uv_shift','negative_CIE_Y_absolute_fraction','invalid_negative_clipping_uv_shift']
    record_keys += [k for k in tab if k.startswith('current_')]
    record_keys=[x for x in record_keys if x in tab]
    grouped={key:g for key,g in tab.groupby('entity_id',sort=False)}
    with gzip.open(OUT/'object_dossiers.jsonl.gz','wt',encoding='utf-8') as stream:
        for r in refined.to_dict('records'):
            clean=json.loads(pd.DataFrame([r]).to_json(orient='records'))[0]
            # IDs are strings throughout; JSON round-tripping never uses a float.
            clean['records_detail']=json.loads(grouped[r['entity_id']][record_keys].to_json(orient='records',double_precision=12))
            stream.write(json.dumps(clean,ensure_ascii=False)+'\n')
    return refined


def all_points(tab,obj):
    q=tab[tab.usable_screen.eq(True)&tab.status.eq('ok')]
    fig,axes=plt.subplots(1,2,figsize=(12,5.1),layout='constrained')
    colours={'DESI':'#227da5','Gaia_XP':'#cc7a30','SDSS':'#8260a2'}
    for kind,group in q.groupby('kind'):
        axes[0].scatter(group.u1960,group.v1960,s=9,alpha=.35,edgecolors='none',color=colours.get(kind,'grey'),label=f'{kind} ({len(group):,} records)')
    reps=obj[obj.eligible_records.gt(0)]
    quiet=reps[~reps.review_required]
    marked=reps[reps.review_required]
    axes[1].scatter(quiet.representative_u1960,quiet.representative_v1960,s=10,color='#b7c1c8',alpha=.6,label=f'No triage trigger ({len(quiet):,})')
    axes[1].scatter(marked.representative_u1960,marked.representative_v1960,s=13,color='#af6740',alpha=.6,label=f'Review flagged ({len(marked):,})')
    head=pd.read_csv(ROOT/'results/headline_candidates.csv')
    for ax in axes:
        locus=c._BB_UV[(c._BB_T>=2300)]
        ax.plot(locus[:,0],locus[:,1],color='#1f303d',lw=1.2,label='Planckian locus')
        for r in head.itertuples():
            ax.scatter(r.u1960,r.v1960,s=75,c=r.hex,edgecolor='#152b37',lw=.9,zorder=10)
        ax.set_aspect('equal',adjustable='box')
        ax.set(xlim=(min(.14,q.u1960.min()-.005),max(.315,q.u1960.max()+.005)),
               ylim=(min(.247,q.v1960.min()-.005),max(.367,q.v1960.max()+.005)),
               xlabel='CIE 1960 u',ylabel='CIE 1960 v')
        ax.grid(alpha=.14);ax.legend(fontsize=8,loc='lower right')
    axes[0].set_title(f'Historical selection: all {len(q):,} eligible spectrum records\nIncludes subsequently converted or withheld flux conventions',fontsize=11)
    axes[1].set_title(f'Historical representative per entity key ({len(reps):,})\nCalibration, instrument preference and S/N; no extremeness selection',fontsize=11)
    fig.suptitle('Historical colour plane for audit — superseded for current inference\nEqual geometric scales; large swatches are original headline DESI + Pan-STARRS estimates',fontsize=12)
    fig.savefig(OUT/'audited_colour_plane.png',dpi=200)
    fig.savefig(OUT/'audited_colour_plane.svg')
    plt.close(fig)


def cross_survey(tab):
    good=tab[current_eligible(tab)].copy()
    current_sha=hashlib.sha256(CURRENT.read_bytes()).hexdigest()
    rows=[]
    for key,g in good.groupby('entity_id'):
        # Per-instrument medians do not turn duplicate archives into independent measurements.
        med=g.groupby('kind')[['current_u1960','current_v1960','current_duv']].median()
        for first,second in [('DESI','Gaia_XP'),('SDSS','Gaia_XP'),('DESI','SDSS')]:
            if first not in med.index or second not in med.index:continue
            delta=med.loc[first]-med.loc[second]
            a=g[g.kind.eq(first)];b=g[g.kind.eq(second)]
            rows.append(dict(entity_id=key,source_id=g.source_id.dropna().iloc[0] if g.source_id.notna().any() else '',
                pair=first+' minus '+second,delta_u=float(delta.current_u1960),delta_v=float(delta.current_v1960),
                delta_duv=float(delta.current_duv),distance_uv=float(np.hypot(delta.current_u1960,delta.current_v1960)),
                n_first=len(a),n_second=len(b),
                first_row_indices='|'.join(map(str,a.row_index)),second_row_indices='|'.join(map(str,b.row_index)),
                both_have_calibrated=bool(a.current_calibrated.eq(True).any() and b.current_calibrated.eq(True).any()),
                identity_epoch_unverified=bool(g.identity_basis.str.contains('positional',na=False).any()),
                colour_snapshot='current_unit_validated',
                note='Selected-sample difference of per-instrument coordinate medians. Shared calibrations, duplicate archive observations, epoch differences and selection are not independent errors; this is not an instrument bias estimate.'))
    pairs=pd.DataFrame(rows)
    pairs.to_csv(OUT/'cross_instrument_pairs.csv',index=False,float_format='%.17g')
    summaries=[]
    fig,axes=plt.subplots(1,3,figsize=(12,4.6),layout='constrained')
    for ax,(label,g) in zip(axes,pairs.groupby('pair',sort=True)):
        ax.scatter(g.delta_u,g.delta_v,s=9,alpha=.3,color='#3c728f')
        ax.axhline(0,color='grey',lw=.7);ax.axvline(0,color='grey',lw=.7)
        radius=max(.01,float(np.abs(g[['delta_u','delta_v']]).to_numpy().max())*1.08)
        ax.set(xlim=(-radius,radius),ylim=(-radius,radius))
        ax.set_xlabel('Difference in CIE 1960 u',fontsize=10)
        ax.set_ylabel('Difference in CIE 1960 v',fontsize=10)
        ax.set_title(f'{label}\n{len(g):,} entity pairs\nMedian distance {g.distance_uv.median():.5f}',fontsize=11)
        ax.xaxis.set_major_locator(MaxNLocator(5))
        ax.yaxis.set_major_locator(MaxNLocator(5))
        ax.tick_params(labelsize=9)
        ax.set_aspect('equal');ax.grid(alpha=.1)
        summaries.append(dict(pair=label,n=len(g),median_distance=float(g.distance_uv.median()),
            p95_distance=float(g.distance_uv.quantile(.95)),discordant_above_0005=int(g.distance_uv.ge(.005).sum()),
            median_delta_u=float(g.delta_u.median()),median_delta_v=float(g.delta_v.median())))
    fig.suptitle('Current unit-validated instrument comparisons\nSelected-sample differences of per-instrument medians; shared observations are not independent',fontsize=12)
    fig.savefig(OUT/'cross_instrument_differences.png',dpi=190)
    fig.savefig(OUT/'cross_instrument_differences.svg')
    plt.close(fig)
    (OUT/'cross_instrument_summary.json').write_text(json.dumps({
        'colour_snapshot':'current_unit_validated',
        'input_path':str(CURRENT.relative_to(ROOT)),'input_sha256':current_sha,
        'input_records':len(tab),'eligible_records':len(good),
        'selection':'usable_screen=true, status=ok, flux_units_validated=true, finite u1960/v1960 in corrected_record_screen.csv.gz',
        'aggregation':'One pair per entity_id and instrument pair; coordinate-wise medians of eligible records within each instrument.',
        'pairs':summaries,
        'interpretation':'Selected-sample descriptive differences, not instrument systematic-bias estimates. Unresolved units are excluded. Duplicate archive observations, shared photometric calibration, differing epochs, uncertain positional identities and sample selection prevent treating pairs as independent error estimates. No population false-discovery rate is estimated.'},indent=2)+'\n')


def spectral_panels(tab,obj):
    # A compact visual contact sheet for every strong outlier entity. Native
    # signed data are retained; binning is display-only, never used in metrics.
    queue=obj[obj.strong_records.gt(0)].sort_values('max_distance',ascending=False)
    frozen=[]
    for name in ['mwdd','sdss']:frozen.extend(load_json(ROOT/f'results/screen_input_{name}.json'))
    directory=OUT/'spectrum_contact_sheets';directory.mkdir(exist_ok=True)
    entries=[]
    for page in range(math.ceil(len(queue)/16)):
        selected=queue.iloc[page*16:(page+1)*16]
        fig,axes=plt.subplots(4,4,figsize=(16,12),layout='constrained')
        for ax,r in zip(axes.flat,selected.itertuples()):
            g=tab[(tab.entity_id.eq(r.entity_id))&tab.kind.isin(['DESI','SDSS','Gaia_XP'])]
            drawn=set();lines=0
            for row in g.sort_values(['kind','record_id']).itertuples():
                rec=frozen[row.row_index];p=c.data_path(rec['parsed_path'])
                if not p.exists() or rec['sha256'] in drawn:continue
                d=np.load(p);w=d['wavelength_angstrom'];f=d['flux_original'] if 'flux_original' in d else d['flux_flam']
                mask=np.isfinite(w)&np.isfinite(f)&(w>3600)&(w<8300)
                w,f=w[mask],f[mask]
                normalization=np.median(f[(w>5200)&(w<5500)])
                if not np.isfinite(normalization) or normalization<=0:normalization=np.median(np.abs(f))
                if not normalization>0:continue
                bins=np.arange(3600,8341,40)
                ids=np.digitize(w,bins)
                bw=[];bf=[]
                for k in range(1,len(bins)):
                    sel=ids==k
                    if sel.any():bw.append(np.mean(w[sel])/10);bf.append(np.mean(f[sel])/normalization)
                label=row.kind+(' direct' if row.archive_origin=='SDSS_DR17_direct' else '')
                ax.plot(bw,bf,lw=.65,alpha=.75,label=label)
                drawn.add(rec['sha256']);lines+=1
            ax.set_title((str(r.source_id) if pd.notna(r.source_id) else r.names[:30])+f'\nmax |Duv|={r.max_distance:.4f}; '+r.spectral_types[:20],fontsize=8)
            ax.set(xlim=(360,830),ylim=(-.2,3.2))
            ax.axhline(0,color='grey',lw=.4);ax.grid(alpha=.1)
            if lines:ax.legend(fontsize=5,loc='upper right')
            else:ax.text(.5,.5,'No verified spectrum available',ha='center',transform=ax.transAxes,fontsize=8)
            entries.append(dict(entity_id=r.entity_id,source_id=r.source_id,contact_sheet=f'spectrum_contact_sheets/page_{page+1:02d}.png',panel=(len(entries)%16)+1,
                plot_caution='Raw archive flux, 40 Angstrom display-only binning, finite signed samples retained, normalized at 5200–5500 A. Plot ordinate limited for shape inspection; all numerical metrics use untrimmed data.'))
        for ax in axes.flat[len(selected):]:ax.axis('off')
        fig.suptitle(f'Strong colour outliers — individual spectra, page {page+1}/{math.ceil(len(queue)/16)}\nRaw spectral shapes; x-axis nm, common visual normalization. Fixed y range is display-only.',fontsize=13)
        fig.savefig(directory/f'page_{page+1:02d}.png',dpi=135)
        plt.close(fig)
        print('Contact sheet',page+1,flush=True)
    pd.DataFrame(entries).to_csv(OUT/'contact_sheet_index.csv',index=False)


def browser_table(tab,obj):
    # Standalone inspection artifact, no dependencies or network calls. Public
    # source links are opened only by a user's explicit click.
    cols=['entity_id','source_id','names','spectral_types','records','eligible_records','instrument_kinds',
          'min_distance','max_distance','between_records_uv','review_required','review_status','review_reasons',
          'recomputed_records','evidence_flags','assessment','representative_u1960','representative_v1960',
          'current_eligible_records','current_strong_records','current_max_distance',
          'current_instrument_kinds','current_instrument_count','current_between_records_uv']
    data=json.loads(obj[cols].to_json(orient='records',double_precision=10))
    records=['entity_id','row_index','kind','archive_origin','source_url','sha256','raw_hex','hex','duv','calibrated',
        'cal_max_residual_mag','calibration_uv_shift','usable_screen','identity_basis','recompute_status','raw_sky_mask_uv_shift','negative_CIE_Y_absolute_fraction']
    records += [k for k in tab if k.startswith('current_')]
    raw=json.loads(tab[records].to_json(orient='records',double_precision=10))
    # Compress only the embedded JSON, with every field and original JSON value
    # retained. The hash addresses the UTF-8 payload before gzip, independently
    # of compression implementation, HTML formatting or download transport.
    payload=json.dumps({'objects':data,'records':raw},ensure_ascii=False,separators=(',',':')).encode('utf-8')
    packed=base64.b64encode(gzip.compress(payload,mtime=0)).decode('ascii')
    payload_meta={'encoding':'gzip+base64','uncompressed_sha256':hashlib.sha256(payload).hexdigest(),
                  'uncompressed_bytes':len(payload),'objects':len(data),'records':len(raw),
                  'current_input_sha256':hashlib.sha256(CURRENT.read_bytes()).hexdigest()}
    template='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>White dwarf object audit</title>
<style>body{font:15px system-ui,sans-serif;margin:24px;color:#24333e;background:#f6f8fa}h1{font-size:25px}input,select{font:inherit;padding:9px;margin:4px 12px 8px 0;max-width:90%}input{width:350px}table{border-collapse:collapse;width:100%;background:white}th,td{text-align:left;padding:9px;border-bottom:1px solid #dbe1e5;font-size:13px}th{position:sticky;top:0;background:#e6edf2}button{font:inherit;color:#145c82;background:none;border:0;cursor:pointer;text-align:left}summary{cursor:pointer}.muted{color:#5b6e7b}.wrap{overflow:auto}#details{background:white;padding:20px;margin:20px 0;overflow:auto}code{font-size:12px;overflow-wrap:anywhere}.badge{font-size:12px;padding:4px;background:#edf1f4;border-radius:4px}.note{max-width:1050px;line-height:1.65}</style>
<h1>Individual white dwarf spectrum audit</h1><p class="note">All __NRECORDS__ frozen records are retained in __NOBJECTS__ catalogue entity keys. The corrected screen admits __NELIGIBLE__ records: verified Fν exports are converted, and unresolved units are withheld. Historical values remain visible for audit. Review rules are exploratory, not discovery significance. Gaia identifiers remain exact strings. Legacy positional identity matches are flagged. Search a Gaia ID, name or evidence flag, then open a source to see every record and its provenance.</p>
<p class="note">The <a href="cross_instrument_differences.png">instrument comparison</a> uses current unit-validated colours. The <a href="audited_colour_plane.png">historical colour plane</a>, historical review queues and 22 contact sheets retain the original selections and archive flux for traceability. Use the <a href="../precision/flux_units/corrected_colour_plane.png">current colour plane</a> for the revised screen. Broad-band calibration, shared observations and observation epochs still require scientific review.</p>
<label>Search <input id="search" disabled placeholder="Gaia ID, star name, quality flag…"></label><label>View <select id="view" disabled><option value="review">Historical review queue</option><option value="strong">Current distance ≥ 0.01 (__NSTRONG__)</option><option value="legacystrong">Historical strong-outlier review (__NLEGACYSTRONG__)</option><option value="multi">Initial __NSHORTLIST__ follow-up candidates</option><option value="all">All entity keys</option></select></label><p id="count" class="muted">Loading the embedded records…</p><div id="details">Choose an object below once loading completes. Current values use validated flux conventions; historical values are retained separately. Missing values stay missing.</div><noscript><p>This viewer needs JavaScript. Download the <a href="object_review.csv">object CSV</a>, <a href="../precision/flux_units/corrected_record_screen.csv.gz">current record CSV (gzip)</a> or <a href="record_audit.csv.gz">historical record CSV (gzip)</a> to inspect the data.</p></noscript><div class="wrap"><table><thead><tr><th>Source / name</th><th>Types</th><th>Current / historical instruments</th><th>Current / historical max distance</th><th>Current / historical between-record distance</th><th>Evidence / next check</th></tr></thead><tbody id="body"></tbody></table></div>
<script>
let DATA=[],RECORDS=[];
const PAYLOAD_META=__PAYLOAD_META__;
const PAYLOAD_GZIP_BASE64="__PAYLOAD_GZIP_BASE64__";
const E=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const N=x=>x==null?'—':Number(x).toFixed(5);
function show(key){
  const o=DATA.find(x=>x.entity_id===key);
  const rows=RECORDS.filter(x=>x.entity_id===key);
  document.querySelector('#details').innerHTML=`<h2>${E(o.names)}</h2><p><code>${E(key)}</code> · ${E(o.assessment)}</p><p><b>Current eligible instruments:</b> ${E(o.current_instrument_kinds)||'None'} (${o.current_eligible_records} records)<br><b>Historical review reasons:</b> ${E(o.review_reasons)||'None'}<br><b>Evidence flags:</b> ${E(o.evidence_flags)||'None'}. Flags prefixed historical_ describe the frozen raw recheck.</p><table><tr><th>Row / instrument</th><th>Current raw → selected colour</th><th>Current / historical Duv</th><th>Current flux convention</th><th>Current / historical calibration Δuv</th><th>Current support / SNR</th><th>Historical raw recheck</th><th>Identity / provenance</th></tr>${rows.map(r=>`<tr><td>${r.row_index}: ${E(r.kind)}<br>${E(r.archive_origin)}</td><td>${E(r.current_raw_hex??'Unavailable')} → ${E(r.current_hex??'Unavailable')}<br>Current calibrated: ${E(r.current_calibrated)}<br><span class="muted">Historical: ${E(r.raw_hex)} → ${E(r.hex)}; calibrated ${E(r.calibrated)}</span></td><td>${N(r.current_duv)} / ${N(r.duv)}<br>Current status: ${E(r.current_status)}<br>Current eligible: ${E(r.current_usable_screen)}</td><td>${E(r.current_flux_input_convention)}<br>Validated: ${E(r.current_flux_units_validated)}<br>Converted: ${E(r.current_flux_conversion_applied)}<br>${E(r.current_flux_unit_evidence)}</td><td>${N(r.current_calibration_uv_shift)} / ${N(r.calibration_uv_shift)}<br>Current system: ${E(r.current_cal_system)}</td><td>Largest gap (Å): ${N(r.current_largest_visible_gap_A)}<br>Negative pixel fraction: ${N(r.current_visible_negative_fraction)}<br>Median pixel SNR: ${N(r.current_visible_median_pixel_snr)}</td><td>${E(r.recompute_status??'Not in targeted raw recheck')}<br>Historical eligible: ${E(r.usable_screen)}</td><td>${E(r.identity_basis)}<br><a href="${E(r.source_url)}" target="_blank" rel="noopener">Original spectrum</a><br><code>SHA256 ${E(r.sha256)}</code></td></tr>`).join('')}</table>`;
  document.querySelector('#details').scrollIntoView({block:'start',behavior:'smooth'});
}
function render(){
  const term=document.querySelector('#search').value.toLowerCase(),view=document.querySelector('#view').value;
  let rows=DATA.filter(o=>(view==='all'||view==='review'&&o.review_required||view==='strong'&&o.current_strong_records>0||view==='legacystrong'&&o.max_distance>=.01||view==='multi'&&o.review_status==='multiple_instrument_colour_candidate')&&(!term||JSON.stringify(o).toLowerCase().includes(term)));
  const field=view==='strong'||view==='all'?'current_max_distance':'max_distance';
  rows.sort((a,b)=>(b[field]??-1)-(a[field]??-1));
  document.querySelector('#count').textContent=rows.length+' matching entity keys; sorted by '+(field==='current_max_distance'?'current':'historical')+' maximum distance; each opens its full record history.';
  const body=document.querySelector('#body');
  body.innerHTML=rows.map(o=>`<tr><td><button data-key="${E(o.entity_id)}">${E(o.names)}</button><br><code>${E(o.source_id)}</code></td><td>${E(o.spectral_types)}</td><td>Current: ${E(o.current_instrument_kinds)||'None'}<br><span class="muted">Historical: ${E(o.instrument_kinds)||'None'}</span></td><td>${N(o.current_max_distance)} / ${N(o.max_distance)}</td><td>${N(o.current_between_records_uv)} / ${N(o.between_records_uv)}</td><td>${E(o.evidence_flags)}<br><span class="muted">${E(o.assessment)}</span></td></tr>`).join('');
  body.querySelectorAll('button').forEach(b=>b.onclick=()=>show(b.dataset.key));
}
document.querySelector('#search').oninput=render;
document.querySelector('#view').onchange=render;
async function initializeData(){
  if(typeof DecompressionStream!=='function')throw new Error('Native gzip decompression is unavailable in this browser.');
  const compressed=Uint8Array.from(atob(PAYLOAD_GZIP_BASE64),c=>c.charCodeAt(0));
  const stream=new Blob([compressed]).stream().pipeThrough(new DecompressionStream('gzip'));
  const bytes=new Uint8Array(await new Response(stream).arrayBuffer());
  if(bytes.length!==PAYLOAD_META.uncompressed_bytes)throw new Error('Embedded record length verification failed.');
  if(globalThis.crypto?.subtle){
    const digest=await globalThis.crypto.subtle.digest('SHA-256',bytes);
    const hex=Array.from(new Uint8Array(digest),b=>b.toString(16).padStart(2,'0')).join('');
    if(hex!==PAYLOAD_META.uncompressed_sha256)throw new Error('Embedded record SHA256 verification failed.');
  }
  const decoded=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(bytes));
  if(!Array.isArray(decoded.objects)||!Array.isArray(decoded.records)||decoded.objects.length!==PAYLOAD_META.objects||decoded.records.length!==PAYLOAD_META.records)throw new Error('Embedded record counts are inconsistent.');
  DATA=decoded.objects;RECORDS=decoded.records;
  document.querySelector('#search').disabled=false;
  document.querySelector('#view').disabled=false;
  render();
  return true;
}
const DATA_READY=initializeData().catch(error=>{
  document.querySelector('#count').textContent='The embedded records could not be opened.';
  document.querySelector('#details').innerHTML=`<p>${E(error.message)} Download the <a href="object_review.csv">object CSV</a>, <a href="../precision/flux_units/corrected_record_screen.csv.gz">current record CSV (gzip)</a> or <a href="record_audit.csv.gz">historical record CSV (gzip)</a> to inspect the complete datasets.</p>`;
  return false;
});</script></html>'''
    text=template.replace('__PAYLOAD_META__',json.dumps(payload_meta,separators=(',',':'))).replace('__PAYLOAD_GZIP_BASE64__',packed)
    counts={'NRECORDS':len(tab),'NOBJECTS':len(obj),'NELIGIBLE':int(current_eligible(tab).sum()),
            'NSTRONG':int(obj.current_strong_records.gt(0).sum()),
            'NLEGACYSTRONG':int(obj.strong_records.gt(0).sum()),
            'NSHORTLIST':int(obj.review_status.eq('multiple_instrument_colour_candidate').sum())}
    for key,value in counts.items():text=text.replace('__'+key+'__',format(value,','))
    (OUT/'object_audit.html').write_text(text,encoding='utf-8')


if __name__=='__main__':
    tab,obj=read()
    obj=adjudicate(tab,obj)
    all_points(tab,obj);cross_survey(tab);browser_table(tab,obj)
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--keep-contact-sheets',action='store_true');args=parser.parse_args()
    if not args.keep_contact_sheets:spectral_panels(tab,obj)
    print('Object dossiers, browser table and figures complete.',flush=True)
