# What additional photometry can identify

**20 October 2026 UTC · exploratory, unreviewed analysis.** [日本語](README.ja.md) · [Fixed prospective design](DESIGN.md) · [Measured-data design](MEASURED_DESIGN.md)

Two completed experiments answer different questions. The first uses **actual SkyMapper DR4 and J-PLUS DR4 photometry** for the frozen candidate set. The second asks whether possible future measurements through real filters could distinguish every permitted pair of opposite channel orderings. Catalogue measurements, constructed spectra and future observations remain separate throughout.

The main result is conditional: **more bands alone do not resolve J0429−0354's colour ordering if the allowed calibration shape remains sufficiently flexible.** In the 400 Å spline / 5% shape experiment, an explicitly constructed strict green/red pair has numerically coincident predictions in all 14 proposed PS1 plus covered J-PLUS bands. Actual SkyMapper r/i measurements add useful constraints, but the primary target's answer still changes when the shape family or measurement bounds change. This is an object-specific identifiability result, not proof that two such physical stellar atmospheres exist.

## 1. Actual additional measurements

The [catalogue investigation](../independent_photometry/README.md) queried all 25 frozen targets, retaining all **450 target/band slots**. It verified 52 strict-quality measurements for 14 targets. Requiring the observed spectrum to cover each full natural passband leaves **46 usable extra measurements for the same 14 targets**. All rejected/missing slots remain in [measured_predictions.csv](measured_predictions.csv), alongside the pre-fit synthetic predictions.

SkyMapper provides independently observed PSF photometry; J-PLUS provides aperture-corrected dual-mode photometry. Their zero points share Gaia-based calibration, and J-PLUS additionally uses a white-dwarf locus and PS1 r anchor. Therefore these additional photon observations do not constitute fully independent calibration evidence. J-PLUS's already applied zero-point offset is not added twice; the recommended zero-point error is included in its reported analysis error. The error boxes below have no assigned joint confidence probability.

For every covered band, the frozen signed DESI + PS1 gri spectrum is integrated through the actual total-system photon response before consuming the added measurement in a fit. Same-letter filters from different surveys are never treated as identical. Predictions use no new extinction correction, extrapolation or clipping of negative valid spectral samples.

### J0429−0354: measurements and fitted constraints

Gaia DR3 `3204436719718449280` matches SkyMapper source `24884480` with an epoch-propagated separation of 0.087 arcsec. Strict SkyMapper **r = 18.8450 ± 0.0181** and **i = 18.7919 ± 0.0197 AB mag** are added. Its g mean passes a looser official-good policy but has four masked pixels in an included exposure, so it is used only in the labelled sensitivity case. Its quality-accepted z measurement extends beyond the spectrum and is not integrated. There is no acquired J-PLUS measurement for this target.

Each solution minimizes the largest continuous multiplicative shape change needed to fit the original PS1 griz boxes and, where stated, the extra photometry. The strict green and strict R>G cases also impose a normalized channel-order guard of 0.005. This is a chosen numerical separation, not a human perceptual threshold.

| J0429, 800 Å spline knots | Fit data; colour unrestricted | Strict green | Strict R > G |
|---|---:|---:|---:|
| Original PS1 griz boxes | 4.2492% | 4.2492% | 4.2492% |
| PS1 + strict SkyMapper r/i | 4.9175% | 5.0103% | 4.9236% |
| PS1 + strict r/i, with 0.02 mag added to each extra box half-width | 4.2492% | 4.2492% | 4.2492% |

The strict green minimum lies just above a chosen 5% budget in the middle row. This is not robust colour identification: a modest stated change in the additional measurement bounds removes the distinction, and 400/1600 Å models give different answers. The 5% budget and extra 0.02 mag are sensitivity assumptions, not measured systematic-error quantiles. Admitting the official-good g measurement does not materially change these near-boundary primary minima.

![Actual SkyMapper constraints and model sensitivity for J0429](j0429_actual_added_measurements.png)

### Every measured candidate was retained and inspected

[All five photometry sheets](visual_review.json) contain the full 25-target set, including unavailable targets. [individual_photometry_review.csv](individual_photometry_review.csv) records actual panel-by-panel observations. Filled points pass both strict quality and full coverage; open points remain excluded. Large residuals do not trigger quality cuts.

