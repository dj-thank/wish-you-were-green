#!/usr/bin/env python3
"""Verify the committed compact research inputs and results without data downloads.

This checks archival input identity and the input-to-result chain. It does not
rerun the full survey, infer discovery significance, or download GaiaXPy models.
See docs/reproducibility.en.md for the scientific scope and tolerances.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import importlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile


HEADLINE_IDS = {
    "J0913+4434": "818833831355548928",
    "J0429-0354": "3204436719718449280",
    "J1329+0033": "3711047662972690688",
    "J1323-0129": "3638333660492606976",
}
GAIA_FILES = {
    f"{source}_{basis}_1nm.npz"
    for source in ("j0913", "j0429")
    for basis in ("full", "truncated")
}


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def resolve_input(root, value):
    """Require the local committed copy, including for historical absolute paths."""
    value = str(value)
    marker = "wd-colour-research/"
    path = root / value.split(marker, 1)[1] if marker in value else Path(value)
    if not path.is_absolute():
        path = root / path
    path = path.resolve()
    require(path.is_relative_to(root), f"Input escapes this checkout: {value}")
    require(path.is_file(), f"Missing committed input: {path.relative_to(root)}")
    return path


def table_path(root, relative):
    for suffix in ("", ".gz"):
        path = root / (relative + suffix)
        if path.is_file():
            return path
    raise FileNotFoundError(f"Missing {relative} (or its .gz copy) in {root}")


def open_text(path):
    opener = gzip.open if path.suffix == ".gz" else open
    return opener(path, "rt", encoding="utf-8", newline="")


def read_json(root, relative):
    with open_text(table_path(root, relative)) as stream:
        return json.load(stream)


def read_csv(root, relative):
    # csv preserves 18/19-digit Gaia source IDs as strings.
    with open_text(table_path(root, relative)) as stream:
        return list(csv.DictReader(stream))


def verify_sha256(path, expected):
    require(isinstance(expected, str) and len(expected) == 64,
            f"Missing SHA-256 for {path.name}")
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    require(actual == expected, f"SHA-256 mismatch for {path.name}: {actual}")


def close(np, actual, expected, label, *, rtol=0.0, atol=2e-8):
    try:
        np.testing.assert_allclose(actual, expected, rtol=rtol, atol=atol,
                                   equal_nan=False, err_msg=label)
    except AssertionError as error:
        raise AssertionError(f"{label}\n{error}") from error


def verify_reference(root, np, pipeline):
    relative = "reference/CIE_xyz_1931_2deg.csv"
    path = resolve_input(root, relative)
    metadata = read_json(root, relative + "_metadata.json")
    expected = next(item["checksum"] for item in metadata["checksums"]
                    if item["hashMethod"].lower() == "sha256")
    verify_sha256(path, expected)
    cmf = np.loadtxt(path, delimiter=",")
    require(cmf.shape == (471, 4), "Unexpected official CIE table dimensions")
    require(np.array_equal(cmf[:, 0], np.arange(360.0, 831.0)),
            "CIE reference must cover 360--830 nm at 1 nm spacing")
    require(np.array_equal(pipeline.CMF_W, cmf[:, 0]) and
            np.array_equal(pipeline.CMF_V, cmf[:, 1:]),
            "Pipeline is not using the committed official CIE table")
    print("PASS CIE reference: official checksum and 471-sample table")
    return cmf


def verify_headlines(root, np, pipeline):
    table = read_csv(root, "results/headline_candidates.csv")
    require(len(table) == 4 and {r["candidate"] for r in table} == set(HEADLINE_IDS),
            "Headline table must contain exactly the four reported candidates")
    manifest = read_json(root, "mwdd/manifest_enriched.json")
    for result in table:
        name = result["candidate"]
        require(result["source_id"] == HEADLINE_IDS[name], f"Source identity changed: {name}")
        require(result["kind"] == "DESI" and result["cal_system"] == "panstarrs",
                f"Unexpected headline instrument/photometry system: {name}")
        records = [r for r in manifest
                   if r.get("source_id") == result["source_id"]
                   and r.get("kind") == "DESI"
                   and r.get("sha256") == result["raw_sha256"]]
        require(len(records) == 1, f"Expected one exact raw-spectrum identity for {name}")
        record = records[0]
        require(record["source_url"] == result["source_url"], f"Source URL changed: {name}")
        raw_path = resolve_input(root, record["raw_path"])
        parsed_path = resolve_input(root, record["parsed_path"])
        require(resolve_input(root, result["parsed_path"]) == parsed_path,
                f"Headline and source manifest point to different arrays: {name}")
        require(pipeline.data_path(record["parsed_path"]).resolve() == parsed_path,
                f"Pipeline path resolution does not use this checkout: {name}")
        verify_sha256(raw_path, result["raw_sha256"])

        # Independently parse the original survey export and compare every column.
        lines = raw_path.read_text(encoding="utf-8").splitlines()
        require("source:DESI DR1" in lines[0], f"Unexpected raw survey metadata: {name}")
        columns = next(csv.reader([lines[1]]))
        require(columns == ["wavelength", "flux", "sigma", "flag"],
                f"Unexpected raw DESI columns: {name}")
        raw = np.loadtxt(io.StringIO("\n".join(lines[2:])), delimiter=",", ndmin=2)
        with np.load(parsed_path, allow_pickle=False) as parsed:
            for index, key in enumerate(("wavelength_angstrom", "flux_original", "sigma", "flag")):
                require(key in parsed and np.array_equal(raw[:, index], parsed[key], equal_nan=True),
                        f"Raw-to-NPZ mismatch in {name}: {key}")
        wave, flux, sigma = raw[:, :3].T
        require(np.all(np.diff(wave) > 0) and wave[0] == 3600.0 and wave[-1] > 9800,
                f"Unexpected angstrom wavelength grid: {name}")
        require(np.all(np.isfinite(flux)), f"Non-finite raw flux: {name}")
        require(np.any(flux < 0), f"Negative noisy samples appear to have been clipped: {name}")
        inverse_variance = np.divide(1.0, sigma**2, out=np.zeros_like(sigma),
                                     where=np.isfinite(sigma) & (sigma > 0))
        photometry = record["photometry"]
        observed = np.array([float(result[f"anchor_{b}_mag"]) for b in "gri"])
        errors = np.array([float(result[f"anchor_{b}_error"]) for b in "gri"])
        close(np, observed, [float(photometry[f"PS_{b}"]) for b in "gri"],
              f"PS1 anchor values: {name}", atol=1e-8)
        close(np, errors, [float(photometry[f"DPS_{b}"]) for b in "gri"],
              f"PS1 anchor errors: {name}", atol=1e-8)

        calibrated, fit = pipeline.recalibrate_gri(wave, flux, observed, errors, "panstarrs")
        correction = 10 ** (-0.4 * (fit["cal_offset_mag"] +
                          fit["cal_tilt_mag_per_1000A"] * (wave - 6200) / 1000))
        metrics = pipeline.integrate_colour(wave, calibrated,
                                             inverse_variance / correction**2, mask_sky=True)
        for key in ("x", "y", "u1960", "v1960", "duv", "green_channel_margin"):
            close(np, metrics[key], float(result[key]), f"Headline {key}: {name}")
        for key in ("cal_offset_mag", "cal_tilt_mag_per_1000A", "cal_max_residual_mag"):
            close(np, fit[key], float(result[key]), f"Headline calibration {key}: {name}", atol=2e-6)
        require(metrics["hex"] == result["hex"], f"Headline HEX changed: {name}")
        print(f"PASS DESI {name}: raw SHA/NPZ/PS1 anchors; "
              f"x={metrics['x']:.9f} y={metrics['y']:.9f} "
              f"Duv={metrics['duv']:+.9f} {metrics['hex']}")


def gaussian_green_probability(np, xyz, covariance, matrix):
    """Deterministic bivariate Gaussian integral, independent of saved MC draws."""
    from scipy.integrate import quad
    from scipy.special import ndtr

    differences = np.array([matrix[1] - matrix[0], matrix[1] - matrix[2]])
    mean = differences @ xyz
    cov = differences @ covariance @ differences.T
    std = np.sqrt(np.diag(cov))
    require(np.all(std > 0), "Degenerate Gaia channel-order covariance")
    a, b = mean / std
    rho = float(cov[0, 1] / (std[0] * std[1]))
    require(abs(rho) < 1, "Invalid Gaia channel correlation")
    conditional_std = np.sqrt(1 - rho**2)
    value, error = quad(lambda t: np.exp(-t*t/2) / np.sqrt(2*np.pi) *
                        ndtr((b-rho*t)/conditional_std), -np.inf, a,
                        epsabs=1e-10, epsrel=1e-10)
    require(error < 1e-7, "Gaussian channel-order integral did not converge")
    return float(value)


def verify_gaia(root, np, pipeline, cmf):
    from scipy.linalg import eigvalsh

    base = root / "mwdd/gaia_validation"
    source_manifest = read_json(root, "mwdd/gaia_validation/source_manifest.json")
    for prefix, source_id in (("j0913", HEADLINE_IDS["J0913+4434"]),
                              ("j0429", HEADLINE_IDS["J0429-0354"])):
        name = f"{prefix}_xp_continuous.csv"
        record = next(item for item in source_manifest if Path(item["path"]).name == name)
        path = resolve_input(root, base / name)
        verify_sha256(path, record["sha256"])
        with path.open(encoding="utf-8", newline="") as stream:
            source = next(csv.DictReader(stream))
        require(source["source_id"] == source_id, f"ESA coefficient source ID changed: {prefix}")

    essentials = read_json(root, "mwdd/gaia_validation/essential_validation_files.json")
    expected_hashes = {item["path"]: item["sha256"] for item in essentials["files"]}
    summaries = read_json(root, "mwdd/gaia_validation/gaia_candidate_summary.json")
    require(len(summaries) == 4 and {r["spectrum"] for r in summaries} == GAIA_FILES,
            "Gaia summary must contain both full/truncated 1 nm products for both stars")

    for saved in summaries:
        name = saved["spectrum"]
        path = resolve_input(root, base / name)
        verify_sha256(path, expected_hashes[name])
        with np.load(path, allow_pickle=False) as spectrum:
            wave = spectrum["wavelength_nm"]
            flux = spectrum["flux_w_m2_nm"]
            error = spectrum["flux_error_w_m2_nm"]
            covariance = spectrum["covariance_w2_m4_nm2"]
            correlation = spectrum["correlation"]
            close(np, spectrum["wavelength_angstrom"], wave * 10, f"Gaia wavelength units: {name}", atol=0)
        require(np.array_equal(wave, np.arange(330.0, 1051.0)), f"Unexpected Gaia 1 nm grid: {name}")
        require(flux.shape == error.shape == (721,) and covariance.shape == correlation.shape == (721, 721),
                f"Unexpected Gaia array dimensions: {name}")
        require(all(np.all(np.isfinite(v)) for v in (flux, error, covariance, correlation)),
                f"Non-finite Gaia data/covariance: {name}")
        require(np.all(error > 0), f"Nonpositive Gaia flux uncertainty: {name}")
        scale = float(np.max(np.diag(covariance)))
        require(scale > 0, f"Nonpositive Gaia variance scale: {name}")
        close(np, covariance / scale, covariance.T / scale,
              f"Gaia covariance symmetry: {name}", atol=1e-12)
        close(np, np.diag(covariance), error**2,
              f"Gaia covariance diagonal and supplied errors: {name}", rtol=2e-10, atol=0)
        close(np, covariance / scale, correlation * np.outer(error, error) / scale,
              f"Gaia covariance/correlation consistency: {name}", rtol=2e-10, atol=1e-12)
        minimum_eigenvalue = float(eigvalsh(covariance / scale, subset_by_index=[0, 0],
                                          check_finite=False)[0])
        require(minimum_eigenvalue > -1e-8, f"Gaia covariance is not positive semidefinite: {name}")

        visible = (wave >= 360) & (wave <= 830)
        w, f = wave[visible], flux[visible]
        require(np.array_equal(w, cmf[:, 0]), f"Gaia/CIE wavelength alignment changed: {name}")
        # Native F_lambda in W m^-2 nm^-1. This dimensional XYZ/covariance check
        # also catches a common multiplier that chromaticity alone cannot catch.
        xyz = np.trapezoid(f[:, None] * cmf[:, 1:], w, axis=0)
        width = np.empty(len(w))
        width[0], width[-1] = (w[1]-w[0])/2, (w[-1]-w[-2])/2
        width[1:-1] = (w[2:]-w[:-2])/2
        weights = cmf[:, 1:] * width[:, None]
        projected = weights.T @ covariance[np.ix_(visible, visible)] @ weights
        close(np, xyz, saved["xyz_native"], f"Gaia native XYZ: {name}", rtol=2e-10, atol=0)
        close(np, projected, saved["xyz_covariance_native"],
              f"Gaia full-covariance XYZ projection: {name}", rtol=2e-9, atol=0)
        metrics = pipeline.integrate_colour(wave*10, flux, mask_sky=False)
        for key in ("x", "y", "u1960", "v1960", "duv"):
            close(np, metrics[key], saved[key], f"Gaia mean {key}: {name}", atol=2e-10)
        require(metrics["hex"] == saved["hex"], f"Gaia mean HEX changed: {name}")

        # Differentiate the homogeneous XYZ -> (u,v) map using its matrix form.
        numerator = np.array([[4.0, 0, 0], [0, 6.0, 0]])
        denominator_vector = np.array([1.0, 15.0, 3.0])
        denominator = float(denominator_vector @ xyz)
        jacobian = (numerator * denominator -
                    np.outer(numerator @ xyz, denominator_vector)) / denominator**2
        uv_cov = jacobian @ projected @ jacobian.T
        close(np, uv_cov, saved["uv_covariance_first_order"],
              f"Gaia first-order uv covariance: {name}", rtol=2e-9, atol=0)
        norm_xyz, norm_cov = xyz / xyz[1], projected / xyz[1]**2
        probability = gaussian_green_probability(np, norm_xyz, norm_cov, pipeline.XYZ_TO_RGB)
        published = saved["probability_linear_green_largest_formal_only"]
        n_draws = int(saved["n_mc"])
        # The archived probability came from finite Monte Carlo, not this exact
        # two-dimensional integral. Allow five binomial SE plus 0.0005.
        tolerance = 5*np.sqrt(probability*(1-probability)/n_draws) + 0.0005
        require(abs(probability-published) <= tolerance,
                f"Gaia formal green probability inconsistent with full covariance: {name}")
        require(0.5 < probability < 0.99,
                f"Gaia coefficient noise alone must not be reported as certain greenness: {name}")
        print(f"PASS Gaia {name}: native mean/full covariance/PSD; "
              f"Duv={metrics['duv']:+.9f} {metrics['hex']}; "
              f"formal Gaussian P(G largest)={probability:.4f}")


def verify_archived_controls(root, np):
    """Check the saved control result; deliberately do not claim raw reanalysis."""
    manifest = read_json(root, "sdss/manifest_with_photometry.json")
    controls = {r["spectrum_id"]: r["selection_group"] for r in manifest
                if r.get("selection_group", "").startswith("control_")}
    require(len(controls) == 54, "Expected 54 selected SDSS controls in source manifest")
    try:
        rows = read_csv(root, "results/sdss_screen.csv")
    except FileNotFoundError:
        rows = read_csv(root, "results/all_spectra_screen.csv")
    frozen = [r for r in rows if r.get("archive_origin") == "SDSS_DR17_direct"
              and r.get("selection_group", "").startswith("control_")]
    require(len(frozen) == 54 and {r["spectrum_id"] for r in frozen} == set(controls),
            "Saved control results do not match the 54 original spectrum identities")
    expected_groups = {"control_DA", "control_DB", "control_DC"}
    require(set(controls.values()) == expected_groups, "Unexpected control classes")
    for group in sorted(expected_groups):
        records = [r for r in frozen if r["selection_group"] == group]
        require(len(records) == 18, f"Expected 18 saved {group} records")
        require(all(r["status"] == "ok" and r["usable_screen"].lower() == "true" for r in records),
                f"A saved {group} control was not usable")
        distances = np.array([float(r["distance_planck_uv"]) for r in records])
        require(np.all(np.isfinite(distances)) and np.all(distances < 0.01),
                f"Saved {group} controls no longer pass the stated thermal-locus check")
        require(all(r["green_dominant"].lower() == "false" for r in records),
                f"A saved {group} control is unexpectedly green-dominant")
        print(f"PASS ARCHIVED RESULTS ONLY {group}: 18 records; "
              f"max distance={distances.max():.6f}; raw SDSS not rerun")
    return controls, frozen


def verify_control_spectra(root, np, pipeline, controls, frozen):
    """Recompute the supplied 54 controls, without reacquiring any survey data."""
    from astropy.io import fits

    records = read_json(root, "results/screen_input_sdss.json")
    selected = {r["spectrum_id"]: r for r in records if r["spectrum_id"] in controls}
    require(set(selected) == set(controls), "Frozen SDSS inputs omit a selected control")
    results = {r["spectrum_id"]: r for r in frozen}
    counts = {group: 0 for group in set(controls.values())}
    for spectrum_id, record in selected.items():
        raw_path = resolve_input(root, record["raw_path"])
        parsed_path = resolve_input(root, record["parsed_path"])
        verify_sha256(raw_path, record["sha256"])
        require(pipeline.data_path(record["parsed_path"]).resolve() == parsed_path,
                f"SDSS control path points outside this checkout: {spectrum_id}")
        with fits.open(raw_path, memmap=False) as hdus:
            coadd = hdus[1].data
            flux = np.asarray(coadd["flux"], dtype=float)
            ivar = np.asarray(coadd["ivar"], dtype=float)
            expected = {
                "wavelength_angstrom": 10.0 ** np.asarray(coadd["loglam"], dtype=float),
                "flux_flam": flux * 1e-17,
                "ivar": ivar / 1e-34,
                "flux_sdss": flux,
                "ivar_sdss": ivar,
            }
            names = {name.lower() for name in coadd.names}
            for key in ("and_mask", "or_mask", "wdisp", "sky", "model"):
                if key in names:
                    expected[key] = np.asarray(coadd[key])
            with np.load(parsed_path, allow_pickle=False) as parsed:
                require(set(parsed.files) == set(expected),
                        f"SDSS control parsed fields changed: {spectrum_id}")
                for key, values in expected.items():
                    require(np.array_equal(parsed[key], values, equal_nan=True),
                            f"SDSS raw FITS-to-NPZ unit/data mismatch: {spectrum_id} {key}")
        calculated = pipeline.analyze_record(record)
        saved = results[spectrum_id]
        require(calculated.get("status") == "ok", f"SDSS control calculation failed: {spectrum_id}")
        for key in ("x", "y", "u1960", "v1960", "duv"):
            close(np, calculated[key], float(saved[key]), f"Recomputed SDSS {key}: {spectrum_id}")
        require(calculated["hex"] == saved["hex"], f"Recomputed SDSS HEX changed: {spectrum_id}")
        require(calculated["distance_planck_uv"] < 0.01 and not calculated["green_dominant"],
                f"Recomputed negative control no longer meets the stated result: {spectrum_id}")
        counts[controls[spectrum_id]] += 1
    for group, count in sorted(counts.items()):
        require(count == 18, f"Incomplete raw control verification: {group}")
        print(f"PASS RECOMPUTED SDSS {group}: {count} raw FITS hashes, "
              "physical-unit NPZ arrays, and calibrated colours")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1],
                        help="Research checkout to verify; defaults to this script's parent checkout")
    parser.add_argument("--with-controls", action="store_true",
                        help="Also recompute the 54 committed SDSS controls from raw FITS/NPZ inputs")
    args = parser.parse_args()
    root = args.root.resolve()
    require((root / "colour_pipeline.py").is_file(), f"Not a research checkout: {root}")

    # The scientific check has no data-network dependency. A library trying a
    # socket connection or DNS lookup is an error, rather than a hidden download.
    def offline_audit(event, arguments):
        if event in {"socket.connect", "socket.getaddrinfo"}:
            raise RuntimeError(f"Offline verification forbids {event}")

    sys.addaudithook(offline_audit)
    sys.dont_write_bytecode = True
    os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    os.environ.setdefault("MPLBACKEND", "Agg")
    sys.path.insert(0, str(root))
    with tempfile.TemporaryDirectory(prefix="wd-colour-verifier-") as cache:
        os.environ["MPLCONFIGDIR"] = cache
        import numpy as np
        pipeline = importlib.import_module("colour_pipeline")
        require(Path(pipeline.__file__).resolve() == root / "colour_pipeline.py",
                "Imported pipeline belongs to a different checkout")
        cmf = verify_reference(root, np, pipeline)
        verify_headlines(root, np, pipeline)
        verify_gaia(root, np, pipeline, cmf)
        controls, frozen = verify_archived_controls(root, np)
        if args.with_controls:
            verify_control_spectra(root, np, pipeline, controls, frozen)
    control_label = "54 recomputed raw SDSS controls" if args.with_controls else "the explicitly archived 54-control result"
    print("PASS offline reproduction: 4 DESI headlines, 4 Gaia mean/covariance products, "
          f"and {control_label}. No full-survey rerun or discovery claim.")


if __name__ == "__main__":
    try:
        main()
    except (AssertionError, FileNotFoundError, KeyError, ValueError, RuntimeError) as error:
        print(f"FAIL offline reproduction: {error}", file=sys.stderr)
        sys.exit(1)
