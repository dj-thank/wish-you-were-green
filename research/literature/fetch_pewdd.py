#!/usr/bin/env python3
"""Fetch an immutable PEWDD data snapshot; no login or catalogue edits.

The data are attributed to Williams et al. (2024) and the original papers in
each row.  This script does not assign the project's code licence to the data.
"""
from __future__ import annotations

import csv
import gzip
import hashlib
import io
import json
from pathlib import Path
import urllib.request

HERE = Path(__file__).resolve().parent
COMMIT = "023dba3176ac367c6cf2b5968847a80d79e3c594"
URL = f"https://raw.githubusercontent.com/jamietwilliams/PEWDD/{COMMIT}/PEWDD.csv"
DEST = HERE / "sources" / "pewdd_023dba3.csv.gz"
MANIFEST = HERE / "sources" / "pewdd_manifest.json"


def main() -> None:
    DEST.parent.mkdir(parents=True, exist_ok=True)
    if DEST.exists() and MANIFEST.exists():
        blob = gzip.decompress(DEST.read_bytes())
        manifest = json.loads(MANIFEST.read_text())
        if hashlib.sha256(blob).hexdigest() != manifest["uncompressed_sha256"]:
            raise RuntimeError("Cached PEWDD snapshot no longer matches its manifest")
        print(json.dumps({"cached": True, **manifest}, indent=2))
        return
    request = urllib.request.Request(URL, headers={"User-Agent": "wish-you-were-green research data audit"})
    with urllib.request.urlopen(request, timeout=60) as response:
        blob = response.read()
        final_url = response.url
    reader = csv.DictReader(io.StringIO(blob.decode("utf-8-sig")))
    fields = reader.fieldnames
    rows = list(reader)
    required = {"Identifier", "Gaia_designation", "Paper", "log(Na/H(e))", "log(Na/H(e))e"}
    if not required.issubset(fields or []):
        raise RuntimeError("Unexpected PEWDD schema")
    DEST.write_bytes(gzip.compress(blob, mtime=0))
    manifest = {
        "requested_url": URL,
        "resolved_url": final_url,
        "repository_commit": COMMIT,
        "repository_commit_date_utc": "2026-03-27T15:09:37Z",
        "retrieval_date_utc": "2026-10-18",
        "path": str(DEST.relative_to(HERE)),
        "uncompressed_bytes": len(blob),
        "uncompressed_sha256": hashlib.sha256(blob).hexdigest(),
        "compressed_sha256": hashlib.sha256(DEST.read_bytes()).hexdigest(),
        "rows": len(rows),
        "field_count": len(fields or []),
        "paper_url": "https://www.aanda.org/articles/aa/full_html/2024/11/aa50509-24/aa50509-24.html",
        "documentation_url": "https://pewdd-tutorial.readthedocs.io/en/latest/usage.html",
        "cautions": [
            "This exact repository snapshot is dated March 2026; not all subsequent abundance papers are included.",
            "One star can have multiple rows for papers or atmosphere assumptions; retain them.",
            "An abundance uncertainty of -1 denotes an upper limit, not a detection.",
            "Atmospheric number ratios are not accreted-body compositions without diffusion and accretion-phase modelling.",
            "The upstream data retain their terms; the project code licence does not relicense this snapshot."
        ],
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
