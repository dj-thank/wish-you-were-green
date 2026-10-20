#!/usr/bin/env python3
"""Minimum additional-flux separation between strict opposite colour sets.

Both spectra satisfy the same measured PS1 boxes and a continuous spline bound.
The result is a conditional minimax design calculation, not a calibrated error
probability. Proposed fluxes are normalized to fixed baseline band fluxes.
"""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import numpy as np
from scipy.interpolate import BSpline, PPoly
from scipy.optimize import linprog

import colour_pipeline as colour

EXTREMA_TOL = 2e-9
CHECK_TOL = 2e-7


def checked_linprog(objective, *, matrix, rhs, bounds, attempts, stage):
    """Retry numerical solver failures without changing scientific constraints."""
    for method, presolve in (("highs", True), ("highs-ds", False),
                              ("highs-ipm", True), ("highs-ipm", False)):
        fitted = linprog(objective, A_ub=matrix, b_ub=rhs, bounds=bounds,
                         method=method, options={"presolve": presolve,
                             "primal_feasibility_tolerance": 1e-10,
                             "dual_feasibility_tolerance": 1e-10})
        attempts.append({"stage": stage, "method": method, "presolve": presolve,
                         "status": int(fitted.status), "message": fitted.message})
        if fitted.status in (0, 2):
            return fitted
    raise RuntimeError(f"All fixed-constraint LP solvers failed: {attempts[-4:]}")


def extrema(knots, coefficients, minimum, maximum):
    spline = BSpline(knots, coefficients, 3)
    roots = PPoly.from_spline(spline).derivative().roots(extrapolate=False)
    roots = roots[np.isfinite(roots) & (roots >= minimum) & (roots <= maximum)]
    wave = np.unique(np.r_[roots, knots])
    values = spline(wave)
    return wave, values


def build_constraints(problem, observed, errors, proposed, budget, guard,
                      opposite, green_grid, other_grid):
    """Independent coefficient blocks, followed by the nonnegative L∞ variable."""
    n = problem.n
    total = 2 * n + 1
    matrices, rhs, blocks = [], [], []

    def append(matrix, bound, name):
        matrix = np.atleast_2d(matrix)
        bound = np.atleast_1d(bound)
        if matrix.shape != (len(bound), total):
            raise AssertionError((name, matrix.shape, bound.shape, total))
        start = sum(len(x) for x in rhs)
        matrices.append(matrix)
        rhs.append(bound)
        blocks.append({"name": name, "start": start, "stop": start + len(bound)})

    low = 10 ** (-0.4 * (observed + errors)) / problem.baseline[:4] - 1
    high = 10 ** (-0.4 * (observed - errors)) / problem.baseline[:4] - 1
    for label, offset, grid in (("green", 0, green_grid),
                                ("opposite", n, other_grid)):
        def embed(local):
            local = np.atleast_2d(local)
            full = np.zeros((len(local), total))
            full[:, offset:offset+n] = local
            return full

        bound_basis = BSpline.design_matrix(grid, problem.knots, 3).toarray()
        append(embed(bound_basis), np.full(len(grid), budget), label + "_upper_spline")
        append(embed(-bound_basis), np.full(len(grid), budget), label + "_lower_spline")
        append(embed(problem.anchors[:4]), high, label + "_upper_PS1")
        append(embed(-problem.anchors[:4]), -low, label + "_lower_PS1")
        append(embed(-problem.xyz_changes / problem.xyz[:, None]),
               np.full(3, 1 - 1e-8), label + "_positive_XYZ")
        if label == "green":
            for channel in ("G-R", "G-B"):
                append(embed(-problem.change[channel]),
                       problem.difference[channel] - guard, label + "_" + channel)
        else:
            if opposite not in ("G-R", "G-B"):
                raise ValueError(opposite)
            append(embed(problem.change[opposite]),
                   -problem.difference[opposite] - guard, label + "_" + opposite)

    if len(proposed):
        # The baseline cancels: Fg/F0 - Fo/F0 = M(ag-ao).
        difference = np.column_stack((proposed, -proposed, -np.ones(len(proposed))))
        reverse = np.column_stack((-proposed, proposed, -np.ones(len(proposed))))
        append(difference, np.zeros(len(proposed)), "proposed_positive_difference")
        append(reverse, np.zeros(len(proposed)), "proposed_negative_difference")
    return np.vstack(matrices), np.concatenate(rhs), blocks


