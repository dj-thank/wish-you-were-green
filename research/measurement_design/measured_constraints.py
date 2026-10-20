#!/usr/bin/env python3
"""Test actual extra-survey measurements in their own fully covered passbands."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MPLCONFIGDIR", "/tmp/wish-green-measured-mpl")
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd

from research.calibration_followup.photometric_feasibility import load_inputs, prepare, Problem, filter_metadata
from research.measurement_design.profiles import load_profiles
from research.measurement_design.minimum_shape import solve_minimum

HERE = Path(__file__).resolve().parent
MEASUREMENTS = ROOT / "research/independent_photometry/measurements.json"
GOALS = ("photometry", "green_strict", "G_lt_R_strict", "G_lt_B_strict")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_observations():
    cohort, derivatives = load_inputs()
    source = json.loads(MEASUREMENTS.read_text())
    measured = source["measurements"]
    if len(measured) != 450 or len({r["source_id"] for r in measured}) != 25:
        raise AssertionError("The frozen 25 x 18 measurement census changed")
    if {(r["source_id"], r["svo_filter_id"]) for r in measured} != {
        (sid, meta["filter_id"]) for sid in derivatives for _, meta in load_profiles()}:
        raise AssertionError("A measurement slot is missing or duplicated")
    return cohort, derivatives, measured


def prepare_target(source_id, quality="strict", extra_box_margin=0.):
    cohort, derivatives, measured = load_observations()
    row = cohort.loc[cohort.source_id == source_id].iloc[0]
    ps1 = [filter_metadata(b) for b in "griz"]
    w, f, baseline, observed, errors, meta = prepare(row, derivatives[source_id], [r[0] for r in ps1])
    profile_lookup = {meta["filter_id"]: (flt, meta) for flt, meta in load_profiles()}
    all_rows, usable = [], []
    for measurement in [r for r in measured if r["source_id"] == source_id]:
        flt, profile = profile_lookup[measurement["svo_filter_id"]]
        covered = w.min() <= flt.wavelength.min() and w.max() >= flt.wavelength.max()
        prediction = float(flt.get_ab_magnitude(f, w)) if covered else None
        finite = measurement["mag_ab"] is not None
        quality_accepted = (measurement["adopted"] if quality == "strict" else
                            measurement["official_good_sensitivity"] if quality == "official_good" else False)
        use = bool(covered and quality_accepted)
        result = {
            **measurement, "passband_covered": bool(covered),
            "profile_minimum_A": profile["minimum_A"], "profile_maximum_A": profile["maximum_A"],
            "baseline_predicted_mag_ab": prediction,
            "baseline_prediction_minus_observation_mag": prediction-measurement["mag_ab"] if covered and finite else None,
            "selected_quality_policy": quality, "used_in_joint_fit": use,
            "joint_fit_error_box_half_width_mag": measurement["mag_error_with_zeropoint"]+extra_box_margin if use else None,
            "additional_systematic_box_margin_mag": extra_box_margin,
            "analysis_exclusion": "" if use else
                ";".join(reason for condition, reason in ((not covered, "observed_spectrum_does_not_cover_full_response"),
                                                          (not quality_accepted, measurement["quality_reasons"])) if condition),
        }
        all_rows.append(result)
        if use:
            path = ROOT / measurement["raw_path"]
            if sha(path) != measurement["raw_sha256"]:
                raise AssertionError("New measurement raw source changed")
            usable.append((flt, profile, result))
    filters = [p[0] for p in ps1] + [p[0] for p in usable]
    baseline = np.array([float(flt.get_ab_maggies(f, w)) for flt in filters])
    labels = ["PS1/"+b for b in "griz"]+[p[1]["filter_id"] for p in usable]
    observed_all = np.r_[observed, [p[2]["mag_ab"] for p in usable]]
    errors_all = np.r_[errors, [p[2]["joint_fit_error_box_half_width_mag"] for p in usable]]
    meta.update(additional_measurement_count=len(usable), band_labels=labels,
                PS1_filter_metadata=[p[1] for p in ps1],
                additional_filter_metadata=[p[1] for p in usable],
                observed_mag_all_bands=observed_all.tolist(), error_box_half_width_all_bands=errors_all.tolist(),
                baseline_mag_all_bands=(-2.5*np.log10(baseline)).tolist())
    return w, f, baseline, filters, observed_all, errors_all, meta, all_rows


def run(pilot=False):
    cohort, derivatives, measured = load_observations()
    targets = ["3204436719718449280"] if pilot else list(derivatives)
    spacings = (800,) if pilot else (400, 800, 1600)
    scenarios, predictions, metadata = [], [], {}
    dest = HERE / ("measured_pilot_certificates" if pilot else "measured_certificates")
    dest.mkdir(exist_ok=True)
    for sid in targets:
        native = prepare_target(sid)
        predictions.extend(native[-1])
        metadata[sid] = native[-2]
        settings = [("PS1_only", "strict", 0.)]
        if native[-2]["additional_measurement_count"]:
            settings.extend([("PS1_plus_strict", "strict", margin) for margin in (0., .02)])
        if sid == "3204436719718449280":
            settings.extend([("PS1_plus_official_good", "official_good", margin) for margin in (0., .02)])
        for label, quality, margin in settings:
            w, f, baseline, filters, obs, err, meta, _ = (native if quality == "strict" and margin == 0
                                                         else prepare_target(sid, quality, margin))
            if label == "PS1_only":
                baseline, filters, obs, err = baseline[:4], filters[:4], obs[:4], err[:4]
                band_labels = meta["band_labels"][:4]
            else:
                band_labels = meta["band_labels"]
            for spacing in spacings:
                problem = Problem(w, f, baseline, filters, spacing)
                row = {"source_id": sid, "WDJname": meta["WDJname"], "scenario": label,
                       "quality_policy": quality, "additional_systematic_box_margin_mag": margin,
                       "spacing_A": spacing, "normalized_guard": .005,
                       "band_labels": band_labels, "observed_mag_all_bands": obs.tolist(),
                       "error_box_half_width_all_bands": err.tolist(), "solutions": {}}
                for goal in GOALS:
                    result = solve_minimum(problem, obs, err, goal)
                    if result["success"]:
                        arrays = {name: np.asarray(result.pop(name)) for name in (
                            "constraint_grid_A", "dual_inequality", "dual_lower", "dual_upper")}
                        certificate = dest/f"case_{len(scenarios):04d}_{goal}.npz"
                        np.savez_compressed(certificate, **arrays)
                        result["certificate_path"] = str(certificate.relative_to(ROOT))
                        result["certificate_sha256"] = sha(certificate)
                    row["solutions"][goal] = result
                scenarios.append(row)
                print(sid, label, margin, spacing,
                      {g: r.get("continuous_witness_supremum") for g, r in row["solutions"].items()}, flush=True)
    hashes = {str(MEASUREMENTS.relative_to(ROOT)): sha(MEASUREMENTS)}
    for name in ("measured_constraints.py", "minimum_shape.py", "MEASURED_DESIGN.md", "profiles.py",
                 "fetch_profiles.py", "profile_manifest.json", "coupled_colour_sets.py"):
        hashes[str((HERE/name).relative_to(ROOT))] = sha(HERE/name)
    for name in ("colour_pipeline.py", "research/calibration_followup/photometric_feasibility.py",
                 "research/precision/photometric_nullspace.py", "research/precision/candidate_recalibration/heldout_z.py"):
        hashes[name] = sha(ROOT/name)
    output = {"created_utc": datetime.now(timezone.utc).isoformat(),
              "scope": "New measured-photometry constraints on a fixed central DESI spectral shape; no confidence probability or intrinsic variability claim",
              "input_and_code_hashes": hashes, "cohort": metadata, "scenarios": scenarios,
              "prediction_slots": len(predictions), "strict_covered_measured_bands": sum(r["used_in_joint_fit"] for r in predictions),
              "sources_with_strict_covered_measurements": len({r["source_id"] for r in predictions if r["used_in_joint_fit"]})}
    tag = "measured_pilot" if pilot else "measured"
    (HERE/f"{tag}_results.json").write_text(json.dumps(output, indent=2, ensure_ascii=False)+"\n")
    (HERE/f"{tag}_predictions.json").write_text(json.dumps(predictions, indent=2, ensure_ascii=False)+"\n")
    pd.DataFrame(predictions).to_csv(HERE/f"{tag}_predictions.csv", index=False)
    flat = []
    for row in scenarios:
        result = {k: row[k] for k in ("source_id", "WDJname", "scenario", "quality_policy", "additional_systematic_box_margin_mag", "spacing_A")}
        result["n_measurements"] = len(row["band_labels"])
        for goal, solution in row["solutions"].items():
            result[goal+"_minimum"] = solution.get("continuous_witness_supremum")
        flat.append(result)
    pd.DataFrame(flat).to_csv(HERE/f"{tag}_summary.csv", index=False)
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pilot", action="store_true")
    args = parser.parse_args()
    run(args.pilot)
