# Independent contact-sheet visual review: pages 12–22

## Scope and result

**All 11 requested pages were opened in the image viewer at original resolution, and all 161 object panels were visually inspected.** Pages 12–21 contain 16 panels each; page 22 contains one. These are the latter 161 of the full 337-object strong-outlier contact-sheet index. The other 176 objects are outside this reviewer's assigned scope.

The 161 objects have **241 stored record rows, of which 227 pass the existing usable-screen filter**; 119 objects have just one stored record. Each object has an individual visual observation below. This is an assistant review of prepared spectral plots and existing audit metadata, not inspection of every original detector image, uncertainty array or Gaia coefficient covariance. No measurement was removed or changed because of these pictures.

## Display interpretation

The curves use raw archive flux (flux_original where available), averaged into 40 Å / 4 nm bins **only for display**. Each spectrum has its own median normalization at 5200–5500 Å, with a median-absolute-flux fallback for a non-positive/non-finite anchor. An absorption-rich anchor can change apparent amplitudes; coincidence there is not absolute-flux agreement. The ordinate is fixed at −0.2 to 3.2 and the displayed wavelength interval is 360–830 nm. Many excursions exceed these bounds. Signed finite samples are retained, but binning can conceal narrow positive/negative features. Numerical audit metrics use untrimmed input and, when available, calibrated flux; their colour differences are not the separation of these raw plotted curves.

Only DESI, SDSS and Gaia XP source types are drawn, and duplicate raw SHA256 values are suppressed. Unsupported source types are not plotted. Stored records, displayed curves and independent observations are different counts. Lines connect occupied bins; a straight segment by itself is not evidence of a wavelength gap. There are no error bars. Catalogue DQ/DZ labels are inherited, not classifications established by this review.

Oscillatory XP curves require coefficient-covariance/extraction checks before physical interpretation. A positive feature need not be a stellar emission line; a negative feature need not identify a particular reduction failure. Neither absence of negative pixels nor smoothness is a validation criterion.

## Priority cases and numerical cross-checks

- **Broad continuum disagreements:** WD 2307−012 (13/12), WD 0930+010 (13/13), LP 444−33 (13/15), SDSS J151835.63+050627.5 (14/15), PM J12476+0646 (17/5), WD 0158−008 (19/13), SDSS J120154.70+340055.9 (19/16) and LHS 2534 (20/14) visibly have different slopes among representations. Their existing between-record uv separations are respectively 0.04047, 0.03041, 0.02835, 0.02914, 0.01800, 0.06543, 0.02900 and 0.02404. These are descriptive separations, not independent-error significances. Match observation IDs, release/format, units, flux transformations, calibration and positional identity before averaging or invoking variability.
- **WD 0158−008 is a useful provenance test:** direct-SDSS record 1db145aa2962c5dcc613 has recorded median pixel S/N 27.13, and DESI ec488c3004906a63b81a has S/N 31.35. The dramatic raw slope disagreement cannot simply be dismissed as low S/N. These plots do not determine whether the cause is epoch, identity, representation or calibration.
- **Known Gaia variable 1245262790370992256 (16/14):** both SDSS and XP show strong positive features near 486 and 656 nm. The separate official-Gaia acquisition records VARIABLE and a best classifier class CV; this classification is not a confirmed physical diagnosis. A constant-DQ colour interpretation is unsafe. Current SDSS record 2fddb71dbc23c1e0ad48 is uncalibrated. See [the independent variability audit](../external_validation/README.md) and [frozen classifier result](../external_validation/results/known_variable_followup.json).
- **Narrow-feature/raw-pixel checks:** 2629980411471669632 (16/11) has several clipped SDSS spikes and raw visible negative-sample fraction 12.54% (record e0d5f0913108b4016901). 2802900781266410112 (18/4) has a deep negative feature near 558 nm and negative fraction 13.41%. For 3688869246424920448 (15/12), the SDSS negative fraction is 16.70%, versus DESI 1.61%, and DESI median pixel S/N is 5.56. These are sample fractions, not lost-flux fractions or rejection probabilities. At 21/9, 1060188315963488640 has a strong SDSS-only feature near 556 nm and an existing sky-mask-sensitivity flag. Inspect native errors/masks and retain signed/masked sensitivity results.
- **A new follow-up hypothesis, not a discovery:** XP-only 5078976609103251456 (20/5), 2163612727665972096 (21/8) and 2002597083798483200 (22/1) have conspicuous positive features around 655–660 nm. None has a calibrated ground spectrum or native pixel S/N in this audit; zero raw negative fraction does not establish quality. Covariance-aware feature tests, Gaia variability/classification checks and independent ground spectra could distinguish emission-bearing objects from representation effects. Visual resemblance to the known-variable case does not classify these objects as CVs.
- **Do not diagnose gaps from appearance:** SDSS J073957.64+302439.8 (12/3) has a straight-looking red segment, but its recorded raw largest visible sampling gap is only 18.995 Å (23556962cb85b246d2ab). Its cause remains unresolved.
- **Counts and identity:** 3075976794811325952 (20/13) and 864943569460727040 (21/10) each have two stored records but only one supported XP curve; their extra records are excluded other-ground/archive formats. LHS 2534 has eight rows, five unsupported and three supported. 2739231150982741760 (20/3) has three rows but only DESI/XP supported. The bright neighbour of 1182083542272959232 (12/1) requires image-level assessment. At 20/4, a DR2-name/DR3-entity mismatch requires release mapping rather than automatic rejection.

