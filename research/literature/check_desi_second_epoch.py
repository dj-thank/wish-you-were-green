#!/usr/bin/env python3
"""Extract and compare the previously unscreened second DESI night of J1329.

Download mode reads the official calibrated exposure products.  The large
whole-camera files are temporary; the exact selected rows and provenance are
retained.  Offline mode recalculates from those compact rows.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import sys
import urllib.request

import numpy as np
from astropy.io import fits

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from colour_pipeline import integrate_colour, recalibrate_gri  # noqa: E402

TARGET_ID = 39627800201661952
GAIA_ID = "3711047662972690688"
EXPID = "00125840"
NIGHT = "20220311"
FIBER = 1225
BASE = f"https://data.desi.lbl.gov/public/dr1/spectro/redux/iron/exposures/{NIGHT}/{EXPID}"
SOURCE = HERE / "sources" / "j1329_desi_20220311_rows.npz"
MANIFEST = HERE / "sources" / "j1329_desi_20220311_manifest.json"


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def download_extract(cache: Path) -> None:
    cache.mkdir(parents=True, exist_ok=True)

    def one_arm(arm: str):
        filename = f"cframe-{arm}2-{EXPID}.fits.gz"
        url = f"{BASE}/{filename}"
        path = cache / filename
        if not path.exists():
            request = urllib.request.Request(url, headers={"User-Agent": "wish-you-were-green research data audit"})
            part = path.with_suffix(path.suffix + ".partial")
            with urllib.request.urlopen(request, timeout=60) as response, part.open("wb") as output:
                for block in iter(lambda: response.read(1024 * 1024), b""):
                    output.write(block)
            part.replace(path)
        with fits.open(path) as hdus:
            fmap = hdus["FIBERMAP"].data
            match = np.flatnonzero((fmap["TARGETID"] == TARGET_ID) & (fmap["FIBER"] == FIBER))
            if len(match) != 1:
                raise RuntimeError(f"{filename}: expected one exact target/fiber match, got {len(match)}")
            row = int(match[0])
            header = hdus[0].header
            if int(header["EXPID"]) != int(EXPID) or str(header["NIGHT"]) != NIGHT:
                raise RuntimeError("Exposure metadata mismatch")
            arrays = {
                f"{arm}_wave_A": np.array(hdus["WAVELENGTH"].data, dtype=float),
                f"{arm}_flux": np.array(hdus["FLUX"].data[row], dtype=float),
                f"{arm}_ivar": np.array(hdus["IVAR"].data[row], dtype=float),
                f"{arm}_mask": np.array(hdus["MASK"].data[row]),
                f"{arm}_resolution": np.array(hdus["RESOLUTION"].data[row]),
            }
            meta = {
                "arm": arm, "url": url, "downloaded_bytes": path.stat().st_size,
                "sha256": sha(path), "fiber_map_row_0based": row,
                "targetid": str(int(fmap["TARGETID"][row])), "fiber": int(fmap["FIBER"][row]),
                "NIGHT": str(header["NIGHT"]), "EXPID": int(header["EXPID"]),
                "DATE-OBS": header.get("DATE-OBS"), "EXPTIME": header.get("EXPTIME"),
                "BUNIT": hdus["FLUX"].header.get("BUNIT"),
                "wavelength_min_A": float(arrays[f"{arm}_wave_A"].min()),
                "wavelength_max_A": float(arrays[f"{arm}_wave_A"].max()),
                "pixels": len(arrays[f"{arm}_wave_A"]),
                "masked_pixels": int(np.count_nonzero(arrays[f"{arm}_mask"])),
            }
            print(json.dumps(meta), flush=True)
            return arrays, meta

    with ThreadPoolExecutor(max_workers=3) as pool:
        products = list(pool.map(one_arm, "brz"))
    arrays, files = {}, []
    for array, metadata in products:
        arrays.update(array)
        files.append(metadata)
    SOURCE.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(SOURCE, **arrays)
    manifest = {
        "gaia_source_id": GAIA_ID, "desi_targetid": str(TARGET_ID),
        "retrieval_date_utc": "2026-10-18", "archive_product": "DESI DR1 iron calibrated exposure cframe",
        "files": files, "selected_rows_path": str(SOURCE.relative_to(HERE)),
        "selected_rows_sha256": sha(SOURCE),
        "data_model": "https://desidatamodel.readthedocs.io/en/latest/DESI_SPECTRO_REDUX/SPECPROD/exposures/NIGHT/EXPID/cframe-CAMERA-EXPID.html",
        "provenance_table": "novelty/swan2026_candidate_audit.json",
        "cautions": [
            "This is a new observing night for the repository but uses the same DESI instrument.",
            "The full-camera source files are not duplicated in git; retrieve their recorded URLs and verify hashes to re-extract.",
            "Resolution matrices are included as instrumental line-spread information, not a pixel covariance matrix.",
            "Flux is F_lambda in units of 1e-17 erg s^-1 cm^-2 Angstrom^-1; common scale cancels from chromaticity."
        ],
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n")


def merge_segments(data, blue_red_join: float, red_z_join: float):
    waves, fluxes, ivars = [], [], []
    # If an entire arm is invalid, keep the good neighbouring arm to its
    # actual edge; do not discard it merely to satisfy a nominal seam.
    valid_z = np.any((data["z_mask"] == 0) & np.isfinite(data["z_ivar"]) & (data["z_ivar"] > 0))
    r_upper = red_z_join if valid_z else np.inf
    for arm, lower, upper in (("b", -np.inf, blue_red_join), ("r", blue_red_join, r_upper), ("z", red_z_join, np.inf)):
        w, f, iv, mask = [data[f"{arm}_{key}"] for key in ("wave_A", "flux", "ivar", "mask")]
        good = (w >= lower) & (w < upper) & (mask == 0) & np.isfinite(f) & np.isfinite(iv) & (iv > 0)
        waves.append(w[good]); fluxes.append(f[good]); ivars.append(iv[good])
    return np.concatenate(waves), np.concatenate(fluxes), np.concatenate(ivars)


def calibration_quality(cal):
    """Use the original screen's residual/tilt acceptance gate explicitly."""
    residual = float(cal["cal_max_residual_mag"])
    tilt = float(cal["cal_tilt_mag_per_1000A"])
    reasons = []
    if not np.isfinite(residual) or residual >= .15:
        reasons.append("maximum gri residual >=0.15 mag or nonfinite")
    if not np.isfinite(tilt) or abs(tilt) >= .25:
        reasons.append("absolute tilt >=0.25 mag/1000 A or nonfinite")
    return {"accepted": not reasons, "rejection_reasons": reasons, "maximum_absolute_tilt_mag_per_1000A": .25, "maximum_residual_mag": .15, "observed_tilt_mag_per_1000A": tilt, "observed_maximum_residual_mag": residual}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--cache", type=Path, default=Path("/tmp/wish-green-desi-cframes"))
    args = parser.parse_args()
    if args.download:
        download_extract(args.cache)
        from extract_j1329_swan_epoch import main as extract_swan_epoch
        extract_swan_epoch(["--download"])
    manifest = json.loads(MANIFEST.read_text())
    if sha(SOURCE) != manifest["selected_rows_sha256"]:
        raise RuntimeError("Selected DESI rows failed hash check")
    with (ROOT / "results" / "headline_candidates.csv").open() as handle:
        import csv
        first = next(row for row in csv.DictReader(handle) if row["source_id"] == GAIA_ID)
    observed = [float(first[f"anchor_{band}_mag"]) for band in "gri"]
    errors = [float(first[f"anchor_{band}_error"]) for band in "gri"]
    results = []
    with np.load(SOURCE) as data:
        # Actual cframe overlaps are B/R=5760--5800 A and R/Z=7520--7620 A.
        for br_join, rz_join in ((5780.0, 7570.0), (5765.0, 7530.0), (5795.0, 7610.0)):
            w, f, iv = merge_segments(data, br_join, rz_join)
            raw = integrate_colour(w, f, iv)
            m, difference, failure, quality = None, None, None, None
            try:
                corrected, cal = recalibrate_gri(w, f, observed, errors, system="panstarrs")
                quality = calibration_quality(cal)
                if not quality["accepted"]:
                    raise ValueError("Rejected calibration: " + "; ".join(quality["rejection_reasons"]))
                correction = np.divide(corrected, f, out=np.ones_like(f), where=f != 0)
                m = integrate_colour(w, corrected, iv / correction ** 2)
                m.update(cal)
                same_uv = [float(first[k]) for k in ("u1960", "v1960")]
                difference = float(np.linalg.norm(np.array([m["u1960"], m["v1960"]]) - same_uv))
            except ValueError as exc:
                failure = str(exc)
            results.append({
                "blue_red_join_A": br_join, "red_z_join_A": rz_join,
                "raw_partial_band_diagnostic": raw, "panstarrs_colour": m,
                "calibration_failure": failure,
                "calibration_quality_gate": quality,
                "accepted_calibrated_colour": m is not None and m["coverage_eligible"],
                "uv_distance_from_first_epoch_same_anchor": difference,
            })
        w, f, iv = merge_segments(data, 5780.0, 7570.0)
    with np.load(ROOT / first["parsed_path"]) as prior:
        old_flag = prior["flag"]
        # Preserve the old-export provenance but obtain the comparison's
        # original masks from the verified official Swan exposure export.
        old_flag_values = np.unique(old_flag).tolist()
    first_source = HERE / "sources/j1329_desi_20220127_swan_rows.npz"
    first_manifest_path = HERE / "sources/j1329_desi_20220127_swan_manifest.json"
    first_manifest = json.loads(first_manifest_path.read_text())
    if sha(first_source) != first_manifest["selected_rows_sha256"]:
        raise RuntimeError("First-epoch Swan exposure rows failed hash check")
    with np.load(first_source) as prior:
        old_w, old_f, old_iv = merge_segments(prior, 5780., 7570.)
        old_sigma = 1 / np.sqrt(old_iv)
    binned = []
    for low in np.arange(4000.0, 7500.0, 100.0):
        high = low + 100.0
        selections = [(old_w, old_f, old_sigma), (w, f, 1 / np.sqrt(iv))]
        row = {"wave_center_A": float((low + high) / 2)}
        for label, (wave, flux, sigma) in zip(("first", "second"), selections):
            good = (wave >= low) & (wave < high) & np.isfinite(flux) & np.isfinite(sigma) & (sigma > 0)
            for center, halfwidth in ((5577.34, 8), (5890, 6), (5896, 6), (6300.30, 8), (6363.78, 8)):
                good &= abs(wave - center) > halfwidth
            row[f"{label}_pixels"] = int(np.count_nonzero(good))
            if not np.any(good):
                raise RuntimeError(f"No usable {label}-epoch pixels in {low}--{high} A")
            row[f"{label}_mean_flux"] = float(np.mean(flux[good]))
            row[f"{label}_mean_flux_error_uncorrelated"] = float(np.sqrt(np.sum(sigma[good] ** 2)) / np.count_nonzero(good))
        binned.append(row)
    norm_first = float(np.median([r["first_mean_flux"] for r in binned if 6500 <= r["wave_center_A"] <= 7100]))
    norm_second = float(np.median([r["second_mean_flux"] for r in binned if 6500 <= r["wave_center_A"] <= 7100]))
    for row in binned:
        row["first_relative_flux"] = row["first_mean_flux"] / norm_first
        row["second_relative_flux"] = row["second_mean_flux"] / norm_second
        row["first_relative_flux_error_uncorrelated"] = row["first_mean_flux_error_uncorrelated"] / norm_first
        row["second_relative_flux_error_uncorrelated"] = row["second_mean_flux_error_uncorrelated"] / norm_second
    summary = {
        "colour_pipeline_sha256": sha(ROOT / "colour_pipeline.py"),
        "candidate": "J1329+0033", "source_id": GAIA_ID,
        "first_epoch_MWDD_url": first["source_url"],
        "first_epoch_MWDD_flag_values": old_flag_values,
        "first_epoch_MWDD_parsed_sha256": sha(ROOT / first["parsed_path"]),
        "first_epoch_shape_source": "Official Swan per-star DESI exposure ASCII export, NIGHT=20220127/EXPID=120460/FIBER=1226",
        "first_epoch_shape_manifest": str(first_manifest_path.relative_to(HERE)),
        "first_epoch_shape_manifest_sha256": sha(first_manifest_path),
        "first_epoch_mask_caveat": "MWDD's uniform flag=1 is not interpreted as a DESI bitmask. Both shapes now use original MASK=0 and IVAR>0; first-night original masks come from Swan's official ASCII extraction, verified via the second-night direct cframes.",
        "first_epoch_panstarrs": {key: first[key] for key in ("hex", "x", "y", "u1960", "v1960", "duv")},
        "second_epoch_manifest": str(MANIFEST.relative_to(HERE)),
        "photometry": {"system": "Pan-STARRS gri", "magnitudes": observed, "quoted_errors": errors, "shared_with_first_epoch": True},
        "arm_join_sensitivity": results,
        "full_colour_validation_status": "unavailable_missing_valid_z_arm" if all(r["panstarrs_colour"] is None for r in results) else "available_with_stated_calibration_limits",
        "shape_comparison": {
            "wavelength_interval_A": [4000, 7500], "bin_width_A": 100,
            "normalization": "Separate median fluxes in 6500--7100 A; no spectral tilt or band shape is fitted.",
            "first_median_flux": norm_first, "second_median_flux": norm_second,
            "note": "This overlap-only comparison cannot establish a complete independently calibrated visible chromaticity."
        },
        "cautions": [
            "No arm is individually rescaled; joins are fixed inside camera overlaps. Alternative joins test instrumental seam sensitivity.",
            "Both nights require original MASK=0 and positive finite inverse variance. The first-night Swan ASCII export is rounded; its second-night counterparts reproduce our direct cframes within that rounding. Narrow airglow windows match the repository integration convention.",
            "The supplied per-pixel noise does not include coherent calibration errors, sky-model errors or inter-pixel covariance.",
            "Both nights use the same photometric anchors: the calibrated colours are not independent calibration evidence.",
            "Do not claim intrinsic variability from a two-night discrepancy until camera coverage, flux calibration and sky subtraction have been checked.",
            "One discrepant exposure must not be silently corrected toward the earlier colour."
        ],
    }
    output = HERE / "outputs"
    output.mkdir(parents=True, exist_ok=True)
    with (output / "j1329_second_epoch_common_bins.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(binned[0]))
        writer.writeheader(); writer.writerows(binned)
    (output / "j1329_second_epoch_comparison.json").write_text(json.dumps(summary, indent=2) + "\n")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    figure, axis = plt.subplots(figsize=(9, 4.8))
    colors = ("#2c677b", "#b35732")
    for label, date, color in zip(("first", "second"), ("NIGHT 20220127 (Swan/DESI original masks)", "NIGHT 20220311 (official DESI cframe)"), colors):
        x = np.array([r["wave_center_A"] for r in binned])
        y = np.array([r[f"{label}_relative_flux"] for r in binned])
        e = np.array([r[f"{label}_relative_flux_error_uncorrelated"] for r in binned])
        axis.plot(x, y, color=color, lw=1.8, marker=".", label=date)
        axis.fill_between(x, y - 1.96 * e, y + 1.96 * e, color=color, alpha=0.14)
    axis.set(xlabel="Wavelength (Angstrom)", ylabel="Relative F_lambda", title="J1329+0033: independent observing night, shared B/R wavelength range")
    axis.legend(frameon=False, fontsize=9)
    axis.grid(alpha=0.2)
    figure.text(0.5, 0.005, "100 A bins; each epoch normalized in 6500--7100 A. Second-night Z arm is entirely masked; full gri colour cannot be verified.", ha="center", fontsize=8)
    figure.tight_layout(rect=(0, 0.035, 1, 1))
    figure.savefig(output / "j1329_second_epoch_spectra.png", dpi=170)
    plt.close(figure)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
