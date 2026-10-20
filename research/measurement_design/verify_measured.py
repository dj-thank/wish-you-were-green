#!/usr/bin/env python3
"""Independently re-integrate measured-band witnesses and replay their bounds."""
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
from research.calibration_followup.photometric_feasibility import Problem
from research.measurement_design.measured_constraints import prepare_target, GOALS
from research.measurement_design.verify_outputs import direct_xyz, require, close


def verify(root=ROOT):
    root = Path(root).resolve()
    require(root == ROOT, "Import the verifier from the checkout being verified")
    base = root/"research/measurement_design"
    checked = {}

    def hashed(path, digest=None):
        path = (root/path).resolve()
        require(path.is_relative_to(root), "Path outside checkout")
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        require(digest is None or actual == digest, f"Hash mismatch: {path}")
        checked[str(path.relative_to(root))] = actual
        return path

    data = json.loads(hashed("research/measurement_design/measured_results.json").read_text())
    predictions = json.loads(hashed("research/measurement_design/measured_predictions.json").read_text())
    for path, digest in data["input_and_code_hashes"].items():
        hashed(path, digest)
    source = json.loads((root/"research/independent_photometry/measurements.json").read_text())["measurements"]
    upstream = {(r["source_id"],r["svo_filter_id"]): r for r in source}
    require(len(data["cohort"]) == 25 and len(predictions) == 450, "Frozen cohort/slot accounting")
    require(len(upstream) == len(predictions) == 450, "Duplicate measurement slot")
    expected, natives = set(), {}
    replayed_prediction = []
    for sid in data["cohort"]:
        natives[(sid, "strict", 0.)] = prepare_target(sid)
        w, f, baseline, filters, obs, err, meta, rows = natives[(sid, "strict", 0.)]
        hashed(meta["input_path"], meta["input_sha256"])
        for row in rows:
            original = upstream[(sid, row["svo_filter_id"])]
            for field, value in original.items():
                require(row[field] == value, "An original measurement/quality field changed")
            hashed(row["raw_path"], row["raw_sha256"])
        replayed_prediction.extend(rows)
        settings = [("PS1_only", "strict", 0.)]
        if meta["additional_measurement_count"]:
            settings.extend([("PS1_plus_strict", "strict", x) for x in (0., .02)])
        if sid == "3204436719718449280":
            settings.extend([("PS1_plus_official_good", "official_good", x) for x in (0., .02)])
        for label, quality, margin in settings:
            for spacing in (400, 800, 1600):
                expected.add((sid, label, margin, spacing))
    require(len(expected) == 165, "Expected 165 measured scenarios")
    actual = [(r["source_id"],r["scenario"],r["additional_systematic_box_margin_mag"],r["spacing_A"]) for r in data["scenarios"]]
    require(len(actual) == len(set(actual)) and set(actual) == expected, "Missing or duplicate measured scenarios")
    pred_index = {(r["source_id"],r["svo_filter_id"]): r for r in predictions}
    for row in replayed_prediction:
        saved = pred_index[(row["source_id"],row["svo_filter_id"])]
        for field in ("passband_covered", "used_in_joint_fit", "analysis_exclusion", "adopted",
                      "mag_ab", "mag_error_quoted", "mag_error_with_zeropoint"):
            require(row[field] == saved[field], f"Prediction metadata changed: {field}")
        for field in ("baseline_predicted_mag_ab", "baseline_prediction_minus_observation_mag"):
            if row[field] is None:
                require(saved[field] is None, "Missing data was filled or spectrum extrapolated")
            else:
                close(row[field], saved[field], "Direct pre-fit prediction", 2e-9)
    require(sum(r["used_in_joint_fit"] for r in predictions) == data["strict_covered_measured_bands"] == 46,
            "Expected 46 strictly accepted, spectrally covered extra measurements")
    require(len({r["source_id"] for r in predictions if r["used_in_joint_fit"]}) == 14,
            "Expected 14 candidates with usable extra measurements")
    successes, infeasible, maxima = 0, 0, {"supremum_gap": 0., "photometry_violation_mag": 0., "duality_gap": 0., "dual_stationarity": 0.}
    for row in data["scenarios"]:
        sid, quality, margin = row["source_id"], row["quality_policy"], row["additional_systematic_box_margin_mag"]
        key = (sid,quality,margin)
        if key not in natives:
            natives[key] = prepare_target(sid, quality, margin)
        w, f, baseline, filters, obs, err, meta, _ = natives[key]
        labels = meta["band_labels"]
        if row["scenario"] == "PS1_only":
            baseline, filters, obs, err, labels = baseline[:4], filters[:4], obs[:4], err[:4], labels[:4]
        require(row["band_labels"] == labels, "Measured filter ordering changed")
        close(obs, row["observed_mag_all_bands"], "Original measured magnitudes", 0)
        close(err, row["error_box_half_width_all_bands"], "Recommended errors and explicit box expansion", 0)
        problem = Problem(w, f, baseline, filters, row["spacing_A"])
        require(set(row["solutions"]) == set(GOALS), "Dropped a colour branch")
        low = 10**(-.4*(obs+err))/baseline-1
        high = 10**(-.4*(obs-err))/baseline-1
        n = problem.n
        objective = np.r_[np.zeros(n), 1.]
        for goal, solution in row["solutions"].items():
            cap, guard = solution["cap"], solution["normalized_guard"]
            require(cap == .95 and guard == .005, "Optimization cap or guard changed")
            local_rows = [*problem.anchors, *(-problem.anchors), *(-problem.xyz_changes/problem.xyz[:,None])]
            local_rhs = [*high, *(-low), *([1-1e-8]*3)]
            if goal == "green_strict":
                for channel in ("G-R", "G-B"):
                    local_rows.append(-problem.change[channel]); local_rhs.append(problem.difference[channel]-guard)
            elif goal != "photometry":
                channel = {"G_lt_R_strict":"G-R", "G_lt_B_strict":"G-B"}[goal]
                local_rows.append(problem.change[channel]); local_rhs.append(-problem.difference[channel]-guard)
            if solution["success"]:
                path = hashed(solution["certificate_path"],solution["certificate_sha256"])
                with np.load(path) as saved:
                    grid = saved["constraint_grid_A"]
                    dual, lower, upper = saved["dual_inequality"], saved["dual_lower"], saved["dual_upper"]
            else:
                grid = np.unique(np.r_[np.arange(w.min(),w.max(),8),problem.knots])
            basis = BSpline.design_matrix(grid,problem.knots,3).toarray()
            matrix = np.vstack((np.column_stack((basis,-np.ones(len(basis)))),
                                np.column_stack((-basis,-np.ones(len(basis)))),
                                np.column_stack((local_rows,np.zeros(len(local_rhs))))))
            rhs = np.r_[np.zeros(2*len(basis)),local_rhs]
            if not solution["success"]:
                for method, presolve in (("highs-ipm",True),("highs-ds",False)):
                    fit = linprog(objective,A_ub=matrix,b_ub=rhs,bounds=[(None,None)]*n+[(0,cap)],method=method,
                                  options={"presolve":presolve,"primal_feasibility_tolerance":1e-10,"dual_feasibility_tolerance":1e-10})
                    if fit.status in (0,2):break
                require(fit.status == 2,f"Bounded infeasibility did not replay: {sid} {goal} {row['spacing_A']}")
                infeasible += 1
                continue
            coefficients = np.asarray(solution["spline_coefficients"])
            t = solution["minimum_max_fractional_distortion"]
            x = np.r_[coefficients,t]
            require(np.max(matrix@x-rhs) < 2e-7 and -.0000002 <= t <= cap+2e-7,
                    "Minimum-shape primal certificate invalid")
            require(np.max(dual) < 2e-8 and np.min(lower) > -2e-8 and np.max(upper) < 2e-8,
                    "Minimum-shape dual signs invalid")
            require(np.max(np.abs(lower[:-1])) < 2e-8 and np.max(np.abs(upper[:-1])) < 2e-8,
                    "Free-variable dual bounds must be zero")
            stationarity = float(np.max(np.abs(objective-matrix.T@dual-lower-upper)))
            dual_value = float(rhs@dual+cap*upper[-1])
            gap = abs(t-dual_value)
            require(max(stationarity,gap) < 2e-7,"Minimum-shape lower bound invalid")
            spline = BSpline(problem.knots,coefficients,3)
            roots = PPoly.from_spline(spline).derivative().roots(extrapolate=False)
            roots = roots[np.isfinite(roots)&(roots >= w.min())&(roots <= w.max())]
            extrema = spline(np.unique(np.r_[roots,problem.knots]))
            sup = float(np.max(np.abs(extrema)))
            require(sup-t <= 2.1e-9 and sup <= cap+2.1e-9 and min(1+extrema) >= 1-cap-2.1e-9,
                    "Continuous model bound invalid")
            close(sup,solution["continuous_witness_supremum"],"Saved continuous minimum",2e-9)
            altered = f*(1+spline(w))
            mags = np.array([float(flt.get_ab_magnitude(altered,w)) for flt in filters])
            violation = max(0.,float(np.max(np.abs(mags-obs)-err)))
            require(violation < 2e-7,"Witness fails actual measured-band constraints")
            close(mags,solution["synthetic_mag_all_bands"],"Fresh survey photometry",2e-8)
            xyz,xyz0 = direct_xyz(w,altered),direct_xyz(w,f)
            require(np.all(xyz >= xyz0*.9e-8),"Nonpositive tristimulus integral")
            rgb,scale = colour.XYZ_TO_RGB@xyz,np.max(np.abs(colour.XYZ_TO_RGB@xyz0))
            differences = {"G-R":float(rgb[1]-rgb[0])/scale,"G-B":float(rgb[1]-rgb[2])/scale}
            if goal == "green_strict":require(min(differences.values()) >= guard-2e-7,"Strict green guard failed")
            elif goal != "photometry":require(differences[channel] <= -guard+2e-7,"Strict opposite guard failed")
            for channel,value in differences.items():
                close(value,solution["normalized_channel_differences"][channel],"Direct channel difference",2e-9)
            metrics = colour.xyz_to_metrics(xyz)
            close([metrics["u1960"],metrics["v1960"]],
                  [solution["metrics"]["u1960"],solution["metrics"]["v1960"]],"Direct colour",2e-9)
            maxima["supremum_gap"] = max(maxima["supremum_gap"],sup-t)
            maxima["photometry_violation_mag"] = max(maxima["photometry_violation_mag"],violation)
            maxima["duality_gap"] = max(maxima["duality_gap"],gap)
            maxima["dual_stationarity"] = max(maxima["dual_stationarity"],stationarity)
            successes += 1
    index = {k:r for k,r in zip(actual,data["scenarios"])}
    nesting = 0

    def comparison(restricted, relaxed):
        nonlocal nesting
        for goal in GOALS:
            a,b = restricted["solutions"][goal],relaxed["solutions"][goal]
            if a["success"]:
                require(b["success"],"Restricted model feasible but relaxed model infeasible")
                require(a["continuous_witness_supremum"] >= b["continuous_witness_supremum"]-2e-7,
                        "Nested measured-set minimum reversed")
            nesting += 1

    for row in data["scenarios"]:
        sid,spacing,scenario,margin = row["source_id"],row["spacing_A"],row["scenario"],row["additional_systematic_box_margin_mag"]
        if scenario != "PS1_only":
            comparison(row,index[(sid,"PS1_only",0.,spacing)])
            if margin == 0:
                comparison(row,index[(sid,scenario,.02,spacing)])
        if scenario == "PS1_plus_official_good":
            comparison(row,index[(sid,"PS1_plus_strict",margin,spacing)])
        any_fit = row["solutions"]["photometry"]
        for goal in GOALS[1:]:
            color = row["solutions"][goal]
            if color["success"]:
                require(any_fit["success"] and color["continuous_witness_supremum"] >= any_fit["continuous_witness_supremum"]-2e-7,
                        "Additional colour constraint reduced required shape change")
            nesting += 1
    summary = {"candidate_count":25,"prediction_slots":450,"strict_covered_extra_measurements":46,
               "candidates_with_extra_measurements":14,"scenarios":165,"colour_branch_optimization_problems":660,
               "witness_spectra_reintegrated":successes,"bounded_infeasible_cases_replayed":infeasible,
               "nested_set_checks":nesting,"numerical_residual_maxima":maxima}
    return {"summary":summary,"checked_files":checked,
            "limitations":"Measured-photometry hard boxes and central signed-pixel spectrum; no catalogue independence, variability, physical-atmosphere fit or frequentist significance claim."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root",type=Path,default=ROOT)
    parser.add_argument("--write-report",action="store_true")
    args = parser.parse_args()
    result = verify(args.root)
    if args.write_report:
        (ROOT/"research/measurement_design/measured_verification.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result["summary"],indent=2))