Two methodological experiments follow from these observations: measure continuum-colour changes for matched observation IDs across archive representations, and estimate the false-positive rate of XP-only outlier/positive-feature selection using covariance-aware null simulations and independent spectra. The visual sample alone cannot estimate that rate or establish a new atmospheric mechanism.

## Per-object ledger

Every row below was visually inspected. Wavelengths are approximate readings from 4 nm-binned plots, not fitted centroids. “No gross break” describes the display and is not a clean-source judgment. Records are total stored / existing usable-screen rows. Existing flags are copied from object_review.csv:

- **G:** no calibrated ground spectrum; **D:** discordant records; **C:** calibration-sensitive; **N:** negative flux in visual response.
- **E:** legacy positional identity needs an epoch check; **P:** published comparison target; **S:** sky-mask-sensitive.
- **B:** neighbour within 10 arcsec; **W:** bright-neighbour wings require image review; **V:** published Gaia variable requires epoch-resolved colour.
- A dash indicates no listed flag, not proof of clean data.

### Page 12 — 16 objects

[Open contact sheet](spectrum_contact_sheets/page_12.png)

| Panel | Entity / name | Records | Existing flags | Individual visual observation |
|---:|---|---:|---|---|
| 1 | gaia:1182083542272959232 | 2/2 | C, B, W | DESI is smooth; XP has large oscillations around a similar broad continuum. Bright-neighbour image review is still needed. |
| 2 | gaia:5341290362323438592 | 1/1 | G | XP has large blue excursions, deep troughs and a positive feature near 650 nm; no separate instrument. |
| 3 | name:SDSS J073957.64+302439.8 | 1/1 | G | SDSS has positive excursions around 560–610 nm and an unusually straight 730–800 nm segment; do not infer a gap from that segment alone. |
| 4 | gaia:3143927674263664768 | 1/1 | G | XP repeatedly crosses the blue display boundaries and oscillates strongly elsewhere. |
| 5 | gaia:1633840370109794432 | 1/1 | N, G | XP blue excursions are off-scale; substantial middle/red oscillations remain. |
| 6 | gaia:6577472380640481536 | 1/1 | G | XP has large repeated peaks and troughs over most of the range. |
| 7 | gaia:3429195278896700928 | 1/1 | G | XP is clipped in the blue, with a smoother middle region and marked red fluctuations. |
| 8 | gaia:6032281365389830272 | 1/1 | G | XP blue flux approaches zero repeatedly; a broad middle maximum precedes a declining, oscillatory red tail. |
| 9 | gaia:5033831864256488832 | 1/1 | G | XP has broad repeated troughs on a declining continuum; blue excursions exceed the red fluctuations. |
| 10 | gaia:5054747702153870592 | 1/1 | G | XP blue excursions are severe; a broad 500 nm trough and red oscillations remain. |
| 11 | gaia:4716418211824896640 | 1/1 | G | XP exceeds the blue ceiling, with broad middle troughs and repeated red fluctuations. |
| 12 | name:SDSS J010651.88+241258.5 | 1/1 | G | SDSS has a steep blue decline and a relatively flat continuum beyond 500 nm; no gross break at this binning. |
| 13 | gaia:4557243498319407488 | 1/1 | G | XP has large excursions across both ends and the middle, some outside the ordinate. |
| 14 | gaia:4406730419580916992 | 1/1 | N, C, G | XP has large blue/middle oscillations and near-zero troughs; the visual continuum alone is insufficient. |
| 15 | gaia:4573582236809330432 | 1/1 | — | SDSS has prominent narrow positive peaks near 405 and 515 nm; their physical origin is undetermined. |
| 16 | gaia:4654450458039688832 | 1/1 | G | XP has clipped blue excursions, a broad 505 nm trough and a declining, oscillatory red tail. |

### Page 13 — 16 objects

[Open contact sheet](spectrum_contact_sheets/page_13.png)

