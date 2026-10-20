#!/usr/bin/env python3
"""Join the initial 27-target follow-up evidence without pooling probabilities.

Run from any working directory: .venv-research/bin/python research/candidate_followup.py
All joins use string Gaia IDs. Only derived outputs beside this file are written.
"""
from __future__ import annotations
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "research"
THRESHOLD = 0.01
SHIFT_THRESHOLD = 0.003
INPUTS = {
    "initial27": "research/external_validation/gaia_extended_input.csv",
    "desi": "research/precision/candidate_recalibration/standardized_colours.csv",
    "desi_summary": "research/precision/candidate_recalibration/summary.json",
    "heldout_z": "research/precision/candidate_recalibration/heldout_z.csv",
    "gaia": "research/precision/gaia_expanded/formal_colour_results.csv",
    "gaia_reconstruction": "research/precision/gaia_expanded/reconstruction.json",
    "quality": "research/external_validation/results/gaia_extended_quality.csv",
    "neighbours": "research/external_validation/results/gaia_extended_neighbours.csv",
    "prior": "research/literature/outputs/candidate27_prior_inventory.csv",
    "nights": "research/literature/outputs/desi_additional_nights_summary.csv",
    "exposures": "research/literature/outputs/candidate27_desi_exposure_inventory.csv",
    "j1329_second_night": "research/literature/outputs/j1329_second_epoch_comparison.json",
    "sdss_units": "research/precision/flux_units/candidate27_sdss_convention_impact.json",
    "photometry_definition": "research/literature/swan_photometry_definition.md",
}
def read_csv(key):
    return pd.read_csv(ROOT / INPUTS[key], dtype=str, keep_default_na=False)
def number(value):
    try:
        value = float(value)
        return value if np.isfinite(value) else None
    except (ValueError, TypeError):
        return None
def integer(value):
    v = number(value)
    return int(v) if v is not None else None
def flag(value):
    return str(value).lower() == "true"
def interval_side(lo, hi):
    if lo is None or hi is None:
        return None
    if lo > THRESHOLD:
        return 1
    if hi < -THRESHOLD:
        return -1
    return 0
def boundary_span(lo, hi):
    if lo is None or hi is None:
        return None
    return any(lo <= x <= hi for x in (-THRESHOLD, THRESHOLD))
def distance(a, b):
    if any(v is None for v in (*a, *b)):
        return None
    return float(np.hypot(a[0]-b[0], a[1]-b[1]))
def safe_text(v):
    return str(v).replace("|", ";").replace("\n", " ")
def interval_text(r, prefix):
    lo, hi = r.get(prefix+"_p025"), r.get(prefix+"_p975")
    if lo is None or hi is None:
        return "Unavailable"
    return f'{r[prefix+"_median"]:+.5f} [{lo:+.5f}, {hi:+.5f}]'
def source_link(key):
    return INPUTS[key].removeprefix("research/")

