#!/usr/bin/env python3
"""Identify MWDD SDSS spectral-density conventions by native-sample identity.

Only a constant scale or a constant times wavelength squared is allowed. Both
raw files are hashed and read directly; continuum slopes alone never qualify.
No frozen source file or historical colour is changed by this script.
"""
from __future__ import annotations

import collections
import csv
import gzip
import hashlib
import io
import json
from pathlib import Path
import sys

import numpy as np
from astropy.io import fits

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from project_io import load_json

OUT = Path(__file__).resolve().parent
C_ANGSTROM_PER_S = 2.99792458e18
THRESHOLDS = {
    "comparison_window_A": [3600.0, 8300.0],
    "nearest_native_wavelength_tolerance_A": 0.02,
    "minimum_wavelength_grid_match_fraction": 0.99,
    "minimum_finite_fraction_of_grid_matches": 0.99,
    "minimum_comparison_samples": 1000,
    "minimum_comparison_span_A": 3500.0,
    "relative_residual_reference_floor_fraction": 0.1,
    "maximum_fractional_shape_residual": 1e-4,
    "maximum_absolute_shape_residual_per_median_abs_reference": 1e-4,
}
REFERENCE_URL = "https://www.sdss4.org/dr17/spectro/spectro_basics/"


def local(path):
    marker = "wd-colour-research/"
    return ROOT / (str(path).split(marker, 1)[1] if marker in str(path) else path)


def read_raw(record):
    path = local(record["raw_path"])
    if not path.exists():
        return None
    blob = path.read_bytes()
    actual = hashlib.sha256(blob).hexdigest()
    if actual != record["sha256"]:
        raise ValueError(f"Raw SHA256 mismatch for row {record['row_index']}")
    if record["raw_path"].startswith("mwdd/"):
        lines = blob.decode("utf-8", "replace").splitlines()
        names = next(csv.reader([lines[1]]))
        values = np.loadtxt(io.StringIO("\n".join(lines[2:])), delimiter=",")
        return {
            "wave": values[:, names.index("wavelength")],
            "flux": values[:, names.index("flux")],
            "header": lines[0],
            "columns": names,
            "raw_sha256_verified": True,
        }
    with fits.open(io.BytesIO(blob)) as hdus:
        values = hdus[1].data
        header = hdus[0].header
        return {
            "wave": 10.0 ** np.asarray(values["loglam"], dtype=float),
            "flux": np.asarray(values["flux"], dtype=float) * 1e-17,
            "header": {k: header.get(k) for k in
                       ["BUNIT", "PLATEID", "MJD", "FIBERID", "RUN2D"]},
            "raw_sha256_verified": True,
        }