| Panel | Entity / name | Records | Existing flags | Individual visual observation |
|---:|---|---:|---|---|
| 1 | gaia:123296175922161920 | 1/1 | G | XP exceeds the blue ceiling; broad 500–550 nm troughs precede a declining red tail. |
| 2 | gaia:5824436284328653312 | 1/1 | G | XP has extreme blue excursions and large fluctuations continuing through the red. |
| 3 | gaia:1419996177529184128 | 1/1 | G | DESI has strong blue suppression, a broad 475 nm peak and narrower middle depressions; one instrument. |
| 4 | gaia:2686856949684821248 / SDSS J213538.94-004706.5 | 1/1 | C | SDSS has a U-shaped continuum and strong red rise. The DZ:+M label does not independently establish a companion. |
| 5 | gaia:4019145286524870912 / SDSS J113837.86+285342.7 | 1/1 | G | SDSS has deep repeated bands and a strongly rising red continuum that reaches the ceiling. |
| 6 | gaia:1631211055554872192 | 1/1 | G | XP has clipped blue excursions followed by middle troughs and a declining red tail. |
| 7 | gaia:6215148772052338176 | 1/1 | N, G | XP fluctuations span the full range and leave the ordinate; native covariance review is needed. |
| 8 | gaia:2119909923600264960 | 2/2 | G | DESI and XP share broad trough positions and continuum shape; XP oscillations are much larger. |
| 9 | gaia:1078624858218235776 | 2/2 | — | DESI and XP share the broad blue rise/red decline, with strong XP excursions. |
| 10 | gaia:4375784119357032448 | 1/1 | N, C, G | XP fluctuates strongly almost throughout, exceeding the blue display bounds. |
| 11 | gaia:5577567504089935488 | 1/1 | G | XP has high blue excursions, broad troughs and a conspicuous 655 nm positive feature; no ground curve. |
| 12 | gaia:2638932738224859776 / WD 2307-012 | 4/4 | C, D, E, P | MWDD SDSS rises/levels in the red while DESI, direct SDSS and XP decline: a broadband continuum disagreement. |
| 13 | gaia:3841133976031526784 / WD 0930+010 | 4/4 | C, D, E | MWDD SDSS is flatter/redder than DESI, direct SDSS and XP; XP blue excursions also remain. |
| 14 | gaia:4948433998718883968 | 1/1 | G | XP has large blue oscillations and a declining, rippled red tail; one curve. |
| 15 | gaia:1198984345958836864 / LP 444-33 | 4/3 | D, G, E, P | MWDD SDSS rises above the direct-SDSS/XP red continuum; matching band positions do not remove this disagreement. |
| 16 | gaia:6236113362117992832 | 1/1 | G | XP has large blue excursions and a wavy middle/red continuum; one curve. |

### Page 14 — 16 objects

[Open contact sheet](spectrum_contact_sheets/page_14.png)

| Panel | Entity / name | Records | Existing flags | Individual visual observation |
|---:|---|---:|---|---|
| 1 | gaia:2031371479242995584 | 1/1 | G | XP has large blue excursions and a conspicuous narrow 655 nm positive feature. |
| 2 | gaia:1378879184294054528 | 1/1 | G | DESI has broad depressions near 470, 510 and 550 nm on a declining continuum; one instrument. |
| 3 | gaia:1581138333953274368 | 1/1 | G | DESI has a deep 500 nm trough and a broad middle/red plateau; no separate spectrum. |
| 4 | gaia:6695506362632368896 | 1/1 | G | XP has repeated near-zero blue troughs and substantial middle/red oscillations. |
| 5 | gaia:861184515291473536 | 1/1 | G | XP leaves the blue ordinate repeatedly and has marked red fluctuations. |
| 6 | gaia:3862198144918070912 | 1/1 | G | DESI shows deep broad 470–560 nm troughs and a smooth declining red continuum. |
| 7 | gaia:5855051189175399168 | 1/1 | G | XP is clipped in the blue and has marked red fluctuations, including a 650 nm positive feature. |
| 8 | gaia:687914432080614528 / SDSS J091621.36+254028.4 | 5/3 | E, P | Several SDSS curves and XP share blue suppression and middle bands; small continuum differences and provenance/epoch identity remain. |
| 9 | gaia:2472075114200625792 | 1/1 | G | DESI has a steep blue continuum, broad middle troughs and a smooth red decline. |
| 10 | gaia:503422703132016384 | 1/1 | G | XP approaches zero in the blue and rises to a broad middle maximum before declining. |
| 11 | gaia:3279388782412362624 | 1/1 | C, G | XP has large blue fluctuations and a sharp 655 nm positive feature above broad repeated bands. |
| 12 | gaia:1549432305553266816 | 1/1 | G | XP blue values reach the floor; large middle/red oscillations include deep red-transition troughs. |
| 13 | gaia:1691957732959636608 | 2/2 | — | DESI and XP show deep bands and a rise toward 600 nm; XP endpoints fluctuate strongly. |
| 14 | gaia:5787829449134743936 | 1/1 | G | XP has severe blue excursions and substantial middle/red oscillations. |
| 15 | gaia:1156006287558141056 / SDSS J151835.63+050627.5 | 4/4 | D, E | MWDD SDSS rises/levels in the red while DESI/direct SDSS decline; normalization only aligns the anchor. |
| 16 | gaia:3204436719718449280 | 2/2 | — | J0429-0354: DESI and XP share broad continuum and blue suppression, with remaining XP fluctuations. |

