#!/usr/bin/env python3
"""Isolate calibration-state differences between proven SDSS representations.

No spectrum is fitted to another spectrum. The three comparisons are raw/raw,
the frozen current states, and the *existing* MWDD correction applied to both.
Replaying the original photometric fits only explains the recorded acceptance
decisions; a replayed or rejected fit is never used to change a plotted curve.
"""
from __future__ import annotations

import csv
import gzip
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().with_suffix('')
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
os.environ.setdefault('MPLCONFIGDIR', str(ROOT / 'mpl-cache'))
import numpy as np
import pandas as pd
from astropy.io import fits
import colour_pipeline as c
from flux_conventions import as_flux_lambda
from build_followup import frozen_inputs, relative, sha
from project_io import load_json

spec = importlib.util.spec_from_file_location('native_identity', ROOT / 'research/precision/flux_convention_audit.py')
native = importlib.util.module_from_spec(spec)
spec.loader.exec_module(native)

SOURCE_IDS = ['1038076351151065088', '1311674353544358912',
              '2586182156053386240', '1025033665052512000']
MODES = ['raw_both', 'current_individual', 'common_existing_mwdd']
COLS = ['row_index', 'entity_id', 'kind', 'archive_origin', 'source_url',
        'sha256', 'status', 'usable_screen', 'flux_input_convention',
        'calibrated', 'cal_system', 'cal_offset_mag', 'cal_tilt_mag_per_1000A',
        'cal_max_residual_mag', 'calibration_notes', 'u1960', 'v1960', 'duv']


def jsonable(x):
    if isinstance(x, dict): return {str(k): jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)): return [jsonable(v) for v in x]
    if isinstance(x, np.generic): return jsonable(x.item())
    if isinstance(x, float) and not np.isfinite(x): return None
    return x


def raw_arrays(index, item, headers):
    """Use exact original bytes or their lossless, bundled gzip copy."""
    origin, record = item
    original = relative(record['raw_path'])
    saved = OUT / f'raw_row_{index}.csv.gz' if origin == 'mwdd' else (
        OUT.parent / 'association_diagnostics' / headers[index]['lossless_original_path'])
    if saved.is_file():
        blob = gzip.decompress(saved.read_bytes())
    else:
        blob = original.read_bytes()
    assert hashlib.sha256(blob).hexdigest() == record['sha256'], f'Raw SHA mismatch: {index}'
    photometric_fields = None
    if origin == 'mwdd':
        lines = blob.decode('utf-8', 'replace').splitlines()
        names = [x.strip() for x in next(csv.reader([lines[1]]))]
        table = np.loadtxt(io.StringIO('\n'.join(lines[2:])), delimiter=',', ndmin=2)
        data = {key: table[:, j] for j, key in enumerate(names)}
        w, f = data['wavelength'], data['flux']
        iv = data.get('ivar')
        if 'sigma' in data:
            s = data['sigma']
            iv = np.divide(1, s * s, out=np.zeros_like(s), where=np.isfinite(s) & (s > 0))
        header = lines[0]
    else:
        with fits.open(io.BytesIO(blob)) as hd:
            data = hd[1].data
            w = 10 ** np.asarray(data['loglam'], float)
            f = np.asarray(data['flux'], float) * 1e-17
            iv = np.asarray(data['ivar'], float) / 1e-34
            header = {k: hd[0].header.get(k) for k in ['BUNIT', 'PLATEID', 'MJD', 'FIBERID', 'RUN2D']}
            hd2 = hd[2].data
            photometric_fields = {}
            for key in ['BESTOBJID', 'OBJID', 'RA', 'DEC', 'CLEAN', 'PSFFLUX', 'PSFFLUX_IVAR', 'PSFMAG', 'PSFMAGERR']:
                if key in hd2.names:
                    value = hd2[key][0]
                    photometric_fields[key] = value.tolist() if isinstance(value, np.ndarray) else value.item() if isinstance(value, np.generic) else value
        assert header['BUNIT'] == '1E-17 erg/cm^2/s/Ang'
        assert headers[index]['original_fits_sha256'] == record['sha256']
    raw = {'wave': w, 'flux': f, 'header': header, 'raw_sha256_verified': True,
           'fits_hdu2_photometric_fields': photometric_fields}
    flam, ivlam, meta = as_flux_lambda(w, f, iv, record)
    return (w, flam, ivlam), raw, blob, saved, meta


