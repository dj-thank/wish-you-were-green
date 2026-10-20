#!/usr/bin/env python3
"""Local-only native/mask check requested after the page-20 visual review."""
from __future__ import annotations

from datetime import datetime, timezone
import gzip
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd
from research.unit_resolution_followup.compact_inputs import CompactInputs
from research.unit_resolution_followup.targeted_followup.analyse import (
    averages, clean_json, counts, mask_names, sha, plt,
)


def compute(root=ROOT):
    root = Path(root).resolve()
    assert root == ROOT
    parent = HERE.parent
    checked = {}

    def hashed(path, expected=None):
        path = Path(path)
        digest = sha(path)
        assert expected is None or digest == expected, str(path)
        checked[str(path.relative_to(root))] = digest
        return path

    registry = json.loads(hashed(parent / "overlay_registry.json").read_text())
    hashed(parent / "compact_manifest.json")
    frozen = json.load(gzip.open(hashed(root / "mwdd/manifest_enriched.json.gz"), "rt"))
    entry = next(r for r in registry["records"] if r["mwdd_row_index"] == 5827)
    meta = next(r for r in frozen if r.get("sha256") == entry["mwdd_sha256"])
    assert entry["convention"] == "flambda"
    assert entry["unit_status"] == "verified_native_pixel_identity"
    store = CompactInputs(root)
    dictionary = store.manifest["wavelength_dictionary"]
    hashed(parent / dictionary["file"], dictionary["sha256"])
    for key in ("mwdd_5827", entry["external_reference_id"]):
        shard = store.entries[key]["shard"]
        hashed(parent / shard, store.shas[shard])
    original = store.load(entry["external_reference_id"])
    export = store.load("mwdd_5827")
    ref = store.entries[entry["external_reference_id"]]
    assert ref["raw_sha256"] == entry["direct_sha256"]
    definitions = mask_names(hashed(HERE / "sources/sdss_bitmasks.html"))
    for path in (Path(__file__), HERE / "analyse.py", parent / "compact_inputs.py",
                 parent / "fetch_and_identify.py", root / "research/precision/flux_convention_audit.py",
                 root / "project_io.py", root / "requirements-core.txt"):
        hashed(path)
    wave, flux, ivar = (original[n] for n in ("wave", "flux", "ivar"))
    and_mask, or_mask = original["and_mask"], original["or_mask"]
    ew, ef = export["wave"], export["flux"]
    ids = np.searchsorted(wave, ew).clip(1, len(wave) - 1)
    ids = np.where(abs(wave[ids - 1] - ew) < abs(wave[ids] - ew), ids - 1, ids)
    matched = (ew >= 3600) & (ew <= 8300)
    maximum_wave_error = float(np.max(abs(wave[ids[matched]] - ew[matched])))
    assert maximum_wave_error < .02
    factor = float(np.median(ef[matched] / flux[ids[matched]]))
    residual = float(np.max(abs(ef[matched] / flux[ids[matched]] / factor - 1)))
    assert residual < 1e-4
    finite = np.isfinite(wave) & np.isfinite(flux)
    good = finite & np.isfinite(ivar) & (ivar > 0)
    visible = finite & (wave >= 3600) & (wave <= 8300)
    clear = good & (and_mask == 0)
    normalization = float(np.median(flux[clear & (wave >= 5200) & (wave <= 5500)]))
    assert normalization > 0
    regions = []
    for lo, hi, label in [(3900, 4200, "first blue window"), (4200, 4510, "second blue window"),
                           (4700, 5060, "middle window"), (6400, 6800, "red visual peak window")]:
        use = visible & (wave >= lo) & (wave <= hi)
        ids = np.flatnonzero(use & good)
        peak, minimum = ids[np.argmax(flux[ids])], ids[np.argmin(flux[ids])]
        regions.append({"label": label, "bounds_A": [lo, hi], "native_pixels": int(use.sum()),
            "positive_ivar_pixels": int((use & good).sum()),
            "AND_zero_positive_ivar_pixels": int((use & clear).sum()),
            "maximum_native_pixel_A": float(wave[peak]), "minimum_native_pixel_A": float(wave[minimum]),
            "maximum_flux_Flambda": float(flux[peak]), "maximum_AND_mask": int(and_mask[peak]),
            "maximum_OR_mask": int(or_mask[peak]),
            "AND_bits": counts(and_mask, use, definitions["SPPIXMASK"]),
            "OR_bits": counts(or_mask, use, definitions["SPPIXMASK"])})
    # The wide red window was selected from the contact sheet before this replay.
    ids = np.flatnonzero(good & (wave >= 6400) & (wave <= 6800))
    peak = ids[np.argmax(flux[ids])]
    side = clear & (((wave >= 6400) & (wave <= 6470)) | ((wave >= 6700) & (wave <= 6800)))
    continuum = np.polyval(np.polyfit(wave[side] - wave[peak], flux[side], 1), wave - wave[peak])
    excess = flux - continuum
    half = excess[peak] / 2
    left, right = peak, peak
    while left > 0 and good[left - 1] and excess[left - 1] >= half:
        left -= 1
    while right + 1 < len(wave) and good[right + 1] and excess[right + 1] >= half:
        right += 1
    cluster = np.zeros(len(wave), dtype=bool)
    cluster[left:right + 1] = True
    warning = int(ref["hdu2_quality"]["ZWARNING"])
    record = clean_json({
        "row_index": 5827, "entity_id": entry["entity_id"], "source_id": entry["source_id"],
        "name": entry["name"], "MWDD_frozen_class": meta["spectype"],
        "MWDD_frozen_temperature_K_metadata_only": meta["teff"],
        "reference_id": entry["external_reference_id"], "header": original["header"],
        "MWDD_source_url": entry["source_url"], "MWDD_raw_sha256": entry["mwdd_sha256"],
        "reference_source_url": ref["source_url"], "reference_raw_sha256": ref["raw_sha256"],
        "automatic_SDSS_quality": ref["hdu2_quality"],
        "automatic_SDSS_ZWARNING_decoded": [n for bit, n in definitions["ZWARNING"].items() if warning & (1 << bit)],
        "native_identity": {"MWDD_input_convention": "flambda", "direct_convention": "flambda",
            "matched_visible_pixels": int(matched.sum()), "maximum_wavelength_difference_A": maximum_wave_error,
            "wavelength_independent_scale": factor, "maximum_fractional_shape_error_after_scale": residual,
            "same_observation_not_independent_confirmation": True},
        "native_visible_quality": {"pixels": int(visible.sum()),
            "nonpositive_ivar_pixels": int((visible & ~good).sum()),
            "negative_flux_pixels": int((visible & (flux < 0)).sum()),
            "positive_ivar_median_pixel_snr": float(np.median(flux[visible & good] * np.sqrt(ivar[visible & good]))),
            "AND_nonzero_pixels": int((visible & (and_mask != 0)).sum()),
            "OR_nonzero_pixels": int((visible & (or_mask != 0)).sum())},
        "windows": regions,
        "red_peak_native_check": {"predeclared_search_window_A": [6400, 6800],
            "maximum_native_pixel_A": float(wave[peak]), "peak_flux_Flambda": float(flux[peak]),
            "peak_supplied_flux_error": float(1 / np.sqrt(ivar[peak])),
            "peak_AND_mask": int(and_mask[peak]), "peak_OR_mask": int(or_mask[peak]),
            "local_continuum_linear_fit_sidebands_A": [[6400, 6470], [6700, 6800]],
            "contiguous_pixels_above_half_peak_excess": int(right - left + 1),
            "contiguous_half_excess_pixel_centres_A": [float(wave[left]), float(wave[right])],
            "half_excess_cluster_AND_bits": counts(and_mask, cluster, definitions["SPPIXMASK"]),
            "half_excess_cluster_OR_bits": counts(or_mask, cluster, definitions["SPPIXMASK"])},
        "limits": "Local-only follow-up of a purposively selected visual flag. Frozen MWDD DZ: and generic SDSS STAR/CV labels are preserved as separate catalogue evidence, without new physical classification or an atomic line identification. A half-excess pixel cluster is a descriptive, sideband-dependent morphology measure, not deconvolved FWHM, line significance, or a variability result. No fresh literature, Gaia, neighbour or proper-motion association check was performed for this additional target; source-array identity is not an independent positional or physical confirmation.",
    })
    return {"record": record, "verified_source_sha256": checked}, {
        "wave": wave, "flux": flux, "ivar": ivar, "and_mask": and_mask, "or_mask": or_mask,
        "good": good, "clear": clear, "normalization": normalization,
    }