### Page 15 — 16 objects

[Open contact sheet](spectrum_contact_sheets/page_15.png)

| Panel | Entity / name | Records | Existing flags | Individual visual observation |
|---:|---|---:|---|---|
| 1 | gaia:1261253842671908096 / SDSS J150126.78+210056.9 | 3/3 | E, P | Two SDSS representations closely share the broad bands; XP agrees beyond the noisy blue edge. Check provenance before counting independent observations. |
| 2 | gaia:3705025573363213952 | 2/2 | D, G | DESI and XP roughly agree in the red, but XP has large blue excursions; numerical disagreement is still material. |
| 3 | gaia:2683345934175922176 / LSPM J2201+0219 | 4/4 | C, D, E | DESI is flatter toward the red than SDSS; XP oscillates around a declining trend. |
| 4 | gaia:2605449241904257792 | 1/1 | G | XP has clipped blue excursions and large repeated middle/red fluctuations. |
| 5 | gaia:2076798828590802816 | 1/1 | G | XP leaves the blue ordinate and has broad middle troughs plus red ripples. |
| 6 | gaia:5578736014371090944 | 1/1 | G | XP has repeated broad depressions on a declining continuum; red fluctuations are smaller. |
| 7 | gaia:941091346746943616 | 1/1 | C, G | XP has exceptionally large excursions at both ends and in the middle, including clipped peaks. |
| 8 | gaia:4545191991882663936 | 2/2 | — | DESI and XP share blue suppression and a broad maximum; XP oscillations remain large. |
| 9 | gaia:2014467548772932864 | 1/1 | N, C, G | XP has extreme blue excursions and repeated large red fluctuations. |
| 10 | gaia:1099452803904038272 | 2/2 | G | DESI and XP share broad structure, but XP sits somewhat higher across much of the middle/red continuum. |
| 11 | gaia:6369368983082159360 | 1/1 | G | XP has near-zero/clipped blue flux and strong broad middle/red oscillations. |
| 12 | gaia:3688869246424920448 | 2/2 | S, N, D, G | SDSS is higher and more irregular in the blue than DESI, with extra narrow red excursions. |
| 13 | gaia:5896955467094484992 | 1/1 | G | XP has large blue excursions and deep red troughs around a fairly level middle continuum. |
| 14 | gaia:1760134536282476160 | 1/1 | G | XP has near-zero blue troughs and repeated middle/red oscillations. |
| 15 | gaia:425167368208643840 | 1/1 | G | XP has prominent blue/middle peaks including one near 480 nm, with red fluctuations. |
| 16 | gaia:1289022219283937408 | 2/2 | D, G | DESI is smooth while XP oscillates strongly over almost the whole range; averaging cannot replace covariance. |

### Page 16 — 16 objects

[Open contact sheet](spectrum_contact_sheets/page_16.png)

| Panel | Entity / name | Records | Existing flags | Individual visual observation |
|---:|---|---:|---|---|
| 1 | gaia:5025212277210850816 | 1/1 | G | XP has strong blue excursions, a broad middle maximum and a declining red tail. |
| 2 | gaia:4722337192154893568 | 1/1 | G | XP has clipped blue peaks and deep middle troughs, then a declining red continuum. |
| 3 | gaia:5564078248764661376 | 1/1 | G | XP has large blue positive excursions and a deep depression around 500 nm. |
| 4 | gaia:2594771266012029952 | 1/1 | G | XP blue values leave the ordinate; large middle oscillations precede a declining red tail. |
| 5 | gaia:6667696969081244928 | 1/1 | G | XP has severe blue excursions and deep middle/red troughs. |
| 6 | gaia:5503523745374993536 | 1/1 | G | XP has a low blue endpoint, marked middle peaks/troughs and a declining red tail. |
| 7 | gaia:913810126798863232 | 2/2 | G | DESI and XP share broad bands; large XP excursions persist. Integrated-colour agreement does not validate every feature. |
| 8 | gaia:1675053875554148352 | 1/1 | N, G | XP repeatedly approaches/crosses zero across blue/middle wavelengths, with large red oscillations. |
| 9 | gaia:4517866516602288512 | 1/1 | N, C, G | XP has severe blue excursions and considerable middle/red fluctuations. |
| 10 | gaia:5514628164276531840 | 1/1 | G | XP has large repeated peaks and troughs over almost the full range. |
| 11 | gaia:2629980411471669632 | 1/1 | N, G | SDSS has very tall narrow positive spikes near 470, 505, 630 and 665 nm, clipped by the ordinate. |
| 12 | gaia:4969601895360102144 | 1/1 | G | XP has repeated strong oscillations throughout, especially in the red, and near-zero troughs. |
| 13 | gaia:2957248776169007616 | 1/1 | G | XP has repeated blue excursions and a broad 510 nm trough; the red declines more smoothly. |
| 14 | gaia:1245262790370992256 | 2/2 | G, V | Known Gaia variable: SDSS and XP both show strong positive peaks near 486 and 656 nm. Agreement does not justify a constant-DQ interpretation. |
| 15 | gaia:4550965664882006144 | 1/1 | G | XP has clipped blue excursions and large middle/red peaks and troughs. |
| 16 | gaia:306779618349361920 / LSPM J0107+2650 | 2/2 | C, D | XP and SDSS share the broad continuum, but XP lies higher in the red and fluctuates more in the blue. |

