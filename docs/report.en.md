# Additional white dwarf colour candidates from public spectra

**Project initiator and maintainer:** Shota Moriwaki  
**Analysis date:** 18 October 2026  
**Status:** Exploratory public-data research note; not peer reviewed.

## Abstract

A reproducible search of public white dwarf spectra identifies **WD J0913+4434** and **WD J0429−0354** as additional candidates for pale yellow-green visible colours. The analysis processes 9,902 spectrum records, including repeated observations and overlapping archive holdings, with deliberate emphasis on carbon-bearing and metal-polluted white dwarfs. Integrating DESI spectra recalibrated against Pan-STARRS g, r and i photometry gives signed distances from the Planckian locus of **+0.01901** and **+0.01281**, respectively, in CIE 1960 u,v. Their corresponding normalized sRGB values are **#F1FFC9** and **#F8FFDC**. Reconstruction from the original Gaia DR3 XP coefficients supports mean colours on the same side of the thermal locus, but propagation of the coefficient covariance shows that Gaia alone does not securely establish a green colour label.

The search also retains **WD J1329+0033** as a pink candidate and **WD J1323−0129** as a candidate with an unusual yellow colour. All four are known stars with previously published classifications or atmosphere analyses. They are absent from the 236 unique named entries in the comparison tables of Hollands et al. (2026). Within the inspected literature, no previous CIE chromaticity or sRGB measurements were found for these candidates. The contribution is a new, documented colour analysis of existing public spectra. Global scientific priority, a new atmospheric mechanism, and a definitive prediction of subjective appearance are not established.

![Computed colour patches for the principal candidates](../figures/candidate_colours.png)

*These patches are calculated display colours, not photographs. A common scale factor sets the largest linear RGB channel to unity before sRGB encoding. They do not reproduce a star's apparent brightness or surface brightness.*

## 1. Motivation and scope

