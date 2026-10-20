#!/usr/bin/env python3
"""Recompute all five model-validation CSVs from curated offline inputs.

``verify(root)`` returns a JSON-serializable summary and file-hash mapping.
It never edits the supplied repository. Only inputs whose recorded hashes
have been checked are copied into a temporary tree. Both original analysis
programs run in this process, so a caller's socket prohibition remains in
effect. Their temporary numerical outputs are compared to every stored CSV
cell, including exact string identifiers and missing-value positions.

This establishes numerical reproducibility, not independent observations,
new atmosphere physics, the accuracy of PDF extraction, or a model update.
"""
from __future__ import annotations

import argparse
from contextlib import redirect_stdout
import csv
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import socket
import sys
import tempfile
from unittest.mock import patch

import numpy as np


BASE = Path("research/model_validation")
CSV_FILES = (
    "photometric_predictions.csv",
    "photometric_predictions_logg8.csv",
    "photometric_input_coverage.csv",
    "published_curve_residuals.csv",
    "published_curve_50A_bins.csv",
)
SUMMARY_FILES = ("photometric_summary.json", "published_curve_summary.json")
PROGRAMS = ("photometric_null_models.py", "published_curve_diagnostics.py")
EXACT_TEXT_COLUMNS = {
    "source_id", "object_key", "spectrum_id", "name", "sample", "survey",
    "spectral_type", "status", "missing_reason", "y_missing_reason", "family",
    "photometry_source_sha256", "archive",
}
ATOL = 2e-10
RTOL = 2e-11


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text())


def table(path):
    with Path(path).open(newline="") as stream:
        reader = csv.DictReader(stream)
        rows = list(reader)
        return reader.fieldnames, rows


def compare_csv(stored, recalculated):
    columns, old = table(stored)
    new_columns, new = table(recalculated)
    require(columns == new_columns, f"CSV schema differs: {stored.name}")
    require(len(old) == len(new), f"CSV row count differs: {stored.name}")
    numerical_cells = 0
    exact_cells = 0
    missing_cells = 0
    max_absolute_difference = 0.0
    for index, (a, b) in enumerate(zip(old, new), start=1):
        for column in columns:
            left, right = a[column], b[column]
            label = f"{stored.name}, row {index}, column {column}"
            if left == "" or right == "":
                require(left == right, f"Missing-value placement differs: {label}")
                missing_cells += 1
                continue
            if column in EXACT_TEXT_COLUMNS or left in ("True", "False") or right in ("True", "False"):
                require(left == right, f"Exact field differs: {label}")
                exact_cells += 1
                continue
            try:
                x, y = float(left), float(right)
            except ValueError:
                require(left == right, f"Text differs: {label}")
                exact_cells += 1
                continue
            require(np.isfinite(x) and np.isfinite(y), f"Nonfinite numeric cell: {label}")
            difference = abs(x - y)
            require(difference <= ATOL + RTOL * abs(y), f"Recomputed number differs: {label}: {left} != {right}")
            numerical_cells += 1
            max_absolute_difference = max(max_absolute_difference, difference)
    return {
        "rows": len(old), "columns": len(columns),
        "numerical_cells": numerical_cells, "exact_cells": exact_cells,
        "missing_cells": missing_cells,
        "max_absolute_numeric_difference": max_absolute_difference,
        "byte_identical": sha(stored) == sha(recalculated),
    }


def compare_nested(stored, recalculated, label):
    """Compare aggregate statistics without requiring identical float text."""
    if isinstance(stored, dict):
        require(isinstance(recalculated, dict) and stored.keys() == recalculated.keys(),
                f"Summary keys differ: {label}")
        for key in stored:
            compare_nested(stored[key], recalculated[key], f"{label}/{key}")
    elif isinstance(stored, list):
        require(isinstance(recalculated, list) and len(stored) == len(recalculated),
                f"Summary list differs: {label}")
        for index, (left, right) in enumerate(zip(stored, recalculated)):
            compare_nested(left, right, f"{label}/{index}")
    elif isinstance(stored, (int, float)) and not isinstance(stored, bool):
        require(isinstance(recalculated, (int, float)) and
                abs(stored - recalculated) <= ATOL + RTOL * abs(recalculated),
                f"Summary statistic differs: {label}")
    else:
        require(stored == recalculated, f"Summary value differs: {label}")