### Page 17 — 16 objects

[Open contact sheet](spectrum_contact_sheets/page_17.png)

| Panel | Entity / name | Records | Existing flags | Individual visual observation |
|---:|---|---:|---|---|
| 1 | gaia:886501797019233920 / SDSS J071011.41+303041.6 | 4/4 | D, G | One SDSS curve develops extra red flux/a step around 600 nm relative to the others and XP. |
| 2 | gaia:5520131219981869568 | 1/1 | G | XP has clipped blue peaks and large middle/red oscillations approaching zero. |
| 3 | gaia:4958557266698832896 | 1/1 | G | XP is clipped in the blue with deep middle troughs and substantial red ripples. |
| 4 | gaia:985839270973984512 | 2/2 | D, G | DESI and XP share broad troughs, but XP has extra continuum/endpoint excursions; colour disagreement remains unresolved. |
| 5 | gaia:3709565658737443200 / PM J12476+0646 | 6/4 | C, D, E, P | SDSS representations separate markedly toward the red, spanning rising/falling slopes; DESI/XP lie between. |
| 6 | gaia:3088437177836191360 | 1/1 | G | XP has clipped blue excursions, broad middle oscillations and an irregular red decline. |
| 7 | gaia:2590183003988836736 | 1/1 | S, N, G | SDSS is jagged with a broad maximum and declining red flux; numerical signed-flux/sky-mask flags need raw review. |
| 8 | gaia:1295063619067459712 / SDSS J150228.71+374452.9 | 4/4 | C, D, E | MWDD SDSS levels/rises in the red while DESI/direct SDSS decline; XP has large blue excursions. |
| 9 | name:SDSS J011749.68+003900.5 | 1/1 | G | SDSS is roughly flat/noisy with a narrow positive excursion near 795 nm. |
| 10 | gaia:4534129393091539712 | 1/1 | G | XP has prominent positive peaks near 550 and 655 nm, plus clipped blue flux; origin unresolved. |
| 11 | gaia:1850813214437017984 | 1/1 | G | XP has repeated blue oscillations, a broad 500 nm trough and a declining red tail. |
| 12 | gaia:4898880590203092992 | 1/1 | G | XP approaches zero in the blue, reaches a broad middle maximum and then declines. |
| 13 | name:SDSS J012110.32+150433.3 | 1/1 | S, N, G | SDSS has deep/negative blue excursions and increasing red irregularity, with several near-zero troughs. |
| 14 | gaia:1371680612947121152 | 1/1 | G | DESI has broad middle depressions and a smooth red decline; one instrument. |
| 15 | gaia:2723767413291151488 | 1/1 | G | DESI has strong blue suppression and substantial 460–620 nm structure; one instrument. |
| 16 | gaia:3884925157638345856 / SDSS J104658.12+132911.3 | 1/1 | C, P | SDSS rises from low blue flux to a nearly flat red plateau; no gross break at this binning. |

### Page 18 — 16 objects

[Open contact sheet](spectrum_contact_sheets/page_18.png)

