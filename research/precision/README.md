# Precision and spectral-support audit

**Audit date:** 18 October 2026 UTC. Original frozen screen: commit
`73287c8ed16d66230381b1e0b9a6d9f75dea086b`.

The principal candidates are insensitive to the spacing of the original
Planckian temperature grid, while tiny near-locus signed offsets can change
side when that grid is replaced with a continuous projection. Masked or
missing spectral support is a more material sensitivity. These results refine
what the existing calculation means; they do not establish a new object,
physical mechanism, or observational detection.

The earlier frozen tables and headline values remain unchanged. Updated
geometry is named separately and keyed to the original spectrum row.

## Reproduce and inspect

From the repository root, in the recorded core Python environment:

```bash
python research/precision/precision_audit.py
python -m unittest discover -s tests -p test_scientific_invariants.py -v
python scripts/verify_reproduction.py --with-controls
```

The first command reads the included inputs and writes only this audit's CSV
and JSON products. It requires no archive access. An alternate output location
is supported with `--output /path/to/audit-output`.

| File | Meaning |
|---|---|
| [precision_audit.py](precision_audit.py) | Reusable continuous geometry, exact integration under a stated interpolation model, rejected-support calculations, and the executable audit |
| [planckian_projection_audit.csv](planckian_projection_audit.csv) | All 9,868 successful records with finite u,v; preserves `row_index`, the zero-based row in the frozen 9,902-record table |
| [headline_mask_gap_audit.csv](headline_mask_gap_audit.csv) | Four DESI+PS1 candidates, with nominal, no-sky-mask and four explicitly synthetic missing-window variants |
| [precision_summary.json](precision_summary.json) | Input and script hashes, package versions, method parameters and summary measurements |
| [photometric_nullspace.py](photometric_nullspace.py) | Separate adversarial test of spectral shapes that conserve the baseline's three synthetic PS1 fluxes |
| [photometric_nullspace.json](photometric_nullspace.json) | That experiment's constraints, numerical bounds and interpretation limits |
| [test_scientific_invariants.py](../../tests/test_scientific_invariants.py) | Five independent physical/numerical checks complementing the raw-data reproduction verifier |

Thirty-four failed or non-finite records cannot be projected. They remain in
the original screen and its wider audit; omission from this geometry table is
not a quality endorsement. Records with unverified original flux conventions
also remain explicitly distinguishable through their archive/type and
`usable_screen` fields. Geometry alone does not make those spectra usable.

## 1. Continuous Planckian geometry

The frozen pipeline finds the nearest member of 8,000 logarithmically spaced
blackbody temperatures plus an explicit Rayleigh–Jeans endpoint. Its signed
Duv uses the vertical residual from that nearest *grid point*. Near the locus,
the tangential error caused by finite grid spacing can exceed the genuine
perpendicular displacement.