def evaluate_spectrum(problem, coefficients, observed, errors, filterset, guard, role):
    changed = problem.flux * (1 + problem.basis @ coefficients)
    fresh_flux = np.array([float(flt.get_ab_maggies(changed, problem.wave))
                           for flt in filterset])
    if np.any(fresh_flux <= 0):
        raise AssertionError("Nonpositive proposed or measured integrated flux")
    magnitudes = -2.5 * np.log10(fresh_flux[:4])
    box_violation = float(max(0., np.max(np.abs(magnitudes - observed) - errors)))
    xyz = problem.xyz_operator.T @ changed
    rgb = colour.XYZ_TO_RGB @ xyz
    channels = {"G-R": float(rgb[1]-rgb[0]) / problem.scale,
                "G-B": float(rgb[1]-rgb[2]) / problem.scale}
    if role == "green":
        colour_violation = max(0., guard - min(channels.values()))
    else:
        colour_violation = max(0., guard + channels[role])
    if box_violation > CHECK_TOL or colour_violation > CHECK_TOL:
        raise AssertionError((box_violation, colour_violation))
    return {
        "PS1_synthetic_griz_mag": magnitudes.tolist(),
        "PS1_box_violation_mag": box_violation,
        "normalized_channel_differences": channels,
        "colour_guard_violation": float(colour_violation),
        "xyz": xyz.tolist(),
        "metrics": colour.integrate_colour(problem.wave, changed, mask_sky=False),
    }, changed, fresh_flux


