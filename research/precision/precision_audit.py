"""Audit numerical geometry and spectral-support assumptions of the frozen screen.

The original result tables and headline definitions are not rewritten. This
module supplies a continuous Planckian projection as a separately named metric,
plus explicitly conditional mask, synthetic-gap, and quadrature diagnostics.
No astronomical data downloads are performed.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import sys

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MPLBACKEND", "Agg")
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd
from scipy.constants import c as LIGHT_SPEED, h as PLANCK_CONSTANT, k as BOLTZMANN_CONSTANT
from scipy.optimize import minimize_scalar

import colour_pipeline as pipeline
from project_io import load_json


class ContinuousPlanckian:
    """Continuous 1000 K--Rayleigh-Jeans projection on the same CIE 1 nm grid.

    q = 1000/T lies on the compact interval [0, 1]. The rescaled F_lambda
    expression lambda^-4 * z/expm1(z), z = hc/(lambda*k*T), is well behaved at
    q=0, where its exact limit is the Rayleigh-Jeans spectrum. It differs from
    Planck radiance only by an achromatic factor, which cancels in chromaticity.
    """

    def __init__(self):
        self.wavelength_m = pipeline.CMF_W * 1e-9
        self.weights = pipeline.CMF_V * pipeline.trapezoid_weights(pipeline.CMF_W)[:, None]
        self.shape = (self.wavelength_m / 550e-9) ** -4
        self.second_radiation_constant = PLANCK_CONSTANT * LIGHT_SPEED / BOLTZMANN_CONSTANT
        self.grid_q = np.r_[1000.0 / pipeline._BB_T[:-1], 0.0]

    def uv(self, q):
        q = float(q)
        if not np.isfinite(q) or not 0 <= q <= 1:
            raise ValueError("q must be finite and in [0, 1]")
        z = self.second_radiation_constant / (1000.0 * self.wavelength_m) * q
        ratio = np.ones_like(z)
        np.divide(z, np.expm1(z), out=ratio, where=z != 0)
        xyz = (self.shape * ratio) @ self.weights
        return np.array([4 * xyz[0], 6 * xyz[1]]) / (xyz @ [1, 15, 3])

    def project(self, u, v):
        point = np.asarray([u, v], dtype=float)
        if not np.all(np.isfinite(point)):
            raise ValueError("Chromaticity must be finite")
        _, index = pipeline._BB_TREE.query(point)
        # The pre-existing dense grid locates the local section, but never sets
        # the final distance or signed side. The smooth locus is not self-crossing.
        lower = self.grid_q[min(int(index) + 2, len(self.grid_q) - 1)]
        upper = self.grid_q[max(int(index) - 2, 0)]

        def objective(q):
            residual = self.uv(q) - point
            return float(residual @ residual)

        fit = minimize_scalar(objective, bounds=(lower, upper), method="bounded",
                              options={"xatol": 1e-15})
        if not fit.success:
            raise RuntimeError("Continuous Planckian projection did not converge")
        options = np.array([fit.x, lower, upper])
        costs = np.array([objective(q) for q in options])
        q = float(options[np.argmin(costs)])
        # Endpoint roundoff at q~1e-15 can beat the exact limit by a few bits.
        # q<=1e-12 has T>=1e15 K and is optically indistinguishable at this audit's
        # precision. An endpoint is reported without a signed perpendicular Duv.
        if lower == 0 and q <= 1e-12:
            q = 0.0
            label = "rayleigh_jeans_endpoint"
        elif upper == 1 and q >= 1 - 1e-12:
            q = 1.0
            label = "low_temperature_endpoint"
        else:
            label = "interior"
        nearest = self.uv(q)
        residual = point - nearest
        distance = float(np.linalg.norm(residual))
        signed = np.nan
        if label == "interior":
            step = 1e-5 * max(q, 1e-5)
            tangent = self.uv(min(1.0, q + step)) - self.uv(max(0.0, q - step))
            # q increases towards cooler temperatures; the tangent has du/dq>0.
            # This rotation gives the normal with positive v component.
            normal = np.array([-tangent[1], tangent[0]])
            signed = float(distance * np.sign(residual @ normal))
        return {
            "distance_continuous": distance,
            "duv_continuous_tangent_sign": signed,
            "continuous_temperature_K": np.inf if q == 0 else 1000 / q,
            "continuous_u": float(nearest[0]),
            "continuous_v": float(nearest[1]),
            "projection_class": label,
        }


def integrate_linear_product(wavelength_angstrom, flux):
    """Exactly integrate two piecewise-linear functions on their joint knots.

    The flux is linearly interpolated between the provided (already cleaned)
    samples, and the reference CMFs are linearly interpolated on their 1 nm
    grid. Their product is quadratic on each joint interval, so midpoint
    Simpson integration is exact there up to floating-point arithmetic.
    """
    wave = np.asarray(wavelength_angstrom, dtype=float) / 10
    flux = np.asarray(flux, dtype=float)
    if wave.ndim != 1 or flux.shape != wave.shape or len(wave) < 2:
        raise ValueError("Aligned one-dimensional spectrum arrays required")
    if np.any(np.diff(wave) <= 0) or not np.all(np.isfinite(wave)) or not np.all(np.isfinite(flux)):
        raise ValueError("Finite, strictly increasing spectral samples required")
    low, high = max(360.0, wave[0]), min(830.0, wave[-1])
    if high <= low:
        raise ValueError("No visible wavelength overlap")
    knots = np.unique(np.r_[wave[(wave >= low) & (wave <= high)],
                            pipeline.CMF_W[(pipeline.CMF_W >= low) & (pipeline.CMF_W <= high)], low, high])
    midpoint = (knots[:-1] + knots[1:]) / 2
    f = np.interp(knots, wave, flux)
    fm = np.interp(midpoint, wave, flux)
    cmf = np.stack([np.interp(knots, pipeline.CMF_W, values) for values in pipeline.CMF_V.T], axis=1)
    cmfm = np.stack([np.interp(midpoint, pipeline.CMF_W, values) for values in pipeline.CMF_V.T], axis=1)
    return np.sum(np.diff(knots)[:, None] / 6 *
                  (f[:-1, None] * cmf[:-1] + 4 * fm[:, None] * cmfm + f[1:, None] * cmf[1:]), axis=0)


def cmf_antiderivative(wavelength_nm):
    """Integral of the reference's piecewise-linear CMFs from 360 nm."""
    wave, values = pipeline.CMF_W, pipeline.CMF_V
    integral = np.vstack([np.zeros(3), np.cumsum(np.diff(wave)[:, None] * (values[:-1] + values[1:]) / 2, axis=0)])
    x = np.clip(np.asarray(wavelength_nm, dtype=float), wave[0], wave[-1])
    indices = np.clip(np.searchsorted(wave, x, side="right") - 1, 0, len(wave) - 2)
    delta = x - wave[indices]
    slope = (values[indices + 1] - values[indices]) / (wave[indices + 1] - wave[indices])[:, None]
    return integral[indices] + delta[:, None] * values[indices] + delta[:, None] ** 2 * slope / 2


