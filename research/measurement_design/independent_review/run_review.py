#!/usr/bin/env python3
"""Independently assemble and replay six declared coupled-colour LP cases.

The frozen target loader, numerical libraries and response tables are shared.
Constraint assembly, CIE quadrature and witness integration are separate from
the production coupled solver. This is bounded numerical review, not a second
physical experiment or an interval-arithmetic proof.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import sys

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import numpy as np
import scipy
from scipy.interpolate import BSpline, PPoly
from scipy.optimize import linprog

import colour_pipeline as colour
from research.measurement_design.run_design import load_target

SOURCE = "3204436719718449280"
PROPOSALS = ("JPLUS_all_covered", "PS1_plus_JPLUS_all", "ideal_XYZ")
CHECK_TOL = 2e-7


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def review(root=ROOT):
    root = Path(root).resolve()
    assert root == ROOT, "Import this module from the checkout being reviewed"
    checked = {}

    def hashed(name, expected=None):
        path = (root / name).resolve()
        assert path.is_relative_to(root)
        value = digest(path)
        assert expected is None or value == expected, name
        checked[str(path.relative_to(root))] = value
        return path

    source = hashed("research/measurement_design/design_full.json")
    data = json.loads(source.read_text())
    for name, expected in data["input_and_code_hashes"].items():
        hashed(name, expected)
    for name in (
        "reference/CIE_xyz_1931_2deg.csv", "requirements-core.txt",
        "research/precision/candidate_recalibration/derivative_manifest.json",
        "research/precision/candidate_recalibration/standardized_colours.csv",
        "research/measurement_design/independent_review/run_review.py",
    ):
        hashed(name)
    selected = [row for row in data["results"] if (
        row["source_id"] == SOURCE and row["relative_shape_budget"] == .05
        and row["spacing_A"] in (400, 800)
        and row["proposal"]["name"] in PROPOSALS)]
    assert len(selected) == 6
    assert {(r["spacing_A"], r["proposal"]["name"]) for r in selected} == {
        (spacing, proposal) for spacing in (400, 800) for proposal in PROPOSALS}
    outputs, loaded = [], {}
    for row in selected:
        spacing = row["spacing_A"]
        if spacing not in loaded:
            loaded[spacing] = load_target(SOURCE, spacing)
        problem, observed, errors, labels, metadata = loaded[spacing]
        assert metadata["PS1_filter_metadata"] == data["cohort"][SOURCE]["PS1_filter_metadata"]
        assert metadata["additional_filter_metadata"] == data["cohort"][SOURCE]["additional_filter_metadata"]
        hashed(metadata["input_path"], metadata["input_sha256"])
        for entry in metadata["additional_filter_metadata"]:
            hashed(entry["raw_path"], entry["raw_sha256"])
        wave, flux, n = problem.wave, problem.flux, problem.n
        spline_basis = BSpline(problem.knots, np.eye(n), 3)
        basis = spline_basis(wave)
        filters = problem.filterset
        baseline = np.array([flt.get_ab_maggies(flux, wave) for flt in filters])
        band_matrix = np.array([
            flt.get_ab_maggies((flux[:, None] * basis).T, wave, axis=-1)
            for flt in filters]) / baseline[:, None]
        visible = (wave >= 3600) & (wave <= 8300)
        nm = wave[visible] / 10
        cmf = np.column_stack([
            np.interp(nm, colour.CMF_W, colour.CMF_V[:, j], left=0, right=0)
            for j in range(3)])
        xyz = np.trapezoid(flux[visible, None] * cmf, nm, axis=0)
        xyz_change = np.trapezoid(
            flux[visible, None, None] * basis[visible, :, None] * cmf[:, None, :],
            nm, axis=0).T
        rgb = colour.XYZ_TO_RGB @ xyz
        scale = np.max(np.abs(rgb))
        difference = np.array([rgb[1] - rgb[0], rgb[1] - rgb[2]]) / scale
        rgb_change = colour.XYZ_TO_RGB @ xyz_change
        change = np.vstack([rgb_change[1] - rgb_change[0],
                            rgb_change[1] - rgb_change[2]]) / scale
        proposal = row["proposal"]
        proposed = (xyz_change / xyz[:, None] if proposal["kind"] == "ideal_XYZ"
                    else band_matrix[proposal["indices"]])
        feasible = [branch for branch in row["branches"] if branch["success"]]
        assert len(feasible) == 1 and feasible[0]["opposite_branch"] == "G-R"
        for solution in feasible:
            certificate = hashed(solution["certificate_path"], solution["certificate_sha256"])
            with np.load(certificate, allow_pickle=False) as archive:
                saved = {key: archive[key].copy() for key in archive.files}
            rows, bounds = [], []

            def add(local, rhs, offset):
                local = np.atleast_2d(local)
                block = np.zeros((len(local), 2 * n + 1))
                block[:, offset:offset + n] = local
                rows.extend(block)
                bounds.extend(np.atleast_1d(rhs))

            for offset, grid_key in ((0, "green_constraint_grid_A"),
                                     (n, "opposite_constraint_grid_A")):
                on_grid = spline_basis(saved[grid_key])
                add(on_grid, np.full(len(on_grid), .05), offset)
                add(-on_grid, np.full(len(on_grid), .05), offset)
                add(band_matrix[:4],
                    10 ** (-.4 * (observed - errors)) / baseline[:4] - 1, offset)
                add(-band_matrix[:4],
                    1 - 10 ** (-.4 * (observed + errors)) / baseline[:4], offset)
                add(-xyz_change / xyz[:, None], np.full(3, 1 - 1e-8), offset)
                if offset == 0:
                    for channel in (0, 1):
                        add(-change[channel], difference[channel] - .005, offset)
                else:
                    channel = {"G-R": 0, "G-B": 1}[solution["opposite_branch"]]
                    add(change[channel], -difference[channel] - .005, offset)
            rows.extend(np.column_stack([proposed, -proposed, -np.ones(len(proposed))]))
            bounds.extend(np.zeros(len(proposed)))
            rows.extend(np.column_stack([-proposed, proposed, -np.ones(len(proposed))]))
            bounds.extend(np.zeros(len(proposed)))
            matrix, rhs = np.array(rows), np.array(bounds)
            objective = np.r_[np.zeros(2 * n), 1.]
            x, dual = saved["primal"], saved["dual_inequality"]
            lower, upper = saved["dual_lower"], saved["dual_upper"]
            stationarity = float(np.max(np.abs(objective - matrix.T @ dual - lower - upper)))
            primal = max(0., float(np.max(matrix @ x - rhs)))
            dual_objective = float(rhs @ dual)
            gap = float(x[-1] - dual_objective)
            assert max(stationarity, primal, abs(gap)) < CHECK_TOL
            assert max(dual) <= 2e-8 and min(lower) >= -2e-8 and max(upper) <= 2e-8
            assert np.max(np.abs(lower[:-1])) < 2e-8 and np.max(np.abs(upper)) < 2e-8
            predictions, witnesses = [], []
            for coefficients, role in ((x[:n], "green"),
                                        (x[n:2 * n], solution["opposite_branch"])):
                correction = BSpline(problem.knots, coefficients, 3)
                roots = PPoly.from_spline(correction).derivative().roots(extrapolate=False)
                roots = roots[np.isfinite(roots) & (roots >= wave[0]) & (roots <= wave[-1])]
                supremum = float(np.max(np.abs(correction(np.r_[roots, problem.knots]))))
                changed_flux = flux * (1 + correction(wave))
                band_flux = np.array([flt.get_ab_maggies(changed_flux, wave) for flt in filters])
                assert np.all(band_flux > 0)
                mags = -2.5 * np.log10(band_flux[:4])
                box_violation = float(np.max(np.abs(mags - observed) - errors))
                changed_xyz = np.trapezoid(changed_flux[visible, None] * cmf, nm, axis=0)
                assert np.all(changed_xyz >= xyz * .9e-8)
                changed_rgb = colour.XYZ_TO_RGB @ changed_xyz
                channels = np.array([changed_rgb[1] - changed_rgb[0],
                                     changed_rgb[1] - changed_rgb[2]]) / scale
                colour_violation = (.005 - min(channels) if role == "green" else
                                    .005 + channels[{"G-R": 0, "G-B": 1}[role]])
                assert supremum <= .05 + 2.1e-9
                assert max(box_violation, colour_violation) <= CHECK_TOL
                predicted = (changed_xyz / xyz if proposal["kind"] == "ideal_XYZ" else
                             band_flux[proposal["indices"]] / baseline[proposal["indices"]])
                assert np.max(np.abs(predicted - (1 + proposed @ coefficients))) < 2e-9
                predictions.append(predicted)
                witnesses.append({"role": role, "continuous_supremum": supremum,
                                  "maximum_box_violation_mag": max(0., box_violation),
                                  "channels": channels.tolist()})
            fresh = linprog(objective, A_ub=matrix, b_ub=rhs,
                            bounds=[(None, None)] * (2 * n) + [(0, None)],
                            method="highs-ds", options={"presolve": False,
                                "primal_feasibility_tolerance": 1e-10,
                                "dual_feasibility_tolerance": 1e-10})
            assert fresh.success and abs(fresh.fun - x[-1]) < CHECK_TOL
            distance = float(np.max(np.abs(predictions[0] - predictions[1])))
            lower_half = max(0., dual_objective) / 2
            upper_half = distance / 2
            separated = dual_objective > CHECK_TOL
            assert abs(solution["uniform_error_half_width_from_dual_lower_bound"] - lower_half) < 2e-9
            assert abs(solution["uniform_error_half_width_from_witness_upper_bound"] - upper_half) < 2e-9
            assert solution["numerically_separated_at_check_tolerance"] == separated
            summary_half = lower_half if separated else 0.
            assert abs(row["separation_error_half_width"] - summary_half) < 2e-9
            if not separated:
                assert row["separation_error_half_width"] == 0.
            outputs.append({
                "spacing_A": spacing, "proposal": proposal["name"],
                "proposed_labels": row["proposed_labels"],
                "branch": solution["opposite_branch"],
                "fresh_outer_lp_objective": float(fresh.fun),
                "saved_objective": float(x[-1]), "independent_dual_objective": dual_objective,
                "direct_witness_distance": distance,
                "dual_lower_bound_half_width": lower_half,
                "witness_upper_bound_half_width": upper_half,
                "sufficient_half_width_at_check_tolerance": summary_half,
                "numerically_separated_at_check_tolerance": separated,
                "primal_residual": primal, "dual_stationarity": stationarity,
                "duality_gap": gap, "witnesses": witnesses})
    assert len(outputs) == 6
    return {
        "status": "PASS", "review_version": "independent_assembly_with_dual_bound_reporting_v2",
        "scope": "Six predeclared J0429 cases: 400/800 A, 5% budget, 0.005 guard, measured PS1 griz boxes, JPLUS all ten covered bands / those ten plus PS1 / ideal XYZ. Feasible G-R branches only. Full branch census and infeasibility replay remain in the production verifier.",
        "independence": "Shared frozen target loader, cleaned pixels, spline knots, response tables, SciPy and speclite. Separate matrix assembly, direct CIE trapezoidal quadrature, fresh synthetic flux integration, saved primal/dual checks and a newly solved dual-simplex LP on saved outer grids. This is a code/numerical review, not independent astronomical data or a separately developed atmosphere model.",
        "environment": {"python": platform.python_version(), "numpy": np.__version__,
                        "scipy": scipy.__version__},
        "summary": {"declared_cases_replayed": len(outputs),
                    "separate_continuous_spectra_checked": 2 * len(outputs),
                    "largest_primal_residual": max(r["primal_residual"] for r in outputs),
                    "largest_dual_stationarity": max(r["dual_stationarity"] for r in outputs),
                    "largest_absolute_duality_gap": max(abs(r["duality_gap"]) for r in outputs),
                    "dual_reporting_fix_checked": True,
                    "numerical_zeros_suppressed_as_precision_requirements": True},
        "review_findings": [
            "No sign error found in the two colour blocks, exact magnitude-to-flux PS1 boxes, free-coefficient duals or nonnegative distance bound.",
            "The continuous coefficient-hull inner witness retains the original finite-grid outer dual lower bound; inner-space failure is not used to declare full-space infeasibility.",
            "The earlier reporting review requested separate dual-lower and witness-upper half-widths. Current branch and summary fields use the lower side for the sufficient numerical separation condition, with zero at or below CHECK_TOL.",
            "Guard 0.005 uses a fixed baseline linear-RGB scale. It is not a visual discrimination threshold or posterior probability.",
            "A zero minimum supplies one common flux vector admitting both strict colours; it does not say that every future measurement is ambiguous.",
            "The dual and continuous-bound residual tolerances are numerical checks, not interval-arithmetic certificates. Per-band boxes are declared hard constraints, not a calibrated simultaneous confidence region.",
        ],
        "reviewed_file_sha256": checked,
        "response_metadata": {"PS1": loaded[400][4]["PS1_filter_metadata"],
                              "additional": loaded[400][4]["additional_filter_metadata"]},
        "checks": outputs,
    }


def verify(root=ROOT):
    path = Path(root) / "research/measurement_design/independent_review/review_results.json"
    saved = json.loads(path.read_text())
    current = review(root)
    assert saved["reviewed_file_sha256"] == current["reviewed_file_sha256"]
    assert saved["summary"]["declared_cases_replayed"] == current["summary"]["declared_cases_replayed"]
    for original, replay in zip(saved["checks"], current["checks"]):
        assert original["proposal"] == replay["proposal"] and original["spacing_A"] == replay["spacing_A"]
        for field in ("fresh_outer_lp_objective", "independent_dual_objective", "direct_witness_distance",
                      "dual_lower_bound_half_width", "witness_upper_bound_half_width",
                      "sufficient_half_width_at_check_tolerance"):
            assert abs(original[field] - replay[field]) < 2e-9, field
    files = dict(current["reviewed_file_sha256"])
    files[str(path.relative_to(root))] = digest(path)
    documentation = HERE / "README.md"
    if documentation.exists():
        files[str(documentation.relative_to(root))] = digest(documentation)
    return {"summary": current["summary"], "verified_file_sha256": files}


if __name__ == "__main__":
    result = review()
    result["completed_utc"] = datetime.now(timezone.utc).isoformat()
    (HERE / "review_results.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result["summary"], indent=2))