def solve_pair(problem, observed, errors, proposed, filterset, budget, guard,
               opposite, proposed_kind="survey", proposed_indices=None):
    """Return a primal/dual record and arrays needed for independent replay."""
    proposed = np.asarray(proposed, dtype=float).reshape((-1, problem.n))
    observed, errors = np.asarray(observed), np.asarray(errors)
    if len(observed) != 4 or len(errors) != 4 or not (0 < budget < 1) or guard <= 0:
        raise ValueError("Unexpected frozen design")
    initial = np.unique(np.r_[np.arange(problem.wave.min(), problem.wave.max(), 8),
                              problem.knots])
    green_grid, other_grid = initial.copy(), initial.copy()
    objective = np.r_[np.zeros(2 * problem.n), 1.]
    result = {"success": False, "opposite_branch": opposite,
              "relative_shape_budget": budget, "normalized_guard": guard,
              "n_spline_coefficients": problem.n, "n_proposed_bands": len(proposed)}
    attempts = []
    witness_strategy = "analytic_extrema_cuts"
    for iteration in range(120):
        matrix, rhs, blocks = build_constraints(
            problem, observed, errors, proposed, budget, guard, opposite,
            green_grid, other_grid)
        fit = checked_linprog(objective, matrix=matrix, rhs=rhs,
                              bounds=[(None, None)] * (2 * problem.n) + [(0, None)],
                              attempts=attempts, stage="outer_finite_grid")
        if not fit.success:
            if fit.status != 2:
                raise RuntimeError(f"Coupled programme failed: {fit.message}")
            result.update(status="no_opposite_pair_in_this_bounded_space",
                          solver_status=int(fit.status), solver_message=fit.message,
                          extrema_iterations=iteration + 1, solver_attempts=attempts)
            return result, None
        green = fit.x[:problem.n]
        other = fit.x[problem.n:2*problem.n]
        gx, gv = extrema(problem.knots, green, problem.wave.min(), problem.wave.max())
        ox, ov = extrema(problem.knots, other, problem.wave.min(), problem.wave.max())
        max_g, max_o = float(np.max(np.abs(gv))), float(np.max(np.abs(ov)))
        if max(max_g, max_o) <= budget + EXTREMA_TOL:
            break
        if iteration == 0:
            # A bounded coefficient convex hull is sufficient (not necessary)
            # for a continuous B-spline bound. If that inner set supplies a
            # witness at the outer LP lower bound, it closes the numerical gap
            # without chasing a highly degenerate sequence of extrema. Keep
            # the OUTER dual certificate; an inner-set optimum alone would
            # not certify the original problem. Never label an inner failure
            # as infeasibility of the full continuous spectral space.
            inner = checked_linprog(
                objective, matrix=matrix, rhs=rhs,
                bounds=[(-budget, budget)]*(2*problem.n)+[(0, float(fit.fun)+1e-9)],
                attempts=attempts, stage="optional_continuous_inner_witness")
            if inner.success:
                fit.x, fit.fun = inner.x, float(inner.fun)
                green, other = fit.x[:problem.n], fit.x[problem.n:2*problem.n]
                gx, gv = extrema(problem.knots, green, problem.wave.min(), problem.wave.max())
                ox, ov = extrema(problem.knots, other, problem.wave.min(), problem.wave.max())
                max_g, max_o = float(np.max(np.abs(gv))), float(np.max(np.abs(ov)))
                if max(max_g, max_o) <= budget + EXTREMA_TOL:
                    witness_strategy = "coefficient_hull_witness_at_outer_dual_bound"
                    break
        if max_g > budget + EXTREMA_TOL:
            green_grid = np.unique(np.r_[green_grid, gx])
        if max_o > budget + EXTREMA_TOL:
            other_grid = np.unique(np.r_[other_grid, ox])
    else:
        raise RuntimeError("Continuous pair constraints did not converge")

    gs, gf, gphot = evaluate_spectrum(problem, green, observed, errors, filterset,
                                     guard, "green")
    os, of, ophot = evaluate_spectrum(problem, other, observed, errors, filterset,
                                     guard, opposite)
    if proposed_kind == "ideal_XYZ":
        independent_g = np.asarray(gs["xyz"]) / problem.xyz
        independent_o = np.asarray(os["xyz"]) / problem.xyz
    elif proposed_kind == "none":
        independent_g = independent_o = np.empty(0)
    else:
        if proposed_indices is None:
            raise ValueError("Survey proposed indices are required")
        ix = np.asarray(proposed_indices, dtype=int)
        independent_g = gphot[ix] / problem.baseline[ix]
        independent_o = ophot[ix] / problem.baseline[ix]
    linear_g = 1 + proposed @ green
    linear_o = 1 + proposed @ other
    operator_error = float(max(np.max(np.abs(independent_g - linear_g), initial=0),
                               np.max(np.abs(independent_o - linear_o), initial=0)))
    distance = float(np.max(np.abs(independent_g - independent_o), initial=0))
    primal_violation = float(max(0, np.max(matrix @ fit.x - rhs)))
    dual = np.asarray(fit.ineqlin.marginals)
    lower = np.asarray(fit.lower.marginals)
    upper = np.asarray(fit.upper.marginals)
    stationarity = float(np.max(np.abs(objective - matrix.T @ dual - lower - upper)))
    dual_value = float(rhs @ dual)  # The only finite variable bound is t>=0.
    dual_gap = float(fit.fun - dual_value)
    wrong_dual_sign = float(max(0, np.max(dual), -np.min(lower), np.max(upper)))
    if max(primal_violation, stationarity, abs(dual_gap), wrong_dual_sign,
           operator_error, abs(distance-float(fit.fun))) > CHECK_TOL:
        raise AssertionError((primal_violation, stationarity, dual_gap,
                              wrong_dual_sign, operator_error, distance, fit.fun))
    result.update(
        success=True, status="feasible_pair", solver_status=0,
        witness_strategy=witness_strategy, solver_attempts=attempts,
        minimum_max_baseline_relative_flux_separation=float(fit.fun),
        finite_grid_dual_objective=dual_value,
        continuous_witness_separation=distance,
        uniform_error_half_width_from_dual_lower_bound=max(0., dual_value) / 2,
        uniform_error_half_width_from_witness_upper_bound=distance / 2,
        numerically_separated_at_check_tolerance=bool(dual_value > CHECK_TOL),
        extrema_iterations=iteration + 1,
        green_continuous_supremum=max_g, opposite_continuous_supremum=max_o,
        maximum_budget_violation=max(0., max_g-budget, max_o-budget),
        primal_violation=primal_violation, dual_stationarity=stationarity,
        duality_gap=dual_gap, wrong_dual_sign=wrong_dual_sign,
        independent_operator_replay_error=operator_error,
        green=gs, opposite=os,
        proposed_green_flux_over_baseline=independent_g.tolist(),
        proposed_opposite_flux_over_baseline=independent_o.tolist(),
        proposed_green_minus_opposite_mag=(-2.5*np.log10(independent_g/independent_o)).tolist(),
        constraint_blocks=blocks,
    )
    arrays = {"primal": fit.x, "dual_inequality": dual, "dual_lower": lower,
              "dual_upper": upper, "green_constraint_grid_A": green_grid,
              "opposite_constraint_grid_A": other_grid}
    return result, arrays
