#!/usr/bin/env python3
"""Check Swan PS1 values/uncertainties against direct MAST DR1 and DR2 rows.

The cached queries retain every returned object. Value matching below is a
numerical-definition comparison, not an independent astrometric identity
proof. IDs are compared as strings; no magnitude/flux columns are mixed.
"""
import csv
import hashlib
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SOURCES, OUT = HERE / "sources", HERE / "outputs"


def main():
    files = ("ps1_mast_dr1_headline_checks.json", "ps1_mast_headline_checks.json")
    checks = [{r["source_id"]: r for r in json.loads((SOURCES / f).read_text())} for f in files]
    prior = json.loads((SOURCES / "candidate27_prior_rows.json").read_text())["candidates"]
    rows = []
    with (ROOT / "results" / "headline_candidates.csv").open() as handle:
        for headline in csv.DictReader(handle):
            sid = headline["source_id"]
            swan = prior[sid]["swan_external"][0]
            selected = []
            for check in checks:
                candidates = [r for r in check[sid]["rows"] if all(float(r[f"{b}MeanPSFMag"]) > 0 and abs(float(r[f"{b}MeanPSFMag"]) - float(swan[f"Pan-STARRS.{b}"])) < 1e-7 for b in "gri")]
                if len(candidates) != 1:
                    raise RuntimeError("Expected one numerical photometry match in each saved MAST response")
                selected.append(candidates[0])
            dr1, dr2 = selected
            if dr1["objID"] != dr2["objID"]:
                raise RuntimeError("PS1 object differs between releases")
            for b in "gri":
                s_mag, s_err = float(swan[f"Pan-STARRS.{b}"]), float(swan[f"Pan-STARRS.{b}_error"])
                d1_mag, d2_mag = float(dr1[f"{b}MeanPSFMag"]), float(dr2[f"{b}MeanPSFMag"])
                d1_err, d2_err = float(dr1[f"{b}MeanPSFMagErr"]), float(dr2[f"{b}MeanPSFMagErr"])
                predicted = math.hypot(round(d1_err, 4), .01)
                rows.append({"source_id": sid, "candidate": headline["candidate"], "band": b, "ps1_objID": dr1["objID"], "swan_mag": s_mag, "mast_dr1_mean_psf_mag": d1_mag, "mast_dr2_mean_psf_mag": d2_mag, "mwdd_anchor_mag": float(headline[f"anchor_{b}_mag"]), "swan_error_mag": s_err, "mast_dr1_native_error_mag": d1_err, "mast_dr2_native_error_mag": d2_err, "mwdd_anchor_error_mag": float(headline[f"anchor_{b}_error"]), "prediction_rounded_dr1_error_plus_0_01mag_quadrature": predicted, "swan_minus_predicted_error_mag": s_err - predicted, "dr1_query_url": checks[0][sid]["url"], "dr2_query_url": checks[1][sid]["url"]})
    with (OUT / "ps1_swan_definition_checks.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    summary = {"date_utc": "2026-10-18", "objects": len({r["source_id"] for r in rows}), "bands_checked": len(rows), "maximum_swan_mast_mag_difference": max(max(abs(r["swan_mag"]-r[key]) for key in ("mast_dr1_mean_psf_mag", "mast_dr2_mean_psf_mag")) for r in rows), "maximum_swan_rounded_dr1_plus_floor_error_difference": max(abs(r["swan_minus_predicted_error_mag"]) for r in rows), "maximum_mwdd_dr2_native_error_difference": max(abs(r["mwdd_anchor_error_mag"]-r["mast_dr2_native_error_mag"]) for r in rows), "native_response_files": [{"path": str((SOURCES / f).relative_to(HERE)), "sha256": hashlib.sha256((SOURCES / f).read_bytes()).hexdigest()} for f in files], "interpretation": ["All checked central values are observed PS1 mean-PSF magnitudes; the DR1 and DR2 central magnitudes agree exactly in these examples.", "Swan uncertainties match DR1 native errors rounded to four decimal places, plus0.01 mag added in quadrature; do not add the same floor a second time.", "Existing MWDD uncertainty fields match DR2 native uncertainties and have not had that Swan floor added.", "The Swan paper describes the extra uncertainty as1%; the retrieved numerical table implements0.01 mag in the checked rows, not exactly0.01 fractional flux.", "These are checks on four already identified examples; they do not establish the astrometric identity or quality of every new PS1 match.", "Swan Section3/Table11 defines units and selection. Reddening is a model parameter; do not deredden these observed anchors unless the spectrum is treated consistently."], "sources": ["https://arxiv.org/html/2609.04314v1#S3", "https://arxiv.org/html/2609.04314v1#A5", "https://outerspace.stsci.edu/spaces/PANSTARRS/pages/298812303/PS1+Filter+properties", "https://outerspace.stsci.edu/spaces/PANSTARRS/pages/298812205/PS1+FAQ+-+Frequently+asked+questions"]}
    (OUT / "ps1_swan_definition_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
