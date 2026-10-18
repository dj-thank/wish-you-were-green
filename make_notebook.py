"""Build and optionally execute the English and Japanese research notebooks.

Both language editions use the same nine scientific code cells and read only
committed data. This does not run survey acquisition or the full Monte Carlo.

    python make_notebook.py --execute --kernel python3

A registered local scientific kernel may be supplied with --kernel. Saved
notebooks always use the portable python3 kernelspec. Source cell IDs are
stable, and execution timestamps are omitted from the generated artifacts.
"""
from pathlib import Path
import argparse
import json
import os
import re
import tempfile
import nbformat as nbf

ROOT = Path(__file__).resolve().parent
FILENAMES = {"en": "white_dwarf_colour_research.ipynb",
             "ja": "white_dwarf_colour_research.ja.ipynb"}
KERNELSPEC = {"display_name": "Python 3 (ipykernel)", "language": "python", "name": "python3"}

# Narrative variants are paired by the source notebook's original cell index.
MARKDOWN = {
    0: {
        "en": r"""# A public-spectrum search for additional white-dwarf colour candidates

**Research snapshot: 18 October 2026. Executed computational research notebook.**

[Japanese notebook](white_dwarf_colour_research.ja.ipynb) · [English report](docs/report.en.md) · [Japanese report](docs/report.ja.md) · [Reproducibility](docs/reproducibility.en.md) · [Research integrity](docs/research-integrity.md)

Reanalysis of public spectra identifies the pale yellow-green candidates **WD J0913+4434 and WD J0429−0354**, the pink candidate **WD J1329+0033**, and the unusual yellow candidate **WD J1323−0129** outside the 236-name comparison list in Hollands et al. (2026).

The potentially new result is a **human-vision chromaticity measurement for known stars**. This work does not claim the discovery of the stars, their temperatures, their elements, or a new absorption mechanism. No previous report of these perceived-colour quantities was located in the literature checked; worldwide priority has not been established.

**Status and authorship:** this analysis, code and narrative were generated with ChatGPT in response to the user's research request. They are an AI-generated, unreviewed research artifact, not a peer-reviewed paper or an independent professional confirmation of discovery. The original observations, classifications and models belong to the cited survey teams and authors. The candidate wording and uncertainty qualifications must travel with any reuse.

This notebook summarizes the frozen full-screen tables and recalculates the headline colours from the included original spectra. It does not redownload observations or rerun all 9,902 spectrum records. The English and Japanese notebooks share exactly the same nine code cells; tables, figures and execution messages use English in both. Large metadata tables are read through `project_io`, which supports the committed `.json.gz` and `.csv.gz` files.""",
        "ja": r"""# 公開スペクトルによる、未報告の白色矮星の色の探索

**解析日：2026年10月18日。実行済み研究ノート。**

[English notebook](white_dwarf_colour_research.ipynb) · [日本語レポート](docs/report.ja.md) · [English report](docs/report.en.md) · [再現手順](docs/reproducibility.en.md) · [研究上の位置づけ](docs/research-integrity.md)

公開されたスペクトルを実際に再解析し、Hollands et al. (2026) の236名称の対象一覧にない、黄緑色候補 **WD J0913+4434 / WD J0429−0354**、ピンク色候補 **WD J1329+0033**、異常な黄色の候補 **WD J1323−0129** を抽出した。

新規性の候補は、既知の星について計算した **人間の視覚に対する色度** である。天体そのもの、温度、元素、吸収機構を新発見したという主張ではない。確認した先行研究でこれらの人間視覚色の報告は見つからなかったが、世界的優先権は証明していない。

このノートは保存済み全走査表を集計し、主要候補の色を同梱した元スペクトルから再計算する。全9,902記録の再走査は `download_frozen_spectra.py` と `run_full_screen.py` で再現できる。

**作成主体と位置づけ：** この解析・コード・文章は、ユーザーの研究依頼に応じてChatGPTが生成した、AIによる未査読の研究成果物である。査読論文や専門研究者による独立した発見の確認ではない。元観測・分類・モデルの功績は引用した観測チームと著者に帰属する。候補という位置づけと不確かさを、再利用時にも保持する。

英語版と日本語版は同じ9個のコードセルを共有する。表・図・実行メッセージは両版とも英語である。大きなメタデータは `project_io` を通じて `.json.gz`・`.csv.gz` を読み込む。"""
    },
    2: {
        "en": r"""## 1. Search scope and selection

The search starts from the 163,279-row MWDD catalogue, emphasizing classifications containing DQ or DZ and adding known-colour comparison objects. It acquired 8,505 spectra for 5,548 catalogue identifiers. A separate SDSS route supplied 1,343 Q/Z-type observations and 18 each of DA, DC and DB controls: 1,397 spectra in total. **The combined 9,902 is a count of data records, not independent stars.** A preliminary five-arcsecond coordinate match gives 6,004 identifier groups; this is not a fully deduplicated population count, especially for high-proper-motion objects.

The screen requires the adopted SDSS, DESI or Gaia XP Fλ convention, more than 99.5% coverage of the CIE sensitivity functions, and a largest wavelength gap below 150 Å. When reliable gri photometry is available, a linear tilt in magnitudes is fitted. The screen uses a 0.10-mag photometric-error limit and rejects fits with maximum residual at least 0.15 mag or absolute tilt at least 0.25 mag per 1,000 Å. Unanchored spectra remain labelled exploratory records; their colours alone do not promote them to strong candidates.

Older observations and continuum-normalized SPY data are excluded from candidate classification when their Fλ shape is not established. An outlier in the full result table is not automatically a discovery.

The control table below is read from the **archived screen result**. To also verify the 54 included raw SDSS FITS spectra and recompute their colours, run `python scripts/verify_reproduction.py --with-controls`.""",
        "ja": r"""## 1. 探索範囲と選別

MWDDの163,279行のカタログからDQ/DZを含む分類を中心に選び、既知の色の検証用対象を加えた5,548天体について8,505スペクトルを取得した。別経路でSDSSのQ/Z型1,343観測とDA/DC/DB対照各18観測、合計1,397本を取得した。**合計9,902はデータ記録数で、独立した天体数ではない。** 座標5秒角の暫定照合後は6,004名称単位となるが、高固有運動の重複を完全に排除した人口統計値としては扱わない。

SDSS・DESI・Gaia XPのFλ形式、CIE感度曲線の99.5%以上の波長被覆、150 Å未満の最大空白を要求する。校正可能な場合はgriへの一次の等級傾斜を使い、測光誤差0.10等以上、最大残差0.15等以上、傾斜の絶対値0.25等/1,000 Å以上を採用しない。校正できないスペクトルも探索用としてラベルを残すが、その色だけで有力候補にしない。

旧観測やSPYの連続光正規化済みデータは、Fλの形が保証できないため候補判定から外した。全ての外れ値を新発見と呼ぶことはしない。

以下の対照表は**保存済みの走査結果**である。同梱された54本のSDSS元FITSを検証し色を再計算する場合は、`python scripts/verify_reproduction.py --with-controls` を実行する。"""
    },
    4: {
        "en": r"""## 2. Colour definition and implementation

The calculation uses the photopic CIE 1931 two-degree standard observer and integrates energy flux density per wavelength:

$$ (X,Y,Z)=\int_{360\,{\rm nm}}^{830\,{\rm nm}}F_\lambda(\lambda)(\bar x,\bar y,\bar z)\,d\lambda. $$

$$x=X/(X+Y+Z),\quad y=Y/(X+Y+Z),\quad u=4x/(3-2x+12y),\quad v=6y/(3-2x+12y).$$

Signed Duv is the shortest distance to the blackbody locus in CIE 1960 u,v, with a sign indicating the side of the locus. **Positive Duv alone does not define a green star.** The results also record whether the linear-sRGB green channel exceeds both red and blue. The blackbody locus spans 1,000 K to 10⁸ K and includes the Rayleigh–Jeans limit. Display colours use sRGB with a D65 white point, normalized to a maximum linear channel of one before applying the sRGB transfer function.

These are chromaticities inferred from received spectra, not photographs from Earth. The rendering does not reproduce stellar surface brightness, individual visual differences, dark-adapted vision or chromatic adaptation. Negative noisy spectral samples are not clipped to zero.""",
        "ja": r"""## 2. 色の定義と実装

明所視のCIE 1931・2度標準観測者を用い、波長ごとのエネルギー流束を積分する。

$$ (X,Y,Z)=\int_{360\,{\rm nm}}^{830\,{\rm nm}}F_\lambda(\lambda)(\bar x,\bar y,\bar z)\,d\lambda. $$

$$x=X/(X+Y+Z),\quad y=Y/(X+Y+Z),\quad u=4x/(3-2x+12y),\quad v=6y/(3-2x+12y).$$

符号付きDuvはCIE 1960の黒体軌跡までの最短距離に上下の符号を付けた指標である。**正のDuvだけで緑色とは判定しない。** 緑寄りの目安として線形sRGBでGがR・Bを上回るかも保存する。黒体軌跡は1,000 Kから10⁸ KとRayleigh–Jeans極限を含む。表示色はD65白色点のsRGBに変換し、最大チャンネルを1に揃えてから正しい伝達関数を適用する。

地球から見た写真の色ではなく、受信スペクトルから推定した色度である。星表面の実際の輝度、個人差、暗所視、色順応を再現してはいない。負のノイズ画素をゼロに切り上げる処理はしない。"""
    },
    6: {
        "en": r"""The known green comparison J0851+1543 is reproduced as `#F1FFF7`, versus the published `#F1FFF8`. The pink comparison J1011+2845 matches `#FF8775` under the present PS1 calibration. Discrepancies are retained where the paper's model and the available observed spectrum differ. In particular, the J1330+6435 observation has low signal-to-noise; agreement with the exact model colour is not claimed.""",
        "ja": r"""緑色の既知例J0851+1543は公表色 `#F1FFF8` に対し `#F1FFF7`、ピンク色J1011+2845は今回のPS1校正で `#FF8775` と一致した。一方、元論文のモデルと観測スペクトルが違う場合の差も残した。特にJ1330+6435は低い信号対雑音比の観測からの再現であり、モデルの正確な色と一致したとは主張しない。"""
    },
    7: {
        "en": r"""## 3. Measured headline candidates

All representative values below use the same choice: **DESI spectra recalibrated to Pan-STARRS gri photometry**. Stellar classifications and temperatures come from prior catalogues; this analysis does not fit a new atmospheric model. The displayed 95% intervals are conditional on the noise and photometric assumptions discussed in Section 4.""",
        "ja": r"""## 3. 主要候補の実測結果

以下の代表値は全て **DESIスペクトルをPan-STARRS griで補正**した同一条件である。各天体の分類・温度は既存カタログ由来で、今回新たに大気モデルをフィットした結果ではない。"""
    },
    9: {
        "en": r"""### Recompute from the original spectra

The following cell verifies the included public CSV's SHA-256, checks that its wavelength and flux columns match the parsed arrays, and reruns the same photometric calibration and CIE integration. Gaia's large numerical identifiers are retained as strings.""",
        "ja": r"""### 元スペクトルからの再計算

同梱した公開CSVのSHA256を確認し、同じ校正・CIE積分を再実行する。Gaiaの巨大な数値IDは文字列として保持する。"""
    },
    11: {
        "en": r"""## 4. Measurement error and remaining systematic error

The saved DESI analysis uses 6,000 Monte Carlo trials drawn from the published pixel errors and photometric errors, with a 0.02-mag floor. A first-order band-magnitude Jacobian follows the photometric recalibration, after which perturbed colour is evaluated nonlinearly. The displayed 95% intervals describe this conditional measurement model; they do not include unknown calibration systematics or a false-discovery rate for the entire search. Correlations between the resampled DESI pixels were not supplied, so this stage uses an independent-pixel approximation. This notebook reads the saved intervals rather than rerunning those trials.

For J0913, original SDSS PSF fluxes were also retrieved independently. SDSS anchoring gives `#F7FFC6`, Duv ≈ 0.0179; PS1 anchoring gives `#F1FFC9`, Duv ≈ 0.0190. Both lie in the pale yellow-green region, and the uncorrected spectrum shows the same tendency. However, an additional large tilt of −0.10 mag per 1,000 Å can make red exceed green in the SDSS-anchored case. The colour-name boundary is not entirely independent of calibration.""",
        "ja": r"""## 4. 誤差と系統誤差を区別する

DESIは公開画素誤差と測光誤差（最低0.02等）から6,000回の乱数試行を行い、測光への再校正を一次のヤコビアンで追随させ、その後の色積分は非線形に計算した。表示される95%区間は、この条件下の測定誤差区間であり、未知の校正誤差や全探索の誤検出率を含むものではない。DESIの再サンプリング画素間相関は提供されていないため独立画素近似である。

J0913についてはSDSSの元PSF流束も別に取得した。SDSS校正では `#F7FFC6`, Duv≈0.0179、PS1校正では `#F1FFC9`, Duv≈0.0190となり、ともに淡い黄緑領域にある。補正前も同じ傾向である。ただし、さらに−0.10等/1,000 Åという大きい傾斜を加えると、SDSS校正の場合はRがGを上回り得る。色名の境界は校正から完全に独立ではない。

このノートでは保存済みの誤差区間を読み込む。6,000回の乱数試行そのものは再実行しない。"""
    },
    13: {
        "en": r"""### Limits revealed by Gaia's original coefficients and full covariance

MWDD's Gaia XP export does not contain an uncertainty array; that absence cannot be interpreted as zero uncertainty. The original ESA XP_CONTINUOUS coefficients and correlations were retrieved, and GaiaXPy 2.1.5 was used to reconstruct the spectra. Both the full 55-basis representation and truncation to the catalogue's recommended basis counts were checked. Coefficient covariance was propagated to integrated XYZ, followed by 200,000 Gaussian trials per saved reconstruction.

**The mean pale yellow-green colour survives both reconstructions, but Gaia alone does not establish a strict green-channel-dominant colour at high significance.** DESI's agreement with independent photometry provides the principal additional evidence; Gaia supplies supporting measurements with substantial uncertainty. Spectra calibrated to the same photometry must not be counted as independent calibration evidence.

The following cell recalculates the means from the four included 1 nm reconstruction products and displays the archived formal covariance intervals. It does not rerun GaiaXPy or its Monte Carlo simulation. The independent offline verifier checks the full covariance projections; see [the Gaia audit](mwdd/gaia_validation/README.md) for coefficient-level reconstruction and its limitations.""",
        "ja": r"""### Gaiaの元係数・全相関で確認した限界

MWDDのGaia XPファイルには誤差がないため、それを誤差ゼロとして扱うことはできない。ESAのXP_CONTINUOUS元係数と相関を取得し、GaiaXPy 2.1.5でスペクトルを再構成した。全55基底と、カタログが推奨する基底数への切り詰めの両方を確認し、係数共分散を積分後のXYZまで伝播して各200,000回の乱数試行を行った。

**平均の黄緑色は両方の再構成で残るが、Gaia単独で緑色を高い有意度で確定したとは言えない。** 主要な根拠はDESIと独立測光との整合であり、Gaiaは不確かさを伴う追認である。同じ測光を使った校正同士は独立した観測証拠として二重に数えない。

次のセルは同梱された4つの1 nm再構成データから平均色を再計算し、保存済みの共分散による区間を表示する。GaiaXPyによる再構成や乱数試行をこのノート内では再実行しない。全共分散の投影は独立したオフライン検証で確認でき、元係数からの再現手順と限界は[Gaia監査](mwdd/gaia_validation/README.md)に記載した。"""
    },
    15: {
        "en": r"""## 5. Neighbouring sources and downgraded candidates

J0913 has a red background source about 5.342 arcsec away in Gaia DR3. SDSS deblends the pair and assigns the target CLEAN=1, but its r band carries interpolation and cosmic-ray-related flags. Four of 48 transits in each Gaia BP and RP band are marked blended. Zero contamination is not established.

The Gaia searches for J0429, J1329 and J1323 found no other catalogued source within 10 arcsec. This does not exclude contamination below the catalogue detection limit. J0429's direct PS1 check likewise found no similarly bright close neighbour, and the original PS1 measurements agree with MWDD.

**LP 616−53 / J1258+0106** also appeared pale yellow-green in a relatively high-signal spectrum. It has a bright companion roughly 2.30 arcsec away and another source about 1.29 arcsec away, with substantial Gaia blend flags. It was therefore downgraded from the headline candidate list. The apparently extreme blue case J1552+2023 was rejected after finding erroneous photometry and an unreasonable tilt correction.

J1323−0129 is yellow and is not counted as green merely because Duv is positive. Published estimates of its temperature and gravity differ substantially; this colour calculation does not establish new physical parameters or composition.""",
        "ja": r"""## 5. 近傍天体と、格下げした候補

J0913には約5.342秒角離れた赤い背景天体がある。SDSSは両者を分離しており対象のCLEAN=1だが、rバンドに補間・宇宙線などのフラグがあり、Gaia BP/RPでも各48回中4回が混合フラグを持つ。混入ゼロとは主張しない。

J0429、J1329、J1323のGaia検索では10秒角以内に他の掲載天体がなかった。これはカタログの検出限界以下の混入まで排除するものではない。J0429のPS1にも同程度に明るい近接天体は見つからず、元の測光値はMWDDと一致した。

高い信号対雑音比で黄緑色に見える **LP 616−53 / J1258+0106** も見つかった。しかし、約2.30秒角の明るい伴星と約1.29秒角の別ソースがあり、Gaiaの混合フラグも多い。そのため主要な新候補から格下げした。極端に青く見えたJ1552+2023は、測光値の大きな誤りと不合理な傾斜補正による偽候補として除いた。

J1323−0129は黄色であり、Duvが正だからといって緑色に数えない。既存論文間で推定温度・重力が大きく変化しているため、今回の色の計算から新しい物理パラメータや組成の発見には進まない。"""
    },
    16: {
        "en": r"""### Contamination estimates from an independent DESI catalogue

The official tables of [Swan et al. (2026)](https://arxiv.org/html/2609.04314v1) provide an additional check. For the four headline candidates, the estimated DESI neighbour-to-target flux ratios are very small under a Gaussian PSF model using Gaia neighbours, proper motions and exposure seeing. LP 616−53 is classified WD+MS, with ratios about 0.0307 in DESI, 0.706 in SDSS and 0.765 in PS1. This supports removing it from a single-star colour claim.

These estimates omit extended PSF wings and spectral cross-talk and are not strict contamination upper bounds. The same paper also describes another object's sodium-like absorption that did not persist in follow-up observations. Measuring a mean chromaticity is distinct from securely identifying its absorbing species or physical mechanism.""",
        "ja": r"""### 独立したDESIカタログの混入推定

[Swan et al. 2026](https://arxiv.org/html/2609.04314v1) の公式表を追加取得した。主要4候補のDESI混入比は、Gaia近傍天体・固有運動・シーイングを使ったガウスPSFモデルではごく小さい。一方、LP 616−53はWD+MS分類で、DESIの近傍光／対象光比は約0.0307、SDSSで約0.706、PS1で約0.765だった。後者を単独星の色の主張から外す判断が裏付けられた。

この指標はPSFの翼やスペクトルのクロストークを扱っていないので、混入の厳密な上限ではない。また同論文には、別天体のNa様吸収が再観測では確認されなかった例もある。今回の平均色の測定と、吸収元素・物理機構の確定は分ける。"""
    },
    18: {
        "en": r"""## 6. What may be new, and what remains prior work

Known names, aliases, Gaia IDs and positions were checked against all 236 names in Hollands (2026) and the 231-object DZ parent catalogue of Hollands (2017). Prior classifications, atmosphere models, SIMBAD references, and the relevant Kilic and Vincent paper text and figures were inspected. Existing model fits qualitatively account for the broad metal absorption of J0913 and molecular-carbon features of J1329. Those mechanisms are already known.

The potentially additional measurement is the standardized human-vision colour of known stars outside the comparison sample, computed from public Fλ spectra with checks on calibration, uncertainty and prior-paper overlap. The novelty statement is limited to the literature actually reviewed. It does not prove the absence of an unindexed study, unpublished calculation or overlooked supplement.

DQ and DZ objects are deliberately overrepresented, so no cosmic incidence of green white dwarfs is inferred. Passing 54 negative controls does not establish discovery significance after screening thousands of spectra, and a reproducible AI-generated calculation remains subject to scientific review.""",
        "ja": r"""## 6. どこまでが新しい研究結果か

既知名・別名・Gaia ID・位置を照合し、Hollands2026の全236名称とHollands2017の231個のDZ親カタログから除外した。候補の過去の分類や大気モデル、SIMBAD文献、Kilic・Vincent等の論文本文と図を確認した。既存のモデルフィットは、J0913の幅広い金属吸収やJ1329の炭素分子の吸収と整合している。これらの機構自体は既知である。

今回の新しい測定は、対象外の既知星について、公開Fλスペクトルから標準化した人間視覚色を求め、校正・誤差・原論文との重複を検査したことにある。先行研究に報告が見当たらなかった範囲を明示する。未索引の研究、公開されていない計算、全ての補足資料まで不存在を証明したわけではない。

この探索はDQ/DZを意図的に多く含むため、緑色白色矮星の宇宙全体での割合は算出しない。54対照が正常でも、何千件もの探索後の世界初の発見有意度を保証するものではない。"""
    },
    20: {
        "en": r"""## 7. Reproduction and the next observations

- **Reproduce this notebook:** install `requirements-core.txt`, open it with the repository root as the working directory, and run the nine code cells in order. Figures and full-screen tables are frozen included products; the four headline spectra and Gaia mean products are recalculated here.
- **Run the independent offline check:** `python scripts/verify_reproduction.py --with-controls` additionally checks all included raw SDSS controls and the Gaia covariance products.
- **Rebuild both language editions:** `python make_notebook.py --execute --kernel python3`. The builder preserves identical scientific code cells, executes each notebook in a fresh kernel, and restores the portable `python3` kernelspec. A different registered kernel can be selected with `--kernel`.
- **Reproduce the full survey screen:** `python download_frozen_spectra.py` reacquires missing public files with SHA-256 checks, followed by `python run_full_screen.py`. This separate step requires network access and substantially more data than the compact notebook.
- **Reproduce candidate uncertainty simulations:** `python validate_candidates.py`. For reconstruction from Gaia coefficients, use the separate environment described in `mwdd/gaia_validation/README.md`.
- **Observations that would strengthen the claim:** independent spectroscopy resolving the candidate and its neighbours, with relative flux calibration across the visible range accurate to a few percent. This would test residual contamination, smooth calibration errors and repeat-observation agreement.
- **Appropriate publication claim:** additional standardized chromaticity measurements and colour candidates. Neither a new astronomical object nor worldwide priority is established. Predicting colour from an atmospheric model would be further physical validation, not an already completed result of this notebook.

## Main data and literature

1. [Hollands et al. 2026, Any colour you like](https://arxiv.org/html/2610.18966v1), DOI: 10.1093/rasti/rzag069.
2. [Montreal White Dwarf Database](https://www.montrealwhitedwarfdatabase.org/), Dufour et al. 2017.
3. [Kilic et al. 2026, Cool White Dwarfs in DESI DR1](https://arxiv.org/html/2606.25377v2), DOI: 10.3847/1538-4357/ae825f; [public model-fit figures](https://doi.org/10.5281/zenodo.20775938).
4. [Vincent et al. 2024, Gaia XP classification](https://arxiv.org/abs/2308.05572), DOI: 10.1051/0004-6361/202347694.
5. [Kepler et al. 2019 source catalogue](https://cdsarc.cds.unistra.fr/ftp/J/MNRAS/486/2169/), DOI: 10.1093/mnras/stz960.
6. [Official CIE 1931 colour-matching functions](https://cie.co.at/datatable/cie-1931-colour-matching-functions-2-degree-observer), DOI: 10.25039/CIE.DS.xvudnb9b, CC BY-SA 4.0.
7. [Gaia programmatic access](https://www.cosmos.esa.int/web/gaia-users/archive/programmatic-access), [GaiaXPy documentation](https://gaia-dpci.github.io/GaiaXPy-website/), [SDSS DR17](https://www.sdss4.org/dr17/spectro/spectro_basics/), and [PS1 API](https://catalogs.mast.stsci.edu/docs/panstarrs.html).
8. [Swan et al. 2026, DESI DR1 white-dwarf catalogue](https://arxiv.org/html/2609.04314v1), used for the independent contamination check.

Source URLs and SHA-256 checksums for raw spectra, original coefficients and consulted tables are retained in the committed manifests. The cited teams retain credit for the original observations, catalogues and models. This is an AI-generated public-data reanalysis submitted for scrutiny, not a peer-reviewed paper.""",
        "ja": r"""## 7. 追試と次の観測が解決すること

- **今回の再現**：このノートを上から実行する。全走査表と主要候補の元データは同梱されている。
- **両言語版の再生成**：`python make_notebook.py --execute --kernel python3`。別の登録済みカーネルを使う場合は `--kernel` で指定する。科学計算は同じ9セルを共有し、保存時には標準の `python3` カーネル指定に戻す。
- **独立したオフライン検証**：`python scripts/verify_reproduction.py --with-controls`。同梱した元SDSS対照スペクトルとGaia共分散も検証する。
- **全標本の再現**：`python download_frozen_spectra.py` でSHA256を照合しながら元データを取得し、`python run_full_screen.py` を実行する。
- **候補の乱数試行の再現**：`python validate_candidates.py`。Gaiaの元係数からの再構成は別環境で `mwdd/gaia_validation/README.md` に従う。
- **確定度を上げる観測**：候補と近傍星を分離し、可視域全体の相対流束を数%程度で校正する独立の分光観測。これで残る混入・滑らかな校正誤差・再観測の一致を検証できる。
- **論文化時の主張**：標準観測者に対する新しい色度測定と追加候補として提示し、現段階で新天体や世界初を断定しない。大気モデルからの色の予測は追加の物理検証であり、今回実施済みの結果と混同しない。

## 主なデータ・文献

1. [Hollands et al. 2026, Any colour you like](https://arxiv.org/html/2610.18966v1), DOI: 10.1093/rasti/rzag069.
2. [Montreal White Dwarf Database](https://www.montrealwhitedwarfdatabase.org/), Dufour et al. 2017.
3. [Kilic et al. 2026, Cool White Dwarfs in DESI DR1](https://arxiv.org/html/2606.25377v2), DOI: 10.3847/1538-4357/ae825f. [公開モデル図](https://doi.org/10.5281/zenodo.20775938).
4. [Vincent et al. 2024, Gaia XP classification](https://arxiv.org/abs/2308.05572), DOI: 10.1051/0004-6361/202347694.
5. [Kepler et al. 2019 の元カタログ](https://cdsarc.cds.unistra.fr/ftp/J/MNRAS/486/2169/), DOI: 10.1093/mnras/stz960.
6. [CIE 1931公式等色関数](https://cie.co.at/datatable/cie-1931-colour-matching-functions-2-degree-observer), DOI: 10.25039/CIE.DS.xvudnb9b, CC BY-SA 4.0.
7. [Gaia公式データ取得](https://www.cosmos.esa.int/web/gaia-users/archive/programmatic-access)、[GaiaXPy公式ドキュメント](https://gaia-dpci.github.io/GaiaXPy-website/)、[SDSS DR17](https://www.sdss4.org/dr17/spectro/spectro_basics/)、[PS1 API](https://catalogs.mast.stsci.edu/docs/panstarrs.html)。

生スペクトル、元係数、使用した表のURLとSHA256は同梱のマニフェストに記録した。原観測・カタログ・モデルの著者に帰属するデータを利用した再解析であり、査読を受けた論文ではない。"""
    },
}

