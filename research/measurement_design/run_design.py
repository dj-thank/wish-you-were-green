#!/usr/bin/env python3
"""Execute the frozen whole-set additional-filter design, without network I/O."""
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
os.environ.setdefault("MPLCONFIGDIR", "/tmp/wish-green-design-mpl")
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd
import scipy
import speclite

from research.calibration_followup.photometric_feasibility import (
    load_inputs, prepare, Problem, filter_metadata,
)
from research.measurement_design.profiles import covered_profiles
from research.measurement_design.coupled_colour_sets import solve_pair

HERE = Path(__file__).resolve().parent
TARGETS = ("3204436719718449280", "818833831355548928")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_target(source_id, spacing, closure_width_A=1.):
    cohort, derivatives = load_inputs()
    row = cohort.loc[cohort.source_id == source_id].iloc[0]
    ps1 = [filter_metadata(b) for b in "griz"]
    w, f, _, observed, errors, meta = prepare(row, derivatives[source_id], [x[0] for x in ps1])
    accepted, excluded = covered_profiles(w.min(), w.max(), closure_width_A)
    filters = [p[0] for p in ps1] + [p[0] for p in accepted]
    baseline = np.array([float(flt.get_ab_maggies(f, w)) for flt in filters])
    labels = ["PS1/" + b for b in "griz"] + [p[1]["filter_id"] for p in accepted]
    meta["PS1_filter_metadata"] = [p[1] for p in ps1]
    meta["additional_filter_metadata"] = [p[1] for p in accepted]
    meta["excluded_filters"] = excluded
    meta["all_filter_labels"] = labels
    meta["all_baseline_flux_maggies"] = baseline.tolist()
    meta["all_baseline_mag"] = (-2.5 * np.log10(baseline)).tolist()
    return Problem(w, f, baseline, filters, spacing), observed, errors, labels, meta


def proposals(labels):
    lookup = {name: i for i, name in enumerate(labels)}
    sky = [i for i, name in enumerate(labels) if name.startswith("SkyMapper/")]
    jplus = [i for i, name in enumerate(labels) if name.startswith("OAJ/JPLUS.")]
    narrow = [i for i in jplus if labels[i].split(".")[-1].startswith("J")]
    results = [{"name": "none", "kind": "none", "indices": []},
               {"name": "PS1_griz", "kind": "survey", "indices": list(range(4))}]
    for i in sky + jplus:
        results.append({"name": labels[i], "kind": "survey", "indices": [i]})
    for name, indices in (
        ("SkyMapper_all_covered", sky), ("JPLUS_narrow_covered", narrow),
        ("JPLUS_all_covered", jplus),
        ("PS1_plus_SkyMapper", list(range(4)) + sky),
        ("PS1_plus_JPLUS_narrow", list(range(4)) + narrow),
        ("PS1_plus_JPLUS_all", list(range(4)) + jplus),
        ("JPLUS_J0430_J0515_J0660", [lookup[f"OAJ/JPLUS.{b}"] for b in ("J0430", "J0515", "J0660")]),
    ):
        results.append({"name": name, "kind": "survey", "indices": indices})
    results.append({"name": "ideal_XYZ", "kind": "ideal_XYZ", "indices": []})
    return results


def proposed_matrix(problem, proposal):
    if proposal["kind"] == "ideal_XYZ":
        return problem.xyz_changes / problem.xyz[:, None]
    return problem.anchors[proposal["indices"]]