| Panel | Entity / name | Records | Existing flags | Individual visual observation |
|---:|---|---:|---|---|
| 1 | gaia:649163347350787200 | 2/2 | D, G | DESI is higher than average XP blue/middle flux in places; red tails are closer, but XP oscillations are large. |
| 2 | gaia:643989938983182080 | 1/1 | G | XP has a low/clipped blue endpoint and repeated middle/red ripples. |
| 3 | gaia:2513256394506328832 | 2/2 | G | DESI and XP share a declining continuum and broad bands; XP blue fluctuations are large. |
| 4 | gaia:2802900781266410112 | 1/1 | S, N, G | SDSS has strong red scatter and a deep narrow negative feature near 558 nm; hotDQ: is a catalogue label, not a quality pass. |
| 5 | gaia:3131070367541545984 | 1/1 | G | XP has large blue peaks and middle troughs, with sizeable red oscillations. |
| 6 | gaia:625669292125492096 / SDSS J101959.51+204553.4 | 1/1 | — | SDSS rises from blue suppression to a broad maximum; an isolated positive 550 nm feature needs native-pixel review. |
| 7 | gaia:2837433589637545856 | 2/2 | D, G | XP sits above DESI in some blue/middle regions and has much larger excursions. |
| 8 | gaia:1570574230528214400 | 1/1 | N, G | XP has extreme excursions across the full range, many clipped or near zero. |
| 9 | gaia:482146775177135872 | 1/1 | N, G | XP has clipped blue fluctuations and substantial middle/red excursions, high relative to the normalization band. |
| 10 | gaia:5867743023727225088 | 1/1 | G | XP has near-zero blue troughs and large middle/red oscillations. |
| 11 | gaia:60936347458462080 | 1/1 | G | XP has severe blue excursions and repeated broad depressions on a declining continuum. |
| 12 | gaia:4921827187420093568 | 1/1 | G | XP has broad depressions and a declining continuum with smaller red ripples. |
| 13 | gaia:3360357673380278016 | 1/1 | G | XP rises sharply from low blue flux to a broad maximum and declines relatively smoothly in the red. |
| 14 | gaia:3660622479174640640 / WD 1353+000 | 4/4 | C, D, E, P | DESI/SDSS broad bands agree, but a blue continuum offset and legacy provenance/identity cautions remain. |
| 15 | gaia:96167513213751936 / SDSS J013655.67+200429.8 | 1/1 | G, P | SDSS is nearly flat in the red with deep 475 and 510 nm bands; one instrument. |
| 16 | gaia:158445436654807680 | 1/1 | G | XP has clipped blue excursions, pronounced middle troughs and repeated red ripples. |

### Page 19 — 16 objects

[Open contact sheet](spectrum_contact_sheets/page_19.png)

| Panel | Entity / name | Records | Existing flags | Individual visual observation |
|---:|---|---:|---|---|
| 1 | gaia:1247729574771529728 / SDSS J134203.60+181332.8 | 1/1 | G | SDSS has very low blue flux, a broad rise and a nearly flat red plateau; smoothness alone does not validate calibration. |
| 2 | gaia:5107534838790080768 | 2/2 | D, G | DESI and XP share broad troughs; XP has larger endpoint oscillations and residual continuum mismatch. |
| 3 | gaia:1095412274766409728 | 1/1 | G | XP has severe blue excursions and substantial repeated middle/red fluctuations. |
| 4 | gaia:4665368917740216704 | 1/1 | G | XP has repeated blue/red oscillations around a broad middle plateau, with low blue troughs. |
| 5 | gaia:3498518529249147904 | 1/1 | G | XP is clipped in the blue with deep broad middle troughs and an oscillatory red decline. |
| 6 | gaia:4445170067643613312 | 2/2 | G | DESI/XP share the declining continuum and major bands, with endpoint and band-depth differences. |
| 7 | gaia:2199343831922256128 | 1/1 | G | XP has large repeated peaks/troughs throughout, including near-zero red minima. |
| 8 | gaia:5749412925173461888 | 1/1 | G | XP has clipped blue excursions and repeated middle/red fluctuations. |
| 9 | gaia:4465315800722467072 / SDSS J161811.41+164647.2 | 2/2 | C, D, G | SDSS rises strongly in the red while XP is flatter/declining: a major broadband disagreement. |
| 10 | gaia:2482684508055379584 | 2/2 | G | DESI and XP are broadly similar, but XP has large excursions and lies higher in some middle/red regions. |
| 11 | gaia:6743673497438569984 | 1/1 | G | XP has severe blue excursions and a declining oscillatory red continuum. |
| 12 | gaia:3705179706854089856 | 2/2 | G | DESI/XP share broad bands but differ in blue flux and band depth; XP endpoints fluctuate strongly. |
| 13 | gaia:2506764706057099520 / WD 0158-008 | 4/4 | D, E | WD 0158-008: direct SDSS is dramatically bluer than DESI/XP; MWDD SDSS is much flatter. |
| 14 | gaia:3936036638555796224 | 1/1 | G | XP has strong blue excursions and repeated middle/red oscillations. |
| 15 | gaia:6110401696588588672 | 1/1 | G | XP has clipped blue peaks, broad middle troughs and an irregular red decline. |
| 16 | gaia:4028120776036373760 / SDSS J120154.70+340055.9 | 6/5 | C, D, E, P | Several SDSS representations give flatter/higher red flux than DESI/XP despite similar absorption-band positions. |