def rejected_native_support(wavelength_angstrom, rejected):
    """CMF weight in rejected native-pixel support cells, without inventing flux.

    Cell boundaries are the midpoints of original neighbouring samples. This
    definition counts support removed by the mask; it does not count the entire
    intervals subsequently bridged by endpoint interpolation. The returned
    XYZ fractions are observer-weight fractions, never missing-flux fractions.
    """
    wave = np.asarray(wavelength_angstrom, dtype=float) / 10
    rejected = np.asarray(rejected, dtype=bool)
    if len(wave) < 2 or rejected.shape != wave.shape or np.any(np.diff(wave) <= 0):
        raise ValueError("Native increasing wavelength grid and aligned mask required")
    edges = np.r_[wave[0] - (wave[1] - wave[0]) / 2,
                  (wave[1:] + wave[:-1]) / 2,
                  wave[-1] + (wave[-1] - wave[-2]) / 2]
    masses = np.diff(cmf_antiderivative(edges), axis=0)
    total = cmf_antiderivative(np.array([830.0]))[0]
    return (masses[rejected].sum(axis=0) / total).tolist()


def rejection_mask(wave, flux, ivar, *, mask_sky, gap_centre=None, gap_halfwidth=70):
    rejected = ~np.isfinite(flux) | ~np.isfinite(ivar) | (ivar <= 0)
    if mask_sky:
        for centre, halfwidth in [(5577.34, 8), (5890, 6), (5896, 6), (6300.30, 8), (6363.78, 8)]:
            rejected |= abs(wave - centre) <= halfwidth
    if gap_centre is not None:
        rejected |= abs(wave - gap_centre) <= gap_halfwidth
    return rejected