# The scientific code below is identical in both language editions.
CODE = {
    1: r"""from pathlib import Path
import hashlib, sys
import numpy as np
import pandas as pd
from IPython.display import display, Image
from project_io import read_dataframe, load_json
ROOT=Path.cwd().resolve()
if not (ROOT/'colour_pipeline.py').exists():
    raise RuntimeError('Open this notebook with the research repository root as its working directory.')
import colour_pipeline as c
from validate_candidates import anchors, get_arrays
assert Path(c.__file__).resolve().parent==ROOT.resolve(), 'Imported a different project copy.'
pd.set_option('display.max_columns',16)
summary=load_json(ROOT/'results/screen_summary.json')
display(pd.Series(summary).to_frame('value'))
print('Python:',sys.version.split()[0])
print('numpy:',np.__version__)
""",
    3: r"""all_spectra=read_dataframe(ROOT/'results/all_spectra_screen.csv',dtype={'source_id':'string'},low_memory=False)
display(pd.crosstab(all_spectra.archive_origin,all_spectra.kind))
controls=all_spectra[all_spectra.selection_group.fillna('').str.startswith('control_')]
control_summary=controls.groupby('selection_group').agg(spectra=('wdid','size'),maximum_Duv_distance=('distance_planck_uv','max'))
display(control_summary)
assert len(controls)==54
assert (controls.distance_planck_uv<0.01).all()
print('Archived control result: all 54 observations lie below the distance > 0.01 outlier threshold. Raw controls are not rerun in this notebook.')
""",
    5: r"""cie_path=ROOT/'reference/CIE_xyz_1931_2deg.csv'
assert hashlib.md5(cie_path.read_bytes()).hexdigest()=='17cca777db64b17170f06f67ce9d3ab7'
official=np.loadtxt(cie_path,delimiter=',')
assert np.max(np.abs(official[:,1:]-c.CMF_V))<1e-12
print('Verified the official CIE MD5 and the colour-matching functions used by the integration.')
display(read_dataframe(ROOT/'results/baseline_reproduction.csv'))
display(Image(filename=str(ROOT/'figures/baseline_reproduction.png')))
""",
    8: r"""headline=read_dataframe(ROOT/'results/headline_candidates.csv',dtype={'source_id':'string'})
display(headline[['candidate','source_id','hex','x','y','duv','duv_mc_p025','duv_mc_p975']])
display(Image(filename=str(ROOT/'figures/candidate_colours.png')))
""",
    10: r"""manifest=load_json(ROOT/'mwdd/manifest_enriched.json')
recomputed=[]
for _,expected in headline.iterrows():
    rec=next(r for r in manifest if r.get('source_id')==expected.source_id and r.get('kind')=='DESI' and r.get('parsed_path'))
    rawpath=c.data_path(rec['raw_path'])
    assert hashlib.sha256(rawpath.read_bytes()).hexdigest()==rec['sha256']
    w,f,iv=get_arrays(rec)
    raw_matrix=np.loadtxt(rawpath,delimiter=',',skiprows=2,ndmin=2)
    raw_columns=rawpath.read_text().splitlines()[1].split(',')
    assert np.array_equal(w,raw_matrix[:,raw_columns.index('wavelength')],equal_nan=True)
    assert np.array_equal(f,raw_matrix[:,raw_columns.index('flux')],equal_nan=True)
    system,obs,errors,origin=next(a for a in anchors(rec) if a[0]=='panstarrs')
    fc,cal=c.recalibrate_gri(w,f,obs,errors,system)
    correction=10**(-.4*(cal['cal_offset_mag']+cal['cal_tilt_mag_per_1000A']*(w-6200)/1000))
    value=c.integrate_colour(w,fc,None if iv is None else iv/correction**2,mask_sky=True)
    assert abs(value['x']-expected.x)<1e-10
    assert abs(value['duv']-expected.duv)<1e-10
    assert value['hex']==expected.hex
    recomputed.append({'candidate':expected.candidate,'sha256_verified':True,'x':value['x'],'y':value['y'],'Duv':value['duv'],'sRGB':value['hex']})
display(pd.DataFrame(recomputed))
""",
    12: r"""validation=read_dataframe(ROOT/'results/candidates/validated_colours.csv',dtype={'source_id':'string'})
display(validation[(validation.candidate.isin(['J0913+4434','J0429-0354'])) & (validation.kind=='DESI')][['candidate','cal_system','hex','duv','duv_mc_p025','duv_mc_p975','green_channel_margin']])
display(Image(filename=str(ROOT/'figures/j0913_validation.png')))
""",
    14: r"""gaia_rows=[]
for short in ['j0913','j0429']:
    audit=load_json(ROOT/f'mwdd/gaia_validation/{short}_colour_covariance_audit.json')
    for row in audit['results']:
        if '_1nm.npz' not in row['spectrum']:continue
        spectrum=np.load(ROOT/'mwdd/gaia_validation'/row['spectrum'])
        measured=c.integrate_colour(spectrum['wavelength_nm']*10,spectrum['flux_w_m2_nm'],mask_sky=False)
        assert abs(measured['duv']-row['duv'])<1e-9
        lo,_,_,_,hi=row['duv_percentiles_2_5_16_50_84_97_5']
        gaia_rows.append({'source':short,'spectrum':row['spectrum'],'sRGB':row['hex'],'Duv':row['duv'],'Duv_formal_sigma':row['duv_stat_error'],'95%_low':lo,'95%_high':hi,'formal_fraction_G_largest':row['probability_linear_green_largest_formal_only']})
display(pd.DataFrame(gaia_rows))
""",
    17: r"""contamination=read_dataframe(ROOT/'novelty/swan2026_candidate_contamination.csv',dtype=str)
display(contamination)
""",
    19: r"""audit=read_dataframe(ROOT/'novelty/novelty_evidence.csv',dtype=str)
print('Prior-literature and source-identity evidence records:',len(audit))
display(audit.head(8))
display(Image(filename=str(ROOT/'figures/survey_colour_plane.png')))
""",
}


