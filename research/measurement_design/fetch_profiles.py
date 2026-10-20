#!/usr/bin/env python3
"""Explicit public retrieval of total-system passbands; never used by CI."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import requests

HERE = Path(__file__).resolve().parent
BASE = "https://svo2.cab.inta-csic.es/theory/fps/fps.php"
FILTER_IDS = tuple(f"SkyMapper/SkyMapper.{b}" for b in "uvgriz") + tuple(
    "OAJ/JPLUS." + b for b in (
        "uJAVA", "J0378", "J0395", "J0410", "J0430", "gSDSS",
        "J0515", "rSDSS", "J0660", "iSDSS", "J0861", "zSDSS",
    )
)


def parse_profile(data):
    root = ET.fromstring(data)
    params = {e.attrib["name"]: e.attrib.get("value", "")
              for e in root.iter()
              if e.tag.split("}")[-1] == "PARAM" and "name" in e.attrib}
    fields = [e.attrib["name"] for e in root.iter()
              if e.tag.split("}")[-1] == "FIELD"]
    rows = [[e.text for e in tr if e.tag.split("}")[-1] == "TD"]
            for tr in root.iter() if tr.tag.split("}")[-1] == "TR"]
    if fields != ["Wavelength", "Transmission"] or len(rows) < 3:
        raise ValueError(f"Unexpected SVO profile table: {fields}, {len(rows)} rows")
    return params, [(float(row[0]), float(row[1])) for row in rows]


def retrieve(filter_id):
    response = requests.get(BASE, params={"ID": filter_id}, timeout=45)
    response.raise_for_status()
    params, rows = parse_profile(response.content)
    if params.get("filterID") != filter_id:
        raise ValueError((filter_id, params.get("filterID")))
    return response.content, {
        "filter_id": filter_id, "url": response.url,
        "retrieved_utc": datetime.now(timezone.utc).isoformat(),
        "http_status": response.status_code,
        "sha256": hashlib.sha256(response.content).hexdigest(),
        "bytes": len(response.content), "rows": len(rows),
        "wavelength_min_A": min(row[0] for row in rows),
        "wavelength_max_A": max(row[0] for row in rows),
        "first_response": rows[0][1], "last_response": rows[-1][1],
        "parameters": params,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download", action="store_true", required=True)
    args = parser.parse_args()
    target = HERE / "sources"
    target.mkdir(parents=True, exist_ok=True)
    records = []
    # Independent public reads are concurrent; writes below are sequential.
    with ThreadPoolExecutor(max_workers=4) as executor:
        for data, record in executor.map(retrieve, FILTER_IDS):
            name = record["filter_id"].replace("/", "_") + ".xml"
            (target / name).write_bytes(data)
            record["file"] = "sources/" + name
            records.append(record)
            print(record["filter_id"], record["rows"],
                  record["wavelength_min_A"], record["wavelength_max_A"], flush=True)
    (HERE / "profile_manifest.json").write_text(
        json.dumps({"source": BASE, "selection": "six SkyMapper and twelve J-PLUS total-system profiles; no _filter-only substitutes",
                    "profiles": records}, indent=2, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
