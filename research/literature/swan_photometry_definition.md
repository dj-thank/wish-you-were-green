# Swan2026外部測光を色較正に利用する際の定義確認

監査日2026-10-18。根拠は [Swan et al.2026](https://arxiv.org/html/2609.04314v1) の§3、§5.2、Table11と、MASTから直接取得したPan-STARRS DR1/DR2の数値である。

## 単位・消光・測光系

- `Pan-STARRS.g/r/i/z/y` と対応する `_error` はmag。PS1は [自然なPS1帯域で定義されたAB測光系](https://outerspace.stsci.edu/spaces/PANSTARRS/pages/298812303/PS1+Filter+properties) であり、SDSS griとして変換せずPS1固有の透過曲線を使う。
- `SDSS.u/g/r/i/z` と `_error` はmag。SwanはSDSSについて小さな零点補正も行っているので、SDSS列を無加工の元SDSS測光と同じと仮定しない。
- `Gaia.DR2.*` と `Gaia.DR3.*` は**electron/sとその誤差**。magではない。
- Swanでは距離・赤化をモデルの自由パラメータとし、3D消光地図をpriorに使う。表のPS1値は観測側の測光として使う。確認した4天体12bandは未消光補正のMAST mean-PSF等級と数値的に完全一致した。色計算で観測スペクトルへ合わせる際に、測光だけを消光補正しない。

## 品質選別と誤差

§3はGaia固有運動を用いたepoch照合を記載する。最初に45″以内の候補を集め、観測epochへ座標を伝播し、最近傍を採用して3″より離れたものを捨てる。PS1では飽和リスクのあるg/r/i<14、z<13.5、y<12.5を除外し、推定近傍混入が1%を超える測光を除外する。§5.2.3のモデル残差による事前選別はDA/DB/DBAについて説明されている。DQ/DZの色を平滑なH/Heモデルに合うように任意に除外・修正する根拠にはしない。

Swanは測光誤差へ1%をquadratureで追加したと述べる。今回の実データ比較では、**0.01 magをquadratureで足した数値**を確認した。これを1%fluxから換算した0.010857 magと混同しない。Swanの公表誤差をそのまま使用する場合、同じ0.01magを再追加しない。これは全誤差が独立であるという意味ではなく、同じPS1をアンカーにした複数スペクトルには共通誤差が残る。

## DR1/DR2の差を実測で確かめた

既存4候補についてMASTの `/panstarrs/dr1/mean.csv` と `/panstarrs/dr2/mean.csv` を直接照会した。すべての戻り行を [DR1応答](sources/ps1_mast_dr1_headline_checks.json)、[DR2応答](sources/ps1_mast_headline_checks.json) に保存した。照合先のobjIDは文字列で保持し、等級・誤差を比較した。これは既に同定済み対象の測光定義の検算であり、等級一致だけで新たな天体同定を成立させる手順ではない。

| 例 | MAST DR1のnative誤差 | MAST DR2のnative誤差 | Swan公表誤差 | 解釈 |
|---|---:|---:|---:|---|
| J0913+4434 g | 0.033326 | 0.026569 | 0.0347691 | sqrt(0.0333²+0.01²)と一致。 |
| J0429−0354 i | 0.007109 | 0.005005 | 0.0122642 | sqrt(0.0071²+0.01²)と一致。 |
| J1329+0033 g | 0.018000 | 0.020552 | 0.0205913 | sqrt(0.0180²+0.01²)と一致。 |

全12bandについて、中心等級はDR1・DR2・Swanで同じである。Swan誤差はDR1 native誤差を小数4桁に丸めた値への0.01mag追加に一致し、MWDDの既存アンカー誤差はDR2 native値に一致した。したがって「誤差が一致しないから異なる天体」とも、「Swan誤差にもう一度floorを追加」とも判断しない。[12band整合表](outputs/ps1_swan_definition_checks.csv)、[検算サマリー](outputs/ps1_swan_definition_summary.json)

PS1の[公式注意点](https://outerspace.stsci.edu/spaces/PANSTARRS/pages/298812205/PS1+FAQ+-+Frequently+asked+questions)には、平均PSF測光の単露出検出限界付近の選択バイアス、stack/forced測光の性質の違い、高固有運動星の分裂検出などがある。新12候補への測光追加では、Swanで存在する値を使う場合でも、変光・近傍像・bandの有限値と品質を個別監査した結果を保持する。

## 実行時の較正受理条件

`check_desi_second_epoch.py` と `validate_desi_candidate_nights.py` は、既存screenと同じ `max gri residual <0.15 mag`、`|tilt| <0.25 mag/1000 Å` を明示的に適用する。計算が収束してもこの条件を満たさないfitは受理しない。完全な色として扱うにはさらに波長coverage条件が必要である。今回の3天体6露出×3接合の全18fitはこの較正gateを通過した。最大|tilt|=0.0214381、最大残差=0.0337857 magである。低S/Nや閾値をまたぐDuvの判定は、この較正gateを通ったことと別に評価する。
