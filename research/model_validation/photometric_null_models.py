#!/usr/bin/env python3
"""Offline gri-only atmosphere-template predictions for unused z/y photometry.

Uses the original public Montreal pure-H / pure-He magnitude tables, not
native DZ/DQ spectra. Fits one temperature and an arbitrary magnitude offset
at each fixed gravity. No z/y value participates in minimization, choice of
gravity or selection of a template family. No downloads and no core edits.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import gzip
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

TRAIN = "gri"
GRAVITIES = (7., 7.5, 8., 8.5, 9.)
ERROR_MIN_MAG = .02
HEADLINES = {
    "818833831355548928": "J0913+4434",
    "3204436719718449280": "J0429-0354",
    "1078624858218235776": "J1105+7247",
    "3711047662972690688": "J1329+0033",
    "3638333660492606976": "J1323-0129",
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def json_read(path):
    with (gzip.open(path, "rt") if path.suffix == ".gz" else path.open()) as stream:
        return json.load(stream)


def number(value):
    try:
        return float(value)
    except (ValueError, TypeError):
        return np.nan


def load_models(base):
    source = json_read(base / "sources/model_sources.json")
    result = {}
    for item in source["models"]:
        path = base / "sources" / item["file"]
        assert sha(path) == item["sha256"], path
        columns = path.read_text().splitlines()[1].replace("log g", "logg").split()
        assert columns[25:35] == ["u", "g", "r", "i", "z", "g", "r", "i", "z", "y"]
        data = np.loadtxt(path, skiprows=2)
        assert data.shape[1] == len(columns) == 44
        assert set(data[:, 1]) == set(GRAVITIES)
        assert np.all(np.isfinite(data))
        result[item["file"].removeprefix("Table_")] = data
    return result


def fit_gravity(table, observed_gri, uncertainty_gri, survey, gravity):
    """Global minimum over every piecewise-linear log(T) interval.

    Magnitudes are interpolated linearly against log(T). The free constant
    is projected out analytically. The remaining objective is quadratic in
    each interval; clipping its analytic minimum to [0,1] checks endpoints
    too. This avoids an optimizer choosing one branch of cool-H CIA colours.
    """
    rows = table[table[:, 1] == gravity]
    rows = rows[np.argsort(rows[:, 0])]
    bands = "grizy" if survey == "PS1" else "griz"
    positions = [30, 31, 32, 33, 34] if survey == "PS1" else [26, 27, 28, 29]
    model = rows[:, positions]
    origin, delta = model[:-1], np.diff(model, axis=0)
    weight = 1 / np.maximum(uncertainty_gri, ERROR_MIN_MAG)**2
    difference = observed_gri[None, :] - origin[:, :3]
    centered_difference = difference - np.average(difference, axis=1, weights=weight)[:, None]
    centered_delta = delta[:, :3] - np.average(delta[:, :3], axis=1, weights=weight)[:, None]
    denominator = np.sum(weight * centered_delta**2, axis=1)
    fraction = np.divide(np.sum(weight * centered_difference * centered_delta, axis=1),
                         denominator, out=np.zeros_like(denominator), where=denominator > 0)
    fraction = np.clip(fraction, 0, 1)
    predicted_absolute = origin + fraction[:, None] * delta
    offset = np.average(observed_gri[None, :] - predicted_absolute[:, :3], axis=1, weights=weight)
    prediction = predicted_absolute + offset[:, None]
    residual = prediction[:, :3] - observed_gri[None, :]
    objective = np.sum(weight * residual**2, axis=1)
    best = int(np.argmin(objective))
    temperature = float(np.exp(np.log(rows[best, 0]) + fraction[best] * np.log(rows[best+1, 0] / rows[best, 0])))
    return {
        "template_teff_K": temperature,
        "fixed_logg": gravity,
        "free_magnitude_offset": float(offset[best]),
        "gri_weighted_squared_residual": float(objective[best]),
        "gri_max_abs_residual_mag": float(np.max(np.abs(residual[best]))),
        "gri_within_0p05mag": bool(np.max(np.abs(residual[best])) <= .05),
        "grid_min_teff_K": float(rows[0, 0]), "grid_max_teff_K": float(rows[-1, 0]),
        "at_native_temperature_boundary": bool(np.isclose(temperature, rows[0, 0]) or np.isclose(temperature, rows[-1, 0])),
        "lower_bracketing_teff_K": float(rows[best, 0]),
        "upper_bracketing_teff_K": float(rows[best+1, 0]),
        "logT_interval_fraction": float(fraction[best]),
        **{f"predicted_{b}_mag": float(prediction[best, i]) for i, b in enumerate(bands)},
        **{f"train_{b}_residual_mag": float(residual[best, i]) for i, b in enumerate(TRAIN)},
    }


def inputs(root):
    prior_path = root / "research/literature/sources/candidate27_prior_rows.json"
    prior = json_read(prior_path)
    objects = []
    for sid in prior["source_ids"]:
        entry = prior["candidates"][sid]
        photometry = entry["swan_external"]
        row = {"source_id": sid, "object_key": sid, "sample": "candidate", "survey": "PS1"}
        if not photometry:
            row.update(name=sid, spectral_type="", status="no_exact_Swan_photometry", missing_reason="No exact-ID Swan external-photometry row in fixed 27-candidate snapshot")
        else:
            assert len(photometry) == 1
            measurement = photometry[0]
            name = measurement["WDJname"]
            spec = entry["swan_catalogue"][0]["specType"]
            row.update(name=HEADLINES.get(sid, name), spectral_type=spec, status="available", missing_reason="")
            for band in "grizy":
                row[f"observed_{band}_mag"] = number(measurement[f"Pan-STARRS.{band}"])
                row[f"observed_{band}_error_mag"] = number(measurement[f"Pan-STARRS.{band}_error"])
            if not all(np.isfinite(row[f"observed_{b}_mag"]) and np.isfinite(row[f"observed_{b}_error_mag"]) and row[f"observed_{b}_error_mag"] > 0 for b in TRAIN):
                row.update(status="invalid_gri", missing_reason="Nonfinite or nonpositive-error gri measurement")
        objects.append(row)
    controls_path = root / "sdss/manifest_with_photometry.json.gz"
    controls = [r for r in json_read(controls_path) if r.get("selection_group", "").startswith("control_")]
    assert len(controls) == len({r["photometry_objid"] for r in controls}) == 54
    for item in controls:
        row = {"source_id": "", "object_key": str(item["photometry_objid"]), "name": item["name"],
               "sample": item["selection_group"], "survey": "SDSS", "spectral_type": item["type"],
               "status": "available", "missing_reason": "", "photometry_clean": item["photometry_clean"],
               "photometry_source_sha256": item["photometry_sha256"], "spectrum_id": item["spectrum_id"],
               "catalogue_ebv_full_sightline": item["ebv"]}
        for band in "griz":
            row[f"observed_{band}_mag"] = number(item[f"{band}_psf_mag"])
            row[f"observed_{band}_error_mag"] = number(item[f"{band}_psf_mag_err"])
        quality = item["photometry_clean"] == 1 and all(np.isfinite(row[f"observed_{b}_mag"]) and 0 < row[f"observed_{b}_error_mag"] < .1 for b in "griz")
        if not quality:
            row.update(status="control_photometry_quality_excluded", missing_reason="Require SDSS clean=1 and finite griz magnitudes with 0 < reported errors < 0.1 mag; no residual-based selection")
        row["y_missing_reason"] = "SDSS has no y filter in this input"
        objects.append(row)
    return objects, [prior_path, controls_path]


def residual_summary(frame, band):
    column = f"heldout_{band}_predicted_minus_observed_mag"
    x = frame[column].dropna().to_numpy(float)
    return {"count": len(x), "median_mag": float(np.median(x)) if len(x) else None,
            "max_abs_mag": float(np.max(np.abs(x))) if len(x) else None,
            "abs_over_0p05mag": int(np.sum(np.abs(x) > .05)),
            "abs_over_0p10mag": int(np.sum(np.abs(x) > .1))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    root = args.root.resolve(); base = root / "research/model_validation"
    models = load_models(base)
    objects, source_paths = inputs(root)
    rows = []
    for obj in objects:
        if obj["status"] != "available":
            continue
        observed = np.array([obj[f"observed_{b}_mag"] for b in TRAIN])
        error = np.array([obj[f"observed_{b}_error_mag"] for b in TRAIN])
        for family, table in models.items():
            for gravity in GRAVITIES:
                fit = fit_gravity(table, observed, error, obj["survey"], gravity)
                row = {**obj, "family": family, **fit}
                for band in "zy":
                    prediction = fit.get(f"predicted_{band}_mag", np.nan)
                    measurement = obj.get(f"observed_{band}_mag", np.nan)
                    row[f"heldout_{band}_predicted_minus_observed_mag"] = prediction - measurement
                # DR17 describes z_AB = z_SDSS + 0.02 as an uncertain
                # estimate. Keep native catalogue values as the primary
                # method-control comparison, and expose this convention
                # sensitivity without selecting a correction by residual.
                row["heldout_z_if_sdss_plus0p02_AB_mag"] = (row["heldout_z_predicted_minus_observed_mag"] - .02) if obj["survey"] == "SDSS" else np.nan
                rows.append(row)
    frame = pd.DataFrame(rows)
    frame.to_csv(base / "photometric_predictions.csv", index=False)
    primary = frame.loc[frame.fixed_logg == 8].copy()
    primary.to_csv(base / "photometric_predictions_logg8.csv", index=False)
    object_frame = pd.DataFrame(objects)
    object_frame.to_csv(base / "photometric_input_coverage.csv", index=False)

    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(), "script_sha256": sha(Path(__file__)),
        "input_sha256": {str(p.relative_to(root)): sha(p) for p in source_paths + [base/"sources/model_sources.json", base/"sources/Table_DA", base/"sources/Table_DB"]},
        "candidate_rows": int(sum(r["sample"] == "candidate" for r in objects)),
        "candidate_available": int(sum(r["sample"] == "candidate" and r["status"] == "available" for r in objects)),
        "control_rows": 54,
        "control_available": dict(Counter(r["sample"] for r in objects if r["sample"] != "candidate" and r["status"] == "available")),
        "all_fits": len(frame), "primary_fits": len(primary),
        "primary_fixed_logg": 8., "gravity_sensitivity": list(GRAVITIES),
        "fitting": "Use only observed gri magnitudes. At each fixed logg, globally minimize diagonal weighted squared residual in all native log(Teff) intervals plus free additive magnitude scale. Linear interpolation in magnitude vs log(Teff), no extrapolation. z/y never enter fitting or selection.",
        "error_handling": "Use max(reported error, 0.02 mag) in gri; do not add another Swan floor. Weights are a numerical fitting convention, not a complete covariance or significance model.",
        "extinction": "Observed magnitudes are not dereddened; no inferred reddening or distance. SDSS full-sightline extinction is preserved as metadata but not applied as though each nearby star were behind all dust.",
        "sdss_zero_point": "Primary SDSS controls use reported near-AB PSF magnitudes and the model's SDSS columns. DR17 documents an uncertain estimate z_AB=z_SDSS+0.02; the heldout_z_if_sdss_plus0p02_AB_mag column carries this separate sensitivity, reducing every SDSS z residual by 0.02 without changing gri fits. No zero point is fitted from controls. SDSS DR17 hypercalibration itself uses PS1, so these are separate objects/filter-system checks, not independently calibrated PS1 controls.",
        "sdss_zero_point_source": "https://www.sdss4.org/dr17/algorithms/fluxcal/",
        "scientific_scope": "Restricted pure-H/pure-He atmospheric null templates. No DZ/DQ abundance fitting, no native spectral model residuals, no physical-parameter inference or discovery significance. SDSS controls validate the fitting procedure in their own filter system; they are not a selection- or survey-matched population for candidate excess rates.",
        "model_version_limit": "Both downloaded tables are dated 2021-01-13; the explanatory web page says updated 2020-08-18. They predate the H3+ partition-function correction reported by Kilic et al. 2026 section II.1 (divide by 8, reducing H3+ and H-minus opacity). These old pure-composition templates are not the updated 2026 DZ/DQ/mixed H-He models. Their prediction failures, especially for ultracool J1323-0129, cannot establish failures of current atmosphere models, an additional component or new physics.",
        "model_version_source": "https://arxiv.org/html/2606.25377v2#S2.SS1",
        "interpolation_precision": "Original magnitude table values have 0.001 mag decimal precision; computed digits are reproducibility digits, not physical precision.",
        "model_ranges": {family: {"rows": len(data), "teff_min_K": float(data[:,0].min()), "teff_max_K": float(data[:,0].max())} for family,data in models.items()},
        "groups": [],
    }
    for (sample, family), group in primary.groupby(["sample", "family"], sort=True):
        summary["groups"].append({"sample": sample, "family": family, "count": len(group),
            "gri_within_0p05mag": int(group.gri_within_0p05mag.sum()),
            "temperature_boundary": int(group.at_native_temperature_boundary.sum()),
            "z": residual_summary(group, "z"), "y": residual_summary(group, "y")})

    # Every input is retained, including unavailable or rejected measurements.
    assert len(objects) == 81 and summary["candidate_available"] == 25
    assert summary["control_available"] == {"control_DA": 14, "control_DC": 17, "control_DB": 16}
    assert len(frame) == 720 and len(primary) == 144
    for family, table in models.items():
        # A synthetic native-grid point must recover its own gri and
        # unseen bands; compare predictions, since Teff can be degenerate.
        native = table[table[:,1] == 8]
        chosen = native[np.argmin(np.abs(native[:,0] - 6000))]
        fit = fit_gravity(table, chosen[[30,31,32]] + 7., np.full(3,.03), "PS1", 8.)
        np.testing.assert_allclose([fit[f"predicted_{b}_mag"] for b in "grizy"], chosen[[30,31,32,33,34]]+7., atol=2e-10, rtol=0)
    summary["verification"] = "PASS: original table hashes; explicit survey columns; fixed input coverage; all intervals searched; two known-template recovery checks."
    (base / "photometric_summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False)+"\n")

    candidates = primary.loc[primary["sample"] == "candidate"]
    order = candidates.loc[candidates.family == "DA"].sort_values("object_key")["object_key"].tolist()
    names = {r["object_key"]: r["name"] for r in objects}
    fig, axes = plt.subplots(2, 2, figsize=(13, 10), gridspec_kw={"height_ratios": [3, 2]})
    colors = {"DA": "#0072B2", "DB": "#D55E00"}
    for column, band in enumerate("zy"):
        ax = axes[0,column]
        for family, dx in (("DA",-.12),("DB",.12)):
            s = candidates.loc[candidates.family == family].set_index("object_key").loc[order]
            residual = s[f"heldout_{band}_predicted_minus_observed_mag"].to_numpy()
            ax.scatter(residual, np.arange(len(order))+dx, s=30, color=colors[family], label="pure H" if family == "DA" else "pure He")
            full = frame.loc[(frame["sample"] == "candidate") & (frame.family == family)]
            for n, key in enumerate(order):
                variation = full.loc[full.object_key == key, f"heldout_{band}_predicted_minus_observed_mag"]
                ax.plot([variation.min(),variation.max()],[n+dx,n+dx],color=colors[family],alpha=.4,lw=2)
        ax.axvline(0,color=".3",lw=.8); ax.axvspan(-.05,.05,color=".92",zorder=0)
        ax.set_yticks(np.arange(len(order)),[names[k].replace("WDJ","") for k in order],fontsize=7)
        ax.invert_yaxis(); ax.set_xlabel(f"Predicted minus observed {band} [mag]")
        ax.set_title(f"PS1 candidate {band}: gri-only fit; log g=8",fontsize=11)
        if column == 0: ax.legend(fontsize=8,loc="best")
    for j, family in enumerate(("DA","DB")):
        ax=axes[1,j]
        for k, sample in enumerate(("control_DA","control_DB","control_DC")):
            values=primary.loc[(primary.family==family)&(primary["sample"]==sample),"heldout_z_predicted_minus_observed_mag"]
            # Deterministic horizontal spacing shows every measurement.
            ax.scatter(k+np.linspace(-.12,.12,len(values)),values,s=25,label=sample.replace("control_", ""))
        ax.axhline(0,color=".3",lw=.8); ax.axhspan(-.05,.05,color=".92",zorder=0)
        ax.set_xticks([0,1,2],["DA (14)","DB (16)","DC (17)"])
        ax.set_ylabel("SDSS predicted minus observed z [mag]")
        ax.set_title(("Pure H" if family=="DA" else "Pure He")+" template: separate SDSS method controls",fontsize=10)
    fig.suptitle("Restricted atmospheric null models: unused bands test the gri fit", fontsize=14)
    fig.text(.5,.013,"Lines: range over fixed log g=7, 7.5, 8, 8.5, 9; not confidence intervals.\nOld 2021 pure H/He grids; not updated 2026 DZ/DQ models; no dust correction.",ha="center",fontsize=9)
    fig.tight_layout(rect=[0,.045,1,.97])
    fig.savefig(base/"photometric_predictions.png",dpi=160)
    plt.close(fig)
    print(f"PASS pure-atmosphere held-out experiment: {summary['candidate_available']}/27 candidates, 47/54 quality controls, {len(frame)} fits; no z/y fitting")
    for group in summary["groups"]:
        if group["sample"] == "candidate": print(json.dumps(group))


if __name__ == "__main__":
    main()