def existing_calibration(row):
    if bool(row['calibrated']):
        a, b = float(row['cal_offset_mag']), float(row['cal_tilt_mag_per_1000A'])
        assert np.isfinite(a + b)
        return a, b
    return 0., 0.


def transformed(arrays, params):
    w, f, iv = arrays
    a, b = params
    factor = 10 ** (-.4 * (a + b * (w - 6200) / 1000))
    return w, f * factor, None if iv is None else iv / factor ** 2


def measure(arrays):
    w, f, iv = arrays
    metrics = c.integrate_colour(w, f, iv, mask_sky=True)
    keep_metrics = {k: metrics[k] for k in ['u1960', 'v1960', 'duv', 'distance_planck_uv',
                                           'n_visible_pixels', 'largest_visible_gap_A']}
    w, f, iv = c.clean_spectrum(w, f, iv, mask_sky=True)
    sel = (w >= 3600) & (w <= 8300)
    w, f = w[sel], f[sel]
    anchor = float(np.median(f[(w >= 5200) & (w <= 5500)]))
    assert anchor > 0 and np.isfinite(anchor)
    f = f / anchor
    edges = np.arange(3600, 8320, 20)
    bins = np.minimum(np.digitize(w, edges) - 1, len(edges) - 2)
    means = np.array([f[bins == j].mean() if np.any(bins == j) else np.nan
                      for j in range(len(edges) - 1)])
    keep_metrics['normalizer_flam_5200_5500_A'] = anchor
    for lo, hi in [(4000, 4500), (6500, 7500)]:
        selected = ((edges[:-1] + edges[1:]) / 2 >= lo) & ((edges[:-1] + edges[1:]) / 2 < hi)
        keep_metrics[f'normalized_mean_{lo}_{hi}_A'] = float(np.nanmean(means[selected]))
    return keep_metrics, (w, f), ((edges[:-1] + edges[1:]) / 20, means)


def shape_difference(first, second):
    w, f = first
    wd, fd = second
    idx = np.searchsorted(wd, w).clip(1, len(wd) - 1)
    idx = np.where(abs(wd[idx - 1] - w) < abs(wd[idx] - w), idx - 1, idx)
    matched = abs(w - wd[idx]) <= native.THRESHOLDS['nearest_native_wavelength_tolerance_A']
    ref = fd[idx]
    reference_floor = .1 * np.median(abs(ref[matched]))
    relative = matched & (abs(ref) > reference_floor)
    residual = f[relative] / ref[relative] - 1
    return {'native_clean_matched_samples': int(matched.sum()),
            'normalized_fractional_residual_samples': int(relative.sum()),
            'relative_reference_floor': float(reference_floor),
            'median_abs_normalized_fractional_residual': float(np.median(abs(residual))),
            'p95_abs_normalized_fractional_residual': float(np.quantile(abs(residual), .95)),
            'max_abs_normalized_fractional_residual': float(np.max(abs(residual)))}


def replay_photometric_decisions(arrays, record):
    """Replay only the original finite gri measurements and original policy."""
    w, f, _ = arrays
    p = record.get('photometry', {})
    out = []
    for system, prefix, eprefix in [('sdss', 's', 'Ds'), ('panstarrs', 'PS_', 'DPS_')]:
        obs = [float(p.get(prefix + b, np.nan)) for b in 'gri']
        err = [float(p.get(eprefix + b, np.nan)) for b in 'gri']
        result = {'system': system, 'observed_gri_mag': obs, 'errors_gri_mag': err}
        if not all(np.isfinite(obs)):
            result['decision'] = 'unavailable_three_finite_magnitudes_required'
        else:
            try:
                _, fit = c.recalibrate_gri(w, f, obs, err, system)
                failures = []
                if fit['cal_max_residual_mag'] >= .15: failures.append('maximum_residual_ge_0.15_mag')
                if abs(fit['cal_tilt_mag_per_1000A']) >= .25: failures.append('absolute_tilt_ge_0.25_mag_per_1000A')
                result.update(fit=fit, decision='rejected' if failures else 'accepted', failed_gates=failures)
            except ValueError as exc:
                result.update(decision='rejected', error=str(exc))
        out.append(result)
        if result['decision'] == 'accepted': break
    return out


