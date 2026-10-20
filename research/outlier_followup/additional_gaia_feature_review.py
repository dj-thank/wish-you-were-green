#!/usr/bin/env python3
"""Inspect five visually selected XP features and query official DR3 metadata.

This is a descriptive, selected-object follow-up, not a spectral-line detector.
It never edits the fixed contact sheets, catalogue selections or previous query.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
OUT = BASE / "gaia_additional_features"
RAW = OUT / "raw"
os.environ.setdefault("MPLCONFIGDIR", "/tmp/wish-green-additional-xp-mpl")
TARGETS = [
    (31, 8, "1951666884868218112", 8303),
    (32, 11, "2096274276193099136", 8307),
    (33, 11, "2208124536065383424", 5948),
    (81, 16, "4565045873343899136", 8370),
    (89, 13, "5589261737965864832", 8390),
]
QUERY = (
    "SELECT g.source_id,g.ra,g.dec,g.ref_epoch,g.pmra,g.pmdec,"
    "g.phot_g_mean_mag,g.bp_rp,g.ruwe,g.phot_variable_flag,g.has_xp_continuous,"
    "v.classifier_name,v.best_class_name,v.best_class_score "
    "FROM gaiadr3.gaia_source AS g LEFT OUTER JOIN gaiadr3.vari_classifier_result AS v "
    "ON g.source_id=v.source_id WHERE g.source_id IN ("
    + ",".join(t[2] for t in TARGETS) + ") ORDER BY g.source_id"
)


def utc():
    return datetime.now(timezone.utc).isoformat()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def dump(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def fetch():
    RAW.mkdir(parents=True, exist_ok=True)
    target = RAW / "gaia_feature_review.csv"
    if target.exists():
        raise FileExistsError("A query response already exists; preserve its acquisition provenance.")
    (OUT / "query.adql").write_text(QUERY + "\n")
    url = "https://gea.esac.esa.int/tap-server/tap/sync?" + urlencode(
        {"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "csv", "QUERY": QUERY}
    )
    provenance = {"request_url": url, "query_started_utc": utc(),
                  "code_sha256_at_acquisition": digest(Path(__file__).read_bytes())}
    try:
        req = Request(url, headers={"User-Agent": "wish-you-were-green research reproducibility"})
        with urlopen(req, timeout=45) as response:
            body = response.read()
            provenance.update({"http_status": response.status, "resolved_url": response.url,
                               "content_type": response.headers.get("Content-Type"),
                               "http_date": response.headers.get("Date")})
        rows = list(csv.DictReader(io.StringIO(body.decode("utf-8"))))
        if {r["source_id"] for r in rows} != {t[2] for t in TARGETS}:
            raise ValueError("Response does not contain the five exact requested identifiers")
        target.write_bytes(body)
        provenance.update({"result": "ok", "retrieved_utc": utc(), "bytes": len(body),
                           "sha256": digest(body), "rows": len(rows)})
    except Exception as exc:
        provenance.update({"result": "error", "retrieved_utc": utc(), "error": str(exc)})
        dump(OUT / "query_provenance.json", provenance)
        raise
    dump(OUT / "query_provenance.json", provenance)
    print(json.dumps({"request": "official_Gaia_DR3", "rows": len(rows), "sha256": digest(body)}))


def analyze():
    import numpy as np
    import pandas as pd
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from build_followup import frozen_inputs, relative, verified_arrays

    RAW.mkdir(parents=True, exist_ok=True)
    provenance = json.loads((OUT / "query_provenance.json").read_text())
    body = (RAW / "gaia_feature_review.csv").read_bytes()
    assert provenance["result"] == "ok" and digest(body) == provenance["sha256"]
    catalogue = {r["source_id"]: r for r in csv.DictReader(io.StringIO(body.decode()))}
    assert set(catalogue) == {t[2] for t in TARGETS}
    table = ROOT / "research/precision/flux_units/corrected_record_screen.csv.gz"
    current = pd.read_csv(table, dtype={"source_id": "string"}, low_memory=False).set_index("row_index")
    index = {(int(r["page"]), int(r["panel"])): r for r in csv.DictReader((BASE / "contact_sheet_index.csv").open())}
    inputs = frozen_inputs()
    retrieval = {r["sha256"]: r for r in map(json.loads, (BASE / "retrieval.jsonl").read_text().splitlines())}
    fig, axes = plt.subplots(5, 3, figsize=(15, 15), layout="constrained")
    results = []
    for row_axes, (page, panel, source, number) in zip(axes, TARGETS):
        r = current.loc[number]
        item = inputs[number]
        rec = item[1]
        ix = index[(page, panel)]
        assert ix["source_id"] == source and str(number) in ix["plotted_row_indices"].split("|")
        assert str(r.source_id) == source and r.kind == "Gaia_XP"
        assert bool(r.flux_units_validated) and bool(r.usable_screen) and r.status == "ok"
        raw_path = relative(rec["raw_path"])
        raw_body = raw_path.read_bytes()
        assert digest(raw_body) == r.sha256 == rec["sha256"]
        copied = RAW / f"row_{number}.txt"
        if copied.exists():
            assert copied.read_bytes() == raw_body
        else:
            copied.write_bytes(raw_body)
        w, f, iv, meta = verified_arrays(item)
        assert iv is None, "Unexpected supplied pixel uncertainty; extend the descriptive plot explicitly"
        if bool(r.calibrated):
            f = f * 10**(-0.4 * (float(r.cal_offset_mag) + float(r.cal_tilt_mag_per_1000A) * (w-6200)/1000))
        order = np.argsort(w); w, f = w[order], f[order]
        finite = np.isfinite(w) & np.isfinite(f)
        anchor = finite & (w >= 5200) & (w <= 5500)
        norm = float(np.median(f[anchor])); assert norm > 0
        f = f / norm
        windows = []
        for ax, (lo, hi) in zip(row_axes, [(3600,8300),(4700,5050),(6400,6750)]):
            mask = finite & (w >= lo) & (w <= hi)
            ax.plot(w[mask]/10, f[mask], ".-", color="#955615", lw=.7, markersize=2)
            ax.axhline(0, color="gray", lw=.5)
            if lo != 3600:
                reference = 4861 if lo == 4700 else 6563
                ax.axvline(reference/10, color="gray", ls=":", lw=.7)
            ax.set_xlabel("Wavelength (nm)")
            ax.set_ylabel("Fλ / median Fλ at 520–550 nm")
            ax.grid(alpha=.15)
            ax.set_title(f"{source} / XP {number}\n{catalogue[source]['phot_variable_flag']} / "
                         f"{catalogue[source]['best_class_name'] or 'no classifier row'}", fontsize=9)
        for center, halfwidth in [(4861,80), (6563,100)]:
            mask = finite & (np.abs(w-center) <= halfwidth)
            indexes = np.flatnonzero(mask)
            maximum = indexes[np.argmax(f[mask])]
            minimum = indexes[np.argmin(f[mask])]
            windows.append({"reference_A": center, "halfwidth_A": halfwidth,
                            "samples": int(mask.sum()), "maximum_A": float(w[maximum]),
                            "maximum_normalized_flux": float(f[maximum]),
                            "minimum_A": float(w[minimum]), "minimum_normalized_flux": float(f[minimum])})
        results.append({"page": page, "panel": panel, "source_id": source, "row_index": number,
                        "raw_sha256": r.sha256, "source_url": rec["source_url"],
                        "raw_copy": str(copied.relative_to(OUT)),
                        "prior_exact_retrieval": retrieval.get(r.sha256),
                        "contact_sheet_sha256": ix["contact_sheet_sha256"],
                        "current_calibrated": bool(r.calibrated), "current_Duv": float(r.duv),
                        "normalization": "median current F_lambda at 5200–5500 A; no refit",
                        "gaia_official": catalogue[source], "descriptive_windows": windows,
                        "unit_withheld_records": int(ix["unit_withheld_records"]),
                        "independent_spectrum_in_current_panel": False})
    fig.suptitle("Five visually selected Gaia XP reconstructions: exact export samples\n"
                 "No independent pixel errors, coefficient covariance or new line identification; reference wavelengths are guides", fontsize=12)
    fig.savefig(OUT / "xp_export_windows.png", dpi=160)
    fig.savefig(OUT / "xp_export_windows.svg")
    plt.close(fig)
    dump(OUT / "results.json", {"created_utc": utc(), "objects": results,
          "code_sha256": digest(Path(__file__).read_bytes()), "current_screen_sha256": digest(table.read_bytes()),
          "query_response_sha256": provenance["sha256"],
          "limitations": ["Selected after visual inspection, with no completeness or population-rate interpretation.",
             "Gaia classification scores are not posterior probabilities.",
             "XP and Gaia variability classification share mission data; no independent photons are added.",
             "No native coefficient covariance, independent spectroscopy, period or new line detection was measured."]})
    rows = [{"source_id": x["source_id"], "page": x["page"], "panel": x["panel"],
             "row_index": x["row_index"], "current_Duv": x["current_Duv"],
             "unit_withheld_records": x["unit_withheld_records"],
             **{k: x["gaia_official"][k] for k in ["phot_variable_flag", "best_class_name", "best_class_score", "ruwe", "has_xp_continuous"]}}
            for x in results]
    with (OUT / "catalogue_matches.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    print(json.dumps({"analyzed_XP_exports": len(results), "catalogue_rows": rows}, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fetch", action="store_true")
    parser.add_argument("--analyze", action="store_true")
    args = parser.parse_args()
    if not (args.fetch or args.analyze):
        parser.error("Choose --fetch and/or --analyze")
    if args.fetch:
        fetch()
    if args.analyze:
        analyze()
