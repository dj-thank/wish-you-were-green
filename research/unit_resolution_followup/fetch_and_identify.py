#!/usr/bin/env python3
"""Fetch bounded original references and add strict flux-convention evidence.

No existing registry, screen or historical image is changed. New SDSS reference
IDs are separate from the immutable 0-based 9902-row input indices.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import argparse
import collections
import csv
import gzip
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import re
import sys
import threading

import numpy as np
import pandas as pd
import requests
from astropy.io import fits

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
CACHE = OUT / 'raw_cache'
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location('original_identity', ROOT / 'research/precision/flux_convention_audit.py')
native = importlib.util.module_from_spec(spec); spec.loader.exec_module(native)
THREAD = threading.local()
MAX_FILE_BYTES = 2_000_000


def sha(blob): return hashlib.sha256(blob).hexdigest()


def inputs():
    output = []
    for origin in ['mwdd', 'sdss']:
        with gzip.open(ROOT / f'results/screen_input_{origin}.json.gz', 'rt') as stream:
            output.extend((origin, row) for row in json.load(stream))
    return output


def reference_key(row):
    run = str(row['run2d']).strip()
    if not re.fullmatch(r'[A-Za-z0-9_.]+', run): raise ValueError('Unexpected pipeline identifier')
    return f"sdss_dr17_{run}_{int(row['plate']):04d}_{int(row['mjd'])}_{int(row['fiberID']):04d}"


def reference_url(row):
    run = str(row['run2d']).strip()
    reference_key(row)
    branch = 'eboss' if run.startswith('v') else 'sdss'
    plate, mjd, fiber = int(row['plate']), int(row['mjd']), int(row['fiberID'])
    return f'https://data.sdss.org/sas/dr17/{branch}/spectro/redux/{run}/spectra/lite/{plate:04d}/spec-{plate:04d}-{mjd}-{fiber:04d}.fits'


def plan(scope):
    universe = pd.read_csv(OUT / 'unresolved_universe.csv', dtype={'source_id': str})
    selected = universe[universe.priority_raw_retrieval] if scope == 'priority' else universe
    if scope == 'pilot': selected = universe[universe.mwdd_row_index.eq(13)]
    keys = set(selected.mwdd_row_index)
    obs = json.loads((OUT / 'catalogue_observations.json').read_text())
    chosen = [r for r in obs if r['row_index'] in keys]
    frozen = inputs()
    jobs = []
    for r in selected.itertuples():
        jobs.append({'key': f'mwdd_{r.mwdd_row_index}', 'format': 'mwdd',
            'mwdd_row_indices': [int(r.mwdd_row_index)], 'source_url': r.mwdd_source_url,
            'expected_sha256': r.mwdd_sha256, 'raw_path': f'raw_cache/mwdd_{r.mwdd_row_index}.csv',
            'old_raw_path': r.old_raw_path})
    grouped = collections.defaultdict(list)
    for row in chosen: grouped[reference_key(row)].append(row)
    direct_frozen = {r['source_url']: r for origin, r in frozen if origin == 'sdss'}
    for key, group in sorted(grouped.items()):
        row = group[0]; url = reference_url(row)
        old = direct_frozen.get(url)
        jobs.append({'key': key, 'format': 'sdss', 'source_url': url,
            'raw_path': 'raw_cache/' + key + '.fits',
            'mwdd_row_indices': sorted(set(int(r['row_index']) for r in group)),
            'catalogue_observation': row,
            'expected_sha256': old['sha256'] if old else None,
            'old_raw_path': old['raw_path'] if old else None})
    payload = {'scope': scope, 'selected_mwdd_records': len(selected),
        'selected_entities': int(selected.entity_id.nunique()),
        'sdss_candidate_references': len(grouped), 'jobs': jobs,
        'query_output_sha256': sha((OUT / 'catalogue_observations.json').read_bytes()),
        'universe_sha256': sha((OUT / 'unresolved_universe.csv').read_bytes()),
        'per_file_max_bytes': MAX_FILE_BYTES, 'concurrency': 4}
    (OUT / f'retrieval_plan_{scope}.json').write_text(json.dumps(payload, indent=2) + '\n')
    return payload


def parse_original(blob, job):
    if job['format'] == 'mwdd':
        lines = blob.decode('utf-8', 'replace').splitlines()
        names = [v.strip() for v in next(csv.reader([lines[1]]))]
        array = np.loadtxt(io.StringIO('\n'.join(lines[2:])), delimiter=',', ndmin=2)
        data = {name: array[:, i] for i, name in enumerate(names)}
        raw = {'wave': data['wavelength'], 'flux': data['flux'], 'header': lines[0], 'columns': names}
        iv = data.get('ivar')
        if 'sigma' in data:
            s = data['sigma']; iv = np.divide(1, s*s, out=np.zeros_like(s), where=np.isfinite(s) & (s > 0))
        raw['ivar'] = iv
    else:
        with fits.open(io.BytesIO(blob), memmap=False) as hd:
            data = hd[1].data
            header = {k: hd[0].header.get(k) for k in ['BUNIT', 'PLATEID', 'MJD', 'FIBERID', 'RUN2D', 'PLUG_RA', 'PLUG_DEC', 'VACUUM']}
            raw = {'wave': 10**np.asarray(data['loglam'], float),
                   'flux': np.asarray(data['flux'], float) * 1e-17,
                   'ivar': np.asarray(data['ivar'], float) / 1e-34, 'header': header}
            if header['BUNIT'] != '1E-17 erg/cm^2/s/Ang': raise ValueError('Unexpected FITS BUNIT')
            target = job['catalogue_observation']
            for a, b in [('PLATEID', 'plate'), ('MJD', 'mjd'), ('FIBERID', 'fiberID')]:
                if int(header[a]) != int(target[b]): raise ValueError('FITS observation identity differs from queried ID')
    raw['raw_sha256_verified'] = True
    return raw


def fetch_one(job):
    path = OUT / job['raw_path']
    result = {**job, 'status': 'failed', 'attempts': []}
    candidates = [path]
    if job.get('old_raw_path'): candidates.append(ROOT / job['old_raw_path'])
    for cached in candidates:
        if not cached.is_file(): continue
        blob = cached.read_bytes(); digest = sha(blob)
        if job['expected_sha256'] is not None and digest != job['expected_sha256']:
            if cached == path: raise ValueError('Previously saved exact input changed: ' + str(path))
            continue
        # Newly acquired references can be reused only under their previous URL/SHA log.
        if job['expected_sha256'] is None:
            old_log = path.with_suffix(path.suffix + '.provenance.json')
            if not old_log.is_file(): continue
            old = json.loads(old_log.read_text())
            if old['sha256'] != digest or old['source_url'] != job['source_url']: continue
        raw = parse_original(blob, job)
        if cached != path: path.write_bytes(blob)
        result.update(status='verified', sha256=digest, bytes=len(blob), raw_header=raw['header'], cached=True)
        break
    if result['status'] != 'verified':
        if not hasattr(THREAD, 'session'):
            THREAD.session = requests.Session()
            THREAD.session.headers['User-Agent'] = 'public-scientific-reproduction/1.0'
        for n in range(2):
            try:
                with THREAD.session.get(job['source_url'], timeout=(15, 40), stream=True) as response:
                    response.raise_for_status(); chunks = []; count = 0
                    for block in response.iter_content(131072):
                        count += len(block)
                        if count > MAX_FILE_BYTES: raise ValueError('Original exceeds 2 MB retrieval bound')
                        chunks.append(block)
                    blob = b''.join(chunks)
                digest = sha(blob)
                if job['expected_sha256'] and digest != job['expected_sha256']:
                    raise ValueError('Retrieved bytes differ from frozen SHA: ' + digest)
                raw = parse_original(blob, job)
                path.write_bytes(blob)
                result.update(status='verified', sha256=digest, bytes=len(blob), raw_header=raw['header'],
                    retrieved_utc=datetime.now(timezone.utc).isoformat(), final_url=response.url, cached=False)
                break
            except Exception as exc:
                result['attempts'].append({'attempt': n + 1, 'error': str(exc)})
                if isinstance(exc, requests.HTTPError) and exc.response.status_code in [404, 410]: break
    if result['status'] == 'verified':
        path.with_suffix(path.suffix + '.provenance.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


def fetch(scope):
    CACHE.mkdir(exist_ok=True)
    payload = plan(scope)
    print(json.dumps({k: v for k, v in payload.items() if k != 'jobs'}, indent=2), flush=True)
    completed = []
    with (OUT / f'retrieval_{scope}.jsonl').open('w') as stream, ThreadPoolExecutor(max_workers=4) as pool:
        for n, future in enumerate(as_completed([pool.submit(fetch_one, j) for j in payload['jobs']]), 1):
            row = future.result(); completed.append(row)
            stream.write(json.dumps(row) + '\n'); stream.flush()
            if n % 50 == 0 or row['status'] != 'verified':
                print('raw inputs', n, '/', len(payload['jobs']), 'failures', sum(x['status'] != 'verified' for x in completed), flush=True)
    completed.sort(key=lambda r: r['key'])
    summary = {'scope': scope, 'raw_inputs': len(completed), 'verified': sum(r['status'] == 'verified' for r in completed),
        'failed': sum(r['status'] != 'verified' for r in completed), 'bytes': sum(r.get('bytes', 0) for r in completed),
        'records': completed}
    (OUT / f'retrieval_{scope}.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps({k: v for k, v in summary.items() if k != 'records'}, indent=2), flush=True)


def identify(scope):
    frozen = inputs()
    retrieval = json.loads((OUT / f'retrieval_{scope}.json').read_text())
    records = retrieval['records']; by_key = {r['key']: r for r in records}
    universe = pd.read_csv(OUT / 'unresolved_universe.csv', dtype={'source_id': str}).set_index('mwdd_row_index')
    direct = sorted([r for r in records if r['format'] == 'sdss'], key=lambda r: r['key'])
    association = {(int(r['row_index']), reference_key(r)): r for r in
                   json.loads((OUT / 'catalogue_observations.json').read_text())}
    raw = {}
    for record in records:
        if record['status'] != 'verified': continue
        blob = (OUT / record['raw_path']).read_bytes()
        if sha(blob) != record['sha256']: raise ValueError('Saved original SHA mismatch')
        raw[record['key']] = parse_original(blob, record)
    pairs, resolved = [], []
    for mw in [r for r in records if r['format'] == 'mwdd']:
        i = mw['mwdd_row_indices'][0]; u = universe.loc[i]; original = frozen[i][1]
        references = [(j, r) for j, r in enumerate(direct) if i in r['mwdd_row_indices']]
        evidence = []
        for j, ref in references:
            if mw['key'] not in raw or ref['key'] not in raw: continue
            first = {'row_index': i, 'entity_id': u.entity_id, 'wdid': original['wdid'],
                'source_url': original['source_url'], 'sha256': mw['sha256']}
            second = {'row_index': -j-1, 'source_url': ref['source_url'], 'sha256': ref['sha256']}
            pair = native.compare(first, second, raw[mw['key']], raw[ref['key']])
            pair.update(direct_row_index=None, reference_index=j, external_reference_id=ref['key'],
                direct_index_note='New reference; not a row of the frozen 9902-record input',
                cone_distance_arcsec=60 * association[(int(i), ref['key'])]['distance'])
            pairs.append(pair); evidence.append(pair)
        accepted = [r for r in evidence if r['convention'] in ['fnu', 'flambda']]
        conventions = {r['convention'] for r in accepted}
        convention = next(iter(conventions)) if len(conventions) == 1 else 'unresolved'
        selected = min(accepted, key=lambda r: r[r['convention'] + '_max_fractional_shape_residual']) if convention != 'unresolved' else None
        row = {'mwdd_row_index': int(i), 'mwdd_sha256': original['sha256'], 'entity_id': u.entity_id,
            'source_id': str(u.source_id), 'name': original['wdid'], 'convention': convention,
            'previous_convention': 'unresolved', 'reference_pairs_assessed': len(evidence),
            'candidate_references': len(references), 'accepted_reference_pairs': len(accepted),
            'previously_unavailable_panel': bool(u.previously_unavailable_panel),
            'disposition': 'resolved_strict_native_identity' if selected else 'conflicting_reference_conventions' if len(conventions) > 1 else 'mwdd_original_unavailable' if mw['key'] not in raw else 'no_catalogue_reference_within_search_cone' if not references else 'no_reference_identity_passed',
            'external_reference_id': selected['external_reference_id'] if selected else None,
            'direct_sha256': selected['direct_sha256'] if selected else None,
            'direct_row_index': None,
            'astrophysical_association_note': 'Spectrum representation identity only; positional catalogue association and physical class are not established by this unit test.'}
        if selected:
            row['selected_identity_evidence'] = selected
        resolved.append(row)
    resolved.sort(key=lambda r: r['mwdd_row_index'])
    summary = {'scope': scope, 'selected_mwdd_records': len(resolved), 'reference_pairs_assessed': len(pairs),
        'conventions': dict(collections.Counter(r['convention'] for r in resolved)),
        'dispositions': dict(collections.Counter(r['disposition'] for r in resolved)),
        'newly_verified_previous_unavailable_entities': len({r['entity_id'] for r in resolved if r['convention'] != 'unresolved' and r['previously_unavailable_panel']}),
        'existing_registry_modified': False, 'thresholds': native.THRESHOLDS,
        'input_sha256': {str(p.relative_to(ROOT)): sha(p.read_bytes()) for p in [OUT / f'retrieval_{scope}.json', OUT / 'catalogue_observations.json', OUT / 'unresolved_universe.csv', ROOT / 'research/precision/flux_convention_evidence.json']},
        'script_sha256': sha(Path(__file__).read_bytes())}
    payload = {'summary': summary, 'records': resolved, 'pair_evidence': pairs}
    (OUT / f'unit_evidence_{scope}.json').write_text(json.dumps(payload, indent=2) + '\n')
    pd.DataFrame([{k: v for k, v in r.items() if k != 'selected_identity_evidence'} for r in resolved]).to_csv(OUT / f'unit_evidence_{scope}.csv', index=False)
    print(json.dumps(summary, indent=2), flush=True)
    for row in resolved:
        if row['mwdd_row_index'] == 13: print('J1323', json.dumps(row, indent=2), flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('command', choices=['fetch', 'identify'])
    p.add_argument('--scope', choices=['pilot', 'priority', 'all'], default='priority')
    args = p.parse_args()
    fetch(args.scope) if args.command == 'fetch' else identify(args.scope)
