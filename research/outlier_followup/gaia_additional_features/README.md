# Five XP feature cases: already catalogued Gaia variables

Updated 19 October 2026 UTC. This is an unreviewed, ChatGPT-assisted investigation within ShotaMoriwaki's project. It follows five individual panels selected while actually inspecting the remaining historical review queue. **All five sources already have `phot_variable_flag=VARIABLE` in Gaia DR3.** Three have a published `CV` classifier label, one has `S`, and one has no joined classifier entry. These are additions to this project's source-level qualifications, not new variable-star discoveries.

## Executed checks and provenance

One public query to the official ESA Gaia DR3 TAP service returned the five exact identifiers at **2026-10-19 10:55:58 UTC**. The [ADQL](query.adql), [unmodified CSV response](raw/gaia_feature_review.csv), and [request URL, retrieval time and SHA256](query_provenance.json) are retained. This query is separate from the earlier [nine-source query](../targeted_diagnostics/README.md), whose response and provenance were preserved.

Five current, eligible Gaia XP Fλ exports were read from the newly recovered spectrum cache. Their bytes matched the frozen input hashes exactly and were copied unchanged into this directory. The [results](results.json) retain each source URL, frozen hash, prior retrieval record, row index, current calibration state, withheld-unit count, and contact-sheet hash. No additional telescope observation or native Gaia coefficient file was acquired for this step.

| Gaia DR3 source_id | Inspected page / panel; XP row | Official variability flag | Published classifier label | Classifier score | Current Duv |
|---|---|---|---|---:|---:|
| 1951666884868218112 | 31 / 8; 8303 | VARIABLE | CV | 0.7057743 | −0.00670646 |
| 2096274276193099136 | 32 / 11; 8307 | VARIABLE | CV | 0.8401985 | −0.00952907 |
| 2208124536065383424 | 33 / 11; 5948 | VARIABLE | No joined entry | — | −0.00699361 |
| 4565045873343899136 | 81 / 16; 8370 | VARIABLE | CV | 0.93689567 | −0.00539536 |
| 5589261737965864832 | 89 / 13; 8390 | VARIABLE | S | 0.4871808 | −0.00838143 |

The literal catalogue labels are retained; the `S` object and the object without a classifier entry are not reassigned to `CV` here. A missing classifier entry is compatible with the explicit `VARIABLE` source flag and does not mean nonvariability. The [machine-readable match table](catalogue_matches.csv) also preserves RUWE and native XP-product availability.

The Duv values are copied from the [current corrected record screen](../../precision/flux_units/corrected_record_screen.csv.gz) and independently reproduced by the offline verifier. All five are inside the |Duv| = 0.01 exploratory boundary; these are follow-ups of historical review-queue features, not five additions to the current strong-colour set. Rows 5948 and 8370 retain accepted calibration from that screen; the other three are uncalibrated there. No photometric fit was repeated in this subanalysis.

## What the enlarged spectra show

The [full exports and two local windows per source](xp_export_windows.png) were actually opened and inspected: **five objects and fifteen plotted panels**. The [visual record](visual_review.json) binds that inspection to the exact figure SHA256. The figure plots the exported samples without the 20 Å display binning of the contact sheets. Signed flux is retained and each curve is normalized by its median current Fλ at 5200–5500 Å. The [SVG](xp_export_windows.svg) supports closer inspection.

All five reconstructions retain broad positive structure in the middle reference window and a positive maximum in the red reference window. The sampled maxima in the 4861 ± 80 Å search interval lie at 4869.32–4900.74 Å. Four red-window maxima lie at 6566.39 Å and one at 6587.53 Å in the 6563 ± 100 Å interval. These are **discrete extrema of a correlated reconstruction**, not fitted line centres or Doppler velocities. The reference wavelengths and finite windows were used to describe the already selected structures; no blind line search, continuum-subtracted significance, equivalent width, or physical identification was obtained. Full descriptive values are in [results.json](results.json).

The XP exports have no supplied uncertainty columns. Native coefficient covariance and the instrument reconstruction response are needed before assigning statistical weight to the peaks or their neighbouring troughs. The published variability classifier also draws on Gaia observations, so matching its label does not supply an independent spectrum or independent photons. ESA's [classifier-result documentation](https://gea.esac.esa.int/archive/documentation/GDR3/Gaia_archive/chap_datamodel/sec_dm_variability_tables/ssec_dm_vari_classifier_result.html) defines the score through classifier confidence ranks; it is not a posterior probability. The [Gaia DR3 variability-processing paper](https://arxiv.org/abs/2206.06416) describes the distinction between general classification and more specific object studies.

Each of these five current contact-sheet panels is XP only. Two other records for 2208124536065383424 and one for 4565045873343899136 have unresolved flux units and remain withheld. Their historical existence is not independent present-day Fλ corroboration. The five-object visual selection also precludes an occurrence-rate or enrichment claim; five matches out of five is a descriptive result for this selected subset.

## Scientific consequence and next discriminating observation

A static, isolated white-dwarf atmosphere cannot be assumed for this subset merely because a colour pipeline produces a finite value or a curve resembles an absorption spectrum elsewhere. The immediate research consequence is to carry the existing variability and classifier qualifications into any object-level interpretation. A useful next test would combine independent optical spectroscopy with contemporaneous photometry and published Gaia epoch information. It should test whether spectral morphology and continuum colour change together, while keeping classifier output separate from a physical atmosphere likelihood. This is a proposed test; no variability period, binary solution or atmosphere model was fitted here.

## Offline reproduction and verification

From the repository root, with the core research environment:

```bash
.venv-research/bin/python research/outlier_followup/additional_gaia_feature_review.py --analyze
.venv-research/bin/python research/outlier_followup/verify_targeted.py
```

Analysis reuses saved files. The first command also uses the exact survey-cache exports recovered for the bounded queue; the verification command uses the ten small retained exports in this and the earlier diagnostics directory and needs no network or full cache. Optional `--fetch` is an acquisition operation and refuses to overwrite an existing Gaia response. The query provenance records the acquisition-time code hash; the analysis records the current code hash, including the later local plotting-cache configuration.

## 日本語の要点

全件目視から選んだXPの局所的な山5例を公式Gaiaに照合すると、5例すべて既に`VARIABLE`でした。内訳は分類器の`CV`が3例、`S`が1例、分類器の行がないものが1例です。新しい変光天体の発見ではありません。元のXP書き出し5本と局所窓10枚も実見しましたが、相関のある再構成であり、誤差共分散や独立分光を加えた検出ではありません。未検証単位の別記録3本は引き続き保留です。静的な単独白色矮星の色・組成として扱う前に、既知変光という情報を含めて個別の物理解釈を見直す必要があります。
