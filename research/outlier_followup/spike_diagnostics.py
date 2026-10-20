#!/usr/bin/env python3
"""Examine three visually flagged narrow peaks on the retained native grid.

No peak is removed from the production screen. Window deletion/re-integration
is an explicit interpolation sensitivity experiment, not an estimated true
spectrum, a new line identification or a significance test.
"""
from __future__ import annotations
from datetime import datetime, timezone
import gzip
import json
import os
from pathlib import Path
import sys

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MPLCONFIGDIR", "/tmp/wish-green-spike-mpl")
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import colour_pipeline as colour
from research.outlier_followup.build_followup import frozen_inputs, verified_arrays, relative, sha

HERE = Path(__file__).resolve().parent
OUT = HERE / "spike_diagnostics"
# The last two initial visual wavelength estimates were imprecise. The native
# samples identify the flagged maxima at 7822.4 and 6345.6 A, respectively.
# Freeze windows around those actual features before any deletion experiment.
SELECTION = ((1883, 5850., 25.), (1502, 7822.4, 30.), (2647, 6345.6, 30.))


def main():
    OUT.mkdir(exist_ok=True)
    table = pd.read_csv(HERE / "record_review.csv.gz", dtype={"source_id": str}, low_memory=False).set_index("row_index", drop=False)
    inputs = frozen_inputs(); results = []
    fig, axes = plt.subplots(3, 2, figsize=(13, 10), layout="constrained")
    for i, (index, center, width) in enumerate(SELECTION):
        row = table.loc[index]
        require(row.plot_status == "plotted_verified_flambda" and row.kind == "DESI", "Selected native spectrum is not eligible DESI")
        origin, record = inputs[index]
        raw = relative(record["raw_path"])
        require(sha(raw) == record["sha256"], "Source bytes changed")
        archived = OUT / f"row_{index}_original.csv.gz"
        archived.write_bytes(gzip.compress(raw.read_bytes(), mtime=0))
        wave, flux, ivar, unit = verified_arrays(inputs[index])
        if row.calibrated == True:
            correction = 10 ** (-.4 * (row.cal_offset_mag + row.cal_tilt_mag_per_1000A * (wave - 6200) / 1000))
            flux = flux * correction; ivar = ivar / correction ** 2
        wave, flux, ivar = colour.clean_spectrum(wave, flux, ivar, mask_sky=True)
        current = colour.integrate_colour(wave, flux, ivar, mask_sky=False)
        require(np.hypot(current["u1960"] - row.u1960, current["v1960"] - row.v1960) < 1e-7, "Current colour mismatch")
        search = abs(wave - center) <= width
        peak = np.flatnonzero(search)[np.argmax(flux[search])]
        position = float(wave[peak])
        local = abs(wave - position) <= 50
        side = ((wave >= position - 50) & (wave <= position - 20)) | ((wave >= position + 20) & (wave <= position + 50))
        continuum = float(np.median(flux[side]))
        norm = float(np.median(flux[(wave >= 5200) & (wave <= 5500)]))
        sigma = 1 / np.sqrt(ivar)
        experiments = []
        for label, keep in (("one_peak_sample", np.arange(len(wave)) != peak),
                            ("peak_plus_minus_4_A", abs(wave - position) > 4),
                            ("peak_plus_minus_10_A", abs(wave - position) > 10)):
            changed = colour.integrate_colour(wave[keep], flux[keep], ivar[keep], mask_sky=False)
            experiments.append({"deletion_window": label, "excluded_valid_samples": int(np.sum(~keep)),
                                "interpolated_colour_metrics": changed,
                                "delta_uv": float(np.hypot(changed["u1960"] - current["u1960"], changed["v1960"] - current["v1960"])),
                                "delta_duv": float(changed["duv"] - current["duv"])})
        result = {"row_index": index, "source_id": row.source_id, "entity_id": row.entity_id,
                  "source_url": record["source_url"], "raw_sha256": record["sha256"],
                  "lossless_raw_path": archived.name, "lossless_raw_sha256": sha(archived),
                  "source_size_bytes": raw.stat().st_size, "calibrated": bool(row.calibrated == True),
                  "selection_window_center_A": center, "selection_halfwidth_A": width,
                  "peak_wavelength_A": position, "peak_flux_over_display_anchor": float(flux[peak] / norm),
                  "peak_sigma_over_display_anchor": float(sigma[peak] / norm),
                  "sideband_median_over_display_anchor": continuum / norm,
                  "peak_excess_over_single_sample_sigma": float((flux[peak] - continuum) / sigma[peak]),
                  "single_sample_ratio_limit": "Descriptive only: fitted continuum uncertainty, look-elsewhere selection, resampling covariance and systematics are not included; not a calibrated line significance",
                  "current_metrics": current, "sensitivity_experiments": experiments,
                  "mask_limit": "MWDD flag is not interpreted as native DESI MASK. Original camera/CCD bit masks are not present in this export.",
                  "disposition": "Retain original spectrum and current colour. Feature origin remains unresolved; no production masking rule changed."}
        results.append(result)
        visible = (wave >= 3600) & (wave <= 8300)
        axes[i, 0].plot(wave[visible] / 10, flux[visible] / norm, color="#166b8c", lw=.5)
        axes[i, 0].axvspan((position - 10) / 10, (position + 10) / 10, alpha=.2, color="#aa5133")
        axes[i, 0].set_title(f"{row.source_id}: DESI row {index}\nNative signed F-lambda; selected interval marked", fontsize=10)
        axes[i, 0].set(xlabel="Wavelength (nm)", ylabel="Relative F-lambda", xlim=(360, 830))
        axes[i, 1].errorbar(wave[local], flux[local] / norm, yerr=sigma[local] / norm, fmt=".-", color="#166b8c", ms=3, lw=.7, elinewidth=.6)
        axes[i, 1].axhline(continuum / norm, color="#777777", lw=.8, ls="--", label="Sideband median")
        axes[i, 1].axvline(position, color="#aa5133", lw=.8)
        axes[i, 1].set_title(f"Peak at {position:.1f} Å; supplied pixel error\nNo line identity or intrinsic variability established", fontsize=10)
        axes[i, 1].set(xlabel="Wavelength (Å)", ylabel="Relative F-lambda", xlim=(position - 50, position + 50))
        axes[i, 1].legend(fontsize=8)
        for ax in axes[i]: ax.grid(alpha=.15)
    fig.suptitle("Three narrow visual outliers: original samples and window-sensitivity checks", fontsize=14)
    fig.savefig(OUT / "native_peak_checks.png", dpi=165)
    plt.close(fig)
    report = {"created_utc": datetime.now(timezone.utc).isoformat(), "selection": "Three peaks flagged by actual full-range/zoom visual inspection, before this numerical check. Coarse visual wavelength estimates for rows 1502 and 2647 were corrected from the native arrays to 7822.4 and 6345.6 A before window-sensitivity integration.",
              "method": "Current accepted calibration and finite/IVAR/standard narrow-sky mask; locate maximum in named visual window; inspect native samples and supplied errors; repeat colour integration after named deletions",
              "limits": "Deletion uses interpolation across a newly missing interval; the missing stellar flux is not measured. The experiment does not define the correct removal window, a line significance, a physical cause or a revised production colour.",
              "input_sha256": {str((HERE / "record_review.csv.gz").relative_to(ROOT)): sha(HERE / "record_review.csv.gz")},
              "code_sha256": sha(Path(__file__)), "results": results}
    (OUT / "native_peak_results.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    for result in results:
        print(result["row_index"], result["peak_wavelength_A"], "peak-minus-sideband / supplied sigma", result["peak_excess_over_single_sample_sigma"], "max sensitivity delta_uv", max(r["delta_uv"] for r in result["sensitivity_experiments"]), flush=True)


def require(condition, message):
    if not condition:
        raise AssertionError(message)


if __name__ == "__main__":
    main()