Some measured combinations are difficult to fit within the selected smooth family. At 800 Å, the minimum for J0716 is 67.09%; J0006 has no bounded solution within the 95% optimization cap. These are incompatibilities of the declared central spectrum, measurement boxes and shape family. **They are not measured 67% or 95% instrument errors**, and do not establish variability, new opacity or incorrect catalogue measurements. J0006 is already in the published J-PLUS metal-outlier group. Its blue narrow-band noise and aperture dependence require particular care. J1031's pre-fit SkyMapper i residual of about +0.163 mag is an actionable discrepancy, but shared systematics and cross-epoch observations prevent a total-error significance claim.

The experiment covers **165 scenarios and 660 colour-branch optimization problems**. Direct integration verifies 595 feasible witnesses; 65 bounded infeasibilities remain explicit. Combining a measurement with the spectrum consumes it: the resulting fitted band's residual is no longer independent validation. The original pre-fit prediction is retained separately.

## 2. Prospective filters: distance between whole colour sets

Let the frozen numerical spectrum be f₀(λ), and let

\[
f(\lambda)=f_0(\lambda)[1+s(\lambda)],\qquad
\sup_\lambda |s(\lambda)|\leq\epsilon.
\]

Here s is a continuous cubic spline with 400, 800 or 1600 Å knot spacing. The multiplier is positive for the tested 5%/10% budgets; signed native noise samples remain signed. Both spectra must fit the same measured PS1 griz boxes and have positive integrated XYZ. No physical atmosphere model is imposed.

Using the same fixed baseline scale S₀ = max|linear RGB(f₀)| and guard h = 0.005, the green set has both (G−R)/S₀ ≥ h and (G−B)/S₀ ≥ h. The strict opposite set is the union (R−G)/S₀ ≥ h or (B−G)/S₀ ≥ h. The intervening channel-order strip remains undecided.

For proposed photon-flux functionals Lⱼ, minimize the largest difference between **independently varying** spectra fG and fO in those sets:

\[
d=\min_{f_G,f_O}\max_j\frac{|L_j(f_G)-L_j(f_O)|}{L_j(f_0)}.
\]

Both opposite branches are solved and their union handled explicitly. The calculations do not merely test whether new filters distinguish the two witnesses saved in the preceding research round.

- **Numerically d = 0:** at least one strict opposite-colour pair shares the proposed flux vector. It does not imply that every possible future measurement is ambiguous.
- **A positive dual lower bound:** equal hard error-box half-widths smaller than half that lower bound cannot intersect both strict sets, conditional on this spectral space and fixed responses. The conservative reported threshold uses the lower bound, not the feasible-witness upper bound.
- **No opposite pair:** the starting bounded spectral sets already lack an opposite pair. This cannot be credited to a proposed observation.

These statements concern strict channel ordering under declared assumptions. They are neither probabilities nor a universal required observing precision. General metamerism and filter-selection theory are prior work; the present contribution is the explicit conditional calculation for these spectra.

### Selected prospective results

All numbers below are d as a fraction of the same baseline flux in each proposed band. Zero denotes numerical coincidence within the verified tolerances.

| Target / spacing / budget | Repeat PS1 griz | SkyMapper gri | J-PLUS 7 covered narrow bands | All 10 covered J-PLUS bands | PS1 + J-PLUS, 14 bands |
|---|---:|---:|---:|---:|---:|
| J0429 / 400 Å / 5% | 0 | 0 | 0 | 0 | 0 |
| J0429 / 800 Å / 5% | 0 | 0 | 0.0000360 | 0.0025928 | 0.0030284 |
| J0429 / 800 Å / 10% | 0 | 0 | 0.0000265 | 0.0011399 | 0.0028042 |
| J0913 / 400 Å / 10% | 0 | 0 | 0 | 0 | 0 |
| J0913 / 800 Å / 10% | 0 | 0 | 0.0000245 | 0.0001929 | 0.0025357 |

For J0429 / 800 Å / 5% with ten J-PLUS bands, the numerical dual lower-bound half-width is **0.0012964147 of baseline band flux**, about **0.1296%**. Its usefulness depends strongly on the assumed shape family; at 400 Å a numerically indistinguishable pair remains. No such J-PLUS observation of J0429 was acquired in this work. Ideal directly measured XYZ integrals are included only as a mathematical positive control, not an instrument or catalogue.

![Minimum separation for all selected real-filter sets and sensitivity cases](filter_set_separation.png)

![An explicit 14-band indistinguishable pair at 400 Å and a 5% multiplier bound](indistinguishable_fourteen_band_witnesses.png)