def build():
    initial, desi, gaia = read_csv("initial27"), read_csv("desi"), read_csv("gaia")
    quality, neighbours = read_csv("quality"), read_csv("neighbours")
    prior, nights, exposures = read_csv("prior"), read_csv("nights"), read_csv("exposures")
    heldout = read_csv("heldout_z").set_index("source_id").to_dict("index")
    initial_ids = initial.source_id.tolist()
    assert len(initial_ids) == len(set(initial_ids)) == 27
    for table in (desi, quality, prior):
        assert table.source_id.is_unique
        assert set(table.source_id) == set(initial_ids), "Input population changed"
    assert not gaia.duplicated(["source_id", "reconstruction"]).any()
    assert set(gaia.reconstruction) == {"full", "truncated"}
    desi, quality, prior = [x.set_index("source_id").to_dict("index") for x in (desi, quality, prior)]
    gaia = {(r["source_id"], r["reconstruction"]): r for r in gaia.to_dict("records")}
    unit_data = json.loads((ROOT / INPUTS["sdss_units"]).read_text())
    units = {}
    for row in unit_data["sdss_records"]:
        units.setdefault(str(row["source_id"]), []).append(row)
    summary_input = json.loads((ROOT / INPUTS["desi_summary"]).read_text())
    records = []
    for order, sid in enumerate(initial_ids, 1):
        d, q, p = desi[sid], quality[sid], prior[sid]
        r = {"initial27_order": order, "population": "initial27", "source_id": sid,
             "name": p["prior_WDJname"] or d["names"], "legacy_name": d["names"],
             "catalogue_spectral_type": p["input_spectral_types"],
             "desi_status": d["status"],
             "desi_photometry_source": d["photometry_source"],
             "desi_photometric_error_floor_mag": number(d["photometric_error_floor_mag"]),
             "desi_newly_anchored": integer(d["old_calibrated_records"]) == 0 and d["status"] == "calibrated_conditional",
             "desi_selected_row_index": integer(d["selected_row_index"]),
             "desi_raw_sha256": d["raw_sha256"],
             "desi_source_url": d["source_url"],
             "desi_hex": d["hex"],
             "desi_nominal_duv": number(d["duv"]),
             "desi_p025": number(d["duv_mc_p025"]),
             "desi_median": number(d["duv_mc_median"]),
             "desi_p975": number(d["duv_mc_p975"]),
             "desi_mc_draws": integer(d["mc_draws"]),
             "desi_old_to_standardized_uv_shift": number(d["old_to_standardized_uv_shift"])}
        r["desi_95_interval_side"] = interval_side(r["desi_p025"], r["desi_p975"])
        r["desi_95_interval_beyond_001"] = None if r["desi_95_interval_side"] is None else r["desi_95_interval_side"] != 0
        r["desi_95_interval_spans_boundary"] = boundary_span(r["desi_p025"], r["desi_p975"])
        z = heldout[sid]
        r["heldout_z_status"] = z["z_status"]
        r["heldout_z_residual_predicted_minus_observed_mag"] = number(z["z_residual_predicted_minus_observed_mag"])
        r["heldout_z_observed_error_mag"] = number(z["z_observed_error_mag"])
        r["heldout_z_pixel_only_error_mag"] = number(z["z_spectral_error_mag_conditional_pixels_only"])
        r["heldout_z_gap_quality_review"] = flag(z["z_gap_quality_review"]) if z["z_status"] == "computed_diagnostic" else None
        r["heldout_z_abs_residual_gt005"] = (abs(r["heldout_z_residual_predicted_minus_observed_mag"]) > 0.05
            if r["heldout_z_residual_predicted_minus_observed_mag"] is not None else None)
        positions = {"desi": (number(d["u1960"]), number(d["v1960"]))}
        for reconstruction in ("full", "truncated"):
            prefix = "gaia_"+reconstruction
            row = gaia.get((sid, reconstruction), {})
            r[prefix+"_status"] = "native_covariance_available" if row else "unavailable_no_XP_result"
            for field in ("duv", "u1960", "v1960"):
                r[prefix+"_nominal_"+field] = number(row.get(field))
            for suffix, field in (("p025","formal_duv_p025"), ("median","formal_duv_median"), ("p975","formal_duv_p975")):
                r[prefix+"_"+suffix] = number(row.get(field))
            r[prefix+"_mc_draws"] = integer(row.get("mc_draws"))
            r[prefix+"_nonpositive_xyz_draws"] = integer(row.get("nonpositive_xyz_draws"))
            r[prefix+"_point_above_001"] = None if not row else abs(float(row["duv"])) > THRESHOLD
            side = interval_side(r[prefix+"_p025"], r[prefix+"_p975"])
            r[prefix+"_95_interval_side"] = side
            r[prefix+"_95_interval_beyond_001"] = None if side is None else side != 0
            r[prefix+"_95_interval_spans_boundary"] = boundary_span(r[prefix+"_p025"], r[prefix+"_p975"])
            positions[prefix] = (number(row.get("u1960")), number(row.get("v1960")))
        full, trunc = "gaia_full", "gaia_truncated"
        available_gaia = r[full+"_nominal_duv"] is not None and r[trunc+"_nominal_duv"] is not None
        r["gaia_full_truncated_point_boundary_cross"] = (
            r[full+"_point_above_001"] != r[trunc+"_point_above_001"] if available_gaia else None)
        r["gaia_full_truncated_95_boundary_status_disagrees"] = (
            r[full+"_95_interval_beyond_001"] != r[trunc+"_95_interval_beyond_001"] if available_gaia else None)
        r["gaia_full_truncated_delta_uv"] = distance(positions[full], positions[trunc])
        r["gaia_full_truncated_abs_delta_duv"] = (
            abs(r[full+"_nominal_duv"]-r[trunc+"_nominal_duv"]) if available_gaia else None)
        r["desi_gaia_full_delta_uv"] = distance(positions["desi"], positions[full])
        r["desi_gaia_truncated_delta_uv"] = distance(positions["desi"], positions[trunc])
        pairs = {k:r[k] for k in ("gaia_full_truncated_delta_uv", "desi_gaia_full_delta_uv", "desi_gaia_truncated_delta_uv") if r[k] is not None}
        r["max_available_pair_delta_uv"] = max(pairs.values()) if pairs else None
        r["max_available_pair"] = max(pairs, key=pairs.get) if pairs else ""
        r["max_delta_uv_ge_003"] = None if not pairs else max(pairs.values()) >= SHIFT_THRESHOLD
        sides = [r[x+"_95_interval_side"] for x in ("desi",full,trunc)]
        # Descriptive intersection only: no multiplication or pooling of p-values.
        r["all_three_95_intervals_same_side_beyond_001"] = len(set(sides)) == 1 and sides[0] in (-1,1)
        r["all_three_intervals_available"] = all(x is not None for x in sides)
        for field in ("ruwe","bp_rp_excess_factor","ipd_frac_multi_peak","bp_blended_fraction","rp_blended_fraction"):
            r["gaia_"+field] = number(q[field])
        r["gaia_variable_flag"] = q["phot_variable_flag"]
        r["known_gaia_variable"] = q["phot_variable_flag"] == "VARIABLE"
        r["legacy_positional_alias_match"] = flag(q["legacy_positional_alias_match"])
        r["gaia_quality_cautions"] = q["quality_cautions"]
        nn = neighbours[neighbours.target_source_id.eq(sid)].to_dict("records")
        r["gaia_neighbour_count_10arcsec"] = integer(q["gaia_neighbour_count_10arcsec"])
        r["gaia_neighbour_max_relative_G_flux"] = max([float(x["relative_G_flux"]) for x in nn],default=None)
        r["bright_neighbour_G_flux_ratio_gt10"] = any(float(x["relative_G_flux"]) > 10 for x in nn)
        r["gaia_neighbour_ids"] = ";".join(x["neighbour_source_id"] for x in nn)
        r["gaia_neighbour_separations_2016_arcsec"] = ";".join(x["separation_2016_arcsec"] for x in nn)
        r["sdss_conventions"] = ";".join(x["convention"] for x in units.get(sid,[])) or "no_SDSS_row_in_initial27_unit_inventory"
        r["sdss_convention_unresolved"] = any(x["convention"] == "unresolved" for x in units.get(sid,[]))
        r["sdss_convention_verified_direct_rows"] = ";".join(str(x["direct_row_index"]) for x in units.get(sid,[]) if x["direct_row_index"] is not None)
        r["independent_instrument_caution"] = ""
        if sid == "3638333660492606976":
            r["independent_instrument_caution"] = "DESI-only colour candidate: native Gaia XP unavailable and legacy SDSS convention unresolved; withdraw independent SDSS colour support."
        elif sid == "1245262790370992256":
            r["independent_instrument_caution"] = "Known Gaia variable; legacy SDSS convention unresolved; external calibrated DESI colour unavailable."
        elif sid == "1542337839923130624":
            r["independent_instrument_caution"] = "SDSS flambda verified against original row 9539; two archive representations of that SDSS observation are not two observations. Gaia is a second instrument; external calibrated DESI colour unavailable."
        for field in ("swan_exact_id_rows","kilic2026_exact_id_rows","pewdd_exact_id_rows","swan_n_exposures","swan_n_nights","swan_nights_with_some_valid_pixels_all_arms"):
            r["prior_"+field] = integer(p[field])
        for field in ("kilic2026_teff","kilic2026_teff_error","kilic2026_logg","kilic2026_logg_error","kilic2026_mass","kilic2026_mass_error",
                      "swan_neighbour_to_target_flux_DESI","swan_neighbour_to_target_flux_PanSTARRS"):
            r["prior_"+field] = number(p[field])
        for field in ("kilic2026_spectral_type","kilic2026_composition","kilic2025_model","prior_urls"):
            r["prior_"+field] = p[field]
        r["prior_atmosphere_fit_available"] = (integer(p["kilic2026_exact_id_rows"]) or 0) > 0
        ee = exposures[exposures.source_id.eq(sid)]
        r["listed_desi_exposures"] = len(ee)
        r["listed_desi_nights"] = int(ee.NIGHT.nunique())
        goodn = nights[nights.source_id.eq(sid) & nights.accepted_calibrated_colour.map(flag)]
        r["retrieved_accepted_night_count"] = int(goodn.night.nunique())
        r["retrieved_night_dates"] = ";".join(goodn.night.tolist())
        r["retrieved_night_duv"] = ";".join(f"{float(x):+.8f}" for x in goodn.shared_anchor_duv)
        r["night_threshold_status_disagrees"] = (
            len(set(abs(float(x)) > THRESHOLD for x in goodn.shared_anchor_duv)) > 1 if len(goodn)>=2 else None)
        r["night_validation_status"] = "multiple_full_colours_shared_PS1" if len(goodn)>=2 else "not_independently_retrieved_for_colour"
        if sid == "3711047662972690688":
            r["night_validation_status"] = "second_night_retrieved_no_valid_z_arm_colour_unavailable"
        if len(goodn)>=2:
            r["night_duv_range"] = float(goodn.shared_anchor_duv.astype(float).max()-goodn.shared_anchor_duv.astype(float).min())
        else:
            r["night_duv_range"] = None
        flags = []
        for code,condition in (
            ("G",r["desi_median"] is None), ("X",not available_gaia), ("V",r["known_gaia_variable"]),
            ("B",r["bright_neighbour_G_flux_ratio_gt10"]), ("R",r["gaia_full_truncated_point_boundary_cross"] is True),
            ("C",r["gaia_full_truncated_95_boundary_status_disagrees"] is True),
            ("D",r["max_delta_uv_ge_003"] is True), ("N",r["night_threshold_status_disagrees"] is True),
            ("Z",r["heldout_z_abs_residual_gt005"] is True),
            ("U",r["sdss_convention_unresolved"]), ("E",r["legacy_positional_alias_match"])):
            if condition: flags.append(code)
        r["followup_flags"] = ",".join(flags)
        next_steps=[]
        if r["known_gaia_variable"]: next_steps.append("Epoch-resolved classification and colour")
        if r["sdss_convention_unresolved"]: next_steps.append("Resolve original SDSS flux convention")
        if not available_gaia: next_steps.append("Independent ground spectrum with verified units")
        if r["desi_median"] is None: next_steps.append("Quality-checked independent photometric anchors")
        if r["bright_neighbour_G_flux_ratio_gt10"]: next_steps.append("Field-image and PSF-wing contamination test")
        if r["legacy_positional_alias_match"]: next_steps.append("Proper-motion/epoch identity verification")
        if r["night_threshold_status_disagrees"]: next_steps.append("Repeat-night calibration and correlated-noise model")
        if r["heldout_z_abs_residual_gt005"]: next_steps.append("Held-out PS1 z residual: inspect red shape, masks, and calibration beyond fitted gri")
        if r["max_delta_uv_ge_003"] or r["gaia_full_truncated_point_boundary_cross"]:
            next_steps.append("Model reconstruction/continuum bias with held-out spectral features")
        if r["prior_atmosphere_fit_available"]:
            next_steps.append("Compare prior atmosphere fit with free abundances and calibration nuisance terms")
        else:
            next_steps.append("Resolve physical classification before atmosphere interpretation")
        r["next_checks"] = "; ".join(next_steps)
        records.append(r)
    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "population": "initial27; frozen historical candidate set, not the final corrected candidate census",
        "target_count": len(records),
        "desi_conditional_interval_count": sum(r["desi_median"] is not None for r in records),
        "newly_anchored_count": sum(r["desi_newly_anchored"] for r in records),
        "gaia_both_native_covariance_count": sum(r["gaia_full_median"] is not None for r in records),
        "gaia_unavailable_ids": [r["source_id"] for r in records if r["gaia_full_median"] is None],
        "desi_interval_beyond_001_count": sum(r["desi_95_interval_beyond_001"] is True for r in records),
        "gaia_point_boundary_cross_count": sum(r["gaia_full_truncated_point_boundary_cross"] is True for r in records),
        "gaia_interval_boundary_status_disagrees_count": sum(r["gaia_full_truncated_95_boundary_status_disagrees"] is True for r in records),
        "max_pair_delta_uv_ge_003_count": sum(r["max_delta_uv_ge_003"] is True for r in records),
        "known_variable_count": sum(r["known_gaia_variable"] for r in records),
        "bright_neighbour_gt10_count": sum(r["bright_neighbour_G_flux_ratio_gt10"] for r in records),
        "night_threshold_disagreement_ids": [r["source_id"] for r in records if r["night_threshold_status_disagrees"]],
        "prior_atmosphere_fit_count": sum(r["prior_atmosphere_fit_available"] for r in records),
        "heldout_z_available_count": sum(r["heldout_z_residual_predicted_minus_observed_mag"] is not None for r in records),
        "heldout_z_abs_residual_gt005_count": sum(r["heldout_z_abs_residual_gt005"] is True for r in records),
        "interval_subset_without_gt10_neighbour_but_z_flag_ids": [r["source_id"] for r in records if r["all_three_95_intervals_same_side_beyond_001"] and not r["bright_neighbour_G_flux_ratio_gt10"] and r["heldout_z_abs_residual_gt005"]],
        "all_three_interval_same_side_beyond_001_ids": [r["source_id"] for r in records if r["all_three_95_intervals_same_side_beyond_001"]],
        "same_interval_subset_without_gt10_neighbour_ids": [r["source_id"] for r in records if r["all_three_95_intervals_same_side_beyond_001"] and not r["bright_neighbour_G_flux_ratio_gt10"]],
        "method": {
            "exploratory_abs_duv_threshold":THRESHOLD,
            "pair_shift_threshold":SHIFT_THRESHOLD,
            "max_delta_uv":"Maximum Euclidean distance in CIE 1960 (u,v) among available DESI, Gaia full and Gaia truncated nominal points; not a significance.",
            "gaia_point_boundary_cross":"Full and truncated nominal |Duv|>0.01 classifications differ.",
            "interval_boundary_status_disagrees":"Full and truncated central-95% intervals differ in being wholly outside [-0.01,0.01].",
            "all_three_interval_subset":"All three central-95% intervals are entirely beyond the same signed boundary. Descriptive intersection only; no pooled probability or confirmation.",
            "interval_models":"DESI: conditional independent-pixel noise + PS1 anchors and offset/tilt. Gaia: native coefficient covariance and formal Monte Carlo, separate full/truncated reconstructions of the SAME observation.",
            "systematics":"No complete calibration/contamination/truncation-bias/selection model. Full/truncated results are correlated; repeat DESI epochs share PS1.",
            "missingness":"Absent catalogue entries, unqueried nights and unavailable intervals are not non-detections.",
            "photometry":"Swan quoted PS1 errors already include rounded DR1 error plus 0.01 mag in quadrature; pipeline applies max(quoted_error,0.02), without re-adding 0.01.",
            "heldout_z":"Predicted minus observed PS1 z magnitude, unused in gri calibration. Absolute residual >0.05 mag is an additional diagnostic, not sigma significance; supplied pixel-only errors are not total errors.",
            "baseline":"Version 0.1 headline values are retained in original outputs. New error/anchor definitions explain revised estimates; these are not measurements of stellar change.",
        },
        "inputs": {key:{"path":value,"sha256":hashlib.sha256((ROOT/value).read_bytes()).hexdigest()} for key,value in INPUTS.items()},
        "source_pipeline_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "candidates": records,
    }
    assert summary["newly_anchored_count"] == summary_input["newly_anchored_entities"]
    pd.DataFrame(records).to_csv(OUT/"candidate27_followup.csv",index=False)
    (OUT/"candidate27_followup.json").write_text(json.dumps(summary,indent=2,ensure_ascii=False,allow_nan=False)+"\n")
    plot(records)
    report(records,summary)
    print(json.dumps({k:v for k,v in summary.items() if k not in ("candidates","inputs","method")},indent=2))
    return records,summary

