#!/usr/bin/env python3
"""Audit every census entity against the pinned PEWDD snapshot.

IDs are strings throughout.  Numeric-ID associations are accepted only for
PEWDD Gaia DR3/EDR3 designations.  Unmatched positions are reported as hints,
not silently accepted crossmatches because the PEWDD coordinate epoch is not
uniformly specified.  No observed colour or upstream abundance is changed.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import csv
import gzip
import hashlib
import io
import json
import math
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PEWDD = HERE / "sources" / "pewdd_023dba3.csv.gz"
RANKING = ROOT / "research" / "outlier_audit" / "object_audit.csv"
HEADLINES = ROOT / "results" / "headline_candidates.csv"


def finite(value: str | None) -> float | None:
    try:
        number = float(value or "")
        return number if math.isfinite(number) else None
    except (TypeError, ValueError):
        return None


def gaia_id(designation: str) -> str | None:
    match = re.fullmatch(r"\s*Gaia\s+(?:DR3|EDR3)\s+(\d{10,20})\s*", designation or "")
    return match.group(1) if match else None


def abundance_state(row: dict, element: str) -> str:
    if finite(row.get(f"log({element}/H(e))")) is None:
        return "not_reported"
    error = finite(row.get(f"log({element}/H(e))e"))
    if error == -1:
        return "upper_limit"
    if error is None or error < 0:
        return "reported_value_without_valid_error"
    return "reported_detection"


def separation_arcsec(ra1: float, dec1: float, ra2: float, dec2: float) -> float:
    dra, ddec = math.radians(ra2 - ra1), math.radians(dec2 - dec1)
    hav = math.sin(ddec / 2) ** 2 + math.cos(math.radians(dec1)) * math.cos(math.radians(dec2)) * math.sin(dra / 2) ** 2
    return math.degrees(2 * math.asin(min(1.0, math.sqrt(max(0.0, hav))))) * 3600


def name_coordinate_check(row: dict) -> dict:
    """Flag gross inconsistencies only; never infer a corrected identity.

    Full J-coordinate designations are used; shortened names and B1950 WD
    names are deliberately excluded. Even a flagged row needs source review.
    """
    match = re.search(r"J(\d{2})(\d{2})(\d{2}(?:\.\d+)?)([+−-])(\d{2})(\d{2})(\d{2}(?:\.\d+)?)", row["Star"])
    ra, dec = finite(row.get("RA")), finite(row.get("Dec"))
    if not match or ra is None or dec is None:
        return {"name_coordinate_separation_arcsec": "", "identity_review_flag": False}
    hh, mm, ss, sign, dd, dm, ds = match.groups()
    encoded_ra = (int(hh) + int(mm) / 60 + float(ss) / 3600) * 15
    encoded_dec = (int(dd) + int(dm) / 60 + float(ds) / 3600) * (1 if sign == "+" else -1)
    sep = separation_arcsec(ra, dec, encoded_ra, encoded_dec)
    return {"name_coordinate_separation_arcsec": sep, "identity_review_flag": sep > 600}


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    output = HERE / "outputs"
    output.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((HERE / "sources" / "pewdd_manifest.json").read_text())
    raw = gzip.decompress(PEWDD.read_bytes())
    if hashlib.sha256(raw).hexdigest() != manifest["uncompressed_sha256"]:
        raise RuntimeError("PEWDD snapshot hash mismatch")
    pewdd = list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))))
    with RANKING.open() as handle:
        ranking = list(csv.DictReader(handle))
    with HEADLINES.open() as handle:
        headlines = list(csv.DictReader(handle))
    index = defaultdict(list)
    positions = []
    identity_audit = []
    for ordinal, row in enumerate(pewdd, start=1):
        check = name_coordinate_check(row)
        if check["identity_review_flag"]:
            identity_audit.append({"pewdd_row_1based": ordinal, "star": row["Star"], "gaia_designation": row["Gaia_designation"], "paper": row["Paper"], "ra_deg": row["RA"], "dec_deg": row["Dec"], **check, "action": "quarantine identity for original-paper review; no automatic correction"})
        sid = gaia_id(row.get("Gaia_designation", ""))
        if sid:
            index[sid].append((ordinal, row))
        ra, dec = finite(row.get("RA")), finite(row.get("Dec"))
        if ra is not None and dec is not None and 0 <= ra < 360 and -90 <= dec <= 90:
            positions.append((ordinal, row, ra, dec))
    summary, measurements = [], []
    for item in ranking:
        sid = item["source_id"]
        matched = index.get(sid, [])
        na, ca, mg = [sum(abundance_state(r, element) == "reported_detection" for _, r in matched) for element in ("Na", "Ca", "Mg")]
        nearest_sep, nearest_name = "", ""
        ra, dec = finite(item.get("ra_deg")), finite(item.get("dec_deg"))
        if not matched and ra is not None and dec is not None and positions:
            nearest_sep, nearest = min((separation_arcsec(ra, dec, a, d), p) for p, (_, _, a, d) in enumerate(positions))
            nearest_name = positions[nearest][1]["Star"]
        summary.append({
            "entity_id": item["entity_id"], "names": item["names"], "source_id": sid,
            "spectral_types": item["spectral_types"], "median_duv": item["median_duv"],
            "min_distance": item["min_distance"], "max_distance": item["max_distance"], "representative_hex": item["representative_hex"],
            "ground_records": item["ground_records"], "calibrated_records": item["calibrated_records"],
            "review_status": item["review_status"], "has_positional_identity": item["has_positional_identity"],
            "association": "exact_numeric_id_to_pewdd_dr3" if matched else "no_exact_id_match_in_snapshot",
            "pewdd_rows": len(matched),
            "pewdd_identity_review_rows": sum(name_coordinate_check(r)["identity_review_flag"] for _, r in matched),
            "pewdd_papers": " | ".join(sorted({r["Paper"] for _, r in matched})),
            "na_detection_rows": na, "ca_detection_rows": ca, "mg_detection_rows": mg,
            "na_ca_same_row_detections": sum(all(abundance_state(r, e) == "reported_detection" for e in ("Na", "Ca")) for _, r in matched),
            "na_mg_same_row_detections": sum(all(abundance_state(r, e) == "reported_detection" for e in ("Na", "Mg")) for _, r in matched),
            "nearest_unmatched_pewdd_star": nearest_name,
            "nearest_unmatched_sep_arcsec": nearest_sep,
            "positional_hint_under_30arcsec": bool(nearest_sep != "" and nearest_sep < 30),
        })
        for ordinal, row in matched:
            record = {
                "entity_id": item["entity_id"], "names": item["names"], "source_id": sid, "pewdd_row_1based": ordinal,
                "pewdd_identifier": row["Identifier"], "pewdd_star": row["Star"],
                "paper": row["Paper"], "origin": row["origin"], "comment": row["comment"],
                "atmosphere": row["atmosphere"], "T_eff": row["T_eff"], "T_eff_err": row["T_eff_err"],
                "logg": row["logg"], "logg_err": row["logg_err"],
                "median_duv": item["median_duv"], "min_distance": item["min_distance"], "max_distance": item["max_distance"],
                **name_coordinate_check(row),
            }
            for element in ("H", "Na", "Ca", "Mg", "Fe", "Li", "K"):
                record[f"log_{element}_over_H_or_He"] = row.get(f"log({element}/H(e))", "")
                record[f"log_{element}_error"] = row.get(f"log({element}/H(e))e", "")
                record[f"{element}_state"] = abundance_state(row, element)
            for first, second in (("Na", "Ca"), ("Na", "Mg"), ("Mg", "Ca")):
                valid = all(abundance_state(row, element) == "reported_detection" for element in (first, second))
                record[f"log_{first}_over_{second}_photospheric"] = finite(row[f"log({first}/H(e))"]) - finite(row[f"log({second}/H(e))"]) if valid else ""
            measurements.append(record)
    write_csv(output / "pewdd_object_crossmatch.csv", summary)
    if measurements:
        write_csv(output / "pewdd_matched_measurements.csv", measurements)
    if identity_audit:
        write_csv(output / "pewdd_identity_review.csv", identity_audit)
    by_id = defaultdict(list)
    for row in summary:
        by_id[row["source_id"]].append(row)
    headline_audit = []
    for candidate in headlines:
        matched = index.get(candidate["source_id"], [])
        headline_audit.append({
            "candidate": candidate["candidate"], "source_id": candidate["source_id"],
            "exact_id_rows": len(matched),
            "papers": sorted({r["Paper"] for _, r in matched}),
            "nearest_hints": [{"star": r["nearest_unmatched_pewdd_star"], "separation_arcsec": r["nearest_unmatched_sep_arcsec"]} for r in by_id[candidate["source_id"]]],
            "interpretation": "Existing rows need their original-paper measurement assumptions checked." if matched else "No entry in this March 2026 snapshot; this is not evidence that no prior abundance analysis exists.",
        })
    summary_json = {
        "source": manifest,
        "census_path": str(RANKING.relative_to(ROOT)),
        "ranking_sha256": hashlib.sha256(RANKING.read_bytes()).hexdigest(),
        "ranking_rows": len(ranking), "ranking_unique_nonempty_ids": len({r["source_id"] for r in ranking if r["source_id"]}),
        "pewdd_rows": len(pewdd), "pewdd_unique_dr3_ids": len(index),
        "pewdd_unparsed_designation_rows": sum(gaia_id(r.get("Gaia_designation", "")) is None for r in pewdd),
        "matched_ranking_rows": sum(r["pewdd_rows"] > 0 for r in summary),
        "matched_unique_ids": len({r["source_id"] for r in summary if r["pewdd_rows"]}),
        "matched_measurement_rows_with_ranking_aliases": len(measurements),
        "unique_matched_pewdd_rows": len({r["pewdd_row_1based"] for r in measurements}),
        "unique_ids_with_na_ca_same_paper_detections": len({r["source_id"] for r in summary if r["na_ca_same_row_detections"]}),
        "source_rows_with_gross_name_coordinate_disagreement": len(identity_audit),
        "candidate27_count": sum(r["review_status"] == "multiple_instrument_colour_candidate" for r in summary),
        "candidate27_with_exact_pewdd_id_match": sum(r["review_status"] == "multiple_instrument_colour_candidate" and r["pewdd_rows"] > 0 for r in summary),
        "unmatched_rows_with_positional_hint_under_30arcsec": sum(r["positional_hint_under_30arcsec"] for r in summary),
        "headline_candidates": headline_audit,
        "cautions": [
            "The source ranking falls back from Gaia EDR3 to DR2 IDs for some objects; confirm release lineage before treating all exact numerical associations as final.",
            "Coordinate-only hints have not been accepted as associations because catalogues can use different epochs and high proper motion.",
            "Rows whose full J-coordinate name differs from the tabulated position by over 600 arcsec are flagged for identity review. This is not a corrected identification; such associations must not enter chemical inference until resolved.",
            "Individual papers and alternate models remain separate rows. Do not treat them as independent stars or average their abundances without an error model.",
            "Reported detections follow the PEWDD uncertainty convention; fixed CI-chondritic abundance ratios in an original paper must still be audited individually.",
            "The original exploration and heterogeneous abundance coverage do not support population prevalence or an uncorrected global significance.",
            "This script supplies a follow-up measurement inventory, not a fitted chemical-origin or causal-colour result."
        ],
    }
    (output / "pewdd_summary.json").write_text(json.dumps(summary_json, indent=2) + "\n")
    print(json.dumps({k: v for k, v in summary_json.items() if k not in ("source", "cautions")}, indent=2))


if __name__ == "__main__":
    main()
