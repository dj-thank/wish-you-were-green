#!/usr/bin/env python3
"""Download public MWDD spectra without modifying their published numeric samples.

Endpoints are documented by the official tables page scripts, not guessed:
scripts/init.js -> table.json; scripts/table.js -> WDs/{wdid}/{wdid}.html;
WDs/graph.js -> spectlist.txt -> individual spectrum paths.
The viewer's explicit request-only conditions are honoured.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import csv
import datetime as dt
import hashlib
import io
import json
from pathlib import Path
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

import numpy as np
try:
    import requests
except ImportError:
    requests = None

BASE = Path(__file__).resolve().parent
ORIGIN = "https://www.montrealwhitedwarfdatabase.org/"
BASELINES = ["WD 1328+648", "WD 0848+159", "SDSS J135123.86+264546.5",
             "[OHD2001] WD J2356-209", "LP 315-42"]
EXTRA_PRIORITY = ["SDSS J114333.46+661532.0", "GD 229"]
USER_AGENT = "MWDD-colour-research/0.1 (public scientific data; cached; max4 workers)"
HTTP_LOCAL = threading.local()


def stamp():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def safe_url(url):
    parts = urllib.parse.urlsplit(url)
    return urllib.parse.urlunsplit((parts.scheme, parts.netloc,
        urllib.parse.quote(urllib.parse.unquote(parts.path), safe="/"),
        parts.query, parts.fragment))


def read_url(url, target):
    """Keep exact response bytes and a sidecar digest; cache successes only."""
    target = Path(target)
    sidecar = target.with_suffix(target.suffix + ".source.json")
    if target.exists() and sidecar.exists():
        data = target.read_bytes()
        meta = json.loads(sidecar.read_text())
        if sha(data) == meta["sha256"]:
            return data, meta
    for attempt in range(2):
        try:
            if requests is not None:
                if not hasattr(HTTP_LOCAL, "session"):
                    HTTP_LOCAL.session = requests.Session()
                    HTTP_LOCAL.session.headers.update({"User-Agent": USER_AGENT})
                with HTTP_LOCAL.session.get(url, timeout=45) as response:
                    response.raise_for_status()
                    data = response.content
                    final_url, status, headers = response.url, response.status_code, response.headers
            else:
                request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
                with urllib.request.urlopen(request, timeout=45) as response:
                    data = response.read()
                    final_url, status, headers = response.geturl(), response.status, response.headers
            meta = {"url": url, "final_url": final_url, "retrieved_utc": stamp(),
                    "http_status": status,
                    "content_type": headers.get("Content-Type"),
                    "etag": headers.get("ETag"),
                    "last_modified": headers.get("Last-Modified"),
                    "size_bytes": len(data), "sha256": sha(data),
                    "path": str(target)}
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            sidecar.write_text(json.dumps(meta, ensure_ascii=False, indent=2))
            return data, meta
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as error:
            if isinstance(error, urllib.error.HTTPError) and error.code in (401, 403, 404):
                raise
            if attempt:
                raise
            time.sleep(0.5)


def number(value):
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def sexagesimal(text, hours=False):
    if not text:
        return None
    try:
        values = [float(v) for v in str(text).replace(":", " ").split()]
        sign = -1 if str(text).strip().startswith("-") else 1
        result = sign * (abs(values[0]) + values[1] / 60 + values[2] / 3600)
        return result * 15 if hours else result
    except (ValueError, IndexError):
        return None


def public_link(filename):
    # Exact logical conditions in official WDs/graph.js addSpectCheckbox.
    return ("blue" not in filename and ("Hollands" in filename or "red" not in filename)
            and "Gianninas2011" not in filename and "Bergeron2011" not in filename
            and "Limoge2015" not in filename)


def spectrum_kind(filename):
    lower = filename.lower()
    if ".xp." in lower:
        return "Gaia_XP"
    if "desi" in lower:
        return "DESI"
    if "sdss" in lower:
        return "SDSS"
    if "spy" in lower:
        return "SPY"
    return "other_ground_or_archive"


def star_metadata(row):
    return {"wdid": row["wdid"], "name": row.get("name"),
            "source_id": row.get("gaiaedr3") or row.get("gaiadr2"),
            "allnames": row.get("allnames", ""),
            "ra_sexagesimal": row.get("icrsra"), "dec_sexagesimal": row.get("icrsdec"),
            "ra_deg": sexagesimal(row.get("icrsra"), True),
            "dec_deg": sexagesimal(row.get("icrsdec")),
            "spectype": row.get("spectype"), "teff": number(row.get("teff")),
            "teff_error": number(row.get("Dteff")), "catalogue_source": row.get("source"),
            "catalogue_nbOpt": row.get("nbOpt"), "binarity": row.get("binarity"),
            "photometry": {key: row.get(key) for key in
                ["sg", "Dsg", "sr", "Dsr", "si", "Dsi", "su", "Dsu", "sz", "Dsz",
                 "pg", "Dpg", "pr", "Dpr", "pi", "Dpi", "pz", "Dpz", "py", "Dpy",
                 "PS_g", "DPS_g", "PS_r", "DPS_r", "PS_i", "DPS_i", "PS_z", "DPS_z", "PS_y", "DPS_y",
                 "G", "DG", "BP", "DBP", "RP", "DRP", "g_PS", "r_PS", "i_PS"]
                if row.get(key) is not None}}


def inspect_csv(data, raw_path):
    lines = data.decode("utf-8", "replace").splitlines()
    if len(lines) < 3:
        raise ValueError("Spectrum has fewer than three lines")
    # The official viewer removes one metadata line before parsing the CSV.
    header_metadata = next(csv.reader([lines[0]]))
    names = [field.strip() for field in next(csv.reader([lines[1]]))]
    matrix = np.loadtxt(io.StringIO("\n".join(lines[2:])), delimiter=",", ndmin=2)
    samples = {name: matrix[:, index] for index, name in enumerate(names)}
    if "wavelength" not in names or "flux" not in names:
        raise ValueError("Required wavelength and flux columns missing: " + str(names))
    wavelength = np.atleast_1d(samples["wavelength"])
    flux = np.atleast_1d(samples["flux"])
    good = np.isfinite(wavelength) & np.isfinite(flux)
    uncertainty_columns = [k for k in names if re.search("err|sigma|ivar|uncert|variance", k, re.I)]
    result = {"header_metadata": header_metadata, "columns": names,
              "npoints": int(len(wavelength)), "finite_points": int(good.sum()),
              "wave_min_angstrom": float(np.nanmin(wavelength)),
              "wave_max_angstrom": float(np.nanmax(wavelength)),
              "negative_flux_points": int((flux < 0).sum()),
              "uncertainty_columns": uncertainty_columns,
              "numeric_sha256_wavelength_flux": sha(np.column_stack([wavelength, flux]).astype("<f8").tobytes()),
              "wavelength_unit": "Angstrom (documented viewer axis)",
              "flux_unit": "unspecified in MWDD CSV; original published scale retained",
              "flux_density_convention": "MWDD viewer spectrum; verify source for F_lambda vs F_nu",
              "normalization_applied": False}
    # Separate faithful numeric copy for convenient analysis; do not imply verified flux units.
    parsed_path = BASE / "parsed" / (raw_path.stem + ".npz")
    parsed_path.parent.mkdir(parents=True, exist_ok=True)
    arrays = {"wavelength_angstrom": wavelength, "flux_original": flux}
    arrays.update({k: np.atleast_1d(samples[k]) for k in names if k not in ("wavelength", "flux")})
    temporary_parsed = parsed_path.with_suffix(".tmp.npz")
    with temporary_parsed.open("wb") as stream:
        np.savez_compressed(stream, **arrays)
    temporary_parsed.replace(parsed_path)
    result["parsed_path"] = str(parsed_path)
    return result


def acquire_star(row):
    star = star_metadata(row)
    star_hash = hashlib.sha256(row["wdid"].encode()).hexdigest()[:16]
    folder_url = ORIGIN + "WDs/" + urllib.parse.quote(row["wdid"], safe="") + "/"
    listing_url = folder_url + "spectlist.txt"
    results = []
    try:
        listing, listing_meta = read_url(listing_url, BASE / "listings" / (star_hash + ".txt"))
        for entry in dict.fromkeys(line.strip() for line in listing.decode().splitlines() if line.strip()):
            spec = dict(star)
            url = safe_url(urllib.parse.urljoin(folder_url, entry))
            spec.update({"spectrum_filename": entry, "kind": spectrum_kind(entry),
                         "source_url": url, "listing_url": listing_url,
                         "listing_path": listing_meta["path"],
                         "star_page_url": folder_url + urllib.parse.quote(row["wdid"], safe="") + ".html"})
            if not public_link(entry):
                spec.update({"status": "skipped_request_only", "reason": "MWDD viewer deliberately does not provide a public download link"})
                results.append(spec)
                continue
            if urllib.parse.urlsplit(url).hostname not in ("www.montrealwhitedwarfdatabase.org", "montrealwhitedwarfdatabase.org"):
                spec.update({"status": "skipped_external", "reason": "External spectrum link needs separate review"})
                results.append(spec)
                continue
            try:
                raw_path = BASE / "spectra" / (hashlib.sha256(url.encode()).hexdigest()[:24] + ".csv")
                data, source = read_url(url, raw_path)
                spec.update(source)
                spec["raw_path"] = str(raw_path)
                spec.update(inspect_csv(data, raw_path))
                spec["status"] = "downloaded"
            except Exception as error:
                spec.update({"status": "error", "error": type(error).__name__ + ": " + str(error)})
            results.append(spec)
    except Exception as error:
        results.append({**star, "listing_url": listing_url, "status": "listing_error",
                        "error": type(error).__name__ + ": " + str(error)})
    return results


def choose_targets(rows, limit, all_qz=False):
    selected = []
    for row in rows:
        st = row.get("spectype", "")
        teff = number(row.get("teff"))
        if row["wdid"] in BASELINES:
            priority = (0, BASELINES.index(row["wdid"]))
        elif row["wdid"] in EXTRA_PRIORITY:
            priority = (0, len(BASELINES) + EXTRA_PRIORITY.index(row["wdid"]))
        elif ("Q" in st or "Z" in st) and teff is not None and teff <= 7000:
            priority = (1, teff)
        elif all_qz and ("Q" in st or "Z" in st):
            priority = (2, teff if teff is not None else float("inf"))
        else:
            continue
        if int(row.get("nbOpt", 0) or 0) > 0:
            selected.append((priority, row))
    selected.sort(key=lambda pair: pair[0])
    return [row for _, row in selected[:limit if limit else None]]


def write_manifest(records):
    target = BASE / "manifest.json"
    temp = BASE / "manifest.tmp.json"
    temp.write_text(json.dumps(records, ensure_ascii=False, indent=2))
    temp.replace(target)
    columns = ["wdid", "name", "source_id", "ra_deg", "dec_deg", "spectype", "teff", "kind",
               "status", "spectrum_filename", "source_url", "raw_path", "parsed_path", "npoints",
               "wave_min_angstrom", "wave_max_angstrom", "sha256", "retrieved_utc", "flux_unit",
               "uncertainty_columns", "photometry", "error"]
    with (BASE / "manifest.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for record in records:
            writer.writerow({k: json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v
                             for k, v in record.items()})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0, help="0 = all DQ/DZ with Teff<=7000 plus baselines")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--all-qz", action="store_true", help="Also include all hotter and unknown-temperature DQ/DZ objects")
    args = parser.parse_args()
    if not 1 <= args.workers <= 4:
        parser.error("workers must be 1..4")
    if not (BASE / "table.json").exists():
        read_url(ORIGIN + "table.json", BASE / "table.json")
    rows = json.loads((BASE / "table.json").read_text())["data"]
    targets = choose_targets(rows, args.limit, args.all_qz)
    (BASE / "selected_targets.json").write_text(json.dumps(targets, ensure_ascii=False, indent=2))
    known = json.loads((BASE / "manifest.json").read_text()) if (BASE / "manifest.json").exists() else []
    # Recover per-star checkpoints that may be newer than the 25-star JSON snapshot.
    if (BASE / "manifest.jsonl").exists():
        for line in (BASE / "manifest.jsonl").read_text().splitlines():
            try:
                known.append(json.loads(line))
            except json.JSONDecodeError:
                pass  # Only a final interrupted write can be incomplete.
    by_source = {}
    for record in known:
        by_source[(record["wdid"], record.get("source_url", record.get("listing_url")))] = record
    known = list(by_source.values())
    groups = {}
    for record in known:
        groups.setdefault(record["wdid"], []).append(record)
    completed = {wdid for wdid, items in groups.items() if all(item.get("status") in
                 ("downloaded", "skipped_request_only", "skipped_external") for item in items)}
    pending = [row for row in targets if row["wdid"] not in completed]
    pending_ids = {row["wdid"] for row in pending}
    records = [record for record in known if record["wdid"] not in pending_ids]
    print(json.dumps({"selected_stars": len(targets), "pending_stars": len(pending), "existing_records": len(records)}), flush=True)
    started = time.monotonic()
    with (BASE / "manifest.jsonl").open("a") as incremental:
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = {executor.submit(acquire_star, row): row for row in pending}
            for index, future in enumerate(concurrent.futures.as_completed(futures), 1):
                results = future.result()
                records.extend(results)
                for record in results:
                    incremental.write(json.dumps(record, ensure_ascii=False) + "\n")
                incremental.flush()
                if index <= 8 or index % 25 == 0 or index == len(pending):
                    write_manifest(records)
                    print(json.dumps({"stars_finished": index, "total_stars": len(pending),
                                      "records": len(records), "last_wdid": futures[future]["wdid"],
                                      "downloaded": sum(r.get("status") == "downloaded" for r in records),
                                      "elapsed_seconds": round(time.monotonic()-started, 1)}), flush=True)
    write_manifest(records)
    summary = {"catalogue_objects": len(rows), "selected_stars": len(targets),
               "downloaded_spectra": sum(r.get("status") == "downloaded" for r in records),
               "downloaded_stars": len({r["wdid"] for r in records if r.get("status") == "downloaded"}),
               "status_counts": {s: sum(r.get("status") == s for r in records) for s in {r.get("status") for r in records}},
               "kind_counts": {s: sum(r.get("status") == "downloaded" and r.get("kind") == s for r in records)
                               for s in {r.get("kind") for r in records if r.get("status") == "downloaded"}},
               "finished_utc": stamp(), "selection": ("all DQ/DZ with an available optical spectrum, plus five colour baselines and GD229"
                   if args.all_qz else "DQ or DZ with Teff <= 7000K and an optical spectrum, plus five known colour baselines and GD229"),
               "catalogue_url": ORIGIN + "table.json", "catalogue_sha256": sha((BASE / "table.json").read_bytes())}
    (BASE / "acquisition_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary), flush=True)


if __name__ == "__main__":
    main()
