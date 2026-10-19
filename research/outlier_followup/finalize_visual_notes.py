#!/usr/bin/env python3
"""Bind manually authored, actually viewed panel notes to immutable image hashes."""
import csv
import hashlib
import json
from pathlib import Path

OUT=Path(__file__).resolve().parent
LIMITS=('Visual description of 20-A display means and retained native ranges only; '
        'not a line identification or a determination of instrumental/astrophysical cause. '
        'Supplied error bands omit XP covariance and calibration uncertainty; archive records may share an observation.')

def main():
    notes=json.loads((OUT/'visual_notes_01_63.json').read_text())
    index=list(csv.DictReader((OUT/'contact_sheet_index.csv').open()))
    rows=[]
    for page,observations in notes.items():
        subset=[r for r in index if int(r['page'])==int(page)]
        assert len(observations)==len(subset), (page,len(observations),len(subset))
        path=OUT/subset[0]['contact_sheet']
        digest=hashlib.sha256(path.read_bytes()).hexdigest()
        assert all(r['contact_sheet_sha256']==digest for r in subset)
        for item,note in zip(subset,observations):
            rows.append({'page':int(page),'panel':int(item['panel']),'entity_id':item['entity_id'],
                'visual_status':'viewed_current_flambda_spectrum' if int(item['plotted_records']) else 'viewed_explicit_unavailable_panel',
                'observation':note,'evidence_limits':LIMITS,
                'contact_sheet_sha256':digest})
    rows.sort(key=lambda r:(r['page'],r['panel']))
    assert len({r['entity_id'] for r in rows})==len(rows)
    with (OUT/'visual_review_01_63.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    text=['# Individual visual review: pages 1–63','',
          f'{len(rows)} panels have actually been displayed and individually described. The CSV carries the exact image SHA for every entry.',
          '',LIMITS,'',
          '| Page | Panel | Entity | Observation |','|---:|---:|---|---|']
    text.extend(f"| {r['page']} | {r['panel']} | {r['entity_id']} | {r['observation']} |" for r in rows)
    (OUT/'visual_review_01_63.md').write_text('\n'.join(text)+'\n')
    print(f'Saved {len(rows)} individually viewed panels across {len(notes)} pages.')

if __name__=='__main__':main()