def make_notebook(language):
    cells = []
    for index in range(21):
        if index in CODE:
            cell = nbf.v4.new_code_cell(CODE[index], id=f"science-{index:02d}")
        else:
            cell = nbf.v4.new_markdown_cell(MARKDOWN[index][language], id=f"{language}-text-{index:02d}")
        cells.append(cell)
    notebook = nbf.v4.new_notebook(cells=cells, metadata={
        "kernelspec": dict(KERNELSPEC),
        "language_info": {"name": "python", "version": "3.12"},
        "research_date": "2026-10-18",
        "narrative_language": language,
        "research_status": "AI-generated, unreviewed public-data reanalysis; colour candidates, not confirmed discoveries",
        "generator": "make_notebook.py",
    })
    nbf.validate(notebook)
    return notebook


def output_text(notebook):
    texts = []
    for cell in notebook.cells:
        for output in cell.get("outputs", []):
            if output.output_type == "error":
                raise RuntimeError("An executed notebook contains an error output")
            if "text" in output:
                texts.append(output.text if isinstance(output.text, str) else "".join(output.text))
            for key, value in output.get("data", {}).items():
                if key.startswith("text/"):
                    texts.append(value if isinstance(value, str) else "".join(value))
    return "\n".join(texts)


def validate_presentation(notebook, language, executed):
    code_cells = [cell for cell in notebook.cells if cell.cell_type == "code"]
    if len(code_cells) != 9:
        raise RuntimeError("The source workflow must retain exactly nine scientific code cells")
    if executed and [cell.execution_count for cell in code_cells] != list(range(1, 10)):
        raise RuntimeError("Notebook did not execute all nine cells in order")
    text = output_text(notebook)
    if "/workspace/scratch/" in text or "/root/.local/" in text:
        raise RuntimeError("A saved output contains a source-workspace path")
    if language == "en":
        visible_text = "\n".join(cell.source for cell in notebook.cells if cell.cell_type == "markdown") + text
        if re.search(r"[\u3040-\u30ff\u3400-\u9fff]", visible_text):
            raise RuntimeError("The default notebook has untranslated Japanese narrative or text output")
    if executed:
        figures = sum("image/png" in output.get("data", {})
                      for cell in code_cells for output in cell.get("outputs", []))
        if figures != 4:
            raise RuntimeError(f"Expected four saved scientific figures, found {figures}")
    notebook.metadata["kernelspec"] = dict(KERNELSPEC)
    for cell in code_cells:
        cell.metadata.pop("execution", None)
    nbf.validate(notebook)


