# Independent identity, prior-art and physical interpretation audit

Audit date: 2026-10-18. This document supports the main public-spectrum colour search. It does not replace its photometric calibration, uncertainty analysis or sample accounting.

## What is potentially new

The promising objects are **known white dwarfs** with published spectra and atmosphere fits. The new work is the reproducible calculation and verification of their human-vision chromaticity from those public spectra. It is not discovery of a previously unknown astronomical object, a new element, a new atmospheric mechanism, or a new measurement of their temperature or elemental abundance.

All six deeply audited candidates are absent from the 236 unique named objects in Tables 3–6 of Hollands et al. (2026), *Any colour you like: The diverse chromaticities of white dwarfs*. Their identities were resolved through SIMBAD using the full Gaia source IDs and checked by position, not only by matching short names. All six also fail to match the complete 231-object Hollands et al. (2017) DZ parent catalogue. One candidate, LP616−53, was subsequently downgraded because the local-field check identified a concrete blending risk.

| Candidate | Gaia DR3 source ID | Nearest entry in Hollands2026 | Separation | Existing physical interpretation |
|---|---|---|---:|---|
| WDJ091336.37+443405.41 | 818833831355548928 | WD J085626.95+451337.01 | 11190.823 arcsec | Cool DZ; broad metal absorption |
| WDJ132312.76−012923.67 | 3638333660492606976 | WD J132144.04−023751.47 | 4317.696 arcsec | Tentative DZ:; atmosphere parameters uncertain |
| WDJ132942.69+003336.60 | 3711047662972690688 | WD J133359.84+001655.03 | 3985.096 arcsec | DQ in DESI; strong Swan bands |
| WDJ140155.42+390326.47 | 1496016553207149952 | WD J135516.62+363612.70 | 10017.431 arcsec | DQ; strong Swan bands |
| WDJ042944.71−035422.00 | 3204436719718449280 | WD J041521.80−073929.20 | 18660.615 arcsec | DZ; blue suppression and metal lines |
| WDJ125858.25+010632.45 / LP616−53 | 3690311908759604608 | WD J130009.06+032841.06 | 8594.395 arcsec | DZ in a close visual pair; downgraded |

Positions used here are SIMBAD J2000 ICRS positions. Small differences from the main pipeline's nearest-separation numbers arise because it uses later-epoch Gaia positions. No epoch was invented for the coordinate-encoded designations in the comparison paper. The separations are large enough that normal proper motions cannot turn any of these six into one of those entries.

