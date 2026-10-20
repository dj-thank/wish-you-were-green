# From unusual white-dwarf colours to a testable research programme

**Updated 20 October 2026 UTC. Research revision 0.2.0 plus dated follow-ups. Project: Shota Moriwaki. This is an unreviewed research record containing ChatGPT-assisted analysis and writing.** [日本語](README.ja.md) · [Project overview](../README.md)

## Current summary — 20 October 2026

The [20 October follow-up](FOLLOWUP_2026-10-20.en.md) ([日本語](FOLLOWUP_2026-10-20.ja.md)) adds original-observation unit matches, newly retrieved imaging photometry, measured and prospective band constraints, and repeated spectral-shape diagnostics. It does not change the research version to a new release or establish a physical discovery.

| Current scope | Result and source |
|---|---|
| Unchanged inventory | 9,902 records / 6,003 entity keys |
| Current scoped scientific screen | **8,074 eligible / 419 strong records / 324 entity keys**; [scientific summary](unit_resolution_followup/science_view_summary.json), [viewer](unit_resolution_followup/current_view.html) |
| MWDD SDSS conventions | **327 Fν / 939 Fλ / 966 unresolved**; 613 additional conventions verified from original observations |
| New native-support audit | **601 usable / 12 colour-withheld** among those 613; ten newly withheld after the old-gate compatibility calculation, two already ineligible |
| Formerly unavailable review entities | Units resolved for 115; supported colour calculations recovered for 112 |
| Additional actual viewing | All 613 records across 39 sheets, with [individual notes](unit_resolution_followup/individual_review.md) and [completion provenance](unit_resolution_followup/review_completion.json) |
| Additional imaging photometry | Fixed25: **450 slots / 52 strict measurements / 46 fully covered / 14 targets**; [source and quality audit](independent_photometry/README.md) |
| Actual measured-band constraints | **165 cases / 660 optimization branches**; [measurement report](measurement_design/README.md) |
| Prospective band-separation experiment | **276 cases plus 8 endpoint-closure cases / 568 branches**; same report, explicitly separate from acquired measurements |
| Repeated spectral shapes | Four DESI pairs; one pair of SDSS coadds comprising **5 nights / 18 physical exposures**; [repeat report](repeat_shape_validation/README.md) |

**The new native-support rules were checked on 613 records, not the whole inventory.** The earlier 7,473 eligible records retain their previous calculations. The retained old-gate compatibility screen, **8,084 / 421 / 325**, precedes the new gap/support exclusions and is not the current scientific selection. The original 18 October and v0.1 tables remain dated evidence.

**J1323−0129 has a revised evidence status.** Its SDSS convention is now proven Fλ against the same original observation, recovering qualitative positive-Duv support. Native S/N 2.36 and an approximately 1.138″ epoch-corrected separation from the SDSS PLUG position keep precision independent corroboration withheld; native Gaia XP is unavailable. The statement that the convention is unresolved in the historical body below describes 18 October, not the current result.

For J0429, adding measured SkyMapper r/i to PS1 griz has a minimum of approximately **4.92%** shape change in the specified 800 Å family; strict green and red-order minima are approximately **5.0103% / 4.9236%**. Adding a 0.02 mag allowance to the new-survey boxes removes that narrow separation. Source photons are newly observed, but calibration standards and J-PLUS's WD-locus/PS1-r anchors can be shared. Bands used in a joint fit are no longer held-out validation of that fit. For J0429, even PS1 griz plus the ten covered J-PLUS bands (14 total) admit numerically indistinguishable opposite-order solutions at 400 Å spacing / 5% budget; this is a conditional numerical counterexample, not a general impossibility theorem.

Use `python scripts/verify_research_oct20.py` from the repository root for the current offline checks. The committed raw responses, lossless query bundle, compact original arrays, numerical witnesses and audit records support computational reproduction; automated verification does not repeat actual viewing or certify physical novelty.

