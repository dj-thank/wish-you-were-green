#!/usr/bin/env python3
"""Enrich a read-only acquisition snapshot while downloads continue independently."""
import argparse
import json
from pathlib import Path

from acquire_mwdd import BASE, inspect_csv, star_metadata


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default=str(BASE / "manifest.json"))
    parser.add_argument("--output", default=str(BASE / "manifest_enriched.json"))
    args = parser.parse_args()
    selected = json.loads((BASE / "selected_targets.json").read_text())
    catalog = {row["wdid"]: row for row in selected}
    records = json.loads(Path(args.input).read_text())
    seen = {}
    for record in records:
        row = catalog.get(record["wdid"])
        if row:
            record.update(star_metadata(row))
        if record.get("status") == "downloaded":
            if not record.get("numeric_sha256_wavelength_flux"):
                record.update(inspect_csv(Path(record["raw_path"]).read_bytes(), Path(record["raw_path"])))
            digest = record["numeric_sha256_wavelength_flux"]
            record["duplicate_numeric_of"] = seen.get(digest)
            seen.setdefault(digest, record["raw_path"])
    target = Path(args.output)
    temp = target.with_suffix(".tmp.json")
    temp.write_text(json.dumps(records, ensure_ascii=False, indent=2))
    temp.replace(target)
    print(json.dumps({"records": len(records), "numeric_unique": len(seen),
                      "duplicates": sum(bool(record.get("duplicate_numeric_of")) for record in records),
                      "path": str(target)}))


if __name__ == "__main__":
    main()
