#!/usr/bin/env python3
"""Replay bounded unit/support research from committed evidence, fully offline.

The original 3719-file cache and unzipped query cache are deliberately absent
from the required inputs. Compact native arrays preserve all tested samples.
"""
from __future__ import annotations
from collections import Counter,defaultdict
import base64
import csv
import gzip
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(HERE))
import numpy as np
import pandas as pd
from compact_inputs import CompactInputs
from overlay import UnitOverlay
from fetch_and_identify import native, reference_key
from build_current import analyze_arrays, aggregate
from native_quality_audit import compute as compute_native, COLOUR_FIELDS
from build_science_view import derive, RECIPE_FIELDS
from build_view import decode_columnar,js_value,classification_context
from j1323_audit import compute as compute_j1323
from archive_queries import verify_archive
from flux_conventions import UnverifiedFluxConvention


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def same(actual,expected,label='',atol=2e-10,rtol=2e-8):
    """Exact categorical agreement and explicit numerical tolerance."""
    if isinstance(actual,np.generic):actual=actual.item()
    if isinstance(expected,np.generic):expected=expected.item()
    if isinstance(actual,dict) and isinstance(expected,dict):
        assert set(actual)==set(expected),(label,'different keys',set(actual)^set(expected))
        for key in actual:same(actual[key],expected[key],label+'/'+str(key),atol,rtol)
    elif isinstance(actual,(list,tuple)) and isinstance(expected,(list,tuple)):
        assert len(actual)==len(expected),(label,'different lengths')
        for i,(a,b) in enumerate(zip(actual,expected)):same(a,b,label+'/'+str(i),atol,rtol)
    elif isinstance(actual,(float,int)) and not isinstance(actual,bool) and isinstance(expected,(float,int)) and not isinstance(expected,bool):
        assert np.isclose(actual,expected,atol=atol,rtol=rtol,equal_nan=True),(label,actual,expected)
    elif pd.isna(actual) and pd.isna(expected):pass
    else:assert actual==expected,(label,actual,expected)


def verify_viewer_annotations(payload,science,root=ROOT):
    """Fast source/identity/link check; no native replay or image regeneration."""
    root=Path(root).resolve();base=root/'research/unit_resolution_followup'
    context=payload['classification_context']
    assert context==classification_context(root), 'Viewer annotations differ from the saved source records'
    expected={6462:('767756877680612864','DQ:'),7607:('4518692348609283712','DAZH'),
        8019:('2780975896637670528','DZ'),7930:('3217759570831525120','DBZAe'),
        5827:('1242828982729309952','DZ:')}
    rows={r['row_index']:r for r in context['records']}
    assert len(context['records'])==len(rows)==5 and set(rows)==set(expected)
    byrow=science.set_index('row_index');verified={}
    sources={6462:json.loads((base/'root_targeted/classification_context.json').read_text())}
    sources.update({r['row_index']:r for r in json.loads((base/'targeted_followup/results.json').read_text())['records']})
    sources[5827]=json.loads((base/'targeted_followup/local_row_5827.json').read_text())['record']
    for index,(source,preserved) in expected.items():
        annotation=rows[index]
        assert isinstance(annotation['source_id'],str)
        assert annotation['source_id']==source==byrow.loc[index,'source_id']==sources[index]['source_id']
        assert annotation['preserved_catalogue_spectype']==preserved
        assert annotation['source_record']==sources[index], ('Changed source evidence',index)
        assert annotation['summary_ja'] and annotation['context_status']
        links={r['href'] for r in annotation['links']}
        required={'root_targeted/README.md'} if index==6462 else {
            'targeted_followup/README.md',f'targeted_followup/native_row_{index}.png'}
        assert required<=links
        for name in links|{annotation['source_file']}:
            path=(base/name).resolve();assert path.is_relative_to(base) and path.is_file()
            verified[str(path.relative_to(root))]=sha(path)
    assert rows[5827]['scope']=='local_native_arrays_and_existing_metadata_only'
    assert 'ローカル確認のみ' in rows[5827]['summary_ja']
    assert '新しい文献・Gaia・位置の検証はしていません' in rows[5827]['summary_ja']
    assert 'カタログ分類の食い違い' in rows[8019]['summary_ja'] and 'Gaiaのスコアも物理確率ではありません' in rows[8019]['summary_ja']
    for name,digest in context['source_document_sha256'].items():
        assert sha(root/name)==digest;verified[name]=digest
    return {'annotation_rows_checked':len(rows),'verified_file_sha256':verified}