def photometric_identity(im, id_, frozen, raw_direct, direct_manifest):
    """A missing MWDD photometric objID remains an explicit unresolved key."""
    pm, pdirect = frozen[im][1].get('photometry', {}), frozen[id_][1].get('photometry', {})
    dm = direct_manifest[frozen[id_][1]['spectrum_id']]
    assert dm['photometry_sha256'] == frozen[id_][1]['sha256']
    hdu2 = raw_direct['fits_hdu2_photometric_fields']
    bestobjid = str(hdu2.get('BESTOBJID', hdu2.get('OBJID', ''))).strip()
    assert bestobjid == dm['photometry_objid']
    bands = []
    for j, band in enumerate('gri', 1):
        raw_flux = hdu2['PSFFLUX'][j]
        raw_ivar = hdu2['PSFFLUX_IVAR'][j]
        expected = float(22.5 - 2.5 * np.log10(raw_flux))
        expected_error = float(2.5 / np.log(10) / raw_flux / np.sqrt(raw_ivar))
        assert abs(expected - float(pdirect['s' + band])) < 1e-10
        assert abs(expected_error - float(pdirect['Ds' + band])) < 1e-10
        bands.append({'band': band, 'mwdd_frozen_mag': float(pm['s' + band]),
            'mwdd_frozen_error_mag': float(pm['Ds' + band]),
            'direct_frozen_flux_derived_mag': expected, 'direct_frozen_error_mag': expected_error,
            'direct_minus_mwdd_mag': expected - float(pm['s' + band]),
            'direct_hdu2_psfmag': hdu2['PSFMAG'][j],
            'direct_flux_mag_minus_hdu2_psfmag': expected - hdu2['PSFMAG'][j]})
    return {'direct_objid': bestobjid,
        'direct_source': 'Original same-observation FITS HDU2 BESTOBJID and PSFFLUX/PSFFLUX_IVAR; no new nearest-neighbour photometric lookup',
        'direct_fits_hdu2_fields': hdu2,
        'mwdd_photometric_objid_in_frozen_input': None,
        'mwdd_frozen_row_has_photometric_objid': any('objid' in k.lower() for k in frozen[im][1]),
        'same_photometric_object_identity': 'unresolved_no_mwdd_photometric_objid_or_photometric_epoch_in_frozen_input',
        'interpretation': 'The same spectral observation is established, but the two photometric anchors cannot be proved to refer to the same imaging detection from these retained inputs. Do not attribute the difference to a wrong nearest match or to intrinsic variability.',
        'gri_comparison': bands}