## Preserved report — 18 October correction and 19 October additions

**The methods and results below retain their original dates. References to “current” within this preserved body mean the 18–19 October snapshot.** Use the summary above and the dated 20 October report for the latest eligibility and J1323 evidence status.

**19 October work: [follow-up report](FOLLOWUP_2026-10-19.en.md).** The remaining 2,007 review entities have individual viewing notes: 1,684 with then-accepted spectra and 323 with explicit unavailable panels. Work executed 450 measured-photometry scenarios, 720 public control-model fits and residual diagnostics for 25 published DZ/DQ plots. J0429 has strict opposite channel-order witnesses inside the same observed griz error boxes and a 5% shape budget.

**18 October correction, preserved: independent SDSS colour support for J1323−0129 was withdrawn.** Its MWDD SDSS flux convention remained unresolved at that stage, and native Gaia XP was unavailable in that acquisition. The DESI estimate remained a single-instrument colour candidate. The historical 9,023 eligible records and 337 strong-outlier entities were superseded for that selection by **7,473 eligible records, 395 strong-outlier records and 308 entity keys**. [18 October corrected summary](precision/flux_units/corrected_screen_summary.json)

The strongest result is a demonstrated flux-representation bug, corrected through original-observation comparisons. Further work connects that correction to covariance, repeated observations, held-out photometry and atmosphere-model questions. The scientific objective is to establish **which unusual chromaticities remain identifiable under measured calibration uncertainties**, then test physical explanations with independent predictions.

## 1. Scope of the work actually completed

All 9,902 spectrum records were catalogued, with 6,003 entity keys. Historical rules flagged 2,344 entities and 4,901 records. The review retrieved 4,355 distinct raw inputs with matching SHA256 hashes: 4,353 reproduced their frozen calculation, while two existing non-positive-XYZ failures remained failures. Maximum successful reproduction displacement was 7.01×10⁻¹³ in uv. Reproducibility and correct physical interpretation were separate tests. [Census](outlier_audit/census_summary.json) · [Retrieval](outlier_audit/retrieval_summary.json) · [Recalculation](outlier_audit/recompute_summary.json)

All 337 historical strong-outlier objects were actually inspected across 22 contact-sheet images, with an individual panel record: [176 objects](outlier_audit/visual_review_01_11.md) and [161 objects](outlier_audit/visual_review_12_22.md). This was inspection of prepared spectra, not every original detector image. Display-only 40 Å binning, individual normalization and fixed ordinate limits conceal some narrow features and excursions. The full record inventory is available through the [object viewer](outlier_audit/object_audit.html). Entity keys include provisional positional assignments and cannot automatically be counted as distinct verified stars.

On 19 October the remaining **2,007 entities / 4,370 records** were followed through [126 current-unit contact sheets](outlier_followup/README.md), retaining 323 unavailable panels and 1,305 unit-withheld records. All 3,041 plotted original inputs passed SHA and current-colour reproduction checks. The [final individual ledger](outlier_followup/individual_review.csv) completes the historical 2,344-entity viewing queue. Supplemental zooms, native peaks, known Gaia variables and original-fibre epoch positions have separate evidence records; preparation of a figure alone is not counted as viewing it.

## 2. The material correction: mixed Fν and Fλ

The historical pipeline treated unspecified MWDD SDSS `flux_original` as energy per wavelength, Fλ. Direct SDSS FITS comparisons establish that some exports instead represent Fν. Up to a wavelength-independent scale, **Fλ ∝ Fν/λ²**. This changes spectral shape and therefore colour.

Of 2,232 MWDD SDSS files, **149 were verified as Fν-shaped, 504 as Fλ-shaped, and 1,579 remained unresolved**. Acceptance required native wavelength/sample identity, at least 1,000 comparison samples spanning 3,500 Å, and strict post-transformation residual gates. A slope close to two alone was insufficient. [Evidence and thresholds](precision/flux_convention_evidence.json)