def audit_screen(root, geometry):
    source = root / "results/all_spectra_screen.csv.gz"
    if not source.exists():
        source = root / "results/all_spectra_screen.csv"
    table = pd.read_csv(source, dtype={"source_id": str}, low_memory=False)
    table.insert(0, "row_index", np.arange(len(table)))
    selection = table.status.eq("ok") & np.isfinite(table.u1960) & np.isfinite(table.v1960)
    selected = table.loc[selection].copy()
    projected = pd.DataFrame([geometry.project(u, v) for u, v in zip(selected.u1960, selected.v1960)], index=selected.index)
    selected = pd.concat([selected, projected], axis=1)
    selected["grid_distance_excess"] = selected.distance_planck_uv - selected.distance_continuous
    selected["duv_side_changed"] = (selected.projection_class.eq("interior") &
                                     (np.sign(selected.duv) != np.sign(selected.duv_continuous_tangent_sign)))
    changed = selected[selected.duv_side_changed]
    thresholds = [0.001, 0.003, 0.005, 0.006, 0.01]
    summary = {
        "source_file": str(source.relative_to(root)),
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "input_records": len(table),
        "evaluated_records": len(selected),
        "nonfinite_or_failed_records_not_projected": int((~selection).sum()),
        "maximum_absolute_distance_change": float(abs(selected.grid_distance_excess).max()),
        "median_grid_distance_excess": float(selected.grid_distance_excess.median()),
        "projection_class_counts": selected.projection_class.value_counts().to_dict(),
        "eligible_projection_class_counts": selected.loc[selected.usable_screen, "projection_class"].value_counts().to_dict(),
        "interior_sign_changes": len(changed),
        "eligible_interior_sign_changes": int(changed.usable_screen.sum()),
        "maximum_old_abs_duv_with_sign_change": float(changed.duv.abs().max()),
        "maximum_continuous_abs_duv_with_sign_change": float(changed.duv_continuous_tangent_sign.abs().max()),
        "threshold_crossings": {str(t): int(((selected.distance_planck_uv > t) !=
                                            (selected.distance_continuous > t)).sum()) for t in thresholds},
    }
    columns = ["row_index", "wdid", "source_id", "kind", "source_url", "usable_screen", "calibrated",
               "u1960", "v1960", "duv", "distance_planck_uv", "nearest_planck_temperature_K",
               "distance_continuous", "duv_continuous_tangent_sign", "continuous_temperature_K",
               "continuous_u", "continuous_v", "projection_class", "grid_distance_excess", "duv_side_changed"]
    return selected[columns], summary


