#!/usr/bin/env python3
"""Fetch a bounded published-catalogue check and two official source documents."""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
from urllib.parse import urlencode

from fetch_context import fetch

HERE = Path(__file__).resolve().parent


def main():
    query = """SELECT * FROM sdssdr7wd WHERE
    (ra BETWEEN 282.66 AND 282.68 AND dec BETWEEN 20.00 AND 20.03) OR
    (ra BETWEEN 11.355 AND 11.375 AND dec BETWEEN 14.627 AND 14.648) OR
    (ra BETWEEN 83.963 AND 83.983 AND dec BETWEEN -0.678 AND -0.658)"""
    (HERE / "kleinman_query.adql").write_text(query + "\n")
    endpoint = "https://heasarc.gsfc.nasa.gov/xamin/vo/tap/sync?" + urlencode({
        "REQUEST": "doQuery", "LANG": "ADQL", "QUERY": query})
    jobs = [(endpoint, "kleinman_catalogue.xml"),
            ("https://heasarc.gsfc.nasa.gov/w3browse/all/sdssdr7wd.html", "kleinman_catalogue_definition.html"),
            ("https://cxc.harvard.edu/target_lists/cycle7/abstracts_cycle7.html", "chandra_cycle7.html"),
            ("https://www.sdss4.org/dr17/algorithms/bitmasks/", "sdss_bitmasks.html")]
    gaia_query = "SELECT * FROM gaiadr3.vari_classifier_result WHERE source_id IN (4518692348609283712,2780975896637670528,3217759570831525120)"
    (HERE / "gaia_variability_query.adql").write_text(gaia_query + "\n")
    gaia_url = "https://gea.esac.esa.int/tap-server/tap/sync?" + urlencode({
        "REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "csv", "QUERY": gaia_query})
    jobs.append((gaia_url, "gaia_variability.csv"))
    def cached_or_fetch(job):
        path = HERE / "sources" / (job[1] + ".provenance.json")
        return json.loads(path.read_text()) if path.exists() else fetch(*job)
    with ThreadPoolExecutor(max_workers=4) as executor:
        records = list(executor.map(cached_or_fetch, jobs))
    initial = HERE / "sources/kleinman_catalogue.csv.provenance.json"
    if initial.exists():
        records.append({**json.loads(initial.read_text()), "data_status":
            "Saved initial VOTable error response: unsupported requested CSV format; not a catalogue nondetection. Retried using server default VOTable."})
    (HERE / "specialist_manifest.json").write_text(json.dumps({
        "selection": "Published source named by the three MWDD pages; bounded coordinates. Chandra proposal is retained as conflicting historical context, not a new physical classification.",
        "sources": records}, indent=2) + "\n")
    print(json.dumps(records, indent=2))


if __name__ == "__main__":
    main()
