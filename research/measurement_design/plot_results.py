#!/usr/bin/env python3
"""Publication-style static plots from saved measured and prospective results."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

os.environ.setdefault("MPLCONFIGDIR", "/tmp/wish-green-design-plot")
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np
from scipy.interpolate import BSpline

from research.measurement_design.run_design import load_target, TARGETS
from research.measurement_design.profiles import load_profiles

HERE = Path(__file__).resolve().parent
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                     "savefig.facecolor": "white"})


def save(fig, name):
    fig.savefig(HERE/f"{name}.png", dpi=170)
    fig.savefig(HERE/f"{name}.svg")
    plt.close(fig)


def design_plots():
    data = json.loads((HERE/"design_full.json").read_text())
    rows = data["results"]
    select = ["PS1_griz", "SkyMapper_all_covered", "JPLUS_narrow_covered", "JPLUS_all_covered",
              "PS1_plus_JPLUS_all", "ideal_XYZ"]
    labels = ["PS1 griz\nreobserved", "SkyMapper\ngri", "J-PLUS\n7 narrow", "J-PLUS\n10 covered",
              "PS1 + J-PLUS\n14 total", "Ideal X,Y,Z\n(math control)"]
    index = {(r["source_id"], r["spacing_A"], r["relative_shape_budget"], r["proposal"]["name"]): r for r in rows}
    fig, axes = plt.subplots(1, 2, figsize=(13.5, 6.3), layout="constrained", sharey=True)
    settings = [(s, b) for s in (400, 800, 1600) for b in (.05, .10)]
    images = []
    for ax, sid in zip(axes, TARGETS):
        values = np.full((len(settings), len(select)), np.nan)
        for i, (spacing, budget) in enumerate(settings):
            for j, proposal in enumerate(select):
                result = index[(sid, spacing, budget, proposal)]
                if result["both_strict_classes_feasible"]:
                    values[i, j] = 100*result["minimum_max_baseline_relative_flux_separation"]
        cmap = plt.get_cmap("YlGnBu").copy()
        cmap.set_bad("#ececec")
        images.append(ax.imshow(values, cmap=cmap, vmin=0, vmax=.56, aspect="auto"))
        for (i, j), value in np.ndenumerate(values):
            text = "no pair" if np.isnan(value) else "0" if value < 2e-5 else f"{value:.4f}"
            ax.text(j, i, text, ha="center", va="center", fontsize=9,
                    color="white" if np.isfinite(value) and value > .35 else "#172531")
        ax.set_xticks(range(len(labels)), labels, fontsize=8)
        ax.tick_params(axis="x", length=0, pad=10)
        ax.set_yticks(range(len(settings)), [f"{s} Å knots / {100*b:.0f}% bound" for s, b in settings])
        ax.set_title(data["cohort"][sid]["WDJname"].removeprefix("WDJ"), fontsize=13, pad=14)
    fig.colorbar(images[0], ax=axes, shrink=.72, pad=.03,
                 label="Minimum separation d (% of baseline band flux)")
    fig.suptitle("Can extra measurements distinguish every strict opposite-colour pair?\n"
                 "Conditional measured-PS1 boxes; fixed normalized channel guard = 0.005", fontsize=14)
    fig.supxlabel("0: an indistinguishable pair exists. 'No pair': the starting bounded spectral sets already lack an opposite pair.\n"
                  "For d > 0, equal hard flux-box half-widths < d/2 separate the strict classes; this is not a probability.",
                  fontsize=9)
    save(fig, "filter_set_separation")

    # A full-set counterexample, not a cherry-picked pair from the earlier run.
    sid, spacing, budget, proposal = TARGETS[0], 400, .05, "PS1_plus_JPLUS_all"
    row = index[(sid, spacing, budget, proposal)]
    solution = min([s for s in row["branches"] if s["success"]],
                   key=lambda s:s["minimum_max_baseline_relative_flux_separation"])
    problem, observed, errors, names, meta = load_target(sid, spacing)
    with np.load(ROOT/solution["certificate_path"]) as saved:
        coefficients = (saved["primal"][:problem.n], saved["primal"][problem.n:2*problem.n])
    fig, axes = plt.subplots(3, 1, figsize=(11, 10.5), layout="constrained")
    colors = ("#16844a", "#b44342")
    roles = ("Strict G > R and B", "Strict R > G")
    scale = np.mean(problem.flux[(problem.wave >= 6500) & (problem.wave <= 7100)])
    edges = np.arange(3600, 9826, 20.)
    centres = (edges[1:]+edges[:-1])/2
    for coeff, color, role in zip(coefficients, colors, roles):
        delta = BSpline(problem.knots, coeff, 3)(problem.wave)
        changed = problem.flux*(1+delta)
        binned = np.array([np.mean(changed[(problem.wave >= lo) & (problem.wave < hi)])
                           if np.any((problem.wave >= lo) & (problem.wave < hi)) else np.nan
                           for lo, hi in zip(edges[:-1], edges[1:])])
        axes[0].plot(centres/10, binned/scale, color=color, lw=1.1, label=role)
        axes[1].plot(problem.wave/10, 100*delta, color=color, lw=1.5, label=role)
    axes[0].set(xlabel="Wavelength (nm)", ylabel="Relative Fλ (20 Å display means)",
                title="Constructed spectra on the same observed DESI baseline")
    axes[0].set_xlim(360, 980)
    axes[0].legend(loc="upper right")
    for boundary in (-5, 5): axes[1].axhline(boundary, color="#999999", ls=":", lw=1)
    axes[1].set(xlabel="Wavelength (nm)", ylabel="Additional multiplier change (%)",
                title="Both continuous spline corrections remain within ±5%")
    axes[1].set_xlim(360, 983)
    labels = [x.replace("OAJ/JPLUS.", "JP ").replace("PS1/", "PS1 ") for x in solution["proposed_labels"]]
    delta_mag = np.asarray(solution["proposed_green_minus_opposite_mag"])
    axes[2].axhline(0, color="#999999", lw=1)
    axes[2].scatter(range(len(labels)), delta_mag*1000, color="#244f7a", s=24)
    axes[2].set_xticks(range(len(labels)), labels, rotation=45, ha="right", fontsize=9)
    axes[2].set(ylabel="Green − opposite magnitude (mmag)",
                title="All proposed PS1 + covered J-PLUS fluxes coincide numerically")
    axes[2].set_ylim(-.001, .001)
    for ax in axes: ax.grid(alpha=.2)
    fig.suptitle("J0429−0354: an explicit 14-band colour ambiguity\n"
                 "400 Å spline knots; actual PS1 griz boxes; strict guard 0.005; hypothetical added J-PLUS fluxes", fontsize=13)
    fig.supxlabel("These are numerical witnesses, not two observed states, atmosphere models, or evidence of stellar variability.", fontsize=9)
    save(fig, "indistinguishable_fourteen_band_witnesses")

    fig, ax = plt.subplots(figsize=(11, 4.8), layout="constrained")
    for flt, meta in load_profiles():
        if meta["filter_id"].startswith("SkyMapper") and meta["filter_id"].split(".")[-1] in "gri":
            ax.plot(flt.wavelength/10, flt.response/max(flt.response), lw=2,
                    label=meta["filter_id"].replace("SkyMapper/SkyMapper.", "SkyMapper "))
        elif meta["filter_id"].startswith("OAJ/JPLUS") and meta["minimum_A"] >= 3600 and meta["maximum_A"] <= 9824:
            ax.plot(flt.wavelength/10, .6*flt.response/max(flt.response), lw=.8, alpha=.5, color="#526278")
    ax.axvspan(360, 982.4, alpha=.06, color="#16844a")
    ax.set(xlim=(300, 1110), xlabel="Wavelength (nm)", ylabel="Display-normalized photon response",
           title="Actual passband shapes matter: SkyMapper gri and 10 covered J-PLUS bands\n"
                 "Shading: observed DESI wavelength interval; unbracketed u/v/z responses are excluded")
    ax.legend(ncol=3, loc="upper right"); ax.grid(alpha=.2)
    save(fig, "passband_coverage")


def measured_plots():
    data = json.loads((HERE/"measured_results.json").read_text())
    predictions = json.loads((HERE/"measured_predictions.json").read_text())
    keys = list(data["cohort"])
    label_order = [meta["filter_id"] for _, meta in load_profiles()]
    short_labels = [name.replace("SkyMapper/SkyMapper.", "SM ").replace("OAJ/JPLUS.", "JP ") for name in label_order]
    figure_log = []
    for page, first in enumerate(range(0, len(keys), 5), 1):
        selected = keys[first:first+5]
        fig, axes = plt.subplots(len(selected), 1, figsize=(12, 2.5*len(selected)+1.3), layout="constrained", squeeze=False)
        for ax, sid in zip(axes[:,0], selected):
            source = [r for r in predictions if r["source_id"] == sid]
            entries = {r["svo_filter_id"]:r for r in source}
            shown = 0
            for x, name in enumerate(label_order):
                row = entries[name]
                if not row["passband_covered"]:
                    ax.axvspan(x-.4, x+.4, color="#f0f0f0", zorder=0)
                value = row["baseline_prediction_minus_observation_mag"]
                if value is None:
                    continue
                used = row["used_in_joint_fit"]
                color = "#186798" if used else "#999999"
                ax.errorbar(x, value, yerr=row["mag_error_with_zeropoint"] if used else None,
                            fmt="o", markersize=5, color=color, markerfacecolor=color if used else "white", capsize=3)
                shown += 1
            ax.axhline(0, color="#555555", lw=.9)
            ax.set_xticks(range(len(label_order)), short_labels, rotation=45, ha="right", fontsize=8)
            meta = data["cohort"][sid]
            count = sum(r["used_in_joint_fit"] for r in source)
            ax.set_title(f"{meta['WDJname']}  |  Gaia {sid}  |  {count} strict, covered bands", fontsize=10, loc="left")
            ax.set_ylabel("Predicted − observed\nAB magnitude")
            ax.grid(axis="y", alpha=.2)
            if not shown:
                ax.text(.5, .7, "No numeric measurement with complete spectral coverage", transform=ax.transAxes,
                        ha="center", color="#666666")
                ax.set_ylim(-.1, .1)
            else:
                lo, hi = ax.get_ylim()
                ax.set_ylim(min(lo, -.06), max(hi, .06))
            figure_log.append({"source_id": sid, "WDJname": meta["WDJname"],
                               "figure": f"photometry_sheet_{page:02d}.png", "panel": len(figure_log)%5+1,
                               "strict_covered_bands": count,
                               "prepared_only_not_a_viewing_record": True})
        fig.suptitle(f"New catalogue photometry: pre-fit DESI predictions ({page}/5)\n"
                     "Natural-passband integration; additional survey measurements were not fitted in these predictions", fontsize=13)
        fig.supxlabel("Filled points: strict-quality measurements; open points: quality-rejected diagnostics. Grey columns: missing spectral coverage.\n"
                      "Error bars use the catalogue/recommended zero-point errors; they are not independent Gaussian significance estimates.", fontsize=9)
        save(fig, f"photometry_sheet_{page:02d}")
    (HERE/"prepared_photometry_panels.json").write_text(json.dumps(figure_log, indent=2)+"\n")

    rows = [r for r in data["scenarios"] if r["source_id"] == TARGETS[0]]
    fig, axes = plt.subplots(1, 3, figsize=(12.5, 5.5), layout="constrained", sharey=True)
    cases = [("PS1_only", 0., "PS1 griz"), ("PS1_plus_strict", 0., "+ SM ri"),
             ("PS1_plus_official_good", 0., "+ SM gri*"), ("PS1_plus_strict", .02, "+ SM ri\nwider boxes")]
    for ax, spacing in zip(axes, (400, 800, 1600)):
        for goal, color, marker, label in (("photometry", "#555555", "o", "Fit data; colour unconstrained"),
                                           ("green_strict", "#15804a", "^", "Strict green"),
                                           ("G_lt_R_strict", "#b44845", "s", "Strict R > G")):
            values = []
            for scenario, margin, _ in cases:
                result = next(r for r in rows if r["scenario"] == scenario and r["spacing_A"] == spacing
                              and r["additional_systematic_box_margin_mag"] == margin)["solutions"][goal]
                values.append(100*result["continuous_witness_supremum"] if result["success"] else np.nan)
            ax.plot(range(len(cases)), values, marker=marker, color=color, lw=1.1, ms=5, label=label)
        ax.axhline(5, ls=":", color="#aaaaaa")
        ax.set_xticks(range(len(cases)), [c[2] for c in cases], rotation=35, ha="right", fontsize=9)
        ax.set_title(f"{spacing} Å spline knots")
        ax.grid(alpha=.2)
    axes[0].set_ylabel("Minimum maximum shape change (%)")
    axes[-1].legend(fontsize=8)
    fig.suptitle("J0429−0354: what the actual SkyMapper measurements add\n"
                 "Fixed central DESI spectrum; measured PS1 griz boxes; normalized strict colour guard = 0.005", fontsize=13)
    fig.supxlabel("* SkyMapper g passes official-good rules but fails the stricter zero-mask rule. SM z is excluded for incomplete wavelength coverage.\n"
                  "Wider boxes add 0.02 mag to each SkyMapper half-width; this is a sensitivity assumption, not a measured systematic error.", fontsize=9)
    save(fig, "j0429_actual_added_measurements")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--design-only", action="store_true")
    args = parser.parse_args()
    design_plots()
    if not args.design_only:
        measured_plots()
