#!/usr/bin/env python3
"""Verify the research extension offline with requirements-core dependencies.

This checks preserved inputs, meaningful numerical invariants and selected
recalculations. It does not repeat the GaiaXPy installation, human image review,
survey retrieval or Monte Carlo draws. Historical whole-code hashes document
the code used then and are not required to equal later unrelated code edits.
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter
import csv
from datetime import datetime, timezone
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import sys

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MPLCONFIGDIR", "/tmp/wish-green-verification-mpl")
import numpy as np
from scipy.interpolate import BSpline, PPoly
from speclite import filters

FROZEN_SHA = "92ccafd605f1bcd469dc997ad946980529aa00dab8bb5bcc2551e0f93375ef28"


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path):
    return json.loads(path.read_text())


def read_csv(path):
    with (gzip.open(path, "rt", newline="") if path.suffix == ".gz" else path.open(newline="")) as handle:
        return list(csv.DictReader(handle))


def yes(value):
    return value is True or value == "True"


def number(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return np.nan


def close(actual, expected, label, *, rtol=0, atol=1e-10):
    np.testing.assert_allclose(actual, expected, rtol=rtol, atol=atol, equal_nan=False, err_msg=label)


def psd(matrix, label):
    require(np.all(np.isfinite(matrix)), f"{label}: nonfinite covariance")
    scale = max(float(np.max(np.abs(matrix))), 1e-300)
    close(matrix / scale, matrix.T / scale, label + " symmetry", atol=1e-12)
    eigen = np.linalg.eigvalsh(matrix / scale)
    require(float(eigen.min()) >= -1e-8 * max(float(eigen.max()), 1e-30), f"{label}: indefinite covariance")


class Verification:
    def __init__(self, root):
        self.root = root
        self.checked_files = {}
        self.checked_lossless_originals = {}
        self.groups = []
        self.shortlist = set()

    def path(self, relative, base=None):
        path = ((base or self.root) / relative).resolve()
        require(path.is_relative_to(self.root) and path.is_file(), f"Missing or nonlocal input: {relative}")
        return path

    def hashed(self, path, expected=None):
        actual = sha(path)
        if expected is not None:
            require(actual == expected, f"SHA256 differs: {path.relative_to(self.root)}")
        self.checked_files[str(path.relative_to(self.root))] = actual
        return actual

    def group(self, name, function):
        result = function()
        self.groups.append({"name": name, "status": "PASS", **result})
        print("PASS " + name + ": " + result["summary"], flush=True)

    def screen(self):
        frozen_path = self.path("results/all_spectra_screen.csv.gz")
        self.hashed(frozen_path, FROZEN_SHA)
        frozen = read_csv(frozen_path)
        base = self.root / "research/precision/flux_units"
        summary = read_json(base / "corrected_screen_summary.json")
        self.hashed(self.path("research/precision/flux_convention_evidence.json"), summary["unit_registry_sha256"])
        require(summary["frozen_baseline_sha256"] == FROZEN_SHA, "Wrong corrected-screen baseline")
        path = base / "corrected_record_screen.csv.gz"
        rows = read_csv(path)
        self.hashed(path)
        require(len(frozen) == len(rows) == 9902, "Frozen/corrected record count")
        require(sorted(int(r["row_index"]) for r in rows) == list(range(9902)), "Corrected row_index coverage/duplicates")
        rows = sorted(rows, key=lambda r: int(r["row_index"]))
        require(all(r["sha256"] == old["sha256"] for r, old in zip(rows, frozen)), "Corrected input raw SHA row mapping")
        registry = read_json(self.root / "research/precision/flux_convention_evidence.json")
        entries = registry["records"]
        counts = Counter(r["convention"] for r in entries)
        require(len(entries) == len({r["mwdd_sha256"] for r in entries}) == 2232, "Unit-registry raw-file uniqueness")
        require(counts == {"fnu": 149, "flambda": 504, "unresolved": 1579}, "Unit-registry counts")
        require(counts == registry["summary"]["registry_conventions"], "Unit-registry summary disagrees")
        for item in entries:
            for i in item["all_mwdd_row_indices"]:
                require(rows[i]["sha256"] == item["mwdd_sha256"], "Registry/input row mismatch")
                require(rows[i]["flux_input_convention"] == item["convention"], "Registry/current convention mismatch")
        unknown = [r for r in rows if not yes(r["flux_units_validated"])]
        physical = "x y u1960 v1960 duv distance_planck_uv hex r_linear g_linear b_linear r g b green_dominant green_channel_margin".split()
        for r in unknown:
            require(r["status"] == "unit_unverified" and not yes(r["usable_screen"]) and not yes(r["calibrated"]), "Unknown units enter current selection")
            keys = physical + [k for k in r if k.startswith("cal_") or (k.startswith("raw_") and k not in ("raw_path", "raw_sha256"))]
            require(all(r.get(k, "") == "" for k in keys), f"Unknown-unit current physical field retained, row {r['row_index']}")
        eligible = [r for r in rows if yes(r["usable_screen"])]
        strong = [r for r in eligible if number(r["distance_planck_uv"]) >= .01]
        keys = {r["entity_id"] for r in strong}
        require((len(eligible), len(strong), len(keys)) == (7473, 395, 308), "Corrected selection count changed")
        require((summary["current_eligible_records"], summary["current_strong_records"], summary["current_strong_entity_keys"]) == (len(eligible), len(strong), len(keys)), "Corrected summary count mismatch")
        objects = read_csv(base / "corrected_object_screen.csv")
        require({r["entity_id"] for r in objects if int(r["current_strong_records"]) > 0} == keys, "Corrected entity aggregation mismatch")
        census = read_csv(self.path("research/outlier_audit/object_audit.csv"))
        self.shortlist = {r["source_id"] for r in census if r["review_status"] == "multiple_instrument_colour_candidate"}
        require(len(self.shortlist) == 27 and all(re.fullmatch(r"\d{18,19}", sid) for sid in self.shortlist), "Shortlist string Gaia IDs")
        return {"summary": "9902 rows; 2232 unit records; 7473 eligible / 395 strong / 308 keys; unknown-unit colours withheld", "unknown_unit_rows": len(unknown), "unit_conventions": dict(counts)}

    def gaia(self):
        base = self.root / "research/precision/gaia_expanded"
        retrieval = read_json(base / "retrieval.json")["results"]
        require({r["source_id"] for r in retrieval} == self.shortlist and len(retrieval) == 27, "Gaia retrieval IDs")
        available = {r["source_id"] for r in retrieval if r["status"] == "downloaded"}
        unavailable = [r for r in retrieval if r["status"] != "downloaded"]
        require(len(available) == 26 and len(unavailable) == 1 and unavailable[0]["source_id"] == "3638333660492606976" and unavailable[0]["status"] == "XP_CONTINUOUS_not_available", "Gaia missing-data accounting")
        for item in retrieval:
            for suffix in (["datalink.xml", "xp_continuous.csv"] if item["status"] == "downloaded" else ["datalink.xml"]):
                path = base / "sources" / f"{item['source_id']}_{suffix}"
                self.hashed(path, read_json(path.with_suffix(path.suffix + ".provenance.json"))["sha256"])
            if item["status"] == "downloaded":
                self.hashed(base / "sources" / f"{item['source_id']}_xp_continuous.csv", item["sha256"])
        reconstruction = read_json(base / "reconstruction.json")
        results = reconstruction["results"]
        require(len(results) == 52 and {(r["source_id"], r["truncation"]) for r in results} == {(s, t) for s in available for t in (False, True)}, "Gaia full/truncated coverage")
        matrix_path = base / "calibration_design_matrices.npz"
        self.hashed(matrix_path, reconstruction["design_matrices_sha256"])
        design = np.load(matrix_path)
        wave = design["wavelength_nm"]
        cmf = np.loadtxt(self.path("reference/CIE_xyz_1931_2deg.csv"), delimiter=",")
        visible = (wave >= 360) & (wave <= 830)
        d = np.diff(wave[visible]); trap = np.r_[d[0]/2, (d[:-1]+d[1:])/2, d[-1]/2]
        weights = np.zeros((len(wave), 3))
        weights[visible] = np.column_stack([np.interp(wave[visible], cmf[:, 0], cmf[:, i]) for i in (1, 2, 3)]) * trap[:, None]
        formal = read_json(base / "formal_colour_results.json")
        formal_rows = read_csv(base / "formal_colour_results.csv")
        require(formal["spectra"] == len(formal_rows) == 52 and formal["source_count"] == 26, "Gaia formal counts")
        formal_index = {(r["source_id"], r["reconstruction"]): r for r in formal_rows}
        require(set(formal_index) == {(s, t) for s in available for t in ("full", "truncated")}, "Gaia formal IDs")
        max_saved_discrepancy = 0.
        for item in results:
            sid = item["source_id"]
            source_path = base / "sources" / f"{sid}_xp_continuous.csv"
            self.hashed(source_path, item["input_sha256"])
            source_rows = read_csv(source_path)
            require(len(source_rows) == 1 and source_rows[0]["source_id"] == sid and isinstance(sid, str), "Native coefficient source identity")
            source = source_rows[0]
            flux = np.zeros(len(wave)); variance = flux.copy(); xyz = np.zeros(3); covariance = np.zeros((3, 3))
            for band in ("bp", "rp"):
                coef = np.asarray(ast.literal_eval(source[f"{band}_coefficients"]), float)
                error = np.asarray(ast.literal_eval(source[f"{band}_coefficient_errors"]), float)
                packed = np.asarray(ast.literal_eval(source[f"{band}_coefficient_correlations"]), float)
                n = len(coef); correlation = np.eye(n)
                diagonal = 0 if len(packed) == n * (n + 1) // 2 else -1
                require(len(packed) in (n * (n - 1)//2, n * (n+1)//2), "Gaia packed correlation length")
                lower = np.tril_indices(n, k=diagonal)
                correlation[lower] = packed
                correlation[np.triu_indices(n, 1)] = correlation.T[np.triu_indices(n, 1)]
                cc = correlation * error[:, None] * error[None, :]
                psd(cc, sid + "/" + band)
                count = int(source[f"{band}_n_relevant_bases"]) if item["truncation"] else n
                require(count == item[f"{band}_bases"], "Gaia retained-basis count")
                matrix = design[band][:count]
                xyz_matrix = matrix @ weights
                flux += coef[:count] @ matrix
                variance += np.einsum("ik,ij,jk->k", matrix, cc[:count, :count], matrix, optimize=True)
                xyz += coef[:count] @ xyz_matrix
                covariance += xyz_matrix.T @ cc[:count, :count] @ xyz_matrix
            path = base / item["output"]
            self.hashed(path, item["output_sha256"])
            with np.load(path) as saved:
                close(saved["wavelength_nm"], wave, sid + " wavelength", atol=0)
                for key, actual in (("flux_w_m2_nm", flux), ("flux_error_w_m2_nm", np.sqrt(np.maximum(variance, 0))), ("xyz_native", xyz), ("xyz_covariance_native", (covariance + covariance.T)/2)):
                    scale = max(float(np.max(np.abs(actual))), 1e-300)
                    close(saved[key]/scale, actual/scale, sid + " native coefficient propagation " + key, atol=2e-11)
                psd(saved["xyz_covariance_native"], sid + " XYZ")
                xx, yy, zz = xyz; denominator = xx + 15*yy + 3*zz
                values = [xx/(xx+yy+zz), yy/(xx+yy+zz), 4*xx/denominator, 6*yy/denominator]
                row = formal_index[sid, "truncated" if item["truncation"] else "full"]
                close([float(row[k]) for k in ("x", "y", "u1960", "v1960")], values, sid + " formal central colour", atol=2e-11)
            discrepancy = max(item["gaiaxpy_flux_max_relative_discrepancy"], item["gaiaxpy_error_max_relative_discrepancy"])
            require(discrepancy < 1e-10, "Recorded GaiaXPy discrepancy gate")
            max_saved_discrepancy = max(max_saved_discrepancy, discrepancy)
        return {"summary": "52 spectra / 26 sources + 1 unavailable; native coefficients reproduce flux, errors and PSD XYZ covariance", "maximum_recorded_GaiaXPy_discrepancy": max_saved_discrepancy, "GaiaXPy_rerun": False}

    def photometry(self):
        base = self.root / "research/precision/candidate_recalibration"
        rows = read_csv(base / "standardized_colours.csv")
        require(len(rows) == 27 and {r["source_id"] for r in rows} == self.shortlist, "PS1 target rows")
        good = [r for r in rows if r["status"] == "calibrated_conditional"]
        require(len(good) == 25 and sum(number(r["old_calibrated_records"]) == 0 for r in good) == 12, "PS1 additional-anchor count")
        manifest_path = base / "derivative_manifest.json"
        manifest = read_json(manifest_path)
        require(len(manifest) == 25 and {r["source_id"] for r in manifest} == {r["source_id"] for r in good}, "PS1 derivative manifest IDs")
        index = {r["source_id"]: r for r in manifest}
        # Nineteen original inputs used to exist only in an ignored MWDD
        # download cache. Always verify the committed lossless snapshots for
        # these records, even when that historical cache is present locally.
        bundle_base = base / "raw_sources"
        bundle_path = self.path("manifest.json", bundle_base)
        self.hashed(bundle_path)
        bundle = read_json(bundle_path)
        require(bundle["format_version"] == 1, "PS1 raw-source bundle format")
        require(self.path(bundle["derivative_manifest_path"]) == manifest_path, "PS1 raw-source derivative manifest path")
        self.hashed(manifest_path, bundle["derivative_manifest_sha256"])
        snapshots = {r["original_path"]: r for r in bundle["records"]}
        require(len(snapshots) == len(bundle["records"]) == 19, "PS1 raw-source snapshot uniqueness/count")
        require(set(snapshots) <= {r["original_record"]["raw_path"] for r in manifest}, "PS1 unused raw-source snapshot")
        prior_path = self.root / "research/literature/sources/candidate27_prior_rows.json"
        prior = read_json(prior_path)["candidates"]
        response = filters.load_filters("panstarrs-g", "panstarrs-r", "panstarrs-i")
        spectra = {}
        for r in good:
            sid = r["source_id"]; item = index[sid]
            self.hashed(prior_path, r["photometry_table_rows_sha256"])
            require(prior[sid]["swan_external"] == [item["photometry_row"]], "PS1 original measurement identity")
            path = base / item["path"]
            self.hashed(path, item["sha256"])
            original = item["original_record"]
            require(original["sha256"] == r["raw_sha256"], "PS1 original raw SHA agreement")
            if original["raw_path"] in snapshots:
                snapshot = snapshots[original["raw_path"]]
                require(snapshot["source_id"] == sid and snapshot["source_url"] == original["source_url"] and snapshot["retrieved_utc"] == original["retrieved_utc"], "PS1 raw-source provenance agreement")
                snapshot_path = self.path(snapshot["snapshot_path"], bundle_base)
                self.hashed(snapshot_path, snapshot["snapshot_sha256"])
                require(snapshot_path.stat().st_size == snapshot["snapshot_size_bytes"], "PS1 gzip size")
                original_bytes = gzip.decompress(snapshot_path.read_bytes())
                original_sha = hashlib.sha256(original_bytes).hexdigest()
                require(original_sha == snapshot["original_sha256"] == r["raw_sha256"], "PS1 decompressed original SHA differs")
                require(len(original_bytes) == snapshot["original_size_bytes"] == original["size_bytes"], "PS1 decompressed original size differs")
                self.checked_lossless_originals[original["raw_path"]] = original_sha
            else:
                self.hashed(self.path(original["raw_path"]), r["raw_sha256"])
            with np.load(path) as data:
                w, f = data["wavelength_angstrom"], data["flux_calibrated"]
                mags = [float(flt.get_ab_magnitude(f, w)) for flt in response]
                residual = np.array(mags) - [float(r[f"anchor_{b}_mag"]) for b in "gri"]
                close(residual, [float(r[f"cal_{b}_residual"]) for b in "gri"], sid + " actual gri residuals", atol=1e-8)
                require(np.max(np.abs(residual)) < .15 and abs(float(r["cal_tilt_mag_per_1000A"])) < .25, "PS1 calibration quality gate")
                correction = 10**(-.4*(float(r["cal_offset_mag"])+float(r["cal_tilt_mag_per_1000A"])*(w-6200)/1000))
                close(data["flux_original"]*correction, f, sid + " signed calibrated flux", rtol=2e-10, atol=0)
                spectra[sid] = (w.copy(), f.copy(), data["inverse_variance_calibrated"].copy())
        held_path = base / "heldout_z.json"
        held = read_json(held_path)
        for field, path in (("input_colours_sha256", base/"standardized_colours.csv"), ("input_derivative_manifest_sha256", manifest_path), ("input_photometry_rows_sha256", prior_path), ("photometry_definition_document_sha256", self.root/"research/literature/swan_photometry_definition.md")):
            self.hashed(path, held[field])
        held_rows = read_csv(base / "heldout_z.csv")
        require(len(held_rows) == len(held["rows"]) == 27 and {r["source_id"] for r in held_rows} == self.shortlist, "Held-out z row coverage")
        calculated = []
        z = filters.load_filter("panstarrs-z"); y = filters.load_filter("panstarrs-y")
        for r in held_rows:
            sid = r["source_id"]
            if sid not in spectra:
                require(r["z_missing_reason"] != "" and r.get("z_predicted_mag", "") == "", "Held-out missing reason")
                continue
            w, f, iv = spectra[sid]; valid = np.isfinite(f) & np.isfinite(iv) & (iv > 0)
            require(w[valid].min() <= z.wavelength.min() and w[valid].max() >= z.wavelength.max(), "z full passband")
            prediction = float(z.get_ab_magnitude(f[valid], w[valid]))
            close(prediction, float(r["z_predicted_mag"]), sid + " actual held-out z integration", atol=1e-10)
            residual = prediction - float(prior[sid]["swan_external"][0]["Pan-STARRS.z"])
            close(residual, float(r["z_residual_predicted_minus_observed_mag"]), sid + " held-out residual", atol=1e-10)
            require(w.max() < y.wavelength.max() and not yes(r["y_full_passband_coverage"]) and r["y_missing_reason"], "Unavailable y was extrapolated")
            calculated.append(residual)
        require(len(calculated) == held["computed_z"] == 25 and sum(abs(x) > .05 for x in calculated) == held["z_absolute_residual_over_0p05mag"] == 10, "Held-out z summary counts")
        return {"summary": "25/27 PS1 spectra; 12 new anchors; gri residuals and unused z reintegrated (10 |delta z|>0.05 mag)"}

    def nullspace(self):
        import colour_pipeline as pipeline
        base = self.root / "research/precision"
        document = read_json(base / "photometric_nullspace.json")
        for relative, expected in document["input_sha256"].items():
            self.hashed(self.path(relative), expected)
        results = document["results"]
        require(len(results) == len(read_csv(base / "photometric_nullspace.csv")) == 12, "Nullspace result count")
        combos = {(r["candidate"], r["spacing_A"], r["colour_boundary"]) for r in results}
        require(combos == {(c, s, b) for c in ("J0913+4434", "J0429-0354") for s in (400, 800, 1600) for b in ("G-R", "G-B")}, "Nullspace scenario coverage")
        maximum_residual = 0.; maximum_gap = 0.
        for r in results:
            path = base / f"{r['candidate']}_gri_null_{r['spacing_A']}A_{r['colour_boundary']}.npz"
            self.hashed(path)
            with np.load(path) as data:
                w, f, altered, delta = [data[k] for k in ("wavelength_angstrom", "nominal_flux", "distorted_flux", "fractional_distortion")]
                with np.load(self.root / f"results/candidates/{r['candidate']}_DESI_panstarrs.npz") as original:
                    source_w, source_f, _ = pipeline.clean_spectrum(original["wavelength_angstrom"], original["flux_calibrated"], original["inverse_variance"], mask_sky=True)
                    source_f = source_f / np.median(source_f[(source_w > 5000) & (source_w < 7000)])
                    close(w, source_w, "Nullspace original wavelength correspondence", atol=0)
                    close(f, source_f, "Nullspace original cleaned spectrum", rtol=1e-12, atol=1e-12)
                require(np.all(np.isfinite(altered)) and np.all(1+delta > 0), "Nullspace nonpositive multiplier")
                close(altered, f*(1+delta), "Nullspace saved perturbation", rtol=1e-12, atol=1e-12)
                spline = BSpline(data["spline_knots_angstrom"], data["spline_coefficients"], 3)
                close(delta, spline(w), "Nullspace saved spline", atol=1e-12)
                roots = PPoly.from_spline(spline).derivative().roots(extrapolate=False)
                extrema = np.unique(np.r_[roots[np.isfinite(roots)&(roots>=w.min())&(roots<=w.max())], data["spline_knots_angstrom"]])
                upper = float(np.max(np.abs(spline(extrema))))
                gap = upper - r["supremum_lower_bound"]
                require(-1e-10 <= gap < 2e-8, "Nullspace continuous supremum gap")
                close(upper, r["supremum_witness_upper_bound"], "Nullspace continuous extrema", atol=1e-11)
                require(np.min(1+spline(extrema)) > 0, "Nullspace multiplier negative between pixels")
                differences = []
                for flt in filters.load_filters("panstarrs-g", "panstarrs-r", "panstarrs-i"):
                    require(w.min() <= flt.wavelength.min() and w.max() >= flt.wavelength.max(), "Nullspace full photometric coverage")
                    differences.append(float(flt.get_ab_magnitude(altered, w) - flt.get_ab_magnitude(f, w)))
                residual = max(abs(v) for v in differences)
                require(residual < 1e-7, "Nullspace actual speclite constraint residual")
                close(residual, r["synthetic_gri_max_residual_mag"], "Nullspace reported residual", atol=1e-10)
                colour = pipeline.integrate_colour(w, altered, mask_sky=False)
                comparison = "r_linear" if r["colour_boundary"] == "G-R" else "b_linear"
                require(abs(colour["g_linear"] - colour[comparison]) < 1e-6, "Nullspace actual linear-sRGB equality boundary")
                maximum_residual = max(maximum_residual, residual); maximum_gap = max(maximum_gap, gap)
        return {"summary": "12 positive continuous spline witnesses; all actual speclite gri constraints and extrema gaps pass", "maximum_gri_residual_mag": maximum_residual, "maximum_supremum_bound_gap": maximum_gap, "lower_bound_caution": "Recorded LP lower bounds checked against saved witness extrema; the LP is not re-solved and no dual optimality certificate is claimed."}

    def visual(self):
        base = self.root / "research/outlier_audit"
        index_path = base / "contact_sheet_index.csv"
        index = read_csv(index_path); self.hashed(index_path)
        require(len(index) == len({r["entity_id"] for r in index}) == 337, "Visual index entity coverage")
        expected = {(Path(r["contact_sheet"]).name, int(r["panel"])): r for r in index}
        require(len(expected) == 337, "Duplicate image panel keys")
        seen = {}; pages = {}
        for filename, count in (("visual_review_01_11.md", 176), ("visual_review_12_22.md", 161)):
            path = base / filename; text = path.read_text(); self.hashed(path)
            page = None; observations = 0
            for line in text.splitlines():
                match = re.match(r"### Page (\d+)", line)
                if match:
                    page = f"page_{int(match[1]):02}.png"
                elif line.startswith("## "):
                    page = None
                match = re.match(r"\|\s*(\d+)\s*\|\s*([^|]+)\|", line)
                if page and match:
                    key = (page, int(match[1]))
                    require(key in expected and key not in seen, "Visual report/index panel mismatch")
                    identity = expected[key]
                    # The first ledger includes names/IDs; the second includes
                    # exact entity keys. Check either unrounded key form.
                    if identity["source_id"]:
                        require(identity["source_id"] in match[2], f"Visual Gaia ID mismatch: {key}")
                    seen[key] = filename; observations += 1
                match = re.search(r"(page_\d+\.png).*?([0-9a-f]{64})", line)
                if match:
                    require(match[1] not in pages, "Duplicate reviewed-image hash")
                    self.hashed(base/"spectrum_contact_sheets"/match[1], match[2]); pages[match[1]] = match[2]
            require(observations == count, f"Visual ledger row count: {filename}")
        require(set(seen) == set(expected) and len(pages) == 22, "Visual full panel/page coverage")
        return {"summary": "337 individual ledger entries map to index; all 22 actually reviewed image snapshot hashes agree", "limitation": "This verifies the recorded review and image identity, not a fresh visual inspection."}

    def desi(self):
        base = self.root / "research/literature"
        additional = read_json(base / "sources/desi_additional_nights_manifest.json")["epochs"]
        require(len(additional) == 6, "DESI additional-night count")
        direct = additional + [read_json(base / "sources/j1329_desi_20220311_manifest.json")]
        observed = set()
        for item in direct:
            path = base / item["selected_rows_path"]
            self.hashed(path, item["selected_rows_sha256"])
            require(len(item["files"]) == 3, "DESI B/R/Z provenance coverage")
            with np.load(path) as data:
                for arm in "brz":
                    w, f, iv, mask = [data[f"{arm}_{k}"] for k in ("wave_A", "flux", "ivar", "mask")]
                    require(w.shape == f.shape == iv.shape == mask.shape and np.all(np.diff(w)>0), "DESI native row shape")
                    meta = next(r for r in item["files"] if r["arm"] == arm)
                    observed.add((str(meta["NIGHT"]), int(meta["EXPID"]), int(meta.get("FIBER", meta.get("fiber")))))
                    require(len(meta.get("full_file_sha256", meta.get("sha256", ""))) == 64, "DESI missing original full-file hash")
                    if path.name == "j1329_desi_20220311_rows.npz" and arm == "z":
                        require(len(mask) == 2881 and np.all(mask != 0) and np.all(iv == 0), "J1329 missing Z arm was altered")
        require(len(observed) == 7, "DESI distinct direct exposure provenance")
        first = read_json(base / "sources/j1329_desi_20220127_swan_manifest.json")
        self.hashed(base / first["selected_rows_path"], first["selected_rows_sha256"])
        require(all(r["matches_published_rounding"] for r in first["second_epoch_ascii_vs_direct_cframe"]), "Swan ASCII/direct comparison")
        second = read_json(base / "outputs/j1329_second_epoch_comparison.json")
        require(second["full_colour_validation_status"] == "unavailable_missing_valid_z_arm" and all(not r["accepted_calibrated_colour"] for r in second["arm_join_sensitivity"]), "Incomplete DESI colour promoted")
        return {"summary": "7 directly extracted B/R/Z exposures plus first-night Swan extraction hash-checked; masked J1329 Z remains unavailable"}

    def ztf(self):
        base = self.root / "research/external_validation"
        audit = read_json(base / "results/ztf_audit.json")
        candidates, controls = audit["candidate_lightcurves"], audit["control_lightcurves"]
        require((len(candidates), len(controls)) == (17, 18), "ZTF object counts")
        raw_rows = {}
        for item in candidates + controls:
            oid = item["oid"]
            require(isinstance(oid, str) and oid.isdigit(), "ZTF object ID must remain a string")
            path = base / "raw" / f"ztf_dr24_oid_{oid}.csv"
            self.hashed(path, read_json(path.with_suffix(".provenance.json"))["sha256"])
            raw = read_csv(path)
            require(len(raw) == item["n_downloaded"] and all(r["oid"] == oid for r in raw), "ZTF downloaded light-curve count/ID")
            if item in candidates:
                for row in raw:
                    key = (oid, row["expid"])
                    require(key not in raw_rows, "Unexpected duplicate native target exposure")
                    raw_rows[key] = row
        epochs_path = base / "results/target_epoch_decisions.csv.gz"
        epochs = read_csv(epochs_path); self.hashed(epochs_path)
        require(len(epochs) == len(raw_rows) == audit["n_target_raw_epochs"] == 2473, "ZTF retained raw-epoch accounting")
        accepted = []; serialization_rounding = Counter()
        for r in epochs:
            original = raw_rows[(r["oid"], r["expid"])]
            for key in ("mjd", "hjd", "mag", "magerr", "ra", "dec", "chi", "sharp", "clrcoeff"):
                a, b = number(r[key]), number(original[key])
                # pandas' CSV parse/write round-trip changes 486 HJD and 178
                # declination values by exactly one float64 step in this
                # snapshot. Photometry and every other source field must be
                # exact; allow only this bounded representation roundoff.
                one_step = key in ("hjd", "dec") and np.isfinite(a) and np.isfinite(b) and (a == np.nextafter(b, np.inf) or a == np.nextafter(b, -np.inf))
                require((np.isnan(a) and np.isnan(b)) or a == b or one_step, f"ZTF original detection changed: {r['oid']}/{r['expid']}/{key}")
                if one_step:
                    serialization_rounding[key] += 1
            finite = all(np.isfinite(number(r[k])) for k in ("mag", "magerr", "mjd", "hjd", "chi", "sharp", "clrcoeff"))
            quality = finite and int(r["catflags"]) == 0 and number(r["magerr"]) > 0 and 0 < number(r["chi"]) < 3 and abs(number(r["sharp"])) < .5
            association = number(r["target_sep_epoch_arcsec"]) < 1.5
            require(quality == yes(r["quality_ok"]) and association == yes(r["association_ok"]) and (quality and association) == yes(r["accepted"]), "ZTF quality/association selection")
            if yes(r["accepted"]):
                accepted.append(r)
        require(len(accepted) == audit["n_target_accepted_epochs"] == 2327, "ZTF accepted count")
        keys = [(r["candidate"], r["expid"], r["filtercode"], r["ccdid"], r["qid"]) for r in accepted]
        require(len(keys) == len(set(keys)), "ZTF accepted repeated exposure")
        require(sum(r["n_downloaded"] for r in controls) == audit["n_control_raw_epochs"] == 4646, "ZTF control raw count")
        event = read_json(base / "results/J1323_offset_event_review.json")
        matches = [r for r in epochs if r["candidate"] == event["candidate"] and r["expid"] == event["event_expid"]]
        require(len(matches) == 1 and int(matches[0]["catflags"]) == 0 and not yes(matches[0]["accepted"]) and number(matches[0]["target_sep_epoch_arcsec"]) > 1.5, "Offset event not retained/rejected correctly")
        close(number(matches[0]["mag"]), event["event_native_r"], "Offset event raw magnitude", atol=0)
        from astropy.io import fits
        for label in ("before", "offset_event", "after"):
            path = base / "raw" / f"J1323_{label}_science_cutout.fits"
            self.hashed(path, read_json(path.with_suffix(".provenance.json"))["sha256"])
            with fits.open(path) as hdus:
                require(hdus[0].data.ndim == 2 and min(hdus[0].data.shape) >= 40, "ZTF retained cutout is not an image")
        return {"summary": "17 target/18 control light curves; 2473 raw/2327 accepted target epochs and 4646 control epochs; rejected offset event and 3 raw cutouts retained", "float64_one_step_CSV_rounding_only": dict(serialization_rounding)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1], help="Checkout root; independent of current working directory")
    args = parser.parse_args()
    root = args.root.resolve()
    sys.path.insert(0, str(root))
    verification = Verification(root)
    report = {"created_utc": datetime.now(timezone.utc).isoformat(), "offline": True,
              "script_sha256": sha(Path(__file__)), "status": "FAIL", "groups": verification.groups,
              "scope": "Preserved input identity, selection invariants and actual numerical recalculation; no new downloads, human visual review, GaiaXPy run or discovery-significance claim."}
    try:
        for name, function in (("corrected screen and unit registry", verification.screen), ("Gaia coefficient/covariance reconstruction", verification.gaia), ("PS1 calibration and held-out z", verification.photometry), ("photometric nullspace witnesses", verification.nullspace), ("visual review provenance", verification.visual), ("DESI individual exposures", verification.desi), ("ZTF native epochs and offset event", verification.ztf)):
            verification.group(name, function)
        report["status"] = "PASS"
    except Exception as error:
        report["error"] = f"{type(error).__name__}: {error}"
        print("FAIL " + report["error"], file=sys.stderr)
    finally:
        report["verified_file_sha256"] = verification.checked_files
        report["verified_lossless_original_sha256"] = verification.checked_lossless_originals
        (root / "research/verification.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    require(report["status"] == "PASS", "Research extension verification failed; see research/verification.json")
    print(f"PASS research extension: {len(verification.groups)} groups, {len(verification.checked_files)} hashed inputs; report research/verification.json")


if __name__ == "__main__":
    main()
