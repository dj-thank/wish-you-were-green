# Independent scientific review of the colour screen

Review date: 2026-10-18 UTC. This review did not edit the main analysis files.

## Conclusion

No material mathematical error was found that invalidates the present, conditional colour estimates for J0913+4434 and J0429−0354. The energy weighting, colour-space transformations, photometric passbands, variance rescaling, and local Monte Carlo recalibration feedback are consistent with their stated purposes. This is an approval of the calculation as a candidate screen and a conditional measurement, not a confirmation of an original astronomical discovery or a complete uncertainty budget.

Reviewed versions:

| File | SHA-256 |
|---|---|
| colour_pipeline.py | 1485fa3567d7e8ef474c7442dfbafb181c4f5b0afa5780024284f994d9057c78 |
| validate_candidates.py | 2c26692c0a2b5e44b8a9dbb1fcb09984d2898492d54cb7f1e1be46bd606a416d |
| run_full_screen.py | 28817d7090dd390a6292cdc8454e855812fb107d673d4b9ed5eebd502df1ab57 |
| rank_candidates.py | 6150f241be63e566eefd2f9265888fe42adbc467c7558122891e4bf180804808 |

## Methods checked

1. **CIE integration:** The calculation integrates energy flux density F_lambda against the CIE 1931 two-degree colour-matching functions with trapezoidal wavelength weights. An additional photon-counting factor of wavelength would be incorrect here and is not applied. Converting wavelength from angstrom to nanometres without simultaneously rescaling flux density changes all three XYZ values by the same constant; the reported chromaticities and normalized RGB values are unaffected.
2. **Photometry:** Synthetic CCD-band fluxes correctly include the wavelength factor appropriate to photon-counting response curves. SDSS and PS1 are evaluated with their own response curves (`sdss2010` and `panstarrs`, the latter documented in the installed response metadata as Tonry et al. 2012). An SDSS g magnitude is never treated as a PS1 g magnitude. The direct SDSS positive PSF fluxes are converted from nanomaggies using 22.5 − 2.5 log10(flux), avoiding asinh-magnitude conventions at low signal.
3. **Colour coordinates:** The implementation uses CIE 1960 u = 4x/(−2x+12y+3) and v = 6y/(−2x+12y+3), not the 1976 v-prime. Blackbody spectra use B_lambda, and the infinite-temperature Rayleigh–Jeans endpoint is included. The nearest-locus distance is measured in the stated 1960 coordinates.
4. **Display conversion:** The XYZ-to-linear-sRGB matrix and the piecewise sRGB transfer function are consistent. Clipping is applied only to the displayed RGB values; chromaticity and the distance statistic remain unclipped. Display normalization cannot supply an absolute brightness or a unique appearance under all viewing conditions.
5. **Uncertainty algebra:** Multiplying flux by a wavelength-dependent correction requires dividing inverse variance by the squared correction; this is implemented correctly. The XYZ and u/v first-order covariance propagation is also algebraically consistent under its independent-pixel assumption.
6. **Recalibration Monte Carlo:** The first-order band-magnitude derivative, the sign of the feedback from noisy synthetic magnitudes, and the weighted two-parameter solution are consistent. Omitting the fitted scalar normalization from a chromaticity calculation is correct because it cancels. The updated function explicitly uses the same `mask_sky` choice for nominal and Monte Carlo calculations.

## Numerical review checks

### Calibration before versus after cleaning

The main functions fit the photometric tilt on the original spectrum, then remove invalid pixels and narrow sky-line windows for the colour integration. For strict consistency, future revisions should fit and integrate the same finite-pixel spectrum. This discrepancy was measured on seven validated candidates; it is small for the present leaders.

| Candidate and spectrum | Anchor | Duv shift after excluding invalid pixels before fitting | Duv shift after also applying nominal sky cleaning before fitting |
|---|---|---:|---:|
| J0913+4434 DESI | SDSS | −0.0000085 | +0.0000101 |
| J0913+4434 DESI | PS1 | −0.0000053 | +0.0000154 |
| J0429−0354 DESI | PS1 | +0.0000362 | +0.0000361 |
| J1258+0106 DESI | SDSS | +0.0000118 | +0.0000117 |

No green classification changed. The largest absolute Duv shift among all tested calibrations was approximately 0.0000692 for the pink candidate J1255+6712. Gaia XP spectra in this test had no removed invalid pixels, so this comparison did not change their results. Full measurements are in `calibration_cleaning_audit.json`.

### Local linearization versus a full nonlinear refit

Eighty Gaussian perturbations of the cleaned J0913+4434 DESI spectrum, with direct SDSS photometric errors and the same 0.02-mag floor, were recalibrated both with the Monte Carlo local linear solution and with a full nonlinear three-band fit. The test anchored the refits to the nominal synthetic magnitudes, matching the local Monte Carlo formulation. A scalar 40-mag normalization shift was used only to keep the normalized test spectrum inside the calibration function's valid magnitude range; it cancels in chromaticity.

| Exact minus linearized quantity | Mean | RMS | Maximum absolute difference |
|---|---:|---:|---:|
| Tilt, mag per 1000 angstrom | 0.0000148 | 0.0000512 | 0.0001515 |
| Duv | 0.000000353 | 0.000001223 | 0.000003604 |
| Normalized linear green-channel margin | 0.0000160 | 0.0000558 | 0.0001691 |

These differences are negligible compared with the approximately 0.002-wide one-sided Duv uncertainty range for this candidate. This check validates the local approximation under its noise assumptions; it does not validate the assumptions themselves. Numeric results are in `linear_mc_audit.json`.

