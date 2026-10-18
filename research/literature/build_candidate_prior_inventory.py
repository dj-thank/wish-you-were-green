#!/usr/bin/env python3
"""Join every census colour candidate to original Swan/Kilic catalogue rows.

Gaia IDs stay strings. Catalogue masks and flux-contamination estimates are
inventory metadata, never replacements for actual exposure masks or proofs
that contaminating light is absent. Alternative atmosphere fits are retained.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import csv
import gzip
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SOURCES = HERE / "sources"
OUT = HERE / "outputs"
CENSUS = ROOT / "research" / "outlier_audit" / "object_audit.csv"
SELECTED = SOURCES / "candidate27_prior_rows.json"
K26 = "https://arxiv.org/html/2606.25377v2"
K25 = "https://arxiv.org/abs/2412.04611"
S26 = "https://arxiv.org/html/2609.04314v1"
B19 = "https://arxiv.org/html/1910.06168v1"


def read_csv(path):
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", newline="") as handle:
        return list(csv.DictReader(handle))


def number(value):
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def write_csv(path, rows):
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def select_original_rows(candidates):
    ids = {r["source_id"] for r in candidates}
    result = {sid: {"swan_catalogue": [], "swan_external": [], "swan_exposures": [], "kilic2026": [], "kilic2025": []} for sid in sorted(ids)}
    by_name = {}
    for row in read_csv(SOURCES / "swan_catalogue.csv.gz"):
        sid = row["designation"].split()[-1]
        if sid in result:
            result[sid]["swan_catalogue"].append(row)
            by_name[row["WDJname"]] = sid
    for kind in ("external", "exposures"):
        for row in read_csv(SOURCES / f"swan_{kind}.csv.gz"):
            if row["WDJname"] in by_name:
                result[by_name[row["WDJname"]]][f"swan_{kind}"].append(row)
    for year, filename in ((2026, "kilic2026_table1.txt"), (2025, "kilic2025_Table2_ALL.txt")):
        for ordinal, line in enumerate((SOURCES / filename).read_text().splitlines(), 1):
            tokens = line.split()
            if len(tokens) > 1 and tokens[1] in result:
                result[tokens[1]][f"kilic{year}"].append({"original_line_1based": ordinal, "line": line})
    selected = {
        "census_sha256": hashlib.sha256(CENSUS.read_bytes()).hexdigest(),
        "selection": "review_status == multiple_instrument_colour_candidate; 2026-10-18 census",
        "sources_manifest": "atmosphere_sources_manifest.json",
        "source_ids": sorted(ids), "candidates": result,
    }
    SELECTED.write_text(json.dumps(selected, indent=2) + "\n")
    return selected


def k26_parsed(record):
    token = record["line"].split()
    if len(token) != 13:
        raise ValueError("Kilic 2026 table layout changed")
    return dict(name=token[0], source_id=token[1], spectral_type=token[2], composition=token[3],
                teff=float(token[4]), teff_error=float(token[5]), logg=float(token[6]), logg_error=float(token[7]),
                mass=float(token[8]), mass_error=float(token[9]))


def k25_parsed(record):
    token = record["line"].split()
    if len(token) != 12:
        raise ValueError("Kilic 2025 table layout changed")
    return dict(name=token[0], source_id=token[1], spectral_type=token[2], composition=token[3] + ";" + token[4],
                teff=float(token[5]), teff_error=float(token[6]), mass=float(token[7]), mass_error=float(token[8]),
                logg=float(token[9]), logg_error=float(token[10]))


def main():
    candidates = [r for r in read_csv(CENSUS) if r["review_status"] == "multiple_instrument_colour_candidate"]
    if (SOURCES / "swan_catalogue.csv.gz").exists():
        selected = select_original_rows(candidates)
    else:
        selected = json.loads(SELECTED.read_text())
        if {r["source_id"] for r in candidates} != set(selected["source_ids"]):
            raise RuntimeError("Candidate set changed; fetch original catalogues to rebuild selected rows")
    pewdd = {r["entity_id"]: r for r in read_csv(OUT / "pewdd_object_crossmatch.csv")}
    night_results_path = OUT / "desi_additional_nights_comparison.json"
    night_results = json.loads(night_results_path.read_text())["epochs"] if night_results_path.exists() else []
    rows, exposure_rows = [], []
    for c in candidates:
        sid = c["source_id"]
        data = selected["candidates"][sid]
        cat = data["swan_catalogue"][0] if len(data["swan_catalogue"]) == 1 else {}
        ext = data["swan_external"][0] if len(data["swan_external"]) == 1 else {}
        k26 = [k26_parsed(r) for r in data["kilic2026"]]
        k25 = [k25_parsed(r) for r in data["kilic2025"]]
        if len(k26) > 1 or len(k25) > 1:
            raise RuntimeError(f"Multiple alternative models for {sid}; update flat-table formatting explicitly")
        model = k26[0] if k26 else {}
        notes, actions = [], []
        if c["has_positional_identity"] == "True":
            notes.append("At least one record was joined by a provisional positional identity.")
            actions.append("Confirm the Gaia association using epoch-propagated coordinates and original spectrum headers.")
        if int(c["calibrated_records"]) == 0:
            notes.append("No photometrically recalibrated spectrum in this entity; colour is preliminary.")
            actions.append("Obtain independent quality-controlled photometry before a calibrated colour claim.")
        if float(c["min_distance"]) <= 0.01:
            notes.append("At least one eligible record lies at or within |Duv|=0.01; the strong-outlier threshold is not passed by every record.")
        if "DZ" in model.get("spectral_type", ""):
            notes.append("Kilic2026 fits Ca with other metal ratios fixed to CI chondrites; Na abundance is not independently measured.")
            actions.append("Fit Na/Ca/Mg separately with coherent calibration nuisance terms; test held-out bands and independent-instrument spectra.")
        if "DQ" in model.get("spectral_type", ""):
            actions.append("Measure C2 band positions and depths; compare pressure-shift and magnetic alternatives using the original spectral resolution.")
        if model.get("mass", 1) < 0.35:
            notes.append("Single-star fit has M<0.35 solar masses; Kilic2026 warns that low-mass DQ parameters can reflect an unresolved companion.")
            actions.append("Test single-atmosphere and unresolved two-component absolute SED models before interpreting mass or carbon abundance.")
        confidence = number(cat.get("specType_confidence"))
        if confidence is not None and confidence < 0.8:
            notes.append(f"Swan classification confidence is {confidence:.3f}; inspect classification log and higher-S/N spectra.")
        if "H" in model.get("spectral_type", "") and model.get("spectral_type", "").startswith("DQ"):
            notes.append("Kilic2026 labels this star DQH; Swan gives DQ. Magnetism is prior classification, not discovered from colour here.")
        if sid in {"761677269868775040", "1182083542272959232"}:
            notes.append("The separate Gaia field audit reports a bright neighbour about 9--10 arcsec away; tiny Gaussian-model contamination is not an empirical PSF-wing upper limit.")
            actions.append("Inspect survey images and realistic PSF wings at the photometry/spectrum epochs.")
        if sid == "1245262790370992256":
            notes.append("Absent from the searched Swan/Kilic DESI tables; Gaia variability is under separate external audit, not a variability discovery here.")
            actions.append("Resolve the SDSS full designation and inspect public variability classification and time series.")
        if sid == "1542337839923130624":
            notes.append("PSO J186.4406+47.1036 already has a Blouin&Dufour2019 Table2 fit: Teff6294+/-67 K, logg7.924+/-0.059, M0.528+/-0.034, logC/He=-5.33, DQ; cited by name, Gaia join still provisional.")
        if sid == "3713218786120541824":
            notes.append("WD1338+027 is DQpec in Blouin&Dufour2019 Table2 (Teff5785+/-20 K, logg8.098+/-0.013, logC/He=-6.00), but DQ in Kilic2026; compare definitions and band shifts before changing classification.")
        if sid == "3638333660492606976":
            notes.append("Kilic2025->2026 changes Teff4262->3648 K, mass0.445->0.268, logCa/He -9.94->-11.87. This is model dependence, not temporal evolution.")
        valid_exps = []
        for exp in data["swan_exposures"]:
            arm_valid = [number(exp.get(f"fractionMasked_{arm}")) is not None and number(exp.get(f"fractionMasked_{arm}")) < 1 for arm in "BRZ"]
            all_arms = all(arm_valid)
            if all_arms:
                valid_exps.append(exp)
            camera = int(exp["FIBER"]) // 500
            exp8 = f"{int(exp['EXPOSURE']):08d}"
            base = f"https://data.desi.lbl.gov/public/dr1/spectro/redux/iron/exposures/{exp['NIGHT']}/{exp8}"
            exposure_rows.append({"source_id": sid, "WDJname": exp["WDJname"], "NIGHT": exp["NIGHT"], "EXPOSURE": exp["EXPOSURE"], "FIBER": exp["FIBER"], "TARGETID": exp["TARGETID"], "MJD": exp["MJD"], "some_valid_pixels_in_each_arm": all_arms,
                                  **{f"fractionMasked_{arm}": exp[f"fractionMasked_{arm}"] for arm in "BRZ"},
                                  **{f"cframe_{arm}_url": f"{base}/cframe-{arm}{camera}-{exp8}.fits.gz" for arm in "brz"}})
        n_exps = len(data["swan_exposures"])
        if cat and n_exps != int(cat["nExposures"]):
            raise RuntimeError("Swan exposure-count mismatch")
        if n_exps and len(valid_exps) < n_exps:
            notes.append(f"Only {len(valid_exps)}/{n_exps} listed exposures have any valid pixels in all three arms; this still does not ensure full band coverage.")
        if len({e["NIGHT"] for e in valid_exps}) > 1:
            actions.append("Retrieve the listed independent-night cframes, keeping invalid masks and camera-seam sensitivity.")
        if sid == "3711047662972690688":
            notes.append("Second night was fetched here: broad C2 features recur, but every Z-arm pixel is invalid, so full independently calibrated colour remains unavailable.")
        for epoch in [r for r in night_results if r["source_id"] == sid]:
            colour = epoch["arm_join_sensitivity"][0]["panstarrs"]
            if colour:
                notes.append(f"Official DESI NIGHT {epoch['night']} extracted here: shared-PS1 calibrated Duv={colour['duv']:+.6f}, pixel-only uv error={colour['uv_stat_error_max']:.5f}, negative visible pixels={100*colour['visible_negative_fraction']:.2f}%. Shared calibration errors remain.")
                if abs(colour["duv"]) <= .01:
                    notes.append("This night does not pass the strict0.01 point-estimate threshold; do not claim all nights reproduce a strong colour outlier.")
        prior = pewdd[c["entity_id"]]
        row = {"entity_id": c["entity_id"], "source_id": sid, "names": c["names"], "prior_WDJname": cat.get("WDJname", ""),
               "input_spectral_types": c["spectral_types"], "median_duv": c["median_duv"], "min_distance": c["min_distance"], "max_distance": c["max_distance"], "representative_hex": c["representative_hex"],
               "calibrated_records": c["calibrated_records"], "has_positional_identity": c["has_positional_identity"],
               "pewdd_exact_id_rows": prior["pewdd_rows"], "swan_exact_id_rows": len(data["swan_catalogue"]), "swan_type": cat.get("specType", ""), "swan_type_confidence": cat.get("specType_confidence", ""),
               "swan_n_exposures": n_exps, "swan_n_nights": len({e["NIGHT"] for e in data["swan_exposures"]}), "swan_exposures_with_some_valid_pixels_all_arms": len(valid_exps), "swan_nights_with_some_valid_pixels_all_arms": len({e["NIGHT"] for e in valid_exps}),
               "swan_fractionMasked_Z": cat.get("fractionMasked_Z", ""), "swan_neighbour_to_target_flux_DESI": cat.get("fluxContamination_DESI", ""),
               **{f"swan_neighbour_to_target_flux_{survey}": ext.get(f"fluxContamination_{survey}", "") for survey in ("PanSTARRS", "SDSS", "Gaia_G", "Gaia_BPRP")},
               "kilic2026_exact_id_rows": len(k26), **{f"kilic2026_{field}": model.get(field, "") for field in ("spectral_type", "composition", "teff", "teff_error", "logg", "logg_error", "mass", "mass_error")},
               "kilic2025_model": json.dumps(k25[0]) if k25 else "", "scientific_notes": " ".join(notes), "next_checks": " ".join(actions),
               "prior_urls": " | ".join(([S26] if cat else []) + ([K26] if k26 else []) + ([K25] if k25 else []) + ([B19] if sid in {"1542337839923130624", "3713218786120541824"} else []))}
        rows.append(row)
    OUT.mkdir(exist_ok=True)
    write_csv(OUT / "candidate27_prior_inventory.csv", rows)
    write_csv(OUT / "candidate27_desi_exposure_inventory.csv", exposure_rows)
    summary = {"candidate_count": len(rows), "census_sha256": hashlib.sha256(CENSUS.read_bytes()).hexdigest(), "swan_exact_id_matches": sum(bool(r["swan_exact_id_rows"]) for r in rows), "kilic2026_exact_id_matches": sum(bool(r["kilic2026_exact_id_rows"]) for r in rows), "pewdd_exact_id_matches": sum(int(r["pewdd_exact_id_rows"]) > 0 for r in rows), "registered_exposure_rows": len(exposure_rows), "exposures_with_some_valid_pixels_all_arms": sum(r["some_valid_pixels_in_each_arm"] for r in exposure_rows), "candidates_with_multiple_registered_nights": sum(r["swan_n_nights"] > 1 for r in rows), "candidates_with_multiple_nights_having_all_arms": sum(r["swan_nights_with_some_valid_pixels_all_arms"] > 1 for r in rows), "source_ids_absent_from_swan": [r["source_id"] for r in rows if not r["swan_exact_id_rows"]], "cautions": ["Absence from any one catalogue is not evidence of novelty.", "Swan contamination is a neighbour/target flux-ratio model estimate, not a measured upper bound.", "Swan H/He-only fitted physical parameters have deliberately not been substituted for appropriate DQ/DZ atmosphere fits.", "All 27 entities remain candidates pending the joint record-level, field and calibration audit.", "This inventory is a per-object literature and observation audit; it does not claim all model-fit figures were visually re-inspected for all 27 stars."]}
    (OUT / "candidate27_prior_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
