#!/usr/bin/env python3
"""Freeze direct ZTF DR24 light curves after public TAP identification."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import csv
import json
import math

from acquire import BASE, RAW, SOURCES, IRSA_TAP, ZTF_API, fetch, tap


def separation(ra, dec, ra0, dec0):
    dra = math.radians(ra - ra0)
    ddec = math.radians(dec - dec0)
    aa = math.sin(ddec / 2) ** 2 + math.cos(math.radians(dec)) * math.cos(math.radians(dec0)) * math.sin(dra / 2) ** 2
    return 2 * math.asin(min(1., math.sqrt(aa))) * 180 / math.pi * 3600


def inventory_path(name):
    if name == "J0429-0354":
        return RAW / "ztf_dr24_J0429_tight_ids.csv"
    return RAW / f"ztf_dr24_{name}_tight_ids.csv"


def candidate_records():
    selected = []
    for name, (source_id, ra, dec) in SOURCES.items():
        for row in csv.DictReader(inventory_path(name).open()):
            row["candidate"] = name
            row["gaia_source_id"] = source_id
            row["separation_from_gaia2016_arcsec"] = separation(float(row["ra"]), float(row["dec"]), ra, dec)
            # The catalogue reference positions can precede the exposure dates.
            # An intentionally generous fixed-epoch radius identifies candidates;
            # exposure-level propagation and matching happen during analysis.
            row["selected"] = row["separation_from_gaia2016_arcsec"] < 1.5 and int(row["ngoodobsrel"]) >= 5
            selected.append(row)
    (BASE / "ztf_object_selection.json").write_text(json.dumps(selected, indent=2) + "\n")
    return [row for row in selected if row["selected"]]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("stage", choices=["candidates", "control_inventory", "controls"])
    args = p.parse_args()
    records = candidate_records()
    if args.stage == "candidates":
        jobs = [("ztf_dr24_oid_" + row["oid"], ZTF_API,
                 dict(ID=row["oid"], COLLECTION="ztf_dr24", FORMAT="csv")) for row in records]
    elif args.stage == "control_inventory":
        jobs = []
        for name, (_, ra, dec) in SOURCES.items():
            primary = max((r for r in records if r["candidate"] == name and int(r["fid"]) == 2),
                          key=lambda r: int(r["ngoodobsrel"]))
            rmag = float(primary["medianmag"])
            # Select on position/magnitude/number of points and shape, never on
            # variability itself; hence a variable control can be discovered.
            q = ("SELECT TOP 300 oid,ra,dec,fid,field,ccdid,qid,medianmag,refmag,refchi,refsharp,"
                 "ngoodobsrel,nobsrel,medmagerr,magrms,chisq,astrometricrms "
                 "FROM ztf_objects_dr24 WHERE "
                 f"CONTAINS(POINT('ICRS',ra,dec),CIRCLE('ICRS',{ra},{dec},0.05))=1 "
                 f"AND fid=2 AND field={primary['field']} AND ccdid={primary['ccdid']} AND qid={primary['qid']} "
                 f"AND medianmag BETWEEN {rmag - 0.35} AND {rmag + 0.35} AND ngoodobsrel>=30")
            jobs.append(tap("ztf_dr24_control_inventory_" + name, IRSA_TAP, q))
    else:
        selection = []
        for name, (_, ra, dec) in SOURCES.items():
            rows = list(csv.DictReader((RAW / f"ztf_dr24_control_inventory_{name}.csv").open()))
            for r in rows:
                r["candidate_field"] = name
                r["distance_arcsec"] = separation(float(r["ra"]), float(r["dec"]), ra, dec)
            eligible = [r for r in rows if r["distance_arcsec"] >= 15 and float(r["refchi"]) < 3
                        and abs(float(r["refsharp"])) < 0.5]
            eligible.sort(key=lambda r: r["distance_arcsec"])
            chosen = eligible[:5]
            selection.extend(chosen)
        (BASE / "control_selection.json").write_text(json.dumps(selection, indent=2) + "\n")
        jobs = [("ztf_dr24_oid_" + row["oid"], ZTF_API,
                 dict(ID=row["oid"], COLLECTION="ztf_dr24", FORMAT="csv")) for row in selection]
    with ThreadPoolExecutor(max_workers=2) as pool:
        for r in pool.map(lambda j: fetch(*j), jobs):
            print(json.dumps(r), flush=True)


if __name__ == "__main__":
    main()
