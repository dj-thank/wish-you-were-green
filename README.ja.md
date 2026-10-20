# Wish You Were Green

## 白色矮星の色度研究 — v0.2

[English](README.md) · **日本語**

**10月20日の追加研究で、SDSSの単位をさらに613記録確定し、別の2サーベイから実際の撮像測光を取得しました。** 現在の対象範囲を限定した選別結果は **8,074適格記録、強外れ419記録・324 entity key** です。MWDD経由SDSSの2,232ファイルは **Fν 327・Fλ 939・未解決966** になりました。今回の元画素による波長支持の監査は新規確定613記録に適用し、以前の適格7,473記録は過去の値を保持しています。全記録を同じ新条件で再監査したという意味ではありません。[現行の科学集計](research/unit_resolution_followup/science_view_summary.json)・[記録を確認する画面](research/unit_resolution_followup/current_view.html)

いずれも既知の星です。この研究は、人間の視覚に対応する色度を計算し、その測定がどの条件で再現するか、大気モデルの何を検証できるかを調べます。**ChatGPT支援による探索的・未査読の研究**であり、新しい星や吸収機構、世界的優先権、母集団の発見率を確定したとはしていません。

**企画・管理：** Shota Moriwaki

**研究改訂版：** 0.2.0＋10月20日追加解析 · **更新：** 2026年10月20日 UTC

