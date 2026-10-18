#!/usr/bin/env python3
"""Source-association and variability audit of frozen public ZTF DR24 data.

This is an observational stability audit, not a period or variable-star
discovery pipeline. Its statistics are conditional on detection-only catalogue
photometry, quality selection, independent Gaussian errors, and a stated floor.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd
from scipy import optimize, stats
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
RAW = BASE / "raw"
OUT = BASE / "results"
FLOOR = 0.02


def angular_distance(ra, dec, ra0, dec0):
    rr, dd, rr0, dd0 = map(np.deg2rad, (ra, dec, ra0, dec0))
    aa = np.sin((dd - dd0) / 2) ** 2 + np.cos(dd) * np.cos(dd0) * np.sin((rr - rr0) / 2) ** 2
    return np.rad2deg(2 * np.arcsin(np.sqrt(np.clip(aa, 0, 1)))) * 3600


def propagated(gaia, mjd):
    # Gaia pmra is mu_alpha*cos(delta), in mas/Julian year. This short-baseline
    # tangent approximation omits parallax (<0.013 arcsec for these targets)
    # and perspective acceleration. It is used for a >=0.5 arcsec association
    # test, not for precision orbit fitting.
    dt = (np.asarray(mjd) - 51544.5) / 365.25 + 2000 - float(gaia.ref_epoch)
    ra = float(gaia.ra) + dt * float(gaia.pmra) / 3_600_000 / np.cos(np.deg2rad(float(gaia.dec)))
    dec = float(gaia.dec) + dt * float(gaia.pmdec) / 3_600_000
    return ra, dec


def read_lc(oid):
    return pd.read_csv(RAW / f"ztf_dr24_oid_{oid}.csv", dtype={"oid": str, "expid": str})


def quality_mask(lc):
    finite = np.isfinite(lc[["mag", "magerr", "mjd", "hjd", "chi", "sharp", "clrcoeff"]]).all(axis=1)
    # There is no clipping on the value of the magnitude, on distance from
    # the mean, or on its quoted uncertainty's upper end.
    return finite & (lc.catflags == 0) & (lc.magerr > 0) & (lc.chi > 0) & (lc.chi < 3) & (abs(lc.sharp) < 0.5)


def fit_stats(y, error, t=None):
    y, error = np.asarray(y, float), np.asarray(error, float)
    n = len(y)
    if n < 3:
        return {"n": n}
    v = error**2
    w = 1 / v
    mu = np.sum(w * y) / np.sum(w)
    residual = y - mu
    q = float(np.sum(residual**2 / v))
    dof = n - 1
    # A Gaussian extra-scatter MLE is descriptive; the catalogue censoring,
    # possible blends, and time-correlated systematics prohibit treating it
    # as an intrinsic stellar-variability amplitude or an upper limit.
    def objective(extra):
        vv = v + extra**2
        ww = 1 / vv
        mm = np.sum(ww * y) / np.sum(ww)
        return float(np.sum(np.log(vv) + (y - mm)**2 / vv))
    best = optimize.minimize_scalar(objective, bounds=(0., max(0.5, np.std(y) * 2)), method="bounded")
    extra = float(best.x) if objective(best.x) < objective(0.) else 0.
    sigma = residual / error
    median = np.median(y)
    result = dict(n=n, weighted_mean_mag=float(mu), weighted_mean_formal_error_mag=float(1 / np.sqrt(np.sum(w))),
                  rms_mag=float(np.std(y, ddof=1)), robust_mad_sigma_mag=float(1.4826 * np.median(abs(y - median))),
                  median_quoted_error_mag=float(np.median(error)), reduced_chi2=q / dof, chi2=q, dof=dof,
                  log10_p_constant_conditional=float(stats.chi2.logsf(q, dof) / np.log(10)),
                  extra_scatter_mle_mag_descriptive=extra,
                  max_abs_standardized_residual=float(max(abs(sigma))), n_abs_standardized_residual_gt5=int(np.sum(abs(sigma) > 5)))
    # A predeclared diagnostic removes the most discrepant 1%, regardless of
    # whether it brightens or dims. The untrimmed result above remains primary.
    nkeep = max(3, n - max(1, int(np.ceil(n * 0.01))))
    idx = np.argsort(abs(sigma))[:nkeep]
    mm = np.sum(w[idx] * y[idx]) / np.sum(w[idx])
    result["remove_top1pct_reduced_chi2_diagnostic"] = float(np.sum(w[idx] * (y[idx] - mm)**2) / (nkeep - 1))
    result["remove_top1pct_n_removed"] = n - nkeep
    if t is not None and n >= 10:
        t = np.asarray(t, float)
        tx = (t - np.average(t, weights=w)) / 365.25
        xx = np.column_stack([np.ones(n), tx])
        cov = np.linalg.inv(xx.T @ (w[:, None] * xx))
        beta = cov @ (xx.T @ (w * y))
        residual_trend = y - xx @ beta
        trend_q = float(np.sum(residual_trend**2 / v))
        inflate = max(1., trend_q / (n - 2))
        result.update(mjd_min=float(min(t)), mjd_max=float(max(t)), baseline_days=float(max(t) - min(t)),
                      trend_mag_per_year=float(beta[1]),
                      trend_se_mag_per_year_scatter_scaled=float(np.sqrt(cov[1, 1] * inflate)))
    return result


def finite_json(value):
    if isinstance(value, dict):
        return {k: finite_json(v) for k, v in value.items()}
    if isinstance(value, list):
        return [finite_json(v) for v in value]
    if isinstance(value, (np.integer, np.floating)):
        value = value.item()
    if isinstance(value, float) and not np.isfinite(value):
        return None
    return value


def target_prepare(selection, gaia, anchors):
    prepared, audit = [], []
    all_associations = []
    for rec in selection:
        if not rec["selected"]:
            continue
        name, oid = rec["candidate"], rec["oid"]
        g = gaia.loc[rec["gaia_source_id"]]
        lc = read_lc(oid)
        ra, dec = propagated(g, lc.mjd)
        lc["target_sep_epoch_arcsec"] = angular_distance(lc.ra, lc.dec, ra, dec)
        lc["target_sep_gaia2016_arcsec"] = angular_distance(lc.ra, lc.dec, float(g.ra), float(g.dec))
        lc["candidate"] = name
        lc["gaia_source_id"] = rec["gaia_source_id"]
        lc["quality_ok"] = quality_mask(lc)
        lc["association_ok"] = lc.target_sep_epoch_arcsec < 1.5
        fid = int(rec["fid"])
        band = {1: "g", 2: "r", 3: "i"}[fid]
        anchor = anchors.loc[name]
        if fid in (1, 2):
            color = float(anchor.anchor_g_mag - anchor.anchor_r_mag)
        else:
            color = float(anchor.anchor_r_mag - anchor.anchor_i_mag)
        lc["adopted_ps1_color_mag"] = color
        lc["mag_colorcorrected"] = lc.mag + lc.clrcoeff * color
        lc["error_with_002_floor"] = np.sqrt(lc.magerr**2 + FLOOR**2)
        lc["accepted"] = lc.quality_ok & lc.association_ok
        kept = lc[lc.accepted].copy()
        duplicate_count = int(kept.duplicated(["expid", "field", "ccdid", "qid", "filtercode"]).sum())
        kept = kept.drop_duplicates(["expid", "field", "ccdid", "qid", "filtercode"])
        # Record every observation's acceptance decision, including rejected
        # points; consumers need not reverse-engineer the quality selection.
        all_associations.append(lc)
        stats_raw = fit_stats(kept.mag, kept.error_with_002_floor, kept.mjd)
        stats_corr = fit_stats(kept.mag_colorcorrected, kept.error_with_002_floor, kept.mjd)
        row = dict(candidate=name, gaia_source_id=rec["gaia_source_id"], oid=oid, band=band,
                   field=int(rec["field"]), ccdid=int(rec["ccdid"]), qid=int(rec["qid"]),
                   n_downloaded=len(lc), n_quality_ok=int(lc.quality_ok.sum()),
                   n_rejected_epoch_association=int((lc.quality_ok & ~lc.association_ok).sum()),
                   n_duplicate_exposure_rows=duplicate_count,
                   epoch_sep_median_arcsec=float(kept.target_sep_epoch_arcsec.median()),
                   epoch_sep_p95_arcsec=float(kept.target_sep_epoch_arcsec.quantile(.95)),
                   fixed2016_sep_median_arcsec=float(kept.target_sep_gaia2016_arcsec.median()),
                   native=stats_raw, colorcorrected=stats_corr,
                   assumed_ps1_color_mag=color,
                   colorcorrection_mean_mag=float((kept.mag_colorcorrected-kept.mag).mean()))
        sensitivity = {}
        for radius in [0.5, 1.0, 1.5]:
            sub = kept[kept.target_sep_epoch_arcsec < radius]
            sensitivity[str(radius)] = fit_stats(sub.mag_colorcorrected, sub.error_with_002_floor, sub.mjd)
        row["association_radius_sensitivity_arcsec"] = sensitivity
        # Rank correlations are diagnostics of known observational covariates,
        # not independently corrected statistical discoveries.
        row["exploratory_correlations"] = {}
        for col in ["airmass", "chi", "sharp", "target_sep_epoch_arcsec", "clrcoeff", "limitmag"]:
            if len(kept) > 10:
                rho, pval = stats.spearmanr(kept.mag_colorcorrected, kept[col], nan_policy="omit")
                row["exploratory_correlations"][col] = dict(rho=float(rho), p_unadjusted=float(pval))
        audit.append(row)
        prepared.append(kept)
    observations = pd.concat(all_associations, ignore_index=True)
    observations.to_csv(OUT / "target_epoch_decisions.csv.gz", index=False, compression={"method": "gzip", "mtime": 0})
    return pd.concat(prepared, ignore_index=True), audit


def controls_prepare(selection):
    prepared, summaries = {}, []
    for rec in selection:
        oid = rec["oid"]
        lc = read_lc(oid)
        kept = lc[quality_mask(lc)].copy()
        kept = kept.drop_duplicates(["expid", "field", "ccdid", "qid", "filtercode"])
        kept["error_with_002_floor"] = np.sqrt(kept.magerr**2 + FLOOR**2)
        w = 1 / kept.error_with_002_floor.to_numpy()**2
        color_term = kept.clrcoeff.to_numpy() - np.average(kept.clrcoeff, weights=w)
        x = np.column_stack([np.ones(len(kept)), color_term])
        # Control colors are not assumed to equal the white dwarf colors.
        # Regressing the native magnitudes against their time-varying color
        # coefficient removes a nuisance calibration trend. It is not an
        # astrophysical measurement of the control's color.
        beta = np.linalg.lstsq(x * np.sqrt(w[:, None]), kept.mag.to_numpy() * np.sqrt(w), rcond=None)[0]
        kept["control_residual_centered_only"] = kept.mag - np.average(kept.mag, weights=w)
        kept["control_residual"] = kept.mag - x @ beta
        prepared[oid] = kept
        summaries.append(dict(oid=oid, candidate_field=rec["candidate_field"],
                              n_downloaded=len(lc), n_used=len(kept), median_mag=float(kept.mag.median()),
                              distance_arcsec=rec["distance_arcsec"], nuisance_color_slope=float(beta[1]),
                              raw=fit_stats(kept.mag, kept.error_with_002_floor, kept.mjd),
                              nuisance_detrended=fit_stats(kept.control_residual, kept.error_with_002_floor, kept.mjd)))
    return prepared, summaries


def ensemble_series(target, controls):
    rows = []
    lookup = {oid: lc.set_index("expid") for oid, lc in controls.items()}
    for _, point in target.iterrows():
        residual, errors, ids = [], [], []
        for oid, lc in lookup.items():
            if point.expid in lc.index:
                match = lc.loc[point.expid]
                residual.append(float(match.control_residual))
                errors.append(float(match.error_with_002_floor))
                ids.append(oid)
        if len(residual) < 2:
            continue
        offset = float(np.median(residual))
        # Approximate standard error of a median for comparable independent
        # Gaussian uncertainties. Real covariance is not supplied by ZTF.
        control_se = float(1.253314 * np.sqrt(np.sum(np.array(errors)**2)) / len(errors))
        rows.append(dict(oid=point.oid, expid=point.expid, mjd=point.mjd,
                         mag_colorcorrected=point.mag_colorcorrected, comparison_offset_mag=offset,
                         target_error=float(point.error_with_002_floor),
                         n_controls=len(ids), controls=";".join(ids),
                         differential_mag=float(point.mag_colorcorrected-offset),
                         differential_error_mag=float(np.hypot(point.error_with_002_floor, control_se))))
    return pd.DataFrame(rows)


def main():
    OUT.mkdir(exist_ok=True)
    gaia = pd.read_csv(RAW / "gaia_dr3_15arcsec_fields.csv", dtype={"source_id": str}).set_index("source_id")
    anchors = pd.read_csv(ROOT / "results/headline_candidates.csv", dtype={"source_id": str}).set_index("candidate")
    selected = json.loads((BASE / "ztf_object_selection.json").read_text())
    ctrl_selection = json.loads((BASE / "control_selection.json").read_text())
    targets, per_oid = target_prepare(selected, gaia, anchors)
    controls, ctrl_stats = controls_prepare(ctrl_selection)
    differential_results, differential_points = [], []
    primary_rows, epoch_outliers = [], []
    all_seasons = []
    for name, group in targets.groupby("candidate", sort=False):
        candidate_stats = [r for r in per_oid if r["candidate"] == name]
        for band in ["g", "r", "i"]:
            choices = [r for r in candidate_stats if r["band"] == band]
            if not choices:
                continue
            primary = max(choices, key=lambda r: r["colorcorrected"]["n"])
            lc = group[group.oid == primary["oid"]].copy()
            row = {k: primary[k] for k in ["candidate", "gaia_source_id", "band", "oid", "field", "ccdid", "qid"]}
            row.update(primary["colorcorrected"])
            row["n_downloaded"] = primary["n_downloaded"]
            row["epoch_sep_median_arcsec"] = primary["epoch_sep_median_arcsec"]
            row["native_reduced_chi2"] = primary["native"]["reduced_chi2"]
            primary_rows.append(row)
            lc["calendar_year"] = (2000 + (lc.mjd-51544.5)/365.25).astype(int)
            for year, season in lc.groupby("calendar_year"):
                if len(season) >= 3:
                    ss = fit_stats(season.mag_colorcorrected, season.error_with_002_floor)
                    all_seasons.append(dict(candidate=name, oid=primary["oid"], band=band, calendar_year=int(year), **ss))
            residual = lc.mag_colorcorrected - primary["colorcorrected"]["weighted_mean_mag"]
            lc["standardized_residual"] = residual / lc.error_with_002_floor
            worst = lc.loc[abs(lc.standardized_residual).nlargest(5).index]
            epoch_outliers.extend(worst.to_dict(orient="records"))
            if band != "r":
                continue
            cnames = [c["oid"] for c in ctrl_selection if c["candidate_field"] == name]
            ctrl_map = {oid: controls[oid] for oid in cnames}
            dif = ensemble_series(lc, ctrl_map)
            if len(dif) < 10:
                differential_results.append(dict(candidate=name, oid=primary["oid"], status="insufficient common exposures", n=len(dif)))
                continue
            dif["candidate"] = name
            differential_points.append(dif)
            before = fit_stats(dif.mag_colorcorrected, dif.target_error, dif.mjd)
            before_with_comparison_errors = fit_stats(dif.mag_colorcorrected, dif.differential_error_mag, dif.mjd)
            after = fit_stats(dif.differential_mag, dif.differential_error_mag, dif.mjd)
            centered_control_map = {}
            for oid, frame in ctrl_map.items():
                frame = frame.copy()
                frame["control_residual"] = frame.control_residual_centered_only
                centered_control_map[oid] = frame
            centered_only = ensemble_series(lc, centered_control_map)
            centered_only_stats = fit_stats(centered_only.differential_mag, centered_only.differential_error_mag, centered_only.mjd)
            leave_one_out = []
            for omit in cnames:
                dd = ensemble_series(lc, {oid: ctrl for oid, ctrl in ctrl_map.items() if oid != omit})
                if len(dd) >= 10:
                    leave_one_out.append(dict(omitted_oid=omit, **fit_stats(dd.differential_mag, dd.differential_error_mag, dd.mjd)))
            differential_results.append(dict(candidate=name, oid=primary["oid"], status="audited",
                                             n_selected_controls=len(cnames), native_on_same_exposures=before,
                                             uncorrected_with_same_total_errors=before_with_comparison_errors,
                                             differential=after, leave_one_control_out=leave_one_out))
            differential_results[-1]["differential_without_control_color_regression"] = centered_only_stats

    pd.DataFrame(primary_rows).to_csv(OUT / "primary_lightcurve_summary.csv", index=False)
    pd.DataFrame(all_seasons).to_csv(OUT / "seasonal_summary.csv", index=False)
    pd.DataFrame(epoch_outliers).to_csv(OUT / "epoch_outliers_for_image_review.csv", index=False)
    if differential_points:
        pd.concat(differential_points, ignore_index=True).to_csv(OUT / "differential_r_epochs.csv.gz", index=False,
                                                               compression={"method": "gzip", "mtime": 0})
    # Plot the primary per-band measurements on a common epoch axis. Errorbars
    # remain visible; the eye is not asked to infer certainty from a smoothed fit.
    fig, axes = plt.subplots(4, 3, figsize=(15, 11), sharex=True)
    names = ["J0913+4434", "J0429-0354", "J1329+0033", "J1323-0129"]
    colors = dict(g="#12855e", r="#a54b32", i="#6b4a93")
    for ii, name in enumerate(names):
        for jj, band in enumerate(["g", "r", "i"]):
            ax = axes[ii, jj]
            match = [r for r in primary_rows if r["candidate"] == name and r["band"] == band]
            if not match:
                ax.text(.5, .5, "No matched released light curve", transform=ax.transAxes, ha="center", fontsize=9)
                ax.set_title(f"{name} · {band}", fontsize=10)
                ax.set_yticks([])
                continue
            s = match[0]
            lc = targets[targets.oid == s["oid"]]
            ax.errorbar(2000+(lc.mjd-51544.5)/365.25, lc.mag_colorcorrected, yerr=lc.error_with_002_floor,
                        fmt=".", color=colors[band], alpha=.45, markersize=3, linewidth=.5)
            ax.axhline(s["weighted_mean_mag"], color="#283449", linewidth=1)
            ax.invert_yaxis()
            ax.set_title(f"{name} · {band} · n={s['n']} · χ²ν={s['reduced_chi2']:.2f}", fontsize=10)
            ax.grid(alpha=.15)
            if jj == 0:
                ax.set_ylabel("Color-corrected magnitude")
            if ii == 3:
                ax.set_xlabel("Julian year")
    fig.suptitle("Independent ZTF observations: stability and calibration audit", fontsize=16, y=.995)
    fig.tight_layout(rect=[0, .02, 1, .985])
    fig.text(.02, .005, "Primary object ID per filter; catflags=0; shape and epoch-position cuts; 0.02 mag error floor. Detection-only data; no nonvariability upper limits.", fontsize=9)
    fig.savefig(OUT / "ztf_primary_lightcurves.png", dpi=160)
    plt.close(fig)

    summary = dict(analysis_utc=datetime.now(timezone.utc).isoformat(), collection="ztf_dr24",
                   n_candidate_lightcurves=len(per_oid), n_target_raw_epochs=int(sum(r["n_downloaded"] for r in per_oid)),
                   n_target_accepted_epochs=int(len(targets)), n_control_lightcurves=len(ctrl_stats),
                   n_target_accepted_duplicate_exposures=int(targets.duplicated(["candidate","expid","filtercode","ccdid","qid"]).sum()),
                   n_control_raw_epochs=int(sum(r["n_downloaded"] for r in ctrl_stats)),
                   adopted_mag_error_floor=FLOOR, baseline_epoch_association_radius_arcsec=1.5,
                   observed_data_type="Released detection-only PSF-catalogue light curves; not forced photometry or difference fluxes",
                   independence="Different instrument and epochs from DESI/Gaia/PS1. ZTF absolute calibration uses PS1, and adopted color terms use the existing PS1 anchors; not statistically independent absolute color confirmation.",
                   candidate_lightcurves=per_oid, primary_lightcurves=primary_rows,
                   control_lightcurves=ctrl_stats, differential_r=differential_results,
                   limits=["No search over periods was performed; sparse cadence does not exclude short events or rotation.",
                           "Gaussian chi-square p values are diagnostics conditional on the noise and censoring assumptions, not new-variable probabilities.",
                           "The 1.5 arcsec match uses linear proper motion; parallax and perspective acceleration omitted at a much smaller angular scale.",
                           "No forced photometry, full image review, survey injection/recovery or physical variability model was performed.",
                           "Control stars were selected by field, position, magnitude and shape, not by small variability. Their astrophysical stability is not assumed proven.",
                           "A constant broadband light curve would not by itself prove constant detailed spectral shape or a perceived hue."])
    (OUT / "ztf_audit.json").write_text(json.dumps(finite_json(summary), indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    print(json.dumps({k: summary[k] for k in ["n_candidate_lightcurves", "n_target_raw_epochs", "n_target_accepted_epochs", "n_control_lightcurves", "n_control_raw_epochs"]}, indent=2))
    print(pd.DataFrame(primary_rows)[["candidate", "band", "n", "reduced_chi2", "remove_top1pct_reduced_chi2_diagnostic", "trend_mag_per_year"]].to_string(index=False))
    for row in differential_results:
        print(row["candidate"], row["status"], row.get("differential", {}).get("reduced_chi2"))


if __name__ == "__main__":
    main()
