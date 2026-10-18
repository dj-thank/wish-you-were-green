"""Independent physical and numerical checks, without replacing frozen-data QA.

Run with: python -m unittest discover -s tests -p test_scientific_invariants.py -v
"""
from pathlib import Path
import os
import sys
import unittest

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MPLBACKEND", "Agg")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np
from scipy.constants import c as LIGHT_SPEED, h as PLANCK_CONSTANT, k as BOLTZMANN_CONSTANT
from scipy.integrate import quad

import colour_pipeline as pipeline
from research.precision.precision_audit import ContinuousPlanckian, integrate_linear_product, rejected_native_support


class ScientificInvariants(unittest.TestCase):
    def test_flat_fnu_ab_standard_has_zero_magnitude_in_all_bands(self):
        # An AB reference has constant F_nu, not constant F_lambda. The explicit
        # Jy -> cgs and F_nu -> F_lambda conversion detects a missing lambda or
        # photon-weight factor in the synthetic-photometry calculation.
        wave = np.arange(2900.0, 11500.1, 1.0)
        flux_nu_cgs = 3631.0e-23
        flux_lambda_cgs_per_angstrom = flux_nu_cgs * LIGHT_SPEED * 1e10 / wave**2
        for system in ("sdss", "panstarrs"):
            with self.subTest(system=system):
                magnitude = pipeline.synthetic_gri(wave, flux_lambda_cgs_per_angstrom, system)
                # The residual of a 1 A numerical spectrum is <4 micro-mag.
                np.testing.assert_allclose(magnitude, 0, atol=1e-5, rtol=0)

    def test_planck_radiance_and_continuous_projection(self):
        geometry = ContinuousPlanckian()
        wave_m = pipeline.CMF_W * 1e-9
        for temperature in (1500, 3000, 5772, 12000, 1e6):
            with self.subTest(temperature=temperature):
                flux = (2 * PLANCK_CONSTANT * LIGHT_SPEED**2 / wave_m**5 /
                        np.expm1(PLANCK_CONSTANT * LIGHT_SPEED / (wave_m * BOLTZMANN_CONSTANT * temperature)))
                xyz = np.trapezoid(flux[:, None] * pipeline.CMF_V, pipeline.CMF_W, axis=0)
                physical = pipeline.xyz_to_metrics(xyz)
                calculated = pipeline.integrate_colour(pipeline.CMF_W * 10,
                                                        pipeline.blackbody(pipeline.CMF_W, temperature), mask_sky=False)
                np.testing.assert_allclose([calculated["u1960"], calculated["v1960"]],
                                           [physical["u1960"], physical["v1960"]], atol=1e-10, rtol=0)
                # The old 8000-temperature mesh deliberately remains frozen.
                # The new continuous projection should recover a true thermal
                # spectrum, including between the original mesh temperatures.
                projected = geometry.project(physical["u1960"], physical["v1960"])
                self.assertLess(projected["distance_continuous"], 1e-9)
                self.assertFalse(calculated["green_dominant"])

    def test_continuous_side_uses_normal_and_flags_endpoints(self):
        geometry = ContinuousPlanckian()
        q = 1000 / 5500
        centre = geometry.uv(q)
        tangent = geometry.uv(q + 1e-6) - geometry.uv(q - 1e-6)
        normal = np.array([-tangent[1], tangent[0]])
        normal /= np.linalg.norm(normal)
        for sign in (-1, 1):
            point = centre + sign * 1e-7 * normal
            result = geometry.project(*point)
            self.assertEqual(result["projection_class"], "interior")
            self.assertEqual(np.sign(result["duv_continuous_tangent_sign"]), sign)
            self.assertAlmostEqual(result["distance_continuous"], 1e-7, delta=1e-11)
        for q, label in ((0, "rayleigh_jeans_endpoint"), (1, "low_temperature_endpoint")):
            result = geometry.project(*geometry.uv(q))
            self.assertEqual(result["projection_class"], label)
            self.assertLess(result["distance_continuous"], 1e-12)
            self.assertTrue(np.isnan(result["duv_continuous_tangent_sign"]))

    def test_uv_noise_propagation_and_flux_unit_scale(self):
        wave = np.linspace(3600, 8300, 73)
        flux = 0.7 + 0.4 * np.exp(-((wave - 5400) / 1200)**2)
        sigma = 0.02 + 0.01 * (wave - wave.min()) / np.ptp(wave)
        nominal = pipeline.integrate_colour(wave, flux, 1 / sigma**2, mask_sky=False)
        jacobian = np.empty((2, len(wave)))
        step = 1e-4
        for index in range(len(wave)):
            upper, lower = flux.copy(), flux.copy()
            upper[index] += step
            lower[index] -= step
            hi = pipeline.integrate_colour(wave, upper, mask_sky=False)
            lo = pipeline.integrate_colour(wave, lower, mask_sky=False)
            jacobian[:, index] = [(hi[key] - lo[key]) / (2 * step) for key in ("u1960", "v1960")]
        expected_covariance = (jacobian * sigma**2) @ jacobian.T
        np.testing.assert_allclose([nominal["u1960_stat_error"], nominal["v1960_stat_error"]],
                                   np.sqrt(np.diag(expected_covariance)), rtol=1e-7, atol=0)
        for scale in (1e-17, 1e17):
            scaled = pipeline.integrate_colour(wave, flux * scale, 1 / (sigma * scale)**2, mask_sky=False)
            keys = ("u1960", "v1960", "u1960_stat_error", "v1960_stat_error", "uv_stat_error_max")
            np.testing.assert_allclose([scaled[key] for key in keys], [nominal[key] for key in keys], rtol=2e-13, atol=0)
            self.assertEqual(scaled["hex"], nominal["hex"])

    def test_joint_knot_quadrature_and_mask_support(self):
        wave_nm = np.array([360, 402, 448, 501, 557, 600, 641, 724, 780, 830], dtype=float)
        flux = np.array([0.8, 1.4, 1.2, 0.4, 1.1, 0.2, 0.3, 0.5, 0.45, 0.4])
        exact = integrate_linear_product(wave_nm * 10, flux)
        knots = np.unique(np.r_[pipeline.CMF_W, wave_nm])
        independent = []
        for index in range(3):
            value, error = quad(lambda w: np.interp(w, wave_nm, flux) *
                               np.interp(w, pipeline.CMF_W, pipeline.CMF_V[:, index]),
                               360, 830, points=knots[1:-1], limit=1200, epsabs=1e-10, epsrel=1e-10)
            self.assertLess(error, 1e-8)
            independent.append(value)
        np.testing.assert_allclose(exact, independent, rtol=2e-12, atol=0)
        # Rejecting no support has zero missing CMF mass, rejecting every native
        # support cell has mass one, and a mask plus its complement is additive.
        native = np.arange(3600, 8300.1, 0.8)
        selected = (native > 5100) & (native < 5250)
        zero = rejected_native_support(native, np.zeros(len(native), dtype=bool))
        complete = rejected_native_support(native, np.ones(len(native), dtype=bool))
        partial = np.array(rejected_native_support(native, selected))
        complement = np.array(rejected_native_support(native, ~selected))
        np.testing.assert_allclose(zero, 0, atol=1e-14, rtol=0)
        np.testing.assert_allclose(complete, 1, atol=1e-12, rtol=0)
        np.testing.assert_allclose(partial + complement, 1, atol=1e-12, rtol=0)


if __name__ == "__main__":
    unittest.main()
