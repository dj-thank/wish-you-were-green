"""Integrate externally calibrated Gaia spectra and their full covariance.

Run with the parent scientific virtualenv. The retained/truncated Gaussian
coefficient noise is propagated exactly to XYZ, then sampled for nonlinear
chromaticities. This is formal statistical uncertainty, not calibration error
or a guarantee of the spectral model. No flux is clipped before integration.
"""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent.parent
sys.path.insert(0, str(PROJECT))
import json
import re
import numpy as np
import pandas as pd
from colour_pipeline import (CMF_W, CMF_V, XYZ_TO_RGB, trapezoid_weights,
    integrate_colour, _BB_TREE, _BB_UV)

RNG = np.random.default_rng(20261018)
N_MC = 200000
PREFIX = sys.argv[1] if len(sys.argv) > 1 else 'j0913'
if re.fullmatch(r'j[0-9]+', PREFIX) is None:
    raise ValueError('Prefix must be j followed by digits')
source_id = str(pd.read_csv(ROOT / f'{PREFIX}_xp_continuous.csv', dtype={'source_id': str}).iloc[0]['source_id'])
records = []
for path in sorted(ROOT.glob(f'{PREFIX}_*nm.npz')):
    data = np.load(path)
    wl = data['wavelength_nm']
    flux = data['flux_w_m2_nm']
    cov = data['covariance_w2_m4_nm2']
    keep = (wl >= 360) & (wl <= 830)
    w, f = wl[keep], flux[keep]
    c = cov[np.ix_(keep, keep)]
    cmf = np.column_stack([np.interp(w, CMF_W, CMF_V[:, k], left=0, right=0) for k in range(3)])
    weight = cmf * trapezoid_weights(w)[:, None]
    xyz = weight.T @ f
    xyz_cov = weight.T @ c @ weight
    xyz_cov = (xyz_cov + xyz_cov.T) / 2
    scale = xyz[1]
    norm_xyz, norm_cov = xyz / scale, xyz_cov / scale**2
    xx, yy, zz = norm_xyz
    den = xx + 15*yy + 3*zz
    jac_uv = np.array([[4*(den-xx), -60*xx, -12*xx],
                       [-6*yy, 6*(den-15*yy), -18*yy]]) / den**2
    uv_cov = jac_uv @ norm_cov @ jac_uv.T
    draws = RNG.multivariate_normal(norm_xyz, norm_cov, size=N_MC, check_valid='raise')
    good = np.all(draws > 0, axis=1)
    draws = draws[good]
    xy = draws[:, :2] / draws.sum(axis=1)[:, None]
    denominator = -2 * xy[:, 0] + 12 * xy[:, 1] + 3
    uv = np.column_stack([4 * xy[:, 0] / denominator, 6 * xy[:, 1] / denominator])
    distance, ix = _BB_TREE.query(uv)
    duv = distance * np.sign(uv[:, 1] - _BB_UV[ix, 1])
    rgb = draws @ XYZ_TO_RGB.T
    rgb_green = (rgb[:, 1] > rgb[:, 0]) & (rgb[:, 1] > rgb[:, 2])
    channel_difference = (XYZ_TO_RGB[1] - XYZ_TO_RGB[0])
    gr = channel_difference @ norm_xyz
    gr_error = np.sqrt(channel_difference @ norm_cov @ channel_difference)
    central = integrate_colour(wl * 10, flux, mask_sky=False)
    rec = {'spectrum': path.name, **central,
           'n_mc': N_MC, 'n_nonpositive_xyz_draws': int(N_MC-len(draws)),
           'xyz_native': xyz.tolist(), 'xyz_covariance_native': xyz_cov.tolist(),
           'uv_covariance_first_order': uv_cov.tolist(),
           'x_stat_error': float(np.std(xy[:, 0])), 'y_stat_error': float(np.std(xy[:, 1])),
           'u_stat_error': float(np.std(uv[:, 0])), 'v_stat_error': float(np.std(uv[:, 1])),
           'duv_stat_error': float(np.std(duv)),
           'duv_percentiles_2_5_16_50_84_97_5': np.percentile(duv, [2.5, 16, 50, 84, 97.5]).tolist(),
           'probability_duv_positive_formal_only': float(np.mean(duv>0)),
           'probability_duv_above_0_005_formal_only': float(np.mean(duv>.005)),
           'probability_linear_green_largest_formal_only': float(np.mean(rgb_green)),
           'linear_green_minus_red_with_Y_normalized': float(gr),
           'linear_green_minus_red_stat_error': float(gr_error),
           'linear_green_minus_red_stat_z': float(gr/gr_error),
           'uncertainty_caveat': 'Published coefficient formal covariance only. Truncation discards high-order signal and does not include truncation bias. BP/RP cross-band calibration covariance and systematic spectral errors are not supplied and not invented.'}
    records.append(rec)
    print(json.dumps(rec), flush=True)
    np.savez_compressed(ROOT / (path.stem + '_colour_mc.npz'),
                        xy=xy, uv1960=uv, duv=duv, xyz_mean=xyz, xyz_covariance=xyz_cov)
sources = json.loads((ROOT / 'mwdd_xp_sources.json').read_text())
mwdd_rec = sources[PREFIX]
if mwdd_rec['source_id'] != source_id:
    raise ValueError('MWDD/ESA source ID mismatch')
raw_path = (ROOT / mwdd_rec['raw_path']).resolve()
import hashlib
if hashlib.sha256(raw_path.read_bytes()).hexdigest() != mwdd_rec['sha256']:
    raise ValueError('Cached MWDD spectrum checksum mismatch')
raw = np.loadtxt(raw_path, delimiter=',', skiprows=2)
comparison = {}
for tag in ['full', 'truncated']:
    model = np.load(ROOT / f'{PREFIX}_{tag}_mwdd_grid.npz')
    f_model = model['flux_w_m2_nm']
    if len(f_model) != len(raw):
        raise ValueError('MWDD source has a different sampling grid')
    residual = raw[:, 1] - f_model
    comparison[tag] = {'mwdd_sha256': mwdd_rec.get('sha256'), 'mwdd_url': mwdd_rec.get('source_url'),
                       'flux_absolute_unit_hypothesis': 'Identical raw units: W m^-2 nm^-1',
                       'max_wavelength_discrepancy_A': float(np.max(abs(raw[:, 0]-model['wavelength_angstrom']))),
                       'max_flux_discrepancy_over_max_abs_flux': float(np.max(abs(residual))/np.max(abs(f_model))),
                       'rms_flux_discrepancy_over_rms_flux': float(np.sqrt(np.mean(residual**2)/np.mean(f_model**2))),
                       'unfitted_scale_median_data_model': float(np.median(raw[:, 1]/f_model))}
out = {'source_id': source_id, 'n_mc': N_MC, 'seed': 20261018,
       'integration': 'CIE 1931 2 degree official 1 nm CMFs, trapezoidal integral of native F_lambda from 360 to 830 nm, no sky masking, no flux clipping, no photometric recalibration, and no illuminant adaptation.',
       'mwdd_native_colour': integrate_colour(*raw.T, mask_sky=False),
       'mwdd_reconstruction_comparison': comparison,
       'results': records}
(ROOT / f'{PREFIX}_colour_covariance_audit.json').write_text(json.dumps(out, indent=2))
pd.DataFrame([{k:v for k,v in r.items() if not isinstance(v, (dict, list))} for r in records]).to_csv(ROOT / f'{PREFIX}_colour_covariance_audit.csv', index=False)
print('MWDD comparison:', json.dumps(comparison), flush=True)
