#!/usr/bin/env python3
"""Derive independent-imaging measurements from immutable public TAP responses.

Offline only.  No colour residual enters the matching or quality selection.
The source IDs remain decimal strings throughout.  Rebuild into another directory
with --output-dir to compare derived products without changing the originals.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import re
from collections import Counter
from pathlib import Path
from xml.etree import ElementTree

import numpy as np
from astropy.time import Time

HERE = Path(__file__).resolve().parent
REL = Path("research/independent_photometry")
MANIFEST = Path("research/precision/candidate_recalibration/derivative_manifest.json")
GAIA = Path("research/external_validation/raw/gaia_dr3_extended_targets.csv")
SKY_BANDS = list("uvgriz")
JP_BANDS = ["rSDSS", "gSDSS", "iSDSS", "zSDSS", "uJAVA", "J0378",
            "J0395", "J0410", "J0430", "J0515", "J0660", "J0861"]
MAX_MATCH_ARCSEC = 1.0
MAX_MAG_ERROR = 0.1


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_rows(path: Path) -> list[dict]:
    text = path.read_text()
    if text.lstrip().startswith("<"):
        raise ValueError(f"An HTML/VOTable error response is not a CSV table: {path}")
    return list(csv.DictReader(io.StringIO("\n".join(
        line for line in text.splitlines() if not line.startswith("#")))))


def finite(value):
    if value is None or str(value).strip().lower() in {"", "null", "nan", "none"}:
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def array(row: dict, key: str) -> list:
    result = [finite(x) for x in row[key].split()]
    assert len(result) == 12, (key, len(result))
    return result


def scalar(row: dict, key: str):
    return finite(row.get(key))


def unit_vector(ra: float, dec: float) -> np.ndarray:
    ra, dec = np.deg2rad([ra, dec])
    return np.array([np.cos(dec) * np.cos(ra), np.cos(dec) * np.sin(ra), np.sin(dec)])


def propagate(gaia: dict, mjd: float) -> np.ndarray:
    """ICRS barycentric direction, constant tangent motion; no parallax/RV model.

    pmra is mu_alpha*cos(delta).  The cone is 15 arcsec; the final match gate is
    1 arcsec.  Annual parallax is not applied to a catalogue's mean position.
    """
    ra, dec = np.deg2rad([float(gaia["ra"]), float(gaia["dec"])])
    direction = unit_vector(float(gaia["ra"]), float(gaia["dec"]))
    years = float(Time(mjd, format="mjd", scale="utc").jyear) - float(gaia["ref_epoch"])
    east = np.array([-np.sin(ra), np.cos(ra), 0.0])
    north = np.array([-np.cos(ra) * np.sin(dec), -np.sin(ra) * np.sin(dec), np.cos(dec)])
    speed = (float(gaia["pmra"]) * east + float(gaia["pmdec"]) * north)
    direction += years * np.deg2rad(1 / 3_600_000) * speed
    return direction / np.linalg.norm(direction)


def separation(left: np.ndarray, right: np.ndarray) -> float:
    return float(np.rad2deg(np.arctan2(np.linalg.norm(np.cross(left, right)),
                                      np.dot(left, right))) * 3600)


def dates(tile: dict) -> list[float]:
    return [float(Time(x, format="isot", scale="utc").mjd)
            for x in tile["OBSERVATION_DATES"].split()]


def write_csv(path: Path, rows: list[dict]) -> None:
    fields = list(dict.fromkeys(k for row in rows for k in row))
    with path.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def raw_input(base: Path, filename: str, root: Path) -> dict:
    path = base / filename
    provenance = json.loads(path.with_name(path.stem + ".provenance.json").read_text())
    assert provenance["http_status"] == 200, filename
    assert provenance["sha256"] == sha(path), filename
    return {"raw_path": str(path.relative_to(root)), "raw_sha256": sha(path),
            "retrieved_utc": provenance["retrieved_utc"], "source_url": provenance["final_url"]}


def build(root: Path, output: Path | None = None) -> dict:
    root = root.resolve()
    output = (output or root / REL).resolve()
    output.mkdir(parents=True, exist_ok=True)
    base = root / REL / "raw"
    selected = json.loads((root / MANIFEST).read_text())
    ids = sorted(x["source_id"] for x in selected)
    assert len(ids) == len(set(ids)) == 25
    assert all(isinstance(x, str) and x.isdecimal() for x in ids)
    targets = {r["source_id"]: r for r in read_rows(root / GAIA)}
    assert set(ids) <= set(targets)
    names = {x["source_id"]: x["original_record"]["allnames"].split(";")[-1]
             for x in selected}
    sky_phot = read_rows(base / "skymapper_photometry_matched.csv")
    jp_matches = read_rows(base / "jplus_dr4_gaia_matches.csv")
    all_jp_matches = read_rows(base / "jplus_dr4_cone_gaia_associations.csv")
    jp_match_map = {(r["TILE_ID"], r["NUMBER"]): r["Source"] for r in all_jp_matches}
    assert len(jp_match_map) == len(all_jp_matches)
    assert all(jp_match_map[(r["TILE_ID"], r["NUMBER"])] == r["Source"] for r in jp_matches)
    jp_tiles = read_rows(base / "jplus_dr4_matched_tiles.csv")
    assert len(jp_tiles) == 84
    jp_tiles += read_rows(base / "jplus_dr4_unmatched_tiles.csv")
    tiles = {(r["REF_TILE_ID"], int(r["FILTER_ID"])): r for r in jp_tiles}
    assert len(tiles) == len(jp_tiles) == 96
    filters = read_rows(base / "jplus_dr4_filters.csv")
    filters.sort(key=lambda r: int(r["FILTER_ID"]))
    assert [r["name"] for r in filters] == JP_BANDS
    enum_text = (base / "jplus_dr4_filter_enumeration.html").read_text()
    enum_pairs = re.findall(r"::<em>([^<]+)</em></td>\s*<td[^>]*>\((\d+)\)", enum_text)
    assert enum_pairs == [(band, str(i + 1)) for i, band in enumerate(JP_BANDS)]
    fnus = {(r["TILE_ID"], r["NUMBER"]): r for r in
            read_rows(base / "jplus_dr4_fnu_matched.csv")}
    gaia_fields = {}
    for p in sorted(base.glob("gaia_dr3_fields15_batch*.csv")):
        gaia_fields.update({r["source_id"]: r for r in read_rows(p)})
    assert set(ids) <= set(gaia_fields)

    measurements, identity, exposure_audit, neighbours, coverage = [], [], [], [], []
    max_ab_difference = 0.0
    max_error_difference = 0.0
    matched_sky_objects = {}
    for sid in ids:
        gaia = targets[sid]
        catalogue_counts = {}
        matched_counts = {}
        for survey, bands, raw_name in [
                ("SkyMapper_DR4", SKY_BANDS, f"skymapper_master_{sid}.csv"),
                ("JPLUS_DR4", JP_BANDS, f"jplus_dr4_dual_{sid}.csv")]:
            provenance = raw_input(base, raw_name, root)
            entries = read_rows(base / raw_name)
            catalogue_counts[survey] = len(entries)
            matches = []
            for entry in entries:
                if survey == "SkyMapper_DR4":
                    cat_id = entry["object_id"]
                    ra, dec = float(entry["raj2000"]), float(entry["dej2000"])
                    epoch = float(entry["mean_epoch"])
                    external_id = entry["gaia_dr3_id1"]
                    id_ok = external_id == sid
                    reference_mag = scalar(entry, "r_psf")
                    reference_flags = scalar(entry, "r_flags")
                    reference_mask = scalar(entry, "r_nimaflags")
                else:
                    key = entry["TILE_ID"], entry["NUMBER"]
                    cat_id = ":".join(key)
                    ra, dec = float(entry["ALPHA_J2000"]), float(entry["DELTA_J2000"])
                    tile = tiles.get((entry["TILE_ID"], 1))
                    epoch = float(np.mean(dates(tile))) if tile else None
                    external_id = jp_match_map.get(key, "")
                    id_ok = external_id == sid
                    reference_mag = array(entry, "MAG_APER_COR_3_0")[0]
                    reference_flags = array(entry, "FLAGS")[0]
                    reference_mask = array(entry, "MASK_FLAGS")[0]
                direction = unit_vector(ra, dec)
                raw_sep = separation(unit_vector(float(gaia["ra"]), float(gaia["dec"])), direction)
                pm_sep = separation(propagate(gaia, epoch), direction) if epoch else None
                match_ok = bool(id_ok and pm_sep is not None and pm_sep <= MAX_MATCH_ARCSEC)
                reasons = []
                if not id_ok:
                    reasons.append("no_exact_published_gaia_association")
                if epoch is None:
                    reasons.append("epoch_unavailable_for_unmatched_catalogue_row")
                elif pm_sep > MAX_MATCH_ARCSEC:
                    reasons.append("proper_motion_position_exceeds_1_arcsec")
                identity.append(dict(source_id=sid, name=names[sid], survey=survey,
                    catalogue_id=cat_id, catalogue_ra_deg=ra, catalogue_dec_deg=dec,
                    catalogue_epoch_mjd=epoch, published_nearest_gaia_source_id=external_id,
                    exact_gaia_id_match=id_ok, separation_gaia2016_arcsec=raw_sep,
                    pm_match_sep_arcsec=pm_sep, selected_identity=match_ok,
                    catalogue_reference_r_mag=reference_mag,
                    catalogue_reference_r_flags=reference_flags,
                    catalogue_reference_r_mask=reference_mask,
                    relative_r_flux_to_selected=None,
                    decision_reasons=";".join(reasons) or "exact_id_and_epoch_position_match",
                    **provenance))
                if match_ok:
                    matches.append((entry, cat_id, epoch, pm_sep))
            assert len(matches) <= 1, (sid, survey, "ambiguous match")
            matched_counts[survey] = len(matches)
            these_rows = [r for r in identity if r["source_id"] == sid and r["survey"] == survey]
            reference = next((r["catalogue_reference_r_mag"] for r in these_rows if r["selected_identity"]), None)
            if reference is not None and reference < 90:
                for row in these_rows:
                    value = row["catalogue_reference_r_mag"]
                    if value is not None and value < 90:
                        row["relative_r_flux_to_selected"] = 10 ** (-0.4 * (value - reference))
            for band_index, band in enumerate(bands):
                result = dict(source_id=sid, name=names[sid], survey=survey, band=band,
                    svo_filter_id=("SkyMapper/SkyMapper." if survey == "SkyMapper_DR4"
                                   else "OAJ/JPLUS.") + band,
                    catalogue_id=None, mag_ab=None, mag_error_quoted=None,
                    zeropoint_error_to_add=None, mag_error_with_zeropoint=None,
                    adopted=False, official_good_sensitivity=False,
                    quality_reasons="no_identified_catalogue_counterpart",
                    epoch_mjd_min=None, epoch_mjd_max=None, catalogue_epoch_mjd=None,
                    pm_match_sep_arcsec=None, photometry_method=None,
                    filter_flags=None, bad_pixel_or_mask_flags=None, psf_neighbour_flag=None,
                    number_good_exposures=None, number_included_exposures=None,
                    number_clipped_or_rejected_exposures=None, catalogue_nclip=None,
                    zero_mask_in_all_included=None,
                    tile_flags=None, variable_flag=None, relative_weight=None,
                    single_detection_id=None, mean_fwhm_arcsec=None,
                    alternate_aperture_mag=None, alternate_aperture_error=None,
                    alternative_minus_primary_mag=None,
                    calibrated_fnu_cgs=None, flux_relative_error=None,
                    **provenance)
                if not matches:
                    measurements.append(result)
                    continue
                entry, cat_id, epoch, pm_sep = matches[0]
                result.update(catalogue_id=cat_id, catalogue_epoch_mjd=epoch,
                              pm_match_sep_arcsec=pm_sep)
                reasons = []
                if survey == "SkyMapper_DR4":
                    matched_sky_objects[cat_id] = sid
                    observations = [p for p in sky_phot if p["object_id"] == cat_id and p["filter"] == band]
                    included = [p for p in observations if p["use_in_clipped"] == "1"]
                    mag, error = scalar(entry, band + "_psf"), scalar(entry, "e_" + band + "_psf")
                    flags, badpix = scalar(entry, band + "_flags"), scalar(entry, band + "_nimaflags")
                    ngood = int(entry[band + "_ngood"])
                    nclip = int(entry[band + "_nclip"])
                    assert len(included) == ngood - nclip, (sid, band, ngood, nclip, len(included))
                    psf_bit = int(entry["flags_psf"]) & (1 << (5 - band_index))
                    zero_pixels = bool(included) and all(int(p["flags"]) == 0 and int(p["nimaflags"]) == 0 for p in included)
                    result.update(photometry_method="catalogue_weighted_mean_PSF_AB",
                        mag_ab=mag, mag_error_quoted=error, zeropoint_error_to_add=0.0,
                        mag_error_with_zeropoint=error, filter_flags=flags,
                        bad_pixel_or_mask_flags=badpix, psf_neighbour_flag=bool(psf_bit),
                        number_good_exposures=ngood, number_included_exposures=len(included),
                        catalogue_nclip=nclip,
                        number_clipped_or_rejected_exposures=len(observations) - len(included),
                        zero_mask_in_all_included=zero_pixels,
                        mean_fwhm_arcsec=float(entry["mean_fwhm"]) * 0.5,
                        alternate_aperture_mag=scalar(entry, band + "_apc05"),
                        alternate_aperture_error=scalar(entry, "e_" + band + "_apc05"))
                    if included:
                        result.update(epoch_mjd_min=min(float(p["exposure_mjd"]) for p in included),
                                      epoch_mjd_max=max(float(p["exposure_mjd"]) for p in included))
                    if ngood < 2 or len(included) < 2:
                        reasons.append("fewer_than_2_good_exposures")
                    if flags != 0:
                        reasons.append("nonzero_or_missing_source_flags")
                    if badpix != 0 or not zero_pixels:
                        reasons.append("nonzero_or_missing_bad_pixels_in_mean")
                    if psf_bit:
                        reasons.append("catalogue_predicted_PSF_neighbour_bias")
                    if ngood and not included:
                        reasons.append("no_included_exposure_metadata")
                    official = bool(ngood >= 2 and len(included) >= 2 and flags is not None and flags < 4
                                    and badpix is not None and badpix < 5 and not psf_bit)
                    official = official and all(int(p["flags"]) < 4 and int(p["nimaflags"]) < 5 for p in included)
                else:
                    mag = array(entry, "MAG_APER_COR_3_0")[band_index]
                    error = array(entry, "MAG_ERR_APER_COR_3_0")[band_index]
                    zp_error = float(filters[band_index]["abs_zp_offset_err"])
                    combined_error = math.hypot(error, zp_error) if error is not None else None
                    flags = array(entry, "FLAGS")[band_index]
                    mask = array(entry, "MASK_FLAGS")[band_index]
                    tile = tiles[(entry["TILE_ID"], band_index + 1)]
                    obs_dates = dates(tile)
                    result.update(photometry_method="catalogue_corrected_3arcsec_aperture_AB",
                        mag_ab=mag, mag_error_quoted=error, zeropoint_error_to_add=zp_error,
                        mag_error_with_zeropoint=combined_error, filter_flags=flags,
                        bad_pixel_or_mask_flags=mask, tile_flags=int(tile["FLAGS"]),
                        variable_flag=int(entry["VAR_FLAGS"]),
                        relative_weight=array(entry, "NORM_WMAP_VAL")[band_index],
                        single_detection_id=int(array(entry, "SINGLE_DETECT")[band_index]),
                        number_good_exposures=int(tile["NCOMBINED"]),
                        number_included_exposures=len(obs_dates),
                        epoch_mjd_min=min(obs_dates), epoch_mjd_max=max(obs_dates),
                        mean_fwhm_arcsec=float(tile["FWHM_MEAN"]),
                        alternate_aperture_mag=array(entry, "MAG_APER_COR_6_0")[band_index],
                        alternate_aperture_error=array(entry, "MAG_ERR_APER_COR_6_0")[band_index])
                    fnu = fnus[(entry["TILE_ID"], entry["NUMBER"])]
                    flux = array(fnu, "FLUX_APER_COR_3_0")[band_index]
                    rel_error = array(fnu, "FLUX_RELERR_APER_COR_3_0")[band_index]
                    result.update(calibrated_fnu_cgs=flux * 1e-30 if flux is not None else None,
                                  flux_relative_error=rel_error)
                    if flux is not None and flux > 0 and mag is not None and mag < 90:
                        predicted = -2.5 * math.log10(flux * 1e-30) - 48.6
                        max_ab_difference = max(max_ab_difference, abs(predicted - mag))
                    if rel_error is not None and error is not None and error < 90:
                        max_error_difference = max(max_error_difference, abs(2.5 / math.log(10) * rel_error - error))
                    if flags != 0:
                        reasons.append("nonzero_source_flags")
                    if mask != 0:
                        reasons.append("nonzero_mask_flags" + ("_bright_star" if int(mask or 0) & 2 else ""))
                    if int(tile["FLAGS"]) != 0:
                        reasons.append("nonzero_tile_flags")
                    if int(entry["VAR_FLAGS"]) != 0:
                        reasons.append("known_variable_flag")
                    if result["single_detection_id"] <= 0:
                        reasons.append("not_detected_in_single_band_catalogue")
                    if (result["relative_weight"] or 0) < 0.8:
                        reasons.append("relative_exposure_weight_below_0p8")
                    if int(tile["NCOMBINED"]) < 2:
                        reasons.append("fewer_than_2_coadded_exposures")
                    official = False  # Sensitivity flag is explicitly the SkyMapper criterion.
                if mag is None or mag >= 90:
                    reasons.append("missing_or_sentinel_magnitude_not_an_upper_limit")
                recommended_error = result["mag_error_with_zeropoint"]
                if recommended_error is None or recommended_error <= 0 or recommended_error > MAX_MAG_ERROR:
                    reasons.append("missing_or_error_above_0p1_mag")
                magnitude_good = mag is not None and mag < 90
                error_good = recommended_error is not None and 0 < recommended_error <= MAX_MAG_ERROR
                result["adopted"] = not reasons
                result["official_good_sensitivity"] = bool(official and magnitude_good and error_good)
                result["quality_reasons"] = ";".join(reasons) or "strict_quality_pass"
                alt = result["alternate_aperture_mag"]
                if magnitude_good and alt is not None and alt < 90:
                    result["alternative_minus_primary_mag"] = alt - mag
                measurements.append(result)

        # Gaia neighbour ledger uses actual original Gaia field rows, including
        # ones outside the candidate set, with no Gaussian PSF-tail assumption.
        own = unit_vector(float(gaia["ra"]), float(gaia["dec"]))
        for nid, near in gaia_fields.items():
            if nid == sid:
                continue
            d = separation(own, unit_vector(float(near["ra"]), float(near["dec"])))
            if d <= 15:
                neighbours.append(dict(source_id=sid, neighbour_gaia_source_id=nid,
                    separation_2016_arcsec=d, neighbour_g_mag=scalar(near, "phot_g_mean_mag"),
                    relative_gaia_g_flux=10 ** (-0.4 * (float(near["phot_g_mean_mag"]) -
                                                        float(gaia["phot_g_mean_mag"]))),
                    limitation="Gaia_G_contrast_is_not_a_filter_specific_PSF_contamination_estimate"))
        mine = [r for r in measurements if r["source_id"] == sid]
        coverage.append(dict(source_id=sid, name=names[sid],
            skymapper_cone_rows=catalogue_counts["SkyMapper_DR4"],
            skymapper_identified_objects=matched_counts["SkyMapper_DR4"],
            jplus_cone_rows=catalogue_counts["JPLUS_DR4"],
            jplus_identified_objects=matched_counts["JPLUS_DR4"],
            skymapper_adopted_bands=";".join(r["band"] for r in mine if r["survey"] == "SkyMapper_DR4" and r["adopted"]),
            jplus_adopted_bands=";".join(r["band"] for r in mine if r["survey"] == "JPLUS_DR4" and r["adopted"]),
            count_adopted=sum(r["adopted"] for r in mine),
            missing_interpretation="No catalogue counterpart is a coverage/detection result, not a flux upper limit."))

    for row in sky_phot:
        sid = matched_sky_objects.get(row["object_id"])
        exposure_audit.append(dict(source_id=sid, object_id=row["object_id"], image_id=row["image_id"],
            filter=row["filter"], ccd=row["ccd"], source_association_accepted=sid is not None,
            exposure_mjd=float(row["exposure_mjd"]), exposure_seconds=float(row["exposure_seconds"]),
            included_in_catalogue_clipped_mean=row["use_in_clipped"] == "1",
            source_flags=int(row["flags"]), masked_pixel_count=int(row["nimaflags"]),
            image_mask_bitfield=int(row["imaflags"]),
            strict_zero_flags_and_pixels=int(row["flags"]) == int(row["nimaflags"]) == 0,
            mag_psf=scalar(row, "mag_psf"), mag_error=scalar(row, "e_mag_psf"),
            native_signed_flux_psf=scalar(row, "flux_psf"), native_flux_error=scalar(row, "e_flux_psf"),
            native_flux_unit="SkyMapper_image_count_units_not_cgs",
            source_fwhm_arcsec=float(row["fwhm"]) * 0.5,
            # The original ADQL alias 'image_fwhm_pixels' was a naming error.
            # TAP_SCHEMA explicitly declares dr4.images.fwhm_mean in arcsec.
            # Preserve raw bytes/ADQL and fix the derived unit label here.
            image_fwhm_arcsec=scalar(row, "image_fwhm_pixels"),
            image_quality=int(row["image_quality"]),
            raw_path=str(REL / "raw/skymapper_photometry_matched.csv"),
            raw_sha256=sha(base / "skymapper_photometry_matched.csv")))

    assert len(measurements) == 25 * 18
    assert len({(r["source_id"], r["survey"], r["band"]) for r in measurements}) == len(measurements)
    # Published tables round magnitude and relative flux errors.  This checks
    # their physical conversion, not a machine-precision equality of display text.
    assert max_ab_difference < 0.00015, max_ab_difference
    assert max_error_difference < 0.0002, max_error_difference
    counts = Counter(r["survey"] for r in measurements if r["adopted"])
    summary = dict(cohort="Fixed 25 candidates in the prior PS1 standardized derivative manifest",
        cohort_count=25, measurement_slots=len(measurements),
        catalogue_identity_rows=len(identity), selected_identity_count=sum(r["selected_identity"] for r in identity),
        rejected_catalogue_rows=sum(not r["selected_identity"] for r in identity),
        matched_objects_by_survey=dict(Counter(r["survey"] for r in identity if r["selected_identity"])),
        strict_adopted_measurements=dict(counts), strict_adopted_total=sum(counts.values()),
        sources_with_any_adopted_measurement=sum(r["count_adopted"] > 0 for r in coverage),
        skymapper_raw_detection_rows=len(exposure_audit),
        gaia_field_radius_arcsec=15.0, gaia_field_unique_rows=len(gaia_fields),
        jplus_ab_from_original_fnu_max_difference_mag=max_ab_difference,
        jplus_error_from_original_relative_flux_max_difference_mag=max_error_difference,
        quality_policy=dict(match_arcsec=MAX_MATCH_ARCSEC, max_recommended_mag_error=MAX_MAG_ERROR,
            common="Exact decimal Gaia association plus proper-motion corrected position; no colour residual cut.",
            skymapper="At least two good exposures, all included source flags and masked-pixel counts zero, PSF-neighbour bit clear.",
            jplus="At least two exposures, source/mask/tile/known-variability flags zero, single-band detection present, relative weight >=0.8.",
            zeropoints="SkyMapper: catalogue error unchanged. J-PLUS: abs_zp_offset_err added in quadrature as instructed; published offsets already applied."),
        limitations=["Different source photons do not imply independent zero-point calibration.",
            "Both surveys use Gaia XP calibration stars; J-PLUS also uses a WD locus and PS1 r global anchor.",
            "Quoted/error-box constraints are not independent Gaussian confidence regions.",
            "Survey absence and magnitude sentinel 99 are not quantitative flux upper limits.",
            "Catalogue flags and aperture comparisons do not substitute for an image-level PSF contamination model.",
            "Passband coverage and synthetic photometry are evaluated separately; no extrapolation is done here."])

    input_paths = [MANIFEST, GAIA]
    # Preserve all queried bytes, including documented failed pilot responses.
    raw_sources = []
    for meta_path in sorted(base.glob("*.provenance.json")):
        meta = json.loads(meta_path.read_text())
        stem = meta_path.name.removesuffix(".provenance.json")
        candidates = [p for p in base.glob(stem + ".*") if p != meta_path and ".provenance." not in p.name]
        assert len(candidates) == 1, (stem, candidates)
        path = candidates[0]
        assert sha(path) == meta["sha256"], path
        protocol = "HTTP_error" if meta["http_status"] != 200 else "retained_public_response"
        if "VOTABLE" in path.read_text()[:300]:
            tree = ElementTree.fromstring(path.read_bytes())
            query_status = [x for x in tree.iter() if x.tag.endswith("INFO") and x.get("name") == "QUERY_STATUS"]
            if any(x.get("value") in {"ERROR", "OVERFLOW"} for x in query_status):
                protocol = "TAP_ERROR_not_an_empty_catalogue"
        record = dict(path=str(path.relative_to(root)), sha256=sha(path),
            provenance_path=str(meta_path.relative_to(root)), provenance_sha256=sha(meta_path),
            http_status=meta["http_status"], retrieved_utc=meta["retrieved_utc"],
            protocol_note=protocol)
        if "QUERY" in (meta.get("query_parameters") or {}):
            query_path = base.parent / "queries" / (stem + ".adql")
            assert query_path.read_text() == meta["query_parameters"]["QUERY"] + "\n"
            record.update(query_path=str(query_path.relative_to(root)), query_sha256=sha(query_path))
        raw_sources.append(record)
    summary["upstream_input_sha256"] = {str(p): sha(root / p) for p in input_paths}
    summary["raw_response_count"] = len(raw_sources)
    access_rows = []
    for sid in ids:
        path = base / f"splus_dr3_{sid}.csv"
        tree = ElementTree.fromstring(path.read_bytes())
        errors = [x for x in tree.iter() if x.tag.endswith("INFO")
                  and x.get("name") == "QUERY_STATUS" and x.get("value") == "ERROR"]
        assert len(errors) == 1 and "Unknown column" in errors[0].text
        access_rows.append(dict(source_id=sid, survey="SPLUS_DR3_public_SkyMapper_mirror",
            query_status="ERROR", returned_catalogue_rows=None, adopted_measurements=0,
            result_interpretation="Catalogue query failed; source presence and flux limits are unknown.",
            error_text=errors[0].text, raw_path=str(path.relative_to(root)), raw_sha256=sha(path)))
    summary["splus_query_failures_not_nondetections"] = len(access_rows)
    payload = dict(schema_version=1, summary=summary, measurements=measurements)
    for filename, data in [("measurements.csv", measurements), ("coverage.csv", coverage),
                           ("identity_audit.csv", identity), ("skymapper_exposure_audit.csv", exposure_audit),
                           ("gaia_neighbour_audit.csv", neighbours),
                           ("splus_access_audit.csv", access_rows)]:
        write_csv(output / filename, data)
    (output / "measurements.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    (output / "source_manifest.json").write_text(json.dumps(dict(
        upstream_input_sha256=summary["upstream_input_sha256"], raw_responses=raw_sources),
        indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    (output / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=HERE.parents[1])
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    result = build(args.root, args.output_dir)
    print(json.dumps({k: v for k, v in result.items() if k not in {"upstream_input_sha256", "quality_policy", "limitations"}}, indent=2))


if __name__ == "__main__":
    main()