def execute_notebook(notebook, kernel, timeout):
    from nbclient import NotebookClient
    # Keep transient runtime/cache files outside the publication tree.
    keys = ("MPLCONFIGDIR", "IPYTHONDIR", "JUPYTER_RUNTIME_DIR")
    previous = {key: os.environ.get(key) for key in keys}
    with tempfile.TemporaryDirectory(prefix="wd-notebook-") as temporary:
        try:
            for key in keys:
                os.environ[key] = str(Path(temporary) / key.lower())
            client = NotebookClient(notebook, timeout=timeout, kernel_name=kernel,
                                    allow_errors=False, record_timing=False,
                                    resources={"metadata": {"path": str(ROOT)}})
            client.execute()
        finally:
            for key, value in previous.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
    return notebook


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="Run both notebooks in separate fresh kernels")
    parser.add_argument("--kernel", default="python3", help="Registered execution kernel; saved kernelspec stays python3")
    parser.add_argument("--timeout", type=int, default=600, help="Per-cell execution timeout in seconds")
    args = parser.parse_args()
    notebooks = {language: make_notebook(language) for language in FILENAMES}
    code_sources = [[cell.source for cell in nb.cells if cell.cell_type == "code"]
                    for nb in notebooks.values()]
    if code_sources[0] != code_sources[1]:
        raise RuntimeError("Language editions have different scientific code")
    for language, notebook in notebooks.items():
        if args.execute:
            print(f"Executing {FILENAMES[language]}: nine scientific code cells", flush=True)
            notebook = execute_notebook(notebook, args.kernel, args.timeout)
        validate_presentation(notebook, language, args.execute)
        path = ROOT / FILENAMES[language]
        nbf.write(notebook, path)
        print(json.dumps({"notebook": path.name, "language": language,
                          "code_cells": 9, "executed": args.execute,
                          "kernelspec": "python3", "bytes": path.stat().st_size}), flush=True)


if __name__ == "__main__":
    main()
