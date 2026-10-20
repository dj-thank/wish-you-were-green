#!/usr/bin/env python3
"""Bounded native-pixel and catalogue follow-up of three actual visual flags."""
from __future__ import annotations

from datetime import datetime, timezone
import gzip
import hashlib
from html import unescape
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("MPLCONFIGDIR", "/tmp/wish-green-targeted-mpl")

import numpy as np
import pandas as pd
from astropy.coordinates import SkyCoord
from astropy import units as u
from astropy.table import Table
from astropy.time import Time
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from research.unit_resolution_followup.compact_inputs import CompactInputs

TARGETS = (7607, 8019, 7930)
INITIAL_7607_VISUAL_WINDOWS = [(3950, 4300), (4400, 4850), (5480, 5970), (6090, 6550)]
WINDOWS = {
    7607: [(3890, 4020, "first resolved blue depression"), (4020, 4200, "second resolved blue depression"),
           (4200, 4500, "third resolved blue depression"), (4700, 5050, "fourth resolved blue depression"),
           (5750, 6040, "middle-red depression"), (6400, 6710, "red depression")],
    8019: [(3800, 4120, "first blue depression"), (4250, 4550, "second blue depression"),
           (3860, 3930, "blue local rise"), (4150, 4260, "second local rise"),
           (4590, 4740, "third local rise"), (5510, 5810, "middle local rise")],
    7930: [(6540, 6600, "narrow red peak")],
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def clean_json(value):
    if isinstance(value, dict):
        return {str(k): clean_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean_json(v) for v in value]
    if isinstance(value, np.ndarray):
        return clean_json(value.tolist())
    if isinstance(value, np.generic):
        return clean_json(value.item())
    if value is np.ma.masked:
        return None
    if isinstance(value, float) and not np.isfinite(value):
        return None
    return value


class Rows(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows, self.row, self.cell = [], None, None

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self.row = []
        if tag in ("td", "th") and self.row is not None:
            self.cell = []

    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self.cell is not None:
            self.row.append(" ".join(" ".join(self.cell).split()))
            self.cell = None
        if tag == "tr" and self.row is not None:
            self.rows.append(self.row)
            self.row, self.cell = None, None


def mwdd_fields(path):
    parser = Rows()
    parser.feed(path.read_text())
    header = next(row for row in parser.rows if row and row[0] == "Parameter")
    fields = {}
    for label in ("Spectral type", "Effective temperature", "log(g)"):
        row = next(row for row in parser.rows if row and row[0] == label)
        fields[label] = {name: value for name, value in zip(header[2:], row[2:]) if value}
    return fields


def mask_names(path):
    text = path.read_text()
    result = {}
    for key in ("SPPIXMASK", "ZWARNING"):
        section = text.split(f'<div id="{key}"', 1)[1].split("</table>", 1)[0]
        parser = Rows()
        parser.feed(section)
        result[key] = {int(row[1]): row[0] for row in parser.rows
                       if len(row) == 3 and row[1].isdigit()}
    return result


def counts(mask, selected, names):
    return [{"bit": bit, "name": name, "pixels": int(np.sum((mask[selected] & (1 << bit)) != 0))}
            for bit, name in sorted(names.items()) if np.any((mask[selected] & (1 << bit)) != 0)]


def averages(wave, flux, selected, lower=3600, upper=8300, width=10):
    edges = np.arange(lower, upper + width, width)
    output = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        use = selected & (wave >= lo) & (wave < hi)
        output.append(((lo + hi) / 2, np.mean(flux[use]) if use.any() else np.nan,
                       int(use.sum())))
    return np.array(output)


def compute(root=ROOT):
    root = Path(root).resolve()
    assert root == ROOT
    parent = HERE.parent
    checked = {}

    def hashed(path, expected=None):
        path = (root / path).resolve()
        assert path.is_relative_to(root)
        digest = sha(path)
        assert expected is None or expected == digest, str(path)
        checked[str(path.relative_to(root))] = digest
        return path

    for name in ("context_manifest.json", "specialist_manifest.json"):
        manifest = json.loads(hashed(HERE / name).read_text())
        for entry in manifest["sources"]:
            hashed(HERE / entry["file"], entry["sha256"])
            hashed(HERE / (entry["file"] + ".provenance.json"))
    registry = json.loads(hashed(parent / "overlay_registry.json").read_text())
    native_manifest = json.loads(hashed(parent / "compact_manifest.json").read_text())
    store = CompactInputs(root)
    hashed(parent / native_manifest["wavelength_dictionary"]["file"],
           native_manifest["wavelength_dictionary"]["sha256"])
    frozen = json.load(gzip.open(hashed(root / "mwdd/manifest_enriched.json.gz"), "rt"))
    gaia = pd.read_csv(hashed(HERE / "sources/gaia_context.csv"), dtype={"source_id": str})
    variables = pd.read_csv(hashed(HERE / "sources/gaia_variability.csv"), dtype={"source_id": str})
    specialist = Table.read(hashed(HERE / "sources/kleinman_catalogue.xml"), format="votable")
    assert len(specialist) == 4
    definitions = mask_names(HERE / "sources/sdss_bitmasks.html")
    for name in ("compact_inputs.py", "fetch_and_identify.py"):
        hashed(parent / name)
    for name in ("analyse.py", "fetch_context.py", "fetch_specialist.py", "gaia_query.adql",
                 "gaia_variability_query.adql", "kleinman_query.adql"):
        hashed(HERE / name)
    rows, native = [], {}
    for index in TARGETS:
        entry = next(r for r in registry["records"] if r["mwdd_row_index"] == index)
        metadata = next(r for r in frozen if r.get("sha256") == entry["mwdd_sha256"])
        reference_id = entry["external_reference_id"]
        ref_meta = store.entries[reference_id]
        assert entry["convention"] == "fnu" and entry["unit_status"] == "verified_native_pixel_identity"
        assert ref_meta["raw_sha256"] == entry["direct_sha256"]
        for key in ("mwdd_" + str(index), reference_id):
            shard = store.entries[key]["shard"]
            hashed(parent / shard, store.shas[shard])
        original, export = store.load(reference_id), store.load("mwdd_" + str(index))
        wave, flux, ivar = original["wave"], original["flux"], original["ivar"]
        and_mask, or_mask = original["and_mask"], original["or_mask"]
        assert len(wave) == len(export["wave"])
        wave_error = float(np.max(np.abs(wave - export["wave"])))
        assert wave_error < .02
        converted = export["flux"] * 2.99792458e18 / export["wave"] ** 2
        comparison = np.isfinite(flux) & (np.abs(flux) > np.median(np.abs(flux)) * .01)
        factor = float(np.median(converted[comparison] / flux[comparison]))
        identity_error = float(np.max(np.abs(converted[comparison] / flux[comparison] / factor - 1)))
        assert identity_error < 2e-12
        finite = np.isfinite(wave) & np.isfinite(flux)
        good = finite & np.isfinite(ivar) & (ivar > 0)
        visible = finite & (wave >= 3600) & (wave <= 8300)
        clear = good & (and_mask == 0)
        normalization = float(np.median(flux[clear & (wave >= 5200) & (wave <= 5500)]))
        assert normalization > 0
        info = {
            "row_index": index, "entity_id": entry["entity_id"], "source_id": entry["source_id"],
            "name": entry["name"], "reference_id": reference_id,
            "MWDD_source_url": entry["source_url"], "MWDD_raw_sha256": entry["mwdd_sha256"],
            "reference_source_url": ref_meta["source_url"], "reference_raw_sha256": ref_meta["raw_sha256"],
            "header": original["header"], "automatic_SDSS_quality": ref_meta["hdu2_quality"],
            "MWDD_frozen_class": metadata["spectype"],
            "MWDD_frozen_temperature_K_metadata_only": metadata["teff"],
            "MWDD_live_source_columns": mwdd_fields(HERE / f"sources/mwdd_{index}.html"),
            "native_identity": {"MWDD_input_convention": "fnu", "direct_convention": "flambda",
                                "maximum_wavelength_difference_A": wave_error,
                                "wavelength_independent_scale": factor,
                                "maximum_fractional_shape_error_after_scale": identity_error,
                                "same_observation_not_independent_confirmation": True},
            "native_visible_quality": {"pixels": int(visible.sum()),
                "nonpositive_ivar_pixels": int((visible & ~good).sum()),
                "negative_flux_pixels": int((visible & (flux < 0)).sum()),
                "positive_ivar_median_pixel_snr": float(np.median(flux[visible & good] * np.sqrt(ivar[visible & good]))),
                "AND_nonzero_pixels": int((visible & (and_mask != 0)).sum()),
                "OR_nonzero_pixels": int((visible & (or_mask != 0)).sum()),
                "AND_bits": counts(and_mask, visible, definitions["SPPIXMASK"]),
                "OR_bits": counts(or_mask, visible, definitions["SPPIXMASK"])},
            "windows": [],
        }
        if index == 7607:
            info["window_revision"] = {"initial_coarse_visual_windows_A": INITIAL_7607_VISUAL_WINDOWS,
                "reason": "After actual native-figure inspection, the initial approximate visual windows were replaced with intervals bracketing the resolved depressions near 397/410/434/486/589/656 nm. The initial approximate wavelengths are not line identifications or native peak measurements."}
        warning = int(ref_meta["hdu2_quality"]["ZWARNING"])
        info["automatic_SDSS_ZWARNING_decoded"] = [name for bit, name in definitions["ZWARNING"].items() if warning & (1 << bit)]
        for lo, hi, label in WINDOWS[index]:
            selected = finite & (wave >= lo) & (wave < hi)
            binned = averages(wave, flux, good, lo, hi, 10)
            binned = binned[np.isfinite(binned[:, 1])]
            minimum, maximum = binned[np.argmin(binned[:, 1])], binned[np.argmax(binned[:, 1])]
            info["windows"].append({
                "visual_region": label, "lower_A": lo, "upper_A": hi,
                "native_pixels": int(selected.sum()), "positive_ivar_pixels": int((selected & good).sum()),
                "AND_zero_positive_ivar_pixels": int((selected & clear).sum()),
                "AND_bits": counts(and_mask, selected, definitions["SPPIXMASK"]),
                "OR_bits": counts(or_mask, selected, definitions["SPPIXMASK"]),
                "minimum_10A_mean_bin_centre_A": float(minimum[0]),
                "minimum_10A_mean_over_normalization": float(minimum[1] / normalization),
                "maximum_10A_mean_bin_centre_A": float(maximum[0]),
                "maximum_10A_mean_over_normalization": float(maximum[1] / normalization),
                "locator_limit": "Predeclared visual window and 10 A arithmetic means; not a fitted transition centre, equivalent width, line identification, or statistical detection."})
        same_position = []
        point = SkyCoord(metadata["ra_deg"] * u.deg, metadata["dec_deg"] * u.deg)
        for spec in specialist:
            position = SkyCoord(float(spec["ra"]) * u.deg, float(spec["dec"]) * u.deg)
            separation = float(point.separation(position).arcsec)
            if separation > 2:
                continue
            fields = ("name", "plate_number", "spectrum_date", "fiber_number", "ra", "dec", "spect_type",
                      "autofit_spect_type", "autofit_eff_temp", "autofit_log_g", "autofit_red_chisquared", "unique_flag")
            known = {name: clean_json(spec[name]) for name in fields}
            known["separation_from_MWDD_coordinate_arcsec"] = separation
            known["same_plate_mjd_fiber_as_selected_reference"] = (
                int(spec["plate_number"]) == original["header"]["PLATEID"]
                and int(spec["spectrum_date"]) == original["header"]["MJD"]
                and int(spec["fiber_number"]) == original["header"]["FIBERID"])
            same_position.append(known)
        info["Kleinman2013_published_rows_within_2arcsec"] = same_position
        target = gaia[gaia.source_id == entry["source_id"]].iloc[0].to_dict()
        year = float(Time(original["header"]["MJD"], format="mjd", scale="utc").jyear)
        dt = year - float(target["ref_epoch"])
        corrected_ra = float(target["ra"]) + float(target["pmra"]) * dt / (3.6e6 * np.cos(np.deg2rad(target["dec"])))
        corrected_dec = float(target["dec"]) + float(target["pmdec"]) * dt / 3.6e6
        plug = SkyCoord(original["header"]["PLUG_RA"] * u.deg, original["header"]["PLUG_DEC"] * u.deg)
        info["Gaia_DR3"] = target
        matches = variables[variables.source_id == entry["source_id"]].to_dict(orient="records")
        info["Gaia_existing_variability_classification"] = matches
        info["association_point_check"] = {
            "approximate_epoch_jyear_from_nominal_coadd_MJD": year,
            "proper_motion_propagated_Gaia_ra_deg": corrected_ra,
            "proper_motion_propagated_Gaia_dec_deg": corrected_dec,
            "separation_from_PLUG_arcsec": float(plug.separation(SkyCoord(corrected_ra * u.deg, corrected_dec * u.deg)).arcsec),
            "limits": "Nominal coadd MJD point estimate; not constituent exposure epochs, covariance likelihood, annual-parallax or radial-velocity correction. No low-S/N or negative parallax is inverted."}
        target_position = SkyCoord(float(target["ra"]) * u.deg, float(target["dec"]) * u.deg)
        neighbours = []
        for _, neighbour in gaia.iterrows():
            distance = float(target_position.separation(SkyCoord(float(neighbour.ra) * u.deg, float(neighbour.dec) * u.deg)).arcsec)
            if neighbour.source_id == entry["source_id"] or distance > 15:
                continue
            neighbours.append({"source_id": neighbour.source_id, "separation_at_2016_arcsec": distance,
                "G_mag": float(neighbour.phot_g_mean_mag),
                "G_flux_ratio_to_target": float(10 ** (-.4 * (float(neighbour.phot_g_mean_mag) - target["phot_g_mean_mag"])))})
        info["Gaia_neighbours_within_15arcsec_at_reference_epoch"] = sorted(neighbours, key=lambda r: r["separation_at_2016_arcsec"])
        if index == 7930:
            peak_candidates = np.where(good & (wave >= 6540) & (wave <= 6600))[0]
            peak = int(peak_candidates[np.argmax(flux[peak_candidates])])
            side = clear & (((wave >= 6500) & (wave <= 6535)) | ((wave >= 6595) & (wave <= 6630)))
            coefficients = np.polyfit(wave[side] - wave[peak], flux[side], 1)
            continuum = np.polyval(coefficients, wave - wave[peak])
            excess = flux - continuum
            half = .5 * excess[peak]
            left, right = peak, peak
            while left > 0 and good[left - 1] and excess[left - 1] >= half:
                left -= 1
            while right + 1 < len(wave) and good[right + 1] and excess[right + 1] >= half:
                right += 1
            cluster = np.zeros(len(wave), dtype=bool)
            cluster[left:right + 1] = True
            info["narrow_peak_native_check"] = {
                "predeclared_search_window_A": [6540, 6600], "maximum_native_pixel_A": float(wave[peak]),
                "peak_flux_Flambda": float(flux[peak]), "peak_supplied_flux_error": float(1 / np.sqrt(ivar[peak])),
                "peak_AND_mask": int(and_mask[peak]), "peak_OR_mask": int(or_mask[peak]),
                "local_continuum_linear_fit_sidebands_A": [[6500, 6535], [6595, 6630]],
                "contiguous_pixels_above_half_peak_excess": right - left + 1,
                "contiguous_half_excess_pixel_centres_A": [float(wave[left]), float(wave[right])],
                "half_excess_cluster_AND_bits": counts(and_mask, cluster, definitions["SPPIXMASK"]),
                "half_excess_cluster_OR_bits": counts(or_mask, cluster, definitions["SPPIXMASK"]),
                "limits": "A native-pixel morphology check retaining the line. Pixel-centre span is not a deconvolved FWHM; no fitted atomic identification, aperture-origin determination or new emission discovery."}
        rows.append(info)
        native[index] = {"wave": wave, "flux": flux, "ivar": ivar, "and_mask": and_mask,
                         "or_mask": or_mask, "good": good, "clear": clear,
                         "normalization": normalization}
    return clean_json({"status": "PASS", "selection": "Root-requested actual visual flags at pages 27/2, 30/9 and 29/13; no population sampling claim.",
                       "records": rows, "verified_source_sha256": checked,
                       "mask_definitions": definitions,
                       "limits": "Original signed F_lambda shapes and native masks retained. Generic classifiers, manual catalogue labels and Gaia classification scores are evidence with separate provenance, not infallible truth or posterior probabilities. No physical-looking feature is removed or reassigned automatically."}), native


def make_figures(result, native):
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
    records = []
    for info in result["records"]:
        index = info["row_index"]
        data = native[index]
        wave, flux, ivar = data["wave"], data["flux"], data["ivar"]
        scale = data["normalization"]
        fig = plt.figure(figsize=(13, 8))
        grid = fig.add_gridspec(2, 2, height_ratios=(1, 1.05), hspace=.5, wspace=.26)
        axes = [fig.add_subplot(grid[0, :])]
        intervals = [(max(3800, float(wave.min())), 8300)]
        if index == 7930:
            axes.append(fig.add_subplot(grid[1, :]))
            intervals.append((6480, 6640))
        else:
            axes.extend([fig.add_subplot(grid[1, 0]), fig.add_subplot(grid[1, 1])])
            intervals.extend([(3900 if index == 7607 else 3800, 4850 if index == 7607 else 4700), (5400, 6650)])
        for number, (ax, (lower, upper)) in enumerate(zip(axes, intervals)):
            select = (wave >= lower) & (wave <= upper)
            positive = select & data["good"]
            rejected = select & ~data["good"]
            flagged = positive & (data["and_mask"] != 0)
            ax.plot(wave[select] / 10, flux[select] / scale, color="#aaa", lw=.6, label="All signed native samples")
            if number:
                ax.errorbar(wave[positive] / 10, flux[positive] / scale,
                            yerr=1 / np.sqrt(ivar[positive]) / scale,
                            fmt=".", ms=2.5, color="#858585", ecolor="#d4d4d4", lw=.5,
                            label="Positive IVAR; supplied pixel errors")
            binned = averages(wave, flux, data["good"], lower, upper, 10)
            ax.plot(binned[:, 0] / 10, binned[:, 1] / scale, color="#1e6386", lw=1.4, label="10 Å mean, positive IVAR")
            strict = averages(wave, flux, data["clear"], lower, upper, 10)
            ax.plot(strict[:, 0] / 10, strict[:, 1] / scale, color="#169661", lw=1, ls="--", label="10 Å mean, plus AND=0")
            ax.scatter(wave[flagged] / 10, flux[flagged] / scale, color="#db8c21", s=8, zorder=5, label="Nonzero AND mask")
            ax.scatter(wave[rejected] / 10, flux[rejected] / scale, color="#cf3434", s=14, marker="x", zorder=6, label="Nonpositive IVAR")
            ax.set(xlim=(lower / 10, upper / 10), xlabel="Observed vacuum wavelength (nm)", ylabel="Fλ / fixed median (520–550 nm)")
            ax.grid(alpha=.17)
            if index == 7607 and number == 2:
                ax.set_ylim(-.15, 1.4)
                ax.set_title("Continuum zoom; full native extrema retained above", fontsize=9)
        axes[0].legend(loc="upper right", ncol=2, fontsize=8)
        if index == 7930:
            peak = info["narrow_peak_native_check"]["maximum_native_pixel_A"]
            axes[1].axvline(peak / 10, color="#b74161", ls=":", label=f"Native maximum {peak:.2f} Å")
            axes[1].legend(fontsize=8)
        fig.suptitle(f"Row {index}: {info['name']}\nNative SDSS morphology; MWDD label {info['MWDD_frozen_class']} retained as catalogue metadata", fontsize=14)
        fig.subplots_adjust(left=.08, right=.985, top=.86, bottom=.13, hspace=.36, wspace=.22)
        fig.text(.5, .025, "All curves are representations of one SDSS coadd. Mask comparison is diagnostic; no feature is removed from stored data.\n"
                 "Generic SDSS and specialist catalogue classifications can disagree; the accompanying record preserves the sources.", ha="center", fontsize=9)
        png, svg = HERE / f"native_row_{index}.png", HERE / f"native_row_{index}.svg"
        fig.savefig(png, dpi=170, facecolor="white")
        fig.savefig(svg, facecolor="white")
        plt.close(fig)
        records.append({"row_index": index, "png": png.name, "png_sha256": sha(png),
                        "svg": svg.name, "svg_sha256": sha(svg),
                        "prepared_only_not_a_visual_review": True})
    return records


if __name__ == "__main__":
    result, native = compute()
    result["created_utc"] = datetime.now(timezone.utc).isoformat()
    (HERE / "results.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    figures = make_figures(result, native)
    (HERE / "figures_manifest.json").write_text(json.dumps(figures, indent=2) + "\n")
    for index, data in native.items():
        selected = (data["wave"] >= 3600) & (data["wave"] <= 8300)
        pd.DataFrame({name: data[name][selected] for name in ("wave", "flux", "ivar", "and_mask", "or_mask")}).to_csv(
            HERE / f"native_row_{index}.csv.gz", index=False, float_format="%.17g", compression={"method": "gzip", "mtime": 0})
    print(json.dumps([{ "row_index": r["row_index"], "native_visible_quality": r["native_visible_quality"],
                       "association_point_check": r["association_point_check"],
                       "narrow_peak_native_check": r.get("narrow_peak_native_check")}
                      for r in result["records"]], indent=2))
