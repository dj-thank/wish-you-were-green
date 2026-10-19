#!/usr/bin/env python3
"""Verify the October 19 follow-up from committed compact evidence, offline.

Numerical witnesses are re-integrated directly. This script cannot repeat
visual inspection, retrieve survey inputs, or turn a constructed spectrum
into an independent observation or a physical atmosphere-model fit.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import socket
import sys

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MPLCONFIGDIR", "/tmp/wish-green-followup-verify")
import numpy as np
import pandas as pd
from scipy.interpolate import BSpline, PPoly
from speclite import filters


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text())


def close(a, b, name, atol=1e-10):
    np.testing.assert_allclose(a, b, rtol=0, atol=atol, equal_nan=False, err_msg=name)


class FollowupVerification:
    def __init__(self, root):
        self.root = root
        self.checked = {}
        self.groups = []

    def hashed(self, relative, expected=None, base=None):
        path = ((base or self.root) / relative).resolve()
        require(path.is_relative_to(self.root) and path.is_file(), f"Missing committed input: {relative}")
        digest = sha(path)
        require(expected is None or digest == expected, f"Hash differs: {relative}")
        self.checked[str(path.relative_to(self.root))] = digest
        return path

    def group(self, name, function):
        result = function()
        self.groups.append({"name": name, "status": "PASS", **result})
        summary = result["summary"]
        print("PASS " + name + ": " + (summary if isinstance(summary, str) else json.dumps(summary, ensure_ascii=False)), flush=True)

    def calibration(self):
        import colour_pipeline as c
        base = self.root / "research/calibration_followup"
        data = read_json(self.hashed("feasibility_results.json", base=base))
        self.hashed("independent_review.json", base=base)
        table = pd.read_csv(self.hashed("feasibility_summary.csv", base=base), dtype={"source_id": str})
        for path, digest in data["input_sha256"].items():
            self.hashed(path, digest)
        for path, digest in data["code_sha256"].items():
            self.hashed(path, digest)
        derivative_dir = self.root / "research/precision/candidate_recalibration"
        derivatives = {r["source_id"]: r for r in read_json(derivative_dir / "derivative_manifest.json")}
        cohort = pd.read_csv(derivative_dir / "standardized_colours.csv", dtype={"source_id": str})
        require(len(data["cohort"]) == len(derivatives) == 25, "25-spectrum cohort changed")
        require(set(data["cohort"]) == set(derivatives), "A candidate was added or omitted")
        require(set(cohort.source_id) - set(derivatives) == {r["source_id"] for r in data["unavailable_entities"]}, "Two unavailable entities not retained")
        responses = [filters.load_filter("panstarrs-" + b) for b in "griz"]
        for response, stored in zip(responses, data["filter_metadata"]):
            numeric = np.column_stack((response.wavelength, response.response)).astype("<f8")
            require(hashlib.sha256(numeric.tobytes()).hexdigest() == stored["wavelength_response_sha256_little_endian_float64"], "PS1 response changed")
        native = {}
        for sid, meta in data["cohort"].items():
            derivative = derivatives[sid]
            require(derivative["sha256"] == meta["input_sha256"], "Wrong calibrated spectrum")
            p = self.hashed(meta["input_path"], meta["input_sha256"])
            with np.load(p) as saved:
                w, f, iv = c.clean_spectrum(saved["wavelength_angstrom"], saved["flux_calibrated"], saved["inverse_variance_calibrated"], mask_sky=True)
            photometry = derivative["photometry_row"]
            close(meta["observed_mag_griz"], [float(photometry[f"Pan-STARRS.{b}"]) for b in "griz"], "Catalogue magnitudes", atol=0)
            close(meta["quoted_error_mag_griz"], [float(photometry[f"Pan-STARRS.{b}_error"]) for b in "griz"], "Quoted errors", atol=0)
            native[sid] = (w, f)
        expected_keys = {(sid, spacing, bands, k) for sid in derivatives for spacing in (400, 800, 1600) for bands in ("gri", "griz") for k in (0, 1, 2)}
        actual_keys = [(r["source_id"], r["spacing_A"], r["bands"], r["error_multiplier"]) for r in data["results"]]
        require(len(actual_keys) == len(set(actual_keys)) == 450 and set(actual_keys) == expected_keys, "Missing or duplicated experiment scenario")
        require(len(table) == 450 and data["n_LPs"] == 1800, "Scenario/LP accounting")
        index = {key: row for key, row in zip(actual_keys, data["results"])}
        csv_index = {(r.source_id, r.spacing_A, r.bands, r.error_multiplier): r for r in table.itertuples()}
        successes = 0; infeasible = 0; maximum_gap = 0.; maximum_mag_violation = 0.

        def verify_witness(solution, row, knots):
            sid = row["source_id"]; wave, flux = native[sid]
            spline = BSpline(knots, np.asarray(solution["spline_coefficients"]), 3)
            roots = PPoly.from_spline(spline).derivative().roots(extrapolate=False)
            roots = roots[np.isfinite(roots) & (roots >= wave.min()) & (roots <= wave.max())]
            values = spline(np.unique(np.r_[roots, knots]))
            sup = float(np.max(np.abs(values)))
            close(sup, solution["continuous_witness_supremum"], "Continuous supremum", atol=2e-10)
            require(abs(sup - solution["minimum_max_fractional_distortion"]) <= 2e-8, "LP objective / continuous witness disagree")
            require(sup <= .95 + 2e-8 and min(1 + values) >= .05 - 2e-8, "Nonpositive or oversized multiplier")
            # Fresh direct filter integration does not use the saved LP matrix.
            altered = flux * (1 + spline(wave))
            mags = np.array([float(response.get_ab_magnitude(altered, wave)) for response in responses])
            close(mags, solution["synthetic_mag_griz"], "Saved synthetic magnitudes", atol=2e-8)
            obs = np.asarray(data["cohort"][sid]["observed_mag_griz"])
            err = np.asarray(data["cohort"][sid]["quoted_error_mag_griz"])
            nband = len(row["bands"])
            violation = max(0., float(np.max(np.abs(mags[:nband] - obs[:nband]) - row["error_multiplier"] * err[:nband])))
            require(violation <= 1e-7, "Witness violates measured photometry box")
            # Reconstruct XYZ directly using the public observer table and
            # trapezoidal integration rather than the saved colour LP rows.
            selected = (wave >= 3600) & (wave <= 8300)
            nm = wave[selected] / 10
            cmf = np.column_stack([np.interp(nm, c.CMF_W, c.CMF_V[:,i], left=0, right=0) for i in range(3)])
            xyz0 = np.trapezoid(cmf * flux[selected, None], nm, axis=0)
            xyz = np.trapezoid(cmf * altered[selected, None], nm, axis=0)
            require(np.all(xyz >= xyz0 * .9e-8), "Witness has invalid XYZ")
            rgb = c.XYZ_TO_RGB @ xyz
            scale = max(abs(c.XYZ_TO_RGB @ xyz0))
            diff = {"G-R": float((rgb[1] - rgb[0]) / scale), "G-B": float((rgb[1] - rgb[2]) / scale)}
            margin = solution.get("required_normalized_channel_margin", 0.)
            for pair in diff:
                close(diff[pair], solution["normalized_channel_differences"][pair], "Unclipped channel difference", atol=2e-9)
            goal = solution["goal"]
            if goal == "green_closed":
                require(min(diff.values()) >= margin - 1e-7, "Green-region constraint violated")
            elif goal in ("G_le_R", "G_le_B"):
                require(diff[{"G_le_R": "G-R", "G_le_B": "G-B"}[goal]] <= -margin + 1e-7, "Non-green-region constraint violated")
            else:
                require(goal == "photometry", "Unknown LP goal")
            measured = c.xyz_to_metrics(xyz)
            close([measured["u1960"], measured["v1960"]], [solution["metrics"]["u1960"], solution["metrics"]["v1960"]], "Chromaticity", atol=2e-10)
            return sup - solution["minimum_max_fractional_distortion"], violation

        def minimum(row, goal):
            solution = row["solutions"][goal]
            return solution["continuous_witness_supremum"] if solution["success"] else np.inf

        for key, row in index.items():
            require(set(row["solutions"]) == {"photometry", "green_closed", "G_le_R", "G_le_B"}, "Four LP goals required")
            for solution in row["solutions"].values():
                if solution["success"]:
                    gap, violation = verify_witness(solution, row, row["spline_knots_angstrom"])
                    maximum_gap = max(maximum_gap, gap); maximum_mag_violation = max(maximum_mag_violation, violation)
                    successes += 1
                else:
                    require(solution["status"] == "infeasible_within_95pct_bound" and solution["solver_status"] == 2, "Unreported solver failure")
                    infeasible += 1
            csv_row = csv_index[key]
            for csv_column, goal in (("photometry_threshold", "photometry"), ("green_closed_threshold", "green_closed")):
                value = minimum(row, goal)
                require((np.isinf(value) and pd.isna(getattr(csv_row, csv_column))) or abs(value - getattr(csv_row, csv_column)) < 2e-12, "CSV threshold differs from witness")
            non_green = min(minimum(row, "G_le_R"), minimum(row, "G_le_B"))
            require((np.isinf(non_green) and pd.isna(csv_row.non_green_threshold)) or abs(non_green - csv_row.non_green_threshold) < 2e-12, "Non-green union minimum incorrect")
            for budget in (2, 5, 10, 20):
                green_ok = minimum(row, "green_closed") <= budget / 100 + 2e-8
                nongreen_ok = non_green <= budget / 100 + 2e-8
                expected = "both_closed_regions_feasible" if green_ok and nongreen_ok else "green_closed_only" if green_ok else "non_green_only" if nongreen_ok else "photometry_incompatible_with_budget"
                require(getattr(csv_row, f"at_{budget}pct") == expected, "Budget classification changed")
        nested = 0
        for (sid, spacing, bands, k), row in index.items():
            for goal in row["solutions"]:
                value = minimum(row, goal)
                if bands == "griz":
                    require(value + 2e-7 >= minimum(index[(sid, spacing, "gri", k)], goal), "Added band reduced a nested minimum")
                    nested += 1
                if k < 2:
                    require(value + 2e-7 >= minimum(index[(sid, spacing, bands, k + 1)], goal), "Wider photometry interval raised a nested minimum")
                    nested += 1
                if goal != "photometry":
                    require(value + 2e-7 >= minimum(row, "photometry"), "Added colour restriction reduced minimum")
                    nested += 1
        require(nested == data["nested_invariant_checks"] == 3450, "Nested invariants missing")
        demonstration = read_json(self.hashed("contrasting_witnesses.json", base=base))
        for path, digest in demonstration["code_sha256"].items():
            self.hashed(path, digest)
        self.hashed(demonstration["array_path"], demonstration["array_sha256"], base=base)
        with np.load(base / demonstration["array_path"]) as arrays:
            for label, solution in demonstration["solutions"].items():
                row = {"source_id": demonstration["source_id"], "bands": "griz", "error_multiplier": 1}
                verify_witness(solution, row, arrays["spline_knots_angstrom"])
                require(solution["continuous_witness_supremum"] < .05, "Contrasting witness exceeds 5%")
                wave, flux = native[row["source_id"]]
                spline = BSpline(arrays["spline_knots_angstrom"], solution["spline_coefficients"], 3)
                close(arrays[label + "_fractional_distortion"], spline(wave), "Saved contrasting distortion", atol=2e-12)
                np.testing.assert_allclose(arrays[label + "_flux_lambda"], flux * (1 + spline(wave)), rtol=1e-12, atol=0)
            require(demonstration["solutions"]["green"]["metrics"]["green_channel_margin"] > .004,
                    "Green demonstration only touches a boundary")
            require(demonstration["solutions"]["red_above_green"]["metrics"]["green_channel_margin"] < -.004,
                    "Opposite demonstration only touches a boundary")
        for name in ("green_constraint_sensitivity.png", "cohort_photometry_feasibility.png", "J0429_contrasting_griz_witnesses.png"):
            self.hashed(name, base=base)
        return {"summary": f"25 spectra / 450 scenarios / {successes} directly re-integrated witnesses / {infeasible} bounded infeasibilities; 3450 nested constraints; two strict opposite-colour witnesses",
                "maximum_continuous_supremum_gap": maximum_gap, "maximum_fresh_photometry_violation_mag": maximum_mag_violation}

    def display(self):
        base = self.root / "research/outlier_followup/display_diagnostics"
        manifest = read_json(self.hashed("display_manifest.json", base=base))
        notes = read_json(self.hashed("visual_review.json", base=base))
        for path, digest in manifest["input_sha256"].items():
            self.hashed(path, digest)
        screen = pd.read_csv(self.hashed("display_range_screen.csv", base=base), dtype={"source_id": str})
        require(len(screen) == 1684 and len(manifest["selected_entities"]) == 30, "Display census changed")
        require(set(screen.loc[screen.zoom_selected.eq(True), "entity_id"]) == {r["entity_id"] for r in manifest["selected_entities"]}, "Display threshold selection changed")
        require(set(r["entity_id"] for r in notes["rows"]) == {r["entity_id"] for r in manifest["selected_entities"]} and len(notes["rows"]) == 30, "Every selected zoom needs a visual note")
        self.hashed("selected_display_arrays.npz", manifest["display_arrays_sha256"], base=base)
        for page in manifest["pages"]:
            self.hashed(page["path"], page["sha256"], base=base)
        for row in notes["rows"]:
            self.hashed(row["image_path"], row["image_sha256"], base=base)
            require(bool(row["observation_ja"].strip()), "Empty visual observation")
        with np.load(base / "selected_display_arrays.npz") as arrays:
            count = 0
            for obj in manifest["selected_entities"]:
                for curve in obj["display_curves"]:
                    wave, mean, low, high, error = arrays[curve["array_key"]]
                    good = np.isfinite(mean)
                    require(np.all(np.diff(wave) > 0) and np.all(low[good] <= mean[good]) and np.all(mean[good] <= high[good]), "Display bins lost signed extrema")
                    require(np.isfinite(error).any() == (curve["largest_bin_error"] is not None), "Missing-error convention changed")
                    count += 1
        return {"summary": f"1684 automatic display checks; 30 actual visual notes / 8 image hashes / {count} compact curves; original pages retained"}

    def delegated_module(self, relative, module_name):
        path = self.hashed(relative)
        spec = importlib.util.spec_from_file_location(module_name, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        result = module.verify(self.root)
        for path, digest in result.pop("verified_file_sha256", {}).items():
            self.hashed(path, digest)
        require(bool(result.get("summary")), "Module did not report its verification scope")
        return result

    def associations(self):
        from astropy import units as u
        from astropy.coordinates import SkyCoord
        from astropy.io import fits
        from astropy.time import Time
        base = self.root / "research/outlier_followup/association_diagnostics"
        report = read_json(self.hashed("association_summary.json", base=base))
        self.hashed("research/outlier_followup/association_diagnostics.py", report["code_sha256"])
        for path, digest in report["input_sha256"].items():
            self.hashed(path, digest)
        metadata = read_json(self.hashed("gaia_sources.provenance.json", base=base))
        self.hashed("gaia_sources.csv", metadata["sha256"], base=base)
        gaia = pd.read_csv(base / "gaia_sources.csv", dtype={"source_id": str}).set_index("source_id")
        headers = read_json(base / "sdss_original_headers.json")
        table = pd.read_csv(self.root / "research/outlier_followup/record_review.csv.gz", dtype={"source_id": str}, low_memory=False).set_index("row_index")
        values = pd.read_csv(self.hashed("epoch_associations.csv", base=base), dtype={"source_id": str}).set_index("source_id")
        require(len(headers) == len(report["results"]) == len(gaia) == 4, "Four position cases must remain present")
        lookup = {r["row_index"]: r for r in report["results"]}
        maximum_error = 0.
        for entry in headers:
            r = lookup[entry["row_index"]]; sid = entry["source_id"]
            source = gaia.loc[sid]; row = table.loc[entry["row_index"]]
            require(row.source_id == sid and row.archive_origin == "SDSS_DR17_direct", "Wrong original SDSS association")
            require(row.sha256 == entry["original_fits_sha256"], "SDSS source differs from the frozen record")
            compressed = self.hashed(entry["lossless_original_path"], entry["lossless_original_sha256"], base=base)
            raw = gzip.decompress(compressed.read_bytes())
            require(hashlib.sha256(raw).hexdigest() == entry["original_fits_sha256"], "Original FITS bytes differ")
            with fits.open(io.BytesIO(raw)) as hdus:
                h = hdus[0].header
                for name, value in entry["header"].items():
                    require(h.get(name) == value, "Extracted FITS header differs")
                require("PLUG_RA" in h and "PLUG_DEC" in h, "Fibre coordinates absent; plate RA/DEC are not a fallback")
                position = SkyCoord(h["PLUG_RA"]*u.deg, h["PLUG_DEC"]*u.deg)
                epoch = Time(h["MJD"], format="mjd")
            coords = SkyCoord(ra=source.ra*u.deg, dec=source.dec*u.deg,
                              pm_ra_cosdec=source.pmra*u.mas/u.yr, pm_dec=source.pmdec*u.mas/u.yr,
                              obstime=Time(source.ref_epoch, format="jyear"))
            fixed = float(coords.separation(position).arcsec)
            moved = float(coords.apply_space_motion(new_obstime=epoch).separation(position).arcsec)
            for key, computed in (("fixed_2016_separation_arcsec", fixed), ("epoch_propagated_separation_arcsec", moved)):
                close(computed, r[key], "Fresh original-header epoch separation", atol=1e-8)
                close(computed, values.loc[sid, key], "Position CSV agrees", atol=1e-8)
                maximum_error = max(maximum_error, abs(computed - r[key]))
            require(source.phot_variable_flag == r["gaia_phot_variable_flag"] == "NOT_AVAILABLE", "Catalogue availability was reclassified")
            require(pd.isna(source.best_class_name) and r["gaia_best_class_name"] == "", "Unreported catalogue class")
        return {"summary": "Four original SDSS FITS and exact Gaia IDs; fibre coordinates and epoch propagation rederived; unknown variability retained",
                "maximum_separation_reproduction_error_arcsec": maximum_error}

    def spikes(self):
        import colour_pipeline as c
        base = self.root / "research/outlier_followup/spike_diagnostics"
        report = read_json(self.hashed("native_peak_results.json", base=base))
        self.hashed("research/outlier_followup/spike_diagnostics.py", report["code_sha256"])
        for path, digest in report["input_sha256"].items():
            self.hashed(path, digest)
        table = pd.read_csv(self.root / "research/outlier_followup/record_review.csv.gz", dtype={"source_id": str}, low_memory=False).set_index("row_index")
        expected_peaks = {1883: 5854.4, 1502: 7822.4, 2647: 6345.6}
        require({r["row_index"] for r in report["results"]} == set(expected_peaks), "Narrow-peak case selection changed")
        experiments = 0
        for result in report["results"]:
            row = table.loc[result["row_index"]]
            require(row.source_id == result["source_id"] and row.kind == "DESI" and row.plot_status == "plotted_verified_flambda" and row.flux_units_validated == True and row.flux_input_convention == "flambda", "Unverified narrow-peak source")
            require(row.sha256 == result["raw_sha256"], "Peak source differs from the frozen record")
            raw = gzip.decompress(self.hashed(result["lossless_raw_path"], result["lossless_raw_sha256"], base=base).read_bytes())
            require(hashlib.sha256(raw).hexdigest() == result["raw_sha256"] and len(raw) == result["source_size_bytes"], "Original native samples changed")
            lines = raw.decode().splitlines()
            require(lines[1] == "wavelength,flux,sigma,flag", "Unexpected original MWDD DESI schema")
            values = np.loadtxt(io.StringIO("\n".join(lines[2:])), delimiter=",")
            wave, flux, sigma = values[:, 0], values[:, 1], values[:, 2]
            ivar = np.divide(1., sigma*sigma, out=np.zeros_like(sigma), where=np.isfinite(sigma)&(sigma>0))
            if row.calibrated == True:
                correction = 10 ** (-.4*(row.cal_offset_mag + row.cal_tilt_mag_per_1000A*(wave-6200)/1000))
                flux = flux*correction; ivar = ivar/correction**2
            wave, flux, ivar = c.clean_spectrum(wave, flux, ivar, mask_sky=True)
            metrics = c.integrate_colour(wave, flux, ivar, mask_sky=False)
            close([metrics["u1960"], metrics["v1960"]], [row.u1960, row.v1960], "Current native peak colour", atol=1e-7)
            close([metrics["u1960"], metrics["v1960"]], [result["current_metrics"]["u1960"], result["current_metrics"]["v1960"]], "Saved native peak metrics", atol=1e-11)
            search = abs(wave-result["selection_window_center_A"]) <= result["selection_halfwidth_A"]
            peak = np.flatnonzero(search)[np.argmax(flux[search])]
            position = wave[peak]
            close(position, expected_peaks[result["row_index"]], "Check actual feature rather than coarse visual estimate", atol=1e-8)
            close(position, result["peak_wavelength_A"], "Peak position", atol=1e-10)
            side = ((wave >= position-50)&(wave <= position-20)) | ((wave >= position+20)&(wave <= position+50))
            continuum = np.median(flux[side])
            ratio = (flux[peak]-continuum)*np.sqrt(ivar[peak])
            close(ratio, result["peak_excess_over_single_sample_sigma"], "Descriptive pixel ratio", atol=1e-8)
            choices = {"one_peak_sample": np.arange(len(wave)) != peak,
                       "peak_plus_minus_4_A": abs(wave-position)>4,
                       "peak_plus_minus_10_A": abs(wave-position)>10}
            require(len(result["sensitivity_experiments"]) == 3, "Missing deletion sensitivity")
            for exp in result["sensitivity_experiments"]:
                keep = choices[exp["deletion_window"]]
                altered = c.integrate_colour(wave[keep], flux[keep], ivar[keep], mask_sky=False)
                delta = np.hypot(altered["u1960"]-metrics["u1960"], altered["v1960"]-metrics["v1960"])
                require(int((~keep).sum()) == exp["excluded_valid_samples"], "Deletion window changed")
                close(delta, exp["delta_uv"], "Fresh deletion sensitivity", atol=1e-11)
                close(altered["duv"]-metrics["duv"], exp["delta_duv"], "Fresh signed-distance sensitivity", atol=1e-10)
                experiments += 1
        self.hashed("native_peak_checks.png", base=base)
        return {"summary": f"Three original native spectra; exact peak locations, supplied errors and {experiments} explicit deletion sensitivities reproduced; production masks unchanged"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--group", choices=("calibration", "display", "outliers", "models", "targeted", "native", "representations", "all"), default="all")
    args = parser.parse_args()
    root = args.root.resolve(); sys.path.insert(0, str(root))
    def forbidden(*args, **kwargs):
        raise RuntimeError("Network use is forbidden during offline verification")
    socket.create_connection = forbidden
    socket.getaddrinfo = forbidden
    verification = FollowupVerification(root)
    report = {"created_utc": datetime.now(timezone.utc).isoformat(), "offline": True,
              "script_sha256": sha(Path(__file__)), "status": "FAIL", "groups": verification.groups,
              "limits": "Checks committed evidence and numerical invariants; does not repeat actual visual review, survey downloads or native atmosphere fitting"}
    try:
        if args.group in ("calibration", "all"):
            verification.group("measured photometry feasibility", verification.calibration)
        if args.group in ("display", "all"):
            verification.group("supplemental display review", verification.display)
        if args.group in ("outliers", "all"):
            verification.group("complete individual review", lambda: verification.delegated_module("research/outlier_followup/verify_outputs.py", "verify_outlier_followup"))
        if args.group in ("models", "all"):
            verification.group("published model comparisons", lambda: verification.delegated_module("research/model_validation/verify_outputs.py", "verify_model_followup"))
        if args.group in ("targeted", "all"):
            verification.group("targeted catalogue and feature checks", lambda: verification.delegated_module("research/outlier_followup/verify_targeted.py", "verify_targeted_followup"))
        if args.group in ("native", "all"):
            verification.group("epoch position associations", verification.associations)
            verification.group("native narrow-peak sensitivity", verification.spikes)
        if args.group in ("representations", "all"):
            verification.group("same-observation calibration branches", lambda: verification.delegated_module("research/outlier_followup/representation_calibration/verify_outputs.py", "verify_representation_followup"))
        report["status"] = "PASS"
    except Exception as error:
        report["error"] = f"{type(error).__name__}: {error}"
        print("FAIL " + report["error"], file=sys.stderr)
    finally:
        report["verified_file_sha256"] = verification.checked
        target = root / "research" / ("followup_verification.json" if args.group == "all" else f"followup_verification_{args.group}.json")
        target.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    require(report["status"] == "PASS", "Follow-up verification failed")
    print("PASS follow-up verification", len(verification.groups), "groups", len(verification.checked), "hashed files")


if __name__ == "__main__":
    main()
