#!/usr/bin/env python3
"""Verify frozen acquisition hashes; optionally reacquire missing exact bytes.

Updated upstream content is saved beside the frozen input with a .changed
suffix and never replaces the expected version or its provenance record.
"""
import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import urllib.request

BASE = Path(__file__).resolve().parent


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--fetch-missing", action="store_true")
    args = p.parse_args()
    checked, errors, recovery = [], [], []
    for mp in sorted((BASE / "raw").glob("*.provenance.json")):
        meta = json.loads(mp.read_text())
        dest = BASE / meta["relative_path"]
        if not dest.exists() and args.fetch_missing:
            try:
                with urllib.request.urlopen(meta["request_url"], timeout=50) as response:
                    data = response.read(15_000_001)
                digest = sha256(data).hexdigest()
                if digest != meta["sha256"]:
                    changed = dest.with_suffix(dest.suffix + ".changed")
                    changed.write_bytes(data)
                    recovery.append(dict(name=meta["name"], status="upstream_bytes_changed", sha256=digest, preserved_as=changed.name))
                else:
                    dest.write_bytes(data)
                    recovery.append(dict(name=meta["name"], status="exact_bytes_recovered", sha256=digest))
            except Exception as exc:
                recovery.append(dict(name=meta["name"], status="retrieval_failed", error=repr(exc)))
        if not dest.exists():
            errors.append({"file": str(dest.relative_to(BASE)), "error": "missing"})
            continue
        actual = sha256(dest.read_bytes()).hexdigest()
        if actual != meta["sha256"]:
            errors.append({"file": str(dest.relative_to(BASE)), "error": "hash mismatch", "actual_sha256": actual})
        else:
            checked.append({"file": str(dest.relative_to(BASE)), "bytes": dest.stat().st_size, "sha256": actual})
    snapshot_meta = json.loads((BASE / "gaia_extended_input.provenance.json").read_text())
    if sha256((BASE / "gaia_extended_input.csv").read_bytes()).hexdigest() != snapshot_meta["snapshot_sha256"]:
        errors.append({"file": "gaia_extended_input.csv", "error": "frozen shortlist hash mismatch"})
    result = dict(verified_utc=datetime.now(timezone.utc).isoformat(), n_verified_raw_responses=len(checked),
                  total_raw_bytes=sum(r["bytes"] for r in checked), errors=errors, recovery=recovery, inputs=checked)
    out = BASE / "results/frozen_input_verification.json"
    out.write_text(json.dumps(result, indent=2)+"\n")
    print(json.dumps({k:result[k] for k in ["n_verified_raw_responses","total_raw_bytes","errors","recovery"]}, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
