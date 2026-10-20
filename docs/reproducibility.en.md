# Reproducing the compact research result

**19 October follow-up:** current CI additionally runs `scripts/verify_research_followup.py`. It verifies all 2,007 additional individual records, observed-band feasibility witnesses, 720 control-model fits and the committed targeted raw evidence. See the [dated follow-up](../research/FOLLOWUP_2026-10-19.en.md) for its exact scope. The 3,041-spectrum bulk retrieval cache is not needed for that check. The original compact result below remains a historical reproducibility target.

> **Scope: the preserved v0.1 compact result.** This guide explains the original four DESI estimates, two Gaia sources and 54 controls. The v0.2 flux-convention correction, current 7,473 eligible records / 308 strong-outlier entity keys, and withdrawal of independent SDSS colour corroboration for J1323−0129 are documented in the [current research report](../research/README.md). Current CI also runs all `test_*.py` unit/invariant tests and `scripts/verify_research_extension.py`; the compact command below is only one part of that verification. Follow the [current root commands](../README.md#reproduce-and-verify) and [research-extension notebook](../research/research_extension.ipynb) for the complete entry point. The historical numerical products described below remain preserved.

The repository contains enough data to verify the four reported DESI colour estimates and the two Gaia sources with both full and truncated basis choices **without downloading any astronomical data**. It also includes the 54 selected raw SDSS control spectra. The continuous-integration job recomputes those controls in addition to the main candidates; a faster default command checks their archived result only and labels that distinction explicitly.

Passing the verification means the committed source files, units, parsed arrays, calibrations, colour calculations and reported Gaia covariance products remain consistent. It does not establish novelty, remove instrumental systematics, resolve neighbouring stars, or confirm a discovery.

## Run the offline check

Use Python 3.12 and the core environment recorded at the repository root:

```bash
python -m venv .venv-colour
.venv-colour/bin/python -m pip install -r requirements-core.txt
.venv-colour/bin/python scripts/verify_reproduction.py
```

To run the same verification as CI, including all 54 raw SDSS controls:

```bash
.venv-colour/bin/python scripts/verify_reproduction.py --with-controls
```

Dependency installation needs access to the package index unless the packages are already cached. The verification step needs no data-network access and rejects socket connections or DNS lookups attempted in its Python process. It does not invoke an acquisition script or contact an observatory archive. It uses a temporary Matplotlib cache and does not rewrite source data or research results.

The command also works outside the checkout:

```bash
/path/to/repository/.venv-colour/bin/python /path/to/repository/scripts/verify_reproduction.py --root /path/to/repository
```

Historical paths containing `wd-colour-research/` are resolved to the current checkout. The verifier refuses to read a data path outside that checkout, so an old research workspace cannot accidentally make a broken relocated copy pass. JSON and CSV input tables may be stored as their original filenames or with an additional `.gz` suffix.

The publication checkout uses compressed large tables, including `mwdd/manifest_enriched.json.gz`, `sdss/manifest_with_photometry.json.gz`, `results/screen_input_sdss.json.gz`, and `results/all_spectra_screen.csv.gz`. References to those tables below use their logical filenames; the verifier automatically reads their `.gz` versions. The four headline DESI CSV/NPZ pairs, four Gaia 1 nm NPZs, original coefficient CSVs and CIE reference remain small directly readable files. The control check prefers `results/sdss_screen.csv` or `.csv.gz` when present and otherwise reads the full screen table.

## What is recomputed

### Four DESI headline estimates

The check requires exactly these source identities from `results/headline_candidates.csv`:

| Candidate | Gaia source ID | Headline system | Reported display colour |
|---|---|---|---|
| J0913+4434 | 818833831355548928 | DESI spectrum, PS1 gri anchors | `#F1FFC9` |
| J0429−0354 | 3204436719718449280 | DESI spectrum, PS1 gri anchors | `#F8FFDC` |
| J1329+0033 | 3711047662972690688 | DESI spectrum, PS1 gri anchors | `#FFC1CF` |
| J1323−0129 | 3638333660492606976 | DESI spectrum, PS1 gri anchors | `#FFE86A` |

For each source, the verifier locates the exact record in `mwdd/manifest_enriched.json`, checks the raw export's SHA-256, reads the original CSV independently, and compares all four columns with the committed NPZ: wavelength, original flux, uncertainty and flag. The comparison preserves negative noisy samples; they must not be clipped to create a different spectrum.

It verifies the PS1 magnitudes and errors against the source manifest, reruns the three-band photometric fit, applies the corresponding inverse-variance correction, and integrates the calibrated spectrum with the reported narrow sky-line masking. The recalculated x, y, CIE 1960 u and v, Duv, green-channel margin, calibration parameters and sRGB hex code are compared with the frozen headline table. This tests the complete committed-input-to-headline calculation rather than a collection of implementation-shaped unit tests.

The official CIE 1931 two-degree table is checked against the SHA-256 in CIE's accompanying metadata. The verifier also checks that the pipeline actually loaded that table rather than silently using a different built-in observer function.

### Four Gaia mean and covariance products

For both J0913 and J0429, the repository includes the 1 nm **full** and **truncated** GaiaXPy reconstructions. The verifier checks the original ESA coefficient CSV hashes and source IDs, and the four NPZ hashes recorded in `essential_validation_files.json`.

For each NPZ it checks:

- The 330–1050 nm grid and its angstrom conversion, expected dimensions, and finite flux/error/covariance values.
- Symmetry and positive semidefiniteness of the supplied full sampled covariance, agreement of its diagonal with the flux-error array, and consistency with the supplied correlation matrix.
- The CIE XYZ mean integrated independently from the native Fλ data in W m⁻² nm⁻¹ over 360–830 nm. Comparing dimensional XYZ values, as well as normalized colour, detects a common unit multiplier that a colour-only comparison would miss.
- The complete projection `C_XYZ = B.T @ C_flux @ B`, including off-diagonal wavelength correlations, and its first-order transformation to CIE u,v covariance.
- Mean x, y, u, v, Duv and sRGB against the frozen Gaia summary.

The probability that G exceeds both R and B is also calculated from the two correlated Gaussian channel differences with deterministic numerical quadrature. This is an independent comparison with the saved 200,000-draw Monte Carlo estimate. It is not based on replaying saved random draws, and it does not assume independent wavelength errors.

This compact check starts from the included GaiaXPy **reconstruction products**. It does not reconstruct those products from coefficient basis functions in CI. The original coefficient files and the separate reconstruction procedure are documented in [the Gaia audit](../mwdd/gaia_validation/README.md). That deeper reconstruction uses its own GaiaXPy-compatible environment; GaiaXPy is not a dependency of this offline verifier.

The unused `gaiaxpy_output_packed_correlation` arrays are preserved for investigation of the documented sampled-correlation discrepancy. The verifier uses `covariance_w2_m4_nm2`, the covariance propagated directly from coefficients, and its matching `correlation` array.

### The 54 SDSS controls

The verifier cross-matches the 54 control spectrum IDs in `sdss/manifest_with_photometry.json` against the committed SDSS result table. It requires 18 DA, 18 DB and 18 DC records, all marked usable, none green-dominant, and all with saved distance from the Planckian locus below 0.01. The largest saved distances are approximately 0.006706, 0.004092 and 0.001981 respectively.

The default command labels this part **`ARCHIVED RESULTS ONLY`**: it checks the saved control result without integrating 54 raw spectra.

With **`--with-controls`**, the verifier additionally locates all 54 exact observations in the frozen SDSS input manifest, checks their raw FITS SHA-256 values, and independently compares the FITS columns with every committed NPZ field. This includes the conversion from SDSS's native 10⁻¹⁷ erg s⁻¹ cm⁻² Å⁻¹ flux units and the corresponding squared-unit conversion for inverse variance. Flux, inverse variance, masks and other source columns remain exact comparisons, including the fixed flux-unit conversions. Only the derived wavelength `10**loglam` permits the two-ULP floating-point allowance explained below. It reruns the normal calibration and colour calculation, checks x, y, u, v, Duv and the display colour against the frozen results, and verifies that these negative controls remain below the stated 0.01 distance threshold without green-channel dominance. Successful recomputation prints **`RECOMPUTED SDSS`** lines.

The CI workflow uses `--with-controls`. Both modes remain offline. Reacquiring the full public sample and running the complete survey screen are separate operations documented at the repository root.

## Numerical tolerances

| Check | Tolerance and reason |
|---|---|
| Raw file hashes, raw CSV–NPZ values and SDSS FITS–NPZ fields other than derived wavelength | Exact identity, including any preserved NaNs in raw columns and the fixed SDSS flux/inverse-variance unit conversions |
| SDSS wavelength derived as float64 `10**loglam` | At most two float64 ULPs, with finite positive float64 values and identical shape required; no general absolute or relative tolerance is used |
| DESI and recomputed SDSS x, y, u, v and Duv; DESI green margin | Absolute difference ≤ 2×10⁻⁸; permits insignificant optimization/platform rounding while detecting meaningful result changes |
| DESI fit parameters | Absolute difference ≤ 2×10⁻⁶ mag or mag per 1000 Å, as appropriate |
| Display hex codes | Exact match under the reported rendering convention |
| Gaia mean chromaticity and Duv | Absolute difference ≤ 2×10⁻¹⁰ |
| Gaia dimensional XYZ | Relative difference ≤ 2×10⁻¹⁰, with zero absolute tolerance |
| Gaia projected covariance | Relative difference ≤ 2×10⁻⁹, with zero absolute tolerance |
| Sampled covariance positive semidefiniteness | Minimum eigenvalue of covariance divided by its largest diagonal variance must exceed −10⁻⁸; allows numerical noise in the rank-deficient matrix |
| Analytic versus archived Monte Carlo green probability | Five binomial standard errors plus 0.0005, since the saved probability has finite-sample noise |

These are reproduction tolerances, not observational error bars. The verifier does not recompute the DESI 6,000-draw uncertainty simulations or every Gaia Monte Carlo percentile. The dedicated analysis scripts perform those longer calculations.

### Why the SDSS wavelength comparison allows two ULPs

SDSS stores `loglam`; the parser derives angstrom wavelengths using `10.0 ** np.asarray(loglam, dtype=np.float64)`. This nonlinear power operation can round differently under different scalar or vector CPU implementations even with the same pinned Python and NumPy versions. A ULP is one step between adjacent representable floating-point values. The verifier counts those steps using the ordered bit patterns of finite positive float64 numbers. Its two-ULP limit allows one rounding step from each implementation; it does not allow a changed unit scale, a lower-precision stored wavelength grid or a broad numerical discrepancy.

The portability audit used Python 3.12.14 and NumPy 2.5.4 on all **236,066 pixels in the 54 controls**. The normal NumPy power implementation exactly reproduced the committed grids. Disabling its AVX-512 dispatch targets caused **13,275 samples** to differ, all by **one ULP**, with maximum absolute difference **1.8189894×10⁻¹² Å** and relative difference **2.21631×10⁻¹⁶**. Python `math.pow` and NumPy `float_power` gave the same mismatch counts; power evaluated with the host's 64-bit-significand extended precision and rounded back to float64 differed at 13,147 samples, also by at most one ULP. In the first affected observation, `5788-56255-0151`, the scalar comparison differed at 261 of 4,626 samples. This reproduces the failure of the previous bitwise comparison without changing any scientific input.

On this x86_64 NumPy build, the reduced-dispatch check was:

```bash
NPY_DISABLE_CPU_FEATURES=X86_V4,AVX512_ICL,AVX512_SPR \
  python scripts/verify_reproduction.py --with-controls
```

Both normal and reduced-dispatch verification passed all four DESI candidates, all four Gaia mean/covariance products and all 54 controls. The verifier now prints the number of differing wavelength samples and arrays, maximum ULP distance, and absolute and relative differences. Over-limit failures identify the spectrum, field, first offending index and both values. All other FITS–NPZ fields retain exact comparison and report their first mismatch; the raw FITS SHA-256 check remains exact.

A separate sensitivity check recalculated the 54 controls with the scalar-power grid and with every stored wavelength shifted two float64 steps in either direction. It kept the source fluxes, inverse variances and selected photometric system fixed, and repeated the photometric fit for the 34 calibrated controls. Across these three comparisons, the largest raw-colour-coordinate difference was **7.22×10⁻¹⁶**. After refitting, the largest difference among x, y, u and v was **7.25×10⁻¹⁰**, and the largest Duv difference was **6.14×10⁻¹¹**; **no display HEX changed**. These measured effects remain below the existing 2×10⁻⁸ result-reproduction tolerance. This is a computational portability check, not an additional observational uncertainty estimate. No frozen spectrum, result, notebook or scientific calculation was changed for this fix.

## Interpreting the uncertainty

The Gaia calculation retains wavelength covariance and therefore does not turn 721 correlated samples into 721 independent measurements. The formal probability that the green channel is largest is materially below certainty for these four products. The verifier checks that the reported covariance and probabilities have not silently become an assertion of certain greenness.

The covariance describes the supplied coefficient-noise model. It excludes calibration systematics, unprovided BP/RP cross-band calibration covariance, neighbour contamination and truncation bias. DESI's reported uncertainty model has different limitations, including unmodelled spectral correlations. Calibrating two spectra to the same photometry introduces shared uncertainty. None of these scientific limitations disappears when the code passes CI.

## Continuous integration

The [reproduction workflow](../.github/workflows/reproduce.yml) runs on pushes, pull requests and manual dispatch. It installs `requirements-core.txt` with Python 3.12 and invokes the verifier with `--with-controls` from the runner's temporary directory to check portability.

The workflow uses the official `actions/checkout@v7` and `actions/setup-python@v7` major versions, verified against their [checkout](https://github.com/actions/checkout) and [setup-python](https://github.com/actions/setup-python) documentation when this workflow was written. It grants only `contents: read`, does not persist checkout credentials, and does not publish artifacts, mutate the repository, or download survey data. Installing Python and dependencies is separate from the offline scientific step.

No additional test framework or unrecorded scientific dependency is required. The verifier directly uses NumPy and SciPy plus the dependencies imported by `colour_pipeline.py`; all are already included in `requirements-core.txt`.

## When a check fails

A hash, identity or path failure means the expected committed data are missing or changed. A raw-to-NPZ discrepancy means the parsed derivative no longer matches the source. A numerical or covariance failure requires scientific review of the changed calculation or input before updating a frozen result. Do not loosen tolerances or replace reference values merely to restore a passing badge.

If an intentional scientific revision changes a result, retain its provenance and explain the reason, the changed assumptions and the effect on the interpretation in the associated change. This repository's validation is evidence of computational reproducibility, not an assessment of publication priority.