The 149 conversions moved chromaticity by median Δuv=0.02890 and maximum 0.03419. The corrected screen recomputed 3,629 SDSS records; unresolved conventions and unsupported formats retain their records but have current physical colours withheld. This does not establish that every unresolved spectrum is Fν. [Current records](precision/flux_units/corrected_record_screen.csv.gz) · [Current entities](precision/flux_units/corrected_object_screen.csv)

Identical original samples in two archives do not constitute independent observations. Verified units also do not establish absolute calibration or correct source identity. Within the initial 27, J1323 and the known Gaia variable retain unresolved SDSS conventions. PSO J186.4406+47.1036 has Fλ verified against original SDSS, retaining SDSS–Gaia comparison. [Candidate impact](precision/flux_units/candidate27_sdss_convention_impact.json)

## 3. Numerical precision versus observational uncertainty

Continuous projection onto the Planckian locus was checked for 9,868 finite historical records. Maximum distance change was 3.78×10⁻⁵. Forty-eight tiny near-locus offsets changed sign, but none crossed the tested screening thresholds; the maximum change for the four headline estimates was 7.02×10⁻⁸. The locus temperature is a colour coordinate, not an atmospheric effective-temperature measurement.

Exact integration under piecewise-linear spectral/observer interpolation moved the four candidates by at most 2.93×10⁻⁵. Changing their narrow sky masks produced approximately 0.00022–0.00063 uv displacement. Input conventions, calibration and spectral support therefore deserve priority over a denser temperature grid. [Precision report](precision/README.md)

A near-unity legacy coverage ratio describes integration across retained samples, including interpolation over rejected regions. Removed native cells account for approximately 3.5–3.6% of Y-observer weight in the headline spectra; this is not the missing fraction of stellar light. Synthetic missing-window tests expose limitations of coverage thresholds but are not measurements of actual missing flux.

## 4. Broadband agreement leaves unconstrained spectral shapes

A constrained optimization constructed positive, smooth multiplicative changes preserving the cleaned baseline's synthetic PS1 g,r,i photon fluxes while reaching a linear-sRGB green-channel boundary.

| Cubic-spline knot spacing | J0913 minimum maximum distortion | J0429 |
|---|---:|---:|
| 400 Å | 7.94% | 4.27% |
| 800 Å | 11.87% | 6.49% |
| 1,600 Å | 29.06% | 12.18% |

These are adversarial existence results within specified spline spaces, **not measured DESI errors, confidence limits, probabilities or abundance perturbations**. Knot spacing is not an inferred instrumental correlation length. Metamerism and broadband null spaces are established concepts; the contribution here is an explicitly reproducible, object-specific sensitivity experiment. Methodological novelty remains subject to specialist literature review. [Constraints and results](precision/photometric_nullspace.json)

The observational counterpart predicts PS1 z after fitting only gri. **Ten of 25 objects have absolute predicted-minus-observed z residuals above 0.05 mag**, ranging from −0.08967 to +0.09904 mag. Residuals are +0.03434 for J0913, −0.06098 for J0429, +0.00311 for J1329 and −0.08149 mag for J1323. All y predictions were withheld because full passband coverage is missing. The z residuals are additional diagnostics; shared PS1 and calibration errors prevent interpreting quoted pixel/photometric errors as complete significance estimates. [Held-out-band analysis](precision/candidate_recalibration/README.md)

## 5. The initial 27 remain a historical follow-up set

Standardized PS1 calibration produced 25 DESI conditional intervals, including 12 newly anchored objects. Swan's quoted errors already include rounded native DR1 errors plus 0.01 mag in quadrature; the pipeline applies max(quoted error, 0.02 mag), without adding the same 0.01 again. Differences from v0.1, including J0913's revised nominal Duv=+0.019058, reflect analysis definitions rather than measured stellar change. Original headline products are preserved. [Photometry audit](literature/swan_photometry_definition.md)