The saved pair has different strict green/red ordering with all 14 flux differences numerically zero. The plotted curves are constructed numerical witnesses on one observed noisy baseline. They are not two observed states, stellar atmosphere fits, or evidence of stellar variability.

## 3. Passband coverage and numerical conventions

[profile_manifest.json](profile_manifest.json) pins all 18 original SVO total-system responses, source URLs, retrieval times and SHA-256. The seven covered J-PLUS narrow bands are J0378, J0395, J0410, J0430, J0515, J0660 and J0861; the three covered broad bands are gSDSS/rSDSS/iSDSS. SkyMapper u/v/z and J-PLUS uJAVA/zSDSS fail full observed coverage and are not used for these constraints.

The J-PLUS response tables end at small nonzero throughput. All tabulated samples are preserved and zero is appended 1 Å outside each end. An explicitly repeated 10 Å closure sensitivity changes the primary distances by at most **6.61×10⁻⁸** and does not change feasibility. This tests table closure only; it does not estimate physical response uncertainty.

![Actual response functions and the observed DESI wavelength interval](passband_coverage.png)

## 4. Numerical verification and what it cannot establish

The prospective grid includes **276 scenarios** plus **8 closure sensitivities**, or **568 colour-branch optimization problems**. Internal extrema cuts and numerical retries require 1,455 solver calls. All 338 spectra from 169 feasible pairs are re-integrated; 399 infeasible branches are replayed. Analytic spline-derivative roots check the continuous bounds, and direct filter/CIE integration checks stored predictions.

Both finite-constraint dual lower bounds and continuous feasible-witness upper bounds are retained. An optional coefficient-bounded inner solution may supply a witness, but failure in that smaller space never certifies infeasibility of the full space. Numerical solver retries change algorithm/presolve configuration, not scientific constraints. These are floating-point checks, not formal interval-arithmetic proofs.

The two verifiers perform 2,121 additional nested-set checks in total. Maximum recorded continuous bound overshoot is below 2×10⁻⁹. A [separate reconstruction](independent_review/README.md) rebuilds six selected cases from fresh integrals without reusing the production constraint-builder, and checks the corrected lower-bound reporting.

```bash
python research/measurement_design/verify_outputs.py --write-report
python research/measurement_design/verify_measured.py --write-report
python research/measurement_design/plot_results.py
python scripts/verify_research_oct20.py
```

[verification.json](verification.json) and [measured_verification.json](measured_verification.json) give hashes and residuals. The CI wrapper forbids network access. Numerical replay verifies the stored experiment; it cannot repeat visual inspection or establish an astrophysical discovery.

## 5. Scientific implication and next decisive test

The work strengthens a specific research question: **which colour claims survive calibration freedoms justified by actual observations?** [Repeated observations](../repeat_shape_validation/README.md) demonstrate real shape differences, but three complete DESI pairs and one selected SDSS pair cannot determine a population calibration distribution, particularly for J0429/J0913 with only one available exposure each.

The next decisive experiment is to estimate wavelength-dependent calibration and covariance from comparable standards and repeat spectra, freeze that model before testing the candidates, and then evaluate the whole permitted colour sets against new observations. A physical atmosphere fit should independently predict unused bands or repeated line profiles, with shared calibration parameters and source-class alternatives. Tightening a spline or error box because it produces a desired colour would not supply that evidence.

### Primary sources and credits

- SkyMapper data and quality definitions: [DR4](https://skymapper.anu.edu.au/data-release/dr4/) and [Onken et al. 2024](https://doi.org/10.1017/pasa.2024.53).
- J-PLUS response definition, including CCD, optics and atmosphere: [official instrumentation](https://www.j-plus.es/survey/instrumentation); [DR4 calibration metadata](https://archive.cefca.es/catalogues/jplus-dr4/adql_help_table?db=J-PLUS-DR4&name=jplus.Filter).
- Filter profiles: [SVO Filter Profile Service](https://svo2.cab.inta-csic.es/theory/fps/); original responses retain their providers' terms.
- Prior white-dwarf outlier classification: [López-Sanjuan et al. 2025](https://doi.org/10.1051/0004-6361/202555286), discussed with exact catalogue joins in the [additional-photometry report](../independent_photometry/README.md).
- Underlying DESI/PS1 spectra, photometry and colour framework retain the project's existing [data acknowledgments](../literature/DATA_ACKNOWLEDGMENTS.md). Shota Moriwaki is the project initiator and maintainer; ChatGPT assistance is disclosed as a tool, not a scientific author.
