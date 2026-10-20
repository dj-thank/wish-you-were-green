# Contact sheets 01–11: independent visual review

Reviewed on 2026-10-18. **All 11 PNGs were actually opened with `view_image` at original resolution (2160 × 1620); every one of their 176 panels was inspected.** The index contains 337 strong-outlier entities in total; this document covers panels 1–176 in their original order, not all 337. Each panel below has its own observation. This is a visual triage of the supplied contact sheets, not an independent re-extraction of every spectrum.

## What the pictures show, and what the audit changed

The sheets show native archive flux, binned into 40 Å intervals **only for display**, divided by the median at 5200–5500 Å (with an absolute-flux fallback), on a fixed −0.2 to 3.2 ordinate. The horizontal axis is nm. They retain finite signed flux values and do not display per-pixel error bars, masks, or the photometric correction used in the colour calculation. Many XP traces exceed the ordinate limits at the blue end; several objects also exceed the upper limit over most of their red spectrum. A curve disappearing at the frame is not a missing spectral interval. Normalization near a deep trough can make the rest of the spectrum appear very tall. A sequence of 40 Å display bins is not a set of independent measurements.

**This actual image review exposed a material spectral-density convention problem.** Repeated cases have a MWDD SDSS curve that is much redder than the directly downloaded SDSS curve. Native-sample comparisons of SHA-verified raw CSV and FITS files establish that some are the same sampled spectrum represented as `F_nu` versus `F_lambda`. Examples inspected here include J083231 (page 03 panel 10), J180302 (10/13), WD 2229−080 (02/10), WD 1156+132 (05/11), and WD 0318−074 (08/01). These differences are not evidence for stellar variability. The independent audit now verifies 149 of the 2,232 MWDD SDSS raw files as Fν-shaped and 504 as Fλ-shaped; 1,579 remain unresolved under strict identity gates. See [the evidence registry](../precision/flux_convention_evidence.json) and [the reproducible comparison script](../precision/flux_convention_audit.py). The gate compares at least 1,000 native samples over at least 3,500 Å; all 653 accepted files in this run actually match 100% of the available visible wavelength grid, with maximum fractional residual below 7.12e−6 after the appropriate transformation and a constant scale. A slope near two alone does not establish the convention.

