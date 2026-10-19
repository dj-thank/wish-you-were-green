#!/usr/bin/env python3
"""Check four visually discordant entities against original SDSS positions.

An epoch-position match constrains a proposed misassociation explanation; it
does not establish absence of contamination, intrinsic variability, or valid
relative spectrophotometry. Selection is from the recorded visual review.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import gzip
import io
import json
import os
from pathlib import Path
import sys
from urllib.parse import urlencode
from urllib.request import Request, urlopen

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import numpy as np
import pandas as pd
from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.time import Time
from research.outlier_followup.build_followup import frozen_inputs, relative, sha

HERE = Path(__file__).resolve().parent
OUT = HERE / "association_diagnostics"
SOURCES = ("1038076351151065088", "1311674353544358912", "2586182156053386240", "1025033665052512000")


def fetch():
    OUT.mkdir(exist_ok=True)
    query = ("SELECT g.source_id,g.ra,g.dec,g.ref_epoch,g.ra_error,g.dec_error,g.parallax,g.parallax_error,"
             "g.pmra,g.pmdec,g.pmra_error,g.pmdec_error,g.phot_g_mean_mag,g.bp_rp,g.ruwe,g.phot_variable_flag,"
             "g.phot_bp_rp_excess_factor,v.best_class_name,v.best_class_score FROM gaiadr3.gaia_source AS g "
             "LEFT OUTER JOIN gaiadr3.vari_classifier_result AS v ON g.source_id=v.source_id "
             "WHERE g.source_id IN (" + ",".join(SOURCES) + ") ORDER BY g.source_id")
    (OUT / "gaia_query.adql").write_text(query + "\n")
    url = "https://gea.esac.esa.int/tap-server/tap/sync?" + urlencode({"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "csv", "QUERY": query})
    started = datetime.now(timezone.utc).isoformat()
    with urlopen(Request(url, headers={"User-Agent": "wish-you-were-green reproducible research"}), timeout=45) as response:
        body = response.read()
        metadata = {"request_url": url, "resolved_url": response.url, "status": response.status,
                    "content_type": response.headers.get("Content-Type"), "http_date": response.headers.get("Date")}
    path = OUT / "gaia_sources.csv"; path.write_bytes(body)
    metadata.update(query_started_utc=started, retrieved_utc=datetime.now(timezone.utc).isoformat(),
                    sha256=sha(path), size_bytes=len(body), source="ESA Gaia DR3 official TAP archive")
    (OUT / "gaia_sources.provenance.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print("Retrieved Gaia exact-ID rows", len(pd.read_csv(path)), flush=True)


def analyze():
    table = pd.read_csv(HERE / "record_review.csv.gz", dtype={"source_id": str}, low_memory=False)
    meta = read_json(OUT / "gaia_sources.provenance.json")
    require(sha(OUT / "gaia_sources.csv") == meta["sha256"], "Gaia source hash changed")
    gaia = pd.read_csv(OUT / "gaia_sources.csv", dtype={"source_id": str})
    require(len(gaia) == 4 and set(gaia.source_id) == set(SOURCES), "Missing or duplicate Gaia ID")
    inputs = frozen_inputs(); results = []; header_inputs = []
    for sid in SOURCES:
        g = gaia[gaia.source_id.eq(sid)].iloc[0]
        coords = SkyCoord(ra=g.ra*u.deg, dec=g.dec*u.deg, pm_ra_cosdec=g.pmra*u.mas/u.yr,
                          pm_dec=g.pmdec*u.mas/u.yr, obstime=Time(g.ref_epoch, format="jyear"))
        rows = table[table.source_id.eq(sid) & table.archive_origin.eq("SDSS_DR17_direct")]
        for r in rows.itertuples():
            origin, original = inputs[r.row_index]
            require(origin == "sdss", "Expected original SDSS archive input")
            raw = relative(original["raw_path"])
            require(raw.is_file() and sha(raw) == original["sha256"], "Original SDSS FITS missing or wrong hash")
            archived = OUT / (raw.name + ".gz")
            archived.write_bytes(gzip.compress(raw.read_bytes(), mtime=0))
            with fits.open(raw) as hdus:
                h = hdus[0].header
                # RA/DEC in these files describe the plate centre, not this
                # fibre. Missing PLUG coordinates must fail rather than silently
                # switching to a different positional quantity.
                ra = h.get("PLUG_RA"); dec = h.get("PLUG_DEC")
                mjd = h.get("MJD")
                require(all(v is not None and np.isfinite(float(v)) for v in (ra, dec, mjd)), "Original fibre coordinates/epoch missing")
                header = {key: h.get(key) for key in ("PLUG_RA", "PLUG_DEC", "RA", "DEC", "MJD", "PLATEID", "FIBERID", "RUN2D", "RUN1D", "SPECOBJID", "OBJTYPE", "VACUUM")}
            target = SkyCoord(float(ra)*u.deg, float(dec)*u.deg)
            epoch = Time(float(mjd), format="mjd")
            moved = coords.apply_space_motion(new_obstime=epoch)
            header_entry = {"row_index": int(r.row_index), "source_id": sid, "original_fits_path": str(raw.relative_to(ROOT)),
                            "original_fits_sha256": original["sha256"], "original_fits_url": original.get("source_url", original.get("url")),
                            "lossless_original_path": archived.name, "lossless_original_sha256": sha(archived),
                            "header": header}
            header_inputs.append(header_entry)
            results.append({"row_index": int(r.row_index), "source_id": sid, "entity_id": r.entity_id,
                            "plug_ra_deg": float(ra), "plug_dec_deg": float(dec), "observation_mjd": float(mjd),
                            "plate": header["PLATEID"], "fiber": header["FIBERID"],
                            "gaia_ra_2016": float(g.ra), "gaia_dec_2016": float(g.dec), "gaia_pmra_mas_yr": float(g.pmra), "gaia_pmdec_mas_yr": float(g.pmdec),
                            "fixed_2016_separation_arcsec": float(coords.separation(target).arcsec),
                            "epoch_propagated_separation_arcsec": float(moved.separation(target).arcsec),
                            "gaia_phot_variable_flag": g.phot_variable_flag,
                            "gaia_best_class_name": g.best_class_name if pd.notna(g.best_class_name) else "",
                            "gaia_best_class_score": float(g.best_class_score) if pd.notna(g.best_class_score) else None,
                            "interpretation": "Epoch consistency diagnostic only; no automatic entity reassignment or physical cause is inferred"})
    (OUT / "sdss_original_headers.json").write_text(json.dumps(header_inputs, indent=2, allow_nan=False) + "\n")
    pd.DataFrame(results).to_csv(OUT / "epoch_associations.csv", index=False)
    report = {"created_utc": datetime.now(timezone.utc).isoformat(), "selected_source_ids": list(SOURCES),
              "selection": "Three pronounced cross-instrument continuum discrepancies from actual visual review, plus one discordant SDSS/XP continuum zoom; selected before the Gaia query",
              "method": "Propagate Gaia DR3 2016.0 position with published pmra/pmdec to original SDSS header MJD; require PLUG_RA/PLUG_DEC. RA/DEC are plate-centre metadata and are never used as a fibre-coordinate fallback.",
              "limits": "No radial-velocity/perspective-motion correction, full astrometric covariance, field PSF modelling or probability of association. A small offset does not exclude blends, changing conditions or calibration errors. NOT_AVAILABLE is not proof of constancy; classifier scores are not posterior probabilities.",
              "input_sha256": {str(p.relative_to(ROOT)): sha(p) for p in (HERE / "record_review.csv.gz", OUT / "gaia_sources.csv", OUT / "gaia_query.adql", OUT / "sdss_original_headers.json")},
              "code_sha256": sha(Path(__file__)), "results": results}
    (OUT / "association_summary.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(pd.DataFrame(results)[["source_id", "row_index", "fixed_2016_separation_arcsec", "epoch_propagated_separation_arcsec", "gaia_phot_variable_flag", "gaia_best_class_name"]].to_string(index=False))


def read_json(path):
    return json.loads(path.read_text())


def require(condition, message):
    if not condition:
        raise AssertionError(message)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("fetch", "analyze"))
    args = parser.parse_args()
    fetch() if args.command == "fetch" else analyze()
