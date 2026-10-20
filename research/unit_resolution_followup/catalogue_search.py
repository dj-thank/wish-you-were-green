#!/usr/bin/env python3
"""Enumerate public SDSS observations for the frozen unresolved MWDD inputs.

A cone hit is a candidate reference, never a unit or astrophysical association.
The initial raw-retrieval priority is the 300 previously unavailable entities
with unresolved SDSS inputs, plus the withdrawn J1323 comparison record.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import argparse
import gzip
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
SERVICE = 'https://skyserver.sdss.org/dr17/SkyServerWS/SearchTools/SqlSearch'
RADIUS_ARCMIN = 0.5


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def census():
    regpath = ROOT / 'research/precision/flux_convention_evidence.json'
    frozenpath = ROOT / 'results/screen_input_mwdd.json.gz'
    indexpath = ROOT / 'research/outlier_followup/contact_sheet_index.csv'
    reg = json.loads(regpath.read_text())
    with gzip.open(frozenpath, 'rt') as stream: frozen = json.load(stream)
    index = pd.read_csv(indexpath, dtype={'source_id': str})
    unavailable = set(index.loc[index.plotted_records.eq(0), 'entity_id'])
    rows = []
    for entry in reg['records']:
        if entry['convention'] != 'unresolved': continue
        i = entry['mwdd_row_index']; r = frozen[i]
        rows.append({'mwdd_row_index': i, 'entity_id': entry['entity_id'],
            'source_id': r.get('source_id', ''), 'name': r['wdid'],
            'ra_deg': r.get('ra_deg'), 'dec_deg': r.get('dec_deg'),
            'old_reference_pairs': entry['reference_pairs_assessed'],
            'previously_unavailable_panel': entry['entity_id'] in unavailable,
            'priority_raw_retrieval': entry['entity_id'] in unavailable or i == 13,
            'priority_reason': 'previously_unavailable_panel' if entry['entity_id'] in unavailable else 'withdrawn_J1323' if i == 13 else 'metadata_enumeration_only_initial_stage',
            'mwdd_sha256': r['sha256'], 'mwdd_source_url': r['source_url'],
            'old_raw_path': r['raw_path'], 'mwdd_wave_min_A': r.get('wave_min_angstrom'),
            'mwdd_wave_max_A': r.get('wave_max_angstrom'), 'mwdd_samples': r.get('npoints')})
    frame = pd.DataFrame(rows).sort_values('mwdd_row_index')
    frame.to_csv(OUT / 'unresolved_universe.csv', index=False, float_format='%.17g')
    manifest = {'selected_from_frozen_unresolved_records': len(frame),
        'prior_no_reference_records': int(frame.old_reference_pairs.eq(0).sum()),
        'prior_nonidentity_reference_records': int(frame.old_reference_pairs.gt(0).sum()),
        'previously_unavailable_entities': int(frame.loc[frame.previously_unavailable_panel, 'entity_id'].nunique()),
        'priority_raw_records': int(frame.priority_raw_retrieval.sum()),
        'cone_radius_arcmin': RADIUS_ARCMIN,
        'method': 'All SpecObjAll observations within 30 arcsec of the retained input coordinates; no sciencePrimary, spectral-class or colour filter. Candidate enumeration only: native-pixel identity will be required separately.',
        'limits': 'Finite search radius and retained-coordinate epochs can miss high-proper-motion observations. A positional hit does not validate the astrophysical association, original archive label or spectral-density units.',
        'input_sha256': {str(p.relative_to(ROOT)): sha(p) for p in [regpath, frozenpath, indexpath]},
        'script_sha256': sha(__file__)}
    (OUT / 'selection.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps(manifest, indent=2), flush=True)
    return frame


def query_batch(rows):
    fields = []
    for r in rows:
        fields.append(f"({r['mwdd_row_index']},{r['ra_deg']:.12f},{r['dec_deg']:.12f})")
    query = ('SELECT q.row_index,CAST(s.specObjID AS varchar(32)) AS specobjid,s.plate,s.mjd,s.fiberID,'
        's.run2d,s.ra,s.dec,s.sciencePrimary,CAST(s.bestObjID AS varchar(32)) AS bestobjid,n.distance '
        'FROM (VALUES ' + ','.join(fields) + f') q(row_index,query_ra,query_dec) CROSS APPLY dbo.fGetNearbySpecObjAllEq(q.query_ra,q.query_dec,{RADIUS_ARCMIN}) n '
        'JOIN SpecObjAll s ON s.specObjID=n.specObjID')
    tag = hashlib.sha256(query.encode()).hexdigest()[:20]
    folder = OUT / 'queries'; folder.mkdir(exist_ok=True)
    sqlpath, rawpath, metapath = [folder / f'{tag}{suffix}' for suffix in ['.sql', '.json', '.provenance.json']]
    if rawpath.exists() and metapath.exists():
        meta = json.loads(metapath.read_text())
        if meta.get('status') == 'ok' and meta['sha256'] == sha(rawpath):
            data = json.loads(rawpath.read_text())
            return meta, [r for t in data for r in t.get('Rows', []) if 'row_index' in r]
    sqlpath.write_text(query + '\n')
    meta = {'row_indices': [r['mwdd_row_index'] for r in rows], 'query': query,
            'radius_arcmin': RADIUS_ARCMIN, 'status': 'failed'}
    for attempt in range(2):
        try:
            response = requests.get(SERVICE, params={'cmd': query, 'format': 'json'}, timeout=(15, 45))
            rawpath.write_bytes(response.content)
            meta.update(url=response.url, http_status=response.status_code,
                        sha256=sha(rawpath), bytes=len(response.content),
                        retrieved_utc=datetime.now(timezone.utc).isoformat(), attempts=attempt + 1)
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, list) or not all(isinstance(t, dict) and 'Rows' in t for t in data):
                raise ValueError('Unexpected SQL response schema: ' + str(data)[:400])
            result = [r for t in data for r in t['Rows'] if 'row_index' in r]
            meta.update(status='ok', observation_rows=len(result))
            meta.pop('error', None)
            metapath.write_text(json.dumps(meta, indent=2) + '\n')
            return meta, result
        except Exception as exc:
            meta['error'] = str(exc)
    metapath.write_text(json.dumps(meta, indent=2) + '\n')
    return meta, []


def run_queries():
    frame = census()
    valid = frame[np.isfinite(frame.ra_deg) & np.isfinite(frame.dec_deg)]
    rows = valid.to_dict('records')
    batches = [rows[start:start + 20] for start in range(0, len(rows), 20)]
    first, first_rows = query_batch(batches[0])
    if first['status'] != 'ok':
        raise RuntimeError('First batch failed; stop before issuing the remaining batches: ' + first.get('error', ''))
    metadata, observations = [first], list(first_rows)
    with ThreadPoolExecutor(max_workers=2) as pool:
        for n, future in enumerate(as_completed([pool.submit(query_batch, b) for b in batches[1:]]), 2):
            meta, result = future.result(); metadata.append(meta); observations.extend(result)
            if n % 10 == 0 or meta['status'] != 'ok':
                print('query batches', n, '/', len(batches), 'observations', len(observations), 'last status', meta['status'], flush=True)
    observations.sort(key=lambda r: (r['row_index'], r['plate'], r['mjd'], r['fiberID'], r['run2d']))
    (OUT / 'catalogue_observations.json').write_text(json.dumps(observations, indent=2) + '\n')
    pd.DataFrame(observations).to_csv(OUT / 'catalogue_observations.csv', index=False, float_format='%.17g')
    failed = {i for m in metadata if m['status'] != 'ok' for i in m['row_indices']}
    hits = {r['row_index'] for r in observations}
    frame['catalogue_status'] = ['query_failed' if i in failed else 'candidate_observations_found' if i in hits else 'no_observation_within_retained_coordinate_cone' if i in set(valid.mwdd_row_index) else 'invalid_retained_coordinates' for i in frame.mwdd_row_index]
    frame['catalogue_observations'] = frame.mwdd_row_index.map(pd.Series([r['row_index'] for r in observations]).value_counts()).fillna(0).astype(int)
    frame.to_csv(OUT / 'search_ledger.csv', index=False, float_format='%.17g')
    summary = {'query_batches': len(metadata), 'successful_batches': sum(m['status'] == 'ok' for m in metadata),
        'status_counts': frame.catalogue_status.value_counts().to_dict(),
        'catalogue_observation_rows': len(observations),
        'priority_records_with_observations': int((frame.priority_raw_retrieval & frame.mwdd_row_index.isin(hits)).sum()),
        'priority_observation_rows': sum(r['row_index'] in set(frame.loc[frame.priority_raw_retrieval, 'mwdd_row_index']) for r in observations),
        'batch_provenance_files': [str(p.relative_to(OUT)) for p in sorted((OUT / 'queries').glob('*.provenance.json'))]}
    (OUT / 'catalogue_summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('command', choices=['census', 'query'])
    args = parser.parse_args()
    census() if args.command == 'census' else run_queries()
