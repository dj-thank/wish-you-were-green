#!/usr/bin/env python3
"""Offline, hash-checked survey passbands with explicit finite-table closure."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re

import numpy as np
from speclite.filters import FilterResponse

from research.measurement_design.fetch_profiles import parse_profile

HERE = Path(__file__).resolve().parent


def load_profiles(closure_width_A=1.):
    """Retain every supplied sample; close nonzero finite-table ends explicitly.

    The small J-PLUS endpoint values do not specify a physical infinite tail.
    This convention adds a linear ramp to zero outside the supplied table.
    Its sensitivity is tested with a 10 Å ramp. No stellar spectrum is extended.
    """
    if closure_width_A <= 0:
        raise ValueError("Closure width must be positive")
    manifest = json.loads((HERE / "profile_manifest.json").read_text())
    outputs = []
    for record in manifest["profiles"]:
        path = HERE / record["file"]
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != record["sha256"]:
            raise AssertionError(f"Profile hash changed: {path}")
        params, rows = parse_profile(data)
        if params["DetectorType"] != "1" or params["WavelengthUnit"] != "Angstrom":
            raise AssertionError("Requires photon-counting responses in Angstrom")
        numeric = np.asarray(rows, dtype=float)
        wave, response = numeric.T
        if not (np.all(np.diff(wave) > 0) and np.all(response >= 0)
                and np.all(np.isfinite(numeric))):
            raise AssertionError("Invalid profile")
        additions = []
        if response[0] != 0:
            additions.append([float(wave[0]-closure_width_A), 0.])
            wave, response = np.r_[wave[0]-closure_width_A, wave], np.r_[0., response]
        if response[-1] != 0:
            additions.append([float(wave[-1]+closure_width_A), 0.])
            wave, response = np.r_[wave, wave[-1]+closure_width_A], np.r_[response, 0.]
        band_name = re.sub(r"[^A-Za-z0-9_]", "_", record["filter_id"])
        flt = FilterResponse(wave, response, meta={"group_name": "additional", "band_name": band_name})
        meta = {
            "filter_id": record["filter_id"], "speclite_name": flt.name,
            "raw_path": str(path.relative_to(HERE.parents[1])),
            "raw_sha256": record["sha256"], "source_url": record["url"],
            "source_retrieved_utc": record["retrieved_utc"],
            "detector_type": "photon_counting", "wavelength_unit": "Angstrom",
            "profile_reference": params.get("ProfileReference"),
            "description": params.get("Description"),
            "raw_sample_count": len(rows), "retained_raw_sample_count": len(rows),
            "endpoint_closure_width_A": float(closure_width_A),
            "added_zero_endpoints": additions,
            "minimum_A": float(wave.min()), "maximum_A": float(wave.max()),
            "effective_wavelength_A": float(flt.effective_wavelength.value),
            "numeric_sha256": hashlib.sha256(np.column_stack((wave, response)).astype("<f8").tobytes()).hexdigest(),
        }
        outputs.append((flt, meta))
    return outputs


def covered_profiles(minimum, maximum, closure_width_A=1.):
    accepted, excluded = [], []
    for flt, meta in load_profiles(closure_width_A):
        if minimum <= flt.wavelength.min() and maximum >= flt.wavelength.max():
            accepted.append((flt, meta))
        else:
            excluded.append({**meta, "reason": "full_tabulated_passband_and_closure_not_bracketed_by_observed_spectrum",
                             "observed_minimum_A": float(minimum), "observed_maximum_A": float(maximum)})
    return accepted, excluded