**リポジトリ：** [dj-thank/wish-you-were-green](https://github.com/dj-thank/wish-you-were-green)

**最新結果は[10月20日の日本語追加報告](research/FOLLOWUP_2026-10-20.ja.md)と[English report](research/FOLLOWUP_2026-10-20.en.md)へ。** [研究概要](research/README.ja.md)には、以前の方法・結果を日付付きで残しています。

### 10月20日の追加：別の実測値と、元画素による支持の確認

**単位を追加確定した613記録は、39枚の図で全件を実際に確認しました。** 元の有効画素と波長域が色計算を支える601記録を採用し、12記録は保留しています。内訳は、今回の波長支持の検査で追加保留となった10記録と、以前の基準でも不適格だった2記録です。以前は表示不可だった115対象の単位が解決し、**112対象で色計算を回復**しました。単位の確定だけで、欠測・ノイズ・対象位置の問題まで解決したとはしていません。[現行レコード表](research/unit_resolution_followup/science_record_view.csv.gz)・[全件の個別記録](research/unit_resolution_followup/individual_review.md)

固定した25候補について**450バンド枠を監査し、SkyMapper／J-PLUSから14対象・52測定を品質条件で採用しました。そのうち46測定は、スペクトルが応答関数の全域を覆います。** 別の撮像で得た光子による情報ですが、Gaia標準星、J-PLUSのWD locus・PS1 r零点を介した共通の較正誤差は残ります。近傍星との誤対応、マスク、欠測、S-PLUSの照会失敗も全件台帳に保持しました。[測光・対応星・品質の根拠](research/independent_photometry/README.md)

J0429−0354では、実測PS1 grizの誤差範囲にSkyMapper r/iを加えると、節点間隔800 Åの補正族で必要な最小形状変化は**4.92%**になりました。厳密な緑優位には約**5.0103%**、赤優位には約**4.9236%**を要します。ただし追加の0.02 magの誤差箱を許すと、この区別は消えます。実測の色変化ではなく、指定した制約での解の存在範囲です。別のJ0429観測設計実験では、PS1 grizとJ-PLUSの被覆10バンド（計14）を用いても、節点400 Å・変形5%の条件で逆の色順序を数値的に区別できない解が残りました。[実測値と提案バンドによる制約](research/measurement_design/README.ja.md)

**J1323−0129のSDSSは、同一原観測の画素からFλと確認できました。** 正のDuvを定性的に支持する計算は回復しましたが、native S/N 2.36と、観測epochでSDSSのPLUG位置から約1.138″離れる問題があり、高精度な独立支持は引き続き保留しています。native Gaia XPもありません。別に調べたSDSSの反復例は、**5夜・18実露出から作った2組のcoadd**であり、2夜の観測とは数えません。[反復スペクトルの形状診断](research/repeat_shape_validation/README.ja.md)・[10月20日の解釈](research/FOLLOWUP_2026-10-20.ja.md)

### 保存した10月19日の成果：個別確認と公開モデル比較

**グラフの大きなずれの実際の原因も2例特定しました。** 同じSDSS原観測の重複表現に、異なる較正の分岐が適用されていました。現行の見かけの差Δuv=0.01360・0.01517は、同じ既存補正で比較すると99.99%以上縮小します。[原画素の証拠と修正した比較図](research/outlier_followup/representation_calibration/README.md)

[10月19日の追加研究報告](research/FOLLOWUP_2026-10-19.ja.md)（[English](research/FOLLOWUP_2026-10-19.en.md)）では、残っていた**2007対象すべて**に実際の閲覧記録を追加しました。適格な曲線を表示できた1684対象と、表示不可理由を確認した323対象を区別しています。以前の337対象と合わせ、過去の要確認集合2344対象は全件に記録が揃いました。全6003 entityの目視や、異常の物理的原因の確定を意味しません。

数値実験は**実測測光450設定・1800線形計画、純H/He対照720 fits、公刊済み組成別モデル図25対象**まで進めました。**J0429−0354では、同じ観測PS1 grizの誤差範囲を満たしながら、緑優位と赤優位の両方の形状を最大約4.25%の変形で構成できました。** 節点800 Å・各公表誤差1倍の条件では、25対象中14対象が2%以下の変形ではgrizに整合しません。指定した補正空間での識別の限界であり、実測の較正誤差分布や新しい大気組成の測定ではありません。[色判定の制約実験](research/calibration_followup/README.md)・[公開モデルとの実比較](research/model_validation/README.md)

## 現行結果と過去の記録

| 対象・処理 | 現行値または監査実績 |
|---|---:|
| 元の全スペクトル台帳 | 9,902記録・6,003 catalogue entity key |
| 今回の対象範囲の波長支持を反映した適格記録 | **8,074** |
| 現行の強外れ選別 | **419記録・324 entity key** |
| MWDD SDSSのフラックス表現 | **Fν 327・Fλ 939・未解決966** |
| 単位と元画素の支持を追加確認した記録 | **613：色の採用601・保留12** |
| 以前表示不可の対象で単位解決／色回復 | **115／112** |
| 固定25候補の追加撮像測光 | **450枠・品質採用52測定・全域被覆46測定・14対象** |
| 実際に全パネル目視した旧強外れ対象 | 337対象・22画像 |
| 10月19日に個別確認を完了した要確認対象 | 2007対象・126画像：曲線あり1684／利用不可323 |
| 10月19日の表示に用いたスペクトル | 原SHA確認・当時の色再現3041記録 |
| 10月20日の追加個別閲覧 | 613記録・39画像、全パネル実見 |
| SHA256一致を確認して再取得した要確認入力 | 4,355件。旧計算4,353件再現、既存失敗2件を保持 |

v0.1の**適格9,023・強外れ337 entity**、10月18日の**適格7,473・強外れ395記録／308 entity**、10月20日の旧基準互換比較**8,084／421／325**は、それぞれ保存した別時点・別条件の値です。現在の判定は[科学レコード表](research/unit_resolution_followup/science_record_view.csv.gz)と[天体表](research/unit_resolution_followup/science_object_view.csv)を使ってください。今回の元画素支持の更新は613記録に限定しています。entity keyには過去の位置照合が残り、同定済みの独立した星の数とは限りません。これらは探索上の選別件数であり、発見の有意性ではありません。[数え方と監査範囲](research/README.ja.md)

![10月20日の対象範囲を限定した元画素支持の更新を反映した色度分布](research/unit_resolution_followup/science_colour_plane.png)

*計算したCIE色度の選別図です。元画素支持の新規監査は613記録に限定し、以前の適格記録は旧値を保持しています。原スペクトル、保留例、旧結果は追跡可能です。*

## 主要4候補の現在のDESI色推定

以下は **DESIスペクトルを、v0.2の標準化処理で観測PS1 g,r,i測光へ再較正した値**です。CIE 1931の2°標準観測者を用い、95%区間は指定した画素ノイズ・測光較正モデルを条件とするモンテカルロ分布の中央区間です。

| 候補 | Gaia DR3 source_id | 表示色の説明 | sRGB | Duv | 条件付き95% Duv区間 |
|---|---|---|---|---:|---|
| WD J0913+4434 | 818833831355548928 | 淡い黄緑 | #F1FFC9 | +0.019058 | +0.016975 ～ +0.021233 |
| WD J0429−0354 | 3204436719718449280 | 淡い黄緑 | #F8FFDC | +0.012809 | +0.011973 ～ +0.013651 |
| WD J1329+0033 | 3711047662972690688 | ピンク | #FFC1CF | −0.022652 | −0.024811 ～ −0.020482 |
| WD J1323−0129 | 3638333660492606976 | 黒体から外れた黄色・高精度SDSS支持は保留 | #FFE96A | +0.023498 | +0.020943 ～ +0.025993 |

[丸め前の根拠表](research/precision/candidate_recalibration/standardized_colours.csv)に、測光アンカー、誤差、原データSHA256、較正係数を記録しています。[v0.1の旧代表値](results/headline_candidates.csv)も保持しています。J1323の表示色の1段階の差を含め、小さな変更は較正・誤差定義の変更による再解析であり、星の時間変化の測定ではありません。16進色の末尾を物理的な測定精度と解釈しないでください。[PS1の定義・DR1/DR2照合](research/literature/swan_photometry_definition.md)

**Duvが正でも、緑色とは限りません。** CIE 1960 u,v図上で黒体軌跡からの符号付きの隔たりを示す値で、|Duv|=0.01は探索上の比較基準です。普遍的な見分けの限界や有意水準ではありません。sRGBは規格化した標準観測者の表示値であり、天体写真、明るさ、暗順応した目での見え方を示しません。

## 追加解析で分かったこと

- **初期27候補を一件ずつ追跡しています。** DESIの条件付き区間は25件、そのうち新しい測光アンカーを得たのは12件。Gaiaのnative共分散は26件です。fullとtruncatedは同じ観測の相関した再構成です。[全27件の総合比較](research/candidate27_followup.md)
- **3区間が探索境界を越えても、発見確定とはしません。** DESIとGaia両再構成の95%区間が、同じ側で|Duv|>0.01となるのは初期27中9件。そのうち1件はGaiaの近傍が10倍超明るく、残る8件にも未使用z残差の注意例が2件あります。これは条件付き結果の共通集合であり、合成確率ではありません。
- **較正に使わない測光への予測を試しました。** griでfitしたスペクトルからPS1 zを予測すると、25件中10件で残差の絶対値が0.05 magを超えます。全誤差を含む有意差ではなく、追加較正診断です。yは全波長域を覆わないため予測を保留しました。[未使用帯域の検証](research/precision/candidate_recalibration/README.md)
- **別夜・時系列の失敗例を保持しました。** DESIの公開済み4対象7露出を新たに取得し、3対象6夜は完全色の比較が可能でした。J1329の追加夜はZカメラが無効です。ZTFは候補2,473測定・対照4,646測定を解析しましたが、新しい固有変光を確立していません。J1323の位置がずれた明るい1点も、生データ・棄却理由・原画像の確認を残しています。[DESI](research/literature/README.md)・[ZTFとGaia近傍](research/external_validation/README.md)
- **元素DBと既存モデルにも来歴確認が必要です。** PEWDDには名前と座標が矛盾する236行があり、3例を元論文とGaiaで確認すると異なる種類の誤りでした。236行すべてのIDが誤りとはしていません。候補には既存の大気解析もあります。[同定監査](research/literature/independent_key_audit.md)・[先行研究表](research/literature/outputs/candidate27_prior_inventory.csv)

次の重点は、固定金属比と個別Na/Ca・Mg/Caの比較、未分離伴星と大気モデルの識別、実測に基づく較正誤差下での回収率・偽陽性評価です。griを変えず色を動かす形状の制約付き試験も実行しましたが、その人工変形を実測誤差としていません。同じ分光から計算した色を、同じ分光の尤度へ独立情報として二重投入しないことも明記しています。[予測・反証条件・追加データを定めた研究計画](research/README.ja.md)

## 報告・ノート・監査表への入口

| 資料 | 内容と版 |
|---|---|
| [10月20日追加報告](research/FOLLOWUP_2026-10-20.ja.md)・[English](research/FOLLOWUP_2026-10-20.en.md) | 現行の限定監査集計、追加の実測制約、反復分光と限界 |
| [研究概要](research/README.ja.md)・[English](research/README.md) | 現行要約と、保存した10月18–19日の方法・結果 |
| [現行記録の閲覧画面](research/unit_resolution_followup/current_view.html)・[科学集計](research/unit_resolution_followup/science_view_summary.json) | 613件の単位判定、元画素の支持による保留、現行の色 |
| [別撮像の測光](research/independent_photometry/README.md)・[測定設計](research/measurement_design/README.ja.md) | 全25対象・450枠の採否、品質採用52／全域被覆46測定、条件付き実験 |
| [反復スペクトルの形状](research/repeat_shape_validation/README.ja.md)・[English](research/repeat_shape_validation/README.md) | DESIの4組とSDSSの2 coadd、共有アンカー・元の観測条件 |
| [10月19日追加研究](research/FOLLOWUP_2026-10-19.ja.md)・[English](research/FOLLOWUP_2026-10-19.en.md) | 個別確認の完了、実測測光の制約、公開モデル比較、原データ診断 |
| [追加2007対象の全件台帳](research/outlier_followup/individual_review.csv) | 個別の観察、利用不可例、固定した画像への対応 |
| [追加研究ノートブック](research/research_extension.ipynb) | v0.2追加解析の保存版。実施時の検証、集計、比較図 |
| [初期27追跡CSV](research/candidate27_followup.csv)・[JSON](research/candidate27_followup.json) | 全候補の区間、来歴、次に確認すること |
| [候補の誤差比較図](research/candidate27_uncertainty_comparison.png) | 全27対象。Gaia両再構成の独立性に注意 |
| [10月18日の天体別監査HTML](research/outlier_audit/object_audit.html) | 全9,902記録の保存した履歴。10月20日の採否は現行閲覧画面を参照 |
| [目視記録01–11](research/outlier_audit/visual_review_01_11.md)・[12–22](research/outlier_audit/visual_review_12_22.md) | 旧強外れ対象の全パネルを実見した個別記録 |
| [v0.1日本語報告](docs/report.ja.md)・[English](docs/report.en.md) | 冒頭に訂正を明記した旧報告。旧数値を保持 |
| [v0.1日本語ノート](white_dwarf_colour_research.ja.ipynb)・[English](white_dwarf_colour_research.ipynb) | 旧実行結果を保持し、冒頭に訂正を追加 |
| [データ公開・利用条件](docs/data-availability.md)・[再現手順](docs/reproducibility.en.md) | 元のコンパクト入力と旧代表値の検証範囲 |
| [変更履歴](CHANGELOG.md) | 研究上の訂正と解釈の変更 |

## 再現・検証

Python 3.12を使います。最初の依存導入にはパッケージ取得先またはローカルキャッシュが必要です。

```bash
git clone https://github.com/dj-thank/wish-you-were-green.git
cd wish-you-were-green
python3.12 -m venv .venv-colour
.venv-colour/bin/python -m pip install -r requirements-core.txt

.venv-colour/bin/python scripts/verify_reproduction.py --with-controls
.venv-colour/bin/python -m unittest discover -s tests -p 'test_*.py' -v
.venv-colour/bin/python scripts/verify_research_extension.py
.venv-colour/bin/python scripts/verify_research_followup.py
.venv-colour/bin/python scripts/verify_research_oct20.py
```

Windowsでは対応する `.venv-colour\Scripts\python.exe` を使ってください。

コンパクト検証は、保存したv0.1の主要DESI/Gaia計算とSDSS対照54観測をオフラインで再計算します。日付付きの追加研究検証器は各時点の保存入力と計算を確認します。10月20日の検証器は、保存したコンパクト入力から単位・画素支持、測光の再構築、実測／提案の制約、反復形状の診断を追加検証します。全サーベイ取得、実際の目視、全乱数試行、GaiaXPyの導入を繰り返す処理ではありません。検証成功は指定した計算の整合性を示し、天体物理の新規性や系統誤差の不存在を証明しません。

より広い再計算は[研究報告の再現説明](research/README.ja.md)を参照してください。native XP再構成は[依存を固定した別のGaiaXPy環境](mwdd/gaia_validation/requirements-gaia.txt)を使います。全原スペクトルやカメラFITSの復元には公開アーカイブへの接続とmanifestのSHA256確認が必要です。過去の入力を現在の別応答へ黙って置き換えません。

## 帰属・引用・再利用

**Shota Moriwaki** が企画・管理しています。取得、コード、解析、検算、文章作成には **OpenAI ChatGPTの支援**を使用しました。ChatGPTは使用したツールとして開示し、科学論文の著者とはしていません。本研究は未査読で、引用した研究者や観測チームの所属・支持を表すものではありません。

観測・較正はDESI、ESA/Gaia/DPAC、SDSS、Pan-STARRS、SkyMapper、J-PLUSの各チームに帰属します。MWDD、PEWDD、CDS、SVO Filter Profile Service、元論文の分類・大気モデル・応答関数もそれぞれの提供者の成果です。Hollandsらの色計算と既知の異常色白色矮星は先行研究として扱います。[謝辞](ACKNOWLEDGMENTS.md)・[追加データの指定謝辞](research/literature/DATA_ACKNOWLEDGMENTS.md)・[文献](docs/references.bib)

利用した版またはcommitを特定し、使った原論文・データも引用してください。[CITATION.cff](CITATION.cff)に機械可読の引用情報を置いています。

> Moriwaki, Shota (2026). *Wish You Were Green: white-dwarf chromaticity research*. Version 0.2.0. Unreviewed public-data research and reproducibility code. https://github.com/dj-thank/wish-you-were-green

独自コードは **Apache-2.0**、独自解説文は **CC BY 4.0**です。第三者資料は元の条件を保持し、未変更のCIE表は **CC BY-SA 4.0**です。[ライセンス詳細](LICENSES/README.md)・[貢献方法](CONTRIBUTING.md)
