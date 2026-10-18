# October 2026 reproducibility and scientific-precision audit

The current original `main` commit,
`73287c8ed16d66230381b1e0b9a6d9f75dea086b`, already passed its offline
reproduction workflow. The additional work below checks scientific
assumptions and numerical precision while preserving that original result.

## The earlier CI failure is resolved

GitHub [run 39091243375](https://github.com/dj-thank/wish-you-were-green/actions/runs/39091243375)
failed when an exact comparison of SDSS's derived `10**loglam` wavelength
array encountered platform floating-point rounding for observation
`5788-56255-0151`. It did not demonstrate a changed source spectrum or a
colour discrepancy.

The subsequent [run 39092008847](https://github.com/dj-thank/wish-you-were-green/actions/runs/39092008847),
completed at 03:00 UTC on 18 October 2026, passed the four DESI candidate
estimates, four Gaia mean/full-covariance products and all 54 raw SDSS
controls. Its log reported 13,275 wavelength samples with at most one
float64 ULP of difference; all other FITS-to-NPZ columns remained exact.
The main commit already contains the narrow, two-ULP allowance and its
measured portability justification. No further relaxation was needed.

The same `--with-controls` command was rerun outside the checkout in the
current Python 3.12.14 environment and passed. The core packages matched
`requirements-core.txt`; this host reproduced all stored SDSS wavelengths
exactly. This is an additional execution check, not external peer review.

## New substantive checks

The complete methods, measurements and machine-readable outputs are in the
[precision audit](../research/precision/README.md). The main findings are:

- **Continuous Planckian geometry:** 9,868 successful, finite records from
  the historical screen were projected continuously from 1,000 K to the Rayleigh–Jeans
  limit. Forty-eight very small offsets changed signed side; their original
  absolute Duv values were below 0.000060. No records crossed distances
  0.001, 0.003, 0.005, 0.006 or 0.01. The four principal estimates changed
  in distance by at most about 0.0000000702.
- **Wavelength support:** the old CMF `coverage` statistic bridges gaps and
  does not measure the support discarded by the mask. New native-cell
  support fractions retain that distinction. A synthetic 140 Å missing
  window can materially change the result while still passing the old
  span/gap thresholds; it is clearly labelled as a stress experiment.
- **Mask sensitivity:** removing only the narrow sky mask changes Duv by
  approximately 0.00019–0.00061 in magnitude for the four candidates. These
  processing effects are substantially larger than the Planck-grid error.
- **Quadrature:** an independent exact integral under piecewise-linear
  interpolation changes CIE u,v by at most approximately 0.0000293 across
  the four candidates. It refines numerical precision but does not supply
  missing physical information.
- **Five physical/numerical invariants:** AB flux-density conventions,
  Planck radiation, continuous signed geometry, finite-difference error
  propagation, unit-scale invariance, quadrature and masked-support
  identities all passed. The final CI workflow runs these five tests and
  ten flux-convention, eligibility and alias-regression tests after the
  original raw-input reproduction.

The final local test run passed all **15 tests**. The complementary
`verify_research_extension.py` run outside a clean Git export passed **seven
groups and 250 hashed input files**: the corrected screen and unit registry,
native Gaia covariance, PS1 and held-out z, constrained spectral witnesses,
the 337 individual visual-review entries and their 22 image snapshots,
individual DESI exposures, and the retained ZTF epochs and offset event.
See the machine-readable [extension verification](../research/verification.json).
This does not reclassify historical unknown-unit colours as current measurements.

The first extension CI run exposed a dependency on 19 original spectra that
were present only in the ignored local download cache. The fix preserves
those exact bytes in committed gzip snapshots and checks both the compressed
file hashes and the decompressed original hashes. Historical input paths and
analysis manifests remain unchanged. The clean export contains no copies of
those 19 historical cache paths; both reproduction scripts and all 15 tests
passed there. The report separately records the 19 verified original hashes.
See the [snapshot provenance mapping](../research/precision/candidate_recalibration/raw_sources/manifest.json).

The new projection table keeps the original zero-based `row_index`, source
identifier and archive information, allowing every corrected geometry value
to be joined to the complete frozen record census. Endpoints carry an
explicit class and no signed perpendicular Duv. Unusable spectra remain
unusable regardless of their corrected coordinates.

## Implications for figures and scientific claims

**The later individual spectrum-image review uncovered a substantive unit
problem despite successful historical reproduction.** Native-sample
comparison now confirms mixed Fν/Fλ conventions in the MWDD SDSS exports:
149 Fν-shaped files and 504 Fλ-shaped files have decisive direct-SDSS
references; 1,579 remain unresolved. The historical integration assumed Fλ
for all SDSS-labelled records. Thus, reproducing its archived numbers was
not sufficient to validate their physical interpretation. See the
[independent unit audit](../research/precision/flux_convention_audit.md),
[176-panel visual log](../research/outlier_audit/visual_review_01_11.md), and
[corrected screen summary](../research/precision/flux_units/corrected_screen_summary.json).
Original spectra and historical values are retained; current selection
requires verified conventions and applies the appropriate flux and
inverse-variance transformation before integration. The previous SDSS
corroboration of J1323−0129 is withheld pending a decisive unit reference.

The original population-figure selector used one calibrated record per
catalogue identifier after a lexical archive-type sort. It was not a complete
all-spectrum view or an explicit best-quality selection. Its fixed axes and
unequal visual axis scales could obscure or distort interpretation of
small offsets. A complete anomaly review should show the full recorded
selection, identify duplicates/aliases, retain quality flags and use equal
u,v aspect where Euclidean distance or covariance geometry is displayed.

Numerical stability is now measured more precisely. The largest remaining
scientific uncertainties still concern relative flux calibration, formal
noise versus instrumental covariance, selection after a broad search,
missing spectral structure and contaminating sources. Three-band agreement
is an important constraint but does not uniquely determine the visible
spectral shape. The adjacent [photometric null-space
experiment](../research/precision/photometric_nullspace.json) makes this
last point quantitatively testable under its stated spline family.

These checks do not establish worldwide priority or a new atmospheric
mechanism. They improve the reliability and inspectability of the proposed
colour measurements and identify where further observations and physical
modelling can add information.
