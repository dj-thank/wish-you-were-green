"""Recompute the same-observation calibration experiment without writes.

Only the six losslessly bundled original spectra are read. Survey caches,
network access, parsed NPZ files and figure regeneration are not required.
"""
from __future__ import annotations

import csv
import gzip
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd


def verify(root):
    previous = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        return _verify(Path(root).resolve())
    finally:
        sys.dont_write_bytecode = previous


def _verify(root):
    base = root / 'research/outlier_followup/representation_calibration'
    checked = {}

    def require(condition, message):
        if not condition:
            raise AssertionError('SDSS representation calibration: ' + message)

    def hashed(path, expected=None):
        path = Path(path).resolve()
        require(path.is_relative_to(root) and path.is_file(), 'Missing bundled evidence: ' + str(path))
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        require(expected is None or digest == expected, 'SHA mismatch: ' + str(path.relative_to(root)))
        checked[str(path.relative_to(root))] = digest
        return path

    def close(actual, expected, label, *, atol=1e-10):
        np.testing.assert_allclose(actual, expected, rtol=1e-8, atol=atol,
                                   equal_nan=False, err_msg=label)

    report = json.loads(hashed(base / 'results.json').read_text())
    for section in ['input_sha256', 'evidence_file_sha256']:
        for path, digest in report[section].items():
            hashed(root / path, digest)
    for path in ['README.md', 'verify_outputs.py', 'visual_review.json']:
        hashed(base / path)
    viewed = json.loads((base / 'visual_review.json').read_text())
    hashed(base / viewed['image'], viewed['sha256'])
    require(viewed['actually_opened_and_viewed'] is True and viewed['panels_viewed'] == 9,
            'Image-bound visual review differs')

    # All imports are rooted explicitly; the caller may have cwd=/tmp.
    original_path = sys.path.copy()
    sys.path.insert(0, str(root))
    try:
        import colour_pipeline as colour
        from flux_conventions import as_flux_lambda
        from astropy.io import fits
        spec = importlib.util.spec_from_file_location(
            '_representation_native_identity_verify', root / 'research/precision/flux_convention_audit.py')
        native = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(native)
    finally:
        sys.path[:] = original_path
    require(Path(colour.ROOT).resolve() == root, 'Colour module came from a different checkout')
    registry = json.loads((root / 'research/precision/flux_convention_evidence.json').read_text())
    require(report['identity_thresholds'] == registry['thresholds'] == native.THRESHOLDS,
            'Native identity thresholds differ')

    frozen = []
    for origin in ['mwdd', 'sdss']:
        with gzip.open(root / f'results/screen_input_{origin}.json.gz', 'rt', encoding='utf-8') as stream:
            frozen.extend((origin, row) for row in json.load(stream))
    require(len(frozen) == 9902, 'Frozen row-index population differs')
    current = pd.read_csv(root / 'research/precision/flux_units/corrected_record_screen.csv.gz',
                          dtype={'source_id': str}, low_memory=False).set_index('row_index')
    summary = pd.read_csv(base / 'comparison_summary.csv', dtype={'source_id': str}).set_index('source_id')
    decisions = pd.read_csv(base / 'photometric_decisions.csv', dtype={'source_id': str})
    require(not decisions.duplicated(['row_index', 'system']).any(), 'Repeated photometric decision')
    decisions = decisions.set_index(['row_index', 'system'])

    expected = {'1311674353544358912': (4185, 9399),
                '2586182156053386240': (978, 8781),
                '1025033665052512000': (1953, 9079)}
    held_id = '1038076351151065088'
    by_source = {r['source_id']: r for r in report['results']}
    require(len(report['results']) == 4 and set(by_source) == set(expected) | {held_id},
            'Selected entity membership differs')
    require(summary.index.is_unique and set(summary.index) == set(by_source), 'Comparison CSV membership differs')
    held = by_source[held_id]
    held_current = current[current.source_id.eq(held_id)]
    require(held['disposition'] == 'held_no_same_observation_mwdd_direct_sdss_pair' and 'modes' not in held,
            'Unpaired object promoted into a same-observation comparison')
    require(not (held_current.kind.eq('SDSS') & held_current.archive_origin.eq('MWDD')).any(),
            'Held object now has an MWDD SDSS record and needs reassessment')
    require(current.loc[3786, 'status'] == 'unit_unverified', 'Unverified Bergeron input status differs')

    raw_count = 0

    def bundled_arrays(row_index, path):
        nonlocal raw_count
        origin, record = frozen[row_index]
        path = hashed(root / path)
        require(path.suffix == '.gz', 'Expected a bundled gzip original')
        blob = gzip.decompress(path.read_bytes())
        require(hashlib.sha256(blob).hexdigest() == record['sha256'], 'Decompressed original SHA differs')
        if origin == 'mwdd':
            require(path == base / f'raw_row_{row_index}.csv.gz', 'MWDD bundle points to a different row')
            lines = blob.decode('utf-8', 'replace').splitlines()
            names = [x.strip() for x in next(csv.reader([lines[1]]))]
            table = np.loadtxt(io.StringIO('\n'.join(lines[2:])), delimiter=',', ndmin=2)
            data = {key: table[:, j] for j, key in enumerate(names)}
            w, f, iv = data['wavelength'], data['flux'], data.get('ivar')
            if 'sigma' in data:
                s = data['sigma']
                iv = np.divide(1, s * s, out=np.zeros_like(s), where=np.isfinite(s) & (s > 0))
            header = lines[0]
        else:
            require(path.parent == base.parent / 'association_diagnostics', 'Direct original is outside the bundled association evidence')
            with fits.open(io.BytesIO(blob), memmap=False) as hd:
                d = hd[1].data
                w = 10 ** np.asarray(d['loglam'], float)
                f = np.asarray(d['flux'], float) * 1e-17
                iv = np.asarray(d['ivar'], float) / 1e-34
                header = {key: hd[0].header.get(key) for key in ['BUNIT', 'PLATEID', 'MJD', 'FIBERID', 'RUN2D']}
            require(header['BUNIT'] == '1E-17 erg/cm^2/s/Ang', 'Official FITS density contract differs')
        raw = {'wave': w, 'flux': f, 'header': header, 'raw_sha256_verified': True}
        flam, ivlam, meta = as_flux_lambda(w, f, iv, record)
        require(meta['flux_units_validated'] and meta['flux_input_convention'] == 'flambda',
                'A selected pair no longer has validated F_lambda units')
        raw_count += 1
        return (w, flam, ivlam), raw

    accepted_records, decision_keys, condition_count = [], set(), 0
    largest_delta_uv_reproduction_error = 0.
    recomputed = []
    for sid, (im, id_) in expected.items():
        result = by_source[sid]
        require((result['mwdd_row_index'], result['direct_row_index']) == (im, id_), 'Pair row identity differs')
        require(result['disposition'] == 'same_observation_identity_reverified', 'Pair status differs')
        rm, rd = current.loc[im], current.loc[id_]
        for index, row in [(im, rm), (id_, rd)]:
            require(row.source_id == sid and row.kind == 'SDSS' and row.status == 'ok', 'Current row identity/status differs')
            require(row.sha256 == frozen[index][1]['sha256'] and row.source_url == frozen[index][1]['source_url'],
                    'Current record differs from frozen original')
        require(len(result['bundled_raw_paths']) == 2, 'Pair does not contain two original bundles')
        am, raw_m = bundled_arrays(im, result['bundled_raw_paths'][0])
        ad, raw_d = bundled_arrays(id_, result['bundled_raw_paths'][1])
        identity = native.compare({'row_index': im, **rm.to_dict()}, {'row_index': id_, **rd.to_dict()}, raw_m, raw_d)
        require(identity['convention'] == 'flambda' and identity['flambda_accepted'] is True and identity['fnu_accepted'] is False,
                'Strict native-pixel identity no longer passes exactly one convention')
        original_identity = result['repeated_native_identity']
        for field in ['mwdd_sha256', 'direct_sha256', 'direct_fits_header', 'comparison_samples', 'all_finite_matched_samples']:
            require(identity[field] == original_identity[field], 'Native evidence differs: ' + field)
        for field in ['wave_grid_match_fraction', 'wave_span_A', 'wave_max_matched_difference_A',
                      'flambda_max_fractional_shape_residual', 'flambda_max_absolute_residual_per_median_reference']:
            close(identity[field], original_identity[field], sid + ' ' + field)

        params = []
        for index, row, arrays in [(im, rm, am), (id_, rd, ad)]:
            p = frozen[index][1].get('photometry', {})
            stored = result['photometric_decision_replay'][str(index)]
            replay = []
            selected = None
            for system, prefix, error_prefix in [('sdss', 's', 'Ds'), ('panstarrs', 'PS_', 'DPS_')]:
                obs = [float(p.get(prefix + b, np.nan)) for b in 'gri']
                err = [float(p.get(error_prefix + b, np.nan)) for b in 'gri']
                failures, fit = [], None
                if not np.all(np.isfinite(obs)):
                    status = 'unavailable_three_finite_magnitudes_required'
                else:
                    _, fit = colour.recalibrate_gri(arrays[0], arrays[1], obs, err, system)
                    if fit['cal_max_residual_mag'] >= .15: failures.append('maximum_residual_ge_0.15_mag')
                    if abs(fit['cal_tilt_mag_per_1000A']) >= .25: failures.append('absolute_tilt_ge_0.25_mag_per_1000A')
                    status = 'rejected' if failures else 'accepted'
                recorded = stored[len(replay)]
                require(recorded['system'] == system and recorded['decision'] == status and recorded.get('failed_gates', []) == failures,
                        f'Photometric acceptance differs for row {index}, {system}')
                tab = decisions.loc[(index, system)]
                require(tab.source_id == sid and tab.decision == status, 'Decision CSV status differs')
                require(('' if pd.isna(tab.failed_gates) else tab.failed_gates) == ';'.join(failures), 'Decision CSV failed gate differs')
                for j, band in enumerate('gri'):
                    for field, actual in [(band + '_mag', obs[j]), (band + '_error_mag', err[j])]:
                        require((np.isnan(actual) and pd.isna(tab[field])) or np.isclose(actual, tab[field], rtol=0, atol=1e-12),
                                'Decision CSV photometric input differs')
                if fit is not None:
                    for key in ['cal_offset_mag', 'cal_tilt_mag_per_1000A', 'cal_max_residual_mag']:
                        close(fit[key], recorded['fit'][key], f'{index} {system} {key}', atol=1e-6)
                        close(fit[key], tab[key], f'Decision CSV {index} {key}', atol=1e-6)
                replay.append(status)
                decision_keys.add((index, system))
                if status == 'accepted':
                    selected = fit
                    break
            require(len(replay) == len(stored), 'Photometric sequence has an extra or missing decision')
            require(bool(selected) == bool(row.calibrated), 'Recomputed acceptance differs from current snapshot')
            if selected:
                require(selected['cal_system'] == row.cal_system, 'Accepted photometric system differs')
                for key in ['cal_offset_mag', 'cal_tilt_mag_per_1000A', 'cal_max_residual_mag']:
                    close(selected[key], row[key], f'Current calibration {index} {key}', atol=1e-6)
                accepted_records.append(index)
                params.append((float(row.cal_offset_mag), float(row.cal_tilt_mag_per_1000A)))
            else:
                params.append((0., 0.))

        modes = {'raw_both': ((0., 0.), (0., 0.)),
                 'current_individual': (params[0], params[1]),
                 'common_existing_mwdd': (params[0], params[0])}
        require(set(result['modes']) == set(modes), 'Comparison conditions differ')
        deltas = {}
        for mode, corrections in modes.items():
            measured = []
            for side, arrays, correction, row in [('mwdd', am, corrections[0], rm), ('direct', ad, corrections[1], rd)]:
                w, f, iv = arrays
                a, b = correction
                factor = np.power(10., -.4 * (a + b * (w - 6200.) / 1000.))
                metric = colour.integrate_colour(w, f * factor, None if iv is None else iv / factor ** 2, mask_sky=True)
                recorded = result['modes'][mode][side]
                close(correction, result['modes'][mode]['applied_offset_and_tilt'][side], 'Applied existing correction differs')
                for field in ['u1960', 'v1960', 'duv', 'distance_planck_uv']:
                    close(metric[field], recorded[field], f'{sid} {mode} {side} {field}')
                require(metric['n_visible_pixels'] == recorded['n_visible_pixels'], 'Retained native support differs')
                if mode == 'current_individual':
                    close([metric['u1960'], metric['v1960']], [row.u1960, row.v1960], 'Current colour did not reproduce')
                measured.append([metric['u1960'], metric['v1960']])
            delta = float(np.linalg.norm(np.subtract(*measured)))
            close(delta, result['modes'][mode]['delta_uv'], f'{sid} {mode} delta_uv')
            close(delta, summary.loc[sid, mode + '_delta_uv'], f'Comparison CSV {sid} {mode}')
            largest_delta_uv_reproduction_error = max(largest_delta_uv_reproduction_error, abs(delta - result['modes'][mode]['delta_uv']))
            deltas[mode] = delta
            condition_count += 1
        if params[0] != params[1]:
            reduction = 1 - deltas['common_existing_mwdd'] / deltas['current_individual']
            close(reduction, result['paired_delta_uv_reduction_fraction'], 'Reported reduction differs')
            close(reduction, summary.loc[sid, 'paired_delta_uv_reduction_fraction'], 'CSV reduction differs')
        else:
            require(result['paired_delta_uv_reduction_fraction'] is None, 'An unchanged pair has a claimed reduction')
        recomputed.append({'source_id': sid, 'mwdd_row_index': im, 'direct_row_index': id_, 'delta_uv': deltas})

    require(raw_count == 6 and condition_count == 9, 'Recomputed original/condition count differs')
    require(set(accepted_records) == {4185, 1953}, 'Accepted row membership differs')
    require(decision_keys == set(decisions.index), 'Decision CSV contains missing or extra fits')
    require(report['same_observation_pairs_reverified'] == 3 and report['held_without_pair'] == 1 and
            report['pairs_with_different_current_corrections'] == 2, 'Summary counts differ')
    return {
        'summary': 'Recomputed all 3 same-observation SDSS pairs in 3 calibration states from 6 bundled raw originals; native-pixel identity and original sequential photometric acceptance decisions pass. Two representation differences collapse under the same existing correction; one unpaired object remains held.',
        'same_observation_pairs': 3, 'conditions_recomputed': condition_count,
        'bundled_raw_originals_sha_verified': raw_count,
        'photometric_decisions_recomputed': len(decision_keys),
        'accepted_record_indices': sorted(accepted_records),
        'largest_delta_uv_reproduction_error': largest_delta_uv_reproduction_error,
        'recomputed_comparisons': recomputed,
        'raw_cache_required': False, 'network_required': False,
        'verified_file_sha256': checked,
    }