## Material limitations and reporting requirements

- **Monte Carlo intervals are conditional.** The supplied DESI/SDSS uncertainties are treated as independent resampled pixels; spectral covariance, residual calibration structure, stellar variability, unresolved sources, and all modelling errors are not included. The original MWDD Gaia XP exports do not supply the full coefficient covariance, and their current simulations are explicitly photometry-only. A separate official Gaia covariance analysis must be reported separately until integrated and checked. A green fraction of 1.0 in 6000 trials is not a 100% probability that the astronomical claim is true.
- **Calibration does not produce fully independent repetitions.** Gaia XP and DESI measurements calibrated to the same gri measurements share photometric uncertainty. Their probabilities or error bars should not be multiplied or combined as if independent. Agreement of the *raw* spectra, and agreement under both SDSS and PS1 anchoring where available, provide additional evidence. Both raw spectra of J0913 and J0429 are green by the implemented criterion.
- **Narrow masking includes genuine Na D absorption.** The nominal 5890/5896-angstrom windows can remove astrophysical line cores as well as airglow. Broad wings remain. The existing no-mask sensitivity calculation should stay in the deliverable. For J0913 DESI, nominal versus unmasked Duv differs by about 0.00062 with SDSS anchors and 0.00061 with PS1 anchors; both remain green and beyond the 0.01 threshold. J0429 likewise retains its classification.
- **The all-object list is a screen.** CLEAN=0 photometry, missing noise arrays, loose 0.15-mag calibration residual acceptance, marginal green-channel dominance, and duplicate observations are not enough for a validated result. The two main candidates have received extra checks. The all-object counts should not be described as a count of newly discovered coloured stars. The two-parameter fit has one residual degree of freedom; residuals relative to the actual band errors are more informative than a universal 0.15-mag gate when promoting further candidates.
- **Threshold meaning:** A distance of 0.01 from the Planckian locus is a colour-selection rule, not a statistical significance, a visual saturation scale, or proof of newness. Positive Duv alone is not sufficient for green-channel dominance. Normalized sRGB hex values describe a fixed rendering convention; these candidates are pale yellow-green under that convention.
- **Duplicate and positional matching:** The same SDSS observation may occur in MWDD and the direct SDSS download. The five-arcsecond catalogue cross-match can also miss high-proper-motion aliases. Count independent instruments/observations from provenance, not just rows, and retain source IDs as strings when reloading CSVs.
- **Main-object photometric quality:** J0913 has a red neighbour at approximately 5.34 arcsec in Gaia DR3, 5.54 arcsec in PS1, and 6.35 arcsec in SDSS. Its SDSS source has CLEAN=1 but is a deblended child and carries r-band interpolation/cosmic-ray flags. Gaia has four blended BP and RP transits out of 48 each. Good RUWE and a non-duplicated source flag do not eliminate blending concerns. These limits belong alongside its positive spectral evidence.

## Direct PS1 check for J0429−0354

The official PS1 DR2 mean catalogue was queried within 10 arcsec with `nDetections > 1`. The target is object **103310674362622776**, at RA 67.4362830967 degrees, Dec −3.9064415057 degrees, with 77 detections. Its direct mean PSF magnitudes agree with the MWDD values used for calibration within 0.000000003 mag, so the existing calibrated colours do not need an update.

| Band | Mean PSF magnitude | Reported mean error | Number of contributing points | Reported scatter |
|---|---:|---:|---:|---:|
| g | 19.22470093 | 0.014436 | 11 | 0.055809 |
| r | 18.80220032 | 0.004775 | 16 | 0.019066 |
| i | 18.78630066 | 0.005005 | 17 | 0.027575 |

The only other returned PS1 mean source is an i-only object with two detections, i = 21.2831 ± 0.1499, at 9.736 arcsec from the target. This query does not show a similarly bright close neighbour; it is not a proof that no unresolved source exists. All three target band flags are 115000, preserved numerically without unsupported flag interpretation. Raw response and exact query/provenance are in `secondary_quality/`. The raw CSV SHA-256 is `b7df439297f19cec0a1a631473ce13e5b948cb58859deb50ca7c1974479bc553`.

## Review disposition of strict candidates

J0913+4434 remains the strongest colour departure supported by both Gaia XP and DESI, with the documented neighbour and covariance caveats. J0429−0354 remains a useful second case: its departure is smaller, but the two spectra agree and the direct PS1 anchor check passes. J1258+0106 should remain downgraded because the independent astrometric review reported close companions. SDSS J101959.51+204553.4 is a weaker screen candidate: only one MWDD SDSS spectrum passes, its export supplies no noise, its green margin is small, and its uncalibrated rendering is close to yellow-white. No priority increase is recommended for that object on this evidence.

## Primary data and method references

- CIE 1931 colour-matching functions: https://cie.co.at/datatable/cie-1931-colour-matching-functions-2-degree-observer
- SDSS magnitude definitions: https://www.sdss4.org/dr17/algorithms/magnitudes/
- SDSS flag guidance: https://www.sdss4.org/dr17/tutorials/flags/
- PS1 catalogue API documentation: https://catalogs.mast.stsci.edu/docs/panstarrs.html
- PS1 system response: Tonry et al. 2012, https://doi.org/10.1088/0004-637X/750/2/99
- Gaia archive programmatic access: https://www.cosmos.esa.int/web/gaia-users/archive/programmatic-access
