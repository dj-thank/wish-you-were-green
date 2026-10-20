#!/usr/bin/env python3
"""Offline exact-ID comparison with Lopez-Sanjuan et al. (2025), A&A 701 A273.

The CDS paper table has no Gaia ID.  It is joined through the original J-PLUS
DR3 published Gaia cross-match by the two-column (TileID, Number) identifier.
The independent 15-arcsec CDS queries cover the full fixed 25-object cohort.
These fitted/classification quantities are not additional measured fluxes.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def helper(path):
    spec = importlib.util.spec_from_file_location("independent_photo_prior_helper", path)
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


def build(root: Path, output: Path | None = None) -> dict:
    root = root.resolve()
    base = root / "research/independent_photometry"
    dest = output or base
    dest.mkdir(parents=True, exist_ok=True)
    code = helper(base / "build_catalogue.py")
    raw = base / "raw"
    cohort = json.loads((root / code.MANIFEST).read_text())
    ids = sorted(r["source_id"] for r in cohort)
    gaia = {r["source_id"]: r for r in code.read_rows(root / code.GAIA)}
    matches = code.read_rows(raw / "jplus_dr3_gaia_matches.csv")
    match_map = {r["Source"]: r for r in matches}
    assert len(match_map) == len(matches)
    all_rows = []
    query_files = sorted(raw.glob("jplus_dr3_wd_cds_cones[0-4].csv"))
    assert len(query_files) == 5
    for path in query_files:
        all_rows += code.read_rows(path)
    row_map = {(r["TileID"], r["Number"]): r for r in all_rows}
    assert len(row_map) == len(all_rows)
    direct = code.read_rows(raw / "jplus_dr3_wd_cds_matched.csv")
    assert {(r["TileID"], r["Number"]) for r in direct} <= set(row_map)
    for r in direct:
        assert r == row_map[r["TileID"], r["Number"]]
    types = {0: "not_an_outlier_in_this_published_model_test",
             1: "published_random_measurement_fluctuation_group",
             2: "published_metal_polluted_group",
             3: "published_two_component_group_including_some_DQ"}
    output_rows = []
    for sid in ids:
        row = dict(source_id=sid, matched_published_classification=False,
            counterpart_status="no_exact_published_DR3_Gaia_crossmatch", tile_id=None, number=None,
            rounded_catalogue_position_sep_from_gaia2016_arcsec=None,
            p_H=None, p_Ca=None, equivalent_width_J0395_angstrom=None,
            equivalent_width_error_angstrom=None, chi2=None, type_outlier=None,
            published_group=None, teff_H_K=None, teff_He_K=None,
            teff_calcium_analysis_K=None, fitted_dereddened_r_mag=None,
            interpretation="Missing table membership is not a normal-spectrum classification.")
        match = match_map.get(sid)
        if match:
            key = match["TILE_ID"], match["NUMBER"]
            row.update(tile_id=key[0], number=key[1], counterpart_status="no_CDS_row_for_exact_DR3_object")
            original = row_map.get(key)
            if original:
                ref = gaia[sid]
                distance = code.separation(code.unit_vector(float(ref["ra"]), float(ref["dec"])),
                    code.unit_vector(float(original["RAJ2000"]), float(original["DEJ2000"])))
                assert distance < 1.0, (sid, distance)
                t = int(original["Typeout"])
                assert t in types
                row.update(matched_published_classification=True,
                    counterpart_status="exact_Gaia_to_DR3_tuple_to_CDS_row",
                    rounded_catalogue_position_sep_from_gaia2016_arcsec=distance,
                    p_H=float(original["pH"]), p_Ca=float(original["pca"]),
                    equivalent_width_J0395_angstrom=float(original["EWJ0395"]),
                    equivalent_width_error_angstrom=float(original["e_EWJ0395"]),
                    chi2=float(original["chi2"]), type_outlier=t, published_group=types[t],
                    teff_H_K=float(original["TeffH"]) or None,
                    teff_He_K=float(original["TeffHe"]) or None,
                    teff_calcium_analysis_K=float(original["TeffCa"]) or None,
                    fitted_dereddened_r_mag=float(original["rmag"]),
                    interpretation="Published DR3 posterior/model-residual classification; not new photometry, not a new discovery.")
        output_rows.append(row)
    result = dict(study="Lopez-Sanjuan et al. 2025, Astronomy & Astrophysics 701, A273",
        doi="10.1051/0004-6361/202555286", paper_url="https://arxiv.org/abs/2509.21304",
        catalogue_url="https://cdsarc.cds.unistra.fr/viz-bin/cat/J/A+A/701/A273",
        fixed_candidates=25, matched_candidates=sum(r["matched_published_classification"] for r in output_rows),
        known_classes_by_source={r["source_id"]: r["type_outlier"] for r in output_rows if r["matched_published_classification"]},
        identity_method="Exact Gaia DR3 ID -> J-PLUS DR3 (TILE_ID,NUMBER) -> CDS (TileID,Number), plus <1 arcsec rounded-coordinate check",
        caveats=["The catalogue's rmag is a fitted de-reddened total magnitude; it is not an observed DR4 measurement.",
                 "pCa depends on the published atmospheric-continuum model and population prior.",
                 "Type 1 is a UMAP group interpreted by the authors; it is not proof of the absence of metals or variability.",
                 "Unmatched objects have no classification assigned here.",
                 "The current public CEFCA TAP schema did not advertise jplus.WhiteDwarf; the CDS archive supplies the numeric publication table.",
                 "DR3 and DR4 can contain the same exposures and must not be treated as independent observations merely because their releases differ."],
        input_sha256={str(p.relative_to(root)): code.sha(p) for p in
            [root / code.MANIFEST, root / code.GAIA, raw / "jplus_dr3_gaia_matches.csv",
             raw / "jplus_dr3_wd_cds_matched.csv", raw / "jplus_dr3_wd_readme.txt"] + query_files},
        candidates=output_rows)
    code.write_csv(dest / "prior_classifications.csv", output_rows)
    (dest / "prior_classifications.json").write_text(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=HERE.parents[1])
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    result = build(args.root, args.output_dir)
    print(json.dumps({k: result[k] for k in ["fixed_candidates", "matched_candidates", "known_classes_by_source"]}, indent=2))


if __name__ == "__main__":
    main()
