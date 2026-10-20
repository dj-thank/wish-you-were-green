#!/usr/bin/env python3
"""Minimum continuous multiplicative change satisfying measured-band boxes."""
from __future__ import annotations

import numpy as np
from scipy.interpolate import BSpline

import colour_pipeline as colour
from research.measurement_design.coupled_colour_sets import checked_linprog, extrema, EXTREMA_TOL


def solve_minimum(problem, observed, errors, goal, guard=.005, cap=.95):
    observed, errors = np.asarray(observed), np.asarray(errors)
    if not (len(observed) == len(errors) == len(problem.baseline)):
        raise ValueError("Every filter must have exactly one actual measurement/error box")
    if not np.all(np.isfinite(observed)) or not np.all(np.isfinite(errors) & (errors > 0)):
        raise ValueError("Invalid measurement")
    low = 10**(-.4*(observed+errors))/problem.baseline-1
    high = 10**(-.4*(observed-errors))/problem.baseline-1
    fixed_a = [*problem.anchors, *(-problem.anchors),
               *(-problem.xyz_changes/problem.xyz[:, None])]
    fixed_b = [*high, *(-low), *([1-1e-8]*3)]
    if goal == "green_strict":
        for channel in ("G-R", "G-B"):
            fixed_a.append(-problem.change[channel])
            fixed_b.append(problem.difference[channel]-guard)
    elif goal in ("G_lt_R_strict", "G_lt_B_strict"):
        channel = {"G_lt_R_strict": "G-R", "G_lt_B_strict": "G-B"}[goal]
        fixed_a.append(problem.change[channel])
        fixed_b.append(-problem.difference[channel]-guard)
    elif goal != "photometry":
        raise ValueError(goal)
    fixed_a = np.column_stack((fixed_a, np.zeros(len(fixed_b))))
    fixed_b = np.asarray(fixed_b)
    grid = np.unique(np.r_[np.arange(problem.wave.min(), problem.wave.max(), 8), problem.knots])
    objective = np.r_[np.zeros(problem.n), 1.]
    attempts = []
    result = {"goal": goal, "normalized_guard": guard, "cap": cap, "success": False}
    for iteration in range(150):
        basis = BSpline.design_matrix(grid, problem.knots, 3).toarray()
        matrix = np.vstack((np.column_stack((basis, -np.ones(len(basis)))),
                            np.column_stack((-basis, -np.ones(len(basis)))), fixed_a))
        rhs = np.r_[np.zeros(2*len(basis)), fixed_b]
        fit = checked_linprog(objective, matrix=matrix, rhs=rhs,
                              bounds=[(None, None)]*problem.n+[(0, cap)],
                              attempts=attempts, stage="measured_minimum_shape")
        if not fit.success:
            result.update(status="no_fit_within_95_percent_model_cap", solver_attempts=attempts,
                          solver_status=int(fit.status))
            return result
        x, values = extrema(problem.knots, fit.x[:-1], problem.wave.min(), problem.wave.max())
        supremum = float(np.max(np.abs(values)))
        if supremum <= fit.fun+EXTREMA_TOL:
            break
        grid = np.unique(np.r_[grid, x])
    else:
        raise RuntimeError("Measured-band continuous bound failed to converge")
    coefficients = fit.x[:-1]
    changed = problem.flux * (1+problem.basis@coefficients)
    maggies = np.array([float(flt.get_ab_maggies(changed, problem.wave)) for flt in problem.filterset])
    if np.any(maggies <= 0):
        raise AssertionError("Invalid integrated flux")
    magnitudes = -2.5*np.log10(maggies)
    xyz = problem.xyz_operator.T@changed
    rgb = colour.XYZ_TO_RGB@xyz
    differences = {"G-R": float(rgb[1]-rgb[0])/problem.scale,
                   "G-B": float(rgb[1]-rgb[2])/problem.scale}
    colour_violation = (max(0., guard-min(differences.values())) if goal == "green_strict" else
                        max(0., guard+differences[channel]) if goal != "photometry" else 0.)
    box_violation = float(max(0., np.max(np.abs(magnitudes-observed)-errors)))
    primal = float(max(0., np.max(matrix@fit.x-rhs)))
    dual = np.asarray(fit.ineqlin.marginals)
    lower, upper = np.asarray(fit.lower.marginals), np.asarray(fit.upper.marginals)
    stationarity = float(np.max(np.abs(objective-matrix.T@dual-lower-upper)))
    dual_value = float(rhs@dual+cap*upper[-1])
    gap = float(fit.fun-dual_value)
    if max(colour_violation, box_violation, primal, stationarity, abs(gap), supremum-cap) > 2e-7:
        raise AssertionError((colour_violation, box_violation, primal, stationarity, gap, supremum))
    result.update(
        success=True, status="feasible", solver_status=0, solver_attempts=attempts,
        minimum_max_fractional_distortion=float(fit.fun),
        continuous_witness_supremum=supremum, extrema_iterations=iteration+1,
        numerical_supremum_gap=supremum-float(fit.fun),
        spline_coefficients=coefficients.tolist(), constraint_grid_A=grid.tolist(),
        dual_inequality=dual.tolist(), dual_lower=lower.tolist(), dual_upper=upper.tolist(),
        finite_grid_dual_objective=dual_value, duality_gap=gap, dual_stationarity=stationarity,
        synthetic_mag_all_bands=magnitudes.tolist(),
        normalized_channel_differences=differences,
        max_photometry_box_violation_mag=box_violation,
        max_colour_constraint_violation=colour_violation,
        metrics=colour.integrate_colour(problem.wave, changed, mask_sky=False),
    )
    return result