Source: [Hollands2026](https://arxiv.org/html/2610.18966v1); [published version](https://academic.oup.com/rasti/article/doi/10.1093/rasti/rzag069/8914458); [Hollands2017 catalogue documentation](https://cdsarc.cds.unistra.fr/ftp/J/MNRAS/467/4970/ReadMe).

The full-text review includes Kilic2020, Kilic2025, Kilic2026, Vincent2023, Vincent2024 and Swan2026. These surveys discuss spectral classification, photometric passband colours, and atmosphere parameters. The retrieved texts do not report CIE chromaticity, sRGB or human perceived-colour quantities for these objects. Occurrences of the word *green* refer to plotting colours, image channels or author/survey names; they are not prior claims that the stars appear green. Whole-word searches were used so that “CIE” inside “efficiency” is not a false hit.

This establishes a bounded prior-art result. It does **not** prove global priority. SIMBAD is incomplete, new references may not yet be indexed, full-text search can miss supplements, and another person may already have computed the same quantity. Therefore the warranted phrase is “new colour candidates found in this analysis, absent from the comparison paper”, with “previously unreported” qualified by the scope of the literature check. A universal “world first” claim is not established.

## J0913+4434: independent physical and numerical checks

The Gaia ID resolves to SDSS J091336.38+443405.4 and WDJ091336.37+443405.41. Kilic2026 table1 already gives DZ, Teff=4662±32 K, logg=8.010±0.041, M=0.575±0.035 solar masses, log(H/He)=−2.0 and log(Ca/He)=−9.12. These are prior fitted quantities. Vincent2024's Gaia XP analysis also provides an earlier DZ classification and parameter estimate, under a fixed metal-abundance model.

The published model-fit figure is independently archived at [Zenodo DOI 10.5281/zenodo.20775938](https://doi.org/10.5281/zenodo.20775938), file `allfitsDZ.pdf`, page 321 (one-based). The page was rendered and visually inspected. Its exact ID and 2021-11-01 12:42:31.161312 DESI observation match the public spectrum analysed here. The existing model qualitatively reproduces the broad depression near Na D and the suppression of blue flux. The plot uses Fν, whereas the human colour integration requires Fλ; these slopes must not be compared without conversion.

The metal-analysis method in [Kilic2026](https://arxiv.org/abs/2606.25377), Section “Metal-Line White Dwarfs”, fits Ca/He or Ca/H and assumes CI-chondritic ratios for the other heavy elements. The authors explicitly note that separate abundance fitting could improve individual spectra but is not performed for this large sample. Thus the fit supports a photospheric absorption interpretation; it does not constitute a separately measured sodium abundance, a crust-composition discovery, or proof of a magnetic field.

An independent script, `audit_j0913_spectrum.py`, integrates the same public spectra on their native wavelength grids. It does not import the main colour pipeline. It weights Fλ by CIE1931 two-degree matching functions, retains signed noise samples, uses trapezoidal wavelength widths, transforms XYZ to linear sRGB, scales all channels together, and then applies the sRGB transfer function. The Planckian locus extends to 10^8 K and is checked against the Rayleigh–Jeans endpoint.

| Input | x | y | sRGB display patch | Distance from CIE1960 Planckian locus | (G−R)/G in linear RGB |
|---|---:|---:|---|---:|---:|
| DESI raw | 0.339152 | 0.387021 | #F3FFC5 | 0.019083 | 0.100507 |
| DESI narrow-line interpolation | 0.339309 | 0.386420 | #F4FFC6 | 0.018756 | 0.094753 |
| Gaia XP raw | 0.345357 | 0.392866 | #F7FFBF | 0.019255 | 0.068729 |

These are **raw-spectrum independent-check values**, not the final photometrically anchored values in the main report. Final reported values should come from one explicitly stated calibration choice and include its sensitivity tests. The independently obtained raw colour lies in a pale yellow-green region. It should not be illustrated as saturated emerald green.

Narrow-line interpolation uses 5565–5588, 5885–5902, 6292–6308 and 6355–6372 Å. It is only a sensitivity experiment; the broad stellar trough is preserved. Applying those same intervals to Gaia XP is not a claim that Gaia suffers terrestrial airglow. The XP spectrum has conspicuous ringing in its noisy blue and red wings, and its covariance is not present in the downloaded MWDD sample. Its agreement with DESI is therefore valuable corroboration but must not be treated as a high-precision independent flux-calibration standard.

A subsequent Gaia DR3 field check found a red background neighbour, Gaia DR3 818833831355548800, 5.342 arcsec from J0913 at epoch2016.0. Its G=19.740602 and parallax=2.0129 mas differ from the target's G=19.619797 and parallax=12.7362 mas. The target has four BP and four RP transits flagged as blended, out of48 listed in each band, with zero flagged as contaminated; RUWE=0.992. This is a specific caveat for Gaia XP corroboration and should accompany it. It does not by itself invalidate the independent ground-based spectrum. These neighbour and target source IDs differ only in their last digits and must always be stored as strings or64-bit integers, never floating-point values.

The mean flux from 5750–6050 Å, divided by a local linear reference through broad sidebands near 5450 and 6450 Å, is 0.587 in DESI and 0.608 in XP. This is a simple flux-depression diagnostic, not a sodium equivalent width or abundance measurement. The sidebands can themselves contain opacity.

As a second diagnostic, artificially replacing the 5500–6300 Å trough with a line between adjacent broad sidebands changes the DESI display from pale green to #FFF2B2, with G−R changing sign. The distance from the Planckian locus remains about 0.0131, which illustrates why “positive Duv” and “green” are different statements: the altered spectrum is still unusual but yellow. Changing the replacement window gives the same sign reversal. This experiment holds the rest of the observed spectrum fixed and is **not a physical sodium-removal atmosphere model**.

## Other audited candidates

### J1323−0129

Its tentative DZ classification and atmosphere fits already exist in [Kilic2025](https://arxiv.org/abs/2412.04611), table2, and [Kilic2026](https://arxiv.org/abs/2606.25377), table1. The earlier values are Teff=4262±34 K, logg=7.784±0.054, M=0.445±0.040 solar masses and log(Ca/He)=−9.94. The newer fit gives Teff=3648±16 K, logg=7.381±0.061, M=0.268±0.030 and log(Ca/He)=−11.87, with log(H/He)=−1.0. This much larger inter-model change than either formal error is a concrete reason not to overinterpret the physical parameters. It does not invalidate a spectrum-derived colour if that colour passes calibration checks independently.

The corresponding Zenodo fit is `allfitsDZ.pdf`, page 572. The plotted red model has a broad depression around 5890 Å and strong blue suppression. The main pipeline's displayed #FFE... colour is yellow, not green. Its positive offset from the blackbody sequence should not be renamed green solely because the sign matches that of J0913.

### J1329+0033

SIMBAD resolves this object to the historical identifier 2QZ J132942.7+003340. Its Gaia XP catalogue classification is uncertain DA:, while Kilic2026's higher-resolution DESI analysis identifies it as DQ. The latter gives Teff=5592±22 K and log(C/He)=−6.14. The published atmosphere fit is `allfitsDQ.pdf`, page 375. The broad Swan-band pattern is clear and qualitatively reproduced by the red model. One narrow positive spike near 5800 Å merits a robustness check; it does not explain the multiple broad molecular troughs.

### J1401+3903

This object is DQ in both the Vincent2024 and Kilic2026 catalogue provenance. The Kilic2026 table gives Teff=5593±35 K and log(C/He)=−6.00. `allfitsDQ.pdf`, page 404, shows the broad Swan bands matched by the prior atmosphere model. Its measured pink-colour status still depends on the main pipeline's photometric and repeat-spectrum checks.

### J0429−0354

Gaia DR3 3204436719718449280 resolves to WDJ042944.71−035422.00. Kilic2026 table1 already gives DZ, Teff=5288±33 K, logg=7.924±0.028, M=0.524±0.023 solar masses, log(Ca/He)=−9.56 and log(H/He)=−6.0. The MWDD provenance also records an earlier DZ classification and Teff=5527±103 K from Vincent2024. The published DESI model-fit panel is `allfitsDZ.pdf`, page174, visually verified to match the GaiaID and observation timestamp2022-02-19 02:29:34.378368. It qualitatively reproduces blue suppression and the metal-line features. This supports an ordinary photospheric explanation for the measured non-blackbody colour; its physical parameters are prior work.

The Gaia DR3 cone query returns only the target within10arcsec of its position. Its RUWE=0.998, IPDfmp=0 and duplicated-source flag=0; there are30 BP and30 RP transits, with one in each band marked blended and none marked contaminated. This resolves the obvious catalogued-neighbour concern for this object. It does not exclude unresolved or fainter sources absent from Gaia.

### J1258+0106 / LP616−53: downgraded

The known aliases include LP616−53, NLTT32489, LSPM J1258+0106S, WDS J12589+0107B and LDS4303B. Kilic2026 has a DZ fit, Teff=5347±92 K, logg=8.325±0.051, M=0.781±0.047 and log(Ca/He)=−9.23; its table's log(H/He)=−30 is the grid's effectively H-free convention, not a precise measured hydrogen abundance. The published panel is `allfitsDZ.pdf`, page551, and is consistent with a metal-polluted atmosphere.

SIMBAD resolves the other visual component, LDS4303A, to LP616−54 / Gaia DR3 3690311908760279808. It is only2.340034arcsec away atJ2000, with G=17.252741 versus18.404011 for LP616−53, corresponding to2.887 times its GaiaG flux. Their parallaxes and proper motions are similar. A Gaia DR3 cone query independently resolves the components at2.301519arcsec separation at epoch2016.0 and lists a third G=19.404352 source, Gaia DR3 3690311908759604480, at1.286610arcsec. LP616−53 has five of seven BP and five of six RP transits flagged as blended. Those flags are not contamination fractions, but the nearby light sources are a concrete reason to downgrade the otherwise interesting colour candidate. There has been no spectral decontamination or proof that the whole green tint is an artefact.

Source records are `primary_papers/simbad_lds4303a.txt`, `primary_papers/simbad_3690311908759604608.txt`, and the exact-query Gaia responses under `primary_papers/gaia10arcsec_*.tsv`. `gaia_neighbour_audit.json` records their query URLs and computed separations. The [Gaia DR3 catalogue at CDS](https://vizier.cds.unistra.fr/viz-bin/VizieR?-source=I/355/gaiadr3) is the source of local-field measurements. J1329 was also checked: only the target is catalogued in its10arcsec cone.

## Latest catalogue check: Swan2026 contamination estimates

[Swan et al.2026, *The DESI Data Release 1 white dwarf catalogue*](https://arxiv.org/html/2609.04314v1), submitted on 2026-09-03, already contains all six exact Gaia source IDs. Its official version1.0 catalogue, external-data table and individual-exposure table were downloaded from the [authors' Warwick repository](https://cygnus.astro.warwick.ac.uk/phsdaj/WhiteDwarfs/). Gaia IDs were preserved as strings, then the exact WDJname linked the three tables. The extraction retains original rows, URLs and SHA256 hashes. The retrieved paper has no matches for CIE, chromaticity/chromaticities, sRGB, perceived, pink or human eye; its 22 whole-word *green* matches are image-channel labels or author names. The absence of those quantities is a bounded statement about this source, not a claim to comprehensive scientific priority.

Section6.6 supplies estimates of neighbouring-star flux entering the DESI aperture. The table below reports the authors' **neighbour flux divided by target flux**, without multiplying by100. It is not the neighbour's share of total collected light.

| Candidate | DESI flux ratio | Pan-STARRS flux ratio | SDSS flux ratio | Gaia BP/RP flux ratio | DESI seeing, arcsec | Swan spectral class |
|---|---:|---:|---:|---:|---|---|
| J0913+4434 | 3.125×10⁻¹⁴ | 1.052×10⁻⁵ | 5.347×10⁻⁶ | 3.036×10⁻⁵ | 0.8095 | DZ |
| J0429−0354 | 0 | 1.006×10⁻²⁷ | 6.994×10⁻²⁶ | 3.080×10⁻²⁹ | 1.1572 | DZ |
| J1329+0033 | 8.293×10⁻³⁷ | 3.658×10⁻²⁴ | 2.517×10⁻²² | 1.634×10⁻²⁵ | 1.8912;0.9576 | DQ |
| J1323−0129 | 0 | 2.471×10⁻³⁰ | 2.149×10⁻²⁹ | 2.105×10⁻³¹ | 1.1584 | DZ |
| J1401+3903 | 0 | 0 | 0 | 0 | 1.0303 | DQ |
| J1258+0106 / LP616−53 | 0.03072 | 0.76528 | 0.70639 | 0.85999 | 1.5455 | WD+MS |

The official estimates support the isolation of the four principal candidates under this model. J0913's 5.34arcsec red Gaia neighbour is included in the broader neighbourhood calculation, and its estimated DESI contribution is negligible in the actual good-seeing exposure. Its Gaia transit-blending flags and possible scan-angle effects remain specific caveats for the XP corroboration.

LP616−53, already downgraded after the independent companion search, also has substantial published contamination estimates. Its DESI ratio is3.072% of the target flux, while the Pan-STARRS, SDSS and Gaia BP/RP ratios are approximately76.5%,70.6% and86.0%. Swan classifies the observed system WD+MS, with classification confidence0.611. This is strong additional reason to exclude its colour from clean intrinsic-white-dwarf claims. It does not prove that the entire inferred tint is caused by contamination, and no spectral deblending was attempted.

The authors use Gaia DR2/DR3 neighbours within60arcsec, propagate their proper motions to each exposure, assume a0.75arcsec-radius circular fibre and a Gaussian PSF whose FWHM is the measured seeing, and weight multiple exposures by effective exposure time. GaiaG supplies the approximate flux ratio. For photometry, fixed survey epochs and assumed apertures/PSFs are used; Gaia BP/RP uses a rough circular approximation despite its actual dispersed rectangular windows and varying scan angles. Accordingly, numerical zero and very small ratios mean negligible contribution **within that calculation**, not a measured zero or rigorous upper bound. Gaussian wings, diffraction spikes, unlisted sources and fibre-to-fibre spectrograph cross-talk are not fully covered. The paper itself gives an example of a bright star2arcmin away causing effects missed by the metric.

The J1329 catalogue entry has two DESI exposures and a Z-arm masked fraction0.5031. The MWDD spectrum used in the colour pipeline may be an individual exposure, so the official coadd's mask fraction must not replace the validity/coverage mask of the actual analysed spectrum. The underlying observation identifiers and seeing for both exposures are retained in the extraction.

Section7.8.7 is a useful instrumental caution. X-Shooter confirmed broad Na-D-like absorption in WDJ034301.05−011401.58 but did not confirm the DESI feature in WDJ220022.42−061430.97. In the latter, the feature appears in two consecutive DESI exposures; the paper leaves its cause unresolved. Thus repeat observations from one setup do not alone establish an intrinsic photospheric feature. The current candidates' multi-instrument agreement and photometric calibration checks provide separate evidence, but this search does not claim a new sodium abundance or atmospheric mechanism. Swan's generic H/He fit parameters were not used to reclassify any human colour.

## Exact bibliographic identifiers

- Vincent et al.2024: *Classification and parameterisation of a large Gaia sample of white dwarfs using XP spectra*, A&A682,A5; [arXiv2308.05572](https://arxiv.org/abs/2308.05572); [journal DOI10.1051/0004-6361/202347694](https://doi.org/10.1051/0004-6361/202347694).
- Kilic et al.2026: *A Detailed Model Atmosphere Analysis of Cool White Dwarfs in DESI DR1*, ApJ1006,issue2; [arXiv2606.25377v2](https://arxiv.org/abs/2606.25377); [journal DOI10.3847/1538-4357/ae825f](https://doi.org/10.3847/1538-4357/ae825f). The journal DOI, title, volume and publication date2026-07-30 were verified against publisher-deposited [Crossref metadata](https://api.crossref.org/works/10.3847/1538-4357/ae825f), preserved in `primary_papers/kilic2026_crossref.json`.
- Swan et al.2026: *The DESI Data Release 1 white dwarf catalogue*; [arXiv2609.04314v1](https://arxiv.org/html/2609.04314v1); official catalogue version1.0, external-data and exposure tables at the [authors' repository](https://cygnus.astro.warwick.ac.uk/phsdaj/WhiteDwarfs/).
- Kilic and Bergeron model-fit figures: [Zenodo DOI10.5281/zenodo.20775938](https://doi.org/10.5281/zenodo.20775938).

## Methodological requirements for the final research result

1. Integrate energy flux per wavelength, not Fν, photon counts or continuum-normalised spectra. Each pixel's wavelength interval matters.
2. Specify the observer, wavelength coverage, display white point and common scaling. Preserve pre-clipping linear RGB and out-of-gamut flags.
3. Use the shortest distance to a sufficiently extended Planckian locus. A finite high-temperature endpoint creates artificial blue outliers. The paper's distance threshold of 0.01 is an operational selection, not a universal perceptual or significance threshold.
4. Do not call every positive-Duv object green. Report numerical chromaticity, the actual patch and a conservative colour description. Correlated colour temperature for an outlier is not its physical effective temperature.
5. Anchor spectra to appropriate measured photometry with the correct survey bandpasses. A first-order magnitude tilt is interpretable; unconstrained higher-order corrections can manufacture unusual colours. Reject implausible photometry and report raw versus corrected values.
6. Statistical pixel-noise simulations do not capture coherent flux-calibration slope errors, photometric errors or Gaia XP covariance. Repeat instruments, alternative photometric anchors and smooth tilt stress tests resolve these different risks.
7. Remove narrow sky/cosmic-ray contamination with care while preserving broad stellar absorption. Do not mask the entire Na D trough as terrestrial sodium.
8. A search of thousands of spectra is exploratory. Do not convert one small formal error into a global discovery significance without selection effects and calibration uncertainty. Candidate ranking and follow-up priorities are valid outcomes.
9. These colours describe a photopic standard-observer rendering of the received spectrum. They are not a claim that an unaided person on Earth sees a coloured stellar disc. Nearby white dwarfs can be observed by telescopes; the limitation concerns unaided-eye brightness and apparent size.

## Reproducible outputs

- `parse_hollands_exclusions.py`: parses the saved comparison-paper HTML; all 238 table entries and 236 unique named objects are preserved.
- `hollands2026_exclusions.csv`, `hollands2026_exclusions_unique.csv`: machine-readable exclusions, aliases and source-table metadata.
- `build_novelty_audit.py`: reproduces the identity matches, table-row matches, bibliography trace and source hashes without network access.
- `candidate_novelty_audit.json`: six candidates, resolved coordinates, aliases, SIMBAD references, exact prior table rows, exclusions, local-field checks and limitations.
- `novelty_evidence.csv`: 49 evidence rows stating what each source establishes and what it does not establish.
- `novelty_source_manifest.json`: local source sizes and SHA-256 hashes.
- `audit_j0913_spectrum.py`, `j0913_independent_color_metrics.json`, `j0913_broad_window_interpolation.json`: independent colour and shape checks.
- `build_neighbour_audit.py`, `gaia_neighbour_audit.json`: reproducible interpretation of the saved Gaia DR3 field queries, preserving full source-ID precision.
- `extract_swan2026_candidates.py`, `swan2026_candidate_audit.json`, `swan2026_candidate_contamination.csv`: reproducible extraction of exact candidate rows, official contamination ratios and exposure seeing, with full provenance and limitations.

Comparison-paper table accounting: Table3 has15 IR-faint objects, Table4 has36 DQs, Table5 has36 DZ model fits for named stars, and Table6 has151 named rows or systems. Two names repeat between tables. The main text's152-star language is not silently substituted for the actual151 table rows; a named binary row may account for the difference, but that explanation was not proven by this audit. Generic model-grid Tables1–2 are not object exclusions.