def main():
    OUT.mkdir(exist_ok=True)
    current_path = ROOT / 'research/precision/flux_units/corrected_record_screen.csv.gz'
    current = pd.read_csv(current_path, dtype={'source_id': str}, low_memory=False)
    registry_path = ROOT / 'research/precision/flux_convention_evidence.json'
    registry = json.loads(registry_path.read_text())
    assert registry['thresholds'] == native.THRESHOLDS
    frozen = frozen_inputs()
    direct_manifest = {r['spectrum_id']: r for r in load_json(ROOT / 'sdss/manifest_with_photometry.json')}
    header_path = OUT.parent / 'association_diagnostics/sdss_original_headers.json'
    headers = {r['row_index']: r for r in json.loads(header_path.read_text())}
    plots, display, results, saved_paths = [], [], [], []
    for sid in SOURCE_IDS:
        group = current[current.source_id.eq(sid)]
        mwdd = group[group.kind.eq('SDSS') & group.archive_origin.eq('MWDD')]
        direct = group[group.kind.eq('SDSS') & group.archive_origin.eq('SDSS_DR17_direct')]
        result = {'source_id': sid, 'entity_id': 'gaia:' + sid,
                  'current_records': group[[x for x in COLS if x in group]].to_dict('records')}
        if mwdd.empty or direct.empty:
            result.update(disposition='held_no_same_observation_mwdd_direct_sdss_pair',
                reason='LHS2086 has no MWDD SDSS representation; Bergeron row 3786 is a different, unit-unverified input. XP/direct differences cannot be assigned to duplicate calibration by this experiment.')
            results.append(result)
            continue
        assert len(mwdd) == len(direct) == 1, 'Do not silently choose among multiple observations'
        rm, rd = mwdd.iloc[0], direct.iloc[0]
        im, id_ = int(rm.row_index), int(rd.row_index)
        evidence = [r for r in registry['pair_evidence']
                    if r['mwdd_row_index'] == im and r['direct_row_index'] == id_]
        assert len(evidence) == 1 and evidence[0]['convention'] in ['fnu', 'flambda']
        am, rawm, bm, pathm, metam = raw_arrays(im, frozen[im], headers)
        ad, rawd, bd, pathd, metad = raw_arrays(id_, frozen[id_], headers)
        repeated = native.compare(rm.to_dict(), rd.to_dict(), rawm, rawd)
        assert repeated['convention'] == evidence[0]['convention'] == rm.flux_input_convention
        assert metam['flux_input_convention'] == repeated['convention']
        assert metad['flux_input_convention'] == 'flambda'
        assert repeated[repeated['convention'] + '_accepted']
        assert not repeated[('fnu' if repeated['convention'] == 'flambda' else 'flambda') + '_accepted']
        assert repeated['mwdd_sha256'] == frozen[im][1]['sha256']
        assert repeated['direct_sha256'] == frozen[id_][1]['sha256']
        if not pathm.is_file(): pathm.write_bytes(gzip.compress(bm, mtime=0))
        saved_paths.extend([pathm, pathd])
        cm, cd = existing_calibration(rm), existing_calibration(rd)
        result.update(disposition='same_observation_identity_reverified',
            mwdd_row_index=im, direct_row_index=id_, repeated_native_identity=repeated,
            bundled_raw_paths=[str(p.relative_to(ROOT)) for p in [pathm, pathd]],
            photometric_decision_replay={str(im): replay_photometric_decisions(am, frozen[im][1]),
                                         str(id_): replay_photometric_decisions(ad, frozen[id_][1])},
            photometric_identity=photometric_identity(im, id_, frozen, rawd, direct_manifest), modes={})
        for row in [rm, rd]:
            accepted = [p for p in result['photometric_decision_replay'][str(int(row.row_index))]
                        if p['decision'] == 'accepted']
            assert bool(accepted) == bool(row.calibrated)
            if accepted:
                fit = accepted[0]['fit']
                assert fit['cal_system'] == row.cal_system
                for key in ['cal_offset_mag', 'cal_tilt_mag_per_1000A', 'cal_max_residual_mag']:
                    assert abs(fit[key] - float(row[key])) < 1e-6
        for mode, corrections in zip(MODES, [((0., 0.), (0., 0.)), (cm, cd), (cm, cm)]):
            metrics_m, clean_m, curve_m = measure(transformed(am, corrections[0]))
            metrics_d, clean_d, curve_d = measure(transformed(ad, corrections[1]))
            delta = float(np.hypot(metrics_m['u1960'] - metrics_d['u1960'], metrics_m['v1960'] - metrics_d['v1960']))
            comparison = {'delta_uv': delta, 'mwdd': metrics_m, 'direct': metrics_d,
                'applied_offset_and_tilt': {'mwdd': list(corrections[0]), 'direct': list(corrections[1])},
                **shape_difference(clean_m, clean_d)}
            if mode == 'current_individual':
                for row, metric in [(rm, metrics_m), (rd, metrics_d)]:
                    reproduction = float(np.hypot(row.u1960 - metric['u1960'], row.v1960 - metric['v1960']))
                    assert reproduction < 1e-7
                    metric['reproduced_current_delta_uv'] = reproduction
            result['modes'][mode] = comparison
            plots.append((sid, im, id_, mode, curve_m, curve_d, delta, cm[1]))
            for idx, curve in [(im, curve_m), (id_, curve_d)]:
                display.extend({'source_id': sid, 'row_index': idx, 'mode': mode,
                                'wavelength_nm': float(w), 'mean_normalized_flambda': float(f)}
                               for w, f in zip(*curve))
        delta_current = result['modes']['current_individual']['delta_uv']
        delta_common = result['modes']['common_existing_mwdd']['delta_uv']
        unequal = cm != cd
        result['different_existing_corrections'] = unequal
        result['paired_delta_uv_reduction_fraction'] = 1 - delta_common / delta_current if unequal else None
        result['existing_mwdd_correction_ratio_4200_over_7000_A'] = float(10 ** (-.4 * cm[1] * (4200 - 7000) / 1000))
        result['current_other_instrument_distances'] = []
        for other in group[group.kind.isin(['Gaia_XP', 'DESI']) & group.status.eq('ok')].itertuples():
            state = result['modes']['common_existing_mwdd']['mwdd']
            result['current_other_instrument_distances'].append({'other_row_index': int(other.row_index),
                'other_kind': other.kind, 'delta_uv_from_common_existing_mwdd_state':
                float(np.hypot(state['u1960'] - other.u1960, state['v1960'] - other.v1960)),
                'interpretation': 'Descriptive comparison to frozen current values from a different instrument; no correction was fitted to this instrument.'})
        results.append(result)
    figure_path = make_figure(plots)
    curves_path = OUT / 'display_curves.csv.gz'
    pd.DataFrame(display).to_csv(curves_path, index=False, float_format='%.17g', compression={'method': 'gzip', 'mtime': 0})
    comparison_rows, decision_rows = [], []
    for result in results:
        summary = {k: result[k] for k in ['source_id', 'entity_id', 'disposition']}
        if 'modes' in result:
            for key in ['mwdd_row_index', 'direct_row_index', 'paired_delta_uv_reduction_fraction',
                        'existing_mwdd_correction_ratio_4200_over_7000_A']:
                summary[key] = result[key]
            evidence = result['repeated_native_identity']
            summary['native_identity_convention'] = evidence['convention']
            summary['native_identity_comparison_samples'] = evidence['comparison_samples']
            summary['native_identity_max_fractional_residual'] = evidence[evidence['convention'] + '_max_fractional_shape_residual']
            for mode in MODES:
                for field in ['delta_uv', 'p95_abs_normalized_fractional_residual']:
                    summary[mode + '_' + field] = result['modes'][mode][field]
            for row_index, decisions in result['photometric_decision_replay'].items():
                for decision in decisions:
                    row = {'source_id': result['source_id'], 'row_index': int(row_index),
                           'system': decision['system'], 'decision': decision['decision'],
                           'failed_gates': ';'.join(decision.get('failed_gates', []))}
                    row.update({key: decision.get('fit', {}).get(key) for key in
                                ['cal_offset_mag', 'cal_tilt_mag_per_1000A', 'cal_max_residual_mag']})
                    for j, band in enumerate('gri'):
                        row[band + '_mag'] = decision['observed_gri_mag'][j]
                        row[band + '_error_mag'] = decision['errors_gri_mag'][j]
                    decision_rows.append(row)
        comparison_rows.append(summary)
    comparison_path, decisions_path = OUT / 'comparison_summary.csv', OUT / 'photometric_decisions.csv'
    pd.DataFrame(comparison_rows).to_csv(comparison_path, index=False, float_format='%.17g')
    pd.DataFrame(decision_rows).to_csv(decisions_path, index=False, float_format='%.17g')
    inputs = [current_path, registry_path, header_path, Path(__file__),
              ROOT / 'research/precision/flux_convention_audit.py', ROOT / 'colour_pipeline.py',
              ROOT / 'flux_conventions.py', ROOT / 'results/screen_input_mwdd.json.gz',
              ROOT / 'results/screen_input_sdss.json.gz', OUT.parent / 'build_followup.py',
              ROOT / 'sdss/manifest_with_photometry.json.gz', ROOT / 'sdss/fetch_photometry.py',
              ROOT / 'run_full_screen.py']
    payload = {'selected_entities': len(SOURCE_IDS), 'same_observation_pairs_reverified': len(plots) // 3,
        'held_without_pair': sum(r['disposition'].startswith('held_') for r in results),
        'pairs_with_different_current_corrections': sum(r.get('different_existing_corrections', False) for r in results),
        'method': 'Exact frozen raw SHA and original strict native-pixel identity gates; no rebinning, interpolation, or continuum tilt fit for identity. Colour uses existing retained native grids. Display only uses 20 A means and independent 5200-5500 A medians. Shared correction is the existing accepted MWDD a,b (or identity if absent).',
        'interpretation_limits': 'The reduction measures a difference between duplicate representations of the same observation. It is not independent confirmation, physical variability, the fraction of instrument error, or validation of the photometric correction. Remaining colours retain wavelength rounding, masks and support differences. Different-instrument residuals remain unresolved. No current screen, eligibility, old panel, manifest or ranking was changed.',
        'photometric_replay_limits': 'Uses only original frozen measurements and the unchanged sequential SDSS/PS1 acceptance rules. It explains existing decisions; replayed/rejected fits are not used to align spectra.',
        'identity_thresholds': native.THRESHOLDS,
        'input_sha256': {str(p.relative_to(ROOT)): sha(p) for p in inputs},
        'evidence_file_sha256': {str(p.relative_to(ROOT)): sha(p) for p in sorted(set(saved_paths) | {figure_path, curves_path, comparison_path, decisions_path})},
        'results': results}
    (OUT / 'results.json').write_text(json.dumps(jsonable(payload), indent=2, ensure_ascii=False, allow_nan=False) + '\n')
    for r in results:
        print(r['source_id'], r['disposition'], {m: r['modes'][m]['delta_uv'] for m in MODES} if 'modes' in r else '')