### Page 20 — 16 objects

[Open contact sheet](spectrum_contact_sheets/page_20.png)

| Panel | Entity / name | Records | Existing flags | Individual visual observation |
|---:|---|---:|---|---|
| 1 | gaia:4565737049547212544 | 1/1 | G | DESI has broad middle troughs and a smooth red decline; one instrument. |
| 2 | gaia:5635366188960145536 | 1/1 | C, G | XP has large blue/red oscillations around a broad middle plateau. |
| 3 | gaia:2739231150982741760 | 3/2 | — | DESI/XP share the broad continuum and 510 nm depression; a third stored record is an excluded format. |
| 4 | gaia:6577159024123317504 | 1/1 | G | XP has near-zero blue troughs and red oscillations. DR2-name/DR3-entity mismatch requires release mapping, not automatic rejection. |
| 5 | gaia:5078976609103251456 | 1/1 | G | XP has conspicuous positive 486 and 656 nm features and clipped blue excursions; inspect classification and native covariance. |
| 6 | gaia:4370302706003791104 | 1/1 | C, G | XP has large blue excursions and sizeable middle/red fluctuations. |
| 7 | gaia:623115504571889280 | 1/1 | G | XP has clipped blue excursions, marked middle structure and red oscillations. |
| 8 | gaia:4553919567291973632 | 1/1 | — | DESI rises from blue suppression to a broad maximum and declines; no gross break, one instrument. |
| 9 | gaia:4452538307377292416 / SDSS J162710.46+091745.8 | 1/1 | G | SDSS has a broad maximum and marked slope change around 590–610 nm, followed by irregular lower red flux. |
| 10 | gaia:3038106453256131968 | 1/1 | N, G | XP has large repeated blue/middle oscillations and near-zero troughs; the red remains irregular. |
| 11 | gaia:1085880432371109888 | 1/1 | G | XP has strong blue excursions and a narrow positive 655 nm feature; no ground comparison. |
| 12 | gaia:992734548910774784 | 1/1 | G | XP has strong oscillations at both ends and broad middle structure. |
| 13 | gaia:3075976794811325952 | 2/1 | G | Only XP is plotted: the second stored record is an excluded other-ground/archive format, not independent confirmation. |
| 14 | gaia:3694399755554510720 / LHS 2534 | 8/3 | C, D | LHS 2534: SDSS rises in the red while DESI/XP decline. Five of eight stored records are excluded formats. |
| 15 | gaia:5257640956502687104 | 1/1 | G | XP has near-zero blue troughs and broad repeated middle/red oscillations. |
| 16 | gaia:5492335733527147520 | 1/1 | G | XP has clipped blue excursions and sizeable middle/red fluctuations with deep troughs. |

### Page 21 — 16 objects

[Open contact sheet](spectrum_contact_sheets/page_21.png)

| Panel | Entity / name | Records | Existing flags | Individual visual observation |
|---:|---|---:|---|---|
| 1 | gaia:5753034063641652608 | 1/1 | G | XP has near-zero blue troughs, a broad middle maximum and a declining red tail. |
| 2 | gaia:144382438121663104 | 1/1 | G | XP has strong blue excursions and broad middle depressions; the red also oscillates. |
| 3 | gaia:4882772946717904768 | 1/1 | G | XP has large blue fluctuations, a deep middle trough and a near-zero red trough around 700 nm. |
| 4 | gaia:5323740434455153536 | 1/1 | G | XP exceeds the blue ceiling and has a positive 655 nm feature above its declining red continuum. |
| 5 | gaia:3802061627746956928 / 2QZ J110006.3-015548 | 2/2 | D, G | DESI/XP share steep blue-to-red decline and bands, with larger XP endpoint excursions and residual continuum differences. |
| 6 | gaia:2626215035118668928 | 1/1 | G | XP has clipped blue excursions and repeated substantial red oscillations. |
| 7 | gaia:3919126669412202880 / WD 1203+125 | 1/1 | G | XP has strong blue oscillations, broad middle troughs and declining red flux. |
| 8 | gaia:2163612727665972096 | 1/1 | G | XP has conspicuous positive 486 and 656 nm features; prioritize covariance/classification follow-up without asserting line identity. |
| 9 | gaia:1060188315963488640 / SDSS J110644.27+673708.6 | 3/3 | S, C, D | SDSS has a tall isolated positive 556 nm feature absent from the other curves; the existing sky-mask flag is material. |
| 10 | gaia:864943569460727040 | 2/1 | G | Only XP is plotted: the second stored record is an excluded other-ground/archive format. |
| 11 | gaia:2343571101456397056 | 1/1 | G | XP has clipped blue excursions, a deep 505 nm trough and repeated red fluctuations. |
| 12 | gaia:4743708915060460288 | 1/1 | G | XP fluctuates strongly across almost the whole range, with clipped peaks and near-zero troughs. |
| 13 | gaia:4545912820537587328 | 2/2 | G | DESI/XP agree broadly on continuum and major bands; individual trough depths differ and XP oscillations persist. |
| 14 | gaia:2945412847030724224 | 1/1 | G | XP has large blue excursions and substantial middle/red fluctuations. |
| 15 | gaia:3491005871238965632 | 1/1 | G | XP has moderate blue fluctuations and a broad 470 nm trough; smaller red oscillations persist. |
| 16 | gaia:1970965886615954304 | 1/1 | G | XP has strong blue excursions, a broad 500 nm trough and a declining red continuum. |

