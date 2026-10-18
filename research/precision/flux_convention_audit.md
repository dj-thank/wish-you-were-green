# Native-sample audit of the MWDD SDSS spectral-density convention

## Result

The visual inspection of the strong-outlier spectra revealed a consequential
input-convention problem in the historical colour screen. Among **2,232 MWDD
SDSS raw files**, an independent comparison against directly downloaded SDSS
FITS observations verifies **149 Fν-shaped files** and **504 Fλ-shaped files**.
**1,579 files remain unresolved** under the strict comparison described below.
The full run compares 957 pairs selected by the existing entity assignments;
all required raw files are present and all raw SHA256 checks pass. Of the
unresolved files, 1,286 have no corresponding direct reference in the frozen
inputs and 293 have reference pairs that do not pass the identity criteria.
There are no conflicting accepted Fν/Fλ determinations in this run.

This is a finding about how this project's historical calculation interpreted
the archived spectra. It does not establish that the MWDD service itself is
incorrect: its acquisition metadata explicitly retained an unspecified original
spectral-density convention. The historical pipeline nevertheless admitted
records labelled `SDSS` to a calculation requiring Fλ.

The reproducible artifacts are:

- [Comparison script](flux_convention_audit.py): reads and hashes the raw files,
  parses CSV and FITS independently, and builds the registry.
- [JSON evidence](flux_convention_evidence.json): one registry record per MWDD
  raw SHA, every assessed pair, native FITS headers, thresholds, URLs, source
  hashes, and unresolved-file information.
- [CSV registry](flux_convention_evidence.csv): the same 2,232 file determinations
  with the best accepted reference where one exists.
- [Two original-observation fixtures](flux_units/fixtures/manifest.json): one
  Fν pair and one Fλ pair, preserving both sets of native wavelength and flux
  arrays for offline regression tests.
- [All 176 individual image observations](../outlier_audit/visual_review_01_11.md):
  the visual review that motivated this comparison.

## Physical distinction and reference authority

Colour integration against wavelength-defined CIE colour-matching functions
requires energy flux density per wavelength. The change of variables is

\[
F_\lambda(\lambda)=F_\nu(\lambda)\frac{c}{\lambda^2},\qquad
c=2.99792458\times10^{18}\ \mathrm{\mathring A\,s^{-1}}.
\]

A constant original amplitude cancels in chromaticity. The wavelength-squared
factor does not. A two-parameter photometric adjustment cannot be used as
evidence that the input convention was correct: it can partially absorb a
wrong smooth shape and still leave a biased spectrum between passbands.