def load_program(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"Cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify(root):
    """Verify hashes, curated-only recomputation, and numerical invariants."""
    root = Path(root).resolve()
    base = root / BASE
    checked = {}
    input_hashes = {}

    def checked_path(relative, expected=None):
        relative = Path(relative)
        path = (root / relative).resolve()
        require(path.is_relative_to(root), f"Input escapes supplied root: {relative}")
        digest = sha(path)
        require(expected is None or digest == expected, f"Recorded SHA256 differs: {relative}")
        checked[relative.as_posix()] = digest
        return path

    summaries = {}
    for filename in SUMMARY_FILES:
        path = checked_path(BASE / filename)
        summaries[filename] = read_json(path)
        for relative, expected in summaries[filename]["input_sha256"].items():
            require(relative not in input_hashes or input_hashes[relative] == expected,
                    f"Conflicting recorded input hashes: {relative}")
            checked_path(relative, expected)
            input_hashes[relative] = expected
    for filename in CSV_FILES + PROGRAMS + ("verify_outputs.py",):
        checked_path(BASE / filename)

    # The shared original 27 identifiers remain exact strings. This is a
    # fixed follow-up cohort, not a newly selected set of successful fits.
    prior = read_json(root / "research/literature/sources/candidate27_prior_rows.json")
    source_ids = prior["source_ids"]
    require(len(source_ids) == len(set(source_ids)) == 27, "Fixed cohort differs")
    require(all(isinstance(sid, str) and sid.isdecimal() for sid in source_ids),
            "Gaia identifiers must be decimal strings")

    comparisons = {}
    with tempfile.TemporaryDirectory(prefix="wish-green-model-verify-") as temporary:
        staged = Path(temporary)
        # No repository spectra cache, downloaded PDF, git checkout, home
        # directory data, or network lookup is copied or requested.
        for relative in list(input_hashes) + [(BASE / name).as_posix() for name in PROGRAMS]:
            source = root / relative
            destination = staged / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
            require(sha(destination) == checked[relative], f"Staging changed bytes: {relative}")

        programs = []
        for index, filename in enumerate(PROGRAMS):
            program = load_program(staged / BASE / filename, f"_wish_model_verify_{index}")
            programs.append(program)
            output = io.StringIO()
            # In-process execution preserves the parent's forbidden-socket
            # monkeypatch. Neither main() has a download or network branch.
            with patch.object(sys, "argv", [filename, "--root", str(staged)]), redirect_stdout(output):
                program.main()
            require("PASS" in output.getvalue(), f"Analysis did not complete: {filename}")

        for filename in CSV_FILES:
            comparisons[filename] = compare_csv(base / filename, staged / BASE / filename)

        # Summary counts and numerical groups must also agree. Timestamp
        # and historical code hashes deliberately remain provenance of
        # the original run, rather than being rewritten during verification.
        summary_fields = {
            "photometric_summary.json": (
                "candidate_rows", "candidate_available", "control_rows", "control_available",
                "all_fits", "primary_fits", "primary_fixed_logg", "gravity_sensitivity", "model_ranges", "groups",
            ),
            "published_curve_summary.json": (
                "candidate_input_count", "figure_available_count", "retained_unavailable_count",
                "bin_width_angstrom", "all_bins", "windows_angstrom",
            ),
        }
        for filename, fields in summary_fields.items():
            current = read_json(staged / BASE / filename)
            for field in fields:
                compare_nested(summaries[filename][field], current[field], f"{filename}/{field}")

        # Independent interpolation of the stored fitted parameters uses
        # NumPy's log-temperature interpolation, not fit_gravity's interval
        # construction. It replays every held-out prediction without z/y
        # entering a fit or a template choice.
        _, predictions = table(base / "photometric_predictions.csv")
        models = programs[0].load_models(staged / BASE)
        maximum_prediction_replay_error = 0.0
        for row in predictions:
            model = models[row["family"]]
            gravity = float(row["fixed_logg"])
            native = model[model[:, 1] == gravity]
            native = native[np.argsort(native[:, 0])]
            temperature = float(row["template_teff_K"])
            require(native[0, 0] - 1e-8 <= temperature <= native[-1, 0] + 1e-8,
                    "A stored fitted temperature extrapolates beyond its native grid")
            bands = "grizy" if row["survey"] == "PS1" else "griz"
            positions = [30, 31, 32, 33, 34] if row["survey"] == "PS1" else [26, 27, 28, 29]
            prediction = np.array([
                np.interp(np.log(temperature), np.log(native[:, 0]), native[:, position])
                for position in positions
            ]) + float(row["free_magnitude_offset"])
            saved = np.array([float(row[f"predicted_{band}_mag"]) for band in bands])
            error = float(np.max(np.abs(prediction - saved)))
            require(error < 2e-10, "Independent interpolation does not reproduce stored predictions")
            maximum_prediction_replay_error = max(maximum_prediction_replay_error, error)
            for band in bands[3:]:
                heldout = float(row[f"heldout_{band}_predicted_minus_observed_mag"])
                require(abs(heldout - (float(row[f"predicted_{band}_mag"]) - float(row[f"observed_{band}_mag"]))) < 2e-10,
                        f"Held-out residual definition differs for {row['object_key']} {band}")
            if row["survey"] == "SDSS":
                require(row["heldout_y_predicted_minus_observed_mag"] == "", "SDSS unexpectedly has a y datum")
                require(abs(float(row["heldout_z_if_sdss_plus0p02_AB_mag"]) -
                            (float(row["heldout_z_predicted_minus_observed_mag"]) - .02)) < 2e-10,
                        "Separate SDSS zero-point sensitivity differs")

    _, coverage = table(base / "photometric_input_coverage.csv")
    candidates = [row for row in coverage if row["sample"] == "candidate"]
    controls = [row for row in coverage if row["sample"] != "candidate"]
    require({row["source_id"] for row in candidates} == set(source_ids), "Coverage loses a candidate ID")
    require(len(coverage) == 81 and len(controls) == 54, "Input coverage count differs")
    require(sum(row["status"] == "available" for row in candidates) == 25, "Candidate availability differs")
    require(sum(row["status"] == "available" for row in controls) == 47, "Control availability differs")
    fit_keys = {(row["sample"], row["object_key"], row["family"], row["fixed_logg"]) for row in predictions}
    require(len(predictions) == len(fit_keys) == 720, "Fit combinations are missing or duplicated")
    require(comparisons["photometric_predictions_logg8.csv"]["rows"] == 144, "Primary fit count differs")
    _, curves = table(base / "published_curve_residuals.csv")
    require(len(curves) == 27 and {row["source_id"] for row in curves} == set(source_ids),
            "Published-curve coverage loses or duplicates a candidate ID")
    require(sum(row["status"] == "published_figure_diagnostic" for row in curves) == 25,
            "Published-curve availability differs")
    require(comparisons["published_curve_50A_bins.csv"]["rows"] == 1750, "Published bin count differs")

    # Also detect accidental writes to any original input/output/code bytes
    # while the temporary analyses were running.
    for relative, expected in checked.items():
        require(sha(root / relative) == expected, f"Verification modified an original file: {relative}")
    return {
        "summary": "25/27 candidates + 47/54 controls; 720 fits / 144 logg=8 fits; 25/27 published curves / 1750 bins; all five CSVs recomputed in a curated-only temporary tree",
        "candidate_count": 27, "candidate_available": 25, "control_count": 54,
        "control_available": 47, "fit_count": 720, "primary_fit_count": 144,
        "published_curve_count": 25, "published_bin_count": 1750,
        "maximum_independent_prediction_replay_error_mag": maximum_prediction_replay_error,
        "csv_comparison": comparisons,
        "numeric_comparison_atol": ATOL, "numeric_comparison_rtol": RTOL,
        "curated_input_sha256": input_hashes,
        "verified_file_sha256": checked,
        "limits": "Reproducibility only: 2021 pure-H/He magnitude tables are old restricted null models; PDF vectors are in-sample plotted relative-Fnu diagnostics, not native spectra or independent observations.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()

    def forbidden(*unused, **unused_keywords):
        raise RuntimeError("Network use is forbidden during offline model verification")

    with patch.object(socket, "create_connection", forbidden), patch.object(socket, "getaddrinfo", forbidden):
        result = verify(args.root)
    print("PASS " + result["summary"])
    print(json.dumps({
        "curated_inputs": len(result["curated_input_sha256"]),
        "checked_files": len(result["verified_file_sha256"]),
        "csvs": len(result["csv_comparison"]),
        "maximum_prediction_replay_error_mag": result["maximum_independent_prediction_replay_error_mag"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
