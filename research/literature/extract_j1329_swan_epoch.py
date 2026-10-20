#!/usr/bin/env python3
"""Recover the first J1329 DESI epoch with its original exposure masks.

Swan's official per-star ASCII export is independently checked against our
direct cframe extraction of the second epoch before the first is retained.
The whole archive is cached outside the repository; only selected rows remain.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import tarfile
import urllib.request

import numpy as np

HERE = Path(__file__).resolve().parent
NAME = "WDJ132942.69+003336.60"
BASE = f"https://cygnus.astro.warwick.ac.uk/phsdaj/WhiteDwarfs/J1329/{NAME}"
URL = f"{BASE}/{NAME}_DESI_DR1_spectra.tar.gz"
EXPECTED_SHA = "9a4e795013e481208622e026e231203cab810d699c9973ebaa5b0f836b4f5b19"
OUTPUT = HERE / "sources/j1329_desi_20220127_swan_rows.npz"
MANIFEST = HERE / "sources/j1329_desi_20220127_swan_manifest.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=Path("/tmp/j1329_swan_spectra.tar.gz"))
    parser.add_argument("--download", action="store_true")
    args = parser.parse_args(argv)
    if not args.cache.exists() and args.download:
        request = urllib.request.Request(URL, headers={"User-Agent": "wish-you-were-green reproducible astronomy audit"})
        args.cache.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(request, timeout=60) as response:
            args.cache.write_bytes(response.read())
    if sha(args.cache) != EXPECTED_SHA:
        raise RuntimeError("Swan per-star archive differs from the pinned snapshot")
    reference = HERE / "sources/j1329_desi_20220311_rows.npz"
    reference_manifest = HERE / "sources/j1329_desi_20220311_manifest.json"
    if sha(reference) != json.loads(reference_manifest.read_text())["selected_rows_sha256"]:
        raise RuntimeError("Independent second-epoch cframe extraction failed hash check")
    inventory_path = HERE / "outputs/candidate27_desi_exposure_inventory.csv"
    with inventory_path.open() as handle:
        inventory = [r for r in csv.DictReader(handle) if r["source_id"] == "3711047662972690688"]
    arrays, members, comparisons = {}, [], []
    with tarfile.open(args.cache) as archive, np.load(reference) as direct:
        for night, exposure, fiber in (("20220127", "00120460", "1226"), ("20220311", "00125840", "1225")):
            expected = [r for r in inventory if r["NIGHT"] == night and int(r["EXPOSURE"]) == int(exposure)
                        and r["FIBER"] == fiber and r["WDJname"] == NAME and r["TARGETID"] == "39627800201661952"]
            if len(expected) != 1:
                raise RuntimeError("Gaia/WDJname/NIGHT/EXPID/FIBER/TARGETID inventory does not match the requested exposure")
            for arm in "brz":
                name = f"{NAME}_DESI_DR1_{night}_{exposure}_{fiber}-{arm}.dat"
                # Read the exact archive member without extracting arbitrary
                # archive paths into the workspace.
                payload = archive.extractfile(name).read()
                data = np.loadtxt(io.BytesIO(payload))
                if data.ndim != 2 or data.shape[1] != 5:
                    raise RuntimeError(f"Unexpected published column count: {name}")
                if not np.all(data[:, 4] == data[:, 4].astype(np.int64)):
                    raise RuntimeError(f"Noninteger mask in {name}")
                members.append({"member": name, "sha256": hashlib.sha256(payload).hexdigest(),
                                "rows": len(data), "masked_pixels": int(np.count_nonzero(data[:, 4])),
                                "zero_ivar_pixels": int(np.count_nonzero(data[:, 3] == 0))})
                if night == "20220127":
                    for index, key in enumerate(("wave_A", "flux", "sigma", "ivar", "mask")):
                        arrays[f"{arm}_{key}"] = data[:, index].astype(np.int64 if key == "mask" else float)
                else:
                    for column, key in ((0, "wave_A"), (1, "flux"), (3, "ivar"), (4, "mask")):
                        original = direct[f"{arm}_{key}"]
                        delta = np.abs(data[:, column] - original)
                        matched = bool(np.allclose(data[:, column], original, rtol=6e-6, atol=5e-6))
                        if key == "mask":
                            matched = bool(np.array_equal(data[:, column], original))
                        if not matched:
                            raise RuntimeError(f"Swan ASCII does not reproduce direct cframe {arm}/{key}")
                        nonzero = original != 0
                        comparisons.append({"arm": arm, "column": key,
                                            "maximum_absolute_difference": float(delta.max()),
                                            "maximum_relative_difference_nonzero": float(np.max(delta[nonzero] / np.abs(original[nonzero]))) if np.any(nonzero) else 0.,
                                            "matches_published_rounding": matched})
    np.savez_compressed(OUTPUT, **arrays)
    manifest = {
        "source_id": "3711047662972690688", "WDJname": NAME,
        "desi_targetid": "39627800201661952", "NIGHT": "20220127", "EXPID": 120460, "FIBER": 1226,
        "url": URL, "source_page": f"{BASE}/index.html", "retrieved_utc_date": "2026-10-18",
        "archive_sha256": EXPECTED_SHA, "archive_bytes": args.cache.stat().st_size,
        "columns": ["vacuum wavelength [A]", "F_lambda [1e-17 erg s^-1 cm^-2 A^-1]", "flux uncertainty", "inverse variance", "original DESI pixel MASK"],
        "members_used": members, "selected_rows_path": str(OUTPUT.relative_to(HERE)),
        "selected_rows_sha256": sha(OUTPUT),
        "second_epoch_direct_npz_sha256": sha(reference),
        "second_epoch_cframe_manifest_sha256": sha(reference_manifest),
        "exposure_inventory_sha256": sha(inventory_path),
        "identity_exposure_rows": inventory,
        "second_epoch_ascii_vs_direct_cframe": comparisons,
        "comparison_tolerance": "Wavelength/flux/IVAR rtol=6e-6, atol=5e-6; MASK must be identical. ASCII flux/IVAR is rounded compared with binary FITS.",
        "identity_basis": "Exact WDJname linked by Swan catalogue to Gaia ID; registered NIGHT/EXPID/FIBER match the published exposure inventory.",
        "cautions": [
            "Swan's published ASCII rows have rounded flux and IVAR. They are derived from DESI, not a second instrument or an independent spectrum.",
            "This selected first-night archive includes the original masks, replacing the unverified MWDD flag in the shape comparison only.",
            "The existing MWDD colour result is kept as a frozen reference; selecting original per-camera masks can change its shape slightly.",
            "Flux uncertainty is provided by the archive authors from IVAR; the comparison calculation uses IVAR directly.",
        ],
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"output": str(OUTPUT), "sha256": sha(OUTPUT),
                      "all_second_epoch_columns_match": all(x["matches_published_rounding"] for x in comparisons),
                      "first_epoch_masked_pixels": {a: int(np.count_nonzero(arrays[f'{a}_mask'])) for a in "brz"}}, indent=2))


if __name__ == "__main__":
    main()
