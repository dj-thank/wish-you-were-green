#!/usr/bin/env python3
"""Offline replay of all continuous witnesses and numerical LP certificates."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import numpy as np
from scipy.interpolate import BSpline, PPoly
from scipy.optimize import linprog

import colour_pipeline as colour
from research.measurement_design.run_design import load_target, proposals, proposed_matrix, TARGETS
from research.measurement_design.coupled_colour_sets import build_constraints


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def close(first, second, name, tolerance=2e-8):
    np.testing.assert_allclose(first, second, rtol=0, atol=tolerance, err_msg=name)


def direct_xyz(wave, flux):
    select = (wave >= 3600) & (wave <= 8300)
    nm = wave[select] / 10
    response = np.column_stack([np.interp(nm, colour.CMF_W, colour.CMF_V[:, i], left=0, right=0)
                                for i in range(3)])
    return np.trapezoid(response * flux[select, None], nm, axis=0)


def verify(root=ROOT):
    root = Path(root).resolve()
    require(root == ROOT, "Import this verifier from the checkout being verified")
    base = root / "research/measurement_design"
    checked, cache, n_witnesses, n_infeasible = {}, {}, 0, 0
    maxima = {"continuous_budget_violation": 0., "primal_violation": 0.,
              "dual_stationarity": 0., "duality_gap": 0., "direct_integration_error": 0.}

    def hashed(path, expected=None):
        path = (root / path).resolve()
        require(path.is_relative_to(root), "Path escapes checkout")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        require(expected is None or digest == expected, f"Hash mismatch: {path}")
        checked[str(path.relative_to(root))] = digest
        return path

    manifest = json.loads(hashed("research/measurement_design/profile_manifest.json").read_text())
    require(len(manifest["profiles"]) == 18, "Passband census changed")
    for record in manifest["profiles"]:
        hashed("research/measurement_design/" + record["file"], record["sha256"])
    documents = {}
    for tag in ("full", "closure10"):
        data = json.loads(hashed(f"research/measurement_design/design_{tag}.json").read_text())
        documents[tag] = data
        hashed(f"research/measurement_design/design_{tag}_summary.csv")
        for path, digest in data["input_and_code_hashes"].items():
            hashed(path, digest)
        expected = set()
        for sid in (TARGETS if tag == "full" else TARGETS[:1]):
            for spacing in ((400, 800, 1600) if tag == "full" else (800,)):
                width = 1. if tag == "full" else 10.
                key = sid, spacing, width
                cache[key] = load_target(sid, spacing, width)
                problem, observed, errors, labels, meta = cache[key]
                hashed(meta["input_path"], meta["input_sha256"])
                require(len(labels) == 17 and len(meta["excluded_filters"]) == 5,
                        "Expected 4 PS1 + 3 SkyMapper + 10 J-PLUS covered responses")
                for flt in problem.filterset:
                    require(problem.wave.min() <= flt.wavelength.min() and problem.wave.max() >= flt.wavelength.max(),
                            "Spectrum was extrapolated outside its native support")
                available = proposals(labels)
                require(len(available) == 23, "Unexpected prospective experiment")
                for budget in (.05, .10):
                    for proposal in available:
                        if tag == "closure10" and proposal["name"] not in (
                            "JPLUS_narrow_covered", "JPLUS_all_covered", "PS1_plus_JPLUS_all", "ideal_XYZ"):
                            continue
                        expected.add((sid, spacing, budget, proposal["name"]))
        actual = [(r["source_id"], r["spacing_A"], r["relative_shape_budget"], r["proposal"]["name"])
                  for r in data["results"]]
        require(len(actual) == len(set(actual)) and set(actual) == expected,
                f"Missing, duplicated or newly selected design cases: {tag}")
        for row in data["results"]:
            sid, spacing, width = row["source_id"], row["spacing_A"], row["closure_width_A"]
            problem, observed, errors, labels, meta = cache[(sid, spacing, width)]
            n = problem.n
            budget, guard = row["relative_shape_budget"], row["normalized_guard"]
            require(guard == .005 and budget in (.05, .10), "Frozen bounds changed")
            proposal = row["proposal"]
            expected_proposal = next(r for r in proposals(labels) if r["name"] == proposal["name"])
            require(proposal == expected_proposal, "Proposed-band selection changed")
            require({b["opposite_branch"] for b in row["branches"]} == {"G-R", "G-B"}
                    and len(row["branches"]) == 2, "An opposite-colour branch was dropped")
            proposed = proposed_matrix(problem, proposal)
            objective = np.r_[np.zeros(2*n), 1.]
            accepted = []
            for solution in row["branches"]:
                branch = solution["opposite_branch"]
                if not solution["success"]:
                    grid = np.unique(np.r_[np.arange(problem.wave.min(), problem.wave.max(), 8), problem.knots])
                    a, b, _ = build_constraints(problem, observed, errors, proposed, budget, guard,
                                                 branch, grid, grid)
                    for method, presolve in (("highs-ipm", True), ("highs-ds", False)):
                        fit = linprog(objective, A_ub=a, b_ub=b, bounds=[(None, None)]*(2*n)+[(0, None)],
                                      method=method, options={"presolve": presolve,
                                          "primal_feasibility_tolerance": 1e-10,
                                          "dual_feasibility_tolerance": 1e-10})
                        if fit.status in (0, 2):
                            break
                    require(fit.status == 2, f"Saved infeasibility does not replay: {sid}, {spacing}, {budget}, {proposal['name']}, {branch}, {fit.status}")
                    n_infeasible += 1
                    continue
                path = hashed(solution["certificate_path"], solution["certificate_sha256"])
                with np.load(path) as saved:
                    x = saved["primal"]
                    y, lower, upper = saved["dual_inequality"], saved["dual_lower"], saved["dual_upper"]
                    a, b, blocks = build_constraints(
                        problem, observed, errors, proposed, budget, guard, branch,
                        saved["green_constraint_grid_A"], saved["opposite_constraint_grid_A"])
                require(blocks == solution["constraint_blocks"], "Constraint block ordering changed")
                require(len(x) == 2*n+1 and len(y) == len(b), "Certificate dimensions")
                require(x[-1] >= -2e-8 and np.max(y) <= 2e-8 and np.min(lower) >= -2e-8
                        and np.max(upper) <= 2e-8, "Invalid primal bound or dual sign")
                # All spline coefficients are free. t has only the zero lower
                # bound, so finite variable bounds add zero to the dual value.
                require(np.max(np.abs(lower[:-1])) < 2e-8 and np.max(np.abs(upper)) < 2e-8,
                        "A dual term was assigned to a nonexistent variable bound")
                primal_error = max(0., float(np.max(a @ x-b)))
                stationarity = float(np.max(np.abs(objective-a.T@y-lower-upper)))
                gap = float(abs(x[-1]-b@y))
                require(max(primal_error, stationarity, gap) < 2e-7, "Invalid numerical lower-bound certificate")
                maxima["primal_violation"] = max(maxima["primal_violation"], primal_error)
                maxima["dual_stationarity"] = max(maxima["dual_stationarity"], stationarity)
                maxima["duality_gap"] = max(maxima["duality_gap"], gap)
                predictions = []
                for coefficients, role, saved_role in (
                    (x[:n], "green", solution["green"]), (x[n:2*n], branch, solution["opposite"])):
                    spline = BSpline(problem.knots, coefficients, 3)
                    roots = PPoly.from_spline(spline).derivative().roots(extrapolate=False)
                    roots = roots[np.isfinite(roots) & (roots >= problem.wave.min()) & (roots <= problem.wave.max())]
                    continuous_sup = float(np.max(np.abs(spline(np.unique(np.r_[roots, problem.knots])))))
                    budget_error = max(0., continuous_sup-budget)
                    require(budget_error <= 2.1e-9, "Continuous bound violated between pixels or masked gaps")
                    maxima["continuous_budget_violation"] = max(maxima["continuous_budget_violation"], budget_error)
                    changed = problem.flux * (1+spline(problem.wave))
                    fresh_bands = np.array([float(flt.get_ab_maggies(changed, problem.wave)) for flt in problem.filterset])
                    require(np.all(fresh_bands > 0), "Invalid signed-pixel integral")
                    mags = -2.5*np.log10(fresh_bands[:4])
                    require(np.max(np.abs(mags-observed)-errors) <= 2e-7, "Witness misses original PS1 boxes")
                    close(mags, saved_role["PS1_synthetic_griz_mag"], "Fresh PS1 magnitudes")
                    xyz0, xyz = direct_xyz(problem.wave, problem.flux), direct_xyz(problem.wave, changed)
                    require(np.all(xyz >= xyz0 * .9e-8), "Invalid XYZ")
                    scale = np.max(np.abs(colour.XYZ_TO_RGB @ xyz0))
                    rgb = colour.XYZ_TO_RGB @ xyz
                    differences = {"G-R": float(rgb[1]-rgb[0])/scale, "G-B": float(rgb[1]-rgb[2])/scale}
                    require((min(differences.values()) >= guard-2e-7) if role == "green"
                            else differences[role] <= -guard+2e-7, "Witness is not in its strict colour class")
                    for channel in differences:
                        close(differences[channel], saved_role["normalized_channel_differences"][channel], "Direct XYZ channels", 2e-9)
                    if proposal["kind"] == "ideal_XYZ":
                        predicted = xyz / xyz0
                    elif proposal["kind"] == "none":
                        predicted = np.empty(0)
                    else:
                        indices = proposal["indices"]
                        predicted = fresh_bands[indices] / problem.baseline[indices]
                    linear = 1+proposed@coefficients
                    err = float(np.max(np.abs(predicted-linear), initial=0))
                    require(err < 2e-9, "Synthetic integration disagrees with LP flux operator")
                    maxima["direct_integration_error"] = max(maxima["direct_integration_error"], err)
                    predictions.append(predicted)
                    n_witnesses += 1
                distance = float(np.max(np.abs(predictions[0]-predictions[1]), initial=0))
                close(distance, x[-1], "Continuous witness and finite-grid optimum", 2e-7)
                close(distance, solution["minimum_max_baseline_relative_flux_separation"], "Saved separation", 2e-7)
                close(predictions[0], solution["proposed_green_flux_over_baseline"], "Saved green-band witness", 2e-9)
                close(predictions[1], solution["proposed_opposite_flux_over_baseline"], "Saved opposite-band witness", 2e-9)
                close(max(0.,float(b@y))/2,solution["uniform_error_half_width_from_dual_lower_bound"],"Dual-side error half-width",2e-9)
                close(distance/2,solution["uniform_error_half_width_from_witness_upper_bound"],"Witness-side error half-width",2e-9)
                accepted.append(distance)
            require(row["both_strict_classes_feasible"] == bool(accepted), "Wrong union status")
            if accepted:
                close(min(accepted), row["minimum_max_baseline_relative_flux_separation"], "Opposite-set union", 2e-7)
                require(row["separation_error_half_width"] <= min(accepted)/2+2e-9,
                        "Sufficient precision condition must use the lower-bound side")
                if row["minimum_max_baseline_relative_flux_separation"] <= 2e-7:
                    require(row["separation_error_half_width"] == 0.,"Numerical zero became a positive precision requirement")

    full = documents["full"]["results"]
    index = {(r["source_id"], r["spacing_A"], r["relative_shape_budget"], r["proposal"]["name"]): r for r in full}
    nested = 0
    for row in full:
        sid, spacing, budget = row["source_id"], row["spacing_A"], row["relative_shape_budget"]
        if row["proposal"]["kind"] != "ideal_XYZ":
            for other in full:
                if (other["source_id"], other["spacing_A"], other["relative_shape_budget"]) != (sid, spacing, budget):
                    continue
                if other["proposal"]["kind"] == "ideal_XYZ":
                    continue
                if set(row["proposal"]["indices"]) < set(other["proposal"]["indices"]):
                    require(row["both_strict_classes_feasible"] == other["both_strict_classes_feasible"], "Proposed bands changed feasibility")
                    if row["both_strict_classes_feasible"]:
                        require(row["minimum_max_baseline_relative_flux_separation"] <= other["minimum_max_baseline_relative_flux_separation"]+2e-7,
                                "More proposed bands reduced the minimax distance")
                    nested += 1
        if budget == .05:
            other = index[(sid, spacing, .10, row["proposal"]["name"])]
            if row["both_strict_classes_feasible"]:
                require(other["both_strict_classes_feasible"], "Larger spectral budget removed a feasible pair")
                require(other["minimum_max_baseline_relative_flux_separation"] <= row["minimum_max_baseline_relative_flux_separation"]+2e-7,
                        "Expanded spectral set increased its minimum separation")
            nested += 1
        if row["proposal"]["kind"] == "ideal_XYZ" and row["both_strict_classes_feasible"]:
            require(row["minimum_max_baseline_relative_flux_separation"] > 1e-5, "Ideal XYZ positive control lost separation")
    closure_diffs = []
    for row in documents["closure10"]["results"]:
        standard = index[(row["source_id"], row["spacing_A"], row["relative_shape_budget"], row["proposal"]["name"])]
        require(row["both_strict_classes_feasible"] == standard["both_strict_classes_feasible"], "Closure changed bounded colour-class feasibility")
        if row["both_strict_classes_feasible"]:
            closure_diffs.append(abs(row["minimum_max_baseline_relative_flux_separation"]-standard["minimum_max_baseline_relative_flux_separation"]))
    summary = {"design_cases": len(full), "closure_sensitivity_cases": len(documents["closure10"]["results"]),
               "colour_branch_optimization_problems": 2*(len(full)+len(documents["closure10"]["results"])),
               "internal_solver_calls_including_extrema_cuts_and_retries": sum(
                   len(solution["solver_attempts"]) for data in documents.values()
                   for row in data["results"] for solution in row["branches"]),
               "continuous_witness_spectra_reintegrated": n_witnesses,
               "infeasible_branches_replayed": n_infeasible, "nested_set_checks": nested,
               "maximum_closure_distance_change": max(closure_diffs, default=0.),
               "numerical_residual_maxima": maxima}
    return {"summary": summary, "checked_files": checked,
            "limitations": "Floating-point primal/dual replay; conditional spline space, fixed response tables and hard PS1 boxes. No measured additional fluxes or confidence probabilities enter this prospective design."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--write-report", action="store_true")
    args = parser.parse_args()
    result = verify(args.root)
    if args.write_report:
        (ROOT / "research/measurement_design/verification.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result["summary"], indent=2))
