# Targeted follow-up of previously noted spectral features

Updated 19 October 2026 UTC. This is a ChatGPT-assisted, unreviewed follow-up of five selected spectrum records and nine Gaia identifiers. It complements the full remaining-review-queue inspection; these targets were chosen from the **previous 337-object visual audit**, not discovered by the new 2,007-object pass.

## What was actually checked

Five MWDD exports were retrieved anew and all five matched their recorded SHA256 exactly: two DESI Fλ spectra and three Gaia XP Fλ reconstructions. A fresh official Gaia DR3 TAP query returned nine source records with a left join to the published variability-classifier table. All six responses, request URLs, timestamps and hashes are retained in [retrieval.json](retrieval.json); the [ADQL](gaia_query.adql) and [unmodified Gaia response](raw/gaia_feature_review.csv) make the catalogue statements inspectable. This is a catalogue query, not acquisition of new telescope observations.

The [script](../targeted_diagnostics.py) reads the exact raw export wavelength grids and preserves signed flux. Both the [five-spectrum overview](native_grid_overview.png) and the [six native DESI window panels](desi_native_windows.png) were actually viewed. The overview uses each record's median flux at 5200–5500 Å only to normalize the display. It does not fit a continuum or recalibrate the input. Here, native-grid means the **archived export grid**, not raw CCD detector pixels or original per-camera data; no new camera FITS were acquired in this step. Gaia XP export samples are correlated reconstructions, **not independent detector pixels**; the three XP exports contain no supplied error columns.

## A previously catalogued variable in the XP feature subset

| Gaia DR3 source_id | Old visual concern | Official DR3 result from this query | Consequence |
|---|---|---|---|
| 5078976609103251456 | Positive structures near 486 and 656 nm, XP-only | `phot_variable_flag=VARIABLE`; classifier `CV`, score 0.583544 | Record already-published variability and a CV classifier assignment. A fixed, isolated white-dwarf atmosphere is not established. |
| 2163612727665972096 | Similar positive structures, XP-only | `NOT_AVAILABLE`; no joined variability-classifier entry | Neither nonvariability nor a CV classification is established. |
| 2002597083798483200 | Positive structure near 656 nm, XP-only | `NOT_AVAILABLE`; no joined variability-classifier entry | Independent spectroscopy and covariance-aware reconstruction remain required. |
| 1245262790370992256 | Previously checked variable, comparison identifier | `VARIABLE`; classifier `CV`, score 0.6277259 | The query reproduces the earlier control's catalogue classification. |

The classifier score is **not a posterior probability**. The newly documented catalogue match for 5078976609103251456 is not a new variable-star discovery. Gaia's classifier and XP use observations from the same mission; they are not independent photon data. Approximate alignment of low-resolution positive structures with named transitions does not constitute a new line identification, equivalent-width measurement or atmospheric diagnosis. Values and other quality fields are in the [source response](raw/gaia_feature_review.csv).

## Native DESI samples change the interpretation of narrow peaks

The two inspected DESI exports have 7,781 samples each. Within the explicitly selected 3600–8300 Å interval each contributes 5,875 finite flux samples; the largest wavelength step is 0.800000000001 Å. There is no large sampling gap in that selected interval. This does not establish validity of every native camera pixel. The export `flag` column equals one throughout this interval for both records. Its semantics have **not** been established as the native DESI camera `MASK`, so this analysis does not reject all those samples or label them all good camera pixels.

| Target / row | Raw visible negative samples | Median raw flux / supplied σ | No-window Duv | Standard five-window Duv | Δuv for only 5577.34 ± 8 Å removal |
|---|---:|---:|---:|---:|---:|
| SDSS J110644.27+673708.6 / 1250 | 347 / 5,875 | 4.15045 | +0.00490723 | +0.00458793 | 0.000222139 |
| Gaia DR3 3688869246424920448 / 3004 | 96 / 5,875 | 5.30422 | +0.00273352 | +0.00259340 | 0.0000601180 |

The positive maximum in the selected 5577 Å window is at the **same sampled 5579.2 Å position** in both exports. Its raw flux divided by its supplied σ is 2.372 and 3.694, respectively. Those ratios include the underlying continuum; they are **not continuum-subtracted line significances** and have not been adjusted for selection or multiple comparisons. Native-window plots show large uncertainties and adjacent troughs. This is compatible with a measurement/reduction concern, but the present export-level check does not determine its physical cause. Original camera masks, sky estimates, extraction and independent epochs would be needed to distinguish a stellar feature from a residual.

The five-window versus no-window Δuv is 0.000407430 for row 1250 and 0.000150503 for row 3004. These are descriptive sensitivity calculations, not total systematic error bars. Both tests remain within the historical |Duv| = 0.01 exploratory boundary. The row 1250 current screen uses PS1 calibration; this raw-flux test does not replace its calibrated +0.00549863 result. Its raw sample S/N also differs from a screen S/N computed after the pipeline's window selection. Complete numbers, selected-window samples and definitions are in [diagnostics.json](diagnostics.json).

## Unit-unresolved historical spikes remain unavailable for a current colour claim

The previously flagged SDSS rows 1248, 3003, 8322, 8339 and 8372 have `unit_unverified` status in the [current record screen](../../precision/flux_units/corrected_record_screen.csv.gz). They correspond to Gaia sources 1060188315963488640, 3688869246424920448, 2629980411471669632, 2802900781266410112 and 4573582236809330432. They are **not plotted as Fλ here**. The old positive/negative-spike descriptions remain historical observations, not validated present-day colour corroboration. Two of those objects have the separate, unit-valid DESI spectra examined above.

The official query supplies no new native Gaia XP availability for the SDSS-only 2629980411471669632, 2802900781266410112 or 4573582236809330432 (`has_xp_continuous=false`). That describes this Gaia DR3 product, not an absence of all possible observations elsewhere.

## Reproduction and limits

The separate [five-object XP feature follow-up](../gaia_additional_features/README.md) arose from the newly inspected remaining queue. Its five official Gaia rows are all already catalogued as variable. That later response is stored separately; the original five exports and nine-source query described here were preserved.

From the repository root, after installing the core requirements:

```bash
.venv-research/bin/python research/outlier_followup/targeted_diagnostics.py --analyze
.venv-research/bin/python research/outlier_followup/verify_targeted.py
```

This reuses saved raw responses and verifies the five frozen spectrum hashes. Optional `--fetch` repeats the public requests and requires network access; a spectrum hash mismatch is recorded as an error rather than replacing the expected input. Current analysis outputs record the current code and input-table hashes. The retrieval record retains the code hash at acquisition time; later additions to parsing diagnostics and figures need not have identical code bytes.

The offline verifier also checks the later five XP exports and Gaia rows, exact record identities, current unit and eligibility gates, query provenance, descriptive window extrema, and the two DESI 5577.34 ± 8 Å sensitivity calculations. It returns a numerical summary and repository-relative verified file hashes for integration into the parent research verification report. It does not certify a visual judgment or a physical classification.

No new formal spectral-line detection, atmospheric fit, variability period, covariance reconstruction or population rate was estimated here. No candidate was removed solely by visual appearance. These results add explicit source-level qualifications and identify the native data needed for the next test.
