#!/usr/bin/env python3
"""Retrieve unchanged official Swan/Kilic sources, checking recorded hashes.

Large full catalogues and source tar archives are local caches. Selected
candidate rows are retained by build_candidate_prior_inventory.py instead.
"""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import io
import json
from pathlib import Path
import tarfile
import urllib.request

HERE = Path(__file__).resolve().parent
DEST = HERE / "sources"
MANIFEST = DEST / "atmosphere_sources_manifest.json"


def fetch(record):
    path = DEST / record["file"]
    if path.exists():
        blob = path.read_bytes()
    else:
        request = urllib.request.Request(record["url"], headers={"User-Agent": "wish-you-were-green astronomy research"})
        with urllib.request.urlopen(request, timeout=60) as response:
            blob = response.read()
    if hashlib.sha256(blob).hexdigest() != record["sha256"]:
        raise RuntimeError(f"Official-source bytes changed: {record['file']}; review before accepting a new version")
    path.write_bytes(blob)
    if path.suffix == ".tar":
        with tarfile.open(fileobj=io.BytesIO(blob)) as archive:
            for item in archive.getmembers():
                if item.isfile() and item.name.lower().endswith((".txt", ".tex")):
                    target = DEST / (path.name.split("_")[0] + "_" + Path(item.name).name)
                    target.write_bytes(archive.extractfile(item).read())
    return {"file": record["file"], "bytes": len(blob), "sha256": record["sha256"]}


def main():
    records = json.loads(MANIFEST.read_text())
    with ThreadPoolExecutor(max_workers=3) as pool:
        for result in pool.map(fetch, records):
            print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
