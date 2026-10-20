"""Read-only verification of the committed per-object visual-review evidence.

Original survey caches are deliberately not required. This verifies recorded
provenance, membership, numerical reproduction results and per-image notes;
it does not repeat visual inspection or reconstruct missing detector data.
"""
from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


def verify(root):
    root = Path(root).resolve()
    base = root / 'research/outlier_followup'
    checked = {}

    def require(condition, message):
        if not condition:
            raise AssertionError('Outlier follow-up: ' + message)

    def hashed(path, expected=None):
        path = Path(path).resolve()
        require(path.is_relative_to(root) and path.is_file(), 'Missing committed evidence: ' + str(path))
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        require(expected is None or expected == digest, 'SHA mismatch: ' + str(path.relative_to(root)))
        checked[str(path.relative_to(root))] = digest
        return path

    def read_json(path, expected=None):
        return json.loads(hashed(path, expected).read_text())

    def csv(path):
        return pd.read_csv(hashed(path), dtype={'source_id': 'string', 'entity_id': 'string'}, low_memory=False)

    done = read_json(base / 'review_completion.json')
    require(done['complete'] is True, 'Review is incomplete')
    require((done['entity_count'], done['record_count'], done['reviewed_main_pages']) == (2007, 4370, 126), 'Completion counts differ')
    for path, digest in done['input_sha256'].items():
        hashed(root / path, digest)
    for path, digest in done['output_sha256'].items():
        hashed(base / path, digest)
    hashed(base / 'complete_review.py', done['code_sha256'])
    historical = csv(root / 'research/outlier_audit/review_queue.csv')
    previous = csv(root / 'research/outlier_audit/contact_sheet_index.csv')
    queue = csv(base / 'queue_entities.csv')
    index = csv(base / 'contact_sheet_index.csv')
    records = csv(base / 'record_review.csv.gz')
    dispositions = csv(base / 'record_dispositions.csv')
    individual = csv(base / 'individual_review.csv')
    current = csv(root / 'research/precision/flux_units/corrected_record_screen.csv.gz')
    require(len(historical) == 2344 and historical.entity_id.is_unique, 'Historical queue changed')
    require(len(previous) == 337 and previous.entity_id.is_unique, 'Previously reviewed set changed')
    require(set(previous.entity_id) <= set(historical.entity_id), 'Previous set is not a subset')
    expected_entities = set(historical.entity_id) - set(previous.entity_id)
    for name, frame in [('queue', queue), ('index', index), ('individual notes', individual)]:
        require(len(frame) == 2007 and frame.entity_id.is_unique and set(frame.entity_id) == expected_entities,
                'Missing or repeated entity in ' + name)
    require(individual.review_state.eq('individually_viewed').all(), 'An individual review is unfinished')
    require(index.followup_index.tolist() == list(range(2007)), 'Index sequence differs')
    require((index.page == index.followup_index // 16 + 1).all() and
            (index.panel == index.followup_index % 16 + 1).all(), 'Panel placement differs')

    expected_records = current[current.entity_id.isin(expected_entities)].set_index('row_index')
    require(len(records) == 4370 and records.row_index.is_unique and set(records.row_index) == set(expected_records.index),
            'Original record membership differs')
    r = records.set_index('row_index').sort_index()
    expected_records = expected_records.reindex(r.index)
    for field in ['entity_id', 'source_id', 'source_url', 'sha256', 'status', 'usable_screen', 'flux_units_validated']:
        require(r[field].fillna('').eq(expected_records[field].fillna('')).all(), 'Current record identity/status differs: ' + field)
    for field in ['u1960', 'v1960', 'distance_planck_uv']:
        np.testing.assert_allclose(r[field], expected_records[field], rtol=0, atol=1e-12, equal_nan=True, err_msg=field)
    eligible = r.usable_screen.eq(True) & r.status.eq('ok') & r.flux_units_validated.eq(True) & np.isfinite(r.u1960) & np.isfinite(r.v1960)
    plotted = r.plot_status.eq('plotted_verified_flambda')
    require(eligible.eq(plotted).all() and eligible.eq(r.eligible_for_plot).all() and int(plotted.sum()) == 3041,
            'Unknown-unit or otherwise ineligible spectrum was plotted, or an eligible spectrum was lost')
    expected_statuses = {'plotted_verified_flambda': 3041, 'withheld_unverified_flux_units': 1305,
                         'withheld_current_eligibility_gate': 23, 'withheld_processing_error': 1}
    require(r.plot_status.value_counts().to_dict() == expected_statuses == done['plot_status_counts'], 'Disposition counts differ')
    require(r.loc[plotted, 'current_recomputed_delta_uv'].between(0, 1e-7).all(), 'Recorded unbinned reproduction failed')
    require(np.isfinite(r.loc[plotted, 'normalizer_flam']).all() and r.loc[plotted, 'normalizer_flam'].gt(0).all(),
            'Invalid display normalization')
    require(len(dispositions) == 4370 and dispositions.row_index.is_unique and set(dispositions.row_index) == set(r.index),
            'Detailed disposition ledger is incomplete')
    detail = dispositions.set_index('row_index').reindex(r.index)
    require(detail.plot_status.eq(r.plot_status).all() and detail.entity_id.eq(r.entity_id).all(), 'Detailed disposition mapping differs')
    require(detail.disposition_detail.fillna('').str.len().gt(15).all(), 'Missing explicit disposition reason')
    gate = r[r.plot_status.eq('withheld_current_eligibility_gate')]
    require(int(gate.largest_visible_gap_A.ge(150).sum()) == 19 and int(gate.coverage_eligible.eq(False).sum()) == 4,
            'Documented eligibility failure reasons differ')

    generation = read_json(base / 'generation_manifest.json')
    require(len(generation['pages_manifest']) == 126, 'Image manifest is incomplete')
    for page in generation['pages_manifest']:
        hashed(base / page['path'], page['sha256'])
        block = index[index.page.eq(page['page'])]
        require(len(block) == page['entity_count'] and block.contact_sheet_sha256.eq(page['sha256']).all(), 'Image/index mismatch')
    old = read_json(base / 'prior_visual_snapshot.json')
    require(len(old['pages']) == 22, 'Original image manifest changed')
    for page in old['pages']:
        hashed(root / page['path'], page['sha256'])
    indexed = index.set_index('entity_id')
    final = individual.set_index('entity_id').reindex(indexed.index)
    for field in ['page', 'panel', 'contact_sheet', 'contact_sheet_sha256', 'all_row_indices', 'plotted_row_indices']:
        require(final[field].fillna('').eq(indexed[field].fillna('')).all(), 'Final note/index field mismatch: ' + field)
    for key, group in r.groupby('entity_id'):
        panel = indexed.loc[key]
        all_rows = {int(value) for value in str(panel.all_row_indices).split('|')}
        drawn = set() if pd.isna(panel.plotted_row_indices) else {int(value) for value in str(panel.plotted_row_indices).split('|')}
        require(all_rows == set(group.index) and drawn == set(group[group.eligible_for_plot.eq(True)].index), 'Panel record membership mismatch')
        require(panel.all_records == len(group) and panel.plotted_records == len(drawn), 'Panel record count mismatch')
        current_max = group.loc[group.eligible_for_plot.eq(True), 'distance_planck_uv'].max()
        require((pd.isna(current_max) and pd.isna(panel.current_max_distance)) or
                np.isclose(current_max, panel.current_max_distance, rtol=0, atol=1e-10), 'A current panel distance is inconsistent')

    assignments = [(1, 63, 1008), (64, 109, 736), (110, 126, 263)]
    require(len(done['manual_review_partitions']) == 3, 'Reviewer partition count differs')
    for partition, expected in zip(done['manual_review_partitions'], assignments):
        require((partition['first_page'], partition['last_page'], partition['entities']) == expected, 'Reviewer assignment differs')
        path = hashed(base / partition['path'], partition['sha256'])
        note = csv(path).set_index('entity_id')
        selected = index[index.page.between(expected[0], expected[1])].set_index('entity_id')
        require(len(note) == expected[2] and note.index.is_unique and set(note.index) == set(selected.index), 'Reviewer entity set differs')
        note = note.reindex(selected.index)
        for field in ['page', 'panel', 'contact_sheet_sha256']:
            require(note[field].eq(selected[field]).all(), 'Reviewer note attached to wrong image')
        has_curve = selected.plotted_records.gt(0)
        require(note.loc[has_curve, 'visual_status'].isin(['viewed_current_flambda_spectrum', 'current_spectrum_panel_inspected']).all(),
                'Plotted panel has wrong inspection status')
        require(note.loc[~has_curve, 'visual_status'].isin(['viewed_explicit_unavailable_panel', 'unavailable_panel_inspected']).all(),
                'Unavailable spectrum was counted as a viewed curve')
        for field in ['visual_status', 'observation', 'evidence_limits']:
            require(note[field].fillna('').eq(final.loc[note.index, field].fillna('')).all(), 'Individual notes changed during merge')
        require(note.observation.fillna('').str.len().gt(15).all(), 'Missing manually authored note')

    plan = read_json(base / 'retrieval_plan.json')
    log = hashed(base / 'retrieval.jsonl')
    latest = {row['sha256']: row for row in map(json.loads, log.read_text().splitlines())}
    require(len(plan['jobs']) == len(latest) == 3041, 'Raw retrieval cardinality differs')
    require(set(latest) == set(r.loc[plotted, 'sha256']), 'Raw log and plotted source SHA set differs')
    frozen = []
    for origin in ['mwdd', 'sdss']:
        path = hashed(root / f'results/screen_input_{origin}.json.gz')
        with gzip.open(path, 'rt', encoding='utf-8') as stream:
            frozen.extend(json.load(stream))
    require(len(frozen) == 9902, 'Frozen row-index population differs')
    for row in r.itertuples():
        original = frozen[row.Index]
        require(row.sha256 == original['sha256'] and row.source_url == original['source_url'], 'Record SHA/URL differs from original input')
    for job in plan['jobs']:
        original = frozen[job['row_index']]
        result = latest[job['sha256']]
        require(job['sha256'] == original['sha256'] and job['source_url'] == original['source_url'], 'Retrieval job targets wrong original')
        require(result['status'] == 'verified' and result['source_url'] == job['source_url'] and result['raw_size_bytes'] > 0,
                'Original raw retrieval remains unresolved')
    require(int(index.plotted_records.gt(0).sum()) == 1684 and int(index.plotted_records.eq(0).sum()) == 323, 'Panel availability counts differ')
    return {
        'summary': 'All 2007 entity panels have individual image-bound notes; 4370 original records retained, 3041 verified-unit curves, 323 explicit unavailable panels; 126 current and 22 historical image hashes verified.',
        'entity_count': 2007, 'record_count': 4370, 'current_spectrum_panels': 1684,
        'explicit_unavailable_panels': 323, 'verified_raw_retrieval_log_entries': 3041,
        'raw_cache_required': False, 'verified_file_sha256': checked,
    }