Native Gaia coefficients/covariance were obtained for 26/27 objects, with 200,000 formal Monte Carlo draws for each full and truncated reconstruction. These are reconstructions of the same observations; unavailable cross-BP/RP covariance, truncation bias and calibration systematics remain limitations. [Formal results](precision/gaia_expanded/formal_colour_results.csv)

![All initial 27 objects and their conditional intervals](candidate27_uncertainty_comparison.png)

Nine objects have DESI and both Gaia central 95% intervals wholly beyond the same signed |Duv|=0.01 boundary; all are negative-Duv cases. Separating one object with a 417.9-times-brighter Gaia neighbour leaves eight, two of which still have flagged z residuals. These are descriptive subsets, not confirmed discoveries or combined probabilities. Five objects change point-threshold classification between Gaia reconstructions; 17 have maximum available pairwise Δuv≥0.003. J0913's truncated lower bound, +0.009956, narrowly crosses the threshold. Duv itself does not define “green.” [Every-object synthesis](candidate27_followup.md)

## 6. Independent observations and identity checks

Seven existing public DESI exposures for four targets were newly retrieved and analysed, with TARGETID/FIBER and observation identifiers preserved. Three targets supplied six complete night comparisons using shared PS1 anchors: J0111 has Duv −0.009529/−0.011147; J1105 +0.010261/+0.013296; J1252 −0.010579/−0.006955. Two pairs straddle the exploratory threshold. J1329's additional exposure has all 2,881 Z-camera pixels masked with zero IVAR, so repeated molecular structure cannot establish a second complete colour. Camera-join sensitivity was retained without tuning individual arm scales. [DESI provenance and results](literature/README.md)

ZTF DR24 supplied 2,473 candidate measurements and 4,646 control-star measurements. Quality and epoch-propagated positional selection retained 2,327 candidate points. No new intrinsic stellar variability was established; period/injection-recovery limits were not calculated. Differential-control uncertainty must be included when interpreting changes in χ². A roughly 0.7-mag bright J1323 point, despite catalogue flag zero, lies 1.549″ from its epoch-propagated position versus 0.775″ from fixed 2016 coordinates. It fails the predeclared 1.5″ cut; raw data and three original-image cutouts remain available. Its cause is unresolved. [Variability audit](external_validation/README.md)

The 27-object Gaia field audit found neighbours for three targets, two with G-flux ratios above ten, and one already catalogued variable. Its best classifier class is CV, but the score is not a posterior probability. NOT_AVAILABLE does not establish constancy, and low RUWE does not exclude photometric contamination.

## 7. Chemical databases need the same provenance discipline

A fixed March 2026 PEWDD snapshot associated 1,107 catalogue IDs with 2,547 literature/model rows. Independent parsing reproduced 236 rows whose coordinate names disagree with their tabulated positions by over ten arcminutes. Three original-paper/CDS plus official-Gaia checks establish two incorrect Gaia associations and one correct Gaia ID with conflicting coordinate fields. **The entire 236-row review list is not a list of proven incorrect IDs.** Unresolved associations are withheld from chemical inference rather than automatically repaired. [Independent checks](literature/independent_key_audit.md)

Non-detections, upper limits, atmosphere assumptions and separate papers remain separate. Thirty IDs with same-paper Na/Ca detections are not an adjudicated chemical sample. All initial27 objects are absent from this PEWDD snapshot, yet 25 have exact-ID prior atmosphere analyses and PSO has a name-based 2019 analysis. Catalogue absence cannot establish novelty. Kilic's DZ fits adjust Ca while fixing other metals to CI-chondritic ratios; they do not independently measure Na. [Prior inventory](literature/outputs/candidate27_prior_inventory.csv)

## 8. Three priority hypotheses

These are proposed experiments, not newly completed atmosphere fits.