def compare(first, second, a, b):
    row = {
        "mwdd_row_index": int(first["row_index"]),
        "mwdd_sha256": first["sha256"],
        "direct_row_index": int(second["row_index"]),
        "direct_sha256": second["sha256"],
        "entity_id": first["entity_id"],
        "name": first["wdid"],
        "mwdd_source_url": first["source_url"],
        "direct_source_url": second["source_url"],
        "mwdd_raw_header": a["header"],
        "direct_fits_header": b["header"],
        "raw_sha256_verified": True,
        "convention": "unresolved",
    }
    w, f, wd, fd = a["wave"], a["flux"], b["wave"], b["flux"]
    if np.any(np.diff(wd) <= 0):
        row["reason"] = "Non-increasing reference wavelengths"
        return row
    lo, hi = THRESHOLDS["comparison_window_A"]
    inside = (w >= lo) & (w <= hi) & (w >= wd.min()) & (w <= wd.max())
    idx = np.searchsorted(wd, w).clip(1, len(wd) - 1)
    idx = np.where(abs(wd[idx - 1] - w) < abs(wd[idx] - w), idx - 1, idx)
    delta = abs(w - wd[idx])
    grid = inside & (delta <= THRESHOLDS["nearest_native_wavelength_tolerance_A"])
    ref = fd[idx]
    finite = grid & np.isfinite(f) & np.isfinite(ref)
    row["wave_grid_match_fraction"] = float(grid.sum() / max(inside.sum(), 1))
    row["finite_grid_fraction"] = float(finite.sum() / max(grid.sum(), 1))
    if not finite.any():
        row["reason"] = "No finite native grid matches"
        return row
    denominator = float(np.median(abs(ref[finite])))
    if not denominator > 0:
        row["reason"] = "Nonpositive median absolute reference flux"
        return row
    keep = finite & (abs(ref) > THRESHOLDS["relative_residual_reference_floor_fraction"] * denominator)
    if keep.sum() < 2:
        row["reason"] = "Too few finite comparison samples"
        return row
    row.update({
        "comparison_samples": int(keep.sum()),
        "all_finite_matched_samples": int(finite.sum()),
        "wave_span_A": float(np.ptp(w[keep])),
        "wave_max_matched_difference_A": float(delta[grid].max()),
    })
    ratio = f[keep] / ref[keep]
    positive = ratio > 0
    if positive.sum() >= 2:
        row["ratio_log_wavelength_slope"] = float(np.polyfit(
            np.log(w[keep][positive]), np.log(ratio[positive]), 1)[0])
    accepted = []
    shared_gate = (
        row["wave_grid_match_fraction"] >= THRESHOLDS["minimum_wavelength_grid_match_fraction"]
        and row["finite_grid_fraction"] >= THRESHOLDS["minimum_finite_fraction_of_grid_matches"]
        and row["comparison_samples"] >= THRESHOLDS["minimum_comparison_samples"]
        and row["wave_span_A"] >= THRESHOLDS["minimum_comparison_span_A"]
    )
    for label in ["flambda", "fnu"]:
        multiplier = np.ones_like(w) if label == "flambda" else C_ANGSTROM_PER_S / w**2
        ratios = ratio * multiplier[keep]
        scale = float(np.median(ratios))
        if not np.isfinite(scale) or scale <= 0:
            row[label + "_accepted"] = False
            continue
        residual = abs(ratios / scale - 1)
        # Also test *all* finite matched samples, including zeros/negative flux
        # and reference points excluded only to stabilize relative divisions.
        absolute_residual = abs(f[finite] * multiplier[finite] / scale - ref[finite]) / denominator
        row.update({
            label + "_constant_scale": scale,
            label + "_median_fractional_shape_residual": float(np.median(residual)),
            label + "_p95_fractional_shape_residual": float(np.quantile(residual, .95)),
            label + "_max_fractional_shape_residual": float(residual.max()),
            label + "_max_absolute_residual_per_median_reference": float(absolute_residual.max()),
        })
        passed = shared_gate and (
            residual.max() < THRESHOLDS["maximum_fractional_shape_residual"]
            and absolute_residual.max() < THRESHOLDS["maximum_absolute_shape_residual_per_median_abs_reference"]
        )
        row[label + "_accepted"] = bool(passed)
        if passed:
            accepted.append(label)
    if len(accepted) == 1:
        row["convention"] = accepted[0]
        row["reason"] = "Native sample identity under exactly one spectral-density convention"
    else:
        row["reason"] = "Both conventions pass" if len(accepted) > 1 else "Neither convention passes all identity gates"
    return row