The [official SDSS documentation](https://www.sdss4.org/dr17/spectro/spectro_basics/)
defines the spectral flux unit as 10⁻¹⁷ erg cm⁻² s⁻¹ Å⁻¹. Every one of the 957
FITS references examined here has the primary-header value
`BUNIT = 1E-17 erg/cm^2/s/Ang`. The independent reader multiplies the native
`flux` column by 10⁻¹⁷. The raw FITS headers and plate–MJD–fibre identifiers are
preserved in the pair evidence. No guessed flux amplitude or filename pattern
is used to decide the convention of a MWDD export.

## Identity test

The alternatives are restricted to a positive constant scale under Fλ or a
positive constant scale after the exact `c / wavelength**2` transformation.
There is no free fitted spectral tilt or flexible continuum model. The
logarithmic slope of the raw flux ratio is recorded only as a diagnostic.

For each possible MWDD/direct SDSS pair in the same existing entity:

1. Read the original CSV and FITS bytes and require their frozen SHA256 values.
2. Match native wavelength samples in the shared 3600–8300 Å interval, with a
   maximum separation of 0.02 Å. Require at least 99% wavelength-grid matching
   and at least 99% finite values among those matches.
3. Require at least 1,000 comparison samples spanning at least 3,500 Å. Divide
   by reference flux only where its absolute value exceeds 0.1 times its median
   absolute value, so near-zero divisions cannot control the relative statistic.
4. For each convention, divide the transformed source/reference ratio by its
   positive median. Require the **maximum** fractional residual to be below
   10⁻⁴, not just the median or a fitted slope.
5. Separately check **all finite matched samples**, including negative and
   near-zero flux: the maximum absolute difference after constant rescaling,
   divided by the median absolute reference flux, must also be below 10⁻⁴.
6. Accept exactly one convention. If both pass, neither passes, or different
   accepted references support conflicting conventions, retain `unresolved`.

The actual accepted matches are appreciably better than these gates: every one
matches 100% of the available visible wavelength grid and has more than 3,200
comparison samples spanning more than 4,465 Å. The maximum fractional residual
over all accepted Fν files is **7.1135 × 10⁻⁶**; for accepted Fλ files it is
**5.0648 × 10⁻⁶**. The corresponding maxima of the all-finite-sample absolute
residual statistic are 1.8305 × 10⁻⁵ and 2.7064 × 10⁻⁵. These tiny residuals
include the spectral features and sampled noise, providing much stronger
evidence of a shared observation than continuum similarity.

## Concrete examples

Indices below are zero-based rows in the original 9,902-record input.

| MWDD object | MWDD row | Direct SDSS row | Determination | Maximum fractional residual after the accepted transformation |
|---|---:|---:|---|---:|
| SDSS J083231.57−040807.8 | 2583 | 9184 | Fν shape | 4.44 × 10⁻¹⁶ |
| SDSS J180302.57+232043.3 | 36 | 9538 | Fν shape | 4.44 × 10⁻¹⁶ |
| WD 2229−080 | 1569 | 9199 | Fν shape, additional constant amplitude | 4.74 × 10⁻⁶ |
| WD 0848+159 | 3 | 8664 | Fλ shape | 4.96 × 10⁻⁶ |

For J083231 and J180302, interpreting the original MWDD values directly as Fλ
produces a different continuum slope from the direct observation. Multiplying
by `c / wavelength**2` removes that discrepancy down to floating-point
precision after a constant scale. WD 2229−080 has the same wavelength-squared
relation with an additional constant factor of approximately 2.997924; its
absolute original scale is not inferred here.

The original 27-object follow-up set contains three MWDD SDSS records. None is
among the 149 verified Fν files. PSO J186.4406+47.1036 (row 1612) is verified Fλ
against direct row 9539. J1323−0129 (Gaia 3638333660492606976, row 13) and Gaia
1245262790370992256 (row 8267) remain unresolved because the frozen inputs have
no direct reference for those MWDD SDSS observations. Their DESI estimates are
unaffected by this SDSS determination; the unresolved SDSS colour cannot yet
serve as verified second-instrument corroboration. See the
[candidate impact inventory](flux_units/candidate27_sdss_convention_impact.json).

## Interpretation and implementation boundaries

The registry validates a relative spectral-density shape, not an absolute
luminosity scale, astrophysical identity, extraction quality, sky subtraction,
or statistical independence. Two archived files that pass the native-sample
identity test should not be counted as independent observations merely because
their file hashes differ. An unresolved record is not automatically Fν and must
not be converted from its amplitude or spectral class alone.

The current pipeline resolves the convention before colour integration and
photometric recalibration. Where an inverse variance is supplied, a flux
conversion by a wavelength-dependent factor `a` requires `ivar / a**2`. This
preserves each sample's signed signal-to-noise ratio. The compact fixture tests
verify that invariant, agreement with an independently downloaded SDSS colour,
unchanged Fλ inputs, rejection of unknown raw SHAs, and rejection of stale or
already-converted arrays that retain the original numeric checksum. Historical
reproduction is explicitly marked and cannot enter current selection without
its separate historical opt-in.

Run the evidence audit with:

```bash
python research/precision/flux_convention_audit.py
```

The full comparison requires the SHA-matched raw inputs. The compact regression
tests run offline from committed fixtures:

```bash
python -m unittest discover -s tests -p 'test_flux_conventions.py' -v
```

The [corrected screen summary](flux_units/corrected_screen_summary.json) and its
record table separately retain historical values and current determinations.
Neither the original frozen results nor original spectra are overwritten by
this audit.