def audit_headlines(root, geometry):
    manifest = load_json(root / "mwdd/manifest_enriched.json")
    headlines = pd.read_csv(root / "results/headline_candidates.csv", dtype={"source_id": str})
    summaries, variants = [], []
    for _, row in headlines.iterrows():
        record = next(r for r in manifest if r.get("source_id") == row.source_id and r.get("kind") == "DESI"
                      and r.get("sha256") == row.raw_sha256)
        with np.load(pipeline.data_path(record["parsed_path"])) as data:
            wave, flux, sigma = data["wavelength_angstrom"], data["flux_original"], data["sigma"]
        ivar = np.divide(1, sigma**2, out=np.zeros_like(sigma), where=np.isfinite(sigma) & (sigma > 0))
        observed = np.array([row[f"anchor_{b}_mag"] for b in "gri"])
        errors = np.array([row[f"anchor_{b}_error"] for b in "gri"])
        calibrated, fit = pipeline.recalibrate_gri(wave, flux, observed, errors, "panstarrs")
        correction = 10 ** (-0.4 * (fit["cal_offset_mag"] + fit["cal_tilt_mag_per_1000A"] * (wave - 6200) / 1000))
        ivc = ivar / correction**2
        nominal = pipeline.integrate_colour(wave, calibrated, ivc, mask_sky=True)
        continuous = geometry.project(nominal["u1960"], nominal["v1960"])
        common = {"candidate": row.candidate, "source_id": row.source_id, "raw_sha256": row.raw_sha256,
                  "source_url": row.source_url, "photometry_system": "panstarrs"}
        entry = {**common, "nominal_duv": nominal["duv"], "nominal_hex": nominal["hex"],
                 "continuous_duv": continuous["duv_continuous_tangent_sign"],
                 "continuous_temperature_K": continuous["continuous_temperature_K"],
                 "grid_distance_excess": abs(nominal["duv"]) - continuous["distance_continuous"]}
        for name, centre, use_sky in [("nominal", None, True), ("no_sky_mask", None, False)] + [
                (f"synthetic_140A_gap_at_{centre:g}A", centre, True) for centre in [5100, 5577.34, 5890, 6300.30]]:
            keep = np.ones(len(wave), dtype=bool) if centre is None else abs(wave - centre) > 70
            metrics = pipeline.integrate_colour(wave[keep], calibrated[keep], ivc[keep], mask_sky=use_sky)
            rejected = rejection_mask(wave, calibrated, ivc, mask_sky=use_sky, gap_centre=centre)
            support = rejected_native_support(wave, rejected)
            result = {**common, "variant": name, "synthetic_gap": centre is not None,
                      "duv": metrics["duv"], "delta_duv": metrics["duv"] - nominal["duv"], "hex": metrics["hex"],
                      "uv_displacement": float(np.hypot(metrics["u1960"] - nominal["u1960"], metrics["v1960"] - nominal["v1960"])),
                      "legacy_cmf_min_coverage": metrics["cmf_min_coverage"],
                      "largest_visible_gap_A": metrics["largest_visible_gap_A"],
                      **{f"rejected_native_support_{label}_cmf_fraction": float(v) for label, v in zip("XYZ", support)}}
            variants.append(result)
            if name == "no_sky_mask":
                entry.update({"no_sky_mask_delta_duv": result["delta_duv"],
                              "no_sky_mask_uv_displacement": result["uv_displacement"], "no_sky_mask_hex": result["hex"]})
        cleaned_wave, cleaned_flux, _ = pipeline.clean_spectrum(wave, calibrated, ivc, mask_sky=True)
        visible = (cleaned_wave >= 3600) & (cleaned_wave <= 8300)
        # Match the original included endpoints exactly; do not make the
        # quadrature comparison an implicit short-wavelength extrapolation.
        xyz_exact = integrate_linear_product(cleaned_wave[visible], cleaned_flux[visible])
        exact_metrics = pipeline.xyz_to_metrics(xyz_exact)
        exact_projection = geometry.project(exact_metrics["u1960"], exact_metrics["v1960"])
        entry.update({"exact_linear_product_duv": exact_projection["duv_continuous_tangent_sign"],
                      "exact_linear_product_hex": exact_metrics["hex"],
                      "exact_linear_product_uv_displacement": float(np.hypot(exact_metrics["u1960"] - nominal["u1960"],
                                                                              exact_metrics["v1960"] - nominal["v1960"]))})
        summaries.append(entry)
    return summaries, pd.DataFrame(variants)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parent,
                        help="Audit output directory; never overwrites the original result tables")
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    geometry = ContinuousPlanckian()
    screen, screen_summary = audit_screen(ROOT, geometry)
    headlines, variants = audit_headlines(ROOT, geometry)
    screen.to_csv(output / "planckian_projection_audit.csv", index=False)
    variants.to_csv(output / "headline_mask_gap_audit.csv", index=False)
    summary = {
        "analysis_date_utc": "2026-10-18",
        "original_screen_commit": "73287c8ed16d66230381b1e0b9a6d9f75dea086b",
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "environment": {name: importlib.metadata.version(name) for name in ["numpy", "scipy", "pandas", "astropy", "colour-science", "speclite"]},
        "continuous_geometry": {"q_definition": "1000 K / T", "q_interval": [0, 1], "minimizer_xatol": 1e-15,
                                "RJ_endpoint_q_tolerance": 1e-12, "second_radiation_constant_m_K": geometry.second_radiation_constant,
                                "CMF_definition": "same committed CIE 1931 2-degree 360--830 nm, 1 nm table as frozen pipeline",
                                "endpoint_signed_duv": "undefined; blank in CSV, retain unsigned distance and projection_class"},
        "screen": screen_summary,
        "headline_precision": headlines,
        "interpretation": ["The original snapshot and representative results are unchanged.",
                           "Numerical differences and synthetic stress tests are not additional observational errors or new detections.",
                           "Rejected-native-support fractions integrate CMFs over masked pixel cells, not unknown missing stellar flux.",
                           "The synthetic 140 A gaps remove available data only to test the screening assumptions.",
                           "Joint-knot integration assumes piecewise-linear flux between remaining samples; it cannot recover missing astrophysical structure."]}
    (output / "precision_summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps(screen_summary, indent=2))
    print("Wrote separately named continuous geometry and four headline precision diagnostics to", output)


if __name__ == "__main__":
    main()
