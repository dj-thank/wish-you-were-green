#!/usr/bin/env python3
"""Add an explicitly clipped continuum view beside full-range review plots.

No data are edited or excluded. The original 126 all-extrema pages are retained.
This detects displays dominated by unusually large native ranges or supplied
errors, and preserves compact, source-hashed display arrays for offline review.
"""
from __future__ import annotations
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MPLCONFIGDIR", "/tmp/wish-green-display-mpl")
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from research.outlier_followup.build_followup import frozen_inputs, spectrum_for_panel, sha

HERE = Path(__file__).resolve().parent
OUT = HERE / "display_diagnostics"
RATIO = 8.
COLORS = {"DESI": "#166b8c", "SDSS": "#9252a0", "Gaia_XP": "#c47919"}


def main():
    OUT.mkdir(exist_ok=True)
    index = pd.read_csv(HERE / "contact_sheet_index.csv", dtype={"source_id": str}).fillna("")
    records = pd.read_csv(HERE / "record_review.csv.gz", dtype={"source_id": str}, low_memory=False)
    inputs = frozen_inputs()
    metrics, selected, compact_arrays = [], [], {}
    for entity, group in records[records.plot_status.eq("plotted_verified_flambda")].groupby("entity_id", sort=True):
        entry = index[index.entity_id.eq(entity)].iloc[0].to_dict()
        curves, all_means, extent = [], [], [0., 1.]
        for row in group.itertuples():
            bins, diagnostic = spectrum_for_panel(inputs[row.row_index], row)
            wave, mean, low, high, error = bins
            all_means.extend(mean[np.isfinite(mean)])
            for values in (low, high, mean - error, mean + error):
                extent.extend(values[np.isfinite(values)])
            curves.append((row, bins, diagnostic))
        qlo, qhi = np.quantile(all_means, [.02, .98])
        qlo, qhi = min(0., qlo), max(1., qhi)
        typical_span = max(qhi - qlo, 1e-6)
        full_lo, full_hi = min(extent), max(extent)
        ratio = (full_hi - full_lo) / typical_span
        zoom_lo, zoom_hi = qlo - .1 * typical_span, qhi + .1 * typical_span
        item = {"entity_id": entity, "source_id": entry["source_id"], "followup_index": int(entry["followup_index"]),
                "original_page": int(entry["page"]), "original_panel": int(entry["panel"]),
                "contact_sheet": entry["contact_sheet"], "contact_sheet_sha256": entry["contact_sheet_sha256"],
                "full_y_low": full_lo, "full_y_high": full_hi, "mean_2pct": qlo, "mean_98pct": qhi,
                "full_to_typical_span_ratio": ratio, "zoom_y_low": zoom_lo, "zoom_y_high": zoom_hi,
                "zoom_selected": bool(ratio >= RATIO), "rows": "|".join(str(row.row_index) for row, _, _ in curves)}
        metrics.append(item)
        if ratio >= RATIO:
            item["display_curves"] = []
            for row, bins, diagnostic in curves:
                wave, mean, low, high, error = bins
                key = f"row_{row.row_index}"
                compact_arrays[key] = np.vstack(bins)
                item["display_curves"].append({
                    "row_index": int(row.row_index), "kind": row.kind, "source_url": row.source_url,
                    "raw_sha256": row.sha256, "calibrated": bool(row.calibrated == True),
                    "archive_origin": row.archive_origin, "array_key": key,
                    "native_minimum": float(diagnostic["native_normalized_min"]),
                    "native_maximum": float(diagnostic["native_normalized_max"]),
                    "largest_bin_error": float(np.nanmax(error)) if np.isfinite(error).any() else None,
                    "native_range_bins_outside_zoom": int(np.sum((low < zoom_lo) | (high > zoom_hi))),
                    "mean_bins_outside_zoom": int(np.sum((mean < zoom_lo) | (mean > zoom_hi))),
                    "error_bins_outside_zoom": int(np.sum((mean - error < zoom_lo) | (mean + error > zoom_hi))),
                    "recomputed_current_delta_uv": diagnostic["current_recomputed_delta_uv"],
                })
            selected.append(item)
        if len(metrics) % 200 == 0:
            print("Scanned", len(metrics), "entities; zoom cases", len(selected), flush=True)
    selected.sort(key=lambda r: r["followup_index"])
    # Only flat scalar columns enter the complete automatic screening table.
    pd.DataFrame([{k: v for k, v in r.items() if k != "display_curves"} for r in metrics]).to_csv(OUT / "display_range_screen.csv", index=False)
    np.savez_compressed(OUT / "selected_display_arrays.npz", **compact_arrays)
    pages = []
    for first in range(0, len(selected), 4):
        block = selected[first:first + 4]
        fig, axes = plt.subplots(len(block), 2, figsize=(14, 3.3 * len(block)), layout="constrained", squeeze=False)
        page_no = first // 4 + 1
        for j, item in enumerate(block):
            for curve in item["display_curves"]:
                wave, mean, low, high, error = compact_arrays[curve["array_key"]]
                color = COLORS[curve["kind"]]
                for ax in axes[j]:
                    ax.vlines(wave, low, high, color=color, lw=.55, alpha=.22)
                    ax.plot(wave, mean, color=color, lw=1., label=f"{curve['kind']} row {curve['row_index']}")
                    if np.isfinite(error).any():
                        ax.fill_between(wave, mean - error, mean + error, color=color, alpha=.15, lw=0)
            span = item["full_y_high"] - item["full_y_low"]
            axes[j, 0].set_ylim(item["full_y_low"] - .06 * span, item["full_y_high"] + .06 * span)
            axes[j, 1].set_ylim(item["zoom_y_low"], item["zoom_y_high"])
            label = f"{item['followup_index'] + 1:04d}  {item['source_id']}  (original page {item['original_page']}, panel {item['original_panel']})"
            axes[j, 0].set_title(label + "\nAll native flux ranges and supplied bin errors", fontsize=9)
            axes[j, 1].set_title(f"Continuum zoom; full/typical span = {item['full_to_typical_span_ratio']:.1f}\nClipped ranges and errors remain in the left view", fontsize=9)
            for ax in axes[j]:
                ax.set_xlim(360, 830); ax.set_xlabel("Wavelength (nm)"); ax.set_ylabel("Relative F-lambda")
                ax.axhline(0, color="#777777", lw=.5); ax.grid(alpha=.15); ax.legend(fontsize=7)
            item.update(zoom_page=page_no, zoom_row=j + 1)
        fig.suptitle("Supplemental display audit: full range and continuum detail\n20 Å means, native extrema, supplied independent-pixel bin errors; no data removed", fontsize=13)
        path = OUT / f"zoom_{page_no:02d}.png"
        fig.savefig(path, dpi=145)
        plt.close(fig)
        pages.append({"path": path.name, "sha256": sha(path), "entities": [r["entity_id"] for r in block]})
    manifest = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "All 1684 newly reviewed entities with current eligible spectra; original 126 pages unchanged",
        "selection": "Full range including native min/max and supplied bin errors divided by the 2nd-to-98th percentile span of all binned means, expanded to include 0 and 1; select ratio >= 8",
        "zoom_policy": "2nd-to-98th percentile binned-mean limits including 0 and 1, plus 10% margin; explicitly clipped auxiliary display only; full range retained alongside",
        "n_entities_scanned": len(metrics), "n_selected": len(selected), "threshold": RATIO,
        "scientific_limit": "A display diagnostic, not a new data-quality exclusion, physical classification or evidence that a flux excursion is intrinsic",
        "input_sha256": {str(p.relative_to(ROOT)): sha(p) for p in (HERE / "contact_sheet_index.csv", HERE / "record_review.csv.gz", Path(__file__), HERE / "build_followup.py")},
        "display_arrays_sha256": sha(OUT / "selected_display_arrays.npz"),
        "display_array_rows": ["wavelength_nm", "mean", "native_min", "native_max", "supplied_independent_bin_error"],
        "pages": pages, "selected_entities": selected,
        "review_state": "requires_actual_visual_review_of_saved_zoom_pages",
    }
    (OUT / "display_manifest.json").write_text(json.dumps(manifest, indent=2, allow_nan=False) + "\n")
    print("DONE", len(metrics), "entities", len(selected), "zoom cases", len(pages), "pages", flush=True)


if __name__ == "__main__":
    main()
