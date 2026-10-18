# Additional white dwarf colour candidates from public spectra

**English** · [日本語](README.ja.md)

**Two additional pale yellow-green white dwarf candidates emerge from a reproducible analysis of public spectra:** WD J0913+4434 and WD J0429−0354. This repository also reports a pink candidate, WD J1329+0033, and an unusually yellow candidate, WD J1323−0129.

These are **known stars**. The potentially new contribution is their calculated human-vision chromaticity and the checks supporting it. This is an **exploratory, unreviewed research note**, not a claim to discovering the stars, new atmospheric physics, or worldwide priority.

**Project initiator and maintainer:** Shota Moriwaki  
**Analysis date:** 18 October 2026 · **Version:** 0.1.0  
**Repository:** [dj-thank/pale-yellow-green-white-dwarf-candidate](https://github.com/dj-thank/pale-yellow-green-white-dwarf-candidate)

![Computed colour patches for the four principal candidates](figures/candidate_colours.png)

*These are normalized sRGB patches computed from spectra, not photographs. They do not show apparent or surface brightness, and they do not model dark-adapted viewing.*

## Principal results

All representative values below use **DESI spectra recalibrated against Pan-STARRS g, r and i photometry**, integrated with the CIE 1931 2° standard observer.

| Candidate | Gaia DR3 source_id | Colour candidate | sRGB | Duv | Conditional 95% Duv interval |
|---|---|---|---|---:|---|
| **WD J0913+4434** | 818833831355548928 | Pale yellow-green | #F1FFC9 | +0.01901 | +0.01695 to +0.02112 |
| **WD J0429−0354** | 3204436719718449280 | Pale yellow-green | #F8FFDC | +0.01281 | +0.01197 to +0.01365 |
| WD J1329+0033 | 3711047662972690688 | Pink | #FFC1CF | −0.02265 | −0.02481 to −0.02048 |
| WD J1323−0129 | 3638333660492606976 | Unusual yellow | #FFE86A | +0.02348 | +0.02094 to +0.02597 |

Full-precision x, y, u, v, calibration parameters, source URLs and hashes are in [headline_candidates.csv](results/headline_candidates.csv). Read the [English report](docs/report.en.md) or [Japanese report](docs/report.ja.md) for the complete interpretation.

**Duv is a signed distance from the Planckian locus in CIE 1960 u,v. Positive Duv does not automatically mean green.** J1323−0129 is a yellow counterexample. The distance threshold of 0.01 follows the comparison convention in [Hollands et al. (2026)](https://doi.org/10.1093/rasti/rzag069); it is not a universal perceptual threshold or discovery significance level.

### What the evidence supports

The two pale yellow-green candidates retain similar mean colours in DESI and reconstructions from the original Gaia XP coefficients. Broadband calibration alternatives, spectral shape, nearby sources and existing atmospheric fits were examined. The official [Swan et al. (2026)](https://arxiv.org/html/2609.04314v1) catalogue gives negligible DESI contamination estimates for the principal candidates under its Gaussian aperture model. This is useful evidence, not an upper bound on all contaminating light.

The principal stars are absent from all **236 unique named entries** in Tables 3–6 of Hollands et al. (2026), and were checked against its **231-object DZ parent catalogue**. The reviewed literature did not supply CIE or sRGB measurements for these candidates. That bounded comparison does not prove the absence of all earlier, unindexed or unpublished calculations. Existing classifications, temperatures, compositions and absorption mechanisms remain credited to the original authors. See the [prior-literature evidence](novelty/novelty_evidence.csv).

### Qualifications that must accompany the results

- **DESI intervals are conditional.** They come from 6,000 draws using supplied pixel errors, photometric errors and a 0.02 mag photometric floor. Unknown spectral correlations, calibration systematics, contamination and selection effects are not fully included.
- **Gaia does not independently settle the colour name.** The full wavelength covariance was propagated from the supplied coefficient errors. Formal fractions with the green channel largest are 85.0% for J0913 and 82.3% for J0429 using all bases; the recommended truncated reconstructions give 77.8% and 96.5%. These are noise-model results, not probabilities that a new physical discovery is real. Truncation bias and unprovided BP/RP calibration correlation remain outside that model.
- **Shared calibration is shared evidence.** Two spectra anchored to the same photometry do not have independent calibration errors. Their probabilities must not be multiplied as though they did.
- **Colour appearance is conditional on the observer and display.** The calculation uses energy Fλ, a photopic standard observer and normalized sRGB/D65. It does not apply a chromatic-adaptation model or infer the unobscured stellar surface by dereddening.
- **The search is exploratory.** Thousands of selected records and multiple processing choices were examined. No survey-wide false-discovery rate or global significance was established. The controls and reproduction checks do not remove this limitation.
- **Some attractive cases were rejected.** LP616−53 was downgraded because of close companions and substantial photometric contamination; an extreme-blue case caused by bad photometric anchors was also rejected. The full ranking is not a list of confirmed discoveries.

The [Gaia covariance audit](mwdd/gaia_validation/README.md), [research-integrity note](docs/research-integrity.md) and [full report](docs/report.en.md) explain these limits in detail.

## What was searched

| Component | Recorded scope |
|---|---|
| Frozen MWDD catalogue | 163,279 rows |
| MWDD spectrum acquisition | 5,548 catalogue objects, primarily Q/Z types and comparison targets; 8,505 records |
| Direct SDSS acquisition | 1,343 Q/Z observations plus 54 DA/DB/DC controls; 1,397 FITS spectra |
| Combined screen | **9,902 spectrum records**, with object and observation overlap |
| Format and wavelength eligibility | 9,023 records |
| Ordinary controls | 18 DA, 18 DB and 18 DC observations; all 54 below distance 0.01, maximum 0.00671 |

MWDD contains 8,502 numerically distinct spectra among its 8,505 records, and the direct SDSS acquisition can repeat observations also hosted by MWDD. The Q/Z emphasis and incomplete archive coverage prevent an estimate of the fraction of all white dwarfs with these colours. Counts and definitions are retained in [screen_summary.json](results/screen_summary.json).

## Reproduce the principal results

Use **Python 3.12**. From a terminal with Git and Python 3.12 installed:

```bash
git clone https://github.com/dj-thank/pale-yellow-green-white-dwarf-candidate.git
cd pale-yellow-green-white-dwarf-candidate
python3.12 -m venv .venv-colour
.venv-colour/bin/python -m pip install -r requirements-core.txt
.venv-colour/bin/python scripts/verify_reproduction.py --with-controls
```

On Windows, use the equivalent environment interpreter, `.venv-colour\Scripts\python.exe`, and a Python 3.12 installation when creating the environment.

After dependencies are installed, the verification runs **without downloading astronomical data**. It checks source hashes and original-to-parsed arrays, recalculates the four DESI colours, validates the included Gaia mean and full-covariance products, and recomputes all **54 raw SDSS controls**. It explicitly prevents network access in the scientific verification step.

The compact verifier begins from the included Gaia reconstruction products; it does not rebuild the Gaia basis calibration or rerun the full survey. The original coefficients and deeper reconstruction instructions are in the [Gaia audit](mwdd/gaia_validation/README.md). DESI uncertainty simulations are also a separate calculation. The faster command without `--with-controls` checks the archived control results only and labels that distinction.

See [reproducibility.en.md](docs/reproducibility.en.md) for numerical tolerances, environment details and the meaning of a passing check. Passing establishes consistency of the committed computation, not astronomical novelty or freedom from instrumental systematics.

### Optional: rerun the full frozen screen

The complete 9,902-record calculation can be rerun from the included frozen manifests. The download step may retrieve approximately 2 GB of public spectra and requires archive access; it verifies every raw-file SHA256 before accepting it.

```bash
.venv-colour/bin/python download_frozen_spectra.py --workers 4
.venv-colour/bin/python run_full_screen.py
```

This path reads the included compressed input and photometry manifests through `project_io.py`; it does not require an omitted bulk MWDD catalogue. It reproduces the **frozen selection**, rather than selecting a new sample from today's catalogue. The full rerun creates uncompressed result tables alongside the preserved compressed snapshots and updates its summary. Use a separate checkout if you want to keep the compact working directory unchanged. No full download is needed for the offline principal-result verification above.

## Reports, notebooks and data

| Resource | Contents |
|---|---|
| [English report](docs/report.en.md) · [日本語報告書](docs/report.ja.md) | Complete methods, measurements, interpretation and limitations |
| [English notebook](white_dwarf_colour_research.ipynb) · [日本語ノートブック](white_dwarf_colour_research.ja.ipynb) | Executed calculations, tables and figures; English is the default notebook |
| [Headline table](results/headline_candidates.csv) | Four representative DESI+Pan-STARRS estimates and provenance |
| [Candidate validation](results/candidates/validated_colours.csv) | Calibration alternatives and conditional intervals |
| [Complete spectrum screen](results/all_spectra_screen.csv.gz) | All 9,902 records and quality flags; compressed CSV |
| [Exploratory object ranking](results/all_object_candidates.csv.gz) | Candidate prioritization, not confirmed discoveries |
| [Frozen MWDD inputs](results/screen_input_mwdd.json.gz) · [Frozen SDSS inputs](results/screen_input_sdss.json.gz) | Exact input records for the full screen |
| [Prior-literature audit](novelty/novelty_evidence.csv) | Identity checks, source evidence and limits on novelty |
| [Swan contamination audit](novelty/swan2026_candidate_audit.json) | Original candidate rows, source URLs, hashes and interpretation |
| [Data availability and reuse](docs/data-availability.md) | Included inputs, upstream archives, provenance and source-specific terms |
| [Acknowledgments](ACKNOWLEDGMENTS.md) · [Bibliography](docs/references.bib) | Original survey, catalogue, model and software attribution |

Selected source spectra, Gaia coefficients, covariance products and control data support the compact reproduction. The complete original spectrum cache is approximately 2 GB and is not duplicated wholesale in Git. Full-sample results and frozen manifests are retained. The documented acquisition scripts can retrieve the remaining public inputs and check their recorded hashes; an upstream change must be treated as a new input version, not silently substituted.

## Attribution, assistance and citation

Observations and their reductions belong to **DESI, ESA/Gaia/DPAC, SDSS and Pan-STARRS** and their teams. MWDD and CDS/SIMBAD/VizieR supplied catalogue access and provenance. The colour framework and comparison measurements are credited to **Hollands et al. (2026)**; classifications, atmosphere models and contamination analyses are credited to **Kilic, Vincent, Swan and their coauthors**, as documented in the report. CIE supplied the standard-observer reference data, and GaiaXPy supplied the native reconstruction tools. Full credits and source-specific notices are in [ACKNOWLEDGMENTS.md](ACKNOWLEDGMENTS.md).

**Shota Moriwaki** initiated and maintains this project. Acquisition, code development and execution, numerical checks, literature comparison and drafting were performed with **OpenAI ChatGPT assistance**. ChatGPT is disclosed as a tool, not a scientific author. This note has not been peer reviewed, and no institutional affiliation or endorsement by the cited authors or surveys is asserted.

If you use the analysis, cite this repository at the version or commit used and cite the underlying papers and datasets relevant to your work. [CITATION.cff](CITATION.cff) provides machine-readable citation metadata. A plain citation is:

> Moriwaki, Shota (2026). *Additional white dwarf colour candidates from public spectra*. Version 0.1.0. Public-data research note and reproducibility code. https://github.com/dj-thank/pale-yellow-green-white-dwarf-candidate

## Licences and contributions

Original project **code is licensed under Apache-2.0**, preserving the repository's [LICENSE](LICENSE). Original explanatory **prose is licensed under CC BY 4.0**. Third-party data, figures, reference tables and dependencies retain their own terms; these project licences do not relicense them. In particular, the unchanged CIE table retains **CC BY-SA 4.0**. Consult [LICENSES/README.md](LICENSES/README.md) and the [data-availability note](docs/data-availability.md) before reusing material from different sources.

Corrections, reproducibility reports and documented candidate follow-up are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for the evidence needed for a useful scientific change and [CHANGELOG.md](CHANGELOG.md) for version history.
