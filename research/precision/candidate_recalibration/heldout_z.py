#!/usr/bin/env python3
"""Predict unused PS1 z from the separately saved gri-calibrated DESI spectra.

This is a diagnostic of the adopted calibration and red spectrum.  It does
not fit z, clip negative pixels, extrapolate y, or report a naive sigma test.
All 27 screened entities receive a row, including unavailable measurements.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/wish-green-matplotlib")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import speclite
from speclite import filters

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PRIOR = ROOT / "research/literature/sources/candidate27_prior_rows.json"
SOURCE_MANIFEST = ROOT / "research/literature/sources/atmosphere_sources_manifest.json"
DEFINITION = ROOT / "research/literature/swan_photometry_definition.md"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def finite_number(value):
    try:
        value = float(value)
    except (ValueError, TypeError):
        return None
    return value if np.isfinite(value) else None


def magnitude(response, wave, flux):
    relative_flux = float(response.get_ab_maggies(flux, wave))
    return -2.5 * np.log10(relative_flux) if relative_flux > 0 else None


def linear_weights(response, wave):
    """Exact numerical linear operator used by this speclite integration.

    Evaluating basis vectors in small batches avoids a large dense matrix and
    automatically includes speclite's interpolation at filter boundaries.
    The result maps signed F_lambda samples to relative AB flux (maggies).
    """
    result = np.empty(len(wave))
    for first in range(0, len(wave), 128):
        count = min(128, len(wave) - first)
        basis = np.zeros((count, len(wave)))
        basis[np.arange(count), first + np.arange(count)] = 1.0
        result[first:first + count] = response.get_ab_maggies(basis, wave)
    return result


def filter_metadata(band):
    response = filters.load_filter(f"panstarrs-{band}")
    path = Path(speclite.__file__).parent / "data/filters" / f"panstarrs-{band}.ecsv"
    numeric = np.column_stack((response.wavelength, response.response)).astype("<f8")
    return response, {
        "name": response.name,
        "file_sha256": sha(path),
        "wavelength_response_sha256_little_endian_float64": hashlib.sha256(numeric.tobytes()).hexdigest(),
        "minimum_A": float(response.wavelength.min()),
        "maximum_A": float(response.wavelength.max()),
        "source": "Tonry et al. 2012, ApJ 750, 99; distributed with speclite",
        "source_url": "https://doi.org/10.1088/0004-637X/750/2/99",
    }


def measure(row, prior, derivative, z_filter, y_filter):
    sid = row["source_id"]
    result = {
        "source_id": sid,
        "names": row["names"],
        "WDJname": row.get("swan_WDJname", ""),
        "calibration_status": row["status"],
        "z_status": "unavailable",
        "z_missing_reason": "",
        "y_status": "unavailable",
        "y_missing_reason": "",
        "calibration_bands": "PS1 g,r,i only; z and y unused",
        "swan_external_table_sha256": next(x["sha256"] for x in json.loads(SOURCE_MANIFEST.read_text()) if x["file"] == "swan_external.csv.gz"),
        "selected_prior_rows_sha256": sha(PRIOR),
        "original_spectrum_sha256": row.get("raw_sha256", ""),
        "original_spectrum_url": row.get("source_url", ""),
        "photometric_definition": "Observed PS1 natural-system AB mean-PSF mag; no extinction correction",
        "z_photometric_error_policy": "Published Swan error already includes 0.01 mag quadrature floor; no extra floor here",
        "uncertainty_caution": "Pixel error conditions on fitted gri calibration and assumes independent pixels. Shared PS1 calibration, fit covariance, inter-pixel correlations, time differences and systematics are not included; no sigma significance.",
    }
    matches = prior["candidates"].get(sid, {}).get("swan_external", [])
    if len(matches) != 1:
        result.update(z_missing_reason=f"Expected one exact-ID Swan external row, found {len(matches)}",
                      y_missing_reason="No unique external photometry row or calibrated spectrum")
        return result
    photometry = matches[0]
    result["photometry_row_sha256"] = hashlib.sha256(json.dumps(photometry, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    for band in "zy":
        result[f"{band}_observed_mag"] = finite_number(photometry.get(f"Pan-STARRS.{band}"))
        result[f"{band}_observed_error_mag"] = finite_number(photometry.get(f"Pan-STARRS.{band}_error"))
    if row["status"] != "calibrated_conditional":
        result.update(z_missing_reason=f"Upstream calibration status: {row['status']}",
                      y_missing_reason="No accepted calibrated spectrum")
        return result
    if row["photometry_table_rows_sha256"] != sha(PRIOR):
        raise RuntimeError(f"{sid}: calibration photometry snapshot differs from current input")
    item = derivative[sid]
    if item["photometry_row"] != photometry:
        raise RuntimeError(f"{sid}: calibration photometry row differs from held-out source")
    path = HERE / item["path"]
    if sha(path) != item["sha256"]:
        raise RuntimeError(f"{sid}: calibrated NPZ hash mismatch")
    result.update(calibrated_npz=path.name, calibrated_npz_sha256=sha(path))
    with np.load(path) as saved:
        wave = np.asarray(saved["wavelength_angstrom"], float)
        flux = np.asarray(saved["flux_calibrated"], float)
        ivar = np.asarray(saved["inverse_variance_calibrated"], float)
    if wave.shape != flux.shape or wave.shape != ivar.shape:
        result.update(z_missing_reason="Missing or mismatched wavelength, flux or inverse variance array",
                      y_missing_reason="Invalid input spectrum")
        return result
    if not np.all(np.isfinite(wave)) or not np.all(np.diff(wave) > 0):
        raise RuntimeError(f"{sid}: wavelength array is nonfinite or not strictly increasing")
    good = np.isfinite(flux) & np.isfinite(ivar) & (ivar > 0)
    result.update(wavelength_min_A=float(wave[0]), wavelength_max_A=float(wave[-1]),
                  quality_mask="Finite signed flux and finite IVAR>0; original DESI bitmask absent in these MWDD-derived arrays")
    zlo, zhi = float(z_filter.wavelength.min()), float(z_filter.wavelength.max())
    ylo, yhi = float(y_filter.wavelength.min()), float(y_filter.wavelength.max())
    full_z = bool(good.any() and wave[good].min() <= zlo and wave[good].max() >= zhi)
    full_y = bool(good.any() and wave[good].min() <= ylo and wave[good].max() >= yhi)
    result.update(z_full_passband_coverage=full_z, z_passband_min_A=zlo, z_passband_max_A=zhi,
                  y_full_passband_coverage=full_y, y_passband_min_A=ylo, y_passband_max_A=yhi)
    if not full_y:
        result["y_missing_reason"] = f"Spectrum ends at {wave[-1]:.1f} A; full PS1 y response requires {yhi:.1f} A; no extrapolation"
    else:
        # Deliberately do not silently change the requested analysis if a future
        # spectrum covers y. A new, explicit y comparison can then be designed.
        result.update(y_status="not_computed", y_missing_reason="This script is a pre-specified z-band diagnostic")
    if not full_z:
        result["z_missing_reason"] = "Valid spectral samples do not bracket the full PS1 z response; no extrapolation"
        return result
    # Keep one good point beyond each filter edge to permit interpolation only
    # inside the observed wavelength range, and retain every negative sample.
    valid_wave, valid_flux, valid_ivar = wave[good], flux[good], ivar[good]
    first = max(0, int(np.searchsorted(valid_wave, zlo, side="right")) - 1)
    last = min(len(valid_wave), int(np.searchsorted(valid_wave, zhi, side="left")) + 1)
    zw, zf, zi = valid_wave[first:last], valid_flux[first:last], valid_ivar[first:last]
    in_z = (wave >= zlo) & (wave <= zhi)
    sampled_step = float(np.median(np.diff(wave)))
    gaps = np.diff(zw)
    result.update(z_native_pixels=int(in_z.sum()), z_invalid_pixels=int((in_z & ~good).sum()),
                  z_negative_valid_pixels=int((in_z & good & (flux < 0)).sum()),
                  z_negative_valid_fraction=float(np.mean(flux[in_z & good] < 0)),
                  native_median_step_A=sampled_step,
                  z_largest_valid_sample_gap_A=float(gaps.max()),
                  z_gaps_over_1p5_native_steps=int((gaps > 1.5 * sampled_step).sum()))
    denominator = float(z_filter.get_ab_maggies(np.ones(len(wave)), wave))
    observed_response = float(z_filter.get_ab_maggies(good.astype(float), wave))
    result["z_invalid_photon_response_fraction_flat_flambda"] = 1 - observed_response / denominator
    predicted = magnitude(z_filter, zw, zf)
    result["z_predicted_mag"] = predicted
    if predicted is None:
        result["z_missing_reason"] = "Signed integrated z flux is nonpositive"
        return result
    weights = linear_weights(z_filter, zw)
    relative_flux = float(weights @ zf)
    reference_flux = float(z_filter.get_ab_maggies(zf, zw))
    if not np.isclose(relative_flux, reference_flux, rtol=2e-12, atol=0):
        raise RuntimeError(f"{sid}: exact linear integration weights failed consistency check")
    result["z_spectral_error_mag_conditional_pixels_only"] = float(2.5 / np.log(10) * np.sqrt(np.sum(weights**2 / zi)) / relative_flux)
    # Two explicit missing-pixel stress calculations, neither a new spectrum
    # nor an uncertainty bound. No original array is modified or clipped.
    zero_fill = np.where(good, flux, 0.0)
    zero_mag = magnitude(z_filter, wave, zero_fill)
    idx = np.searchsorted(valid_wave, wave)
    left, right = np.maximum(0, idx - 1), np.minimum(len(valid_wave) - 1, idx)
    closest = np.where(np.abs(wave - valid_wave[left]) <= np.abs(wave - valid_wave[right]), left, right)
    nearest_mag = magnitude(z_filter, wave, valid_flux[closest])
    result.update(z_zero_fill_stress_mag=zero_mag,
                  z_zero_fill_minus_interpolated_mag=None if zero_mag is None else float(zero_mag - predicted),
                  z_nearest_fill_minus_interpolated_mag=None if nearest_mag is None else float(nearest_mag - predicted))
    if np.all(np.isfinite(flux)):
        all_mag = magnitude(z_filter, wave, flux)
        result["z_all_pixels_minus_valid_interpolation_mag"] = None if all_mag is None else float(all_mag - predicted)
    severe_gaps = bool(result["z_invalid_photon_response_fraction_flat_flambda"] > .05 or gaps.max() > 50)
    result["z_gap_quality_review"] = severe_gaps
    observed = result["z_observed_mag"]
    if observed is None or result["z_observed_error_mag"] is None or result["z_observed_error_mag"] <= 0:
        result.update(z_status="prediction_only", z_missing_reason="No finite positive-error Swan z measurement")
        return result
    result.update(z_status="computed_gap_review" if severe_gaps else "computed_diagnostic",
                  z_residual_predicted_minus_observed_mag=float(predicted - observed))
    return result


def plot(rows):
    available = sorted((r for r in rows if "z_residual_predicted_minus_observed_mag" in r),
                       key=lambda r: r["z_residual_predicted_minus_observed_mag"])
    fig, ax = plt.subplots(figsize=(10.6, 10))
    positions = np.arange(len(available))
    residuals = [r["z_residual_predicted_minus_observed_mag"] for r in available]
    phot_errors = [r["z_observed_error_mag"] for r in available]
    labels = [r["WDJname"].replace("WDJ", "J") for r in available]
    ax.axvline(0, color="#555555", linewidth=1)
    ax.axvspan(-.05, .05, color="#dbe5ec", alpha=.35, label="±0.05 mag guide (no significance threshold)")
    ax.errorbar(residuals, positions, xerr=phot_errors, fmt="none", ecolor="#718595",
                capsize=2, linewidth=1.0, label="Swan z error only; not the total uncertainty")
    points = ax.scatter(residuals, positions, c=[r["z_invalid_photon_response_fraction_flat_flambda"] * 100 for r in available],
                        cmap="viridis", s=42, edgecolor="#303030", linewidth=.4, zorder=3)
    ax.set_yticks(positions, labels, fontsize=8.5)
    ax.set_xlabel("Predicted PS1 z − observed PS1 z [AB mag]\npositive: spectrum predicts less z-band flux")
    ax.set_ylabel("Previously screened candidate")
    ax.grid(axis="y", alpha=.18)
    ax.set_title("Unused z-band diagnostic after PS1 gri calibration\n25 computed; 2 unavailable; all y predictions withheld for incomplete coverage", fontsize=12)
    ax.legend(fontsize=8, loc="lower right")
    colorbar = fig.colorbar(points, ax=ax, pad=.025, fraction=.035)
    colorbar.set_label("Invalid-pixel photon response [%], flat Fλ")
    fig.text(.5, .008, "Shared PS1 anchors, parameter covariance, time differences and spectral systematics remain. No sigma significance is inferred.", ha="center", fontsize=8)
    fig.tight_layout(rect=(0, .035, 1, 1))
    fig.savefig(HERE / "heldout_z.png", dpi=170)
    plt.close(fig)


def main():
    input_path = HERE / "standardized_colours.csv"
    with input_path.open() as handle:
        input_rows = list(csv.DictReader(handle))
    prior = json.loads(PRIOR.read_text())
    derivative = {r["source_id"]: r for r in json.loads((HERE / "derivative_manifest.json").read_text())}
    z_filter, z_metadata = filter_metadata("z")
    y_filter, y_metadata = filter_metadata("y")
    rows = [measure(r, prior, derivative, z_filter, y_filter) for r in input_rows]
    fields = list(dict.fromkeys(k for r in rows for k in r))
    with (HERE / "heldout_z.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    computed = [r for r in rows if "z_residual_predicted_minus_observed_mag" in r]
    residual = np.array([r["z_residual_predicted_minus_observed_mag"] for r in computed])
    summary = {
        "date_utc": "2026-10-18",
        "script_sha256": sha(Path(__file__)),
        "input_colours_sha256": sha(input_path),
        "input_derivative_manifest_sha256": sha(HERE / "derivative_manifest.json"),
        "input_photometry_rows_sha256": sha(PRIOR),
        "photometry_definition_document_sha256": sha(DEFINITION),
        "swan_external_source": next(x for x in json.loads(SOURCE_MANIFEST.read_text()) if x["file"] == "swan_external.csv.gz"),
        "software": {"numpy": np.__version__, "speclite": speclite.__version__},
        "filters": {"z": z_metadata, "y": y_metadata},
        "entities": len(rows), "computed_z": len(computed),
        "missing_z": len(rows) - len(computed),
        "full_z_passband": sum(r.get("z_full_passband_coverage", False) for r in rows),
        "full_y_passband": sum(r.get("y_full_passband_coverage", False) for r in rows),
        "z_gap_quality_review": sum(r.get("z_gap_quality_review", False) for r in rows),
        "z_gap_review_rule": "Diagnostic review if invalid photon response >5% (flat F_lambda) or any valid-sample gap >50 A; fixed before reading residuals",
        "z_residual_median_mag": float(np.median(residual)),
        "z_residual_min_mag": float(residual.min()),
        "z_residual_max_mag": float(residual.max()),
        "z_absolute_residual_over_0p05mag": int((np.abs(residual) > .05).sum()),
        "z_absolute_residual_over_0p1mag": int((np.abs(residual) > .1).sum()),
        "maximum_invalid_response_fraction": max(r["z_invalid_photon_response_fraction_flat_flambda"] for r in computed),
        "maximum_valid_sample_gap_A": max(r["z_largest_valid_sample_gap_A"] for r in computed),
        "maximum_absolute_zero_fill_stress_mag": max(abs(r["z_zero_fill_minus_interpolated_mag"]) for r in computed),
        "maximum_absolute_nearest_fill_stress_mag": max(abs(r["z_nearest_fill_minus_interpolated_mag"]) for r in computed),
        "method": "Photon-weighted speclite PS1 z AB magnitude from signed calibrated F_lambda and valid IVAR>0 samples; linear interpolation within fully observed passband only; no z refit",
        "limitations": [
            "z was unused as a calibration anchor; it still shares the PS1 survey and overlaps the red tail of i in wavelength.",
            "Spectral statistical errors are conditional on the existing fitted calibration and assume independent valid samples. Interpolation reuses endpoints; exact weights preserve that dependence.",
            "No total sigma, p-value or discovery probability is computed. Calibration parameter covariance, correlated pixels, atmospheric/sky residuals, non-simultaneity and survey systematics remain.",
            "The published Swan z errors already contain a 0.01 mag quadrature floor; no additional copy of that floor is added.",
            "Input NPZ files preserve signed pixels. Their inverse variance can exclude invalid errors; the original DESI bitmask is not carried by these MWDD-derived products.",
            "Zero filling and nearest-pixel filling are sensitivity diagnostics, not measured replacements or bounds on the missing flux.",
            "All available spectra stop at 9824 A; PS1 y requires 11010 A and is not extrapolated.",
            "The 0.05/0.10 mag summary counts describe residual sizes, not statistical significance or a candidate acceptance gate.",
        ],
        "rows": rows,
    }
    (HERE / "heldout_z.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n")
    plot(rows)
    print(json.dumps({k: v for k, v in summary.items() if k not in ("rows", "limitations", "filters")}, indent=2))


if __name__ == "__main__":
    main()