def main():
    with gzip.open(ROOT / "research/outlier_audit/record_audit.csv.gz", "rt") as stream:
        records = list(csv.DictReader(stream))
    groups = collections.defaultdict(list)
    for record in records:
        if record["kind"] == "SDSS":
            groups[record["entity_id"]].append(record)
    raw_cache, missing, failures, pairs = {}, {}, {}, []
    mwdd_records = [r for r in records if r["kind"] == "SDSS" and r["raw_path"].startswith("mwdd/")]
    for group in groups.values():
        mwdd = [r for r in group if r["raw_path"].startswith("mwdd/")]
        direct = [r for r in group if r["raw_path"].startswith("sdss/")]
        for first in mwdd:
            for second in direct:
                for record in [first, second]:
                    key = record["sha256"]
                    if key not in raw_cache:
                        try:
                            raw_cache[key] = read_raw(record)
                        except Exception as exc:
                            raw_cache[key] = None
                            failures[key] = {"row_index": int(record["row_index"]), "error": str(exc)}
                        if raw_cache[key] is None and key not in failures:
                            missing[key] = {k: record[k] for k in ["row_index", "entity_id", "wdid", "sha256", "raw_path", "source_url"]}
                a, b = raw_cache[first["sha256"]], raw_cache[second["sha256"]]
                if a is not None and b is not None:
                    pairs.append(compare(first, second, a, b))
    by_sha = collections.defaultdict(list)
    for pair in pairs:
        by_sha[pair["mwdd_sha256"]].append(pair)
    registry = []
    unique = {}
    for record in mwdd_records:
        unique.setdefault(record["sha256"], []).append(record)
    for sha, originals in unique.items():
        evidence = by_sha[sha]
        matches = [p for p in evidence if p["convention"] != "unresolved"]
        conventions = {p["convention"] for p in matches}
        selected = None
        if len(conventions) == 1:
            convention = next(iter(conventions))
            selected = min(matches, key=lambda p: p[convention + "_max_fractional_shape_residual"])
            reason = "At least one native sample identity; all accepted reference matches agree"
        else:
            convention = "unresolved"
            reason = "Conflicting accepted reference conventions" if conventions else "No reference identity passed all gates"
        entry = {
            "mwdd_row_index": int(originals[0]["row_index"]),
            "mwdd_sha256": sha,
            "all_mwdd_row_indices": [int(r["row_index"]) for r in originals],
            "entity_id": originals[0]["entity_id"],
            "name": originals[0]["wdid"],
            "convention": convention,
            "direct_row_index": selected["direct_row_index"] if selected else None,
            "direct_sha256": selected["direct_sha256"] if selected else None,
            "reference_pairs_assessed": len(evidence),
            "accepted_reference_pairs": len(matches),
            "reason": reason,
        }
        if selected:
            entry.update({k: v for k, v in selected.items() if k not in {"convention", "reason"}})
        registry.append(entry)
    summary = {
        "mwdd_sdss_records": len(mwdd_records),
        "mwdd_sdss_unique_raw_sha256": len(unique),
        "reference_pairs_assessed": len(pairs),
        "pair_conventions": dict(collections.Counter(p["convention"] for p in pairs)),
        "registry_conventions": dict(collections.Counter(r["convention"] for r in registry)),
        "missing_raw_files_for_possible_pairs": len(missing),
        "raw_validation_failures": len(failures),
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    payload = {
        "summary": summary,
        "thresholds": THRESHOLDS,
        "direct_flux_unit_documentation": REFERENCE_URL,
        "reference_flux_unit": "erg cm^-2 s^-1 Angstrom^-1; native SDSS flux multiplied by 1e-17",
        "interpretation": "Sample identity establishes representation up to a wavelength-independent positive scale. It does not verify absolute calibration, sky subtraction, variance, astrophysical identity, or independence of repeated archive copies. Unresolved records are not automatically F_lambda. Contradictory accepted reference conventions are quarantined.",
        "records": registry,
        "pair_evidence": pairs,
        "missing_raw_files": list(missing.values()),
        "raw_validation_failures": list(failures.values()),
    }
    (OUT / "flux_convention_evidence.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    keys = list(dict.fromkeys(k for r in registry for k in r))
    with (OUT / "flux_convention_evidence.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=keys)
        writer.writeheader()
        for record in registry:
            writer.writerow({k: json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v for k, v in record.items()})
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
