"""Reconstruct an officially retrieved Gaia DR3 XP spectrum with covariance.

This script reads only the locally cached ESA DataLink CSV, uses GaiaXPy's
installed calibration models, and preserves native W m^-2 nm^-1 units.
No clipping, continuum fitting, or flux normalisation is applied.
"""
from pathlib import Path
import os
ROOT = Path(__file__).resolve().parent
os.environ.setdefault('MPLCONFIGDIR', str(ROOT / 'mpl-cache'))
import json
import hashlib
import shutil
import ast
import importlib
import sys
import re
import numpy as np
import pandas as pd
import gaiaxpy
from gaiaxpy.core.generic_functions import array_to_symmetric_matrix

calibrator_module = importlib.import_module('gaiaxpy.calibrator.calibrator')

PREFIX = sys.argv[1] if len(sys.argv) > 1 else 'j0913'
if re.fullmatch(r'j[0-9]+', PREFIX) is None:
    raise ValueError('Prefix must be j followed by digits')
SOURCE = ROOT / f'{PREFIX}_xp_continuous.csv'
if not SOURCE.exists():
    shutil.copyfile(ROOT / f'{PREFIX}_xp_continuous_download.bin', SOURCE)
inp = pd.read_csv(SOURCE)
scalar_columns = [c for c in inp if not c.endswith(('coefficients', 'coefficient_errors', 'coefficient_correlations'))]
scalar_fields = inp[scalar_columns].copy()
for identifier in ['source_id', 'solution_id']:
    scalar_fields[identifier] = scalar_fields[identifier].astype(str)
metadata = {
    'gaiaxpy_version': gaiaxpy.__version__,
    'input_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
    'input_scalar_fields': json.loads(scalar_fields.to_json(orient='records')),
    'flux_unit': 'W m^-2 nm^-1',
    'wavelength_unit': 'nm',
    'normalisation': None,
    'covariance_method': 'Independent exact linear propagation of published coefficient covariance through the same GaiaXPy calibration design matrices and both BP/RP merge weights. BP and RP coefficient errors are treated as independent across bands, as in GaiaXPy. Published formal errors already include band standard deviation. No added systematic calibration covariance.',
    'calibrations': [],
}
coefficient_data = {}
for band in ['bp', 'rp']:
    source_row = inp.iloc[0]
    coefficients = np.asarray(ast.literal_eval(source_row[f'{band}_coefficients']), float)
    errors = np.asarray(ast.literal_eval(source_row[f'{band}_coefficient_errors']), float)
    packed_correlation = np.asarray(ast.literal_eval(source_row[f'{band}_coefficient_correlations']), float)
    corr = array_to_symmetric_matrix(packed_correlation, len(coefficients))
    coefficient_data[band] = {'coefficients': coefficients, 'covariance': corr * errors[:, None] * errors[None, :],
                              'n_relevant': int(source_row[f'{band}_n_relevant_bases'])}
for grid_tag, grid, step in [('2nm', np.arange(330., 1051., 2.), 2.),
                             ('1nm', np.arange(330., 1050.5, 1.), 1.),
                             ('mwdd_grid', np.geomspace(330., 1050., 361), None)]:
    bases, merge = calibrator_module.__generate_xp_matrices_and_merge('calibrator', grid, 'v375wi', 'v142r')
    for truncation in [False, True]:
        tag = f"{'truncated' if truncation else 'full'}_{grid_tag}"
        result, sampling = gaiaxpy.calibrate(
            SOURCE, sampling=grid, truncation=truncation,
            save_file=False, with_correlation=True,
        )
        row = result.iloc[0]
        print(tag, 'columns:', list(result), flush=True)
        flux = np.asarray(row['flux'], float)
        error = np.asarray(row['flux_error'], float)
        packed_correlation_gaiaxpy = np.asarray(row['correlation'], float)
        gaiaxpy_correlation = array_to_symmetric_matrix(packed_correlation_gaiaxpy, len(grid))
        independent_flux = np.zeros(len(grid))
        covariance = np.zeros((len(grid), len(grid)))
        for band in ['bp', 'rp']:
            coeff = coefficient_data[band]['coefficients']
            coeff_cov = coefficient_data[band]['covariance']
            matrix = bases[band].get_design_matrix() * merge[band][None, :]
            n = coefficient_data[band]['n_relevant'] if truncation else len(coeff)
            independent_flux += coeff[:n] @ matrix[:n]
            covariance += matrix[:n].T @ coeff_cov[:n, :n] @ matrix[:n]
        independent_error = np.sqrt(np.maximum(np.diag(covariance), 0))
        # Coefficient covariance multiplication is symmetric to floating precision.
        covariance = (covariance + covariance.T) / 2
        correlation = covariance / independent_error[:, None] / independent_error[None, :]
        flux_match = float(np.max(abs(flux-independent_flux)) / np.max(abs(flux)))
        error_match = float(np.max(abs(error-independent_error)) / np.max(abs(error)))
        if flux_match > 1e-10 or error_match > 1e-10:
            raise ValueError(f'Independent propagation does not reproduce GaiaXPy flux/errors: {flux_match}, {error_match}')
        target = ROOT / f'{PREFIX}_{tag}.npz'
        np.savez_compressed(target, wavelength_nm=sampling,
                            wavelength_angstrom=sampling * 10,
                            flux_w_m2_nm=flux, flux_error_w_m2_nm=error,
                            correlation=correlation, covariance_w2_m4_nm2=covariance,
                            gaiaxpy_output_packed_correlation=packed_correlation_gaiaxpy)
        pd.DataFrame({'wavelength_nm': sampling, 'flux_w_m2_nm': flux,
                      'flux_error_w_m2_nm': error}).to_csv(ROOT / f'{PREFIX}_{tag}.csv', index=False)
        rec = {'tag': tag, 'truncation': truncation, 'step_nm': step,
               'sampling_length': len(sampling), 'result_columns': list(result),
               'path': target.name,
               'sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
               'visible_negative_fraction': float(np.mean(flux[(sampling>=360)&(sampling<=830)] < 0)),
               'visible_median_snr': float(np.median((flux/error)[(sampling>=400)&(sampling<=750)])),
               'independent_flux_max_relative_discrepancy': flux_match,
               'independent_error_max_relative_discrepancy': error_match,
               'gaiaxpy_correlation_max_difference': float(np.max(abs(correlation-gaiaxpy_correlation))),
               'gaiaxpy_correlation_eigenvalue_min': float(np.linalg.eigvalsh(gaiaxpy_correlation).min()),
               'propagated_correlation_eigenvalue_min': float(np.linalg.eigvalsh(correlation).min()),
               'correlation_max_asymmetry': float(np.max(abs(correlation-correlation.T)))}
        metadata['calibrations'].append(rec)
        print(json.dumps(rec), flush=True)
(ROOT / f'{PREFIX}_reconstruction_metadata.json').write_text(json.dumps(metadata, indent=2))
print(json.dumps(metadata['input_scalar_fields'], indent=2), flush=True)
