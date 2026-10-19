#!/usr/bin/env python3
"""Join actual per-panel notes and verify the complete bounded follow-up.

This checks and joins saved observations; it never infers a visual observation
from numerical data and never changes spectra, colours or contact-sheet bytes.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
PARTITIONS = [
    ('visual_review_01_63.csv', 1, 63, 1008),
    ('visual_review_64_126.csv', 64, 109, 736),
    ('visual_review_110_126.csv', 110, 126, 263),
]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_csv(path):
    return pd.read_csv(path, dtype={'source_id': 'string', 'entity_id': 'string'}, low_memory=False)


def number(value):
    try:
        return float(value)
    except (ValueError, TypeError):
        return float('nan')


def disposition_detail(row):
    status = row.plot_status
    if status == 'plotted_verified_flambda':
        suffix = '; verified F_nu converted with c/lambda^2' if row.unit_conversion_applied == True else ''
        return 'Original raw SHA verified; F_lambda convention validated; current unbinned colour reproduced' + suffix
    if status == 'withheld_unverified_flux_units':
        return 'Spectral-density convention unresolved; original record retained; no current physical-colour comparison'
    if status == 'withheld_processing_error':
        return 'Current processing error: ' + str(row.error)
    reasons = []
    if row.coverage_eligible != True:
        reasons.append('wavelength support fails current coverage eligibility')
    coverage = number(row.cmf_min_coverage)
    if not np.isfinite(coverage) or coverage <= .995:
        reasons.append(f'CMF support metric not above 0.995 ({coverage:.8g})')
    gap = number(row.largest_visible_gap_A)
    if not np.isfinite(gap) or gap >= 150:
        reasons.append(f'largest visible gap fails <150 A gate ({gap:.8g} A)')
    if row.calibrated == True:
        residual = number(row.cal_max_residual_mag)
        tilt = number(row.cal_tilt_mag_per_1000A)
        if not np.isfinite(residual) or residual >= .15:
            reasons.append('accepted-calibration residual fails <0.15 mag gate')
        if not np.isfinite(tilt) or abs(tilt) >= .25:
            reasons.append('accepted-calibration tilt fails <0.25 mag per 1000 A gate')
    if not np.isfinite(number(row.ra_deg)) or not np.isfinite(number(row.dec_deg)):
        reasons.append('finite position unavailable')
    if not np.isfinite(number(row.u1960)) or not np.isfinite(number(row.v1960)):
        reasons.append('finite current chromaticity unavailable')
    require(bool(reasons), f'An eligibility failure lacks an explicit reason: row {row.row_index}')
    return '; '.join(reasons)


def main(verify_raw=False):
    plan = json.loads((OUT / 'retrieval_plan.json').read_text())
    generation = json.loads((OUT / 'generation_manifest.json').read_text())
    for path, digest in plan['input_sha256'].items():
        require(sha(ROOT / path) == digest, 'Pinned scientific input changed: ' + path)
    historical = read_csv(ROOT / 'research/outlier_audit/review_queue.csv')
    previous = read_csv(ROOT / 'research/outlier_audit/contact_sheet_index.csv')
    queue = read_csv(OUT / 'queue_entities.csv')
    index = read_csv(OUT / 'contact_sheet_index.csv')
    records = read_csv(OUT / 'record_review.csv.gz')
    current = read_csv(ROOT / 'research/precision/flux_units/corrected_record_screen.csv.gz')
    require(previous.entity_id.is_unique and len(previous) == 337, 'Prior entity set changed')
    require(set(previous.entity_id) <= set(historical.entity_id), 'Prior review is not a subset')
    expected = set(historical.entity_id) - set(previous.entity_id)
    require(len(expected) == 2007, 'Bounded queue has a different size')
    for label, frame in [('queue', queue), ('index', index)]:
        require(frame.entity_id.is_unique and set(frame.entity_id) == expected, label + ' entity membership differs')
    require(index.followup_index.tolist() == list(range(2007)), 'Follow-up sequence changed')
    require((index.page == index.followup_index // 16 + 1).all(), 'Page mapping changed')
    require((index.panel == index.followup_index % 16 + 1).all(), 'Panel mapping changed')
    expected_records = current[current.entity_id.isin(expected)]
    require(records.row_index.is_unique and len(records) == 4370, 'Record count or uniqueness changed')
    require(set(records.row_index) == set(expected_records.row_index), 'Some original entity records are missing')
    check = records.set_index('row_index').join(expected_records.set_index('row_index'), rsuffix='_current')
    for field in ['entity_id', 'source_url', 'sha256', 'status', 'usable_screen', 'flux_units_validated']:
        require(check[field].fillna('') .eq(check[field + '_current'].fillna('')).all(), 'Current metadata differs: ' + field)
    eligible = (records.usable_screen.eq(True) & records.status.eq('ok') & records.flux_units_validated.eq(True)
                & np.isfinite(records.u1960) & np.isfinite(records.v1960))
    require(eligible.eq(records.eligible_for_plot).all(), 'Eligibility snapshot differs')
    require(eligible.eq(records.plot_status.eq('plotted_verified_flambda')).all(), 'Eligible plot failed or withheld plot was admitted')
    require(int(eligible.sum()) == 3041, 'Eligible record count changed')
    require(records.loc[eligible, 'current_recomputed_delta_uv'].between(0, 1e-7).all(), 'Current colour reproduction failed')
    groups = {key: group for key, group in records.groupby('entity_id')}
    for panel in index.itertuples():
        group = groups[panel.entity_id]
        all_rows = {int(value) for value in str(panel.all_row_indices).split('|')}
        plotted_rows = (set() if pd.isna(panel.plotted_row_indices) else
                        {int(value) for value in str(panel.plotted_row_indices).split('|')})
        require(all_rows == set(group.row_index), 'Panel omits an original row')
        require(plotted_rows == set(group.loc[group.eligible_for_plot.eq(True), 'row_index']), 'Panel has the wrong curves')
        require(panel.all_records == len(group) and panel.plotted_records == len(plotted_rows), 'Panel counts differ')
        require(panel.unit_withheld_records == int(group.status.eq('unit_unverified').sum()), 'Panel unit-withheld count differs')
        require(pd.isna(panel.unavailable_eligible_row_indices), 'An eligible curve is unavailable')

    pages = generation['pages_manifest']
    require(len(pages) == 126, 'Final page count differs')
    for page in pages:
        require(sha(OUT / page['path']) == page['sha256'], 'Final image bytes changed: ' + page['path'])
        block = index[index.page.eq(page['page'])]
        require(len(block) == page['entity_count'], 'Page entity count differs')
        require(block.contact_sheet_sha256.eq(page['sha256']).all(), 'Page/index SHA differs')
    old = json.loads((OUT / 'prior_visual_snapshot.json').read_text())
    require(len(old['pages']) == 22, 'Original historical page count differs')
    for page in old['pages']:
        require(sha(ROOT / page['path']) == page['sha256'], 'An original historical sheet changed')

    latest = {}
    for line in (OUT / 'retrieval.jsonl').read_text().splitlines():
        result = json.loads(line)
        latest[result['sha256']] = result
    jobs = plan['jobs']
    expected_raw = set(records.loc[eligible, 'sha256'])
    require(len(jobs) == 3041 and {job['sha256'] for job in jobs} == expected_raw, 'Raw retrieval plan differs')
    require(set(latest) == expected_raw and all(row['status'] == 'verified' for row in latest.values()), 'Raw retrieval unresolved')
    raw_bytes = 0
    if verify_raw:
        for job in jobs:
            path = ROOT / job['raw_path']
            require(sha(path) == job['sha256'], 'Raw archive SHA differs: ' + job['raw_path'])
            raw_bytes += path.stat().st_size

    notes = []
    partitions = []
    has_curve_status = {'viewed_current_flambda_spectrum', 'current_spectrum_panel_inspected'}
    unavailable_status = {'viewed_explicit_unavailable_panel', 'unavailable_panel_inspected'}
    for file, first, last, count in PARTITIONS:
        review = read_csv(OUT / file)
        expected_block = index[index.page.between(first, last)]
        require(len(review) == count and set(review.entity_id) == set(expected_block.entity_id), 'Incomplete actual review: ' + file)
        require(review.entity_id.is_unique, 'Duplicate observation in ' + file)
        joined = review.merge(index[['page', 'panel', 'entity_id', 'plotted_records', 'contact_sheet_sha256']],
                              on=['page', 'panel', 'entity_id'], validate='one_to_one', suffixes=('', '_index'))
        require(len(joined) == count, 'Observation is attached to wrong panel: ' + file)
        require(joined.contact_sheet_sha256.eq(joined.contact_sheet_sha256_index).all(), 'Observation image SHA mismatch: ' + file)
        curve_field = 'plotted_records_index' if 'plotted_records_index' in joined else 'plotted_records'
        has_curve = joined[curve_field].gt(0)
        require(joined.loc[has_curve, 'visual_status'].isin(has_curve_status).all(), 'Curve inspection status mismatch')
        require(joined.loc[~has_curve, 'visual_status'].isin(unavailable_status).all(), 'Unavailable panel status mismatch')
        for field in ['observation', 'evidence_limits']:
            require(joined[field].fillna('').str.strip().str.len().gt(15).all(), 'Missing individual note: ' + file)
        keep = joined[['page', 'panel', 'entity_id', 'visual_status', 'observation', 'evidence_limits']].copy()
        keep['review_notes_file'] = file
        notes.append(keep)
        partitions.append({'path': file, 'first_page': first, 'last_page': last, 'entities': count,
                           'with_current_spectrum': int(has_curve.sum()), 'explicit_unavailable': int((~has_curve).sum()),
                           'sha256': sha(OUT / file)})
    review = pd.concat(notes, ignore_index=True)
    require(review.entity_id.is_unique and set(review.entity_id) == expected, 'Merged individual review incomplete')
    combined = index.rename(columns={'review_state': 'generation_review_state'}).merge(
        review, on=['page', 'panel', 'entity_id'], validate='one_to_one').sort_values('followup_index')
    combined['review_state'] = 'individually_viewed'
    combined.to_csv(OUT / 'individual_review.csv', index=False, float_format='%.17g')
    fields = ['row_index', 'entity_id', 'kind', 'archive_origin', 'source_url', 'sha256', 'status',
              'flux_input_convention', 'flux_conversion_applied', 'eligible_for_plot', 'plot_status',
              'coverage_eligible', 'cmf_min_coverage', 'largest_visible_gap_A', 'current_recomputed_delta_uv']
    details = records[fields].copy()
    details['disposition_detail'] = [disposition_detail(row) for row in records.itertuples()]
    details['gap_gt_50_A_requires_coverage_review'] = records.largest_visible_gap_A.gt(50)
    details = details.merge(index[['entity_id', 'followup_index', 'page', 'panel']], on='entity_id', validate='many_to_one')
    details.sort_values('row_index').to_csv(OUT / 'record_dispositions.csv', index=False, float_format='%.17g')
    summary = {
        'created_utc': datetime.now(timezone.utc).isoformat(), 'complete': True,
        'scope': 'All 2007 entity keys in the historical 2344-object review queue outside the previously viewed 337',
        'entity_count': 2007, 'record_count': 4370, 'reviewed_main_pages': 126,
        'current_spectrum_panels_actually_viewed': int(combined.plotted_records.gt(0).sum()),
        'explicit_unavailable_panels_actually_viewed': int(combined.plotted_records.eq(0).sum()),
        'plotted_records': 3041, 'plot_status_counts': records.plot_status.value_counts().to_dict(),
        'eligible_records_by_instrument': records.loc[eligible, 'kind'].value_counts().to_dict(),
        'largest_recomputed_uv_difference': float(records.current_recomputed_delta_uv.max()),
        'unique_original_raw_verified_at_retrieval': 3041,
        'raw_hashes_rechecked_this_completion': 3041 if verify_raw else 0,
        'raw_bytes_rechecked_this_completion': raw_bytes,
        'prior_337_historical_pages_preserved': 22, 'baseline_commit': old['baseline_commit'],
        'manual_review_partitions': partitions,
        'input_sha256': {**plan['input_sha256'], **{str((OUT / name).relative_to(ROOT)): sha(OUT / name) for name in
            ['contact_sheet_index.csv', 'record_review.csv.gz', 'generation_manifest.json', 'retrieval_plan.json',
             'retrieval.jsonl', 'prior_visual_snapshot.json']}},
        'output_sha256': {name: sha(OUT / name) for name in ['individual_review.csv', 'record_dispositions.csv']},
        'code_sha256': sha(Path(__file__)),
        'limits': 'Individual visual triage of prepared, unit-validated spectra is complete. Physical causes, observation independence, missing spectral support and unverified units are not thereby resolved. No production colours or spectra were changed. Additional zoom reviews overlap this census and add no new entities.',
    }
    (OUT / 'review_completion.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps({key: summary[key] for key in ['complete', 'entity_count', 'record_count',
          'current_spectrum_panels_actually_viewed', 'explicit_unavailable_panels_actually_viewed',
          'raw_hashes_rechecked_this_completion', 'largest_recomputed_uv_difference']}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify-raw', action='store_true', help='Recheck the 3041 downloaded original archive bytes as well')
    main(parser.parse_args().verify_raw)
