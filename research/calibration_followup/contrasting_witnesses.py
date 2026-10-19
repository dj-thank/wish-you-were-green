#!/usr/bin/env python3
"""Concrete, strictly opposite channel-order witnesses for J0429.

Both spectra use the same saved DESI pixels and observed PS1 griz boxes.
They demonstrate non-uniqueness of this measurement-constrained shape model;
neither is asserted to be the true corrected stellar spectrum.
"""
from __future__ import annotations
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from research.calibration_followup.photometric_feasibility import (
    HERE, Problem, load_inputs, prepare, filter_metadata, sha,
)
import numpy as np
import matplotlib.pyplot as plt

SID = "3204436719718449280"
SPACING = 800
REQUIRED_MARGIN = .005


def main():
    cohort, derivatives = load_inputs()
    row = cohort[cohort.source_id.eq(SID)].iloc[0].to_dict()
    filterset = [filter_metadata(b)[0] for b in "griz"]
    wave, flux, baseline, obs, err, meta = prepare(row, derivatives[SID], filterset)
    problem = Problem(wave, flux, baseline, filterset, SPACING)
    solutions = {"green": problem.solve(obs, err, "griz", 1, "green_closed", REQUIRED_MARGIN),
                 "red_above_green": problem.solve(obs, err, "griz", 1, "G_le_R", REQUIRED_MARGIN)}
    arrays = {"wavelength_angstrom": wave, "baseline_flux_lambda": flux,
              "spline_knots_angstrom": problem.knots}
    for label, solution in solutions.items():
        if not solution["success"] or solution["continuous_witness_supremum"] > .05:
            raise AssertionError("Specified 5% contrasting-witness experiment was unsuccessful")
        a = np.asarray(solution["spline_coefficients"])
        distortion = problem.basis @ a
        arrays[label + "_fractional_distortion"] = distortion
        arrays[label + "_flux_lambda"] = flux * (1 + distortion)
    path = HERE / "J0429_contrasting_griz_witnesses.npz"
    np.savez_compressed(path, **arrays)
    result = {
        "created_utc": datetime.now(timezone.utc).isoformat(), "source_id": SID,
        "design": "Fixed 800 A cubic splines; observed PS1 griz each within one published magnitude error; no extra error floor; positive multiplicative spectral changes. Require G-R and G-B >= 0.005 of baseline max(abs(RGB)) for the green witness, and R-G >= 0.005 on the same scale for the opposite witness.",
        "interpretation": "Two explicit strict channel-order possibilities inside a 5% shape budget; neither is an inferred correction, posterior, atmosphere model or independent observation",
        "cohort_metadata": meta, "spacing_A": SPACING, "required_normalized_margin": REQUIRED_MARGIN,
        "code_sha256": {str(p.relative_to(ROOT)): sha(p) for p in (Path(__file__), HERE / "photometric_feasibility.py")},
        "array_path": path.name, "array_sha256": sha(path), "solutions": solutions,
    }
    (HERE / "contrasting_witnesses.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    fig, axes = plt.subplots(1, 3, figsize=(14, 4), layout="constrained")
    styles = {"green": ("#287f59", "Green channel highest"), "red_above_green": ("#ad4e35", "Red above green")}
    for label, (color, name) in styles.items():
        solution = solutions[label]
        axes[0].plot(wave / 10, 100 * arrays[label + "_fractional_distortion"], color=color, label=name, lw=1.4)
        offsets = np.asarray(solution["synthetic_mag_griz"]) - obs
        axes[1].plot(np.arange(4), offsets, marker="o", color=color, label=name)
        channel_differences = solution["normalized_channel_differences"]
        axes[2].plot(np.arange(2), 100 * np.array([channel_differences["G-R"], channel_differences["G-B"]]), marker="o", color=color, label=name)
    axes[0].axhspan(-5, 5, color="#bbbbbb", alpha=.15)
    axes[0].axhline(0, color="#888888", lw=.6)
    axes[0].set(xlabel="Wavelength (nm)", ylabel="Change from saved spectrum (%)", xlim=(360, 983), ylim=(-5.3, 5.3))
    axes[0].set_title("Both remain inside the 5% budget")
    axes[1].errorbar(np.arange(4), np.zeros(4), yerr=err, fmt="none", color="#444444", capsize=6, lw=2, label="Published error box")
    axes[1].set(xticks=np.arange(4), xticklabels=list("griz"), ylabel="Synthetic minus observed magnitude")
    axes[1].set_title("Both satisfy the same measured bands")
    axes[1].axhline(0, color="#888888", lw=.6)
    axes[2].set(xticks=np.arange(2), xticklabels=["G - R", "G - B"], ylabel="Difference / baseline max RGB (%)")
    axes[2].set_title("Strictly different channel ordering")
    axes[2].axhline(0, color="#444444", lw=.8)
    for ax in axes:
        ax.grid(alpha=.16)
    axes[0].legend(fontsize=8); axes[1].legend(fontsize=8)
    fig.suptitle("J0429-0354: observed griz agreement does not uniquely determine channel ordering\nConditional constructed witnesses; not two observations or physical atmosphere fits", fontsize=13)
    fig.savefig(HERE / "J0429_contrasting_griz_witnesses.png", dpi=180)
    fig.savefig(HERE / "J0429_contrasting_griz_witnesses.svg")
    plt.close(fig)
    for label, value in solutions.items():
        print(label, value["continuous_witness_supremum"], value["metrics"]["green_channel_margin"], value["metrics"]["hex"], flush=True)


if __name__ == "__main__":
    main()
