# Individual spectrum audit: current and historical evidence

The audit retains all **9,902 frozen records in 6,003 catalogue entity keys**.
The current screen admits **7,473 records**, including **395 strong-colour
records in 308 entity keys**. The historical selection contained 337 strong
entity keys; all 337 were visually reviewed in the 22 retained contact sheets.
An entity key is a catalogue association, not proof that every associated
archive observation is correctly identified or statistically independent.

## Current instrument comparisons

[cross_instrument_pairs.csv](cross_instrument_pairs.csv),
[cross_instrument_summary.json](cross_instrument_summary.json), and
[the comparison figure](cross_instrument_differences.png) use
[corrected_record_screen.csv.gz](../precision/flux_units/corrected_record_screen.csv.gz).
Each included record must have `usable_screen=true`, `status=ok`,
`flux_units_validated=true`, and finite CIE 1960 `u1960` and `v1960`.
Verified Fν records enter only after conversion to Fλ; unresolved conventions
cannot contribute current colours or instrument medians.

For each entity and instrument, take the coordinate-wise medians of eligible
records. Subtract these medians in the order named below. The distance is
`sqrt(delta_u**2 + delta_v**2)`. Each row in the pair table lists the original
zero-based input row indices contributing to both medians. The JSON summary
records the corrected input file SHA256 and the exact selection.

| Instrument pair | Entity pairs | Median distance | 95th percentile distance | Distance ≥ 0.005 | Median Δu | Median Δv |
|---|---:|---:|---:|---:|---:|---:|
| DESI − Gaia XP | 1,170 | 0.002539794 | 0.007008602 | 179 | +0.000351732 | −0.001105905 |
| DESI − SDSS | 437 | 0.002146969 | 0.005781711 | 40 | −0.000173539 | +0.000220357 |
| SDSS − Gaia XP | 583 | 0.002592723 | 0.007515059 | 93 | +0.000676789 | −0.000812277 |

These are **descriptive differences in the selected sample**. They are not
estimates of instrument bias, a complete systematic uncertainty, intrinsic
variability, or a population false-discovery rate. Duplicate copies of one
observation can remain within an instrument; taking medians does not make them
independent. Shared photometric anchors, different epochs, unresolved
positional associations and selection effects also remain relevant. The
figures display every pair on equal geometric scales.

Earlier SDSS comparisons used mixed or unresolved flux conventions. Their
larger medians must not be quoted as current instrument systematics. Both unit
conversion and exclusion of unresolved records change the present sample, so
the difference between old and current medians is not a pure calibration
correction measured on a fixed cohort.

## Inspecting every object

[object_audit.html](object_audit.html) is a standalone searchable table with all
6,003 keys and all 9,902 record histories. It distinguishes current and
historical instrument lists, colour distances, calibrations, eligibility and
raw-to-selected colours. The current strong-outlier view sorts by current
distance. Historical queues retain their original membership. Source URLs,
SHA256 hashes and exact string Gaia identifiers remain available.
The within-entity distance is the maximum among eligible record coordinates;
its value is zero by definition for a single eligible record and supplies no
evidence of replication in that case.

[object_review.csv](object_review.csv) and
[object_dossiers.jsonl.gz](object_dossiers.jsonl.gz) contain the same current
assessments. Columns beginning `current_` come from the validated current
screen. Unprefixed colour and original selection columns describe the frozen
historical audit. Evidence flags beginning `historical_` refer to the original
raw recomputation, including mask and negative-response sensitivity; they are
not newly recomputed physical diagnostics for a subsequently converted flux
convention. Current support and calibration flags use current eligible records.
Thresholds remain exploratory follow-up rules, not statistical significance.

**J1323−0129, Gaia DR3 `3638333660492606976`:** the current dossier retains the
DESI colour candidate (row 14), while SDSS row 13 has unresolved flux units and
no current physical colour. Independent SDSS corroboration is withdrawn.
Gaia XP is unavailable. The historical SDSS value is preserved and labelled for
traceability.

## Historical evidence deliberately retained

[record_audit.csv.gz](record_audit.csv.gz), [object_audit.csv](object_audit.csv)
and [review_queue.csv](review_queue.csv) preserve the original census and
selection. [audited_colour_plane.png](audited_colour_plane.png) shows the
historical 9,023 eligible records and historical representatives; its title
explicitly marks it as superseded for current inference. The corresponding
[current colour plane](../precision/flux_units/corrected_colour_plane.png)
shows the revised selection.

[contact_sheet_index.csv](contact_sheet_index.csv) maps all 337 originally
strong entity keys to their individual panels. All 22 `page_*.png` contact
sheets are preserved byte for byte after the visual audit. The pages show
historical archive flux with 40 Å display-only bins and a common visual
normalization. **Their overlaid ordinates can include different flux-density
conventions**; slope disagreements on these retained images are not physical
cross-instrument colour measurements. The fixed ordinate range can hide
extreme pixels. Current numerical colours come from the validated screen, not
from displayed bins, clipping, or an interpretation of the contact sheets.

The actual individual visual-review records and limitations are in
[visual_review_01_11.md](visual_review_01_11.md) and
[visual_review_12_22.md](visual_review_12_22.md). These preserve observations
made from the original figures, including the investigation that exposed
mixed Fν/Fλ inputs. See the
[flux-convention evidence audit](../precision/flux_convention_audit.md) for
native-pixel evidence and quarantined cases.

## Rebuild the current dossiers and comparisons

From the repository root, after rebuilding the corrected screen:

```bash
python research/outlier_audit/build_review.py --keep-contact-sheets
```

The generator requires the corrected screen and checks its input row,
entity, exact Gaia ID, raw SHA and instrument against the frozen audit before
joining. `--keep-contact-sheets` preserves the previously reviewed image bytes
and panel index; it must be used when updating the current dossiers without a
new visual-review pass. The current comparison summary pins its input SHA256,
so a reader can distinguish snapshots even if later upstream research changes
the current screen.
