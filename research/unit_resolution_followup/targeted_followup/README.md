# Targeted follow-up of four visually flagged spectra

**The native spectra preserve the broad structures in rows 7607 and 8019. The
narrow red maximum in row 7930 carries native sky-residual flags.** Existing
specialist and automated classifications must be reconciled before these
features are used in any claim about unusual white-dwarf physics. This bounded
follow-up does not add a physical discovery or change the frozen audit images,
unit registry, or core candidate results.

The targets were requested after actual inspection of pages 27/panel 2,
30/panel 9 and 29/panel 13 of the [unit-resolution sheets](../contact_sheet_index.csv).
All values and source identities below are in [results.json](results.json).
The [three native figures](figures_manifest.json) were actually inspected;
[visual_review.json](visual_review.json) records the final PNG hashes and notes.
An additional local-only check of page 20/panel 3, **row 5827**, retains its
own [numerical record](local_row_5827.json) and [actual native-figure inspection](local_row_5827_visual_review.json).
The total is four distinct targets and four actually inspected final PNGs;
only the first three targets have newly retrieved external catalogue context.

## What was retrieved and compared

For each MWDD export, the new unit-resolution evidence identifies one exact
SDSS plate/MJD/fibre. Here the original SDSS Fλ, IVAR, AND and OR arrays are
loaded from the [lossless compact inputs](../compact_manifest.json). The three
MWDD exports are Fν representations; after the specified `c/λ²` conversion and
a constant scale, the native flux shapes agree. These are two representations
of one observation, not independent spectroscopic confirmations.

New public reads obtained the three actual MWDD pages, the original cited
Kleinman et al. (2013) catalogue rows through NASA HEASARC, official Gaia DR3
target/15″ field data and variability classifications, a historical Chandra
proposal record, and official SDSS bit definitions. Original responses,
queries, access UTC, URL and SHA-256 are retained in [sources/](sources/),
[context_manifest.json](context_manifest.json), and
[specialist_manifest.json](specialist_manifest.json). An initial HEASARC
response rejected the requested CSV format; that error is retained explicitly
and was followed by a successful VOTable retrieval. It is not counted as an
absent catalogue entry.

## Row 7607: an existing DAZH label and surviving multi-pixel structure

**SDSS J185040.71+200056.2 / Gaia 4518692348609283712**, original
`2833 / 54650 / 374`, has specialist type **DAZH** in the cited Kleinman table
at that exact observation ID. The MWDD page also reproduces the same catalogue
source column. Its generic SDSS classification is `STAR / WD`, `ZWARNING=0`;
the pipeline and specialist labels are preserved as separate fields.
[Native figure](native_row_7607.png) · [published catalogue response](sources/kleinman_catalogue.xml)

The original visible interval contains 3,373 pixels, no nonpositive-IVAR
pixels, seven negative flux samples, and 41 nonzero AND masks. The resolved
10 Å arithmetic-mean minima occur in bins centred on approximately
3965, 4105, 4345, 4865, 5895 and 6565 Å. These are locators of displayed
structure, not fitted transition wavelengths. In the six corresponding broad
windows, respectively 143/143, 190/190, 299/300, 312/312, 214/214 and 206/206
native samples retain positive IVAR and zero AND mask. The broad depressions
therefore survive this simple quality comparison. The sharp excursion around
5577 Å is visibly distinct and flagged. The lower right panel uses an explicit
continuum zoom; all native extrema remain in the upper panel.

The initial contact-sheet wavelength estimates were too coarse. Their original
windows and the revision after native inspection remain in the JSON. No
magnetic field strength, abundance, Zeeman component, or new atmospheric
classification was fitted. The old catalogue's 13,722 K and autofit log(g)=5.8
are metadata, not a verified parameter determination for this object.

Gaia parallax is 0.1378 ± 0.1759 mas, so no inverse-parallax distance is used.
The field includes faint Gaia sources at 2.94″ and 3.13″, with G flux ratios
0.119 and 0.135 relative to the target. Their aperture contribution has not
been measured. The nominal-coadd-epoch proper-motion check places the Gaia
point estimate 0.158″ from the original PLUG position. This supports the
intended association but does not resolve blending or the physical class.

## Row 8019: strong structure accompanied by a catalogue-classification conflict