### Page 22 — 1 objects

[Open contact sheet](spectrum_contact_sheets/page_22.png)

| Panel | Entity / name | Records | Existing flags | Individual visual observation |
|---:|---|---:|---|---|
| 1 | gaia:2002597083798483200 | 1/1 | G | XP has a narrow positive feature near 656 nm reaching about three normalization units, large blue excursions and repeated troughs. This is the only stored spectrum; independent line/colour confirmation is absent. |

## Input hashes and limits

Completed 2026-10-18 16:34 UTC. IDs were read as strings. This additional review performed no new catalogue retrieval or physical fitting. The following hashes identify the local inputs and every inspected image.

| Input | SHA256 |
|---|---|
| contact_sheet_index.csv | 476b5847bb9f8cec83b88a7e2282bea35a198574b9929a314ba84a26b072e445 |
| object_review.csv | 63f90608e966c49b24836b46bc4a8f2575ce4f990d7a147bbcc4f6bea7a2bf9f |
| record_audit.csv.gz | 45e2f26cc53f1ec7eddc77cf5fa1cbfb2b2603469b0644852176238b6d3cbf93 |
| build_review.py | 7b2914f02cf8e55cf1c9d19834951e0444bcb3e0d7b8a41f2970e492b23925b1 |
| spectrum_contact_sheets/page_12.png | 7aaa30235142c069d740c437ed02f2082070087283afd0dd6843f2723c25b80b |
| spectrum_contact_sheets/page_13.png | 15846c9976b0dcb34880543f39f0c8ca92cecf8e3627b15f62de4e8d2150d9c7 |
| spectrum_contact_sheets/page_14.png | f7cb8245efbe154b3e3f7bccb63d2dc5839f5f4ae685bb1c04bd3e0d9a99e2f5 |
| spectrum_contact_sheets/page_15.png | a7c1bec520c9c1172885a184ac502187896ce52ce4737775b10e5a397684ae24 |
| spectrum_contact_sheets/page_16.png | 4c856a775eb0883f8799d7ab3a31605e36d66a9232f395f108e6fcef43c40c95 |
| spectrum_contact_sheets/page_17.png | f100d873cc8cd783ba8a6583e8c625198e0e83aac25a4239616821b41036cd9f |
| spectrum_contact_sheets/page_18.png | a9310bc4866f774c77a6114ce69f2d8ae12200bd20af32f33d02d0c2443bd330 |
| spectrum_contact_sheets/page_19.png | d684052960283503a55c11446fd05158ff63a85e9e6f163fcbddc169835e5bdb |
| spectrum_contact_sheets/page_20.png | dba1327b028e6395a605cfdaf99143da88b1049dad70d2c03f1f55097bfe033c |
| spectrum_contact_sheets/page_21.png | e9c1e555457208d0f96665e5dd7b0dae00278315f597bbca7163e03d10dbe5dc |
| spectrum_contact_sheets/page_22.png | ee190b0baeb592fc4d2801d7eac395292cd479feb708d58bf6e5c70e25c3a8bb |

Native uncertainty/mask checks, matched-observation provenance, covariance-aware XP inference, epoch-resolved variable colours and acquisition/field images remain object-dependent follow-ups. This completes the requested contact-sheet inspection of 161 objects, not those scientific validation tasks. No missing second curve or absent quality flag has been converted into evidence of a clean source.

### 日本語の要点

指定された後半11ページ・161天体を全パネル実見し、一件ごとの目視記録を残した。複数アーカイブ表現の広域傾斜不一致、XP青端の大振幅振動、SDSSの細い正負スパイク、変光既知天体の恒常色としての扱いに注意が必要である。画像だけで原因を決めつけず、原画素・誤差・マスク・同一観測の来歴・時刻と固有運動の検証に戻す。約656 nmの正ピークを持つXP単独例は追加検証の仮説であり、新しい輝線天体群の発見とはしていない。
