# Research integrity and limitations / 研究の誠実性と限界

Analysis and initial evidence audit: **2026-10-18**.
[English](#english) · [日本語](#日本語)

## English

### Status and contribution

This is a reproducible reanalysis of public observations of **already known
white dwarfs**. It identifies candidates for additional human-vision colour
measurements. It is not a peer-reviewed discovery paper. Independent external
expert review and endorsement by the original observers, catalogue authors,
survey teams or software developers have not been established.

The principal proposed contribution is the explicit calculation and validation
of CIE chromaticities and display sRGB values for known objects, with provenance,
calibration sensitivity and a bounded literature comparison. The analysis
retains WD J0913+4434 and WD J0429−0354 as pale yellow-green candidates, alongside
additional pink and unusual-yellow measurements. The objects themselves,
their classifications and existing model parameters were reported previously.
The result does not establish new elemental abundances, temperatures,
planetary material, or a new atmospheric mechanism.

The source IDs, rather than shortened names alone, are the stable identifiers
used in the principal follow-up:

| Candidate | Gaia DR3 source_id | Scope of the proposed colour result |
|---|---|---|
| WD J0913+4434 | `818833831355548928` | Pale yellow-green mean chromaticity; nearby-source and colour-boundary uncertainty remain |
| WD J0429−0354 | `3204436719718449280` | A weaker, nearly white yellow-green mean; catalogue checks reduce but do not eliminate blending concerns |
| WD J1329+0033 | `3711047662972690688` | Additional pink chromaticity measurement |
| WD J1323−0129 | `3638333660492606976` | Additional yellow chromaticity outside the thermal locus; positive Duv does not make it green |

The numerical evidence is in the headline table, candidate validation outputs,
Gaia reconstruction audit and novelty records. Temperatures and classifications
in the reports remain attributed to their original catalogues.

### What the colour quantities mean

The calculations integrate measured or reconstructed **Fλ** with the CIE 1931
2° colour-matching functions. The display swatches apply an sRGB conversion
and normalize the largest linear display channel before encoding. They are
computed illustrations of spectral shape, not direct colour photographs,
absolute surface brightness, or a guarantee of naked-eye appearance. Observer
adaptation, brightness and display conditions are not observations made in
this project. [CIE dataset](https://doi.org/10.25039/CIE.DS.xvudnb9b)

Here **Duv** is a signed distance from the blackbody/Planckian colour locus in
CIE 1960 u,v. A positive value locates the point on its green side; it does not
by itself identify the perceived hue as green. A green-side yellow object is
possible and occurs in this candidate set. The screening distance of 0.01 is
an operational comparison with [Hollands et al. (2026)](https://doi.org/10.1093/rasti/rzag069),
not a universal visibility threshold or a calibrated discovery significance.

### Uncertainty, calibration and independence

**Gaia coefficients and correlations.** For J0913 and J0429, the original ESA
DR3 XP_CONTINUOUS coefficients, coefficient errors and packed correlations were
retrieved. GaiaXPy 2.1.5 reconstructed both all-basis spectra and spectra using
Gaia's recommended truncation. The MWDD XP exports match the all-basis official
reconstruction, in native Fλ units, to the precision of the exported text.

The covariance used for inference is propagated from coefficient space through
the calibration basis and both BP/RP merge weights. If `A` maps coefficients to
flux samples and `C` is the coefficient covariance, the two bands contribute
`A_BP.T @ C_BP @ A_BP + A_RP.T @ C_RP @ A_RP`. The same linear operation carries
the covariance into the XYZ integral. The archive does not provide the missing
cross-band calibration covariance; none was invented. Correlated XYZ draws,
not independent wavelength pixels, produce the reported Gaia intervals.

The installed GaiaXPy version's returned packed *sampled* correlations showed
a validation discrepancy in the truncated cases, including negative
eigenvalues inconsistent with a covariance model. They are preserved for
inspection but are not used for inference. The direct propagation reproduces
GaiaXPy's flux and flux errors to floating precision. This is an observed
discrepancy for these inputs, not a claim that its upstream cause or a general
software defect has been established. Full equations, retained arrays and
checks appear in the Gaia audit README.

| Gaia reconstruction | Duv ± formal 1σ | Formal 95% Duv interval | Draws in which green is the largest linear channel |
|---|---:|---:|---:|
| J0913, all 55 BP + 55 RP bases | +0.01923 ± 0.00351 | +0.01236 to +0.02612 | 85.0% |
| J0913, recommended 10 BP + 2 RP | +0.01635 ± 0.00327 | +0.00995 to +0.02274 | 77.8% |
| J0429, all 55 BP + 55 RP bases | +0.01299 ± 0.00220 | +0.00867 to +0.01730 | 82.3% |
| J0429, recommended 4 BP + 2 RP | +0.01493 ± 0.00180 | +0.01141 to +0.01846 | 96.5% |

These 200,000-draw results support displacement to the green side more strongly
than a strict green-over-red hue claim. They are conditional on the supplied
formal noise model and exclude calibration systematics, blend contamination
and truncation bias. Retaining fewer bases can reduce variance while removing
real signal; a smaller formal error is not automatically a more accurate
physical spectrum.

**DESI and photometry.** The headline DESI intervals include the supplied pixel
uncertainties and photometric uncertainty under the stated model, with an
independent-pixel approximation and a 0.02 mag photometric error floor. They
do not include an unknown full instrument covariance or all calibration
systematics. Shared PS1 or SDSS photometric anchors introduce common errors
between recalibrated spectra. Gaia and DESI probabilities are therefore not
multiplied as if those calibrated results were wholly independent.

**Sample selection.** The 9,902 records were selected to favour unusual Q/Z
spectral types, with duplicates and repeat observations possible. They are
not a volume-complete or random population sample. The approximately 6,004
identifiers after the screening cross-match are not a fully established unique
star count: proper motion and matching choices can affect identity. Per-source
formal intervals after this search are not multiple-testing-corrected
discovery p-values, and the sample cannot estimate the fraction of all white
dwarfs with a particular hue.

### Alternatives and rejected interpretations

The recorded checks include original-flux units, wavelength coverage,
comparison objects, calibration changes, neighbour catalogues and literature
evidence. They do not remove every alternative explanation.

- **J0913 has a nearby red source and Gaia blend flags.** Catalogue deblending
  and small published contamination estimates are useful evidence, but do not
  establish exactly zero contamination.
- **J0429 has fewer identified close neighbours.** A catalogue cone search
  cannot exclude objects below its detection limits or all extraction effects.
- **LP 616−53 / J1258+0106 was downgraded.** Its apparently green spectrum is
  accompanied by a close companion, blend flags and substantial photometric
  contamination evidence; it is not presented as a secure isolated-star hue.
- **J1552+2023 illustrated a calibration failure.** Forcing unreliable
  catalogue photometry could generate an extreme artificial colour. Its
  unforced spectra and other photometry did not support that interpretation.
- **Broad absorption is not a new abundance determination.** Removing an
  absorption-shaped depression by an interpolated continuum is a diagnostic
  experiment, not a physical atmosphere with one element removed. Swan et al.
  (2026) also report a broad Na-like DESI feature in another object that was
  not reproduced in follow-up; a feature's shape alone is insufficient to
  identify its origin. [Swan et al.](https://arxiv.org/html/2609.04314v1)

The Swan contamination values are model estimates based on specified PSFs,
epochs, neighbours and apertures, not rigorous upper limits. Neighbour-to-target
flux ratios must not be described as fractions of the total flux.

### Bounded novelty and scientific priority

The audit compared the candidate identities with the 236 named objects
extracted from the Hollands et al. (2026) comparison tables and the related
231-object Hollands et al. (2017) DZ catalogue. It inspected relevant source
identifications, papers, tables and public model products, including work by
Kilic, Vincent and Swan. The audit did not find the candidates' CIE/sRGB
measurements in the inspected material. Existing astronomical colour indices
or atmosphere parameters are not equivalent to a reported human-vision
chromaticity measurement.

This supports the bounded statement **“a new reproducible colour analysis of
known stars, with no earlier equivalent measurement found in the inspected
sources.”** It does not prove absence from every paper, unpublished analysis,
thesis, language or database. A Git commit, public repository or release
timestamp documents this project's record; it does not alone establish
worldwide scientific priority. A relevant earlier measurement should be
acknowledged and the novelty wording updated.

### AI involvement and responsibility

**ChatGPT performed the analysis at Shota Moriwaki's direction.** Its work
included finding sources, retrieving public data, writing and running analysis
code, calculating colours and uncertainties, performing the recorded
computational checks, and drafting the English and Japanese documentation.
Shota Moriwaki directed the project and authorized its public release.

AI assistance is not an independent scientific reviewer or a substitute for
human responsibility for publication. The reported internal cross-checks,
including alternative calculations and separately tasked AI analyses, must
not be described as external expert review. No claim is made that Shota
Moriwaki independently rederived every calculation, or that the original
authors, institutions, OpenAI, or survey collaborations approved these
conclusions. No AI system is presented as an accountable scientific author.

### Corrections and further evidence

The code, source hashes, retained failures and numerical outputs are provided
so others can test the result. A useful correction identifies the source ID,
release/input hash, analysis version and the discrepant calculation or prior
reference. Corrections should distinguish a changed archive input from a
code, calibration, identity or interpretation error. Preserve the earlier
version and record changes that alter headline values or candidate status.

Independent visible spectroscopy with reliable relative flux calibration and
separation from neighbouring sources would strengthen the hue assessment.
No such new observing campaign is claimed here. Further publication should
include appropriate human scientific review and the original survey credits;
this document does not assert that either step has already occurred.

## 日本語

### 研究の位置づけと、今回の寄与

本研究は、**既に知られている白色矮星の公開観測データを再解析したもの**です。
人間の視覚に対応する追加の色度測定候補を示します。査読済みの発見論文ではなく、
外部の専門家による独立した査読や、原観測者、カタログ著者、サーベイ、
ソフトウェア開発者による承認は確認されていません。

主な寄与は、既知天体のCIE色度・表示用sRGBを実際に計算し、出典、校正感度、
不確かさ、範囲を限定した先行研究照合とともに公開することです。
WD J0913+4434、WD J0429−0354を淡い黄緑色の候補として残し、
WD J1329+0033のピンク、WD J1323−0129の通常の熱放射から外れた黄色も
追加の色の測定対象としました。正確なGaia識別子は英語節の表に記載しています。

天体そのもの、既存の分類、温度、元素量、大気モデルは既報です。これらを今回
新たに発見・測定したとは主張せず、惑星物質や新しい大気機構の発見にも結びつけて
いません。報告に用いる温度や分類は、それぞれの原カタログに帰属します。

### 色の数値が意味するもの

測定または再構成したFλにCIE 1931の2°等色関数を掛けて積分し、表示用の色を
計算します。色見本は最大の線形表示チャンネルをそろえたsRGBで、天体写真や
実際の表面輝度ではありません。肉眼で必ず同じ色に見えることも保証していません。
明るさ、目の順応、表示装置の条件を実際に観測した研究ではないためです。
[CIE原データ](https://doi.org/10.25039/CIE.DS.xvudnb9b)

DuvはCIE 1960 u,v上で黒体の色の軌跡から測った符号付き距離です。
正なら軌跡の緑側ですが、それだけで色名を「緑」と断定できません。
J1323−0129はその具体例で、Duvが正でも表示色は黄色です。探索に用いた0.01は
[Hollands et al. (2026)](https://doi.org/10.1093/rasti/rzag069)との比較の目安であり、
普遍的な識別限界や発見の有意水準ではありません。

### 不確かさ、校正、独立性

J0913とJ0429では、ESAのGaia DR3 XP_CONTINUOUS元係数、係数誤差、相関を
取得し、GaiaXPy 2.1.5で全基底と推奨基底数の両方を再構成しました。
MWDDのXP公開値は、公式係数を全基底で再構成したFλと丸め誤差程度で一致します。
推論に用いる共分散は係数から校正基底・BP/RPの合成重みを通して直接伝播し、
さらにXYZ積分へ伝播しました。波長サンプルを独立とみなす方法ではありません。

使用したGaiaXPyの返す「サンプル間」の相関には、切り詰めたケースで共分散モデルと
整合しない負の固有値などの検証上の不一致がありました。その配列は検査用に残し、
推論には使っていません。直接伝播の流束と誤差はGaiaXPy出力と浮動小数点精度で
一致します。これは該当する入力で観測した不一致であり、上流の原因や一般的な
ソフトウェア不具合が確定したという主張ではありません。

各200,000回の相関した乱数試行で、Duvは全基底・推奨基底数の平均のいずれでも
緑側に残りました。一方、Gが最大となった試行割合はJ0913で85.0%／77.8%、
J0429で82.3%／96.5%です。したがって、Gaiaだけで「緑が赤を確実に上回る」と
強く断定しません。数値と区間は英語節の表およびGaia監査資料に保存しています。

これらは提供された形式的ノイズモデルに条件付けた結果です。未提供のBP/RP間の
校正共分散、系統的な流束校正誤差、混入、基底切り詰めのバイアスは含みません。
基底を減らすと分散は小さくても、本来の信号まで除く可能性があります。

DESIの主要な区間は、公開された画素誤差と測光誤差を使用し、画素独立の近似と
0.02等の測光誤差下限を含みます。未知の完全な装置共分散や全系統誤差を網羅した
誤差予算ではありません。同じPS1またはSDSS測光に合わせたGaiaとDESIには
共通の誤差が入るため、確率を完全に独立として掛け合わせません。

9,902記録はQ/Z型を意図的に多く含み、重複や繰り返し観測もある標本です。
体積完全・無作為標本ではなく、全白色矮星の何%が特定の色かは推定できません。
照合後の約6,004識別子も、固有運動や位置照合により重複の余地が残ります。
多数を探索した後の天体別の形式誤差を、多重比較まで補正した発見確率とは扱いません。

### 代替解釈と、残さなかった主張

原流束の単位、波長範囲、比較天体、校正変更、近傍カタログ、先行研究は点検しました。
それでも、次の制約は残ります。

- **J0913には赤い近傍天体とGaiaの混合フラグがあります。** カタログ上の分離や
  小さな混入推定は有用ですが、混入が厳密にゼロとは言えません。
- **J0429では確認された近傍天体の懸念が少ないものの、** 検出限界より暗い天体や
  あらゆる抽出誤差をカタログ検索だけで排除できません。
- **LP 616−53／J1258+0106は格下げしました。** 近接した伴星、混合フラグ、
  測光への混入情報があり、安全な単独星の色として提示しません。
- **J1552+2023は校正の誤検出例です。** 信頼できない測光値を強制すると極端な色を
  作れましたが、元のスペクトルと他の測光はその解釈を支持しませんでした。
- **幅広い吸収だけで元素量を決めません。** 吸収状の落ち込みを補間で埋める操作は
  診断実験であり、その元素を取り除いた物理的な大気モデルではありません。
  [Swan et al. (2026)](https://arxiv.org/html/2609.04314v1)には、別の天体でNa様の
  DESI吸収が追観測では再現されなかった例もあります。

Swanの混入値は、指定したPSF、時刻、近傍天体、開口に基づくモデル推定で、
厳密な上限ではありません。近傍光／対象光の比を、全光量中の混入割合へ
読み替えることもしません。

### 新規性と優先権の範囲

監査ではHollands et al. (2026)の比較表から抽出した236名称、関連する
Hollands et al. (2017)の231天体のDZカタログと照合しました。SIMBADの同定、
Kilic、Vincent、Swanらの関連論文・表・公開モデル資料も確認しました。
確認した資料では、主要候補について同等のCIE/sRGB測定を見つけられませんでした。
既存の天文学的な色指数や大気パラメータの報告とは区別しています。

この記録が支持するのは、**「既知天体についての再現可能な新しい色解析であり、
確認した資料では同等の先行測定を見つけていない」**という範囲です。
全論文、未公表解析、学位論文、言語、データベースを網羅した不存在の証明では
ありません。Gitやリリースの時刻も、本プロジェクトの記録を示すもので、世界的な
科学的優先権を単独で証明するものではありません。先行測定が判明した場合は
引用を加え、新規性の記述を修正します。

### AIの関与と責任

**ChatGPTがShota Moriwakiの指示のもとで解析を実行しました。**
担当した作業は、資料の検索、公開データ取得、コードの作成・実行、色と不確かさの
計算、記録された計算上の確認、英語・日本語の文書作成です。
Shota Moriwakiが研究の方向を指示し、公開を承認しました。

AIによる補助は独立した科学査読者でも、公開に対する人間の責任の代わりでも
ありません。別経路の計算や別担当のAIによる内部確認を、外部専門家の査読と
表現しません。Shota Moriwakiが全計算を独立に再導出したという主張もしていません。
原著者、研究機関、OpenAI、サーベイが結論を承認したとは扱わず、AIを責任を負える
科学論文の著者として表示しません。

### 訂正と今後の証拠

出典ハッシュ、コード、残した失敗例、数値結果は、第三者が検証できるように
提供します。問題の報告には天体ID、入力／リリースのハッシュ、解析版、相違のある
計算または先行文献を示すと追跡できます。アーカイブの更新と、コード・校正・同定・
解釈の誤りを区別し、主要値や候補の位置づけが変わる場合は旧版と変更記録を残します。

近傍天体から分離した独立の可視分光と、信頼できる相対流束校正は色の判断を
強める証拠になります。本研究が新たな観測を実施したとは主張しません。
今後の学術発表では適切な人間による科学的検討と原サーベイの謝辞を反映すべきであり、
それらが既に完了したという意味ではありません。

原データの出典、再取得方法、利用条件は[データの所在と利用条件](data-availability.md)を参照してください。
