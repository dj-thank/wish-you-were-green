#!/usr/bin/env python3
"""Official Gaia DR3 quality/field audit for the frozen 27-object shortlist."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from hashlib import sha256
import io
import json
from pathlib import Path

import numpy as np
import pandas as pd

from acquire import BASE, RAW, GAIA_TAP, fetch, tap
from analyze_ztf import angular_distance, propagated, finite_json

ROOT = BASE.parents[1]
COLS = ["source_id", "ra", "dec", "ref_epoch", "parallax", "parallax_error", "pmra", "pmdec", "pmra_error", "pmdec_error",
        "ruwe", "astrometric_params_solved", "duplicated_source", "ipd_frac_multi_peak", "ipd_frac_odd_win",
        "phot_bp_rp_excess_factor", "phot_g_mean_mag", "phot_bp_mean_mag", "phot_rp_mean_mag",
        "phot_bp_n_obs", "phot_rp_n_obs", "phot_bp_n_contaminated_transits", "phot_bp_n_blended_transits",
        "phot_rp_n_contaminated_transits", "phot_rp_n_blended_transits", "phot_variable_flag", "has_epoch_photometry",
        "has_xp_continuous", "non_single_star"]


def main():
    snapshot = BASE / "gaia_extended_input.csv"
    if not snapshot.exists():
        input_path = ROOT / "research/outlier_audit/object_audit.csv"
        content = input_path.read_bytes()
        all_objects = pd.read_csv(io.BytesIO(content), dtype={"source_id": str})
        selected = all_objects[all_objects.review_status == "multiple_instrument_colour_candidate"].copy()
        selected.to_csv(snapshot, index=False)
        (BASE / "gaia_extended_input.provenance.json").write_text(json.dumps(dict(
            input_path="research/outlier_audit/object_audit.csv", input_sha256=sha256(content).hexdigest(),
            selection="review_status == multiple_instrument_colour_candidate", selected_count=len(selected),
            frozen_utc=datetime.now(timezone.utc).isoformat(), snapshot_sha256=sha256(snapshot.read_bytes()).hexdigest()), indent=2) + "\n")
    targets = pd.read_csv(snapshot, dtype={"source_id": str})
    ids = ",".join(targets.source_id)
    query = "SELECT " + ",".join(COLS) + f" FROM gaiadr3.gaia_source WHERE source_id IN ({ids})"
    print(fetch(*tap("gaia_dr3_extended_targets", GAIA_TAP, query)), flush=True)
    gp = RAW / "gaia_dr3_extended_targets.csv"
    if not gp.exists():
        raise RuntimeError("Official target query failed; no field absence inference")
    gaia = pd.read_csv(gp, dtype={"source_id": str})
    missing_ids = sorted(set(targets.source_id) - set(gaia.source_id))
    if missing_ids:
        (BASE / "gaia_extended_unresolved_source_ids.json").write_text(json.dumps(missing_ids, indent=2)+"\n")
    jobs = []
    for index, offset in enumerate(range(0, len(gaia), 8)):
        batch = gaia.iloc[offset:offset+8]
        cones = " OR ".join(f"1=CONTAINS(POINT('ICRS',ra,dec),CIRCLE('ICRS',{r.ra},{r.dec},{10/3600}))" for r in batch.itertuples())
        query = "SELECT " + ",".join(COLS) + " FROM gaiadr3.gaia_source WHERE " + cones
        jobs.append(tap(f"gaia_dr3_extended_fields_batch{index}", GAIA_TAP, query))
    with ThreadPoolExecutor(max_workers=2) as pool:
        for result in pool.map(lambda j: fetch(*j), jobs):
            print(result, flush=True)
    fields = []
    for job in jobs:
        path = RAW / f"{job[0]}.csv"
        if not path.exists():
            raise RuntimeError(f"A field query failed: {job[0]}; complete field audit cannot be inferred")
        fields.append(pd.read_csv(path, dtype={"source_id": str}))
    field = pd.concat(fields, ignore_index=True).drop_duplicates("source_id")
    gaia = gaia.set_index("source_id")
    records, neighbor_records = [], []
    for rec in targets.itertuples():
        if rec.source_id not in gaia.index:
            records.append(dict(source_id=rec.source_id, field_audit_status="source_id_not_returned"))
            continue
        g = gaia.loc[rec.source_id]
        separation = angular_distance(field.ra, field.dec, float(g.ra), float(g.dec))
        neighbours = field[(separation <= 10.000001) & (field.source_id != rec.source_id)].copy()
        neighbours["separation_2016_arcsec"] = np.asarray(separation)[(separation <= 10.000001) & (field.source_id != rec.source_id)]
        neighbours["relative_G_flux"] = 10**(-.4*(neighbours.phot_g_mean_mag - float(g.phot_g_mean_mag)))
        nearest = float(neighbours.separation_2016_arcsec.min()) if len(neighbours) else None
        flags = []
        if str(g.phot_variable_flag) == "VARIABLE":
            flags.append("gaia_known_variable_requires_phase_resolved_calibration")
        if float(g.ruwe) >= 1.4:
            flags.append("ruwe_ge_1p4_diagnostic")
        if str(g.duplicated_source).lower() == "true":
            flags.append("duplicated_source")
        if float(g.ipd_frac_multi_peak) > 0:
            flags.append("ipd_multi_peak_nonzero")
        if float(g.ipd_frac_odd_win) > 0:
            flags.append("ipd_odd_window_nonzero")
        if len(neighbours):
            flags.append("catalogued_gaia_neighbour_within_10arcsec")
        bp_fraction = float(g.phot_bp_n_blended_transits / g.phot_bp_n_obs) if g.phot_bp_n_obs > 0 else None
        rp_fraction = float(g.phot_rp_n_blended_transits / g.phot_rp_n_obs) if g.phot_rp_n_obs > 0 else None
        if (bp_fraction and bp_fraction > 0) or (rp_fraction and rp_fraction > 0):
            flags.append("gaia_bp_or_rp_blended_transits")
        # The parent's earlier identifier association used catalogue coordinates
        # without a matched observation epoch. Preserve that provenance caveat.
        legacy_position_association = bool(rec.has_positional_identity)
        if legacy_position_association:
            flags.append("legacy_positional_alias_match_requires_epoch_identity_review")
        input_offset = float(angular_distance(float(rec.ra_deg), float(rec.dec_deg), float(g.ra), float(g.dec)))
        if input_offset > 1.:
            flags.append("input_coordinate_offset_gt1arcsec_epoch_unspecified")
        pm = float(np.hypot(g.pmra, g.pmdec))
        row = dict(source_id=rec.source_id, names=rec.names, parent_review_status=rec.review_status,
                   field_audit_status="official_Gaia_DR3_queried", ra2016_deg=float(g.ra), dec2016_deg=float(g.dec),
                   input_catalogue_offset_from_gaia2016_arcsec=input_offset,
                   legacy_positional_alias_match=legacy_position_association,
                   parallax_mas=float(g.parallax), parallax_error_mas=float(g.parallax_error), ruwe=float(g.ruwe),
                   astrometric_params_solved=int(g.astrometric_params_solved), pm_mas_per_year=pm,
                   predicted_linear_displacement_2016_to2026_arcsec=pm*.01,
                   phot_g_mean_mag=float(g.phot_g_mean_mag), bp_rp_excess_factor=float(g.phot_bp_rp_excess_factor),
                   ipd_frac_multi_peak=float(g.ipd_frac_multi_peak), ipd_frac_odd_win=float(g.ipd_frac_odd_win),
                   bp_blended_fraction=bp_fraction, rp_blended_fraction=rp_fraction,
                   phot_variable_flag=str(g.phot_variable_flag), has_epoch_photometry=bool(g.has_epoch_photometry),
                   non_single_star=int(g.non_single_star), gaia_neighbour_count_10arcsec=len(neighbours),
                   nearest_gaia_neighbour_2016_arcsec=nearest, quality_cautions="|".join(flags))
        records.append(row)
        for n in neighbours.itertuples():
            nr = dict(target_source_id=rec.source_id, neighbour_source_id=n.source_id,
                      separation_2016_arcsec=float(n.separation_2016_arcsec), relative_G_flux=float(n.relative_G_flux),
                      neighbour_Gmag=float(n.phot_g_mean_mag), neighbour_parallax_mas=float(n.parallax),
                      neighbour_pmra=float(n.pmra), neighbour_pmdec=float(n.pmdec),
                      propagated_2026_separation_arcsec=None)
            if np.all(np.isfinite([n.pmra, n.pmdec, g.pmra, g.pmdec])):
                ra1, dec1 = propagated(g, 51544.5 + (2026-2000)*365.25)
                ra2, dec2 = propagated(n, 51544.5 + (2026-2000)*365.25)
                nr["propagated_2026_separation_arcsec"] = float(angular_distance(ra1, dec1, ra2, dec2))
            neighbor_records.append(nr)
    output = BASE / "results"
    output.mkdir(exist_ok=True)
    pd.DataFrame(records).to_csv(output / "gaia_extended_quality.csv", index=False)
    pd.DataFrame(neighbor_records).to_csv(output / "gaia_extended_neighbours.csv", index=False)
    summary = dict(n_shortlisted_targets=len(targets), n_official_source_ids_returned=len(gaia),
                   n_distinct_gaia_rows_in_cones=len(field), n_with_catalogued_neighbours=sum(r.get("gaia_neighbour_count_10arcsec", 0)>0 for r in records),
                   n_with_ruwe_ge1p4=sum(r.get("ruwe", 0)>=1.4 for r in records), n_legacy_positional_aliases=sum(r.get("legacy_positional_alias_match", False) for r in records),
                   n_with_gaia_variable_flag=sum(r.get("phot_variable_flag")=="VARIABLE" for r in records),
                   statement="These are data-quality/identity diagnostics for an exploratory shortlist, not confirmed discoveries or a complete clean sample.",
                   limitations=["Gaia DR3 cones miss unresolved companions, uncatalogued galaxies and objects fainter than Gaia's local completeness.",
                                "No Gaia catalogue neighbour does not establish uncontaminated ground-based or XP spectra.",
                                "Blended-transit ratios describe flags; they are not contaminating-flux fractions.",
                                "NOT_AVAILABLE variability status and has_epoch_photometry=false do not establish a constant star.",
                                "RUWE 1.4 is a heuristic audit threshold; the white dwarf's colour anomaly is not confirmed or refuted by it.",
                                "The BP/RP excess factor is retained without cutting on it: unusual white dwarf spectral structure can itself affect this diagnostic.",
                                "Linear epoch propagation ignores parallax and radial-velocity perspective terms."])
    (output / "gaia_extended_summary.json").write_text(json.dumps(finite_json(summary), indent=2, allow_nan=False)+"\n")
    classifier_path = RAW / "gaia_dr3_variable_candidate_classifier.csv"
    variability_path = RAW / "gaia_dr3_variable_candidate_summary.csv"
    if classifier_path.exists() and variability_path.exists():
        classifier = pd.read_csv(classifier_path, dtype={"source_id":str}).iloc[0]
        variability = pd.read_csv(variability_path, dtype={"source_id":str}).iloc[0]
        followup = dict(source_id=str(classifier.source_id),
                        evidence_type="Previously published Gaia DR3 automatic variability classification; not a newly found variable",
                        classifier_name=str(classifier.classifier_name), best_class_name=str(classifier.best_class_name),
                        best_class_score=float(classifier.best_class_score), score_is_probability=False,
                        n_selected_g_fov=int(variability.num_selected_g_fov),
                        time_duration_g_fov_days=float(variability.time_duration_g_fov),
                        full_range_g_mag=float(variability.range_mag_g_fov),
                        trimmed_range_g_mag=float(variability.trimmed_range_mag_g_fov),
                        std_dev_g_mag=float(variability.std_dev_mag_g_fov),
                        calibration_implication="Do not treat noncontemporaneous mean photometry and spectra as a validated constant-SED colour measurement; investigate phase and classification.")
        (output / "known_variable_followup.json").write_text(json.dumps(followup, indent=2)+"\n")
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    main()