[Hollands et al. (2026)](https://doi.org/10.1093/rasti/rzag069) calculated human-vision chromaticities for white dwarfs and showed how strong atmospheric absorption can produce colours away from the usual thermal sequence. That work supplies the scientific motivation, comparison objects and colour-distance convention for this search. It already establishes the underlying possibility of unusually coloured white dwarfs; the present analysis examines additional public spectra for further examples.

A spectrum's astronomical colour index, such as g−r, is not itself a human colour measurement. Here, colour means the chromaticity obtained by integrating a spectral energy distribution against the **CIE 1931 2° standard observer** functions, followed by a specified display conversion. DQ white dwarfs exhibit carbon features, while DZ white dwarfs exhibit metal absorption. Their classifications and the interpretation of their atmospheric features are prior work, principally represented here by [Kilic et al. (2026)](https://doi.org/10.3847/1538-4357/ae825f), [Vincent et al. (2024)](https://doi.org/10.1051/0004-6361/202347694) and [Swan et al. (2026)](https://arxiv.org/html/2609.04314v1).

The analysis asks a narrower question: **which additional known white dwarfs have public spectra that imply unusual human-vision chromaticities, and how well do those inferences survive data-quality, calibration, uncertainty and prior-literature checks?**

## 2. Principal measurements

For a consistent comparison, every representative measurement below uses a **DESI spectrum adjusted to Pan-STARRS g, r and i photometry**. The intervals are conditional Monte Carlo intervals described in Section 4; they are not discovery probabilities or complete uncertainty budgets.

| Candidate | Gaia DR3 source_id | Colour description | CIE x | CIE y | sRGB | Duv | Conditional 95% Duv interval |
|---|---|---|---:|---:|---|---:|---|
| WD J0913+4434 | 818833831355548928 | Pale yellow-green | 0.33548 | 0.38355 | #F1FFC9 | +0.01901 | +0.01695 to +0.02112 |
| WD J0429−0354 | 3204436719718449280 | Pale yellow-green | 0.32845 | 0.36353 | #F8FFDC | +0.01281 | +0.01197 to +0.01365 |
| WD J1329+0033 | 3711047662972690688 | Pink | 0.35245 | 0.31521 | #FFC1CF | −0.02265 | −0.02481 to −0.02048 |
| WD J1323−0129 | 3638333660492606976 | Unusual yellow | 0.40830 | 0.45014 | #FFE86A | +0.02348 | +0.02094 to +0.02597 |

The full-precision representative values, source URLs and hashes are in [headline_candidates.csv](../results/headline_candidates.csv). Other calibration choices and uncertainty summaries are in [validated_colours.csv](../results/candidates/validated_colours.csv). Hexadecimal values are useful for reproducing the chosen display convention; their last digit should not be interpreted as physical measurement precision.

**Positive Duv does not mean green.** It denotes one side of the Planckian locus in the adopted coordinates. J1323−0129 provides a direct example: it has the largest positive Duv in this table while its display colour is yellow. Channel ordering and human colour names also require separate consideration.

## 3. Public data and selection

### 3.1 Archive acquisition

The primary source is the [Montreal White Dwarf Database, MWDD](https://www.montrealwhitedwarfdatabase.org/), described by [Dufour et al. (2017)](https://arxiv.org/abs/1610.00986). The frozen catalogue contained 163,279 rows. Selection included catalogue spectral types containing Q or Z with at least one listed optical spectrum, together with a small set of known-colour comparison objects and GD 229. This is a targeted sample, not a volume-complete or magnitude-complete census.

An additional acquisition used the public [Kepler et al. (2019) SDSS DR14 classification catalogue](https://doi.org/10.1093/mnras/stz960), distributed through [CDS](https://cdsarc.cds.unistra.fr/ftp/J/MNRAS/486/2169/), to obtain spectra directly from SDSS. This route adds a separate archive-retrieval check; a spectrum downloaded through SDSS can still be the same observation as one hosted by MWDD.

| Stage | Scope or result |
|---|---|
| Frozen MWDD catalogue | 163,279 rows |
| MWDD acquisition | 5,548 selected catalogue objects; 8,505 spectrum records |
| Direct SDSS acquisition | 1,343 Q/Z observations plus 54 controls; 1,397 FITS spectra |
| Combined scan | 9,902 spectrum records, with observation and object overlap |
| Eligible for the numerical screen | 9,023 records |
| Photometrically recalibrated records | 4,218 |
| Direct SDSS photometry recovered | 1,390 observations |
| Ordinary comparison spectra | 18 DA, 18 DC and 18 DB observations |

These counts are preserved in [screen_summary.json](../results/screen_summary.json), the [MWDD acquisition summary](../mwdd/acquisition_summary.json) and the SDSS manifests. The 8,505 MWDD records contain 8,502 numerically distinct wavelength/flux arrays. A 5″ positional association was used when merging archive identifiers; high proper motion and unresolved aliases can leave duplicate object entries. Neither 9,902 records nor the number of ranked identifiers is a count of independent stars or discoveries.

Exact retrieval URLs and SHA256 digests identify the analysed versions. The frozen input lists are [screen_input_mwdd.json.gz](../results/screen_input_mwdd.json.gz) and [screen_input_sdss.json.gz](../results/screen_input_sdss.json.gz). Full results, including failed or uncalibrated cases, remain in [all_spectra_screen.csv.gz](../results/all_spectra_screen.csv.gz).

### 3.2 Flux conventions and numerical eligibility

The colour calculation uses **energy flux density per unit wavelength, Fλ**. Wavelength arrays are stored in ångströms and converted to nanometres for CIE integration. A wavelength-independent change of flux units cancels from chromaticity; confusing Fν with Fλ would change the result and is not harmless.

SDSS and DESI provide spectra in an Fλ convention. Legacy MWDD exports with unverified conventions, including possible continuum-normalized or Fν spectra, are retained as acquisition records but do not qualify as discovery evidence in the main screen. For the two green candidates, direct comparison with GaiaXPy independently verifies that the MWDD XP fluxes retain GaiaXPy's Fλ units of W m⁻² nm⁻¹, although the MWDD wavelength column is in ångströms. See the [native Gaia audit](../mwdd/gaia_validation/README.md) and the [SDSS spectrum documentation](https://www.sdss4.org/dr17/spectro/spectro_basics/).

Non-finite samples and samples with invalid supplied inverse variance are removed. Wavelengths are sorted and duplicate wavelengths handled. Negative noisy flux samples are retained rather than clipped to zero. Narrow ground-based airglow windows around 5577, 5890/5896, 6300 and 6364 Å are omitted, with quadrature bridging the short gaps. This treatment is not applied to the space-based Gaia spectra and does not excise the broad stellar absorption near Na D.

Screen eligibility requires a verified source convention, sufficient wavelength extent, more than 99.5% coverage of each unweighted CIE matching-function integral, and no retained visible wavelength gap of 150 Å or more. The matching-function coverage criterion is a numerical screen, not a guarantee that an arbitrary missing piece contributes less than 0.5% of the true stellar flux. Principal spectra cover essentially the full 360–830 nm integration interval. The implementation and flags are in [colour_pipeline.py](../colour_pipeline.py) and [rank_candidates.py](../rank_candidates.py).

## 4. Colour calculation, calibration and uncertainty

### 4.1 CIE integration and the thermal reference

The official [CIE matching-function table](https://doi.org/10.25039/CIE.DS.xvudnb9b) spans 360–830 nm at 1 nm intervals. Its published MD5 checksum, `17cca777db64b17170f06f67ce9d3ab7`, matches the retained file. The functions are linearly interpolated to the retained spectral wavelengths and integrated by trapezoidal quadrature:

$$
(X,Y,Z)=k\int_{360\,\mathrm{nm}}^{830\,\mathrm{nm}}
F_\lambda(\lambda)\,[\bar{x}(\lambda),\bar{y}(\lambda),\bar{z}(\lambda)]\,d\lambda.
$$

The arbitrary common positive scale k does not affect chromaticity. No extra photon-counting factor belongs in this energy-based CIE integral. The normalized coordinates are x = X/(X+Y+Z) and y = Y/(X+Y+Z). CIE 1960 coordinates are

$$
u=\frac{4x}{-2x+12y+3},\qquad
v=\frac{6y}{-2x+12y+3}.
$$

The thermal reference is computed using the same matching functions for blackbodies over 1,000–10⁸ K, including the Rayleigh–Jeans limiting spectrum. This avoids falsely treating a very hot thermal spectrum as an outlier merely because a temperature grid ended too early. Duv is the signed shortest distance to the sampled locus in these coordinates, with the sign determined by the vertical displacement from the nearest locus point. The nearest thermal colour temperature is a geometric reference, not a fitted atmospheric effective temperature.

Following the comparison convention in Hollands et al. (2026), an absolute distance of 0.01 is used as an exploratory threshold. It is not a universal perceptual threshold, a physical boundary between stellar types, or a statistical significance level. The tabulated [Planckian locus](../reference/planckian_locus.csv) makes the reference calculation reproducible.

### 4.2 Display convention and interpretation

XYZ is converted to linear sRGB using the fixed, rounded transformation used by the pipeline, then all channels are divided by the largest channel. The standard piecewise sRGB transfer function and rounding to 8-bit values produce the displayed patches. Any clipping is display-only: chromaticity, distance and ranking use the original XYZ values. All four representative colours lie within the chosen sRGB gamut.

These are standard-observer, photopic calculations with an sRGB/D65 display convention. No chromatic adaptation transform, individual observer model, telescope throughput, atmospheric viewing model or dark-adapted vision model is applied. The spectra are not dereddened in this analysis, so the reported values describe the observed, recalibrated spectral distributions rather than an inferred unobscured stellar surface. Apparent hue also depends on luminance, surroundings, adaptation and the display. A faint point source cannot be assumed to look like a bright screen patch. The original comparison paper and the [CIE metadata](../reference/CIE_xyz_1931_2deg.csv_metadata.json) document the standard-observer basis; the limitations of the present rendering follow from the explicit choices above.

### 4.3 Broadband recalibration

Relative spectral calibration is central to this problem. The pipeline computes synthetic AB g, r and i magnitudes with the appropriate SDSS or Pan-STARRS response functions, then fits an overall magnitude offset and a smooth linear tilt in magnitude:

$$
F_{\lambda,\mathrm{cal}}=F_\lambda\,10^{-0.4[a+b(\lambda-620\,\mathrm{nm})/(100\,\mathrm{nm})]}.
$$

Here a changes the overall scale and b is the tilt in magnitudes per 1,000 Å. The fit does not independently reshape individual absorption features. Synthetic photometry uses the passbands' photon-response weighting; this is distinct from the CIE energy integral.

Three valid photometric bands are required. Anchors with reported uncertainty above 0.10 mag are rejected, and a 0.02 mag uncertainty floor is used. Fits requiring an absolute tilt of approximately 0.25 mag per 1,000 Å or larger, or a maximum band residual of approximately 0.15 mag or larger, are rejected from the calibrated screen. Raw results remain labelled separately. Candidate validation compares available SDSS and Pan-STARRS anchors; the main table consistently chooses Pan-STARRS. Direct positive SDSS PSF fluxes are converted to AB magnitudes where available, avoiding inappropriate use of low-signal asinh magnitudes.

The recovered SDSS photometry differed from the earlier catalogue by more than 0.05 mag in 84 band entries across 1,390 observations. Those differences motivated direct source checks rather than uncritical use of the inherited magnitudes. For J0913, the SDSS alternative uses the directly retrieved PSF flux of the clean, deblended child object. Calibration details and source-quality checks are retained in [sdss/](../sdss/).

### 4.4 Conditional DESI uncertainty and stress tests

Each representative DESI result uses **6,000 Monte Carlo draws**, with seed 20261018. Draws perturb supplied spectral errors and the photometric anchors, propagate a first-order refit of the calibration tilt, and integrate the perturbed spectra nonlinearly. The displayed 95% intervals are the 2.5th and 97.5th percentiles of that procedure. If a flux correction multiplies flux by a factor q, inverse variance is divided by q².

This DESI calculation treats the supplied spectral samples as independent. It does not include unknown pixel correlations, unrestricted wavelength-dependent calibration errors, contamination, source variability or a global selection model. The 0.02 mag photometric floor is a practical assumption, not a measurement of every systematic effect. Even if all 6,000 draws have the same channel ordering or exceed the exploratory distance threshold, that is not 100% confidence in a physical discovery.

Checks include changes to narrow sky masking, additional tilts of ±0.05 and ±0.10 mag per 1,000 Å, and smooth 5% curvature perturbations. Their separate outcomes are in [calibration_sensitivity.csv](../results/candidates/calibration_sensitivity.csv); the noise interval is not intended to summarize every stress scenario. For J0913, 80 full nonlinear calibration refits were compared with the linear approximation: the Duv difference had RMS 1.22×10⁻⁶ and maximum 3.60×10⁻⁶, small relative to the reported conditional interval. This validates that approximation locally, not the completeness of the error model. See the [numerical audit](../sdss/linear_mc_audit.json).

## 5. The two pale yellow-green candidates

### 5.1 WD J0913+4434

The full designation is **WDJ091336.37+443405.41**, with aliases including SDSS J091336.38+443405.4. Its Gaia DR3 source ID is **818833831355548928**. A parallax of 12.7362±0.3484 mas gives approximately 78.5 pc, or 256 light-years, by simple inversion. This is not a new distance fit. Kilic et al. (2026) already classify it DZ and give an atmosphere fit near 4,662 K with helium-dominated composition and metal absorption. These quantities belong to the prior analysis.

| Spectrum or calibration choice | sRGB | Duv |
|---|---|---:|
| DESI before broadband tilt correction, after invalid-pixel and narrow-sky treatment | #F5FFC7 | +0.01835 |
| DESI with direct SDSS PSF photometry | #F7FFC6 | +0.01789 |
| DESI with Pan-STARRS photometry | #F1FFC9 | +0.01901 |
| Native Gaia reconstruction, all 55 BP + 55 RP bases | #F7FFBF | +0.01923 |
| Native Gaia reconstruction, recommended 10 BP + 2 RP bases | #F9FFC9 | +0.01635 |

The persistence of the mean colour across these choices is more informative than a single raw hex value. DESI and Gaia also show a broad depression around 589 nm and suppressed blue flux. The previously published atmosphere-model panel, `allfitsDZ.pdf`, page 321 in the [Kilic and Bergeron figure archive](https://doi.org/10.5281/zenodo.20775938), qualitatively reproduces the broad structure. This panel uses the same DESI observation, so it is supporting physical interpretation, not an independent observation.

Kilic et al. fit calcium abundance while fixing other heavy-element ratios to CI-chondritic values in this large-sample analysis. The comparison therefore does not yield a newly measured individual sodium abundance or a new composition for accreted planetary material. A diagnostic experiment artificially replacing the broad trough by a line joining adjacent regions changes the sign of the linear RGB G−R difference and makes the colour more yellow. This demonstrates sensitivity to the spectral shape; it is not a physical atmosphere calculation with sodium removed. The independent numerical experiment is documented in [novelty_methodology.md](../novelty/novelty_methodology.md).

![J0913 spectrum and colour validation](../figures/j0913_validation.png)

The local field contains a red background source approximately **5.342″** away at Gaia epoch 2016.0. Its source ID, **818833831355548800**, differs from the target ID only in the last digits; IDs must remain strings or exact integers. SDSS resolves the pair into separate child objects and marks the target CLEAN=1, although the r-band data carry interpolation/cosmic-ray flags. Gaia reports four blended transits out of 48 in each of BP and RP. The official DESI contamination estimate is small under the Gaussian model discussed in Section 7, but the neighbour and Gaia flags remain relevant qualifications. The source records are in the [local-field audit](../novelty/gaia_neighbour_audit.json) and [J0913 quality summary](../sdss/j0913_quality/quality_summary.json).

### 5.2 WD J0429−0354

The full designation is **WDJ042944.71−035422.00**, Gaia DR3 **3204436719718449280**. Kilic et al. (2026) already classify it DZ and give a model temperature near 5,288 K. Its published metal-bearing atmosphere fit appears in `allfitsDZ.pdf`, page 174 of the same model archive. The atmospheric interpretation is established prior work.

The representative DESI+Pan-STARRS colour is **#F8FFDC**, compared with **#FAFFD7** for the full Gaia basis and **#F7FFD3** for the recommended 4 BP + 2 RP bases. Its mean display colour is closer to white than J0913's. The conditional DESI Duv interval, +0.01197 to +0.01365, lies above the exploratory 0.01 threshold.

The Gaia DR3 query returns only the target within 10″. Direct Pan-STARRS values agree with the inherited photometry. Another Pan-STARRS entry lies about 9.736″ away and is a faint i-only source with two detections. These checks reduce the obvious catalogue-neighbour concern; they cannot exclude unresolved or undetected light. Query details are retained in the [J0429 quality summary](../sdss/secondary_quality/J0429-0354_summary.json).

## 6. Gaia covariance places an important limit on the colour labels

The original ESA **XP_CONTINUOUS** coefficients, formal coefficient errors and within-band correlations were retrieved for both green candidates through [Gaia DataLink](https://www.cosmos.esa.int/web/gaia-users/archive/datalink-products). Spectra were reconstructed with [GaiaXPy](https://gaia-dpci.github.io/GaiaXPy-website/) version 2.1.5. The public MWDD exports match full-basis reconstructions sampled at 361 logarithmically spaced points over 330–1,050 nm to the expected text-rounding precision. They are not the separate ESA XP_SAMPLED product. Exact source URLs and hashes are in the [Gaia source manifest](../mwdd/gaia_validation/source_manifest.json).

For each band, the coefficient covariance is formed from the supplied errors and correlation matrix. It is then propagated through the calibrated basis functions and BP/RP merging weights to the sampled spectrum, and through the linear CIE integral to a 3×3 XYZ covariance. This retains wavelength correlations. BP and RP are treated as independent of each other because their cross-band calibration covariance is not supplied in this calculation.

The direct propagated diagonal reproduces GaiaXPy's flux errors. The audit does not use GaiaXPy's returned packed sampled correlations for inference: for these inputs and the installed version, their truncated reconstruction produced a covariance validation discrepancy, including substantial negative eigenvalues. The untouched returned arrays are retained for investigation. The directly propagated covariance is symmetric and positive semidefinite to floating precision. This is a documented implementation check, not a claim that the upstream cause has been established; the full details are in the [Gaia audit README](../mwdd/gaia_validation/README.md).

Using that covariance, **200,000 correlated XYZ draws** per case give:

| Candidate | Gaia basis choice | Mean Duv ± formal 1σ | Formal 95% Duv interval | Draws with G as largest channel |
|---|---|---|---|---:|
| J0913 | All 55 BP + 55 RP | +0.01923 ± 0.00351 | +0.01236 to +0.02612 | 85.0% |
| J0913 | Recommended 10 BP + 2 RP | +0.01635 ± 0.00327 | +0.00995 to +0.02274 | 77.8% |
| J0429 | All 55 BP + 55 RP | +0.01299 ± 0.00220 | +0.00867 to +0.01730 | 82.3% |
| J0429 | Recommended 4 BP + 2 RP | +0.01493 ± 0.00180 | +0.01141 to +0.01846 | 96.5% |

The recommended counts are Gaia's published relevant-basis counts. They are not GaiaXPy's default, which uses no truncation. Truncation suppresses poorly constrained structure but can introduce bias, and that bias is not included in the formal intervals. Agreement of 1 nm and 2 nm integration was checked; the largest Duv difference was 1.9×10⁻⁵, much smaller than the coefficient uncertainty.

The means corroborate a displacement from the thermal sequence, while the precise channel ordering is less secure. **Gaia alone does not firmly establish that either star should be called green.** The supplied noise model also omits unknown calibration systematics, cross-band calibration correlation and contamination. Further, Gaia and DESI spectra adjusted to the same photometric anchors share calibration information; their conditional probabilities must not be multiplied as independent evidence. The table above uses the native Gaia reconstruction without photometric adjustment.

## 7. Independent catalogue checks for contaminating light

[Swan et al. (2026)](https://arxiv.org/html/2609.04314v1), Section 6.6, provides an exposure-dependent estimate of neighbouring light in DESI fibres and corresponding photometric apertures. Exact Gaia IDs identify all six deeply audited candidates in the authors' [version 1.0 tables](https://cygnus.astro.warwick.ac.uk/phsdaj/WhiteDwarfs/).

The following values are **neighbour flux divided by target flux**, not the contaminant's fraction of total collected light. They are ratios, without multiplication by 100.

| Candidate | DESI ratio | Pan-STARRS ratio | SDSS ratio | Gaia BP/RP ratio | DESI seeing |
|---|---:|---:|---:|---:|---|
| J0913+4434 | 3.125×10⁻¹⁴ | 1.052×10⁻⁵ | 5.347×10⁻⁶ | 3.036×10⁻⁵ | 0.8095″ |
| J0429−0354 | 0 | 1.006×10⁻²⁷ | 6.994×10⁻²⁶ | 3.080×10⁻²⁹ | 1.1572″ |
| J1329+0033 | 8.293×10⁻³⁷ | 3.658×10⁻²⁴ | 2.517×10⁻²² | 1.634×10⁻²⁵ | 1.8912″; 0.9576″ |
| J1323−0129 | 0 | 2.471×10⁻³⁰ | 2.149×10⁻²⁹ | 2.105×10⁻³¹ | 1.1584″ |
| LP616−53 | 0.03072 | 0.76528 | 0.70639 | 0.85999 | 1.5455″ |

The model uses Gaia neighbours within 60″, positions propagated to each exposure, a 0.75″ circular fibre radius and Gaussian PSFs based on measured seeing. Multiple exposures are weighted by effective exposure time. Gaia G supplies an approximate flux ratio. Photometric estimates use assumed survey epochs and PSFs; Gaia BP/RP is only approximately represented by a circular aperture despite its dispersed windows and varying scan angles.

The estimates support low contamination for the principal candidates under those assumptions, including J0913's good-seeing exposure. **They are not upper bounds.** Extended PSF wings, diffraction spikes, unlisted sources and spectrograph fibre-to-fibre cross-talk are not fully represented. A tabulated zero means negligible light within this calculation, not a measured absence of all contamination.

The J1329 catalogue combines two DESI exposures and reports a Z-arm masked fraction 0.5031. That metadata must not replace the validity mask of the particular MWDD spectrum analysed here. Observation identifiers and individual seeing values are preserved in the extraction.

Swan et al., Section 7.8.7, also report a useful caution: X-Shooter confirmed broad Na-D-like absorption in WDJ034301.05−011401.58, but not the DESI feature in WDJ220022.42−061430.97. The latter appears in two consecutive DESI exposures and remains unexplained. Repeated spectra from one instrumental setup therefore cannot, by themselves, prove an intrinsic photospheric feature. The present study does not infer new abundances from an apparent trough alone.

Candidate values are in [swan2026_candidate_contamination.csv](../novelty/swan2026_candidate_contamination.csv). Original rows, exact download URLs, SHA256 hashes and the model limitations are in [swan2026_candidate_audit.json](../novelty/swan2026_candidate_audit.json).

## 8. Pink and unusual yellow candidates

### WD J1329+0033

**WDJ132942.69+003336.60**, Gaia DR3 **3711047662972690688**, is also known as 2QZ J132942.7+003340. Its representative colour is **#FFC1CF**, Duv=**−0.02265**. Kilic et al. (2026) classify the DESI spectrum DQ and model strong carbon Swan bands, with Teff≈5,592 K and log(C/He)=−6.14. The published model panel is `allfitsDQ.pdf`, page 375. An older uncertain DA: classification from XP should not override the resolved molecular pattern without examination.

The calculated pink colour is consistent with suppression in broad molecular bands. Those bands and the DQ interpretation are prior results, while the human-vision integration is the quantity analysed here. The target has no other catalogued Gaia source within the queried 10″ cone. The conditional DESI interval is well separated from the thermal locus. Gaia spectrum comparisons are retained, but this project performs the full native coefficient-covariance analysis only for the two green candidates; it does not attach an equally complete Gaia uncertainty calculation to J1329.

### WD J1323−0129

**WDJ132312.76−012923.67**, Gaia DR3 **3638333660492606976**, gives **#FFE86A**, Duv=**+0.02348**. SDSS and DESI both yield yellow colours, and the departure from the thermal sequence persists across the examined calibration choices. This is a colour measurement candidate, not an example of positive Duv automatically implying green.

Its atmospheric parameters are materially model-dependent. [Kilic et al. (2025)](https://arxiv.org/abs/2412.04611) give a tentative DZ: fit near 4,262 K, whereas Kilic et al. (2026) give approximately 3,648 K, with substantially different gravity and abundance estimates. The change is much larger than the respective formal temperature errors. A colour integral does not require choosing either atmospheric model, but a new physical interpretation would. This report does not convert the small formal fit errors into a secure abundance or evolutionary claim.

## 9. Controls, rejected cases and search significance

All 54 ordinary comparison spectra—18 each of DA, DC and DB type—lie within a distance 0.01 of the Planckian locus; the largest distance is 0.00671. These controls test gross implementation errors and provide context. They are too few and too selectively assembled to establish the false-positive rate of a large heterogeneous survey search.

Known-colour comparisons also provide useful checks. J0851+1543 gives **#F1FFF7**, compared with published **#F1FFF8**. The Pan-STARRS-adjusted colour for the known pink J1011+2845 agrees with published **#FF8775**. Other comparisons, including J1330+6435, retain larger differences between available observations and the comparison paper's models; exact reproduction of every published patch is not claimed. Results are in [baseline_reproduction.csv](../results/baseline_reproduction.csv).

Two rejected cases illustrate why the screen cannot be read as a discovery catalogue:

- **LP616−53 / J1258+0106:** a DESI-derived value near #F4FFCC and Duv≈+0.01727 initially appears interesting. A brighter companion lies about 2.30″ away at Gaia epoch 2016.0, with another catalogue entry about 1.29″ away. Gaia flags five of seven BP and five of six RP transits as blended. Swan classifies the observed system WD+MS and estimates substantial photometric contamination. It is excluded from the principal claims about the intrinsic colour of a single white dwarf. No spectral deblending was attempted, and this does not prove the entire tint is an artefact.
- **J1552+2023:** anomalously faint and highly uncertain inherited SDSS r and i values produce an extreme artificial blue colour if imposed on the spectrum. The required tilt and residuals are unacceptable, while unadjusted Gaia/DESI spectra and other photometry indicate an ordinary warm colour. Calibration-quality cuts reject the forced result.

![Exploratory colour distribution](../figures/survey_colour_plane.png)

*The plot selects one calibrated result per catalogue identifier for display. The Q/Z selection, incomplete archive coverage and remaining duplicate identities prevent inference of the population frequency of green, pink or yellow white dwarfs.*

The search is exploratory and candidates were selected after examining thousands of records and several processing choices. No preregistered test, survey-wide null distribution, family-wise error rate or false-discovery-rate calculation was performed. Consequently, a per-candidate 95% interval is **not** a 95% global discovery statement. The complete ranking is a set of follow-up priorities. Uncalibrated cases, single-spectrum cases and very unusual Gaia-only results remain in [all_object_candidates.csv.gz](../results/all_object_candidates.csv.gz) with that status.

## 10. Prior-literature and identity audit

The comparison does not rely on searching for short names or the phrase green star. Hollands et al. (2026), Tables 3–6, were parsed into **238 entries and 236 unique names**: 15 infrared-faint entries, 36 DQ entries, 36 named DZ models and 151 nearby-system entries. Named physical stars in model tables were included; generic model grids were excluded. The complete [unique exclusion table](../novelty/hollands2026_exclusions_unique.csv) retains aliases and coordinate information.

Full Gaia IDs were resolved through [SIMBAD](https://simbad.cds.unistra.fr/simbad/), and positions were checked against the comparison table. The principal candidates also do not match the full 231-object parent DZ catalogue of [Hollands et al. (2017)](https://cdsarc.cds.unistra.fr/ftp/J/MNRAS/467/4970/ReadMe).

| Candidate | Nearest named Hollands et al. (2026) entry | Angular separation in the independent audit |
|---|---|---:|
| J0913+4434 | WDJ085626.95+451337.01 | 11,190.823″ |
| J0429−0354 | WDJ041521.80−073929.20 | 18,660.615″ |
| J1329+0033 | WDJ133359.84+001655.03 | 3,985.096″ |
| J1323−0129 | WDJ132144.04−023751.47 | 4,317.696″ |

The independent audit uses SIMBAD J2000 ICRS positions. The coordinate-encoded comparison names do not have an assumed invented epoch; small differences from the main pipeline's separations arise from different catalogue epochs. These large separations make an ordinary proper-motion or short-alias confusion immaterial for the four cases.

The reviewed sources include Kilic et al. (2020, 2025, 2026), Vincent et al. (2023, 2024) and Swan et al. (2026), as well as individual catalogue rows and public atmosphere-model panels. They already report classifications, atmospheric fits and astronomical passband colours. The inspected texts and supplements did not supply CIE chromaticity or sRGB values for the principal candidates. For example, the Swan text contains no CIE, chromaticity, sRGB, perceived-colour or pink measurements; occurrences of green concern image channels or author names.

This is a bounded literature result. SIMBAD can be incomplete or slow to index recent papers, and absence from a particular paper or search result cannot prove that no earlier calculation exists. The [49-row evidence table](../novelty/novelty_evidence.csv) records what each source establishes and its limits; [candidate_novelty_audit.json](../novelty/candidate_novelty_audit.json) retains the object-level checks. **The stars and their known physics are not new discoveries. The potentially new result is their explicitly calculated and tested human-vision chromaticity.**

## 11. Reproduction and useful follow-up

The executed [research notebook](../white_dwarf_colour_research.ipynb) checks selected input hashes, recalculates principal DESI colours, verifies the retained Gaia reconstructed means and summarizes the full scan. The [repository README](../README.md) gives environment setup and commands. Separate pinned environments and instructions are provided for the native Gaia reconstruction.

Selected source spectra, Gaia coefficients, computed results and provenance are retained for reproducing the principal claims. Recreating the complete acquisition requires approximately 2 GB of public spectra beyond the compact selected-data package. [download_frozen_spectra.py](../download_frozen_spectra.py) uses the saved URLs and verifies hashes; a changed or missing upstream source must not silently be substituted. Literature-extraction scripts additionally require the cited source documents when those documents are not redistributed. Bibliographic records are provided in [references.bib](references.bib).

The next material observation would be independently calibrated visible spectroscopy that spatially separates nearby sources, with repeat observations and relative flux calibration at the few-percent level. Such data could test whether the pale green channel excess survives remaining calibration and contamination uncertainties. This report contains no new telescope observations and does not imply that those follow-up checks have already occurred.

The present evidence supports **two additional pale yellow-green candidates, one pink candidate and one unusually yellow candidate** for further study. A robust departure from the thermal colour sequence and a definite subjective colour name are different levels of inference; the available Gaia covariance makes that distinction particularly clear.

## 12. Attribution and research transparency

The original observations, reductions, classifications, catalogue construction and atmosphere models are the work of their respective survey teams and cited authors. MWDD supplied access and provenance for spectra from multiple observing programmes. SDSS, DESI, Gaia and the Gaia Data Processing and Analysis Consortium supplied the underlying survey measurements and calibrations. Pan-STARRS photometry was accessed through public catalogue services, including MAST. SIMBAD and VizieR/CDS supported identity and local-field checks. The unusual-colour framework and comparison measurements are credited to Hollands et al. (2026); the prior atmospheric analyses are credited to their original authors.

This project was initiated and is maintained by **Shota Moriwaki**. Data acquisition, code development and execution, numerical checks, literature comparison, and report preparation were carried out with assistance from **OpenAI's ChatGPT** in response to the maintainer's research request. ChatGPT is disclosed as an analytical and writing tool, not listed as a scientific author. The reproducible records document the work performed; this note has not been peer reviewed, and no institutional affiliation or external endorsement is asserted.

The unchanged CIE reference dataset is **CIE 2019**, DOI [10.25039/CIE.DS.xvudnb9b](https://doi.org/10.25039/CIE.DS.xvudnb9b), licensed **CC BY-SA 4.0**. Its official metadata and checksums are retained. Original third-party datasets and documents keep their respective attribution and reuse terms; a licence for this project's code or prose does not transfer ownership of the surveys' material.

## References and data documentation

Full machine-readable entries, including source-version notes, are in [references.bib](references.bib). Journal metadata not established in the retained evidence is omitted rather than guessed.

1. **Hollands, M. A., Gänsicke, B. T., Tremblay, P.-E., & Koester, D. (2026).** *Any colour you like: The diverse chromaticities of white dwarfs.* RAS Techniques and Instruments. DOI [10.1093/rasti/rzag069](https://doi.org/10.1093/rasti/rzag069); [arXiv 2610.18966v1](https://arxiv.org/html/2610.18966v1). Comparison chromaticities, method and named-object exclusions.
2. **Hollands, M. A., et al. (2017).** *Cool DZ white dwarfs. I. Identification and spectral analysis.* MNRAS 467, 4970–5000. [CDS catalogue J/MNRAS/467/4970](https://cdsarc.cds.unistra.fr/ftp/J/MNRAS/467/4970/ReadMe). Parent 231-object identity check.
3. **Dufour, P., et al. (2017).** *The Montreal White Dwarf Database: A Tool for the Community.* ASP Conference Series 509, 3. [arXiv 1610.00986](https://arxiv.org/abs/1610.00986); [MWDD](https://www.montrealwhitedwarfdatabase.org/). Spectral holdings and catalogue provenance.
4. **Kilic, M., et al. (2020).** *The 100 pc White Dwarf Sample in the SDSS Footprint.* ApJ 898, 84. DOI [10.3847/1538-4357/ab9b8d](https://doi.org/10.3847/1538-4357/ab9b8d); [arXiv 2006.00323](https://arxiv.org/abs/2006.00323). Earlier classifications and atmosphere analyses.
5. **Kilic, M., et al. (2025).** *The 100 pc White Dwarf Sample in the SDSS Footprint II. A New Look at the Spectral Evolution of White Dwarfs.* ApJ 979, 157. DOI [10.3847/1538-4357/ad9bb3](https://doi.org/10.3847/1538-4357/ad9bb3); [arXiv 2412.04611](https://arxiv.org/abs/2412.04611). Earlier J1323 fit and spectral-evolution context. Journal citation is recorded in the consulted Kilic et al. (2026) bibliography.
6. **Kilic, M., et al. (2026).** *A Detailed Model Atmosphere Analysis of Cool White Dwarfs in DESI DR1.* ApJ 1006(2), 248. DOI [10.3847/1538-4357/ae825f](https://doi.org/10.3847/1538-4357/ae825f); [arXiv 2606.25377v2](https://arxiv.org/abs/2606.25377). Prior classifications and atmospheric fits. Publisher-deposited Crossref metadata was checked.
7. **Kilic, M., & Bergeron, P. (2026).** *Model Fit Figures for: A Detailed Model Atmosphere Analysis of Cool White Dwarfs in DESI DR1.* Zenodo. DOI [10.5281/zenodo.20775938](https://doi.org/10.5281/zenodo.20775938). Public individual-star model panels.
8. **Vincent, O., Bergeron, P., & Dufour, P. (2023).** *Data-driven selection and spectral classification of white dwarf stars.* MNRAS 521, 760–771. DOI [10.1093/mnras/stad580](https://doi.org/10.1093/mnras/stad580); [arXiv 2301.05209](https://arxiv.org/abs/2301.05209). Prior survey classification methods.
9. **Vincent, O., et al. (2024).** *Classification and parameterisation of a large Gaia sample of white dwarfs using XP spectra.* A&A 682, A5. DOI [10.1051/0004-6361/202347694](https://doi.org/10.1051/0004-6361/202347694); [arXiv 2308.05572](https://arxiv.org/abs/2308.05572). Prior XP classifications and atmosphere estimates.
10. **Swan, A., et al. (2026).** *The DESI Data Release 1 white dwarf catalogue.* [arXiv 2609.04314v1](https://arxiv.org/html/2609.04314v1); [official version 1.0 data tables](https://cygnus.astro.warwick.ac.uk/phsdaj/WhiteDwarfs/). Catalogue classifications, contamination estimates and Na-feature follow-up.
11. **Kepler, S. O., et al. (2019).** *White dwarf and subdwarf stars in the Sloan Digital Sky Survey Data Release 14.* MNRAS 486, 2169–2183. DOI [10.1093/mnras/stz960](https://doi.org/10.1093/mnras/stz960); [CDS catalogue](https://cdsarc.cds.unistra.fr/ftp/J/MNRAS/486/2169/). Direct SDSS target selection.
12. **CIE (2019).** *Colour-matching functions of CIE 1931 standard colorimetric observer.* DOI [10.25039/CIE.DS.xvudnb9b](https://doi.org/10.25039/CIE.DS.xvudnb9b). Standard-observer reference dataset, CC BY-SA 4.0.
13. **Gaia/ESA/DPAC.** [DataLink products](https://www.cosmos.esa.int/web/gaia-users/archive/datalink-products), [programmatic archive access](https://www.cosmos.esa.int/web/gaia-users/archive/programmatic-access), and [GaiaXPy documentation](https://gaia-dpci.github.io/GaiaXPy-website/). Native XP coefficients and reconstruction software.
14. **SDSS and Pan-STARRS/MAST.** [SDSS DR17 spectrum documentation](https://www.sdss4.org/dr17/spectro/spectro_basics/) and [MAST catalogue API documentation](https://catalogs.mast.stsci.edu/docs/panstarrs.html). Source conventions and photometric queries.
15. **CDS.** [SIMBAD](https://simbad.cds.unistra.fr/simbad/) and [Gaia DR3 catalogue I/355 at VizieR](https://vizier.cds.unistra.fr/viz-bin/VizieR?-source=I/355/gaiadr3). Object identities, bibliography, neighbouring-source and astrometric checks.