def plot(records):
    n=len(records)
    fig,ax=plt.subplots(figsize=(16,17))
    fig.subplots_adjust(left=.24,right=.85,top=.90,bottom=.15)
    labels=[]
    for i,r in enumerate(records):
        labels.append(r["name"]+"\n"+r["source_id"])
        if i%2==0: ax.axhspan(i-.5,i+.5,color="#f5f7f9",zorder=0)
    ax.axvspan(-THRESHOLD,THRESHOLD,color="#e8ebed",alpha=.6,zorder=0)
    for x in (-THRESHOLD,THRESHOLD): ax.axvline(x,color="#555b60",ls="--",lw=1)
    ax.axvline(0,color="#a6abb0",lw=.7)
    styles=[("desi",-.22,"#0072B2","o","DESI + PS1: conditional 95%"),
            ("gaia_full",0,"#D55E00","s","Gaia XP full: coefficient-noise 95%"),
            ("gaia_truncated",.22,"#7C4DA3","^","Gaia XP truncated: coefficient-noise 95%")]
    for prefix,offset,color,marker,label in styles:
        seen=False
        for i,r in enumerate(records):
            if r[prefix+"_median"] is None: continue
            m,lo,hi=[r[prefix+"_"+x] for x in ("median","p025","p975")]
            assert lo<=m<=hi
            ax.errorbar(m,i+offset,xerr=[[m-lo],[hi-m]],fmt=marker,ms=4.4,lw=1.15,
                        capsize=2,color=color,label=label if not seen else None,zorder=3)
            seen=True
    ax.set_yticks(np.arange(n),labels,fontsize=8)
    ax.set_ylim(n-.5,-.5)
    vals=[r[p+"_"+q] for r in records for p,_,_,_,_ in styles for q in ("p025","p975") if r[p+"_"+q] is not None]
    ax.set_xlim(min(vals)-.003,max(vals)+.003)
    ax.set_xlabel("Signed Duv relative to the Planckian locus (CIE 1960 u,v)",fontsize=12)
    ax.tick_params(axis="x",labelsize=10)
    ax.grid(axis="x",alpha=.18)
    ax.spines[["top","right"]].set_visible(False)
    handles, legend_labels = ax.get_legend_handles_labels()
    fig.legend(handles, legend_labels, loc="upper center", bbox_to_anchor=(.55,.934), ncol=3, frameon=False, fontsize=9)
    ax.text(1.018,1.012,"Follow-up flags / prior fit",transform=ax.transAxes,fontsize=9,ha="left")
    for i,r in enumerate(records):
        annotation=(r["followup_flags"] or "—")+" / "+("fit" if r["prior_atmosphere_fit_available"] else "unlisted")
        ax.text(1.018,i,annotation,transform=ax.get_yaxis_transform(),va="center",fontsize=8)
        if r["desi_median"] is None:
            ax.text(.008,i-.22,"DESI unavailable",color="#0072B2",fontsize=7.8,va="center")
        if r["gaia_full_median"] is None:
            ax.text(-.015,i+.16,"Gaia XP unavailable; SDSS units unresolved",color="#7C4DA3",fontsize=7.4,va="center")
    fig.suptitle("Initial 27 candidates: colour uncertainty and follow-up evidence",fontsize=17,y=.977)
    fig.text(.5,.95,"All 27 are retained. Dashed ±0.01 lines are exploratory selection boundaries, not discovery criteria.",ha="center",fontsize=10)
    fig.text(.065,.066,"Points: Monte Carlo medians; bars: central 95% intervals conditional on the stated error model.\n"
             "Full and truncated Gaia use the same coefficients: they are not independent observations.\n"
             "DESI intervals omit a complete correlated-noise/calibration model; same-PS1 epoch colours share anchor errors.",fontsize=10,linespacing=1.5)
    fig.text(.065,.018,"G: no DESI interval   X: no native Gaia XP   V: known variable   B: neighbour G flux >10× target\n"
             "R: Gaia point boundary switch   C: Gaia 95% boundary-status switch   D: max pair Δuv ≥0.003\n"
             "N: night threshold disagreement   Z: held-out |z residual| >0.05 mag   U: SDSS units unresolved   E: positional identity",fontsize=9,linespacing=1.45)
    for suffix in ("png","svg"): fig.savefig(OUT/f"candidate27_uncertainty_comparison.{suffix}",dpi=160)
    plt.close(fig)

