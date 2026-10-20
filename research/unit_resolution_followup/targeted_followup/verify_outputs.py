#!/usr/bin/env python3
"""Offline replay of three source-backed targets and one local-only follow-up."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd

from research.unit_resolution_followup.targeted_followup.analyse import compute, TARGETS
from research.unit_resolution_followup.targeted_followup.local_row_5827 import compute as compute_local


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def compare(first, second, label="result"):
    if isinstance(first, dict):
        assert isinstance(second, dict) and first.keys() == second.keys(), label
        for key in first:
            compare(first[key], second[key], label + "/" + str(key))
    elif isinstance(first, list):
        assert isinstance(second, list) and len(first) == len(second), label
        for i, (a, b) in enumerate(zip(first, second)):
            compare(a, b, label + "/" + str(i))
    elif isinstance(first, (int, float)) and not isinstance(first, bool):
        assert isinstance(second, (int, float)), label
        np.testing.assert_allclose(first, second, rtol=2e-12, atol=1e-22, err_msg=label)
    else:
        assert first == second, label


def verify(root=ROOT):
    root = Path(root).resolve()
    assert root == ROOT, "Import the verifier from the checkout being verified"
    recorded = json.loads((HERE / "results.json").read_text())
    replay, native = compute(root)
    compare(recorded["records"], replay["records"])
    assert recorded["verified_source_sha256"] == replay["verified_source_sha256"]
    assert [r["row_index"] for r in recorded["records"]] == list(TARGETS)
    checked = dict(replay["verified_source_sha256"])
    by_index = {r["row_index"]: r for r in recorded["records"]}
    assert [r["MWDD_frozen_class"] for r in recorded["records"]] == ["DAZH", "DZ", "DBZAe"]
    for index in (7607, 7930):
        known = by_index[index]["Kleinman2013_published_rows_within_2arcsec"]
        assert len(known) == 1 and known[0]["same_plate_mjd_fiber_as_selected_reference"]
    known = by_index[8019]["Kleinman2013_published_rows_within_2arcsec"]
    assert len(known) == 2 and not any(r["same_plate_mjd_fiber_as_selected_reference"] for r in known)
    assert by_index[8019]["Gaia_existing_variability_classification"][0]["best_class_name"] == "AGN"
    assert by_index[8019]["Gaia_DR3"]["phot_variable_flag"] == "VARIABLE"
    assert by_index[8019]["automatic_SDSS_ZWARNING_decoded"] == ["MANY_OUTLIERS", "NEGATIVE_EMISSION"]
    chandra = (HERE / "sources/chandra_cycle7.html").read_text()
    section = chandra.split("07700859", 1)[1].split("07700984", 1)[0]
    assert "SDSS J004527.69+1438" in section and "00:45:27.70" in section
    assert "+14:38:16.20" in section and "BALQSOs" in section
    peak = by_index[7930]["narrow_peak_native_check"]
    assert peak["peak_AND_mask"] == peak["peak_OR_mask"] == 1 << 27
    assert peak["contiguous_pixels_above_half_peak_excess"] == 2
    assert peak["half_excess_cluster_AND_bits"] == [{"bit": 27, "name": "BADSKYCHI", "pixels": 2}]
    samples = 0
    for index, arrays in native.items():
        exported = pd.read_csv(HERE / f"native_row_{index}.csv.gz", float_precision="round_trip")
        visible = (arrays["wave"] >= 3600) & (arrays["wave"] <= 8300)
        assert len(exported) == int(visible.sum())
        for name in ("wave", "flux", "ivar", "and_mask", "or_mask"):
            np.testing.assert_allclose(exported[name].to_numpy(), arrays[name][visible],
                                       rtol=2e-15, atol=0, err_msg=f"Native sample export: {index}/{name}")
        samples += len(exported)
    figures = json.loads((HERE / "figures_manifest.json").read_text())
    visual = json.loads((HERE / "visual_review.json").read_text())
    assert len(figures) == visual["actually_viewed_final_PNGs"] == 3
    assert {r["row_index"] for r in figures} == set(TARGETS)
    notes = {r["row_index"]: r for r in visual["records"]}
    for item in figures:
        assert sha(HERE / item["png"]) == item["png_sha256"]
        assert sha(HERE / item["svg"]) == item["svg_sha256"]
        note = notes[item["row_index"]]
        assert note["actually_viewed"] and note["sha256"] == item["png_sha256"]
        assert note["figure"] == item["png"] and note["observation"]
    local_recorded = json.loads((HERE / "local_row_5827.json").read_text())
    local_replay, local_native = compute_local(root)
    compare(local_recorded["record"], local_replay["record"], "local_row_5827")
    assert local_recorded["verified_source_sha256"] == local_replay["verified_source_sha256"]
    checked.update(local_replay["verified_source_sha256"])
    assert local_recorded["record"]["MWDD_frozen_class"] == "DZ:"
    assert local_recorded["record"]["automatic_SDSS_quality"]["SUBCLASS"] == "CV"
    assert local_recorded["record"]["red_peak_native_check"]["peak_AND_mask"] == 0
    assert local_recorded["record"]["red_peak_native_check"]["peak_OR_mask"] == 0
    exported = pd.read_csv(HERE / "native_row_5827.csv.gz", float_precision="round_trip")
    visible = (local_native["wave"] >= 3600) & (local_native["wave"] <= 8300)
    assert len(exported) == int(visible.sum())
    for name in ("wave", "flux", "ivar", "and_mask", "or_mask"):
        np.testing.assert_allclose(exported[name].to_numpy(), local_native[name][visible],
                                   rtol=2e-15, atol=0, err_msg=f"Native sample export: 5827/{name}")
    samples += len(exported)
    local_figure = local_recorded["figure"]
    assert sha(HERE / local_figure["png"]) == local_figure["png_sha256"]
    assert sha(HERE / local_figure["svg"]) == local_figure["svg_sha256"]
    local_visual = json.loads((HERE / "local_row_5827_visual_review.json").read_text())
    assert local_visual["actually_viewed"] and local_visual["row_index"] == 5827
    assert local_visual["figure"] == local_figure["png"]
    assert local_visual["sha256"] == local_figure["png_sha256"]
    assert local_visual["observation"] and local_visual["evidence_limits"]
    for path in sorted(HERE.rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts and path.name != "verification.json":
            checked[str(path.relative_to(root))] = sha(path)
    return {"summary": {
        "targeted_entities": 4, "source_backed_catalogue_followup_entities": 3,
        "additional_local_only_followup_entities": 1, "native_visible_samples_replayed": samples,
        "original_SDSS_Flambda_with_native_masks": 4, "same_observation_Fnu_exports_identified": 3,
        "same_observation_Flambda_exports_identified": 1,
        "published_Kleinman_rows_replayed": 4, "exact_selected_observation_classification_rows": 2,
        "same_position_other_observation_classification_rows": 2,
        "new_Gaia_target_rows": 3, "existing_Gaia_AGN_classification_rows": 1,
        "actually_viewed_final_PNGs_with_matching_hashes": 4,
        "spectral_shapes_deleted": 0, "network_required": False, "full_raw_cache_required": False,
        "limits": "Numerical/source replay of four purposively selected visual flags. Three include newly retrieved catalogue context; the fourth uses local native arrays and existing metadata only. No new physical classification, astronomical discovery, atmospheric fit, calibrated probability, or repeated visual perception."},
        "verified_file_sha256": checked}


if __name__ == "__main__":
    result = verify()
    result["status"] = "PASS"
    result["completed_utc"] = datetime.now(timezone.utc).isoformat()
    (HERE / "verification.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result["summary"], indent=2))
