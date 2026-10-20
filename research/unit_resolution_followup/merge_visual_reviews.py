#!/usr/bin/env python3
"""Bind actually viewed panel notes to immutable image and row identities."""
from __future__ import annotations
import csv
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def records(path):
    with Path(path).open(newline='') as f:return list(csv.DictReader(f))

def build():
    index=records(OUT/'contact_sheet_index.csv')
    by_panel={(int(r['page']),int(r['panel'])):r for r in index}
    source=json.loads((OUT/'visual_notes_01_20.json').read_text())
    first=[]
    for page in range(1,21):
        note=source['page_notes'][str(page)]
        assert len(note['observations'])==16
        actual=sha(OUT/f'contact_sheets/page_{page:02d}.png')
        assert actual==note['image_sha256']
        for panel,observation in enumerate(note['observations'],1):
            entry=by_panel[page,panel];assert actual==entry['contact_sheet_sha256']
            first.append({key:entry[key] for key in ['page','panel','entity_id','row_index','contact_sheet_sha256']}|
                {'visual_status':'actually_viewed_frozen_compatibility_spectrum','observation':observation,
                 'evidence_limits':'Actually opened this fixed page and inspected this panel. The 40 A mean can dilute narrow features; grey is native min/max, not an error band. Approximate wavelengths are visual locators, not fitted line positions. Negative pixels remain visible. These frozen compatibility-recipe Duv values precede the new native-IVAR support gate. Unit proof, physical association, calibration, pixel quality and novelty remain separate.',
                 'review_agent':'repro_audit','recorded_utc_date':'2026-10-20'})
    fields=['page','panel','entity_id','row_index','contact_sheet_sha256','visual_status','observation','evidence_limits','review_agent','recorded_utc_date']
    with (OUT/'visual_review_01_20.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fields);writer.writeheader();writer.writerows(first)
    combined=first+records(OUT/'root_visual_review_21_30.csv')+records(OUT/'external_visual_review_31_39.csv')
    assert len(combined)==613
    assert len({r['entity_id'] for r in combined})==613
    assert len({int(r['row_index']) for r in combined})==613
    for r in combined:
        page,panel=int(r['page']),int(r['panel']);target=by_panel[page,panel]
        assert all(str(r[key])==str(target[key]) for key in ['entity_id','row_index','contact_sheet_sha256'])
        assert all(r.get(key,'').strip() for key in ['observation','visual_status','evidence_limits'])
        if not r.get('review_agent'):r['review_agent']='external_validation' if page>=31 else 'root'
        r.setdefault('recorded_utc_date','2026-10-20')
    combined.sort(key=lambda r:(int(r['page']),int(r['panel'])))
    assert set(by_panel)=={(int(r['page']),int(r['panel'])) for r in combined}
    with (OUT/'individual_review.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fields);writer.writeheader();writer.writerows(combined)
    md=['# 追加単位確定スペクトルの個別視認台帳','',
        '39 枚を実際に開き、613 記録 / 613 天体を個別に確認した。画像生成、画素照合、実際の画像閲覧は別の工程として記録している。',
        '', 'この固定画像は単位修正後・旧 gate 互換の表示であり、native IVAR による支持監査後の現行色は `science_record_view.csv.gz` を参照する。灰色は各 40 Å 区間の native min/max であり、誤差帯ではない。波長の目測は線同定でも位置測定でもない。',
        '', '| Page / panel | Row | Entity | Reviewer | Individual observation |', '|---|---:|---|---|---|']
    for r in combined:md.append(f"| {r['page']} / {r['panel']} | {r['row_index']} | {r['entity_id']} | {r['review_agent']} | {r['observation'].replace('|','/')} |")
    (OUT/'individual_review.md').write_text('\n'.join(md)+'\n')
    sources=[OUT/'visual_notes_01_20.json',OUT/'visual_review_01_20.csv',OUT/'root_visual_review_21_30.csv',OUT/'external_visual_review_31_39.csv',OUT/'contact_sheet_index.csv',OUT/'contact_sheet_manifest.json']
    summary={'complete':True,'actually_opened_fixed_images':39,'individually_viewed_records':613,
        'individually_viewed_entities':613,'duplicate_row_or_entity_notes':0,
        'previously_unavailable_entities_with_new_unit_evidence_viewed':sum(r['previously_unavailable_panel']=='True' for r in index),
        'reviewer_counts':{name:sum(r['review_agent']==name for r in combined) for name in ['repro_audit','root','external_validation']},
        'reviewed_image_stage':'Frozen unit-resolved compatibility recipe before native-IVAR support gate; not a claim of current colour eligibility.',
        'limits':'A displayed curve can be inspected while its physical colour is later withheld. The 613 reviews include low S/N and invalid-support cases; inspection does not certify calibration, association, classification, feature significance or novelty.',
        'input_sha256':{str(p.relative_to(ROOT)):sha(p) for p in sources},
        'output_sha256':{p.name:sha(p) for p in [OUT/'individual_review.csv',OUT/'individual_review.md']},
        'image_sha256':{r['contact_sheet']:r['contact_sheet_sha256'] for r in index}}
    assert summary['previously_unavailable_entities_with_new_unit_evidence_viewed']==115
    (OUT/'review_completion.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps({k:v for k,v in summary.items() if not k.endswith('sha256')},indent=2))

if __name__=='__main__':build()
