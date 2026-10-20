# Wish You Were Green

## White-dwarf chromaticity research — v0.2

**English** · [日本語](README.ja.md)

**The 20 October follow-up resolves 613 more SDSS flux conventions and adds observed photometry from two other surveys.** The current scoped screen contains **8,074 eligible spectrum records and 419 strong-outlier records / 324 entity keys**. Of 2,232 MWDD SDSS exports, **327 are verified as Fν-shaped, 939 as Fλ-shaped, and 966 remain unresolved**. The new native-pixel support audit applies to the 613 newly resolved records; the earlier 7,473 eligible values are retained without claiming a new support audit of them. [Current scientific summary](research/unit_resolution_followup/science_view_summary.json) · [Interactive record view](research/unit_resolution_followup/current_view.html)

These are known stars. The research investigates their calculated human-vision chromaticities, measurement robustness and possible atmosphere-model tests. It remains **exploratory, ChatGPT-assisted and unreviewed**; it does not establish new stars, new absorption physics, worldwide priority or a population discovery rate.

**Project initiator and maintainer:** Shota Moriwaki

**Research revision:** 0.2.0 plus 20 October follow-up · **Updated:** 20 October 2026 UTC

**Repository:** [dj-thank/wish-you-were-green](https://github.com/dj-thank/wish-you-were-green)

**Start with the [20 October research report](research/FOLLOWUP_2026-10-20.en.md) or [日本語の追加報告](research/FOLLOWUP_2026-10-20.ja.md).** The [research overview](research/README.md) preserves the dated earlier methods and results alongside current updates.

### New on 20 October: actual additional measurements and stricter support checks

The original pixels establish conventions for **613 further records**, all individually viewed across 39 contact sheets. Of these, **601 have sufficient native support for a current colour; 12 remain withheld**, including ten newly rejected by the support check and two already rejected by the earlier gate. Units were resolved for 115 previously unavailable review entities; **112 now have a supported colour calculation**. Resolving units alone does not validate spectral coverage, noise or target centring. [Current record table](research/unit_resolution_followup/science_record_view.csv.gz) · [Individual notes](research/unit_resolution_followup/individual_review.md)

For the fixed 25-candidate cohort, **450 band slots were audited; 14 targets supplied 52 quality-selected SkyMapper/J-PLUS measurements, of which 46 have complete spectral passband coverage**. Their source photons come from different observations, while Gaia-based calibration and J-PLUS's WD-locus/PS1-r zero points can share systematic errors. Misassociated neighbours, masks, missing values and failed S-PLUS queries remain explicit. [Photometry and identity evidence](research/independent_photometry/README.md)

Adding SkyMapper r/i to the observed PS1 griz boxes raises J0429−0354's minimum required shape change to **4.92%** in the specified 800 Å spline family. Strict green and red-order solutions require approximately **5.0103% and 4.9236%**, respectively. An additional 0.02 mag box allowance removes that distinction; these are conditional feasibility bounds, not evidence of a measured colour change. A separate J0429 experiment finds that even PS1 griz plus the ten covered J-PLUS bands (14 total) can admit numerically indistinguishable opposite-colour spectra at 400 Å spacing and a 5% shape budget. [Measured and prospective constraints](research/measurement_design/README.md)

**J1323−0129's SDSS convention is now verified as Fλ by the same original observation.** Qualitative positive-Duv support is recovered, but low native S/N (2.36) and an approximately 1.138″ epoch-corrected separation from the SDSS PLUG position keep precision independent corroboration withheld. Native Gaia XP remains unavailable. Separately, a discrepant SDSS pair comprises **two coadds from five nights and 18 physical exposures**, not two individual nights. [Repeated-shape analysis](research/repeat_shape_validation/README.md) · [Full 20 October interpretation](research/FOLLOWUP_2026-10-20.en.md)

### Preserved 19 October work: individual review and model comparisons

**A concrete source of misleading graph offsets was identified:** two proven duplicates of the same SDSS observations followed different calibration branches. Their apparent Δuv differences of 0.01360 and 0.01517 shrink by more than 99.99% under the same existing correction. [Original-pixel evidence and corrected comparison](research/outlier_followup/representation_calibration/README.md)

The [19 October follow-up](research/FOLLOWUP_2026-10-19.en.md) ([日本語](research/FOLLOWUP_2026-10-19.ja.md)) adds actual individual notes for the remaining **2,007 review entities**, including 1,684 with accepted spectra and 323 explicit unavailable panels. Together with the earlier 337, every entity in the historical 2,344-object review queue has a viewing record; this is not visual inspection of all 6,003 inventory entities or confirmation of physical anomalies.

New computations cover **450 measured-photometry scenarios / 1,800 linear programmes**, **720 pure-H/He control-template fits**, and 25 published composition-specific model plots. For **J0429−0354, two explicitly constructed spectra fit the same observed PS1 griz error boxes while having opposite green/red channel ordering, both within about 4.25% maximum shape change**. Under the fixed 800 Å spline model and one quoted error per band, 14/25 candidates cannot fit griz within a 2% shape budget. These are conditional identifiability tests, not inferred calibration-error distributions or new atmosphere measurements. [Calibration experiment](research/calibration_followup/README.md) · [Published model tests](research/model_validation/README.md)

## Current results and historical records

| Scope | Current or recorded result |
|---|---:|
| Original spectrum inventory | 9,902 records; 6,003 catalogue entity keys |
| Current eligible records, with the scoped native-support update | **8,074** |
| Current strong-outlier screen | **419 records / 324 entity keys** |
| MWDD SDSS representation checks | **327 Fν / 939 Fλ / 966 unresolved** |
| Newly resolved records with individual native-support review | **613: 601 usable / 12 colour-withheld** |
| Previously unavailable entities with newly resolved units / supported colours | **115 / 112** |
| Additional photometry, fixed 25-candidate cohort | **450 slots / 52 selected measurements / 46 fully covered / 14 targets** |
| Historical strong-outlier objects actually inspected | 337 objects across 22 contact sheets |
| Review entities inspected on 19 October | 2,007 across 126 sheets: then 1,684 with spectra / 323 unavailable |
| Original spectra checked in the 19 October visual review | 3,041 original-file hashes checked and snapshot colours reproduced |
| New 20 October individual viewing records | 613 records across 39 sheets; all panels actually viewed |
| Review inputs recovered with their recorded raw SHA256 | 4,355; 4,353 old calculations reproduced, two existing failures retained |

The historical v0.1 **9,023 eligible / 337 strong-outlier entities**, 18 October **7,473 / 395 records / 308 entity keys**, and 20 October old-gate compatibility **8,084 / 421 / 325** describe different retained snapshots. The current [record table](research/unit_resolution_followup/science_record_view.csv.gz) and [object table](research/unit_resolution_followup/science_object_view.csv) apply the additional native-support review to its declared 613-record scope. Entity keys include legacy positional associations and must not be counted automatically as verified distinct stars. These are exploratory selection counts, not discovery significance. [Audit definitions](research/README.md)

![Current chromaticity screen with the scoped 20 October native-support update](research/unit_resolution_followup/science_colour_plane.png)

*The diagram is a calculated CIE chromaticity screen. The new native-support audit covers 613 records; previously eligible records retain their earlier values. Raw spectra, withheld cases and historical outputs remain traceable.*

## Four principal DESI colour estimates

The current values below come from **DESI spectra recalibrated against the observed PS1 g,r,i anchors in the standardized v0.2 analysis**, using the CIE 1931 2° observer. Intervals are central 95% Monte Carlo intervals conditional on the adopted spectral-noise and photometric-calibration model.

| Candidate | Gaia DR3 source_id | Display description | sRGB | Duv | Conditional 95% Duv interval |
|---|---|---|---|---:|---|
| WD J0913+4434 | 818833831355548928 | Pale yellow-green | #F1FFC9 | +0.019058 | +0.016975 to +0.021233 |
| WD J0429−0354 | 3204436719718449280 | Pale yellow-green | #F8FFDC | +0.012809 | +0.011973 to +0.013651 |
| WD J1329+0033 | 3711047662972690688 | Pink | #FFC1CF | −0.022652 | −0.024811 to −0.020482 |
| WD J1323−0129 | 3638333660492606976 | Unusual yellow; precision SDSS corroboration withheld | #FFE96A | +0.023498 | +0.020943 to +0.025993 |

The [full-precision source table](research/precision/candidate_recalibration/standardized_colours.csv) records anchors, uncertainties, raw hashes and calibration parameters. The old [v0.1 headline table](results/headline_candidates.csv) is preserved. Small changes, including J1323's one-channel display difference, reflect calibration/error definitions rather than measured stellar variability. Hexadecimal digits are display values, not physical measurement precision. [PS1 definitions and DR1/DR2 comparison](research/literature/swan_photometry_definition.md)

**Positive Duv does not by itself mean green.** It measures a signed displacement from the Planckian locus in CIE 1960 u,v. The |Duv|=0.01 boundary is an exploratory convention, not a universal visual threshold or a significance level. These sRGB values are normalized standard-observer calculations, not photographs, brightness estimates or dark-adapted appearances.

## What the additional work established

- **All initial 27 candidates remain in a follow-up ledger.** There are 25 standardized DESI intervals, including 12 newly anchored objects, and native Gaia covariance for 26 targets. Full and truncated Gaia use the same observations and are correlated reconstructions. [Every-object comparison](research/candidate27_followup.md)
- **Agreement among three interval estimates is still limited evidence.** Nine initial candidates have DESI conditional and both Gaia formal 95% intervals wholly beyond the same signed |Duv|=0.01 boundary. One has a >10× brighter Gaia neighbour; of the remaining eight, two have flagged held-out z residuals. These counts are descriptive subsets, not confirmed discoveries or pooled probabilities.
- **Held-out photometry identifies further calibration questions.** Ten of 25 predictions for PS1 z, unused in gri fitting, differ from the observed value by more than 0.05 mag. These are additional diagnostics, not total-error significance estimates. All y predictions were withheld for incomplete spectral coverage. [Held-out-band report](research/precision/candidate_recalibration/README.md)
- **Independent nights and time-domain checks retain failures.** Seven public DESI exposures for four targets were retrieved; three targets have six accepted complete-night comparisons. J1329's extra night lacks valid Z-arm coverage. ZTF supplied 2,473 candidate and 4,646 control measurements; no new intrinsic variability was established. A displaced bright J1323 measurement is retained with its rejection reason and original-image checks. [DESI](research/literature/README.md) · [ZTF and Gaia fields](research/external_validation/README.md)
- **Database keys and physical models also need review.** The PEWDD snapshot contains 236 name–coordinate conflicts. Three original-paper/Gaia checks establish different error types; they do not prove 236 wrong Gaia IDs. The initial candidates also have substantial prior atmosphere work. [Identity audit](research/literature/independent_key_audit.md) · [Prior inventory](research/literature/outputs/candidate27_prior_inventory.csv)

The proposed next experiments compare free Na/Ca and Mg/Ca against fixed metal ratios, test unresolved-companion and atmosphere alternatives, and measure recovery/false-positive rates under empirically constrained calibration errors. An object-specific broadband-null-space stress test motivates these observations; its constructed distortions are not measured errors. Colour derived from a spectrum must not be counted as independent evidence in that same spectrum's likelihood. [Hypotheses, predictions and falsification conditions](research/README.md#8-three-priority-hypotheses)

## Reports, notebook and audit navigation

| Resource | Status and contents |
|---|---|
| [20 October report](research/FOLLOWUP_2026-10-20.en.md) · [日本語](research/FOLLOWUP_2026-10-20.ja.md) | Current scoped census, additional measured constraints, repeat spectra and limitations |
| [Research overview](research/README.md) · [日本語報告](research/README.ja.md) | Current summary with preserved 18–19 October methods and results |
| [Current record viewer](research/unit_resolution_followup/current_view.html) · [Scientific summary](research/unit_resolution_followup/science_view_summary.json) | 613 new unit decisions, native-support exclusions and current colours |
| [Independent-observation photometry](research/independent_photometry/README.md) · [Measurement-design report](research/measurement_design/README.md) | All 25 targets, 450 availability decisions, 52 selected / 46 covered measurements and conditional experiments |
| [Repeated spectral shapes](research/repeat_shape_validation/README.md) · [日本語](research/repeat_shape_validation/README.ja.md) | Four DESI pairs and two disjoint SDSS coadds; shared anchors and observing conditions |
| [19 October follow-up](research/FOLLOWUP_2026-10-19.en.md) · [日本語](research/FOLLOWUP_2026-10-19.ja.md) | Completed review queue, measured-band feasibility, actual model comparisons and targeted diagnostics |
| [All 2,007 additional review records](research/outlier_followup/individual_review.csv) | Individual observations, unavailable cases and fixed image links |
| [Research-extension notebook](research/research_extension.ipynb) | Preserved v0.2 extension: dated verification, corrected counts and figures |
| [Initial27 follow-up CSV](research/candidate27_followup.csv) · [JSON](research/candidate27_followup.json) | Every candidate, conditional intervals, provenance and next checks |
| [Candidate uncertainty comparison](research/candidate27_uncertainty_comparison.png) | All 27 objects; full/truncated Gaia are not independent |
| [18 October object audit HTML](research/outlier_audit/object_audit.html) | Preserved histories for all 9,902 records; consult the current record viewer for 20 October eligibility |
| [Visual review pages 01–11](research/outlier_audit/visual_review_01_11.md) · [12–22](research/outlier_audit/visual_review_12_22.md) | Actual inspection notes for every historical strong-outlier panel |
| [v0.1 English report](docs/report.en.md) · [日本語](docs/report.ja.md) | Historical report, with a correction banner; old numbers retained |
| [v0.1 English notebook](white_dwarf_colour_research.ipynb) · [日本語](white_dwarf_colour_research.ja.ipynb) | Historical executed outputs; introductory correction banner |
| [Data availability](docs/data-availability.md) · [Reproduction guide](docs/reproducibility.en.md) | Original compact inputs and baseline verification scope |
| [Version history](CHANGELOG.md) | Scientific corrections and interpretation changes |

## Reproduce and verify

Use Python 3.12. Initial dependency installation requires a package index or a local cache.

```bash
git clone https://github.com/dj-thank/wish-you-were-green.git
cd wish-you-were-green
python3.12 -m venv .venv-colour
.venv-colour/bin/python -m pip install -r requirements-core.txt

.venv-colour/bin/python scripts/verify_reproduction.py --with-controls
.venv-colour/bin/python -m unittest discover -s tests -p 'test_*.py' -v
.venv-colour/bin/python scripts/verify_research_extension.py
.venv-colour/bin/python scripts/verify_research_followup.py
.venv-colour/bin/python scripts/verify_research_oct20.py
```

On Windows, use the environment interpreter at `.venv-colour\Scripts\python.exe`.

The compact verifier reproduces the preserved v0.1 principal DESI/Gaia calculation and all 54 raw SDSS controls offline. The dated extension/follow-up verifiers check their preserved inputs and calculations. The 20 October verifier adds unit-resolution/support evidence, the photometry reconstruction, measured/prospective constraints and repeated-shape diagnostics from committed compact inputs. Verification does not repeat survey downloads, actual image inspection, all Monte Carlo draws or a GaiaXPy installation. A passing check establishes specified computational consistency, not astrophysical novelty or absence of systematics.

The [research report](research/README.md#9-observation-and-reproduction-priorities) explains deeper recalculation. Native XP reconstruction uses a [separate pinned GaiaXPy environment](mwdd/gaia_validation/requirements-gaia.txt). Full raw-spectrum or camera-FITS recovery requires archive access and the documented SHA256 manifests. Historical inputs are not silently replaced with newer archive responses.

## Attribution, citation and reuse

**Shota Moriwaki** initiated and maintains the project. Code, acquisition, analysis, checks and drafting used **OpenAI ChatGPT assistance**. ChatGPT is a disclosed tool, not a scientific author. This work is unreviewed and implies no affiliation with or endorsement by the cited surveys or authors.

Observations and reductions are credited to DESI, ESA/Gaia/DPAC, SDSS, Pan-STARRS, SkyMapper and J-PLUS; catalogue, model and passband contributions remain credited to MWDD, PEWDD, CDS, the SVO Filter Profile Service and the original authors. The colour framework and previous unusual-colour measurements, including those of Hollands and coauthors, are prior work. [Acknowledgments](ACKNOWLEDGMENTS.md) · [Extension data acknowledgments](research/literature/DATA_ACKNOWLEDGMENTS.md) · [Bibliography](docs/references.bib)

Cite the version or commit actually used and the underlying data/papers. [CITATION.cff](CITATION.cff) contains machine-readable metadata:

> Moriwaki, Shota (2026). *Wish You Were Green: white-dwarf chromaticity research*. Version 0.2.0. Unreviewed public-data research and reproducibility code. https://github.com/dj-thank/wish-you-were-green

Original code retains **Apache-2.0** and original explanatory prose **CC BY 4.0**. Third-party materials retain their terms; the unchanged CIE table remains **CC BY-SA 4.0**. [Licence details](LICENSES/README.md) · [Contributing](CONTRIBUTING.md)
