#!/usr/bin/env python3
"""Offline verification of selected exports and the two official Gaia queries.

The check reproduces numerical descriptions; it cannot verify a human visual
judgment, establish a spectral-line identification, or certify classification.
"""
from __future__ import annotations

import csv
from datetime import datetime
import gzip
import hashlib
import io
import json
from pathlib import Path
import sys
from urllib.parse import parse_qs, urlparse

import numpy as np

INITIAL_ROWS = {1250, 3004, 2714, 2930, 8376}
INITIAL_GAIA = {"1060188315963488640", "3688869246424920448",
    "2629980411471669632", "2802900781266410112", "4573582236809330432",
    "2163612727665972096", "2002597083798483200", "5078976609103251456",
    "1245262790370992256"}
ADDITIONAL = {8303: (31,8,"1951666884868218112"),
    8307: (32,11,"2096274276193099136"), 5948: (33,11,"2208124536065383424"),
    8370: (81,16,"4565045873343899136"), 8390: (89,13,"5589261737965864832")}


def verify(root):
    root = Path(root).resolve()
    sys.path.insert(0, str(root))
    import colour_pipeline as colour

    base = root / "research/outlier_followup"
    initial = base / "targeted_diagnostics"
    additional = base / "gaia_additional_features"
    files = {}

    def sha(path):
        path = Path(path)
        value = hashlib.sha256(path.read_bytes()).hexdigest()
        files[str(path.relative_to(root))] = value
        return value

    def read_json(path):
        path = Path(path)
        if not path.exists() and path.with_suffix(path.suffix + ".gz").exists():
            path = path.with_suffix(path.suffix + ".gz")
        sha(path)
        if path.suffix == ".gz":
            with gzip.open(path, "rt") as stream:
                return json.load(stream)
        return json.loads(path.read_text())

    def near(actual, expected, *, atol=2e-10):
        assert np.isclose(float(actual), float(expected), rtol=2e-10, atol=atol), (actual, expected)

    def timestamp(value):
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        assert parsed.tzinfo is not None, "Acquisition UTC must be timezone-aware"
        return parsed

    table = root / "research/precision/flux_units/corrected_record_screen.csv.gz"
    current_hash = sha(table)
    with gzip.open(table, "rt") as stream:
        current = {int(r["row_index"]): r for r in csv.DictReader(stream)}
    frozen = []
    for origin in ["mwdd", "sdss"]:
        frozen.extend(read_json(root / f"results/screen_input_{origin}.json"))

    def validated_record(number, path):
        row = current[number]
        original = frozen[number]
        assert row["status"] == "ok" and row["usable_screen"] == "True"
        assert row["flux_units_validated"] == "True" and row["flux_input_convention"] == "flambda"
        assert row["sha256"] == original["sha256"] == sha(path)
        assert row["source_url"] == original["source_url"]
        lines = Path(path).read_text().splitlines()
        assert lines[0].startswith("wdid:")
        names = next(csv.reader([lines[1]]))
        a = np.loadtxt(io.StringIO("\n".join(lines[2:])), delimiter=",", ndmin=2)
        values = {key.strip(): a[:,i] for i,key in enumerate(names)}
        assert "wavelength" in values and "flux" in values
        order = np.argsort(values["wavelength"])
        values = {key: val[order] for key,val in values.items()}
        return row, values

    retrieval = read_json(initial / "retrieval.json")
    first = read_json(initial / "diagnostics.json")
    assert retrieval["input_table_sha256"] == first["input_table_sha256"] == current_hash
    assert first["code_sha256"] == sha(base / "targeted_diagnostics.py")
    assert len(retrieval["requests"]) == 6 and all(r["result"] == "ok" for r in retrieval["requests"])
    originals = {r["saved_path"]: r for r in retrieval["requests"]}
    assert {int(x["row_index"]) for x in first["records"]} == INITIAL_ROWS
    repeated = []
    for rec in first["records"]:
        number = int(rec["row_index"])
        path = initial / f"raw/row_{number}.txt"
        provenance = read_json(path.with_name(path.name + ".provenance.json"))
        row, values = validated_record(number, path)
        assert provenance == originals[str(path.relative_to(root))]
        assert provenance["result"] == "ok" and provenance["status"] == 200
        assert timestamp(provenance["retrieved_utc"]) >= timestamp(provenance["query_started_utc"])
        assert provenance["bytes"] == path.stat().st_size
        assert provenance["sha256"] == provenance["expected_frozen_sha256"] == rec["raw_sha256"] == row["sha256"]
        assert provenance["request_url"] == rec["source_url"] == row["source_url"]
        assert rec["source_id"] == row["source_id"] and rec["kind"] == row["kind"]
        assert rec["flux_convention"] == "flambda" and rec["raw_spectrum_not_recalibrated_here"] is True
        assert rec["current_calibrated"] == row["calibrated"]
        near(rec["current_stored_Duv"], row["duv"])
        w, f = values["wavelength"], values["flux"]
        visible = (w >= 3600) & (w <= 8300) & np.isfinite(w) & np.isfinite(f)
        assert len(w) == rec["samples"] and int(visible.sum()) == rec["visible_samples"]
        assert int((f[visible] < 0).sum()) == rec["visible_negative_samples"]
        near(np.diff(w[visible]).max(), rec["largest_visible_step_A"])
        norm = float(np.median(f[(w >= 5200) & (w <= 5500) & np.isfinite(f)]))
        near(norm, rec["normalization_median_5200_5500"])
        for window in rec["predeclared_feature_windows"]:
            mask = visible & (np.abs(w-window["window_center_A"]) <= window["halfwidth_A"])
            ids = np.flatnonzero(mask)
            assert int(mask.sum()) == window["finite_samples"]
            j, k = ids[np.argmax(f[mask])], ids[np.argmin(f[mask])]
            near(w[j], window["maximum_A"]); near(w[k], window["minimum_A"])
            near(f[j]/norm, window["maximum_flux_over_anchor"])
            near(f[k]/norm, window["minimum_flux_over_anchor"])
        if rec["kind"] == "DESI":
            sigma = values["sigma"]
            positive = visible & np.isfinite(sigma) & (sigma > 0)
            assert int((sigma[visible] <= 0).sum()) == rec["visible_nonpositive_error_samples"]
            near(np.median(f[positive]/sigma[positive]), rec["visible_median_pixel_snr"])
            labels, counts = np.unique(values["flag"][visible], return_counts=True)
            assert {str(int(v)): int(c) for v,c in zip(labels,counts)} == rec["export_flag_values_counts"]
            iv = np.divide(1., sigma*sigma, out=np.zeros_like(sigma), where=np.isfinite(sigma)&(sigma>0))
            a = colour.integrate_colour(w, f, iv, mask_sky=False)
            b = colour.integrate_colour(w, f, iv, mask_sky=True)
            keep = np.abs(w-5577.34) > 8
            c = colour.integrate_colour(w[keep], f[keep], iv[keep], mask_sky=False)
            expected = rec["raw_mask_sensitivity"]
            near(a["duv"], expected["all_samples_duv"])
            near(b["duv"], expected["standard_five_sky_windows_duv"])
            near(c["duv"], expected["only_5577_34_pm8A_removed_duv"])
            delta = float(np.hypot(a["u1960"]-c["u1960"], a["v1960"]-c["v1960"]))
            near(delta, expected["only_5577_window_delta_uv"])
            near(np.hypot(a["u1960"]-b["u1960"], a["v1960"]-b["v1960"]), expected["standard_windows_delta_uv"])
            native = visible & (np.abs(w-5577.34) <= 12)
            supplied = np.array([[p["wavelength_A"],p["flux"],p["sigma"]] for p in rec["native_window_samples"]])
            assert np.allclose(supplied, np.column_stack([w[native], f[native], sigma[native]]), rtol=2e-10, atol=2e-10)
            repeated.append({"row_index": number, "only_5577_window_delta_uv": delta})
        else:
            assert rec["kind"] == "Gaia_XP" and "sigma" not in values and "ivar" not in values

    # The old spike descriptions cannot silently become validated current F_lambda inputs.
    for number in [1248,3003,8322,8339,8372]:
        assert current[number]["status"] == "unit_unverified"
        assert current[number]["flux_units_validated"] != "True"

    def gaia_query(folder, expected_ids, *, old=False):
        raw = folder / "raw/gaia_feature_review.csv"
        if old:
            provenance = read_json(raw.with_name(raw.name + ".provenance.json"))
            assert provenance == originals[str(raw.relative_to(root))]
            adql = folder / "gaia_query.adql"
        else:
            provenance = read_json(folder / "query_provenance.json")
            adql = folder / "query.adql"
        assert provenance["result"] == "ok" and provenance.get("status", provenance.get("http_status")) == 200
        assert sha(raw) == provenance["sha256"] and raw.stat().st_size == provenance["bytes"]
        assert timestamp(provenance["retrieved_utc"]) >= timestamp(provenance["query_started_utc"])
        parsed = urlparse(provenance["request_url"])
        assert parsed.hostname == "gea.esac.esa.int" and parsed.path == "/tap-server/tap/sync"
        sha(adql)
        query = adql.read_text().strip()
        assert parse_qs(parsed.query)["QUERY"] == [query]
        assert "LEFT OUTER JOIN gaiadr3.vari_classifier_result" in query
        assert all(source in query for source in expected_ids)
        rows = list(csv.DictReader(raw.open()))
        assert len(rows) == len(expected_ids) and {r["source_id"] for r in rows} == expected_ids
        for row in rows:
            if row["best_class_score"]:
                assert 0 <= float(row["best_class_score"]) <= 1
        return rows

    first_gaia = gaia_query(initial, INITIAL_GAIA, old=True)
    assert first_gaia == first["gaia_official_rows"]
    new_gaia = gaia_query(additional, {x[2] for x in ADDITIONAL.values()})
    new = read_json(additional / "results.json")
    assert new["current_screen_sha256"] == current_hash
    assert new["code_sha256"] == sha(base / "additional_gaia_feature_review.py")
    assert new["query_response_sha256"] == sha(additional / "raw/gaia_feature_review.csv")
    assert {int(x["row_index"]) for x in new["objects"]} == set(ADDITIONAL)
    gaia_by_id = {r["source_id"]: r for r in new_gaia}
    index_path = base / "contact_sheet_index.csv"; sha(index_path)
    index = {(int(r["page"]),int(r["panel"])):r for r in csv.DictReader(index_path.open())}
    maximum_colour_error = 0.
    for rec in new["objects"]:
        number = int(rec["row_index"])
        page, panel, source = ADDITIONAL[number]
        assert (rec["page"],rec["panel"],rec["source_id"]) == (page,panel,source)
        assert rec["gaia_official"] == gaia_by_id[source]
        assert rec["independent_spectrum_in_current_panel"] is False
        ix = index[(page,panel)]
        assert ix["source_id"] == source and str(number) in ix["plotted_row_indices"].split("|")
        assert rec["contact_sheet_sha256"] == ix["contact_sheet_sha256"] == sha(base/ix["contact_sheet"])
        assert rec["unit_withheld_records"] == int(ix["unit_withheld_records"])
        row, values = validated_record(number, additional/rec["raw_copy"])
        assert rec["raw_sha256"] == row["sha256"] and rec["source_url"] == row["source_url"]
        assert row["kind"] == "Gaia_XP" and "sigma" not in values and "ivar" not in values
        assert rec["prior_exact_retrieval"]["status"] == "verified"
        assert rec["prior_exact_retrieval"]["sha256"] == row["sha256"]
        assert rec["prior_exact_retrieval"]["source_url"] == row["source_url"]
        timestamp(rec["prior_exact_retrieval"]["checked_utc"])
        w, f = values["wavelength"], values["flux"]
        assert rec["current_calibrated"] == (row["calibrated"] == "True")
        if row["calibrated"] == "True":
            f = f*10**(-.4*(float(row["cal_offset_mag"])+float(row["cal_tilt_mag_per_1000A"])*(w-6200)/1000))
        calculated = colour.integrate_colour(w,f,None,mask_sky=False)
        near(calculated["duv"],rec["current_Duv"]); near(rec["current_Duv"],row["duv"])
        maximum_colour_error = max(maximum_colour_error, abs(calculated["duv"]-rec["current_Duv"]))
        finite = np.isfinite(w)&np.isfinite(f)
        norm = np.median(f[finite&(w>=5200)&(w<=5500)]); assert norm > 0
        f = f/norm
        for window in rec["descriptive_windows"]:
            mask = finite & (np.abs(w-window["reference_A"]) <= window["halfwidth_A"])
            ids = np.flatnonzero(mask); j,k = ids[np.argmax(f[mask])],ids[np.argmin(f[mask])]
            assert int(mask.sum()) == window["samples"]
            near(w[j],window["maximum_A"]); near(w[k],window["minimum_A"])
            near(f[j],window["maximum_normalized_flux"]); near(f[k],window["minimum_normalized_flux"])
    assert all(r["phot_variable_flag"] == "VARIABLE" for r in new_gaia)
    assert sum(r["best_class_name"] == "CV" for r in new_gaia) == 3
    assert sum(r["best_class_name"] == "S" for r in new_gaia) == 1
    assert sum(r["best_class_name"] == "" for r in new_gaia) == 1
    with (additional / "catalogue_matches.csv").open() as stream:
        matches = list(csv.DictReader(stream))
    assert len(matches) == 5 and {r["source_id"] for r in matches} == set(gaia_by_id)
    for row in matches:
        for key in ["phot_variable_flag","best_class_name","best_class_score","ruwe","has_xp_continuous"]:
            assert row[key] == gaia_by_id[row["source_id"]][key]
    visual = read_json(additional / "visual_review.json")
    assert visual["actually_viewed"] is True and visual["object_rows_viewed"] == 5 and visual["panels_viewed"] == 15
    assert {int(r["row_index"]) for r in visual["observations"]} == set(ADDITIONAL)
    assert visual["figure_sha256"] == sha(additional / visual["figure"])

    for folder in [initial,additional]:
        for path in sorted(folder.rglob("*")):
            if path.is_file():
                sha(path)
    sha(Path(__file__))
    return {"summary": {"initial_export_spectra": 5, "initial_official_Gaia_rows": 9,
              "additional_XP_exports": 5, "additional_official_Gaia_rows": 5,
              "additional_previously_catalogued_variables": 5,
              "additional_classifier_counts": {"CV":3,"S":1,"no_entry":1},
              "withheld_historical_SDSS_spike_rows": 5,
              "offline_DESI_window_reintegration": repeated,
              "maximum_additional_XP_Duv_reproduction_difference": maximum_colour_error},
            "verified_file_sha256": dict(sorted(files.items()))}


if __name__ == "__main__":
    result = verify(Path(__file__).resolve().parents[2])
    print(json.dumps(result, indent=2))
