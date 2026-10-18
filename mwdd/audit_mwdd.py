#!/usr/bin/env python3
"""Report numerical input quality without making colour or novelty claims."""
import csv
import json
from pathlib import Path

import numpy as np

from acquire_mwdd import BASE


def finite_value(value):
    value = float(value)
    return value if np.isfinite(value) else None


def main():
    source = BASE / "manifest_enriched.json"
    records = json.loads(source.read_text())
    output = []
    for record in records:
        if record.get("status") != "downloaded":
            continue
        with np.load(record["parsed_path"], allow_pickle=False) as samples:
            wavelength = samples["wavelength_angstrom"]
            flux = samples["flux_original"]
            visible = np.isfinite(wavelength) & (wavelength >= 3800) & (wavelength <= 7800)
            ordered_wavelengths = np.unique(wavelength[np.isfinite(wavelength)])
            steps = np.diff(ordered_wavelengths)
            visible_wavelengths = np.sort(wavelength[visible])
            visible_steps = np.diff(visible_wavelengths)
            row = {"wdid": record["wdid"], "kind": record.get("kind"),
                   "source_url": record["source_url"], "raw_path": record["raw_path"],
                   "npoints": len(wavelength), "n_visible_points": int(visible.sum()),
                   "n_nonfinite_flux": int((~np.isfinite(flux)).sum()),
                   "n_nonfinite_wavelength": int((~np.isfinite(wavelength)).sum()),
                   "n_negative_visible_flux": int((visible & (flux < 0)).sum()),
                   "n_nonincreasing_steps": int((np.diff(wavelength) <= 0).sum()),
                   "n_duplicate_wavelengths": int(len(wavelength)-len(ordered_wavelengths)),
                   "min_wavelength_angstrom": finite_value(wavelength.min()),
                   "max_wavelength_angstrom": finite_value(wavelength.max()),
                   "max_gap_angstrom": finite_value(steps.max()) if len(steps) else None,
                   "max_visible_gap_angstrom": finite_value(visible_steps.max()) if len(visible_steps) else None,
                   "covers_3800_7800": bool(wavelength.min() <= 3800 and wavelength.max() >= 7800),
                   "covers_3600_8300": bool(wavelength.min() <= 3600 and wavelength.max() >= 8300),
                   "sigma_supplied": "sigma" in samples,
                   "flag_supplied": "flag" in samples,
                   "duplicate_numeric_of": record.get("duplicate_numeric_of")}
            if "sigma" in samples:
                sigma = samples["sigma"]
                valid = visible & np.isfinite(flux) & np.isfinite(sigma) & (sigma > 0)
                row["median_visible_flux_over_sigma"] = finite_value(np.median(flux[valid]/sigma[valid])) if valid.any() else None
                row["n_invalid_visible_sigma"] = int((visible & (~np.isfinite(sigma) | (sigma <= 0))).sum())
            if "flag" in samples:
                row["n_nonzero_visible_flags"] = int((visible & (samples["flag"] != 0)).sum())
        output.append(row)
    columns = list(dict.fromkeys(key for row in output for key in row))
    with (BASE / "input_quality.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(output)
    summary = {"spectra_checked": len(output),
               "nonfinite_flux_spectra": sum(r["n_nonfinite_flux"] > 0 for r in output),
               "nonfinite_wavelength_spectra": sum(r["n_nonfinite_wavelength"] > 0 for r in output),
               "nonincreasing_wavelength_spectra": sum(r["n_nonincreasing_steps"] > 0 for r in output),
               "covers_3800_7800_spectra": sum(r["covers_3800_7800"] for r in output),
               "covers_3600_8300_spectra": sum(r["covers_3600_8300"] for r in output),
               "sigma_supplied_spectra": sum(r["sigma_supplied"] for r in output),
               "flag_supplied_spectra": sum(r["flag_supplied"] for r in output),
               "nonzero_visible_flag_spectra": sum(r.get("n_nonzero_visible_flags", 0) > 0 for r in output),
               "interpretation": "These are numerical input diagnostics, not final science selection or independence tests."}
    (BASE / "input_quality_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