def make_figure(record, data):
    wave, flux, ivar = (data[n] for n in ("wave", "flux", "ivar"))
    scale = data["normalization"]
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
    fig = plt.figure(figsize=(13, 8))
    grid = fig.add_gridspec(2, 2)
    axes = [fig.add_subplot(grid[0, :]), fig.add_subplot(grid[1, 0]), fig.add_subplot(grid[1, 1])]
    for number, (ax, bounds) in enumerate(zip(axes, [(3800, 8300), (3900, 5060), (6400, 6800)])):
        lo, hi = bounds
        use = (wave >= lo) & (wave <= hi)
        good = use & data["good"]
        flagged = good & (data["and_mask"] != 0)
        ax.plot(wave[use] / 10, flux[use] / scale, color="#aaaaaa", lw=.6, label="All signed native samples")
        if number:
            ax.errorbar(wave[good] / 10, flux[good] / scale, yerr=1 / np.sqrt(ivar[good]) / scale,
                        fmt=".", ms=2.5, color="#858585", ecolor="#d4d4d4", lw=.5,
                        label="Positive IVAR; supplied pixel errors")
        binned = averages(wave, flux, data["good"], lo, hi, 10)
        clear = averages(wave, flux, data["clear"], lo, hi, 10)
        ax.plot(binned[:, 0] / 10, binned[:, 1] / scale, color="#1e6386", lw=1.4, label="10 Å mean, positive IVAR")
        ax.plot(clear[:, 0] / 10, clear[:, 1] / scale, color="#169661", lw=1, ls="--", label="10 Å mean, plus AND=0")
        ax.scatter(wave[flagged] / 10, flux[flagged] / scale, color="#db8c21", s=8, label="Nonzero AND mask")
        bad = use & ~data["good"]
        ax.scatter(wave[bad] / 10, flux[bad] / scale, marker="x", color="#cf3434", s=12, label="Nonpositive IVAR")
        ax.set(xlim=(lo / 10, hi / 10), xlabel="Observed vacuum wavelength (nm)", ylabel="Fλ / fixed median (520–550 nm)")
        ax.grid(alpha=.17)
    axes[0].legend(loc="upper right", ncol=2, fontsize=8)
    peak = record["red_peak_native_check"]["maximum_native_pixel_A"]
    axes[2].axvline(peak / 10, color="#b74161", ls=":")
    axes[2].set_title(f"Native maximum {peak:.3f} Å; AND=OR=0", fontsize=10)
    fig.suptitle("Row 5827: Gaia DR3 1242828982729309952\nNative SDSS morphology; MWDD DZ: and automatic STAR/CV labels kept separately", fontsize=14)
    fig.subplots_adjust(left=.08, right=.985, top=.85, bottom=.14, hspace=.42, wspace=.22)
    fig.text(.5, .025, "One SDSS coadd; the MWDD export represents the same observation. All native shapes are retained.\n"
             "Local-only follow-up: no atomic identification, independent positional confirmation or new physical classification.", ha="center", fontsize=9)
    png, svg = HERE / "native_row_5827.png", HERE / "native_row_5827.svg"
    fig.savefig(png, dpi=170, facecolor="white")
    fig.savefig(svg, facecolor="white")
    plt.close(fig)
    return {"png": png.name, "png_sha256": sha(png), "svg": svg.name, "svg_sha256": sha(svg)}


if __name__ == "__main__":
    result, data = compute()
    result["created_utc"] = datetime.now(timezone.utc).isoformat()
    result["figure"] = make_figure(result["record"], data)
    (HERE / "local_row_5827.json").write_text(json.dumps(result, indent=2) + "\n")
    use = (data["wave"] >= 3600) & (data["wave"] <= 8300)
    pd.DataFrame({n: data[n][use] for n in ("wave", "flux", "ivar", "and_mask", "or_mask")}).to_csv(
        HERE / "native_row_5827.csv.gz", index=False, float_format="%.17g", compression={"method": "gzip", "mtime": 0})
    print(json.dumps(result["record"], indent=2))