The SDSS FITS references all give `BUNIT = 1E-17 erg/cm^2/s/Ang`, consistent with the [official SDSS unit documentation](https://www.sdss4.org/dr17/spectro/spectro_basics/). The previous acquisition code explicitly retained an unspecified original convention, while the historical colour pipeline treated `flux_original` as Fλ. Historical frozen values and the supplied raw-unit sheets therefore require their historical interpretation; they are not a validated final discovery catalogue. In particular, an apparently discordant pair must first be put into a common verified convention. Curves that coincide after this operation can share the exact original observation despite having different archive hashes.

### Concrete raw-data follow-ups

| Panel | Object / original row(s) | Verified additional evidence | Consequence |
|---|---|---|---|
| 01/06 | Gaia 2813998628866350976; rows 1279, 1280 | SDSS visible negative-pixel fraction 0.46564 and historical Duv +0.03711; DESI fraction 0.01141 and Duv +0.0009504. | The extreme SDSS outlier is not independently reproduced by its DESI record. Revisit extraction, errors, masking and units before an atmosphere claim. |
| 08/16 | WD 0030+145; rows 959, 961, 962 | SDSS historical Duv −0.01907 versus XP −0.002590 and DESI −0.002334; SDSS negative-pixel fraction 0.12534. | Preserve the discrepant record as evidence to investigate; do not average away its disagreement. |
| 09/03 | Gaia 1661432129076263296; row 8295 | Raw CSV values themselves fall negative around 630–700 nm and recover almost linearly toward the red. In 6400–6500 Å every stored value is negative; this is not solely a cropped display. The file has no error column. | Inspect the original SDSS extraction and mask before interpreting this as an absorption feature. A small adjacent-sample wavelength gap does not diagnose a suspiciously filled continuous interval. Its origin is not established here. |
| 10/07 | WD 0807+463; row 8499 | SDSS visible negative-pixel fraction 0.32671, no uncertainty column in the frozen MWDD export, uncalibrated historical record. | The small contact sheet cannot establish a stable continuum; require a direct extraction with uncertainty and full vertical range. |
| 10/08 | Gaia 1293407827571542528; rows 1973–1975 | SDSS historical Duv −0.01704 versus DESI +0.0008992; negative-pixel fractions 0.31732 versus 0.0003455. | Strong numerical and visual disagreement; investigate measurement representation and errors first. |
| 06/05 | J1323−0129; rows 13, 14 | Broad blue suppression appears in both curves, but the MWDD SDSS convention has no matching direct reference in the frozen inputs and remains unresolved. | The DESI evidence is retained; the SDSS curve is not yet a verified independent second-instrument colour measurement. |

Negative pixels alone do not prove a bad observation: an unbiased noisy estimate may legitimately be negative. The fractions above identify records requiring an error-aware analysis; they are not an automatic clipping rule. No physical absorption species, stellar variability, contaminating source, or detector failure is assigned from these pictures alone.

## Per-object inspection log

Panels run left to right, top to bottom. The ID and name are copied from `contact_sheet_index.csv` and `object_review.csv` without rounding Gaia identifiers. `rows` are the original zero-based indices in the frozen 9,902-record input and include only DESI/SDSS/XP records represented by the plotting code. `SDSS units` reports the later direct-reference identity audit for MWDD SDSS files in that entity; it is separate from the visual observation. `unresolved` means not verified by this particular comparison, not proved Fν. Automated quality flags remain available in [object_review.csv](object_review.csv) and [record_audit.csv.gz](record_audit.csv.gz).

### Page 01

[Open page 01](spectrum_contact_sheets/page_01.png)

| Panel | Object / Gaia ID | rows | Visual observation and specific caution | MWDD SDSS units |
|---|---|---|---|---|
| 1 | Gaia DR2 3030820432081929088 | 69 | XP 青端の大振幅振動が上下の表示範囲外。赤側にも強い細かな凹凸。 | — |
| 2 | WD 1331+005; 3662951038644235776 | 791, 792, 793 | DESI・SDSS に広い谷と約630 nmの山が共通。XP の両端の振動を区別。 | unresolved |
| 3 | Gaia DR2 6745009197907325440 | 3176 | XP 約450 nmより青で上下にクリップ。中央の広い谷と赤側の振動。 | — |
| 4 | SDSS J133359.86+001654.81 | 9506 | SDSS direct に複数の深い広い谷。単一表示曲線で独立再観測までは確認できない。 | — |
| 5 | Gaia DR3 1073663827393917056 | 1150 | DESI に複数の深い谷。約460–550 nmの形が明瞭で、細かな揺れも残る。 | — |
| 6 | Gaia DR3 2813998628866350976 | 1279, 1280 | DESI は滑らかな減少傾向だが SDSS は全域で大きな正負の跳び。最優先で誤差・原抽出を確認。 | unresolved |
| 7 | Gaia DR2 4259121228365719168 | 1187 | XP 青端の大きい振動、中央の広い谷、赤側の周期的な凹凸。 | — |
| 8 | Gaia DR2 5171072763900932480 | 2960 | XP の赤側が大部分上限外。規格化域が谷にある影響と、軸外の値を個別図で確認。 | — |
| 9 | Gaia DR2 5873955745478729984 | 1069 | XP 青側の振動が大きい。中央の広い谷と赤側の緩やかな山は見える。 | — |
| 10 | Gaia DR2 51090628850761088 | 1456 | XP 青側が大きくクリップ。赤側にも繰り返す凹凸。 | — |
| 11 | Gaia DR2 5426155304016807296 | 1159 | XP 青側に加え650–770 nm付近の振動が目立つ。 | — |
| 12 | Gaia DR3 2255562926592151808 | 675 | XP が青・赤の両側で上限・下限を頻繁に越える。小図から精密な連続成分を読まない。 | — |
| 13 | Gaia DR2 1087367040811588224 | 1916 | XP 青側の振動が大きく、赤側に複数の細かな谷。 | — |
| 14 | Gaia DR2 6312858487757223296 | 1901 | XP 約480 nmでゼロ近くまで落ちる谷。青側のクリップと赤側の振動。 | — |
| 15 | GJ 3614; 3553682127126319360 | 991 | GJ 3614：広い約500 nmの谷と550–650 nmの幅広い山。XP 曲線は他のXP例より滑らか。 | — |
| 16 | Gaia DR3 1385277929651467648 | 953, 954 | DESI とXPで広い谷の位置は似るが赤側の高さが違う。XP は全域で振動が大きい。 | — |

### Page 02

[Open page 02](spectrum_contact_sheets/page_02.png)

| Panel | Object / Gaia ID | rows | Visual observation and specific caution | MWDD SDSS units |
|---|---|---|---|---|
| 1 | SDSS J114136.53+383611.9; 766499483055284864 | 1162, 1163, 1164, 9537 | 複数の地上曲線で谷の位置・形がほぼ重なる。XP は青端と赤側で大きく振動。 | flambda |
| 2 | Gaia DR3 1136291253798320512 | 893 | DESI に繰り返す広い深い谷。単独装置の裏付けに留まる。 | — |
| 3 | Gaia DR3 1314632142902900864 | 64 | DESI の青〜中央が不規則で、赤側の山が高い。負フラックス・誤差を確認。 | — |
| 4 | Gaia DR2 1523861990123367808 | 844 | XP 青端が極端な振動で見切れ、赤側も不規則。 | — |
| 5 | Gaia DR2 2704122988794215168 | 922 | DESI の深い複数の谷と赤側の減少が明瞭。校正感度は別途確認。 | — |
| 6 | WD 0933+006; 3841045053027974912 | 912, 913, 914 | WD 0933+006：MWDD SDSS の赤側が急に高くなり上限外。DESI・XPとの表現／校正差を未解決として保持。 | unresolved |
| 7 | Gaia DR3 1628641771759023232 | 1121 | XP 青側の多くが表示範囲外。赤側にも大きい山谷が連続。 | — |
| 8 | Gaia DR2 1632737005895324672 | 1894 | XP 青端の振動。中央の谷と赤側の小さい凹凸。 | — |
| 9 | Gaia DR2 6728838955276744832 | 1233 | XP 青端が強くクリップし、中央〜赤側にも大きな凹凸。 | — |
| 10 | WD 2229-080; 2621565333592122496 | 1569, 1570, 1571, 9199 | WD 2229−080：一つのSDSS曲線だけ赤側が高く平坦。他の地上曲線は減少。後述のFν表現差を確認済み。 | fnu |
| 11 | Gaia DR2 5494231295867704064 | 823 | XP 青側に激しい振動。赤側の大部分が上限外で、中央の一部は下限外。 | — |
| 12 | Gaia DR2 15592281767723392 | 512 | XP 青側と650–750 nmの振動。広い谷の位置は読み取れるが細かい構造は保留。 | — |
| 13 | SDSS J131146.94+292351.14 | 9491 | SDSS direct の複数の深い谷と赤側の連続成分が明瞭。 | — |
| 14 | WD 1309+296; 1462641629366243712 | 665, 666 | WD 1309+296：SDSS の赤側が上限外へ上昇、XP は比較的低い。単位・校正の照合が必要。 | unresolved |
| 15 | Gaia DR2 2201461976641376512 | 1568 | XP 青側の振動が大きい。中央〜赤側は比較的低振幅。 | — |
| 16 | Gaia DR2 5207394168452773888 | 1148 | XP 青端のクリップと赤側の不規則な凹凸。 | — |

### Page 03

[Open page 03](spectrum_contact_sheets/page_03.png)

| Panel | Object / Gaia ID | rows | Visual observation and specific caution | MWDD SDSS units |
|---|---|---|---|---|
| 1 | Gaia DR3 2172419369130721792 | 2435 | XP 青端の大きいクリップと赤側の繰り返す振動。 | — |
| 2 | LP 426-49; 684598618544000384 | 631, 632, 9372 | LP 426−49：二つの地上表示曲線がほぼ重なる。XP は赤側でやや低く凹凸が増す。 | flambda |
| 3 | Gaia DR3 1952024153127649664 | 1035 | XP 青端と赤側の双方に大きい振動。 | — |
| 4 | Gaia DR2 4553956847607826816 | 1103 | XP 青側が不規則。650 nm以降の鋭い上下動が目立つ。 | — |
| 5 | Gaia DR3 970900343926548224 | 2257 | XP の青から赤まで大きく繰り返す振動。連続成分の安定性を別途評価。 | — |
| 6 | WD 1235+422; 1534384148897669248 | 535, 537 | WD 1235+422：SDSS の赤側が高くほぼ平坦、XP は低く減少。未確認の表現差を物理変動と解釈しない。 | unresolved |
| 7 | SDSS J094454.66+320652.6; 793161574876944640 | 8469, 9603 | SDSS とSDSS direct の曲線がほぼ重なる。原観測の共有を確認して独立性を数えない。 | flambda |
| 8 | WD 1328+648; 1666074615061406336 | 1 | WD 1328+648：青側はゼロ近辺、赤側へ増加し細かな揺れが大きい。DC分類だけから原因を決めない。 | unresolved |
| 9 | Gaia DR3 717311181119046528 | 1153 | XP 青側が上下に見切れ、赤側も大きく振動。 | — |
| 10 | SDSS J083231.57-040807.8; 3065744460430556032 | 2583, 2584, 2585, 9184 | J083231：MWDD SDSSだけ赤側が高い。直接SDSSとDESIはよく重なる。Fν/Fλ差を同一標本で確認済み。 | fnu |
| 11 | Gaia DR2 5803741173388493440 | 401 | DZ：XP青側が弱くゼロ付近を上下。中央の幅広い山と赤側の小さい凹凸。 | — |
| 12 | Gaia DR2 5598574704531141120 | 1677 | XP に広い複数の谷。青端の振動はあるが赤側の振幅は比較的小さい。 | — |
| 13 | Gaia DR2 3114596105649038208 | 420 | XP の中央に複数の深い谷。青側は大きく振動。 | — |
| 14 | Gaia DR3 5377768168101100928 | 2470 | XP の広い谷と赤側の振動。独立な地上曲線なし。 | — |
| 15 | SDSS J225901.16+215843.9; 2835808683249711744 | 1577, 9527 | J225901：SDSS direct とMWDD SDSSで赤側の傾きが大幅に異なる。直接対応の厳格検定は未解決。 | unresolved |
| 16 | WD 1111+020; 3810552434493888768 | 810, 811, 812 | WD 1111+020：各曲線の広い谷は似るがSDSSだけ赤側が増加。単位・校正の確認を優先。 | unresolved |

### Page 04

[Open page 04](spectrum_contact_sheets/page_04.png)

| Panel | Object / Gaia ID | rows | Visual observation and specific caution | MWDD SDSS units |
|---|---|---|---|---|
| 1 | Gaia DR3 4303181957853467904 | 853 | XP 青側の大振幅クリップと中央〜赤側の凹凸。 | — |
| 2 | SDSS J090632.17+470235.8; 1012210992942502144 | 705, 706, 707, 9563 | 複数の地上曲線で谷が共通。赤側に軽い高さの違い、XPに大きい振動。 | flambda |
| 3 | Gaia DR3 4510354069045617408 | 1679 | XP 青端と650–720 nmで大きい振動。 | — |
| 4 | Gaia DR3 4835710657888494848 | 1903 | XP 複数の広い谷。青側と赤側にも細かな振動。 | — |
| 5 | WD 0805+468; 929774314079963264 | 636, 637, 9547 | WD 0805+468：地上曲線同士は重なり、XPの振動が目立つ。重複原観測の独立性を確認。 | flambda |
| 6 | Gaia DR2 4589316969764785024 | 2407 | XP 青側の強い凹凸と中央の広い谷。赤側は中程度の振動。 | — |
| 7 | SDSS J111341.33+014641.72 | 9482 | SDSS direct に一つの幅広い深い谷と赤側の緩やかな減少。 | — |
| 8 | Gaia DR2 5911947273786170496; 5911947273786682624 | 1645 | XP に複数の広い谷。索引のGaia IDと表示名のDR2 IDは異なり、世代対応の来歴を保持。 | — |
| 9 | LP 315-42; 740483560857296768 | 7, 8, 9 | LP 315−42：三装置の広い谷が共通だが約620 nm以降は全曲線が上限外。赤側の全体像はこの図では見えない。 | unresolved |
| 10 | Gaia DR2 19399306419780224 | 1550, 1551 | DESI とXPの谷の位置は概ね似る。XPは青側で特に大きく振動。 | — |
| 11 | Gaia DR3 5628855946255729280 | 2354 | XP 青側が上下にクリップ。赤側にも細かな振動。 | — |
| 12 | Gaia DR2 2283760245882786560 | 701 | XP に広い複数の谷。青端の振動を分離して扱う。 | — |
| 13 | PSO J186.4406+47.1036; 1542337839923130624 | 1612, 1613, 9539 | PSO J186.4406：地上曲線がよく重なり、XPも広い形は似る。MWDD SDSSのFλ形は直接データで確認済み。 | flambda |
| 14 | Gaia DR3 3782527364866017664 | 1945, 1946 | DESI の広い形は明瞭だがXPは青端から赤側まで激しく上下する。 | — |
| 15 | SDSS J112036.74+010629.3; 3798221652107253760 | 1088 | SDSS に複数の深い谷。小さい不規則な揺れが残る。 | unresolved |
| 16 | Gaia DR3 6534571635948347648 | 2336 | XP 青端が大きくクリップし赤側も振動。 | — |

### Page 05

[Open page 05](spectrum_contact_sheets/page_05.png)

| Panel | Object / Gaia ID | rows | Visual observation and specific caution | MWDD SDSS units |
|---|---|---|---|---|
| 1 | Gaia DR3 6493691450030410496 | 1940 | XP の複数の深い谷。青端の大きい振動と赤側の細かな揺れ。 | — |
| 2 | Gaia DR2 5012284833670868736 | 2127 | XP 約500 nmの谷がゼロ付近に届く。青側の振動が大きい。 | — |
| 3 | Gaia DR3 194102113412236160 | 1437 | XP 全域の不規則な振動が強く、青側と中央にも下限越え。 | — |
| 4 | Gaia DR2 3962125442437204096 | 101 | DZ：XP青側はほぼゼロで大きく振動。赤側にも大きな凹凸。 | — |
| 5 | SDSS J151417.00+142354.1; 1183073068378187776 | 2101, 2102, 2103, 9544 | 複数の地上曲線で深い谷がほぼ一致。XPの大きい振動を別に評価。 | flambda |
| 6 | Gaia DR2 3711047662972690688 | 826, 827 | J1329+0033：DESI の広い谷と比較してXPの振動が大きい。校正の感度とXP誤差を別途確認。 | — |
| 7 | [SHW2006] J095442.91+091352.3; 3878126391912309760 | 2562, 2563, 9558 | J095442：MWDD SDSSだけ赤側が高い。DESI・SDSS directは低く減少する。 | fnu |
| 8 | Gaia DR2 2935415125246460032 | 1330 | XP 青側が強く振動。中央〜赤側には比較的滑らかな広い谷。 | — |
| 9 | Gaia DR2 1679189040001914880 | 1253, 1254 | DQH：DESI の広い中央の谷に対しXPの青側が激しく振動。 | — |
| 10 | Gaia DR3 5613330292326101888 | 1634 | XP 青端のクリップと赤側の周期的な凹凸。 | — |
| 11 | WD 1156+132; 3919950955240152832 | 1919, 1920, 9189 | WD 1156+132：MWDD SDSSの赤側が高く平坦。SDSS direct・XPは低く減少。Fν表現差を確認済み。 | fnu |
| 12 | Gaia DR3 4979124185749149824 | 667 | XP 青側が大きくクリップ。中央〜赤側も繰り返し振動。 | — |
| 13 | Gaia DR3 2893966728030460544 | 2176 | XP 複数の広い谷と赤側の小さな振動。 | — |
| 14 | Gaia DR3 2435964167342744576 | 3628 | XP 青側・赤側双方の振動が大きい。 | — |
| 15 | SDSS J183500.21+642917.0; 2256422164865057536 | 2568, 2569, 2570, 9142 | 複数の地上曲線に共通の谷。XPは主に青端で大きく揺れる。 | flambda |
| 16 | Gaia DR3 3801262630686591104 | 1105 | DESI の複数の広い谷が明瞭。単独装置表示である点を保持。 | — |

### Page 06

[Open page 06](spectrum_contact_sheets/page_06.png)

| Panel | Object / Gaia ID | rows | Visual observation and specific caution | MWDD SDSS units |
|---|---|---|---|---|
| 1 | Gaia DR3 1811353288304784512 | 2388 | XP 青側が激しく上下し、赤側にも周期的な凹凸。 | — |
| 2 | Gaia DR3 6055175671373717504 | 325 | DZ：XPが全域で大きく振動。青側は負側への見切れも多い。 | — |
| 3 | Gaia DR3 2453225705329412480 | 1106, 1107 | DESI の広い谷に対しXPは大きく振動するが中央の形は概ね似る。 | — |
| 4 | Gaia DR3 6199083700279618816 | 1377 | XP 青端の大振幅振動。中央に複数の谷、赤側にも揺れ。 | — |
| 5 | Gaia DR2 3638333660492606976 | 13, 14 | J1323−0129：両曲線に弱い青側と中央への立ち上がり。赤側はSDSSが低い。SDSS単位は未検証で第二装置の追認は保留。 | unresolved |
| 6 | Gaia DR2 1906327526458564352 | 769 | XP に広い複数の谷。青側・赤側の振動が残る。 | — |
| 7 | Gaia DR3 4770661758988444672 | 2229 | XP 青側の大きい振動。中央〜赤側は低振幅の谷と揺れ。 | — |
| 8 | Gaia DR2 1687084559986707840 | 1327 | XP の谷の連なり。青側の細かい凹凸と赤側の小振動。 | — |
| 9 | Gaia DR2 568089105130012800 | 839 | DZ：青側のXPは弱くゼロ付近。中央の幅広い山と赤側の減少。 | — |
| 10 | SDSS J074414.66+464912.5; 927618687178189056 | 278, 279, 280, 281, 8646 | DZ：複数のSDSS表示曲線の幅広い形がほぼ重なる。XPの弱い青側は振動が大きい。 | flambda, unresolved |
| 11 | SDSS J105533.73+372542.7; 774872607698171392 | 670, 671, 8919 | DZ：DESI・SDSSで青側抑制からの立ち上がりが概ね共通。狭い谷は原分解能で確認。 | flambda |
| 12 | SDSS J092909.03+331011.7; 701307621874580864 | 1866, 1867, 9410 | 地上曲線はほぼ重なり、XPは赤側がやや低く振動。 | flambda |
| 13 | Gaia DR2 5124325343418987392 | 2252 | XP の深い約460 nmの谷と他の広い谷。青側の振動あり。 | — |
| 14 | Gaia DR3 1496016553207149952 | 830, 831 | DESI の複数の谷は明瞭。XPは青端と赤側で振動が大きい。 | — |
| 15 | Gaia DR3 1323443938325221376 | 1442, 1443 | DESI とXPで谷の位置は似るがXPの細かな上下動が目立つ。 | — |
| 16 | Gaia DR2 386584233877132416 | 2194 | DQ:：XPに広い約500 nmの谷。赤側は比較的滑らかで、青側に小さな揺れ。 | — |

### Page 07

[Open page 07](spectrum_contact_sheets/page_07.png)

| Panel | Object / Gaia ID | rows | Visual observation and specific caution | MWDD SDSS units |
|---|---|---|---|---|
| 1 | Gaia DR3 1406386937996153344 | 8278 | SDSS の複数の広い谷、青から赤へ大きく減少する連続成分。 | unresolved |
| 2 | Gaia DR2 2324148950103276800 | 1003 | XP 青端の激しい見切れ。深い中央の谷と赤側の幅広い山。 | — |
| 3 | Gaia DR3 1221503714190903296 | 2187 | XP に複数の広い谷。青端の振動と赤側の小さな凹凸。 | — |
| 4 | Gaia DR2 5432581777684448128 | 2264 | XP は比較的滑らかな中央〜赤側の形。青側に細かな揺れ。 | — |
| 5 | Gaia DR2 5511401509966160640 | 1310 | XP の青・赤双方で振動が大きい。中央の広い谷も見える。 | — |
| 6 | Gaia DR3 2797899510893221632 | 2456, 2457 | DESI の谷の位置にXPも類似するが、XPは大きく上下する。 | — |
| 7 | WD 2050-072; 6909994246262080000 | 2218, 2220, 9464 | WD 2050−072：MWDD SDSSの赤側が高く平坦、直接SDSS・XPは減少。 | fnu |
| 8 | Gaia DR2 4520056606339200640 | 10 | XP 青端は大きく揺れるが中央の深い谷と赤側の幅広い山は比較的滑らか。 | — |
| 9 | Gaia DR3 2650081859144423040 | 8326 | SDSS に幅広い中央の窪み。約620 nm以降は大部分上限外。軸外値を個別表示で確認。 | unresolved |
| 10 | Gaia DR2 2047102054631445504 | 128 | XP 青側に強い振動。赤側にも多数の凹凸。 | — |
| 11 | Gaia DR2 5065728108167084032; 5065728112464023424 | 331 | DZ：弱い青側はゼロ周辺で上下し、中央〜赤側も不規則。表示名DR2と索引DR3のID来歴を保持。 | — |
| 12 | Gaia DR2 391292754986384256 | 1529 | XP 青端で上下のクリップ、赤側にも大きい鋭い谷。 | — |
| 13 | Gaia DR2 5597759970724418688 | 899 | DQpec：XP中央〜赤側の複数の谷は滑らか。台帳の非適格記録を外見だけで採用しない。 | — |
| 14 | Gaia DR3 4724971175340169088 | 350 | DZ：XP青端の振動が非常に強く、赤側も大きく上下する。 | — |
| 15 | Gaia DR2 4193463474904213248 | 339 | DZ:：XP青側が大きく振動。中央の広い谷の解釈は原データに戻る。 | — |
| 16 | Gaia DR3 1778812833657756800 | 1446 | DESI の複数の深い谷と滑らかな赤側の減少。 | — |

### Page 08

[Open page 08](spectrum_contact_sheets/page_08.png)

| Panel | Object / Gaia ID | rows | Visual observation and specific caution | MWDD SDSS units |
|---|---|---|---|---|
| 1 | WD 0318-074; 5169190159475821312 | 1955, 1957, 1958, 9481 | WD 0318−074：MWDD SDSSの赤側だけ高く平坦。直接SDSS・DESIは減少。Fν表現差を確認済み。 | fnu |
| 2 | Gaia DR3 4487762193165249792 | 2817 | XP 青側の強い振動とゼロ近傍への谷。赤側にも凹凸。 | — |
| 3 | Gaia DR3 1896105534357500160 | 1952 | XP 中央を含め細かな振動が大きい。広い谷の確度は別途確認。 | — |
| 4 | Gaia DR2 6279455526367838592 | 3406 | XP 青端が大きくクリップし赤側にも繰り返す大きい振動。 | — |
| 5 | Gaia DR3 4114023351792748160 | 2495 | XP の青側と赤側双方が激しく振動。中央の広い谷は見える。 | — |
| 6 | Gaia DR2 4555293235271174016 | 1537, 1538 | DESI とXPで広い谷・赤側減少が概ね似る。XPの青端振動は残る。 | — |
| 7 | Gaia DR3 6034879644498344320 | 2511 | XP 青端の強い見切れと赤側の凹凸。 | — |
| 8 | SDSS J082005.03+520453.5; 1031375235800215680 | 6874, 9557 | SDSS とSDSS directがほぼ重なる。同じ原観測のコピーを独立な追認と数えない。 | flambda |
| 9 | Gaia DR2 5727797557366321024 | 1926 | XP 複数の広い谷、青側はゼロ近傍も含み大きく上下する。 | — |
| 10 | Gaia DR3 4055233289668168448 | 3225 | XP 中央の深い谷と赤側の振動。青側が大きく見切れる。 | — |
| 11 | Gaia DR2 5231326653942790400 | 1498 | XP 青側の上下動と約500 nmの負側への谷。赤側にも揺れ。 | — |
| 12 | Gaia DR3 1619759710670842368 | 397 | XP 青端の激しいクリップ、中央の深い谷と赤側の振動。 | — |
| 13 | Gaia DR2 818833831355548928 | 212, 213 | J0913+4434：DESIの弱い青側・中央の山・約590 nmの広い谷が見える。XPの大きい振動から細部の追認を主張しない。 | — |
| 14 | Gaia DR2 770611347305289984 | 8247, 9103 | DZ：SDSS directとMWDD SDSSがほぼ重なり、弱い青側から中央へ立ち上がる。 | flambda |
| 15 | Gaia DR2 2091088597099984000 | 2073 | XP 青側に多くの振動、中央〜赤側は比較的小さな広い谷。 | — |
| 16 | WD 0030+145; 2780434524599787136 | 959, 961, 962 | WD 0030+145：SDSSの青側は上限外、赤側は強い揺れ。DESI・XPは滑らかな減少で大きく異なる。 | unresolved |

### Page 09

[Open page 09](spectrum_contact_sheets/page_09.png)

| Panel | Object / Gaia ID | rows | Visual observation and specific caution | MWDD SDSS units |
|---|---|---|---|---|
| 1 | Gaia DR3 2524782368741619328 | 4094 | XP 青側の強い周期的振動と赤側の凹凸。 | — |
| 2 | Gaia DR2 3534053469454724224 | 70 | DZ:：XP青側の振動が非常に強く中央にも大きい谷。 | — |
| 3 | Gaia DR3 1661432129076263296 | 8295 | SDSS 約630 nmで急落し、負側から赤側へほぼ直線で戻る区間。原CSVにも確認した異常区間。 | unresolved |
| 4 | Gaia DR3 6522493092697283200 | 1368 | XP 青側の上下動と中央〜赤側の周期的な凹凸。 | — |
| 5 | Gaia DR3 2775678724492967936 | 2279 | XP 中央に複数の谷。青側の小さな揺れと赤側の凹凸。 | — |
| 6 | Gaia DR3 2233443432700228992 | 226 | DZ：XP青側と赤側の細かな上下動が大きい。 | — |
| 7 | Gaia DR2 761677269868775040 | 1350, 1351 | DESI とXPの広い谷は似る。近傍の明るい星についての台帳警告はこのスペクトル図だけでは解決しない。 | — |
| 8 | Gaia DR2 6900915338227553408 | 1349 | XP 青側は激しく上下し、中央〜赤側にも深い谷が連続。 | — |
| 9 | Gaia DR3 1272349121883277312 | 157 | DZ：XP青側が弱く負側まで振動。赤側の細かな凹凸も大きい。 | — |
| 10 | Gaia DR3 5528416345032033152 | 1720 | XP 青端のクリップと複数の広い谷。赤側は小振幅。 | — |
| 11 | Gaia DR2 6374845787939712000 | 136 | DZ：XP青端と650–750 nmで振動が目立つ。 | — |
| 12 | GJ 1276; 2611561706216413696 | 54 | GJ 1276：弱い青側から中央へ緩やかに立ち上がる比較的滑らかなXP。非適格記録の扱いは台帳で確認。 | — |
| 13 | Gaia DR3 4674958033525400704 | 2742 | XP 青側の大きい振動と中央〜赤側の谷。 | — |
| 14 | Gaia DR2 6691814103801080704 | 301 | DZ：XP青側が弱くゼロ付近。中央の山と赤側の小さい凹凸。 | — |
| 15 | Gaia DR3 5037953589751105408 | 81 | DZ：XP青側のゼロ周辺の振動と赤側の大きい凹凸。 | — |
| 16 | Gaia DR3 693196971274079872 | 8414 | DZ:：SDSSに弱い青側からの立ち上がり。約560 nmの突出した点と全域の細かな揺れ。sky-mask感度を確認。 | unresolved |

### Page 10

[Open page 10](spectrum_contact_sheets/page_10.png)

| Panel | Object / Gaia ID | rows | Visual observation and specific caution | MWDD SDSS units |
|---|---|---|---|---|
| 1 | Gaia DR2 271069404823970176 | 93 | DZ:：XP青側はゼロ周辺で上下し、赤側にも大きい振動。 | — |
| 2 | SDSS J102801.74+351257.9; 752814274140797568 | 1134, 1135, 9468 | 地上曲線の谷はほぼ重なり、XPの小さい凹凸が加わる。原観測の共有を保持。 | flambda |
| 3 | Gaia DR2 3690311908759604608 | 604 | J1258+0106：DESIは滑らかな青側抑制と中央の山。既存の汚染・校正検討を図の滑らかさだけで覆さない。 | — |
| 4 | Gaia DR3 2300801885839806848 | 2415 | XP に複数の深い谷。青側の振動と赤側の小さい凹凸。 | — |
| 5 | Gaia DR3 1255460206666687488 | 805 | XP 青側の見切れと赤側の大きく繰り返す振動。 | — |
| 6 | Gaia DR2 6432211608825427328 | 2039 | XP 中央〜赤側の谷は比較的滑らか。青端には細かい揺れ。 | — |
| 7 | WD 0807+463 | 8499 | WD 0807+463：SDSSが全域で大きく揺れ、赤側の多くが上限外。単独曲線の極端な色を採用しない。 | unresolved |
| 8 | Gaia DR3 1293407827571542528 | 1973, 1974, 1975 | DESIは滑らかな減少、MWDD SDSSは大振幅の凹凸。XPも揺れる。観測間差を数値誤差・抽出から確認。 | unresolved |
| 9 | Gaia DR3 949721447873160832 | 3454 | DESI の複数の深い谷と赤側の減少が明瞭。 | — |
| 10 | SDSS J163601.34+161907.18 | 9070 | DZ：SDSS directは弱い青側から中央へ立ち上がり赤側へ減少。単一観測表示。 | — |
| 11 | Gaia DR3 12431632514624512 | 173 | DZ：XP青側が強く見切れ、中央〜赤側も大振幅で上下。 | — |
| 12 | Gaia DR3 547793872828407680 | 2216 | XP 複数の谷。青端の振動と赤側の小さい凹凸。 | — |
| 13 | SDSS J180302.57+232043.3; 4577545533852426624 | 36, 37, 9538 | J180302：MWDD SDSSの赤側が上限へ増加し、SDSS directは低く減少。Fν/Fλ差を同一標本で確認済み。 | fnu |
| 14 | SDSS J010039.50+081401.0; 2580742013037386880 | 1805, 9523 | J010039：二つのSDSS曲線の谷は似るが赤側の傾きが大幅に異なる。厳格な単位照合は未解決。 | unresolved |
| 15 | WD 1338+027; 3713218786120541824 | 1072, 1073 | WD 1338+027：DESI・XPの広い谷と赤側の形がよく似る。XP青端の小振動は残る。 | — |
| 16 | Gaia DR2 4131862957999471744 | 76 | XP に広い中央の窪みと赤側の山。青端の上下動が大きい。 | — |

### Page 11

[Open page 11](spectrum_contact_sheets/page_11.png)

| Panel | Object / Gaia ID | rows | Visual observation and specific caution | MWDD SDSS units |
|---|---|---|---|---|
| 1 | Gaia DR3 2690496260154655616 | 948, 949, 950 | DESI・SDSSの中央〜赤側は概ね似るが、XPは青端から赤側まで大振幅の振動。 | unresolved |
| 2 | GJ 841 B; 6558209044297239424 | 2069 | GJ 841 B：XPの広い谷と赤側減少が滑らか。非適格記録と既発表比較対象の注意は保持。 | — |
| 3 | Gaia DR3 1872385362003961344 | 2315 | XP 青側が大きく振動し、中央〜赤側にも周期的な細かな揺れ。 | — |
| 4 | SDSS J135123.86+264546.5; 1450680729561299840 | 2, 8997 | J135123：二つのSDSS曲線で中央の山・赤側傾きが異なる。厳格な単位同一性検定は未解決。 | unresolved |
| 5 | Gaia DR3 1592611909587317632 | 471 | DESIに幅広い中央の窪み。細かい不規則な揺れが全域にある。 | — |
| 6 | Gaia DR3 788333997276426624 | 293 | DZ：XP青側はゼロ付近で激しく振動、赤側にも大きい凹凸。 | — |
| 7 | WD 0240+008; 2498928486686282368 | 4937 | WD 0240+008：SDSS青端が高く見切れ、赤側の振動と低／負値が目立つ。sky-mask感度を確認。 | unresolved |
| 8 | Gaia DR3 2641890287064121088 | 481, 482 | DESIの滑らかな広い形に対しXPは全域で激しく揺れる。 | — |
| 9 | Gaia DR2 555258461563927552 | 65 | DZ：XP青側は弱いが振動が大きく、赤側にも大きい山谷。 | — |
| 10 | SDSS J073635.22+411828.2; 924478859922238720 | 41, 42, 43, 8810 | J073635：複数の地上曲線に弱い青側・中央の立ち上がりが共通。XP青端と赤側の振動を区別。 | flambda |
| 11 | Gaia DR2 6202013623890855936 | 1369 | XP に幅広い中央の窪みと小さな赤側の揺れ。 | — |
| 12 | Gaia DR2 6012936553497274112 | 116 | DZ:：XP青側が弱く上下に振動。赤側にも目立つ周期的な凹凸。 | — |
| 13 | Gaia DR2 761361190340648448 | 8249 | SDSS 約560 nmより赤側で急に高くなり大部分が上限外。単位・元観測・全振幅表示を要確認。 | unresolved |
| 14 | Gaia DR2 3961591831405665280 | 753, 754 | DESIの中央の谷に対しXPは大きく振動。色の観測間差を小図だけで変動と解釈しない。 | — |
| 15 | Gaia DR3 6034526190179480832 | 3764 | XP 青側に細かな揺れと中央の谷。赤側も小振幅の振動。 | — |
| 16 | Gaia DR3 6377656895573979392 | 4244 | XP 青側の強い周期的な振動、中央〜赤側の谷と小さい揺れ。 | — |

## Limits and next display improvements

This review covers all 176 displayed panels, with raw-array inspection for the explicitly listed follow-ups. It does **not** certify every native pixel, check every direct FITS exposure, inspect all neighbour images, or reconstruct XP coefficient covariance. There are no claims of human inspection of the other 161 strong-outlier panels in this file. The 176-panel pass is not the same as auditing every one of the 9,902 spectrum records.

Useful next displays are: a verified common Fλ convention before overlaying sources; a full-range inset for clipped spectra; visible normalization wavelength bounds; uncertainty and masked-region overlays; an explicit mapping from each coloured line to archive URL, raw SHA and plate–MJD–fibre or exposure identifier; both historical and corrected colour summaries where the convention changes. Direct SDSS and MWDD SDSS copies should be labelled as a shared observation when sample identity establishes that relation. Record-level native data and plots with independently controlled axes are needed for the most unstable XP and SDSS cases. The fixed-range contact sheet is useful for locating such cases, but cannot resolve them alone.

## Reviewed image snapshot hashes

These hashes identify the exact images actually inspected. If the contact sheets are regenerated after the unit audit, this log refers to the snapshot below and a new visual pass is needed before claiming the regenerated version was inspected.

| Image | SHA256 |
|---|---|
| page_01.png | `2aaf58ba6574ebc282e56489d627602f7d1da86faf61ad58b04f6ab6712b73f5` |
| page_02.png | `069f29d11ab434788c9f2e8cc6bdbc8a6be859b9555156a35f79d4917cb251a4` |
| page_03.png | `cfb960e3c637e2fd79be1cdd939dfdf1eac85d752b11229ed3c3aa069fabbc1b` |
| page_04.png | `3a05c06f89893a8e387892c35c61553a94b00f7feb50c82555263910e22341d5` |
| page_05.png | `791e22b85da2bf8b59a52dfc5bc26f637f3cb7700fbc13534b7353004828f079` |
| page_06.png | `2065f0ac49968ec2c0f4ce57d67f110edf456f091a7906a19973890fdb95abc6` |
| page_07.png | `5abe5d83eafea69c1559ea51d47e85c89f8ff627d91bd15116a891cf42024560` |
| page_08.png | `9bf49b3fe71ce27cbcfb69c69a7743eca11e2a4ce026cd82039478dd12217bde` |
| page_09.png | `6f4112d945336390f7ef7cc9727c8359b1fe8826b604e9191cdc1948ae2367db` |
| page_10.png | `240c13f60be46ccc1cd011b1ea18ecb76a3a7ba03d4f5baf104420e3d7e57271` |
| page_11.png | `dc49ad7d2478c9ffea75226609b738c8500b662d9ae0e9867608900f0c9f8971` |