def verify(root=ROOT):
    root=Path(root).resolve();base=root/'research/unit_resolution_followup';verified={}
    def track(path,expected=None):
        p=Path(path);p=p if p.is_absolute() else root/p
        value=sha(p)
        if expected is not None:assert value==expected,('file SHA mismatch',str(p))
        verified[str(p.relative_to(root))]=value
        return p
    def read(name):
        path=track(base/name);return json.loads(path.read_text())
    def input_hashes(payload):
        for path,digest in payload.get('input_sha256',{}).items():track(path,digest)
    frozen=[]
    for origin in ['mwdd','sdss']:
        path=track(root/f'results/screen_input_{origin}.json.gz')
        with gzip.open(path,'rt') as f:frozen.extend(json.load(f))
    assert len(frozen)==9902
    prior=json.loads(track(root/'research/precision/flux_convention_evidence.json').read_text())
    unknown={int(r['mwdd_row_index']):r for r in prior['records'] if r['convention']=='unresolved'}
    universe=pd.read_csv(track(base/'unresolved_universe.csv'),dtype={'source_id':'string'})
    assert len(universe)==1579 and set(universe.mwdd_row_index)==set(unknown)
    for r in universe.itertuples():
        assert r.mwdd_sha256==unknown[r.mwdd_row_index]['mwdd_sha256']==frozen[r.mwdd_row_index]['sha256']
        assert r.mwdd_source_url==frozen[r.mwdd_row_index]['source_url']
    selection=read('selection.json');input_hashes(selection)
    archive=verify_archive(base);verified.update(archive['verified_file_sha256'])
    observations=read('catalogue_observations.json')
    assert len(observations)==2175 and len({reference_key(r) for r in observations})==2140
    association={(int(r['row_index']),reference_key(r)):r for r in observations}
    assert len(association)==2175 and {i for i,k in association}<=set(unknown)
    evidence=read('unit_evidence_all.json');input_hashes(evidence['summary'])
    assert evidence['summary']['thresholds']==native.THRESHOLDS
    assert len(evidence['pair_evidence'])==len(association)==2175
    assert {(r['mwdd_row_index'],r['external_reference_id']) for r in evidence['pair_evidence']}==set(association)
    retrieval=read('retrieval_all.json');assert retrieval['raw_inputs']==retrieval['verified']==3719 and retrieval['failed']==0
    raw_records={r['key']:r for r in retrieval['records']};assert len(raw_records)==3719
    assert Counter(r['format'] for r in raw_records.values())=={'mwdd':1579,'sdss':2140}
    assert sum(r['bytes'] for r in raw_records.values())==674779985
    assert all(r['status']=='verified' for r in raw_records.values())
    store=CompactInputs(root);manifest=store.manifest;track(base/'compact_manifest.json');input_hashes(manifest)
    assert set(store.entries)==set(raw_records) and manifest['records_count']==3719 and manifest['quality_reference_count']==613
    for s in manifest['shards']:track(base/s['file'],s['sha256'])
    d=manifest['wavelength_dictionary'];track(base/d['file'],d['sha256'])
    for key,r in raw_records.items():
        compact=store.entries[key]
        assert compact['raw_sha256']==r['sha256'] and compact['source_url']==r['source_url'] and compact['raw_bytes']==r['bytes']
        value=store.load(key)  # Every stored sample and array SHA is checked.
        assert value['compact_array_sha256_verified'] and len(value['wave'])==compact['pixel_count']
        if r['format']=='mwdd':
            i=r['mwdd_row_indices'][0]
            numeric=hashlib.sha256(np.column_stack([value['wave'],value['flux']]).astype('<f8').tobytes()).hexdigest()
            assert numeric==frozen[i]['numeric_sha256_wavelength_flux'] and r['sha256']==frozen[i]['sha256']
        else:
            header=value['header'];assert header['BUNIT']=='1E-17 erg/cm^2/s/Ang'
            for field,column in [('PLATEID','plate'),('MJD','mjd'),('FIBERID','fiberID')]:
                assert int(header[field])==int(r['catalogue_observation'][column])
    replay_by_row=defaultdict(list)
    for old in evidence['pair_evidence']:
        i=old['mwdd_row_index'];key=old['external_reference_id'];original=frozen[i]
        assert (i,key) in association
        result=native.compare({'row_index':i,'entity_id':old['entity_id'],'wdid':original['wdid'],
            'source_url':original['source_url'],'sha256':original['sha256']},
            {'row_index':-1,'source_url':raw_records[key]['source_url'],'sha256':raw_records[key]['sha256']},
            store.load('mwdd_'+str(i)),store.load(key))
        for k,v in result.items():
            if k!='direct_row_index':same(v,old[k],f'identity row {i}/{key}/{k}',atol=2e-12,rtol=2e-8)
        same(old['cone_distance_arcsec'],60*association[i,key]['distance'],'cone distance')
        result['external_reference_id']=key;replay_by_row[i].append(result)
    assert sum(map(len,replay_by_row.values()))==2175
    accepted={};counts=Counter()
    for row in evidence['records']:
        i=row['mwdd_row_index'];proofs=replay_by_row[i]
        good=[p for p in proofs if p['convention']!='unresolved'];conventions={p['convention'] for p in good}
        decision=next(iter(conventions)) if len(conventions)==1 else 'unresolved'
        assert row['convention']==decision and row['reference_pairs_assessed']==len(proofs)
        assert row['accepted_reference_pairs']==len(good)
        counts[decision]+=1
        if decision!='unresolved':
            assert all(p[decision+'_accepted'] and not p[('fnu' if decision=='flambda' else 'flambda')+'_accepted'] for p in good)
            selected=min(good,key=lambda p:p[decision+'_max_fractional_shape_residual'])
            assert row['external_reference_id']==selected['external_reference_id'];accepted[i]=row
        else:assert row['external_reference_id'] is None
    assert counts=={'flambda':435,'fnu':178,'unresolved':966} and len(accepted)==613
    assert {r['mwdd_row_index'] for r in evidence['records']}==set(unknown)
    overlay=UnitOverlay(root);track(base/'overlay_registry.json')
    assert {r['mwdd_row_index'] for r in overlay.payload['records']}==set(accepted)
    # Conversion/inverse-variance invariants and rejection of one-bit changes
    # in the actual bundled spectral values, under both accepted conventions.
    for convention in ['fnu','flambda']:
        item=next(r for r in accepted.values() if r['convention']==convention);i=item['mwdd_row_index']
        raw=store.load('mwdd_'+str(i));w,f=raw['wave'],raw['flux'];iv=np.linspace(1,2,len(w))
        new,newiv,_=overlay.as_flux_lambda(w,f,iv,frozen[i]);factor=2.99792458e18/w**2 if convention=='fnu' else np.ones(len(w))
        np.testing.assert_array_equal(new,f*factor);np.testing.assert_array_equal(newiv,iv/factor**2)
        np.testing.assert_allclose(new*np.sqrt(newiv),f*np.sqrt(iv),rtol=5e-15,atol=0)
        assert np.array_equal(new<0,f<0)
        changed=f.copy();changed[0]=np.nextafter(changed[0],np.inf)
        try:overlay.as_flux_lambda(w,changed,iv,frozen[i])
        except ValueError:pass
        else:raise AssertionError('Changed numerical values passed overlay')
    unresolved=next(r for r in evidence['records'] if r['convention']=='unresolved')
    i=unresolved['mwdd_row_index'];r=store.load('mwdd_'+str(i))
    try:overlay.as_flux_lambda(r['wave'],r['flux'],r['ivar'],frozen[i])
    except UnverifiedFluxConvention:pass
    else:raise AssertionError('Unknown convention was admitted')
    compatibility=pd.read_csv(track(base/'current_record_screen.csv.gz'),dtype={'source_id':'string'},low_memory=False)
    newtable=pd.read_csv(track(base/'newly_resolved_record_screen.csv.gz'),dtype={'source_id':'string'},low_memory=False).set_index('row_index')
    assert len(newtable)==613 and set(newtable.index)==set(accepted)
    for i in sorted(accepted):
        replay=analyze_arrays(frozen[i],store.load('mwdd_'+str(i)),overlay);saved=newtable.loc[i]
        assert replay['status']==saved.status and bool(replay['calibrated'])==bool(saved.calibrated)
        for k,v in replay.items():
            if k in COLOUR_FIELDS or k.startswith('cal_') or k.startswith('raw_') and k not in ['raw_path','raw_sha256']:
                if k in saved:same(v,saved[k],f'existing calibration/colour {i}/{k}',atol=2e-8,rtol=2e-7)
    assert newtable.usable_screen.eq(True).sum()==611
    current_summary=read('current_summary.json');input_hashes(current_summary)
    for name,digest in current_summary['output_sha256'].items():track(base/name,digest)
    assert current_summary['current_eligible_records']==8084 and current_summary['current_strong_records']==421 and current_summary['current_strong_entities']==325
    quality=pd.read_csv(track(base/'native_quality_metrics.csv.gz'),dtype={'source_id':'string'},low_memory=False)
    recomputed=compute_native(root)
    assert len(quality)==len(recomputed)==1226
    for actual,expected in zip(recomputed.to_dict('records'),quality.to_dict('records')):
        for k,v in actual.items():
            # The evidence preserves a few missing Gaia IDs as the literal
            # token "nan"; CSV readers represent that missing field as null.
            # Entity and frozen row IDs, never this token, are the join keys.
            if k=='source_id' and v=='nan' and pd.isna(expected[k]):continue
            same(v,expected[k],f'native support {actual["row_index"]}/{actual["mode"]}/{k}',atol=2e-9,rtol=2e-8)
    assert quality.native_visible_samples_without_export_correspondence.eq(0).all()
    quality_summary=read('native_quality_summary.json');input_hashes(quality_summary)
    track(base/'native_quality_metrics.csv.gz',quality_summary['output_sha256'])
    science=pd.read_csv(track(base/'science_record_view.csv.gz'),dtype={'source_id':'string'},low_memory=False)
    reconstructed=derive(compatibility,recomputed)
    assert len(science)==9902 and science.entity_id.nunique()==6003
    assert np.array_equal(science.row_index,np.arange(9902)) and science.entity_id.equals(compatibility.entity_id)
    for k in COLOUR_FIELDS+['status','usable_screen','native_support_audit_scope','science_quality_status','science_quality_reason']:
        for i,(a,b) in enumerate(zip(reconstructed[k],science[k])):same(a,b,f'science derived {i}/{k}',atol=2e-9,rtol=2e-8)
    outside=~science.row_index.isin(accepted)
    for k in COLOUR_FIELDS:
        if k in compatibility:
            for a,b in zip(science.loc[outside,k],compatibility.loc[outside,k]):same(a,b,'outside-scope retention')
    held=science.status.eq('native_support_withheld');assert held.sum()==12
    assert science.loc[held,COLOUR_FIELDS].isna().all().all()
    assert all(not value for value in science.loc[held,'usable_screen'])
    summary=read('science_view_summary.json');input_hashes(summary)
    for name,digest in summary['output_sha256'].items():track(base/name,digest)
    assert [summary[k] for k in ['current_eligible_records','current_strong_records','current_strong_entities']]==[8074,419,324]
    assert [summary[k] for k in ['previously_unavailable_entities_with_units_resolved','previously_unavailable_entities_with_native_supported_colour']]==[115,112]
    eligible=science.usable_screen.eq(True)&science.status.eq('ok')&science.flux_units_validated.eq(True)
    strong=eligible&science.distance_planck_uv.ge(.01)
    assert int(eligible.sum())==8074 and int(strong.sum())==419 and science[strong].entity_id.nunique()==324
    objects=pd.read_csv(track(base/'science_object_view.csv'),dtype={'source_id':'string'},low_memory=False)
    assert len(objects)==6003 and objects.entity_id.is_unique
    # All held record colours are absent, including display swatches. Object
    # records use eligible spectra and retain every frozen row/alias identity.
    for r in objects.itertuples():
        rows=science[science.entity_id.eq(r.entity_id)]
        assert set(map(int,r.record_rows.split('|')))==set(rows.row_index)
        assert r.eligible_records==int(eligible.loc[rows.index].sum())
        if pd.notna(r.representative_row_index):assert eligible.iloc[int(r.representative_row_index)]
    completion=read('review_completion.json');input_hashes(completion)
    for name,digest in completion['output_sha256'].items():track(base/name,digest)
    assert completion['complete'] and completion['individually_viewed_records']==613 and completion['actually_opened_fixed_images']==39
    index=pd.read_csv(track(base/'contact_sheet_index.csv'),dtype={'source_id':'string'})
    reviews=pd.read_csv(track(base/'individual_review.csv'),dtype={'entity_id':'string'})
    assert len(index)==len(reviews)==613 and index.row_index.is_unique and reviews.row_index.is_unique
    assert set(reviews.row_index)==set(index.row_index)==set(accepted)
    assert index.entity_id.nunique()==reviews.entity_id.nunique()==613
    joined=index.merge(reviews,on=['row_index','entity_id','page','panel','contact_sheet_sha256'],validate='one_to_one')
    assert len(joined)==613 and joined.observation.str.strip().ne('').all() and joined.evidence_limits.str.strip().ne('').all()
    for r in index.drop_duplicates('contact_sheet').itertuples():track(base/r.contact_sheet,r.contact_sheet_sha256)
    assert index.previously_unavailable_panel.eq(True).sum()==115
    image_manifest=read('contact_sheet_manifest.json');input_hashes(image_manifest)
    track(base/'contact_sheet_index.csv',image_manifest['index_sha256']);track(base/'contact_sheet_curves.csv.gz',image_manifest['curves_sha256'])
    assert len(image_manifest['files'])==39
    for key,digest in completion['image_sha256'].items():track(base/key,digest)
    # Three bundled originals independently replay the highlighted identity,
    # source proper-motion propagation, native masks and all colour conditions.
    jmanifest=read('j1323/input_manifest.json')
    for r in jmanifest['records']:
        path=track(base/'j1323'/r['bundled_file'],r['bundled_sha256'])
        assert hashlib.sha256(gzip.decompress(path.read_bytes())).hexdigest()==r['sha256']
    track(jmanifest['gaia_input_path'],jmanifest['gaia_input_sha256'])
    jreplay,jcurves=compute_j1323(root,base/'j1323');jsaved=read('j1323/results.json')
    same(jreplay,jsaved,'J1323 full original replay',atol=2e-8,rtol=2e-7)
    with np.load(track(base/'j1323/display_curves.npz'),allow_pickle=False) as arrays:
        assert set(arrays.files)==set(jcurves)
        for k,v in jcurves.items():np.testing.assert_allclose(arrays[k],v,rtol=2e-7,atol=2e-8,equal_nan=True)
    view_manifest=read('current_view_manifest.json');input_hashes(view_manifest)
    html_path=track(base/'current_view.html',view_manifest['html_sha256']);html=html_path.read_text()
    blob=base64.b64decode(re.search(r'<script id="payload"[^>]*>(.*?)</script>',html,re.S).group(1))
    decoded=gzip.decompress(blob);assert hashlib.sha256(decoded).hexdigest()==view_manifest['decoded_json_sha256']
    payload=json.loads(decoded)
    for key,table in [('records',science),('objects',objects),('contact_index',index)]:
        expected=[{k:js_value(v) for k,v in r.items()} for r in table.to_dict('records')]
        assert decode_columnar(payload[key])==expected,('HTML changed field',key)
    assert payload['summary']==summary
    annotations=verify_viewer_annotations(payload,science,root);verified.update(annotations['verified_file_sha256'])
    assert view_manifest['classification_annotation_rows']==[r['row_index'] for r in payload['classification_context']['records']]
    node=shutil.which('node');assert node,'Node is required for the committed native-JavaScript viewer verification'
    checked=subprocess.run([node,str(track(base/'check_viewer.js')),str(html_path)],cwd='/tmp',capture_output=True,text=True,check=True)
    node_result=json.loads(checked.stdout);assert node_result['status']=='PASS'
    assert node_result['classification_annotation_rows_checked']==annotations['annotation_rows_checked']==5
    assert node_result['annotation_source_ids_and_original_fields_verified']
    track(base/'science_colour_plane.png',view_manifest['science_colour_plane_sha256'])
    display=read('display_review.json')
    assert sum(r['panels_actually_viewed'] for r in display['images'])==8
    for r in display['images']:
        track(base/r['file'],r['sha256']);assert len(r['observations'])==r['panels_actually_viewed']
    for name in ['fetch_and_identify.py','compact_inputs.py','overlay.py','build_current.py','native_quality_audit.py','build_science_view.py','build_view.py','merge_visual_reviews.py','j1323_audit.py','verify_outputs.py']:
        track(base/name)
    for name in ['README.md','j1323/README.md','j1323/colour_metrics.csv','j1323/comparisons.csv',
                 'retrieval_all.jsonl','retrieval_plan_all.json','search_ledger.csv','catalogue_observations.csv']:
        track(base/name)
    result={'status':'PASS','summary':{'frozen_records':9902,'frozen_entity_keys':6003,
        'previously_unresolved_records_rechecked':1579,'query_successful_batches':79,'historical_failed_batches_retained':79,
        'raw_SHA_logged_inputs':3719,'lossless_numerical_inputs_replayed':3719,'native_identity_pairs_recomputed':2175,
        'new_Fnu_records':178,'new_Flambda_records':435,'still_unit_unresolved_records':966,
        'new_native_support_audited_records':613,'new_native_supported_colours':601,'new_colour_withheld_records':12,
        'current_eligible_records':8074,'current_strong_records':419,'current_strong_entity_keys':324,
        'outside_native_audit_prior_eligible_records_retained':7473,'actually_viewed_new_entities':613,'actually_viewed_fixed_images':39,
        'previously_unavailable_units_resolved':115,'previously_unavailable_native_supported_colours':112,
        'J1323_original_input_replay':True,'viewer_native_JavaScript':node_result['status'],
        'viewer_separate_classification_annotations_checked':annotations['annotation_rows_checked'],
        'original_raw_or_query_cache_required':False,'network_required':False},
        'checked_files':len(verified),'verified_file_sha256':dict(sorted(verified.items()))}
    return result


if __name__=='__main__':
    result=verify();(HERE/'verification_summary.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'status':result['status'],'checked_files':result['checked_files'],**result['summary']},indent=2))
