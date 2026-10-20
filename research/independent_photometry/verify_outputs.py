#!/usr/bin/env python3
"""Verify and regenerate this catalogue extension without network or cache access."""
from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import math
import tempfile
import warnings
from collections import Counter
from pathlib import Path

import astropy.units as u
from astropy.coordinates import SkyCoord
from astropy.time import Time
from erfa import ErfaWarning

HERE = Path(__file__).resolve().parent


def module(path):
    spec = importlib.util.spec_from_file_location("independent_photometry_builder", path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def compare(left, right, location=""):
    """Tolerances cover rounding, with scale-aware checks for physical fluxes."""
    if isinstance(left, dict):
        assert set(left) == set(right), (location, "keys")
        for key in left:
            compare(left[key], right[key], location + "/" + key)
    elif isinstance(left, list):
        assert len(left) == len(right), (location, "length")
        for i, (a, b) in enumerate(zip(left, right)):
            compare(a, b, location + f"/{i}")
    elif isinstance(left, float):
        assert isinstance(right, (int, float)), location
        key = location.rsplit("/", 1)[-1]
        if "flux" in key or "fnu" in key:
            atol = 0.0
        elif "arcsec" in key:
            atol = 1e-7
        elif "mjd" in key:
            atol = 1e-9
        else:
            atol = 1e-11
        assert math.isclose(left, right, rel_tol=1e-11, abs_tol=atol), (location, left, right)
    else:
        assert type(left) is type(right) and left == right, (location, left, right)


def verify(root: Path) -> dict:
    root = Path(root).resolve()
    base = root / "research/independent_photometry"
    build = module(base / "build_catalogue.py")
    manifest = json.loads((base / "source_manifest.json").read_text())
    hashes = dict(manifest["upstream_input_sha256"])
    for entry in manifest["raw_responses"]:
        hashes[entry["path"]] = entry["sha256"]
        hashes[entry["provenance_path"]] = entry["provenance_sha256"]
        if "query_path" in entry:
            hashes[entry["query_path"]] = entry["query_sha256"]
    for path, expected in hashes.items():
        assert build.sha(root / path) == expected, (path, "input SHA mismatch")

    with tempfile.TemporaryDirectory(prefix="wd_independent_photometry_verify_") as tmp:
        regenerated = Path(tmp)
        summary = build.build(root, regenerated)
        products = ["measurements.csv", "coverage.csv", "identity_audit.csv",
                    "skymapper_exposure_audit.csv", "gaia_neighbour_audit.csv",
                    "splus_access_audit.csv", "measurements.json", "source_manifest.json", "summary.json"]
        for name in products:
            if name.endswith(".json"):
                compare(json.loads((base / name).read_text()),
                        json.loads((regenerated / name).read_text()), name)
            else:
                original = build.read_rows(base / name)
                new = build.read_rows(regenerated / name)
                assert len(original) == len(new), name
                for i, (left, right) in enumerate(zip(original, new)):
                    assert set(left) == set(right), name
                    for key in left:
                        if left[key] == right[key]:
                            continue
                        # Decimal identifiers and booleans must match exactly.
                        assert not key.endswith("_id") and key != "source_id", (name, i, key)
                        compare(float(left[key]), float(right[key]), f"{name}/{i}/{key}")
        prior = module(base / "prior_classifications.py")
        reproduced_prior = prior.build(root, regenerated)
        compare(json.loads((base / "prior_classifications.json").read_text()),
                reproduced_prior, "prior_classifications.json")
        assert build.read_rows(base / "prior_classifications.csv") == build.read_rows(regenerated / "prior_classifications.csv")
        assert reproduced_prior["known_classes_by_source"] == {
            "1691957732959636608": 1, "2119909923600264960": 0, "2739231150982741760": 2}
        assert reproduced_prior["fixed_candidates"] == 25 and reproduced_prior["matched_candidates"] == 3
        products += ["prior_classifications.json", "prior_classifications.csv"]

    values = json.loads((base / "measurements.json").read_text())["measurements"]
    cohort = json.loads((root / build.MANIFEST).read_text())
    ids = {r["source_id"] for r in cohort}
    assert len(ids) == 25
    assert len(values) == 450
    assert {r["source_id"] for r in values} == ids
    assert all(isinstance(r["source_id"], str) and r["source_id"].isdecimal() for r in values)
    assert len({(r["source_id"], r["survey"], r["band"]) for r in values}) == 450
    counts = Counter(r["source_id"] for r in values)
    assert set(counts.values()) == {18}
    # Independently express the recorded quality gates, without fitting colours.
    for row in values:
        finite_mag = row["mag_ab"] is not None and row["mag_ab"] < 90
        error = row["mag_error_with_zeropoint"]
        finite_error = error is not None and 0 < error <= 0.1
        if row["catalogue_id"] is None:
            assert not row["adopted"] and row["mag_ab"] is None
            assert row["quality_reasons"] == "no_identified_catalogue_counterpart"
            continue
        assert row["pm_match_sep_arcsec"] <= 1
        if row["survey"] == "SkyMapper_DR4":
            expected = (finite_mag and finite_error and row["number_good_exposures"] >= 2
                        and row["number_included_exposures"] >= 2
                        and row["filter_flags"] == 0 and row["bad_pixel_or_mask_flags"] == 0
                        and row["zero_mask_in_all_included"] and not row["psf_neighbour_flag"])
            assert error == row["mag_error_quoted"]
        else:
            expected = (finite_mag and finite_error and row["filter_flags"] == 0
                        and row["bad_pixel_or_mask_flags"] == 0 and row["tile_flags"] == 0
                        and row["variable_flag"] == 0 and row["single_detection_id"] > 0
                        and row["relative_weight"] >= 0.8 and row["number_good_exposures"] >= 2)
            wanted = math.sqrt(row["mag_error_quoted"] ** 2 + row["zeropoint_error_to_add"] ** 2)
            assert math.isclose(error, wanted, abs_tol=1e-14)
            if row["calibrated_fnu_cgs"] and row["calibrated_fnu_cgs"] > 0 and finite_mag:
                mag = (row["calibrated_fnu_cgs"] * u.erg / (u.s * u.cm ** 2 * u.Hz)).to(u.ABmag).value
                assert abs(mag - row["mag_ab"]) < 0.00015
        assert bool(expected) == row["adopted"], (row["source_id"], row["band"], "quality mismatch")
    assert Counter(r["survey"] for r in values if r["adopted"]) == {"SkyMapper_DR4": 20, "JPLUS_DR4": 32}
    assert len({r["source_id"] for r in values if r["adopted"]}) == 14

    # Separate implementation of proper motion through Astropy/ERFA.  This also
    # catches treating mu_alpha*cos(delta) as bare mu_alpha at high declination.
    gaia = {r["source_id"]: r for r in build.read_rows(root / build.GAIA)}
    identities = build.read_rows(base / "identity_audit.csv")
    differences = []
    for row in identities:
        if not row["catalogue_epoch_mjd"]:
            continue
        ref = gaia[row["source_id"]]
        coordinate = SkyCoord(ra=float(ref["ra"]) * u.deg, dec=float(ref["dec"]) * u.deg,
            pm_ra_cosdec=float(ref["pmra"]) * u.mas / u.yr, pm_dec=float(ref["pmdec"]) * u.mas / u.yr,
            obstime=Time(float(ref["ref_epoch"]), format="jyear"))
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", ErfaWarning)  # No measured radial velocity/distance assumed.
            moved = coordinate.apply_space_motion(new_obstime=Time(float(row["catalogue_epoch_mjd"]), format="mjd"))
        cat = SkyCoord(ra=float(row["catalogue_ra_deg"]) * u.deg, dec=float(row["catalogue_dec_deg"]) * u.deg)
        differences.append(abs(moved.separation(cat).arcsec - float(row["pm_match_sep_arcsec"])))
        assert (row["selected_identity"] == "True") == (
            row["published_nearest_gaia_source_id"] == row["source_id"]
            and moved.separation(cat).arcsec <= 1.0)
    assert max(differences) < 1e-6, max(differences)

    aliases = {(r["source_id"], r["catalogue_id"]): r for r in identities}
    for sid, cat_id in [("1182083542272959232", "2421604951"),
                        ("4545191991882663936", "2427456996"),
                        ("3638333660492606976", "107990965"),
                        ("761677269868775040", "190232:15354")]:
        row = aliases[sid, cat_id]
        assert row["selected_identity"] == "False" and float(row["pm_match_sep_arcsec"]) > 8
    assert aliases["3638333660492606976", "107990969"]["selected_identity"] == "True"
    row = next(r for r in values if r["source_id"] == "3204436719718449280" and r["survey"] == "SkyMapper_DR4" and r["band"] == "g")
    assert not row["adopted"] and row["official_good_sensitivity"]
    assert row["bad_pixel_or_mask_flags"] == 4 and row["mag_ab"] == 19.1114
    assert not any(r["adopted"] for r in values if r["source_id"] == "2513256394506328832" and r["survey"] == "JPLUS_DR4")

    for name in products + ["build_catalogue.py", "prior_classifications.py", "verify_outputs.py"]:
        path = base / name
        hashes[str(path.relative_to(root))] = build.sha(path)
    return dict(summary=dict(fixed_candidates=25, slots=450, strict_measurements=52,
        sources_with_strict_measurements=14, catalogue_rows_checked=len(identities),
        proper_motion_independent_max_difference_arcsec=max(differences),
        skymapper_exposures_checked=summary["skymapper_raw_detection_rows"],
        original_input_hashes_checked=len(manifest["upstream_input_sha256"]) +
            sum(2 + ("query_path" in r) for r in manifest["raw_responses"]),
        regenerated_products=len(products), published_classifications_checked=3,
        splus_failed_queries_distinguished_from_nondetections=25,
        status="PASS"), verified_file_sha256=hashes)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=HERE.parents[1])
    parser.add_argument("--json", type=Path)
    args = parser.parse_args()
    result = verify(args.root)
    if args.json:
        args.json.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print("PASS independent photometry: " + json.dumps(result["summary"], ensure_ascii=False))


if __name__ == "__main__":
    main()
