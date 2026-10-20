#!/usr/bin/env python3
"""Fetch only the three preselected public catalogue contexts, with provenance."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
TARGET_ROWS = (7607, 8019, 7930)


def fetch(url, name):
    folder = HERE / "sources"
    folder.mkdir(exist_ok=True)
    request = Request(url, headers={"User-Agent": "wish-you-were-green research audit; public read"})
    retrieved = datetime.now(timezone.utc).isoformat()
    with urlopen(request, timeout=45) as response:
        blob = response.read()
        record = {"url": url, "final_url": response.geturl(),
                  "retrieved_utc": retrieved, "http_status": response.status,
                  "content_type": response.headers.get("Content-Type"),
                  "bytes": len(blob), "sha256": hashlib.sha256(blob).hexdigest(),
                  "file": "sources/" + name}
    (folder / name).write_bytes(blob)
    (folder / (name + ".provenance.json")).write_text(json.dumps(record, indent=2) + "\n")
    return record


def main():
    registry = json.loads((HERE.parent / "overlay_registry.json").read_text())
    manifest = json.load(gzip.open(ROOT / "mwdd/manifest_enriched.json.gz", "rt"))
    selected = []
    for index in TARGET_ROWS:
        overlay = next(r for r in registry["records"] if r["mwdd_row_index"] == index)
        metadata = next(r for r in manifest if r.get("sha256") == overlay["mwdd_sha256"])
        selected.append((index, metadata))
    columns = "source_id,ra,dec,ref_epoch,parallax,parallax_error,pmra,pmdec,ruwe,phot_g_mean_mag,bp_rp,phot_variable_flag,duplicated_source,non_single_star,has_xp_continuous,ipd_frac_multi_peak"
    ids = ",".join(r["source_id"] for _, r in selected)
    cones = " OR ".join(
        "1=CONTAINS(POINT('ICRS',ra,dec),CIRCLE('ICRS',%.12f,%.12f,0.0041666666667))"
        % (r["ra_deg"], r["dec_deg"]) for _, r in selected)
    query = f"SELECT {columns} FROM gaiadr3.gaia_source WHERE source_id IN ({ids}) OR {cones} ORDER BY source_id"
    (HERE / "gaia_query.adql").write_text(query + "\n")
    url = "https://gea.esac.esa.int/tap-server/tap/sync?" + urlencode(
        {"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "csv", "QUERY": query})
    jobs = [(r["star_page_url"], f"mwdd_{index}.html") for index, r in selected]
    jobs.append((url, "gaia_context.csv"))
    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(lambda job: fetch(*job), jobs))
    (HERE / "context_manifest.json").write_text(json.dumps({
        "selection": "Three root-requested visually flagged rows, fixed before context retrieval",
        "row_indices": list(TARGET_ROWS), "sources": results}, indent=2) + "\n")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
