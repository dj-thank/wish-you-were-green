#!/usr/bin/env python3
"""Validate all available nights of three additional colour candidates.

For each night, select the highest-SN_R exposure with some valid pixels in
each arm using the authors' inventory, before inspecting its colour. Keep
each night separate; neither repeated exposures nor shared gri anchors are
treated as independent calibration measurements.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import csv
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
from check_desi_second_epoch import calibration_quality, merge_segments, sha  # noqa: E402

SOURCES, OUT = HERE / "sources", HERE / "outputs"
LABELS = {"2482684508055379584": "J0111-0533", "1078624858218235776": "J1105+7247", "1691957732959636608": "J1252+7457"}
MANIFEST = SOURCES / "desi_additional_nights_manifest.json"
AIRGLOW = ((5577.34, 8), (5890, 6), (5896, 6), (6300.30, 8), (6363.78, 8))


def selected_exposures():
    data = json.loads((SOURCES / "candidate27_prior_rows.json").read_text())["candidates"]
    selected = []
    for sid in LABELS:
        by_night = {}
        for row in data[sid]["swan_exposures"]:
            valid = all(row[f"fractionMasked_{arm}"] != "" and float(row[f"fractionMasked_{arm}"]) < 1 for arm in "BRZ")
            if not valid or not row["SN_R"]:
                continue
            prev = by_night.get(row["NIGHT"])
            if prev is None or float(row["SN_R"]) > float(prev["SN_R"]):
                by_night[row["NIGHT"]] = row
        for night, row in sorted(by_night.items()):
            selected.append({"gaia_source_id": sid, "label": LABELS[sid], "exposure_inventory": row})
    return selected


def download_extract(cache):
    selected = selected_exposures()
    cache.mkdir(parents=True, exist_ok=True)

    def one_camera(task):
        candidate, arm = task
        row = candidate["exposure_inventory"]
        night, expid, fiber, targetid = row["NIGHT"], int(row["EXPOSURE"]), int(row["FIBER"]), int(row["TARGETID"])
        camera = fiber // 500
        filename = f"cframe-{arm}{camera}-{expid:08d}.fits.gz"
        url = f"https://data.desi.lbl.gov/public/dr1/spectro/redux/iron/exposures/{night}/{expid:08d}/{filename}"
        path = cache / filename
        if not path.exists():
            partial = path.with_suffix(path.suffix + ".partial")
            request = urllib.request.Request(url, headers={"User-Agent": "wish-you-were-green astronomy research"})
            with urllib.request.urlopen(request, timeout=60) as response, partial.open("wb") as output:
                for block in iter(lambda: response.read(1024 * 1024), b""):
                    output.write(block)
            partial.replace(path)
        with fits.open(path) as hdus:
            fiber_map = hdus["FIBERMAP"].data
            matches = np.flatnonzero((fiber_map["TARGETID"] == targetid) & (fiber_map["FIBER"] == fiber))
            if len(matches) != 1:
                raise RuntimeError(f"Expected one TARGETID/FIBER match in {filename}")
            idx = int(matches[0])
            header = hdus[0].header
            if str(header["NIGHT"]) != night or int(header["EXPID"]) != expid:
                raise RuntimeError(f"Wrong exposure header in {filename}")
            arrays = {f"{arm}_{key}": np.array(hdus[extension].data if key == "wave_A" else hdus[extension].data[idx]) for key, extension in (("wave_A", "WAVELENGTH"), ("flux", "FLUX"), ("ivar", "IVAR"), ("mask", "MASK"), ("resolution", "RESOLUTION"))}
            meta = {"arm": arm, "url": url, "full_file_sha256": sha(path), "full_file_bytes": path.stat().st_size, "fiber_map_row_0based": idx, "TARGETID": str(targetid), "FIBER": fiber, "NIGHT": night, "EXPID": expid, "DATE-OBS": header.get("DATE-OBS"), "EXPTIME": header.get("EXPTIME"), "BUNIT": hdus["FLUX"].header.get("BUNIT"), "pixels": len(arrays[f"{arm}_wave_A"]), "mask_nonzero": int(np.count_nonzero(arrays[f"{arm}_mask"])), "positive_ivar": int(np.count_nonzero(arrays[f"{arm}_ivar"] > 0))}
        print(json.dumps({"label": candidate["label"], "night": night, "arm": arm, "mask_nonzero": meta["mask_nonzero"], "pixels": meta["pixels"]}), flush=True)
        return arrays, meta

    # At most three full-camera HTTP transfers at a time.
    tasks = [(candidate, arm) for candidate in selected for arm in "brz"]
    with ThreadPoolExecutor(max_workers=3) as pool:
        products = list(pool.map(one_camera, tasks))
    manifests = []
    for offset, candidate in enumerate(selected):
        arrays, files = {}, []
        for payload, meta in products[offset * 3: offset * 3 + 3]:
            arrays.update(payload)
            files.append(meta)
        row = candidate["exposure_inventory"]
        path = SOURCES / f"desi_{candidate['gaia_source_id']}_{row['NIGHT']}_{row['EXPOSURE']}.npz"
        np.savez_compressed(path, **arrays)
        manifests.append({**candidate, "files": files, "selected_rows_path": str(path.relative_to(HERE)), "selected_rows_sha256": sha(path)})
    manifest = {"retrieval_date_utc": "2026-10-18", "selection_rule": "Within each night choose highest published SN_R among exposures with fractionMasked_B,R,Z < 1; retain all nights. Selection uses no computed colour.", "selection_source": "sources/candidate27_prior_rows.json", "archive": "DESI DR1 iron calibrated exposures", "data_model": "https://desidatamodel.readthedocs.io/en/latest/DESI_SPECTRO_REDUX/SPECPROD/exposures/NIGHT/EXPID/cframe-CAMERA-EXPID.html", "epochs": manifests}
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n")


def normalize_bins(wave, flux, ivar):
    rows = []
    for low in np.arange(4000, 7500, 100):
        mask = (wave >= low) & (wave < low + 100) & np.isfinite(flux) & np.isfinite(ivar) & (ivar > 0)
        for center, halfwidth in AIRGLOW:
            mask &= abs(wave - center) > halfwidth
        n = int(mask.sum())
        mean = float(np.mean(flux[mask])) if n else float("nan")
        err = float(np.sqrt(np.sum(1 / ivar[mask])) / n) if n else float("nan")
        rows.append({"wave_center_A": float(low + 50), "pixels": n, "mean_flux": mean, "mean_flux_error_uncorrelated": err})
    norm = float(np.median([r["mean_flux"] for r in rows if 6500 <= r["wave_center_A"] <= 7100]))
    for row in rows:
        row["relative_flux"] = row["mean_flux"] / norm
        row["relative_flux_error_uncorrelated"] = row["mean_flux_error_uncorrelated"] / norm
    return rows, norm


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--cache", type=Path, default=Path("/tmp/wish-green-desi-cframes"))
    args = parser.parse_args()
    if args.download:
        download_extract(args.cache)
    manifest = json.loads(MANIFEST.read_text())
    original = json.loads((SOURCES / "candidate27_prior_rows.json").read_text())["candidates"]
    result, bins = [], []
    for epoch in manifest["epochs"]:
        sid = epoch["gaia_source_id"]
        path = HERE / epoch["selected_rows_path"]
        if sha(path) != epoch["selected_rows_sha256"]:
            raise RuntimeError("Extracted exposure hash mismatch")
        phot = original[sid]["swan_external"][0]
        magnitudes = [float(phot[f"Pan-STARRS.{band}"]) for band in "gri"]
        errors = [float(phot[f"Pan-STARRS.{band}_error"]) for band in "gri"]
        sensitivity = []
        with np.load(path) as arrays:
            for br_join, rz_join in ((5780, 7570), (5765, 7530), (5795, 7610)):
                wave, flux, ivar = merge_segments(arrays, br_join, rz_join)
                raw = integrate_colour(wave, flux, ivar)
                calibrated, failure, quality = None, None, None
                try:
                    corrected, cal = recalibrate_gri(wave, flux, magnitudes, errors, system="panstarrs")
                    quality = calibration_quality(cal)
                    if not quality["accepted"]:
                        raise ValueError("Rejected calibration: " + "; ".join(quality["rejection_reasons"]))
                    correction = np.divide(corrected, flux, out=np.ones_like(flux), where=flux != 0)
                    calibrated = integrate_colour(wave, corrected, ivar / correction ** 2)
                    calibrated.update(cal)
                except ValueError as exc:
                    failure = str(exc)
                sensitivity.append({"blue_red_join_A": br_join, "red_z_join_A": rz_join, "raw": raw, "panstarrs": calibrated, "calibration_failure": failure, "calibration_quality_gate": quality, "accepted_calibrated_colour": calibrated is not None and calibrated["coverage_eligible"]})
            wave, flux, ivar = merge_segments(arrays, 5780, 7570)
            binned, norm = normalize_bins(wave, flux, ivar)
        exp = epoch["exposure_inventory"]
        bins.extend({"source_id": sid, "label": epoch["label"], "night": exp["NIGHT"], "exposure": exp["EXPOSURE"], **row} for row in binned)
        result.append({"source_id": sid, "label": epoch["label"], "night": exp["NIGHT"], "exposure": exp["EXPOSURE"], "exptime_s": exp["EXPTIME"], "observed_mjd": exp["MJD"], "photometry_source": "Swan2026 externalData_1.0; Pan-STARRS gri; identical anchors across nights", "magnitudes": magnitudes, "quoted_magnitude_errors": errors, "shape_normalization_6500_7100_A": norm, "arm_join_sensitivity": sensitivity})
    comparisons = []
    for sid in LABELS:
        epochs = [r for r in result if r["source_id"] == sid]
        a, b = [r["arm_join_sensitivity"][0] for r in epochs]
        def uv_distance(x, y):
            if x is None or y is None:
                return None
            return float(np.hypot(x["u1960"] - y["u1960"], x["v1960"] - y["v1960"]))
        comparisons.append({"source_id": sid, "label": LABELS[sid], "nights": [r["night"] for r in epochs], "raw_between_nights_uv": uv_distance(a["raw"], b["raw"]), "same_anchor_calibrated_between_nights_uv": uv_distance(a["panstarrs"], b["panstarrs"]), "calibrated_colour_coverage_eligible_each_night": [r["panstarrs"].get("coverage_eligible") if r["panstarrs"] else False for r in (a, b)]})
    summary = {"manifest": str(MANIFEST.relative_to(HERE)), "epochs": result, "comparisons": comparisons, "cautions": ["Selecting best SN_R within each night was determined before looking at the colour; all nights are retained.", "MASK=0 and finite positive IVAR are required; no camera is independently rescaled to enforce agreement.", "Same instrument and shared Pan-STARRS anchors leave correlated calibration errors; calibrated-night agreement is a stability diagnostic.", "Per-pixel uncertainties and plotted bands omit coherent calibration errors, inter-pixel covariance and uncertainty in the normalization. They are not total-error significance intervals.", "A shape discrepancy or colour difference is not an intrinsic-variability detection.", "Catalogued valid-arm fractions are only an initial selection; actual cframe masks are retained and rechecked."]}
    OUT.mkdir(exist_ok=True)
    summary["colour_pipeline_sha256"] = sha(ROOT / "colour_pipeline.py")
    summary["photometry_reference_sha256"] = sha(SOURCES / "candidate27_prior_rows.json")
    summary["calibration_gate"] = "Require maximum gri residual <0.15 mag and absolute tilt <0.25 mag/1000 A; numerical convergence alone is insufficient. Complete colour additionally requires spectrum coverage_eligible."
    (OUT / "desi_additional_nights_comparison.json").write_text(json.dumps(summary, indent=2) + "\n")
    compact = []
    for epoch in result:
        central = epoch["arm_join_sensitivity"][0]
        cal = central["panstarrs"] or {}
        compact.append({"source_id": epoch["source_id"], "label": epoch["label"], "night": epoch["night"], "exposure": epoch["exposure"], "raw_hex": central["raw"]["hex"], "raw_duv": central["raw"]["duv"], "shared_anchor_hex": cal.get("hex", ""), "shared_anchor_duv": cal.get("duv", ""), "coverage_eligible": cal.get("coverage_eligible", False), "accepted_calibrated_colour": central["accepted_calibrated_colour"], "passes_absolute_duv_0_01_point_estimate": abs(cal.get("duv", 0)) > .01, "uv_error_max_uncorrelated_pixels_only": cal.get("uv_stat_error_max", ""), "negative_visible_flux_fraction": cal.get("visible_negative_fraction", ""), "tilt_mag_per_1000A": cal.get("cal_tilt_mag_per_1000A", ""), "max_gri_fit_residual_mag": cal.get("cal_max_residual_mag", ""), "join_duv_min": min((r["panstarrs"]["duv"] for r in epoch["arm_join_sensitivity"] if r["panstarrs"]), default=None), "join_duv_max": max((r["panstarrs"]["duv"] for r in epoch["arm_join_sensitivity"] if r["panstarrs"]), default=None)})
    with (OUT / "desi_additional_nights_summary.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(compact[0])); writer.writeheader(); writer.writerows(compact)
    with (OUT / "desi_additional_nights_common_bins.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(bins[0])); writer.writeheader(); writer.writerows(bins)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(3, 1, figsize=(13, 13), sharex=True)
    for ax, sid in zip(axes, LABELS):
        for night in sorted({r["night"] for r in bins if r["source_id"] == sid}):
            rows = [r for r in bins if r["source_id"] == sid and r["night"] == night]
            x = np.array([r["wave_center_A"] for r in rows]); y = np.array([r["relative_flux"] for r in rows]); e = np.array([r["relative_flux_error_uncorrelated"] for r in rows])
            line, = ax.plot(x, y, marker="o", markersize=3, label=f"NIGHT {night}")
            ax.fill_between(x, y-e, y+e, alpha=.12, color=line.get_color())
        ax.set_title(LABELS[sid]); ax.set_ylabel("Relative F_lambda"); ax.grid(alpha=.2); ax.legend()
    axes[-1].set_xlabel("Wavelength (Angstrom)")
    fig.suptitle("Additional DESI nights: shared wavelength range, no spectral tilt fitted", fontsize=16)
    fig.text(.5, .007, "100 A bins; each epoch normalized over 6500--7100 A; shaded bands contain uncorrelated pixel noise only", ha="center", fontsize=10)
    fig.tight_layout(rect=(0,.023,1,.97))
    fig.savefig(OUT / "desi_additional_nights_spectra.png", dpi=150)
    plt.close(fig)
    print(json.dumps(comparisons, indent=2))


if __name__ == "__main__":
    main()
