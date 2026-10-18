# 文献・元素量・別観測夜による追加研究

監査日: 2026-10-18。これは既存の4候補だけを補強する調査ではなく、`research/outlier_audit/object_audit.csv` の全6,003 entityと、そのうちの27色候補を対象とした追加監査である。entityには暫定的な位置照合を含むものがあり、6,003を無条件に独立した星の数とは扱わない。入力のSHA256は各出力に保存している。

## 今回、実際に進めたこと

### 1. 全entityをPEWDDに照合し、外部データの識別不整合を検出した

[PEWDD](https://github.com/jamietwilliams/PEWDD) のコミット `023dba3176ac367c6cf2b5968847a80d79e3c594`（2026-03-27）を固定した。取得した表は3,475行、206列である。Gaia DR3/EDR3の数値IDを文字列のまま照合し、6,003 entity中1,107 IDに2,547件の文献・モデル行が対応した。星ごとに論文を潰して平均せず、各行のTeff、logg、H/Na/Ca/Mg/Fe/Li/K、検出か上限かを残した。[出力と数え方](outputs/pewdd_summary.json)

**外部表だから正しいと仮定しない。** 完全なJ座標名から復元した位置と、同じ行のRA/Decが10分角を超えて異なる行を236件検出した。これは233種類のGaia designationを含むが、「233個のGaia IDが誤り」という意味ではない。別実装による独立確認で、少なくとも2例はGaia IDの誤対応、別の1例はGaia IDが正しくRA/Decだけが誤対応と分かった。原論文CDS表とESA Gaiaの一次データで照合した根拠は [独立確認記録](independent_key_audit.md) にある。残りを自動修正せず、[要確認行](outputs/pewdd_identity_review.csv) として保持する。

PEWDDでは誤差 `-1` は上限であり、検出として扱わない。同じ論文・同じモデル行でNaとCaが検出されたIDは30個だが、これは校正・identity・モデル仮定を全て通過した化学組成サンプルの数ではない。大気中の元素比を降着天体の元素比へ直接読み替えることもできない。[Williams et al. 2024](https://www.aanda.org/articles/aa/full_html/2024/11/aa50509-24/aa50509-24.html)

### 2. 27候補すべてに個別の先行研究・露出台帳を作った

[個別研究表](outputs/candidate27_prior_inventory.csv) は、各候補の既知分類、温度、重力、質量、元素比の仮定、Swan分類の確信度、混入推定、使える夜数、今回の判断、次に確かめる項目を収録する。[元の対象行](sources/candidate27_prior_rows.json) を残したので、列の転記や解釈を追跡できる。

27候補のうち25個は [Swan et al. 2026](https://arxiv.org/html/2609.04314v1) と [Kilic et al. 2026](https://arxiv.org/html/2606.25377v2) に正確なGaia IDで一致した。PEWDDの上記snapshotには27個とも一致しないが、25個に既存の大気解析があることからも、単一DBの不掲載を新規発見の根拠にできない。DESI表にないPSO J186.4406+47.1036にも、[Blouin & Dufour 2019, Table 2](https://arxiv.org/html/1910.06168v1) の既存解析がある。名前で対応するDQの値はTeff=6294±67 K、logg=7.924±0.059、M=0.528±0.034太陽質量、log(C/He)=−5.33である。Gaiaとの位置照合の確認は別途必要である。

Kilic2026のDZ解析はCa量を調節し、他の金属をCIコンドライト比に固定している。したがってこの表にNa量を独立測定した証拠はない。同論文のH/Heに関する仮定も、形式的なTeff・質量誤差に収まらない変動を生み得る。SwanのH/Heモデルから得た物理量を、適切な金属・炭素大気モデルの代わりに採用していない。

27候補にはDESIの登録露出が42件あり、全3カメラに少なくとも有効画素がある露出は32件である。この条件はまだ完全波長域の保証ではない。J1105+7247の「13露出」は、そのうち9件がB/R/Z全画素マスクされている。J0006+0257は2露出でも同一夜である。これらを独立観測証拠として水増ししない。[全露出と直接取得URL](outputs/candidate27_desi_exposure_inventory.csv)

PS1測光の単位・消光・品質・誤差floorを原論文で確認し、既存4候補ではMASTのDR1/DR2原応答とも照合した。12個のgri中心等級は全て一致し、Swan誤差はDR1の丸めたnative誤差へ0.01 magをquadratureで加えた値に一致する。これを重複して追加しない。[測光定義の検証](swan_photometry_definition.md)

この測光を使う別処理で25候補のgri再較正が可能になったため、較正に使わないzへの予測も実行した。25個ともzの全波長域を含み、残差は−0.08967～+0.09904 mag、絶対値0.05 mag超は10個だった。griで一致するだけでは赤側まで同じ精度で較正できたといえない対象を具体的に選べた。欠損画素の影響と条件付き画素誤差を記録し、全25個のyは波長不足として外挿しなかった。[未使用zの結果と限界](../precision/candidate_recalibration/README.md)

### 3. 新たに4天体の別観測夜を原データまで追った

[DESIの公式説明](https://data.desi.lbl.gov/doc/access/) では、SPARCLの対象はHEALPixごとの合成スペクトルである。今回必要なのは露出ごとの比較なので、DESI DR1 ironの `exposures/NIGHT/EXPID/cframe-*.fits.gz` を直接取得した。TARGETIDとFIBERを同時に照合し、元ファイルSHA256、観測日時、Fλ、IVAR、MASK、波長、分解能行列を保存した。分解能行列は装置の線拡がりを表し、画素ノイズの共分散行列とは異なる。[公式データモデル](https://desidatamodel.readthedocs.io/en/latest/DESI_SPECTRO_REDUX/SPECPROD/exposures/NIGHT/EXPID/cframe-CAMERA-EXPID.html)

追加3天体については、色を計算する前に「各夜でR帯S/Nが最大、かつ各カメラに有効画素がある露出」を選ぶ規則を固定し、全6夜のB/R/Zを取得した。生の画素を保ち、解析時にMASK=0かつIVAR>0を要求する。3種類のカメラ接合位置を試し、カメラごとの倍率を調整して一致させることはしていない。

| 天体 | DESI NIGHT | 同じPan-STARRS測光によるDuv | 今回の結論 |
|---|---|---:|---|
| J0111−0533 | 20211024 / 20211110 | −0.009529 / −0.011147 | C2形状は繰り返し見えるが、強い外れ値の閾値0.01を両夜で越えない。 |
| J1105+7247 | 20210223 / 20220314 | +0.010261 / +0.013296 | 両夜の点推定は閾値を越えるが、旧夜の画素ノイズだけのuv誤差が約0.00106あり境界的。 |
| J1252+7457 | 20210422 / 20210425 | −0.010579 / −0.006955 | 第2夜は負fluxが9.13%、画素ノイズだけのuv誤差が約0.00174。強い外れ値が再現したとは数えない。 |

このDuvは「確定した固有色」の新しい採用値ではない。各夜を比較するために同じ測光を使った診断値であり、独立した校正の証拠ではない。画素ノイズに加えて、測光誤差、波長に相関する校正残差、空の差し引き、時間変化を扱う必要がある。正規化した図の陰影には、正規化係数自体の不確かさや画素間共分散も入っていない。[6露出の数値](outputs/desi_additional_nights_summary.csv)、[全計算](outputs/desi_additional_nights_comparison.json)、[共通波長域の図](outputs/desi_additional_nights_spectra.png)

J1329+0033は別夜（NIGHT 20220311）の深いC2バンドが再現する一方、Zカメラは全2,881画素がマスクされIVAR=0だった。可視域端の色感度が小さくても、完全なgri再較正に成功したと見なさず、完全色の追加検証は「不可」と明記した。比較元MWDDの`flag=1`はDESI bitmaskと同じ意味とは確認できないため、[Swan公式の対象別ASCII](https://cygnus.astro.warwick.ac.uk/phsdaj/WhiteDwarfs/J1329/WDJ132942.69+003336.60/index.html)から第1夜の原MASKも回収した。同archiveの第2夜の波長・flux・IVARが直接取得したcframeと公表桁丸めの範囲で一致し、MASKは全画素で完全一致することを検算した。最終の形状図では両夜とも原MASK=0かつIVAR>0を要求する。最初の夜のB/R/Zで4/7/18画素がマスクされている。[第1夜の出典と独立照合](sources/j1329_desi_20220127_swan_manifest.json)、[第2夜のFITS由来情報](sources/j1329_desi_20220311_manifest.json)、[比較と限界](outputs/j1329_second_epoch_comparison.json)

## 学術的発見に向けて、優先する仮説

既知の緑色WD、Naによる緑から青への連続変化、C2によるピンク色、H/He混合大気のCIA自体を新説と呼ばない。[Hollands et al. 2026](https://arxiv.org/html/2610.18966v1) にはこれらの機構と複数の既知緑色対象があり、既存repoでも既知対象を照合済みである。新規性の中心を「別の色名を付けた星の数」から、モデルや観測のどの仮定が破れたかを再現可能に示すことへ移す。

### 優先1: 金属比を固定する大気モデルは色の外れ方を説明できるか

J0913+4434、J0429−0354、J1105+7247、J1500+1343などのDZについて、固定CI金属比モデルを基準に、Na/CaとMg/Caを自由にしたモデルが**未使用波長域や別装置の測光**を改善するかを検証する。Na Dの広い翼、Caの青側抑制、Mgの領域を別々に評価し、滑らかな校正傾斜だけで改善する仮説とも比較する。Kilic2026が個別元素調整を行っていない点はこの検証の具体的な余地である。

棄却条件は、Naを自由にしても未使用データへの予測性能が上がらないこと、あるいは改善が許容される校正誤差で説明されること。観測スペクトルから計算した色を同じスペクトルと別の独立情報として尤度に二重投入しない。色は3つの積分に圧縮した診断であり、追加の物理情報そのものではない。今ある公刊図を見ただけで、独立Na測定、地殻物質降着、異常元素比を宣言することはできない。

### 優先2: 大気モデルの不安定さと未分離伴星を分ける

J1323−0129はKilic2025から2026への変更でTeffが4262→3648 K、質量が0.445→0.268太陽質量、log(Ca/He)が−9.94→−11.87となる。これは時系列変化の証拠ではなく、モデル仮定を変えた解析の差である。Gaia距離で固定した絶対SED、H/He・Na線翼・CIA、単星と二成分SEDを同じ誤差モデルで比較する。モデルの公開説明では主な金属大気gridの下端は4000 Kなので、3648 Kの解に実際に使われたgrid範囲・補間の扱いも確認対象となる。説明不足だけで解を無効と断定しない。[Kilic2025](https://arxiv.org/abs/2412.04611)、[Kilic2026](https://arxiv.org/html/2606.25377v2)

さらにJ0716+6217、J0111−0533、J0851+4245、J1642+0804のDQ単星fitは0.20–0.264太陽質量である。Kilic2026自身が低質量DQの伴星混入と元素量の不確かさを指摘しているため、その警告を対象ごとの絶対SED・バンド深さへ落とし込む価値がある。J0111の分子形状は今回の2夜で観測されたので、対象選定の根拠はある。連星性の確定には時系列速度などの追加観測が必要であり、色だけで判定しない。

### 優先3: DQの色を、炭素量と圧力シフトを分ける診断へする

DQpecのC2帯の圧力シフトと密度依存性は既知である。[Blouin & Dufour 2019](https://arxiv.org/html/1910.06168v1) は大気密度に伴うDQ→DQpec変化と例外を調べている。今回の候補ではPSO J186.4406+47.1036にDQ/DQPEC、WD1338+027に2019年のDQpecと2026年のDQという表記差がある。最初に分類基準と実際の帯位置を確認する。

新たに検証する量は、Teffと炭素量を合わせたときの各C2帯位置・深さと、連続光除去後の色残差との対応である。圧力シフトのある・ないモデルの予測方向が、装置の波長校正誤差や磁気歪みの方向と区別できるかをテストする。まず既知の圧力シフト・磁気DQを対照群にし、候補で同じ規則が成立するかを検証する。モデル間で密度や磁場を識別できなければ、その限界を成果として報告する。

### 優先4: 選択関数を持つ、再現可能な異常色標本を作る

今回、個別のカメラ欠損や低S/N夜を追加しただけで「全観測で強い外れ値」と言える対象が変わった。全件の選別手順、閾値、欠測、別装置・別夜の証拠を固定し、通常WDスペクトルへ相関した校正傾斜や実際のノイズを加えて、偽陽性と回収率を測る。探索に使わなかったサーベイ部分で性能を検証する。これにより、近傍汚染や古いDBの欠落を含む不均質な便宜標本の割合から、母集団の割合を推測する誤りを避ける。

元素DBとの連携は、まず今回見つかった識別情報の整合性監査から始める。元論文・Gaiaの正しい対応を確認した修正候補表を作り、元データを保存したまま由来を追える補正層を持たせる。外部DBへ無断で変更を送ってはいない。これは元素比・色・冷却年齢を結び付ける解析の前提となる、実用性の高い成果である。

### 追加の検証可能な展開

- **変光と平均色:** Gaiaの変光分類やZTFを用い、単一epoch分光と期間平均の測光の組合せが色をずらすか調べる。Gaiaの`NOT_AVAILABLE`は一定光度の証明ではない。位相依存の分光を得た場合は、Duvだけでなく実際のC2/Na帯変化を確認する。
- **未使用測光への予測:** griで再較正した後、波長域が十分なら独立のu/z/yや紫外・近赤外データを検証に使う。新しい測光で同じモデルを再fitした結果を、未使用データへの予測と混同しない。
- **希少型分類との交差:** [Byrne et al. 2025](https://academic.oup.com/rasti/article/doi/10.1093/rasti/rzaf044/8272669) の[公開手法](https://github.com/xbyrne/wd_xp_methods)、Vincentなどの分類表と照合し、色外れ値と分類不一致が専門大気解析の失敗を予測するか検証する。既存のt-SNE/UMAP検出を再実行しただけで新手法とは呼ばない。
- **色観測者モデルへの頑健性:** CIE1931を比較の主軸に残し、他の標準観測者関数でも結論が変わらない対象を区別する。表示色や色覚依存の差を、新しい星の物理として数えない。

## 再実行

repo rootから実行する。小さな対象行とmanifestは保持し、論文全文・全サーベイ表・全カメラFITSはキャッシュ扱いとする。`build_candidate_prior_inventory.py` は対象行の保存があれば全サーベイ表なしでも再実行できる。DESIコードにはnumpy/astropy/matplotlibおよびrepoの色計算依存が必要である。

```bash
python research/literature/fetch_pewdd.py
python research/literature/crossmatch_pewdd.py
python research/literature/build_candidate_prior_inventory.py
.venv-research/bin/python research/literature/check_desi_second_epoch.py
.venv-research/bin/python research/literature/validate_desi_candidate_nights.py
python research/literature/build_candidate_prior_inventory.py
python research/literature/verify_swan_ps1_definition.py
.venv-research/bin/python research/precision/candidate_recalibration/heldout_z.py
```

元の大きな表や全FITSから再抽出する場合:

```bash
python research/literature/fetch_atmosphere_sources.py
.venv-research/bin/python research/literature/check_desi_second_epoch.py --download
.venv-research/bin/python research/literature/validate_desi_candidate_nights.py --download
```

ダウンロード先の変更や大気表の新versionを黙って受け入れず、記録したSHA256との差を確認する。色計算コードのSHA256も別夜比較のJSONに記録する。棄却された観測、較正失敗、未確認のidentityを削除して成功例だけ残す処理は行っていない。

## データの由来・利用条件・謝辞

DESI DR1データは[CC BY 4.0](https://data.desi.lbl.gov/doc/acknowledgments/)で公開され、対応するDR1論文の引用、変更の明示、指定謝辞が求められる。使用論文は DESI Collaboration et al. (2026), *Data Release 1 of the Dark Energy Spectroscopic Instrument*, AJ 171, 285。公開アーカイブのFITSから対象行を抽出してNPZに格納した。元fluxを調節して保存しておらず、解析時だけ不良画素除外、カメラ接合、測光再較正、色積分を行う。元ファイルのURL/SHAと、加工の手順・生成物はmanifestとコードに分かれている。指定謝辞は [DATA_ACKNOWLEDGMENTS.md](DATA_ACKNOWLEDGMENTS.md) に記載する。

Swan2026の[公式数値表](https://cygnus.astro.warwick.ac.uk/phsdaj/WhiteDwarfs/Tables/)、Kilic2025/2026のarXiv同梱数値表、PEWDDは、各著者・元論文に帰属する。著者が示す利用条件を保持し、本repoのコードのライセンスを外部表へ付け替えない。全論文本文や図を新たにrepoへ転載していない。PEWDDを引用する際はWilliams et al.2024に加え、実際の元素量を報告した各元論文も引用する。Pan-STARRS、SDSS、Gaia測光の原出典と謝辞は、それらを用いる本研究の最終論文にも明記する。