def report(records,s):
    selected=s["all_three_interval_same_side_beyond_001_ids"]
    eight=s["same_interval_subset_without_gt10_neighbour_ids"]
    parts=[f"""# Follow-up synthesis for the initial 27 candidates

This report preserves the **initial 27-object candidate set**. It is not the final census after the flux-convention audit, and it does not assign confirmed/discovery labels or combine probabilities.

## Results that survive explicit bookkeeping

There are **{s["desi_conditional_interval_count"]} DESI conditional intervals**, including **{s["newly_anchored_count"]} newly anchored objects**, and **{s["gaia_both_native_covariance_count"]} objects with both full and truncated native-coefficient Gaia intervals**. J1323−0129 has no available native Gaia XP result. These counts come from [standardized DESI colours]({source_link("desi")}) and [formal Gaia results]({source_link("gaia")}), joined against the [frozen initial set]({source_link("initial27")}).

**{len(selected)} objects** have DESI and both Gaia central 95% intervals entirely beyond the same signed exploratory |Duv|=0.01 boundary. All nine lie on the negative-Duv side. This is a descriptive intersection of conditional intervals, not a joint significance. One of these, Gaia DR3 761677269868775040, has a Gaia neighbour with G-band flux ratio 417.90 at 9.268 arcsec. Keeping that field concern separate leaves **{len(eight)} objects without this particular >10× neighbour flag**, not eight confirmed or contamination-free discoveries. The broader [field audit]({source_link("quality")}) and [neighbour table]({source_link("neighbours")}) remain necessary.

Full versus truncated Gaia point estimates switch sides of the exploration boundary in **{s["gaia_point_boundary_cross_count"]} objects**. Whether the Gaia 95% interval is wholly beyond that boundary differs between reconstructions for **{s["gaia_interval_boundary_status_disagrees_count"]} objects**. The maximum nominal two-dimensional uv separation among available DESI/full-Gaia/truncated-Gaia estimates is at least 0.003 for **{s["max_pair_delta_uv_ge_003_count"]} objects**. This last quantity is a sensitivity diagnostic, not an error-normalized statistic.

![All initial 27 objects and their conditional uncertainty intervals](candidate27_uncertainty_comparison.png)

## Definitions and limitations

The plot shows MC medians and central 2.5–97.5 percentile intervals. DESI uses the supplied 6,000-draw conditional spectral-noise/PS1-anchor calculation; the independent resampled-pixel assumption does not include the full spectral covariance or coherent calibration errors. Gaia uses 200,000 draws per reconstruction with native coefficient covariance propagated to colour. Cross-BP/RP covariance is unavailable and set to zero; calibration, contamination, truncation bias and selection are not fully modelled. **Full and truncated Gaia are reconstructions of the same observations.** A narrow truncated interval can accompany substantial reconstruction bias. These intervals must not be pooled as independent evidence. See [reconstruction metadata]({source_link("gaia_reconstruction")}) and the model caveats in the source result tables.

The photometric pipeline applies max(quoted error, 0.02 mag). Swan's quoted PS1 errors already include the rounded native DR1 error and 0.01 mag in quadrature; the latter is not added again. The means of the four headline stars agree with the checked PS1 entries, while error definitions/releases differ from the original calculation. J0913's new standardized nominal Duv is +0.019058 rather than exactly the v0.1 headline value. This is a change in calibration/error treatment, not evidence of a stellar change. See [the photometry-definition audit]({source_link("photometry_definition")}). Original v0.1 headline results are retained.

“Max Δuv” is the largest Euclidean distance in CIE 1960 (u,v) among the available nominal DESI, full Gaia and truncated Gaia points. The full/truncated-only distance and both DESI–Gaia distances are also stored individually in [CSV](candidate27_followup.csv). A missing measurement is left unavailable; it is not evidence for constancy or absence of an effect. The complete definitions and hashed inputs are in [JSON](candidate27_followup.json).

## Cases that change the interpretation

- **J1323−0129 / 3638333660492606976:** DESI colour remains available, but native Gaia XP is unavailable and the legacy SDSS flux convention is unresolved. Independent SDSS colour support is withdrawn; this is a DESI-only colour candidate pending a spectrum with verified units.
- **1245262790370992256:** already a Gaia variable, with CV as its catalogue best classifier class; the classifier score is not a posterior classification probability. The legacy SDSS convention is unresolved and no standardized DESI interval is available. Obtain epoch-resolved classification and colour.
- **PSO J186.4406+47.1036 / 1542337839923130624:** the SDSS F_lambda convention is verified against original row 9539. Two archive representations of the same SDSS observation do not add an independent observation. Gaia supplies a second instrument, but the external calibrated DESI interval remains unavailable. These unit decisions follow the [initial27 SDSS impact table]({source_link("sdss_units")}); none of its three SDSS entries is among the positively identified F_nu set.
- **J0913+4434 / 818833831355548928:** full Gaia has a positive interval beyond +0.01, but the truncated lower bound is +0.009956, just below the exploratory threshold. It is consequently outside the nine-object interval intersection, despite its strong positive DESI result. This near-boundary bookkeeping is not a physical verdict on colour or novelty.
- **1182083542272959232:** truncated Gaia moves the nominal Duv close to zero, and a neighbour is 11.30 times brighter in Gaia G. Both reconstruction sensitivity and the actual field require follow-up.
- **Separate-night checks:** the independently extracted complete DESI colours for 2482684508055379584 are −0.009529 and −0.011147, straddling the point-estimate threshold. For 1691957732959636608 they are −0.010579 and −0.006955, also straddling it. For 1078624858218235776 they are +0.010261 and +0.013296, both above +0.01. These nights use the same PS1 anchors and incomplete covariance models, so the differences do not establish intrinsic variability. J1329's extra retrieved night lacks valid z-arm coverage and cannot supply a second full colour. See [six accepted night results]({source_link("nights")}) and [J1329's failed full-colour validation]({source_link("j1329_second_night")}).
- **Prior work:** {s["prior_atmosphere_fit_count"]}/27 have exact-ID matches to prior atmosphere-fit tables. Missing table matches do not establish novelty. The [prior inventory]({source_link("prior")}) supplies fitted composition, temperature, gravity, mass and citations; these are inherited model results, not independent measurements performed here. For DZ fits with other metal ratios fixed to CI chondrites, test flexible Na/Ca/Mg rather than treating Na as already measured. Very low-mass DQ single-star fits should be tested against unresolved-companion alternatives.

- **Held-out PS1 z:** {s["heldout_z_abs_residual_gt005_count"]}/{s["heldout_z_available_count"]} have |predicted minus observed z| >0.05 mag, including two of the eight interval-subset objects without the >10× neighbour flag. The z band was not fitted in the gri calibration. J0429 has residual −0.06098 mag, J0913 +0.03434, J1329 +0.00311 and J1323 −0.08149. These are additional shape/calibration diagnostics, not total-error significances; no Z-flag source is automatically rejected or corrected. See [held-out residuals]({source_link("heldout_z")}).

## Every-object comparison

Intervals below are signed Duv median [2.5%, 97.5%]. Flags are follow-up requirements, not a ranking. G = DESI interval unavailable; X = native Gaia unavailable; V = known variable; B = neighbour G flux ratio >10; R = full/truncated point-boundary switch; C = full/truncated interval-boundary-status switch; D = max pair Δuv ≥0.003; N = observed-night threshold disagreement; Z = held-out |z residual| >0.05 mag; U = unresolved SDSS convention; E = legacy positional identity. A dash means none of these selected flags, not clean data.

| Initial # / source | DESI conditional 95% | Gaia full formal 95% | Gaia truncated formal 95% | Max Δuv | z pred−obs (mag) | Flags | Prior atmosphere fit |
|---|---|---|---|---:|---:|---|---|
"""]
    for r in records:
        prior=(r["prior_kilic2026_spectral_type"]+" "+r["prior_kilic2026_composition"]) if r["prior_atmosphere_fit_available"] else "No exact-ID fit in checked table"
        mx="Unavailable" if r["max_available_pair_delta_uv"] is None else f'{r["max_available_pair_delta_uv"]:.5f}'
        z_text="Unavailable" if r["heldout_z_residual_predicted_minus_observed_mag"] is None else f'{r["heldout_z_residual_predicted_minus_observed_mag"]:+.5f}'
        parts.append(f'| {r["initial27_order"]}. {r["name"]}<br>{r["source_id"]} | {interval_text(r,"desi")} | {interval_text(r,"gaia_full")} | {interval_text(r,"gaia_truncated")} | {mx} | {z_text} | {r["followup_flags"] or "—"} | {safe_text(prior)} |\n')
    parts.append("\n## Per-object next checks\n\n| Source | Next work |\n|---|---|\n")
    for r in records: parts.append(f'| {r["source_id"]} | {safe_text(r["next_checks"])} |\n')
    parts.append("\n## Reproduction\n\nRun from the repository root:\n\n")
    parts.append("    MPLCONFIGDIR=/tmp/wish_green_mpl .venv-research/bin/python research/candidate_followup.py\n\n")
    parts.append("The script performs only local string-ID joins, arithmetic diagnostics and plotting. It reads the listed upstream source files and writes the CSV, JSON, PNG, SVG and this report; it does not alter the upstream analysis or retrieve new data. The original source inputs and this script are SHA256-recorded in JSON. The counts are conditional on the frozen input snapshots and the stated exploration rules.\n\n")
    parts.append("### 日本語の要点\n\n初期27候補を全件保持し、DESIの条件付き95%区間とGaiaのfull/truncated両再構成の形式的95%区間を並べた。3区間とも同じ側で|Duv|>0.01となる9件は、発見確率を統合した結果ではない。Gaia明るい近傍1件を注意対象として分けると8件で、すべて負Duv側である。XP再構成依存、別夜の閾値不一致、既知変光、SDSS単位未解決、先行大気モデルを天体ごとに明記した。較正に使わなかったPS1 zでは25件中10件に0.05 magを超える残差があり、8件の中にも2件含まれる。これは追加較正診断であり、有意差や棄却判定ではない。J1323は独立SDSS色支持を取り下げ、DESI単独候補として次の観測を要求する。\n")
    (OUT/"candidate27_followup.md").write_text("".join(parts),encoding="utf-8")

if __name__ == "__main__":
    build()

