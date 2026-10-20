#!/usr/bin/env python3
"""Conditional colour identifiability with measured PS1 gri / griz constraints.

This is a bounded sensitivity calculation on frozen observed spectra. It is
not an atmosphere fit, an estimate of actual calibration error, a probability,
or an independent stellar measurement. All 27 original entities are retained;
the 25 with a saved, accepted DESI + PS1 product enter the numerical experiment.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import sys

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MPLCONFIGDIR", "/tmp/wish-green-feasibility-mpl")
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy
from scipy.interpolate import BSpline, PPoly
from scipy.optimize import linprog
import speclite

import colour_pipeline as colour
from research.precision.photometric_nullspace import smooth_basis, colour_operator, exact_photometry_matrix
from research.precision.candidate_recalibration.heldout_z import filter_metadata

HERE = Path(__file__).resolve().parent
INPUT = ROOT / "research/precision/candidate_recalibration"
SPACINGS = (400, 800, 1600)
BANDSETS = ("gri", "griz")
ERROR_MULTIPLIERS = (0, 1, 2)
GOALS = ("photometry", "green_closed", "G_le_R", "G_le_B")
CAP = 0.95
EXTREMA_TOL = 2e-9
MAG_TOL = 1e-7


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def compact_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def load_inputs():
    manifest = json.loads((INPUT / "derivative_manifest.json").read_text())
    cohort = pd.read_csv(INPUT / "standardized_colours.csv", dtype={"source_id": str}).fillna("")
    by_id = {row["source_id"]: row for row in manifest}
    if len(cohort) != 27 or len(by_id) != 25:
        raise AssertionError("Frozen 27-entity / 25-spectrum cohort changed")
    return cohort, by_id


def prepare(row, derivative, filterset):
    path = INPUT / derivative["path"]
    if sha(path) != derivative["sha256"]:
        raise AssertionError(f"Input hash mismatch: {path}")
    with np.load(path) as data:
        original_w = data["wavelength_angstrom"]
        original_f = data["flux_calibrated"]
        original_iv = data["inverse_variance_calibrated"]
    wave, flux, ivar = colour.clean_spectrum(original_w, original_f, original_iv, mask_sky=True)
    # Signed valid samples are retained. The masks remove narrow sky intervals,
    # not broad Na/Mg/carbon absorption. No extinction correction is introduced.
    baseline = np.array([float(flt.get_ab_maggies(flux, wave)) for flt in filterset])
    if not np.all(baseline > 0):
        raise AssertionError("Nonpositive synthetic band flux")
    for flt in filterset:
        if wave.min() > flt.wavelength.min() or wave.max() < flt.wavelength.max():
            raise AssertionError("No passband extrapolation is permitted")
    photo = derivative["photometry_row"]
    observed = np.array([float(photo[f"Pan-STARRS.{b}"]) for b in "griz"])
    errors = np.array([float(photo[f"Pan-STARRS.{b}_error"]) for b in "griz"])
    if not np.all(np.isfinite(observed)) or not np.all(np.isfinite(errors) & (errors > 0)):
        raise AssertionError("Invalid published PS1 photometry")
    meta = {
        "source_id": row["source_id"], "names": row["names"], "WDJname": row["swan_WDJname"],
        "input_path": str(path.relative_to(ROOT)), "input_sha256": sha(path),
        "raw_spectrum_sha256": derivative["original_record"]["sha256"],
        "raw_spectrum_url": derivative["original_record"]["source_url"],
        "photometry_row_sha256": compact_hash(photo),
        "observed_mag_griz": observed.tolist(), "quoted_error_mag_griz": errors.tolist(),
        "cleaned_baseline_mag_griz": (-2.5 * np.log10(baseline)).tolist(),
        "original_pixels": len(original_w), "retained_pixels": len(wave),
        "retained_negative_pixels": int(np.sum(flux < 0)),
        "largest_gap_A": float(np.max(np.diff(wave))),
        "minimum_A": float(wave.min()), "maximum_A": float(wave.max()),
        "nominal_metrics": colour.integrate_colour(wave, flux, mask_sky=False),
    }
    return wave, flux, baseline, observed, errors, meta


class Problem:
    def __init__(self, wave, flux, baseline, filterset, spacing):
        self.wave, self.flux = wave, flux
        self.baseline, self.filterset = baseline, filterset
        self.basis, self.knots = smooth_basis(wave, spacing)
        self.n = self.basis.shape[1]
        self.anchors = exact_photometry_matrix(wave, flux, self.basis, filterset)
        self.xyz_operator = colour_operator(wave)
        self.xyz = self.xyz_operator.T @ flux
        self.xyz_changes = self.xyz_operator.T @ (flux[:, None] * self.basis)
        if not np.all(self.xyz > 0):
            raise AssertionError("Nonpositive baseline XYZ")
        self.rgb = colour.XYZ_TO_RGB @ self.xyz
        self.scale = float(np.max(np.abs(self.rgb)))
        self.difference = {}
        self.change = {}
        for pair, other in (("G-R", 0), ("G-B", 2)):
            operator = colour.XYZ_TO_RGB[1] - colour.XYZ_TO_RGB[other]
            self.difference[pair] = float(operator @ self.xyz) / self.scale
            self.change[pair] = operator @ self.xyz_changes / self.scale
        # This is only an initial cutting grid. Every accepted solution is
        # bounded at all analytic cubic-spline extrema, including masked gaps.
        grid = np.unique(np.r_[np.arange(wave.min(), wave.max(), 8), self.knots])
        self.initial_bounds = BSpline.design_matrix(grid, self.knots, k=3).toarray()

    def solve(self, observed, errors, bands, error_multiplier, goal, channel_margin=0.):
        nband = len(bands)
        # Flux intervals are the exact transformation of magnitude intervals.
        # They are not a multivariate confidence region or a likelihood.
        lo = 10 ** (-0.4 * (observed[:nband] + error_multiplier * errors[:nband]))
        hi = 10 ** (-0.4 * (observed[:nband] - error_multiplier * errors[:nband]))
        lower, upper = lo / self.baseline[:nband] - 1, hi / self.baseline[:nband] - 1
        other_a, other_b = [], []
        # Keep positive integrated XYZ, with a tiny scale-relative floor.
        other_a.extend(-self.xyz_changes / self.xyz[:, None])
        other_b.extend([1 - 1e-8] * 3)
        if goal == "green_closed":
            for pair in ("G-R", "G-B"):
                other_a.append(-self.change[pair]); other_b.append(self.difference[pair] - channel_margin)
        elif goal in ("G_le_R", "G_le_B"):
            pair = {"G_le_R": "G-R", "G_le_B": "G-B"}[goal]
            other_a.append(self.change[pair]); other_b.append(-self.difference[pair] - channel_margin)
        elif goal != "photometry":
            raise ValueError(goal)
        if error_multiplier == 0:
            aeq = np.column_stack((self.anchors[:nband], np.zeros(nband)))
            beq = lower
        else:
            aeq, beq = None, None
            other_a.extend(self.anchors[:nband]); other_b.extend(upper)
            other_a.extend(-self.anchors[:nband]); other_b.extend(-lower)
        fixed_a = np.column_stack((np.asarray(other_a), np.zeros(len(other_a))))
        fixed_b = np.asarray(other_b)
        bound_basis = self.initial_bounds.copy()
        objective = np.r_[np.zeros(self.n), 1.]
        answer = {"goal": goal, "required_normalized_channel_margin": channel_margin, "success": False}
        for iteration in range(120):
            aub = np.vstack((
                np.column_stack((bound_basis, -np.ones(len(bound_basis)))),
                np.column_stack((-bound_basis, -np.ones(len(bound_basis)))), fixed_a,
            ))
            bub = np.r_[np.zeros(2 * len(bound_basis)), fixed_b]
            fitted = linprog(objective, A_ub=aub, b_ub=bub, A_eq=aeq, b_eq=beq,
                             bounds=[(None, None)] * self.n + [(0, CAP)], method="highs",
                             options={"primal_feasibility_tolerance": 1e-10,
                                      "dual_feasibility_tolerance": 1e-10})
            if not fitted.success:
                answer.update(status="infeasible_within_95pct_bound" if fitted.status == 2 else "solver_failure",
                              solver_status=int(fitted.status), solver_message=fitted.message)
                if fitted.status != 2:
                    raise RuntimeError(answer)
                return answer
            spline = BSpline(self.knots, fitted.x[:-1], 3)
            roots = PPoly.from_spline(spline).derivative().roots(extrapolate=False)
            roots = roots[np.isfinite(roots) & (roots >= self.wave.min()) & (roots <= self.wave.max())]
            extrema = np.unique(np.r_[roots, self.knots])
            values = spline(extrema)
            supremum = float(np.max(np.abs(values)))
            if supremum - fitted.fun <= EXTREMA_TOL:
                break
            bound_basis = np.vstack((bound_basis, BSpline.design_matrix(extrema, self.knots, k=3).toarray()))
        else:
            raise RuntimeError(f"Continuous spline bound did not converge: {bands}, k={error_multiplier}, {goal}, gap={supremum-fitted.fun:.3g}, t={fitted.fun:.9g}")
        delta = self.basis @ fitted.x[:-1]
        changed_flux = self.flux * (1 + delta)
        fresh_bands = np.array([float(flt.get_ab_maggies(changed_flux, self.wave)) for flt in self.filterset])
        if not np.all(fresh_bands > 0):
            raise AssertionError("Nonpositive verification band flux")
        mags = -2.5 * np.log10(fresh_bands)
        mag_violation = float(max(0., np.max(np.abs(mags[:nband] - observed[:nband]) - error_multiplier * errors[:nband])))
        xyz = self.xyz_operator.T @ changed_flux
        rgb = colour.XYZ_TO_RGB @ xyz
        differences = {"G-R": float(rgb[1] - rgb[0]) / self.scale, "G-B": float(rgb[1] - rgb[2]) / self.scale}
        colour_violation = (max(0., channel_margin - min(differences.values())) if goal == "green_closed" else
                            max(0., channel_margin + differences[{"G_le_R": "G-R", "G_le_B": "G-B"}[goal]]) if goal != "photometry" else 0.)
        if mag_violation > MAG_TOL or colour_violation > 1e-7 or supremum > CAP + 2e-8 or np.min(xyz / self.xyz) < 0.9e-8:
            raise AssertionError((mag_violation, colour_violation, supremum, xyz / self.xyz))
        answer.update(
            success=True, status="feasible", solver_status=0,
            minimum_max_fractional_distortion=float(fitted.fun),
            continuous_witness_supremum=supremum,
            numerical_supremum_gap=supremum - float(fitted.fun),
            extrema_iterations=iteration + 1,
            minimum_continuous_multiplier=float(1 + np.min(values)),
            maximum_continuous_multiplier=float(1 + np.max(values)),
            synthetic_mag_griz=mags.tolist(),
            max_photometry_box_violation_mag=mag_violation,
            normalized_channel_differences=differences,
            max_colour_constraint_violation=colour_violation,
            metrics=colour.integrate_colour(self.wave, changed_flux, mask_sky=False),
            spline_coefficients=fitted.x[:-1].tolist(),
        )
        return answer


def threshold(solution):
    return solution.get("continuous_witness_supremum") if solution["success"] else None


def check_nesting(results):
    """An added band can only shrink a feasible set; a wider box expands it."""
    index = {(r["source_id"], r["spacing_A"], r["bands"], r["error_multiplier"]): r for r in results}
    checks = 0
    for row in results:
        for goal in GOALS:
            current = row["solutions"][goal]
            before = []
            if row["bands"] == "griz":
                before.append(index[(row["source_id"], row["spacing_A"], "gri", row["error_multiplier"])]["solutions"][goal])
            # The current (narrower) error box is the more restricted problem.
            if row["error_multiplier"] < max(ERROR_MULTIPLIERS):
                before.append(index[(row["source_id"], row["spacing_A"], row["bands"], row["error_multiplier"] + 1)]["solutions"][goal])
            for less_restricted in before:
                if current["success"]:
                    if not less_restricted["success"]:
                        raise AssertionError("Feasible restricted problem but infeasible relaxed problem")
                    if threshold(current) + 2e-7 < threshold(less_restricted):
                        raise AssertionError("Nested feasible-set minimum reversed")
                checks += 1
        fit = row["solutions"]["photometry"]
        for goal in GOALS[1:]:
            restricted = row["solutions"][goal]
            if restricted["success"] and (not fit["success"] or threshold(restricted) + 2e-7 < threshold(fit)):
                raise AssertionError("Adding a colour constraint reduced the minimum")
            checks += 1
    return checks


def make_plots(table, cohort_meta):
    selected = [(sid, meta) for sid, meta in cohort_meta.items()
                if str(meta["WDJname"]).startswith(("WDJ0913", "WDJ0429"))]
    fig, axes = plt.subplots(len(selected), 3, figsize=(12, 3.7 * len(selected)), sharey="row", layout="constrained", squeeze=False)
    for i, (sid, meta) in enumerate(selected):
        for j, spacing in enumerate(SPACINGS):
            ax = axes[i, j]
            d = table[(table.source_id == sid) & (table.spacing_A == spacing)]
            for bands, style, col in (("gri", "--", "#626262"), ("griz", "-", "#166590")):
                q = d[d.bands == bands].sort_values("error_multiplier")
                ax.plot(q.error_multiplier, 100 * q.photometry_threshold, style, color=col, marker="o", label=f"{bands}: fit measurements")
                ax.plot(q.error_multiplier, 100 * q.non_green_threshold, style, color=col, marker="s", alpha=.85, label=f"{bands}: allow G <= R or B")
            ax.set_title(f"{meta['WDJname']}\n{spacing} Å knot spacing", fontsize=9)
            ax.set_xticks(ERROR_MULTIPLIERS); ax.set_xlabel("Quoted-error box multiplier k")
            ax.grid(alpha=.2)
            if j == 0: ax.set_ylabel("Minimum additional shape change (%)")
            if i == 0 and j == 2: ax.legend(fontsize=7)
        # Set row limits after all three panels have been populated. Setting a
        # lower limit early freezes shared-axis autoscaling and can hide later
        # (larger) thresholds, particularly the 1600 A exact-anchor scenario.
        row_values = table[table.source_id == sid][["photometry_threshold", "non_green_threshold"]].to_numpy()
        axes[i, 0].set_ylim(0, 108 * float(np.nanmax(row_values)))
    fig.suptitle("Measured PS1 constraints and green-channel sensitivity\nConditional spline feasibility; k is not a joint confidence level", fontsize=13)
    fig.savefig(HERE / "green_constraint_sensitivity.png", dpi=180)
    fig.savefig(HERE / "green_constraint_sensitivity.svg")
    plt.close(fig)
    d = table[(table.spacing_A == 800) & (table.error_multiplier == 1)]
    order = d[d.bands == "griz"].sort_values("photometry_threshold").source_id.tolist()
    labels = [cohort_meta[s]["WDJname"].removeprefix("WDJ") for s in order]
    fig, ax = plt.subplots(figsize=(10, 9), layout="constrained")
    for bands, col, marker in (("gri", "#707070", "o"), ("griz", "#166590", "s")):
        q = d[d.bands == bands].set_index("source_id").reindex(order)
        ax.scatter(100 * q.photometry_threshold, np.arange(len(q)), label=bands, color=col, marker=marker, s=28)
    ax.set_yticks(np.arange(len(order)), labels, fontsize=8)
    ax.set_xlabel("Minimum additional multiplicative distortion to fit photometry (%)")
    ax.set_title("All 25 fixed candidates: central spectrum versus observed PS1\n800 Å spline knots; each magnitude within one quoted error")
    ax.grid(axis="x", alpha=.2); ax.legend(title="Constrained bands")
    fig.savefig(HERE / "cohort_photometry_feasibility.png", dpi=180)
    fig.savefig(HERE / "cohort_photometry_feasibility.svg")
    plt.close(fig)


def run(source_ids=None):
    cohort, derivatives = load_inputs()
    filter_pairs = [filter_metadata(b) for b in "griz"]
    filterset = [p[0] for p in filter_pairs]
    results, meta, omissions = [], {}, []
    for _, source_row in cohort.iterrows():
        row = source_row.to_dict(); sid = row["source_id"]
        if sid not in derivatives:
            omissions.append({"source_id": sid, "names": row["names"], "reason": row["status"]})
            continue
        if source_ids and sid not in source_ids:
            continue
        wave, flux, baseline, obs, err, info = prepare(row, derivatives[sid], filterset)
        meta[sid] = info
        for spacing in SPACINGS:
            problem = Problem(wave, flux, baseline, filterset, spacing)
            for bands in BANDSETS:
                for multiplier in ERROR_MULTIPLIERS:
                    solved = {goal: problem.solve(obs, err, bands, multiplier, goal) for goal in GOALS}
                    alternatives = [g for g in ("G_le_R", "G_le_B") if solved[g]["success"]]
                    selected = min(alternatives, key=lambda g: threshold(solved[g])) if alternatives else None
                    results.append({"source_id": sid, "spacing_A": spacing, "bands": bands,
                                    "error_multiplier": multiplier, "spline_knots_angstrom": problem.knots.tolist(),
                                    "solutions": solved, "non_green_selected_goal": selected})
            print(sid, info["WDJname"], spacing, "complete", flush=True)
        # Durable, small checkpoint; finalized results below include all hashes.
        (HERE / "feasibility_results.partial.json").write_text(json.dumps({"cohort": meta, "results": results}, separators=(",", ":")) + "\n")
    nested_checks = check_nesting(results)
    flattened = []
    for result in results:
        s = result["solutions"]
        nongreen = result["non_green_selected_goal"]
        item = {k: result[k] for k in ("source_id", "spacing_A", "bands", "error_multiplier")}
        item.update(WDJname=meta[result["source_id"]]["WDJname"],
                    photometry_threshold=threshold(s["photometry"]), green_closed_threshold=threshold(s["green_closed"]),
                    non_green_threshold=threshold(s[nongreen]) if nongreen else None, non_green_selected_goal=nongreen)
        for budget in (2, 5, 10, 20):
            g, ng = item["green_closed_threshold"], item["non_green_threshold"]
            has_g = g is not None and g <= budget / 100 + 2e-8
            has_ng = ng is not None and ng <= budget / 100 + 2e-8
            item[f"at_{budget}pct"] = ("both_closed_regions_feasible" if has_g and has_ng else "green_closed_only" if has_g else "non_green_only" if has_ng else "photometry_incompatible_with_budget")
        flattened.append(item)
    table = pd.DataFrame(flattened)
    out = {
        "schema_version": 1, "created_utc": datetime.now(timezone.utc).isoformat(),
        "design": {
            "cohort": "Frozen initial 27 entities; all 25 accepted DESI + PS1 spectra; 2 unavailable retained with reasons",
            "multiplicative_model": "F_new(lambda) = F_saved_cleaned(lambda) * [1 + cubic_B_spline(lambda) @ a]",
            "objective": "Minimum continuous supremum of absolute fractional change across the entire retained spectral range",
            "spacing_A": list(SPACINGS), "bands": list(BANDSETS), "quoted_error_box_multiplier": list(ERROR_MULTIPLIERS),
            "error_policy": "Swan published PS1 errors already contain their 0.01 mag quadrature floor. No additional floor is added here. The saved baseline used max(quoted error, 0.02 mag); this new experiment varies measured-band intervals explicitly.",
            "box_definition": "For each used band, observed_mag - k*quoted_error <= synthetic_mag <= observed_mag + k*quoted_error; k=0 fixes the catalogue central values",
            "positive_multiplier_floor": 1 - CAP,
            "XYZ_policy": "Each integrated XYZ component is constrained above 1e-8 of its positive baseline value",
            "colour_sets": "green_closed = G>=R and G>=B; non_green = (G<=R) or (G<=B), solved as two LPs. Ties belong to both sets; strict green dominance is not certified by a boundary witness.",
            "norm_computation": "8 A initial constraint grid plus knots; iterative inclusion of all analytic derivative roots and knots; final continuous witness supremum checked against LP objective",
            "scope": "Observed colour at Earth; fixed signed spectral samples after the existing finite/IVAR and narrow sky masks; same PS1 survey; no extinction correction, new noise draw or inter-survey independence assumption",
            "limitations": [
                "Existence/minimum in chosen spline spaces, not inferred calibration error, confidence, probability or atmosphere-model perturbation",
                "Error boxes are neither a joint confidence region nor a covariance model; PS1 shared errors and non-simultaneity are not inferred",
                "Adding z in griz uses it for fitting. It must no longer be described as held out in that scenario",
                "Results condition on the frozen selected spectra. Pixel covariance, bit masks absent from MWDD arrays and unknown systematics remain",
                "Spacing choices are sensitivity scenarios, not measured instrumental correlation lengths",
                "Numerical LP/extrema agreement is not a formal interval-arithmetic optimality certificate",
                "Failure with t<=0.95 is infeasibility within this bounded model, not proof that a real star cannot have a given colour",
            ],
        },
        "software": {"python": platform.python_version(), "numpy": np.__version__, "scipy": scipy.__version__, "speclite": speclite.__version__, "matplotlib": matplotlib.__version__},
        "input_sha256": {str((INPUT / f).relative_to(ROOT)): sha(INPUT / f) for f in ("derivative_manifest.json", "standardized_colours.csv")},
        "code_sha256": {str(p.relative_to(ROOT)): sha(p) for p in (Path(__file__), ROOT / "colour_pipeline.py", ROOT / "research/precision/photometric_nullspace.py", ROOT / "research/precision/candidate_recalibration/heldout_z.py")},
        "filter_metadata": [p[1] for p in filter_pairs], "cohort": meta, "unavailable_entities": omissions,
        "n_scenarios": len(results), "n_LPs": len(results) * len(GOALS), "nested_invariant_checks": nested_checks,
        "results": results,
    }
    suffix = ".pilot" if source_ids else ""
    (HERE / f"feasibility_results{suffix}.json").write_text(json.dumps(out, indent=2, allow_nan=False) + "\n")
    table.to_csv(HERE / f"feasibility_summary{suffix}.csv", index=False)
    if not source_ids:
        make_plots(table, meta)
        (HERE / "feasibility_results.partial.json").unlink(missing_ok=True)
    print("DONE", len(meta), "spectra", len(results), "scenarios", nested_checks, "nested checks", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-id", action="append", help="Pilot: run just this ID without replacing final results")
    args = parser.parse_args()
    run(args.source_id)