**[VV2006] J004527.7+143815 / Gaia 2780975896637670528**, selected original
`419 / 51879 / 104`, has 3,393 visible native samples, one nonpositive IVAR and
no negative flux. The median supplied pixel S/N over that interval is 30.36.
The deep blue depressions remain under both positive-IVAR and additional
AND=0 selection. Their 10 Å mean minima are near 3995 and 4435 Å; the relevant
windows retain 350/351 and 297/297 samples. Treating these broad structures as
a few defective pixels would not be supported by this check.
[Native figure](native_row_8019.png) · [native data](native_row_8019.csv.gz)

However, the physical label is unresolved across the retained sources:

| Evidence | Actual reported value or scope |
|---|---|
| MWDD page | DZ, attributed to Kleinman et al. 2013 |
| Original Kleinman catalogue | DZ at the same position for `419/51868/106` and `419/51812/105`; these are different observations from the selected coadd |
| Those historical autofits | Reduced χ² 30.449 and 27.539; their temperatures/log(g) are not accepted physical fits here |
| Selected SDSS coadd | QSO / BROADLINE, automatic z=1.87237, `ZWARNING=80` |
| Official Gaia DR3 | `VARIABLE`; existing variability class AGN, score 0.37219465 |
| Gaia astrometry | Parallax −0.0260 ± 0.0866 mas; proper motions −0.1138 and −0.0441 mas/yr |
| Chandra Cycle 7 proposal 07700859 | The same named/positioned target appears in a BAL-quasar observing programme |

The SDSS warning is the combination `MANY_OUTLIERS` and `NEGATIVE_EMISSION`,
not an assertion that all spectral pixels are invalid. Gaia's score is a
classifier score, not a 37.2% physical probability. The Chandra proposal is
historical target-selection context, not a new spectroscopic proof. Its
source [record](sources/chandra_cycle7.html) and the [Gaia response](sources/gaia_variability.csv)
are retained. The nominal-epoch Gaia–PLUG separation is 0.055″, with no other
Gaia row returned within 15″. That absence does not exclude an unresolved or
uncatalogued contaminant.

The conclusion is **a documented classification conflict requiring specialist
reconciliation**, with independent existing AGN-related evidence. It is not a
new white-dwarf absorption discovery. The original flux structure and every
conflicting catalogue label remain available for review.