The audit uses the same committed [CIE 1931 two-degree reference
table](https://doi.org/10.25039/CIE.DS.xvudnb9b), spanning 360–830 nm at 1 nm.
It evaluates Planck spectra continuously using SI constants from SciPy and
minimizes the squared CIE 1960 u,v distance. The compact inverse-temperature
coordinate is

\[
q=\frac{1000\,\mathrm{K}}{T},\qquad 0\le q\le1.
\]

Up to a wavelength-independent factor, the spectrum can be written

\[
F_\lambda(q)\propto\lambda^{-4}
\frac{z}{\operatorname{expm1}(z)},\qquad
z=\frac{hc}{\lambda kT}.
\]

This is ordinary energy-per-wavelength Planck radiation. The ratio tends to
one at q=0, so the Rayleigh–Jeans endpoint is represented exactly without
substituting an arbitrarily high finite temperature. The original dense grid
only brackets the local section for the scalar minimizer. It does not supply
the corrected distance or signed side. Both bracket endpoints are tested.

At an interior minimum, the sign is determined by the local normal with
positive v component. At the 1,000 K or Rayleigh–Jeans endpoint, the audit
reports the nonnegative distance and an explicit endpoint class; signed
perpendicular Duv is left blank. There is no finite correlated temperature
for a Rayleigh–Jeans projection. Values of q at or below 10⁻¹² are treated as
that numerical endpoint; this corresponds to T at or above 10¹⁵ K and is not
an estimate of a physical stellar temperature.

### Measured effect on the entire frozen screen

| Quantity | Result |
|---|---:|
| Records evaluated | 9,868 |
| Largest absolute distance change | 3.78023×10⁻⁵ |
| Median original-grid distance excess | 6.00211×10⁻⁸ |
| Interior signed-side changes | 48, including 47 eligible records |
| Largest original absolute Duv among those side changes | 5.96676×10⁻⁵ |
| Rayleigh–Jeans endpoint projections | 178 overall; 12 eligible |
| Low-temperature endpoint projections | 5 overall; none eligible |
| Crossings of distance 0.001, 0.003, 0.005, 0.006 or 0.01 | 0 at each threshold |

These are record counts, not deduplicated star counts. The main colour
candidates are far from the numerical ambiguity: the largest distance change
among their four representative DESI+PS1 estimates is 7.02×10⁻⁸. The largest
change occurs for J0429−0354. More temperature samples would not resolve its
observational uncertainty.

A tiny plotted offset of order 10⁻⁵ therefore needs continuous geometry
before its sign is interpreted. This issue does not explain offsets near
0.006 or 0.01 and does not turn a screening threshold into a significance
level. The corrected projection temperature is a *colour-locus coordinate*,
not a newly fitted atmospheric effective temperature.

## 2. Spectral masks and what “coverage” means

The legacy `cmf_min_coverage` integrates the CMF samples after rejected pixels
have been removed. Trapezoidal integration bridges each remaining gap. It
therefore describes a quadrature/interpolation span, and is not the fraction
of the observer-weighted spectral support actually measured. The ratio can
even exceed one because of quadrature across a curved CMF.

For the four representative DESI spectra, the legacy ratio is approximately
one. Their invalid-uncertainty and narrow sky masks nevertheless reject
native sample cells containing approximately **4.3–4.5% of the integrated X
CMF weight and 3.5–3.6% of the Y CMF weight**. This does not mean that these
percentages of the stellar light are unknown: a CMF-weight fraction is not a
flux fraction, and neighbouring measurements constrain a smooth continuum.
It does make the interpolation assumption explicit.

The new diagnostic assigns each original sample a cell bounded by the
midpoints to its neighbours, integrates the piecewise-linear CMFs over the
rejected cells, and divides by the full reference CMF integral. It preserves
both measures separately:

- `legacy_cmf_min_coverage`: the original span/quadrature diagnostic;
- `rejected_native_support_X/Y/Z_cmf_fraction`: how much CMF-weighted native
  support the explicit rejection mask removed;
- `largest_visible_gap_A`: the largest interval bridged by the retained
  samples.

The support fractions alone cannot recover missing flux, and they should
not be inserted into an error budget as percentages of XYZ.

### Removing the existing narrow sky mask

This recomputation holds the calibrated flux and its supplied valid-error
selection fixed, then changes only the sky mask. It is a processing
sensitivity check; an unmasked sky residual is not automatically a better
stellar measurement.

| Candidate | No-sky-mask minus nominal Duv | CIE u,v displacement |
|---|---:|---:|
| J0913+4434 | +0.00060588 | 0.00062688 |
| J0429−0354 | −0.00019035 | 0.00021983 |
| J1329+0033 | +0.00023252 | 0.00047750 |
| J1323−0129 | +0.00035324 | 0.00046518 |

The direction and broad candidate interpretation persist, but this effect is
larger than the Planck-grid correction. The sodium-region sky windows overlap
wavelengths that can contain real stellar absorption; masking them is a
choice whose sensitivity should remain visible in candidate validation.

### A synthetic missing-window stress test

The audit also removes **available** samples within ±70 Å of 5,100, 5,577.34,
5,890 and 6,300.30 Å. These synthetic gaps are not present observations or an
estimate of real missing data. They test whether the broad eligibility rules
alone guarantee colour stability.

For example, removing the 140 Å window centred at 5,100 Å from J0913+4434
changes Duv by **−0.005735** and produces `#FFFFCF`, with green-channel
dominance lost. Yet the legacy CMF ratio is **1.000654**, and the largest
remaining gap is **140.8 Å**: both pass the old span/gap thresholds. The
rejected Y-CMF support rises to about **10.19%**, compared with 3.56% in the
nominal mask. This demonstrates a limitation of those thresholds. It does
not show that J0913 really has this missing window or negate its actual
calibrated spectrum.

Interpolation over a broad gap can give its noisy endpoint samples large
integration weights. A more informative quality assessment records the
removed support and explores physically or instrumentally justified bounds
on the missing spectral shape. A favourable `coverage` number alone is
insufficient.

## 3. Integration under an explicit interpolation model

The original calculation trapezoidally integrates the product of sampled
flux and interpolated CMFs on the retained native wavelength grid. A separate
calculation now integrates the product **exactly under piecewise-linear
interpolation of both functions**. It uses the union of spectral and CMF
knots. The product is quadratic on each resulting interval, so a midpoint
Simpson formula is exact there up to floating-point arithmetic. It retains
the same visible endpoints and masks.

The largest CIE u,v displacement among the four candidates is approximately
**2.93×10⁻⁵**, for J1329+0033. J0913 changes by about 1.52×10⁻⁵; the other
two change by about 4×10⁻⁶. These are smaller than the masked-sky sensitivities
above. The exact-interpolation calculation can change a display channel by
one 8-bit level at a rounding boundary; that is not an independently
meaningful colour discovery.

This calculation improves quadrature under a particular interpolation
assumption. It does not reconstruct unresolved absorption or missing data.
Point-sampling a noisy DESI spectrum at 1 nm is also not a valid independent
convergence test: downsampling must conserve the spectral integral and carry
the resulting covariance. Otherwise the test adds sampling noise and
aliasing instead of isolating numerical integration error.

## 4. What the independent checks establish

The five added tests cover physical or numerical identities with independent
constructions:

1. A 3,631 Jy flat Fν source, explicitly converted to Fλ, has zero AB
   magnitude to within the expected 1 Å integration residual in SDSS and
   Pan-STARRS g,r,i. The photon-weighted Fλ convention is documented by
   [speclite](https://speclite.readthedocs.io/en/latest/api/speclite.filters.FilterResponse.html).
2. Planck radiance from the physical constants reproduces the pipeline's
   thermal chromaticities; continuous projection returns true thermal
   spectra to the locus between the frozen grid temperatures.
3. Tiny offsets along the continuous local normal have the correct signed
   side, and both finite-domain endpoints are explicitly labelled.
4. Finite differences in the original pixel fluxes reproduce the analytic
   first-order u,v uncertainties. Changing flux units by factors of 10⁻¹⁷
   or 10¹⁷ with the matching variance conversion preserves colour and error.
5. General adaptive quadrature agrees with the joint-knot integral, and
   rejected-support fractions satisfy zero, complete and complementary-mask
   identities.

All five passed in the recorded Python environment. They complement the
existing raw-file hashes, exact parsed-column comparisons and full-covariance
Gaia checks. They do not test whether a star is new, whether its relative
spectral calibration is accurate, or whether its atmosphere has a novel
composition.

## Scientific consequence

The subsequent actual inspection of 176 outlier contact-sheet panels exposed
a more consequential issue than the small quadrature corrections: mixed Fν
and Fλ conventions among MWDD SDSS exports. The independent
[native-sample convention audit](flux_convention_audit.md) verifies 149 Fν
files and 504 Fλ files against direct SDSS observations, with 1,579 still
unresolved. Its [raw-SHA registry](flux_convention_evidence.json) now controls
admission to the [corrected screen](flux_units/corrected_screen_summary.json).
The original results remain historical snapshots. In particular, J1323−0129's
MWDD SDSS record lacks a decisive reference and its second-instrument colour
corroboration is held pending unit verification; its DESI estimate is retained.

The [real-observation regression tests](../../tests/test_flux_conventions.py)
complement the five physical invariants above. They verify recovery of a
directly measured SDSS colour after Fν conversion, unchanged Fλ inputs, signed
signal-to-noise preservation, and the separation between explicit historical
reproduction and current unit-verified candidate selection.

Further effort should concentrate on relative spectral calibration,
independent observing epochs, aperture contamination, the provenance of
broad absorption, and the relationship between physical atmosphere models
and these chromaticities. The separate [photometric null-space
experiment](photometric_nullspace.json) addresses why matching three
broadband anchors can leave smooth shape changes unconstrained. Its
adversarial perturbations are conditional mathematical constructions, not
measured DESI errors or probabilities that a candidate is genuine.

The original [research-integrity note](../../docs/research-integrity.md) and
[reproduction guide](../../docs/reproducibility.en.md) remain applicable.