def run(pilot=False, closure_width_A=1., only_source_id=None):
    targets = [only_source_id] if only_source_id else TARGETS
    spacings = (800,) if pilot else (400, 800, 1600)
    budgets = (.05,) if pilot else (.05, .10)
    selected = {"none", "PS1_griz", "SkyMapper_all_covered", "JPLUS_all_covered", "ideal_XYZ"} if pilot else None
    # Profile-closure sensitivity is deliberately limited to the primary target
    # and 800 Å knots; no new spectral or measurement selections are optimized.
    if closure_width_A != 1.:
        targets, spacings, budgets = [TARGETS[0]], (800,), (.05, .10)
        selected = {"JPLUS_narrow_covered", "JPLUS_all_covered", "PS1_plus_JPLUS_all", "ideal_XYZ"}
    tag = "pilot" if pilot else "closure10" if closure_width_A != 1 else "full"
    destination = HERE / ("pilot_certificates" if pilot else "certificates")
    destination.mkdir(exist_ok=True)
    records, metas = [], {}
    for sid in targets:
        for spacing in spacings:
            problem, observed, errors, labels, meta = load_target(sid, spacing, closure_width_A)
            metas[sid] = meta
            for budget in budgets:
                for proposal in proposals(labels):
                    if selected is not None and proposal["name"] not in selected:
                        continue
                    proposal_labels = ([labels[i] for i in proposal["indices"]] if proposal["kind"] == "survey"
                                       else ["ideal_X", "ideal_Y", "ideal_Z"] if proposal["kind"] == "ideal_XYZ" else [])
                    solutions = []
                    for branch in ("G-R", "G-B"):
                        result, arrays = solve_pair(
                            problem, observed, errors, proposed_matrix(problem, proposal), problem.filterset,
                            budget, .005, branch, proposed_kind=proposal["kind"],
                            proposed_indices=proposal["indices"],
                        )
                        result.update(source_id=sid, spacing_A=spacing,
                                      closure_width_A=closure_width_A,
                                      proposal=proposal, proposed_labels=proposal_labels)
                        if arrays is not None:
                            sequence = len(records) * 2 + len(solutions)
                            certificate = destination / f"{tag}_{sequence:04d}.npz"
                            np.savez_compressed(certificate, **arrays)
                            result["certificate_path"] = str(certificate.relative_to(ROOT))
                            result["certificate_sha256"] = sha(certificate)
                        solutions.append(result)
                    feasible = [s for s in solutions if s["success"]]
                    row = {"source_id": sid, "WDJname": meta["WDJname"], "spacing_A": spacing,
                           "relative_shape_budget": budget, "normalized_guard": .005,
                           "closure_width_A": closure_width_A, "proposal": proposal,
                           "proposed_labels": proposal_labels, "branches": solutions,
                           "both_strict_classes_feasible": bool(feasible)}
                    if feasible:
                        best = min(feasible, key=lambda r: r["minimum_max_baseline_relative_flux_separation"])
                        row.update(minimum_max_baseline_relative_flux_separation=best["minimum_max_baseline_relative_flux_separation"],
                                   active_opposite_branch=best["opposite_branch"],
                                   separation_error_half_width=(best["uniform_error_half_width_from_dual_lower_bound"]
                                                               if best["numerically_separated_at_check_tolerance"] else 0.),
                                   separation_error_half_width_witness_upper_bound=best["uniform_error_half_width_from_witness_upper_bound"])
                    records.append(row)
                    print(sid, spacing, budget, proposal["name"],
                          row.get("minimum_max_baseline_relative_flux_separation", "no opposite pair"), flush=True)
    inputs = {str((HERE / name).relative_to(ROOT)): sha(HERE / name)
              for name in ("DESIGN.md", "profiles.py", "fetch_profiles.py", "coupled_colour_sets.py",
                           "run_design.py", "profile_manifest.json")}
    for name in ("colour_pipeline.py", "research/calibration_followup/photometric_feasibility.py",
                 "research/precision/photometric_nullspace.py", "research/precision/candidate_recalibration/heldout_z.py"):
        inputs[name] = sha(ROOT / name)
    output = {
        "created_utc": datetime.now(timezone.utc).isoformat(), "design_version": "coupled_strict_sets_v1",
        "scope": "conditional spline minimax design; proposed additional fluxes are not measurements",
        "tag": tag, "environment": {"python": platform.python_version(), "numpy": np.__version__,
                                      "scipy": scipy.__version__, "speclite": speclite.__version__},
        "input_and_code_hashes": inputs, "cohort": metas, "results": records,
    }
    (HERE / f"design_{tag}.json").write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n")
    flat = []
    for r in records:
        flat.append({k: r.get(k) for k in ("source_id", "WDJname", "spacing_A", "relative_shape_budget", "normalized_guard", "closure_width_A", "both_strict_classes_feasible", "minimum_max_baseline_relative_flux_separation", "separation_error_half_width")} | {"proposal": r["proposal"]["name"], "n_bands": len(r["proposed_labels"])})
    pd.DataFrame(flat).to_csv(HERE / f"design_{tag}_summary.csv", index=False)
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pilot", action="store_true")
    parser.add_argument("--closure-width-A", type=float, default=1.)
    parser.add_argument("--source-id", choices=TARGETS)
    args = parser.parse_args()
    run(args.pilot, args.closure_width_A, args.source_id)