The primary public entry points are the [NASA Chandra Cycle 7 programme list](https://cxc.harvard.edu/target_lists/cycle7/abstracts_cycle7.html)
(proposal **07700859**, target **SDSS J004527.69+1438**, coordinates
**00:45:27.70 +14:38:16.20**), the [official Gaia TAP service](https://gea.esac.esa.int/tap-server/tap)
with this saved [exact-source variability query](gaia_variability_query.adql),
and the [original selected SDSS coadd](https://data.sdss.org/sas/dr17/sdss/spectro/redux/26/spectra/lite/0419/spec-0419-51879-0104.fits).
The conflicting specialist label is preserved in the
[Kleinman catalogue response](sources/kleinman_catalogue.xml), whose
[NASA HEASARC documentation](https://heasarc.gsfc.nasa.gov/w3browse/all/sdssdr7wd.html)
identifies the published source and distinguishes manual spectral type from
autofit output. The exact dates, warnings, classifier score and source hashes
are in [results.json](results.json); these records do not make a definitive
physical reclassification.

## Row 7930: a narrow peak with a native sky-residual warning

**SDSS J053553.56−004003.9 / Gaia 3217759570831525120**, original
`2072 / 53430 / 60`, has **DBZAE:** in the original Kleinman table, at this
exact observation ID. MWDD also displays DBZAe and a later Vincent et al.
(2023) DB label in separate source columns. Those prior labels already
contain classification context; a new emission claim cannot be inferred from
this audit's plot. The generic SDSS fit is `STAR / L9`, `ZWARNING=12`
(`SMALL_DELTA_CHI2` plus `NEGATIVE_MODEL`).
[Native figure](native_row_7930.png) · [source columns](sources/mwdd_7930.html)

Within the declared 6540–6600 Å search interval, the largest native sample is
at **6565.98795 Å in vacuum**. Its Fλ is `1.73822e−16` with supplied pixel
error `1.83909e−17` erg cm⁻² s⁻¹ Å⁻¹. The two consecutive pixels above half of
the local peak excess have centres **6564.47419 and 6565.98795 Å**. Both carry
`BADSKYCHI` in **both AND and OR masks**. The official
[mask definition](sources/sdss_bitmasks.html) associates this bit with poor sky
residual fits. This is a reason to withhold a new-line interpretation; it does
not by itself prove that the astrophysical line is absent.

The plot retains the peak and compares it with the additional AND=0 view.
The supplied error is not a line-detection significance, and the two-pixel
span is not a deconvolved FWHM. A G≈16 neighbour at 14.83″ is about 24.8 times
brighter in G than the target; PSF wings have not been quantified. Gaia's
nominal-coadd-epoch position lies 0.125″ from PLUG, supporting the intended
target while leaving aperture-origin questions open.

## Row 5827: an additional local-only check with a CV classification conflict

**Gaia DR3 1242828982729309952**, selected original **2136 / 53494 / 541**,
has frozen MWDD type **DZ:** and generic SDSS **STAR / CV**, `ZWARNING=0`,
pipeline `SN_MEDIAN_ALL=18.72`. Its MWDD export was already Fλ; the native
shapes agree with the original SDSS array after a constant scale to a maximum
fractional residual of `4.852e−6`. This is another representation of the same
coadd. [Numerical record](local_row_5827.json) · [native figure](native_row_5827.png)

The final native figure resolves two adjacent red maxima, together with
several broad blue depressions containing local positive structure. The
maximum in the declared 6400–6800 Å window is **6550.88409 Å** in vacuum,
with **AND=OR=0**. All **264** native samples in that window have positive
IVAR and zero AND mask. The contiguous half-excess cluster around the higher
maximum covers **10 pixels**, centres 6544.85588–6558.43347 Å; this describes
one of the two visible maxima. Two of those samples have the OR-only
`COMBINEREJ` bit. The reference continuum uses fixed local sidebands, so this
cluster is not a deconvolved width or a line significance. The three broad
blue/middle windows retain **322/322, 309/309 and 321/321** positive-IVAR,
AND=0 samples. No physical-looking feature was removed.

This addition uses only local source arrays, original headers and frozen
classification metadata. No new literature search, Gaia query, epoch-position
or aperture analysis was performed for row 5827. The CV/DZ: disagreement and
the surviving structure warrant specialist reconciliation; neither a new
atomic line identification nor a physical reclassification follows here.

## Reproduction and limits

```bash
python research/unit_resolution_followup/targeted_followup/analyse.py
python research/unit_resolution_followup/targeted_followup/local_row_5827.py
python research/unit_resolution_followup/targeted_followup/verify_outputs.py
```

The numerical replay is offline and uses the existing compact input shards;
no full original SDSS cache is needed. It checks unit-identity evidence,
native quality arrays, the cited catalogue rows, Gaia context, window and
peak calculations, exported native samples and source/figure hashes.
The callable `verify(root)` returns a `summary` dictionary and a
`verified_file_sha256` mapping from repository-relative paths to SHA-256.
[verification.json](verification.json) records the result. The verifier checks
the bytes tied to a recorded visual inspection; it does not perform that
perceptual act again. SVG counterparts are generated from the same figures
but were not independently rendered for visual inspection.

The three astrometric checks use nominal coadd MJDs, linear proper-motion point
estimates, and no covariance, radial velocity, or annual-parallax correction.
No negative or insignificant parallax is inverted. Selection was purposeful,
not a population sample. No broad feature was deleted, no classifier was made
ground truth, and no new physical discovery, variability detection, abundance
fit or calibrated discovery probability is claimed.

### 日本語の要点

7607の吸収構造は多数の有効な原画素に残り、原論文カタログにも同じ観測のDAZH分類がありました。
8019は原画素でも深い構造を示しますが、白色矮星カタログのDZと、SDSS・Gaia・過去のChandra
観測提案のAGN/QSO関連情報が食い違います。「新しい白色矮星の吸収」として扱わず、分類の
根拠を整理する対象です。7930の赤い鋭いピークは、原格子の6564.47–6565.99 Åの2画素に
BADSKYCHIがありました。既存のDBZAE:という分類を保存したまま、今回のピークだけから新しい
輝線を確認したとはしません。全3件で元の形、負値、フラグ、原論文の行ID、取得応答を保持しています。

追加の5827はローカル原配列だけで確認し、既存DZ:とSDSS自動STAR/CVの食い違いを保存しました。
原図では赤側の2つの山が分かれ、最大は6550.884 Å、6400–6800 Åの264画素はすべて正のIVARかつ
AND=0でした。原因や輝線種は断定せず、専門分類で再検討する対象とします。計4件の最終原図を
実際に見て記録し、同じ検証モジュールでオフライン再計算します。新規Gaia・原論文の取得対象は
最初の3件であり、5827について追加取得したかのようには数えません。

Original project author: **ShotaMoriwaki**. This is ChatGPT-assisted exploratory
research, not independent astronomical peer review.
