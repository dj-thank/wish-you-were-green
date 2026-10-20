#!/usr/bin/env python3
"""Offline, coarse residual diagnostics of published fitted figure curves.

No native model spectrum, uncertainty array, abundance fit or independent
observation is claimed. Curves retain the authors' relative Fnu normalization.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/wish-green-model-validation-mpl")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HEADS = {
    "818833831355548928": "J0913+4434", "3204436719718449280": "J0429-0354",
    "1078624858218235776": "J1105+7247", "3711047662972690688": "J1329+0033",
    "3638333660492606976": "J1323-0129"}
WINDOWS = {
    "blue_Ca_region": (3850., 4350.), "C2_4700_region": (4600., 4800.),
    "Mg_C2_5200_region": (5000., 5350.), "C2_5600_region": (5500., 5650.),
    "Na_C2_5900_region": (5700., 6100.), "red_reference": (6200., 6500.)}
EDGES = np.arange(3800., 7300.1, 50.)
GRID = np.arange(3800., 7301., 1.)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def resample(points, target, shift=0.):
    axis = target["axis"]
    wavelength = np.polyval(axis["x_to_wavelength_polynomial"], points[:, 0]) + shift
    flux = np.polyval(axis["y_to_relative_fnu_polynomial"], points[:, 1])
    # Vertical segments can share x because the graphic is quantized.
    # Their median y specifies the coarse plotted trace, not a native pixel.
    unique = pd.DataFrame({"x": wavelength, "y": flux}).groupby("x", sort=True).y.median()
    return np.interp(GRID, unique.index.to_numpy(), unique.to_numpy(), left=np.nan, right=np.nan)


def bins(flux):
    result, count = [], []
    for lo, hi in zip(EDGES[:-1], EDGES[1:]):
        f = flux[(GRID >= lo) & (GRID < hi)]
        valid = np.isfinite(f)
        count.append(int(valid.sum()))
        result.append(float(np.median(f[valid])) if valid.all() else np.nan)
    return np.array(result), np.array(count)


def summarize_wave_windows(center, observed, model, reference):
    result = {}
    difference = (observed-model)/reference
    for name, (lo, hi) in WINDOWS.items():
        selected = (center >= lo) & (center < hi)
        valid = selected & np.isfinite(difference)
        result[name+"_mean_residual_over_reference"] = float(np.mean(difference[valid])) if valid.any() else np.nan
        result[name+"_complete_bins"] = int(valid.sum())
        result[name+"_expected_bins"] = int(selected.sum())
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    root = args.root.resolve(); base = root/"research/model_validation"
    manifest_path = base/"sources/published_curve_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    prior_path = root/manifest["selection_evidence"]["candidate_input_path"]
    assert sha(prior_path) == manifest["selection_evidence"]["candidate_input_sha256"]
    ids = json.loads(prior_path.read_text())["source_ids"]
    targets = {r["source_id"]: r for r in manifest["selected_pages"]}
    assert set(ids)-set(targets) == set(manifest["selection_evidence"]["not_available_source_ids"])
    assert len(ids) == 27 and len(targets) == 25
    center = (EDGES[:-1]+EDGES[1:])/2
    rows, all_bins, inputs = [], [], {str(manifest_path.relative_to(root)): sha(manifest_path), str(prior_path.relative_to(root)): sha(prior_path)}
    displays = {}
    for sid in ids:
        if sid not in targets:
            rows.append({"source_id": sid, "name": sid, "status": "no_exact_Kilic_fit_in_fixed_input",
                         "missing_reason": "No exact-ID Kilic 2026 table row in the fixed initial 27 input"})
            continue
        target = targets[sid]
        assert target["gaia_ocr_exact_after_whitespace_removal"]
        assert sid in "".join(target["label_ocr"].split())
        axis = target["axis"]
        assert axis["x_tick_fit_max_error_angstrom"] < .6
        assert axis["y_tick_fit_max_error_relative_fnu"] < .001
        path = root/target["compact_path"]
        assert sha(path) == target["compact_sha256"], path
        inputs[str(path.relative_to(root))] = sha(path)
        with np.load(path, allow_pickle=False) as npz:
            points = {kind: npz[kind+"_pdf_xy"].astype(float) for kind in ("observed", "model")}
            for kind in points:
                assert len(points[kind]) == target["vector_diagnostics"][kind]["vertices"]
                assert np.all(np.isfinite(points[kind]))
                assert target["vector_diagnostics"][kind]["max_join_gap_angstrom"] < .01
                segments = npz[kind+"_segment_id"]
                assert len(segments) == len(points[kind]) and len(np.unique(segments)) == target["vector_diagnostics"][kind]["path_segments"]
        observed, observed_n = bins(resample(points["observed"], target))
        model, model_n = bins(resample(points["model"], target))
        norm_window = (center >= 6200) & (center < 6500)
        assert np.all(np.isfinite(model[norm_window]))
        reference = float(np.median(model[norm_window]))
        assert reference > 0
        diagnostic = summarize_wave_windows(center, observed, model, reference)
        # Stress the graphic reconstruction, not measurement uncertainty.
        # Opposite one-quantum vertical shifts give +/- 2*dy residual;
        # shift the model wavelength by +/- (2*dx + axis tick-fit error).
        dw = 2*axis["one_graphic_quantum_angstrom"]+axis["x_tick_fit_max_error_angstrom"]
        dy = 2*axis["one_graphic_quantum_relative_fnu"]
        stress = []
        for shift in (-dw, 0., dw):
            shifted_model, _ = bins(resample(points["model"], target, shift=shift))
            for delta in (-dy, 0., dy):
                stress.append(summarize_wave_windows(center, observed+delta, shifted_model, reference))
        for name in WINDOWS:
            key = name+"_mean_residual_over_reference"
            finite = [r[key] for r in stress if np.isfinite(r[key])]
            diagnostic[name+"_graphic_stress_min"] = min(finite) if finite else np.nan
            diagnostic[name+"_graphic_stress_max"] = max(finite) if finite else np.nan
        common = (center >= 3850) & (center < 6500) & np.isfinite(observed) & np.isfinite(model)
        row = {"source_id": sid, "name": HEADS.get(sid, target["name"]), "spectral_type": target["spectral_type"],
               "status": "published_figure_diagnostic", "missing_reason": "", "archive": target["archive"], "page_1based": target["page_1based"],
               "model_red_reference_relative_fnu": reference, "common_complete_50A_bins_3850_6500": int(common.sum()),
               "median_abs_residual_over_reference_3850_6500": float(np.median(np.abs(observed[common]-model[common]))/reference),
               "graphic_stress_wavelength_shift_angstrom": dw, "graphic_stress_residual_shift_relative_fnu": dy,
               "magnetic_classification_not_magnetic_model": "H" in target["spectral_type"], **diagnostic}
        rows.append(row)
        displays[sid] = (center, observed/reference, model/reference, row)
        for n, x in enumerate(center):
            all_bins.append({"source_id": sid, "name": row["name"], "bin_low_angstrom": EDGES[n], "bin_high_angstrom": EDGES[n+1],
                             "observed_resampled_points": observed_n[n], "model_resampled_points": model_n[n],
                             "complete_for_both": bool(np.isfinite(observed[n]) and np.isfinite(model[n])),
                             "observed_median_relative_fnu": observed[n], "model_median_relative_fnu": model[n],
                             "observed_minus_model_over_red_reference": (observed[n]-model[n])/reference})
    frame = pd.DataFrame(rows)
    frame.to_csv(base/"published_curve_residuals.csv", index=False)
    pd.DataFrame(all_bins).to_csv(base/"published_curve_50A_bins.csv", index=False)
    summary = {"created_utc": datetime.now(timezone.utc).isoformat(), "script_sha256": sha(Path(__file__)), "input_sha256": inputs,
               "candidate_input_count": len(ids), "figure_available_count": len(targets), "retained_unavailable_count": len(ids)-len(targets),
               "bin_width_angstrom": 50., "all_bins": len(all_bins), "windows_angstrom": WINDOWS,
               "method": "Preserve authors plotted relative Fnu and common normalization. Median-resample duplicate vector x positions; interpolate drawn paths at 1 Angstrom; take medians in complete 50 Angstrom bins. Divide observed-minus-model differences by the median published model in 6200-6500 Angstrom, without refitting any scale or composition.",
               "graphic_sensitivity": "The min/max columns cover 9 finite reconstruction stresses (relative wavelength shift and opposite vertical quantization shifts). They are not measurement uncertainty bounds, confidence intervals or a replacement for native flux/ivar/mask/resolution data.",
               "scope": "Published in-sample fitted curves and smoothed observations only. These are not native atmospheric spectra, independent observations or held-out spectral tests. No p-values, fitted abundances, equivalent widths or complete visible-colour integration are inferred. Wavelength-window names are locations of potentially blended features, not element-specific abundance measurements.",
               "citation": manifest["paper_url"], "archive_doi": manifest["archive_doi"], "license": manifest["license"],
               "verification": "PASS: all 27 IDs retained; 25 exact page IDs; input and vector hashes; axis roundoff; monotone segments; complete reference bins; all 9 reconstruction stresses evaluated."}
    (base/"published_curve_summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False)+"\n")

    fig, axes = plt.subplots(5, 2, figsize=(12, 12), gridspec_kw={"width_ratios": [3, 2]})
    for i, (sid, name) in enumerate(HEADS.items()):
        x, observed, model, row = displays[sid]
        ax, residual_ax = axes[i]
        ax.plot(x, observed, color=".25", lw=1., label="Published observation, 50 A bins")
        ax.plot(x, model, color="#CC3311", lw=1.3, label="Published fitted model, 50 A bins")
        ax.set_ylabel("Relative Fnu / red reference")
        ax.set_title(name+"  ("+row["spectral_type"]+")", fontsize=10, loc="left")
        ax.set_xlim(3800, 7300 if row["archive"].endswith("DZ.pdf") else 6750)
        ax.axvspan(3850, 4350, color="#0072B2", alpha=.07)
        ax.axvspan(5700, 6100, color="#EECC66", alpha=.13)
        residual_ax.plot(x, observed-model, color="#0072B2", lw=1.)
        residual_ax.axhline(0, color=".4", lw=.8)
        residual_ax.axvspan(3850, 4350, color="#0072B2", alpha=.07)
        residual_ax.axvspan(5700, 6100, color="#EECC66", alpha=.13)
        residual_ax.set_xlim(ax.get_xlim())
        residual_ax.set_ylabel("(Observed - model) / reference")
        residual_ax.set_title("Published-fit residual; no refit", fontsize=10)
        if i == 0:
            ax.legend(fontsize=7, loc="upper left")
        if i == 4:
            ax.set_xlabel("Plotted wavelength [Angstrom]"); residual_ax.set_xlabel("Plotted wavelength [Angstrom]")
    fig.suptitle("Where does a published tailored atmosphere fit leave residuals?", fontsize=13)
    fig.text(.5, .012, "Kilic et al. (2026), Zenodo 20775938 (CC BY 4.0); selected PDF vector paths, reconstructed and binned here.\nThese are fitted figure curves, not native spectral models or independent validation. Shading marks wavelength windows, not isolated elements.", ha="center", fontsize=8)
    fig.tight_layout(rect=[0, .045, 1, .975]); fig.savefig(base/"published_curve_headlines.png", dpi=160); plt.close(fig)
    # A complete contact sheet makes the all-target extraction reviewable,
    # including objects outside the five headline examples.
    fig, axes = plt.subplots(5, 5, figsize=(17, 12))
    ordered = sorted(targets, key=lambda sid: targets[sid]["name"])
    for ax, sid in zip(axes.flat, ordered):
        x, observed, model, row = displays[sid]
        ax.plot(x, observed, color=".25", lw=.9)
        ax.plot(x, model, color="#CC3311", lw=1.)
        ax.set_title(targets[sid]["name"].removeprefix("WDJ")+"  "+row["spectral_type"], fontsize=8)
        ax.set_xlim(3800, 7300); ax.set_xticks([4000, 5500, 7000]); ax.tick_params(labelsize=7)
    fig.supxlabel("Plotted wavelength [Angstrom]", fontsize=10)
    fig.supylabel("Relative Fnu / model red reference", fontsize=10)
    fig.suptitle("All 25 published fits: black = plotted observation; red = fitted model (50 Angstrom bins)", fontsize=12)
    fig.text(.5, .005, "Kilic et al. (2026), Zenodo 20775938, CC BY 4.0; vector extraction and binning here. In-sample figure diagnostics; no native model or independent validation.", ha="center", fontsize=8)
    fig.tight_layout(rect=[.01, .022, 1, .975]); fig.savefig(base/"published_curve_all25.png", dpi=160); plt.close(fig)
    print("PASS published-curve diagnostics: 25/27 exact-ID figures, 50 Angstrom bins, 9 graphic sensitivity cases per target; no native-model inference")
    heads = frame.loc[frame.source_id.isin(HEADS)]
    print(heads[["name", "blue_Ca_region_mean_residual_over_reference", "Na_C2_5900_region_mean_residual_over_reference", "median_abs_residual_over_reference_3850_6500"]].to_string(index=False))


if __name__ == "__main__":
    main()
