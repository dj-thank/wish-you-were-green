"""Regression evidence for the real MWDD SDSS F_nu / F_lambda mixture.

Uses compact copies of two SHA-verified original observation pairs. The main
invariant is agreement with the *independent direct SDSS reference*, including
the colour that the unconverted F_nu input previously changed.
"""
from pathlib import Path
import copy
import hashlib
import json
import os
import sys
import tempfile
import unittest

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd

import colour_pipeline as pipeline
import flux_conventions as units
from project_io import load_json
from rank_candidates import annotate, summarize
from validate_candidates import get_arrays


class FluxConventionEvidence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture_root = ROOT / "research/precision/flux_units/fixtures"
        manifest = json.loads((cls.fixture_root / "manifest.json").read_text())
        cls.fixture = {}
        cls.evidence = {}
        for item in manifest["fixtures"]:
            path = cls.fixture_root / item["file"]
            if hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]:
                raise AssertionError("Independent source fixture SHA256 changed")
            convention = item["evidence"]["convention"]
            cls.fixture[convention] = dict(np.load(path, allow_pickle=False))
            cls.evidence[convention] = item["evidence"]
        cls.frozen = load_json(ROOT / "results/screen_input_mwdd.json")

    def record(self, convention="fnu"):
        entry = self.evidence[convention]
        record = copy.deepcopy(self.frozen[entry["mwdd_row_index"]])
        self.assertEqual(record["sha256"], entry["mwdd_sha256"])
        # Isolate the flux-density convention from an external photometry fit.
        record["photometry"] = {}
        return record

    def save_parsed(self, directory, convention="fnu", multiplier=1.0):
        arrays = self.fixture[convention]
        record = self.record(convention)
        path = Path(directory) / (convention + ".npz")
        np.savez(path, wavelength_angstrom=arrays["wave_mwdd"],
                 flux_original=arrays["flux_mwdd"] * multiplier)
        record["parsed_path"] = str(path)
        return record

    def test_real_fnu_observation_recovers_direct_sdss_colour(self):
        arrays = self.fixture["fnu"]
        w, original = arrays["wave_mwdd"], arrays["flux_mwdd"]
        converted, _, info = units.as_flux_lambda(w, original, None, self.record())
        reference = pipeline.integrate_colour(arrays["wave_direct"], arrays["flux_direct_flam"])
        corrected = pipeline.integrate_colour(w, converted)
        historical = pipeline.integrate_colour(w, original)
        keys = ["x", "y", "u1960", "v1960"]
        np.testing.assert_allclose([corrected[k] for k in keys],
                                   [reference[k] for k in keys], atol=2e-10, rtol=0)
        historical_distance = np.hypot(historical["u1960"] - reference["u1960"],
                                       historical["v1960"] - reference["v1960"])
        self.assertGreater(historical_distance, .01)
        self.assertTrue(info["flux_conversion_applied"])
        self.assertEqual(info["flux_input_convention"], "fnu")
        # A constant original scale is allowed; the native-sample shape must
        # still match the reference, including the actual line/noise pattern.
        direct = np.interp(w, arrays["wave_direct"], arrays["flux_direct_flam"])
        valid = (w > 4000) & (w < 8000) & (abs(direct) > .1 * np.median(abs(direct)))
        ratios = converted[valid] / direct[valid]
        np.testing.assert_allclose(ratios / np.median(ratios), 1, atol=1e-9, rtol=0)

    def test_verified_flambda_is_unchanged_and_agrees_with_reference(self):
        arrays = self.fixture["flambda"]
        w, original = arrays["wave_mwdd"], arrays["flux_mwdd"]
        converted, _, info = units.as_flux_lambda(w, original, None, self.record("flambda"))
        np.testing.assert_array_equal(converted, original)
        self.assertFalse(info["flux_conversion_applied"])
        actual = pipeline.integrate_colour(w, converted)
        reference = pipeline.integrate_colour(arrays["wave_direct"], arrays["flux_direct_flam"])
        np.testing.assert_allclose([actual["u1960"], actual["v1960"]],
                                   [reference["u1960"], reference["v1960"]], atol=5e-7, rtol=0)

    def test_frequency_to_wavelength_preserves_signed_signal_to_noise(self):
        arrays = self.fixture["fnu"]
        w, f = arrays["wave_mwdd"], arrays["flux_mwdd"]
        sigma = .03 * abs(f) + .01 * np.median(abs(f))
        ivar = 1 / sigma**2
        corrected, corrected_ivar, _ = units.as_flux_lambda(w, f, ivar, self.record())
        # A change of spectral-density units cannot change a pixel's signed
        # S/N; this catches incorrect variance factors, especially inversion.
        np.testing.assert_allclose(corrected * np.sqrt(corrected_ivar),
                                   f * np.sqrt(ivar), atol=2e-13, rtol=1e-14)
        self.assertTrue(np.all(corrected_ivar > 0))
        np.testing.assert_array_equal(np.signbit(corrected), np.signbit(f))

    def test_unknown_sha_is_rejected_even_for_familiar_sdss_archive(self):
        arrays = self.fixture["fnu"]
        record = self.record()
        record["sha256"] = "0" * 64
        with self.assertRaises(units.UnverifiedFluxConvention):
            units.as_flux_lambda(arrays["wave_mwdd"], arrays["flux_mwdd"], None, record)
        with tempfile.TemporaryDirectory() as directory:
            record = self.save_parsed(directory)
            record["sha256"] = "0" * 64
            result = pipeline.analyze_record(record)
            self.assertEqual(result["status"], "unit_unverified")
            self.assertFalse(result["flux_units_validated"])
            self.assertNotIn("u1960", result)
            self.assertNotIn("hex", result)
            with self.assertRaises(units.UnverifiedFluxConvention):
                get_arrays(record)

    def test_stale_or_double_converted_arrays_fail_at_both_entry_points(self):
        # Keep the verified original raw SHA and numeric hash while supplying
        # an already-converted NPZ: a realistic cache/entry-point regression.
        arrays = self.fixture["fnu"]
        with tempfile.TemporaryDirectory() as directory:
            record = self.save_parsed(directory, multiplier=units.C_ANGSTROM_PER_SECOND / arrays["wave_mwdd"]**2)
            result = pipeline.analyze_record(record)
            self.assertEqual(result["status"], "error")
            self.assertNotIn("u1960", result)
            with self.assertRaises(ValueError):
                get_arrays(record)

    def test_validation_helper_accepts_direct_flambda_and_inverse_variance(self):
        arrays = self.fixture["flambda"]
        evidence = self.evidence["flambda"]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "direct.npz"
            ivar = np.linspace(1, 3, len(arrays["wave_direct"])) * 1e32
            np.savez(path, wavelength_angstrom=arrays["wave_direct"],
                     flux_flam=arrays["flux_direct_flam"], ivar=ivar)
            record = {"kind": "SDSS", "source_url": evidence["direct_source_url"],
                      "sha256": evidence["direct_sha256"], "parsed_path": str(path)}
            w, f, iv = get_arrays(record)
            np.testing.assert_array_equal(w, arrays["wave_direct"])
            np.testing.assert_array_equal(f, arrays["flux_direct_flam"])
            np.testing.assert_array_equal(iv, ivar)

    def test_historical_reproduction_requires_explicit_selection_opt_in(self):
        with tempfile.TemporaryDirectory() as directory:
            record = self.save_parsed(directory)
            record["sha256"] = "0" * 64
            historical = pipeline.analyze_record(record, legacy_unverified_units=True)
            self.assertEqual(historical["status"], "ok")
            self.assertFalse(historical["flux_units_validated"])
            self.assertEqual(historical["flux_input_convention"], "legacy_assumed_flambda")
            current = annotate(pd.DataFrame([historical]))
            self.assertFalse(current.iloc[0].usable_screen)
            reproduced = annotate(pd.DataFrame([historical]), legacy_unverified_units=True)
            self.assertTrue(reproduced.iloc[0].usable_screen)
            raw = pipeline.integrate_colour(self.fixture["fnu"]["wave_mwdd"],
                                            self.fixture["fnu"]["flux_mwdd"])
            self.assertAlmostEqual(historical["u1960"], raw["u1960"], delta=1e-14)

    def test_entire_unknown_batch_is_retained_without_candidate_metrics(self):
        with tempfile.TemporaryDirectory() as directory:
            record = self.save_parsed(directory)
            record["sha256"] = "0" * 64
            rejected = pipeline.analyze_record(record)
        result = annotate(pd.DataFrame([rejected]))
        self.assertEqual(len(result), 1)
        self.assertEqual(result.iloc[0].status, "unit_unverified")
        self.assertFalse(result.iloc[0].usable_screen)

    def test_representative_does_not_prefer_the_largest_colour_anomaly(self):
        with tempfile.TemporaryDirectory() as directory:
            record = self.save_parsed(directory)
            baseline = pipeline.analyze_record(record)
        self.assertEqual(baseline["status"], "ok")
        stable, noisy = dict(baseline), dict(baseline)
        stable.update(visible_median_pixel_snr=30, duv=.005, distance_planck_uv=.005,
                      u1960=.20, v1960=.31, source_url="https://example.invalid/stable")
        noisy.update(visible_median_pixel_snr=2, duv=.04, distance_planck_uv=.04,
                     u1960=.22, v1960=.33, source_url="https://example.invalid/noisy")
        table = annotate(pd.DataFrame([noisy, stable]))
        table["known_hollands_colour"] = False
        result = summarize(table)
        self.assertEqual(len(result), 1)
        self.assertEqual(result.iloc[0].best_duv, .005)

    def test_catalogue_aliases_do_not_change_the_number_of_ranked_entities(self):
        with tempfile.TemporaryDirectory() as directory:
            baseline = pipeline.analyze_record(self.save_parsed(directory))
        # One physical association has two archive names; a second association
        # happens to share the first display name. Names must neither split the
        # first entity nor merge the second one into it.
        first, alias, other = [dict(baseline) for _ in range(3)]
        first.update(entity_id="gaia:1234567890123456789", source_id="1234567890123456789", wdid="Archive A name",
                     visible_median_pixel_snr=2, source_url="https://example.invalid/a")
        alias.update(entity_id=first["entity_id"], source_id=first["source_id"], wdid="Archive B name",
                     visible_median_pixel_snr=30, source_url="https://example.invalid/b")
        other.update(entity_id="gaia:2234567890123456789", source_id="2234567890123456789", wdid="Archive A name",
                     visible_median_pixel_snr=15, source_url="https://example.invalid/c")
        table = annotate(pd.DataFrame([first, alias, other]))
        table["known_hollands_colour"] = False
        ranked = summarize(table).set_index("entity_id")
        self.assertEqual(len(ranked), 2)
        self.assertEqual(ranked.spectra.sum(), 3)
        self.assertEqual(ranked.loc[first["entity_id"], "spectra"], 2)
        self.assertEqual(ranked.loc[first["entity_id"], "wdid"], "Archive B name")
        self.assertEqual(ranked.loc[other["entity_id"], "spectra"], 1)
        renamed = table.assign(wdid=["Renamed A", "Renamed B", "Renamed C"])
        after = summarize(renamed.iloc[::-1]).set_index("entity_id")
        pd.testing.assert_frame_equal(ranked.drop(columns="wdid").sort_index(),
                                      after.drop(columns="wdid").sort_index())
        legacy = summarize(table.drop(columns="entity_id"))
        self.assertEqual(set(legacy.wdid), {"Archive A name", "Archive B name"})
        self.assertEqual(legacy.spectra.sum(), 3)
        self.assertTrue(legacy.entity_id.isna().all())


if __name__ == "__main__":
    unittest.main()
