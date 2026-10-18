#!/usr/bin/env python3
"""Read-only public Gaia/IRSA acquisition, retaining exact bytes and queries.

No credentials, proprietary ZTF collection, or forced-photometry submission is
used. A successful empty query is preserved and is not called a nondetection.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import csv
from datetime import datetime, timezone
from hashlib import sha256
import io
import json
from pathlib import Path
import urllib.error
import urllib.parse
import urllib.request

BASE = Path(__file__).resolve().parent
RAW = BASE / "raw"
SOURCES = {
    "J0913+4434": ("818833831355548928", 138.4021030032363, 44.56813161736343),
    "J0429-0354": ("3204436719718449280", 67.43628526183, -3.90650606101),
    "J1329+0033": ("3711047662972690688", 202.42771312194, 0.55963910805),
    "J1323-0129": ("3638333660492606976", 200.80308349614, -1.49042513540),
}
GAIA_TAP = "https://gea.esac.esa.int/tap-server/tap/sync"
IRSA_TAP = "https://irsa.ipac.caltech.edu/TAP/sync"
ZTF_API = "https://irsa.ipac.caltech.edu/cgi-bin/ZTF/nph_light_curves"


def fetch(name, endpoint, params, extension="csv"):
    RAW.mkdir(parents=True, exist_ok=True)
    dest = RAW / f"{name}.{extension}"
    meta_path = RAW / f"{name}.provenance.json"
    if dest.exists() and meta_path.exists():
        meta = json.loads(meta_path.read_text())
        if meta["sha256"] != sha256(dest.read_bytes()).hexdigest():
            raise RuntimeError(f"Frozen response hash mismatch: {dest}")
        return {"name": name, "cached": True, "bytes": dest.stat().st_size}
    url = endpoint + ("?" + urllib.parse.urlencode(params) if params else "")
    req = urllib.request.Request(url, headers={"User-Agent": "wish-you-were-green-public-research/1.0"})
    started = datetime.now(timezone.utc).isoformat()
    try:
        with urllib.request.urlopen(req, timeout=50) as response:
            content = response.read(15_000_001)
            status = response.status
            resolved_url = response.url
            headers = dict(response.headers)
        if len(content) > 15_000_000:
            raise RuntimeError("Response exceeds this narrow-query 15 MB safety limit")
        if extension == "csv" and content.lstrip().startswith((b"<?xml", b"<html", b"<!DOCTYPE")):
            (RAW / f"{name}.service_error.xml").write_bytes(content)
            raise RuntimeError("Service returned XML/HTML instead of CSV; retained as service_error.xml, "
                               + "sha256=" + sha256(content).hexdigest() + ": " + content[-700:].decode(errors="replace"))
        dest.write_bytes(content)
        meta = dict(name=name, endpoint=endpoint, parameters=params, request_url=url,
                    resolved_url=resolved_url, status=status, headers=headers,
                    query_started_utc=started, retrieved_utc=datetime.now(timezone.utc).isoformat(),
                    relative_path=str(dest.relative_to(BASE)), bytes=len(content), sha256=sha256(content).hexdigest())
        meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n")
        return {"name": name, "status": status, "bytes": len(content), "sha256": meta["sha256"]}
    except Exception as exc:
        diagnostic = dict(name=name, endpoint=endpoint, parameters=params, request_url=url,
                          attempted_utc=started, error=repr(exc))
        (RAW / f"{name}.error.json").write_text(json.dumps(diagnostic, indent=2) + "\n")
        return diagnostic


def tap(name, endpoint, query):
    return (name, endpoint, dict(REQUEST="doQuery", LANG="ADQL", FORMAT="csv", QUERY=query))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=["metadata", "lightcurves", "controls"])
    parser.add_argument("--collection", default="ztf_dr24", help="Explicit public ZTF release")
    args = parser.parse_args()
    if args.stage == "metadata":
        columns = ["source_id", "ra", "dec", "ref_epoch", "ra_error", "dec_error", "parallax", "parallax_error",
                   "pmra", "pmdec", "pmra_error", "pmdec_error", "ruwe", "astrometric_params_solved",
                   "duplicated_source", "ipd_frac_multi_peak", "ipd_frac_odd_win", "phot_bp_rp_excess_factor",
                   "phot_g_mean_mag", "phot_bp_mean_mag", "phot_rp_mean_mag", "phot_bp_n_obs", "phot_rp_n_obs",
                   "phot_bp_n_contaminated_transits", "phot_bp_n_blended_transits",
                   "phot_rp_n_contaminated_transits", "phot_rp_n_blended_transits", "phot_variable_flag",
                   "has_epoch_photometry", "has_xp_continuous", "non_single_star"]
        cones = " OR ".join(f"1=CONTAINS(POINT('ICRS',ra,dec),CIRCLE('ICRS',{ra},{dec},{15/3600}))"
                            for _, ra, dec in SOURCES.values())
        gaia_query = "SELECT " + ",".join(columns) + " FROM gaiadr3.gaia_source WHERE " + cones
        jobs = [tap("gaia_dr3_15arcsec_fields", GAIA_TAP, gaia_query),
                tap("irsa_ztf_table_inventory", IRSA_TAP,
                    "SELECT table_name,description FROM TAP_SCHEMA.tables WHERE table_name LIKE 'ztf_objects_dr%'"),
                ("ztf_lightcurve_api", "https://irsa.ipac.caltech.edu/docs/program_interface/ztf_lightcurve_api.html", {}, "html"),
                ("ztf_dr24_release_notes", "https://irsa.ipac.caltech.edu/data/ZTF/docs/releases/dr24/src/dr24.html", {}, "html")]
    elif args.stage == "lightcurves":
        jobs = [(f"ztf_{args.collection}_{name}", ZTF_API,
                 dict(POS=f"CIRCLE {ra} {dec} {10/3600}", COLLECTION=args.collection, FORMAT="csv"))
                for name, (_, ra, dec) in SOURCES.items()]
    else:
        config = json.loads((BASE / "control_queries.json").read_text())
        jobs = [tap(item["name"], IRSA_TAP, item["query"]) for item in config]
    with ThreadPoolExecutor(max_workers=2) as pool:
        for result in pool.map(lambda job: fetch(*job), jobs):
            print(json.dumps(result, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
