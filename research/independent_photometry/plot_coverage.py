#!/usr/bin/env python3
"""Plot catalogue/quality coverage; colour here encodes quality, not stellar colour."""
import argparse
import csv
import json
import os
import tempfile
from pathlib import Path

_MPL_CONFIG = tempfile.TemporaryDirectory(prefix="wd_independent_photometry_mpl_")
os.environ.setdefault("MPLCONFIGDIR", _MPL_CONFIG.name)
import matplotlib
matplotlib.use("Agg")
matplotlib.rcParams["svg.hashsalt"] = "independent_photometry_coverage_v1"
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch
import numpy as np

HERE = Path(__file__).resolve().parent


def coordinate_label(ra, dec):
    hours = ra / 15
    return f"J{int(hours):02d}{int((hours % 1) * 60):02d}{'+' if dec >= 0 else '-'}{int(abs(dec)):02d}{int((abs(dec) % 1) * 60):02d}"


def main(root):
    base = root / "research/independent_photometry"
    payload = json.loads((base / "measurements.json").read_text())
    rows = payload["measurements"]
    astrometry = {r["source_id"]: r for r in csv.DictReader(
        (root / "research/external_validation/raw/gaia_dr3_extended_targets.csv").open())}
    ids = sorted({r["source_id"] for r in rows}, key=lambda sid: float(astrometry[sid]["ra"]))
    bands = list(dict.fromkeys((r["survey"], r["band"]) for r in rows))
    index = {(r["source_id"], r["survey"], r["band"]): r for r in rows}
    matrix = np.zeros((len(ids), len(bands)), dtype=int)
    for i, sid in enumerate(ids):
        for j, (survey, band) in enumerate(bands):
            r = index[sid, survey, band]
            matrix[i, j] = 2 if r["adopted"] else int(r["mag_ab"] is not None and r["mag_ab"] < 90)
    colours = ["#edf1f5", "#efc77b", "#267e72"]
    fig, ax = plt.subplots(figsize=(11.8, 10.2))
    fig.subplots_adjust(left=0.15, right=0.98, top=0.84, bottom=0.13)
    ax.imshow(matrix, cmap=ListedColormap(colours), vmin=-0.5, vmax=2.5, aspect="auto")
    ax.set_xticks(range(len(bands)), [band for _, band in bands], rotation=45, ha="right")
    labels = [coordinate_label(float(astrometry[s]["ra"]), float(astrometry[s]["dec"])) for s in ids]
    assert len(set(labels)) == len(labels)
    ax.set_yticks(range(len(ids)), labels, fontsize=9)
    ax.set_xticks(np.arange(-0.5, len(bands), 1), minor=True)
    ax.set_yticks(np.arange(-0.5, len(ids), 1), minor=True)
    ax.grid(which="minor", color="white", linewidth=1.4)
    ax.tick_params(which="minor", bottom=False, left=False)
    ax.axvline(5.5, color="#526170", linewidth=1.4)
    ax.text(2.5, -1.5, f"SkyMapper DR4: {np.sum(matrix[:, :6] == 2)} selected", ha="center", fontsize=11, color="#153e37")
    ax.text(11.5, -1.5, f"J-PLUS DR4: {np.sum(matrix[:, 6:] == 2)} selected", ha="center", fontsize=11, color="#153e37")
    fig.suptitle(f"Additional imaging photometry for the fixed {len(ids)}-object cohort", y=0.96, fontsize=15)
    fig.text(0.5, 0.917, f"{np.sum(matrix == 2)} quality-selected measurements for {np.sum(np.any(matrix == 2, axis=1))} objects; {matrix.size} band slots audited", ha="center", fontsize=11)
    legend = [Patch(facecolor=colours[0], label="No identified catalogue magnitude"),
              Patch(facecolor=colours[1], label="Retained magnitude; fails strict quality"),
              Patch(facecolor=colours[2], label="Passes strict quality")]
    fig.legend(handles=legend, loc="lower center", ncol=3, frameon=False, bbox_to_anchor=(0.53, 0.046), fontsize=9)
    fig.text(0.5, 0.023, "Quality selection only: full passband coverage is tested separately. Independent source photons can share calibration standards.",
             ha="center", fontsize=8.5, color="#46505b")
    for side in ax.spines.values():
        side.set_visible(False)
    fig.savefig(base / "coverage.png", dpi=160, facecolor="white")
    fig.savefig(base / "coverage.svg", facecolor="white", metadata={"Date": None})
    plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=HERE.parents[1])
    main(parser.parse_args().root.resolve())