def make_figure(plots):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(3, 3, figsize=(16, 12), layout='constrained')
    labels = ['Both raw Fλ', 'Current individual calibration states', 'Same existing MWDD correction on both']
    for ax, (sid, im, id_, mode, cm, cd, delta, tilt) in zip(axes.flat, plots):
        ax.plot(*cm, color='#26558a', lw=1.4, label=f'MWDD row {im}')
        ax.plot(*cd, color='#ca5a2b', lw=1.2, ls='--', label=f'Direct row {id_}')
        ax.axhline(1, color='#999999', lw=.5)
        ax.set_xlim(360, 830)
        ax.set_xlabel('Wavelength (nm)')
        ax.set_ylabel('Normalized Fλ; 20 Å mean')
        ax.set_title(f'{sid}\n{labels[MODES.index(mode)]}\nΔuv = {delta:.7g}', fontsize=10)
        ax.grid(alpha=.18)
        ax.legend(fontsize=8)
    fig.suptitle('Proven duplicates of three SDSS observations: isolate existing calibration state\n'
        'Native-pixel identity is reverified before this comparison; no spectrum-to-spectrum fit', fontsize=14)
    fig.supxlabel('Each curve: median at 5200–5500 Å = 1. Means shown without uncertainty inference.\n'
        'Fourth selected object, LHS2086 / 1038076351151065088, has no MWDD SDSS pair and is held.', fontsize=10)
    target = OUT / 'same_observation_comparison.png'
    fig.savefig(target, dpi=150)
    plt.close(fig)
    return target


if __name__ == '__main__':
    main()