**1. Fixed metal ratios fail held-out DZ predictions even after calibration uncertainty is modelled.** Compare fixed-CI models with free Na/Ca and Mg/Ca for J0913, J0429 and J1105, allowing identical calibration nuisance functions. The prediction is improvement in unused wavelengths or independent photometry consistent with Na wings, Ca suppression and Mg features. Reject this interpretation if predictive improvement disappears or is absorbed by permissible calibration distortions. Required data are full-range, separately calibrated spectra, simultaneous photometry, native-resolution elemental regions and field images. Colour derived from a spectrum must not be counted as independent information in that spectrum's likelihood.

**2. Some low-mass DQ or extreme cool solutions reflect incomplete single-atmosphere modelling.** Compare Gaia-distance-constrained absolute SEDs and molecular-band dilution under single and unresolved two-component models. Treat carbon abundance, pressure shifts, magnetic effects and H/He assumptions separately. The prediction is consistent improvement of held-out UV/infrared flux and band depth across epochs. The hypothesis is unsupported if a calibrated single-star model predicts equally well or the components remain unidentifiable. Additional UV/near-infrared observations, repeated velocities and sometimes polarimetry are needed; absent velocity variability alone does not exclude a companion. Published J1323 parameter changes are model comparisons, not temporal evolution.

**3. A measurement-process model predicts which marginal colour classifications fail replication.** Inject empirically constrained correlated noise, calibration distortions and contamination into normal and known unusual WD controls. Predict z, independent instruments and epochs before using them in fits. Success means validated interval coverage and recovery/false-positive rates in held-out samples. Failure means unpredicted, instrument- or class-dependent discrepancies persist. This requires non-candidate parent samples, measured calibration residuals, masks/covariance and PSF-wing images. It offers a calibration-robust chromaticity methodology paper without claiming metamerism as new physics.

## 9. Observation and reproduction priorities

Proposed observations should cover the full 360–830 nm interval and required calibration passbands, with simultaneous photometry and independent epochs. **Relative spectrophotometry at 1–2% is a design target, not a guaranteed capability.** Verify it using standards, repeats and held-out bands. Preserve Gaia release/epoch, SDSS plate–MJD–fiber, DESI TARGETID/NIGHT/EXPOSURE/FIBER, PS1 object/release and original-paper rows when joining photometric, spectral and chemical evidence.

The [research-extension notebook](research_extension.ipynb) connects the current evidence tables, figures and verification scope. With required inputs/caches available, local reproduction includes:

```bash
.venv-research/bin/python scripts/verify_reproduction.py --with-controls
.venv-research/bin/python -m unittest discover -s tests -p 'test_*.py' -v
.venv-research/bin/python scripts/verify_research_extension.py
.venv-research/bin/python scripts/verify_research_followup.py
.venv-research/bin/python research/precision/precision_audit.py
.venv-research/bin/python research/precision/flux_units/build_corrected_screen.py
.venv-research/bin/python research/candidate_followup.py
```

The first three commands verify the preserved compact results, all core tests, and the extension's inputs, invariants and selected recalculations. The remaining commands regenerate specified research products. The extension verifier does not repeat survey downloads, human image inspection, every Monte Carlo draw or installation of GaiaXPy.

Use [core requirements](../requirements-core.txt) and the separate [pinned GaiaXPy 2.1.5 environment](../mwdd/gaia_validation/requirements-gaia.txt). Run `research/precision/gaia_candidate_covariance.py reconstruct` there, then `colours` in the core environment. Initial downloads and `fetch` require network access; offline recalculation requires the documented manifests/caches. [Compact-result reproduction guide](../docs/reproducibility.en.md)

Population incidence, selection-corrected discovery probabilities and FDR remain uncalculated. The physical fits and empirical calibration/recovery experiments above remain future work. Specialist review and a fuller novelty assessment are required before publication. Known green WDs, sodium/carbon colour effects and pressure/CIA mechanisms are not claimed as new discoveries. Original sources retain their attribution and terms; consult the [literature report](literature/README.md) and [data acknowledgments](literature/DATA_ACKNOWLEDGMENTS.md).
