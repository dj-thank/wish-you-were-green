# 装置間で形状が違う4対象の、原ファイバー位置と観測epochの照合

2026-10-19 UTC。実際のグラフ確認で選んだ4対象を、公式Gaia DR3の座標・固有運動と、SDSS原FITSのファイバー位置まで戻って調べました。[照会ADQL](gaia_query.adql)、[Gaia原CSV](gaia_sources.csv)、[取得来歴](gaia_sources.provenance.json)、[原FITSヘッダーと可逆圧縮コピーの一覧](sdss_original_headers.json)を保存しています。

| Gaia DR3 source_id | SDSS row | plate / MJD / fiber | 固定2016位置との距離 | 観測epochへ移した位置との距離 |
|---|---:|---|---:|---:|
| 1038076351151065088 | 9122 | 5708 / 56605 / 705 | 2.0433″ | **0.8959″** |
| 1311674353544358912 | 9399 | 5201 / 55832 / 412 | 0.3243″ | **0.0713″** |
| 2586182156053386240 | 8781 | 4661 / 55614 / 318 | 1.7313″ | **1.2131″** |
| 1025033665052512000 | 9079 | 7445 / 56720 / 47 | 2.0033″ | **1.8025″** |

丸め前の値は[結果CSV](epoch_associations.csv)と[JSON](association_summary.json)にあります。対象を選んだのは位置照会の前です。どの曲線もこの距離に応じて移動・除去していません。

## 実際に確認した点

元のSDSS FITSで、対象ファイバーの座標は **PLUG_RA / PLUG_DEC** です。同じヘッダーの **RA / DECはプレート中心**であり、対象位置の代替に使えません。コードはPLUG座標がなければ停止します。この4例には全てPLUG座標があり、代替座標を使った値は結果に含みません。

Gaiaのpmraは赤緯のcosを含む定義として扱い、DR3のref_epochから原FITSのMJDへ `SkyCoord.apply_space_motion` で伝播しました。距離・視線速度によるperspective motion、全位置共分散、観測日の中の時刻差はモデル化していません。位置の誤差確率や対応の事後確率を報告する解析ではありません。

4例はいずれもBOSS系の原スペクトルで、記録したRUN2Dはv5_13_2です。[SDSSの原資料](https://www.sdss4.org/dr17/spectro/spectro_basics/)はこの処理版をDR17のBOSS/SEQUELS/eBOSSに対応付け、[装置資料](https://www.sdss4.org/instruments/boss_spectrograph/)はBOSSのファイバー直径を2″としています。

2例ではepoch補正後も中心間距離が1″を超えます。これは開口による光量損失や色依存の集光、入力座標・追尾条件を調べる理由になりますが、**別天体への誤対応の確定ではありません**。点像分布の裾はファイバーに入り得るため、半径1″を二値的な「観測できた／できない」の境界にはしていません。0.0713″の例では、単純な大きい中心ずれで形状差を説明する仮説は支持されません。

## 較正経路も異なる

表示されている現行の各曲線は、較正の有無と使った測光系が同じとは限りません。元台帳で確認できる例をそのまま記録します。

| 対象 | 現行台帳に記録された主な違い |
|---|---|
| 1038076351151065088 | Gaia XP row3787はSDSSアンカーで較正、direct SDSS row9122は未再較正。別のrow3786は単位保留 |
| 1311674353544358912 | MWDD SDSS row4185は傾き約0.2001 mag/1000 Å、XP・DESIの傾きは約0.0072・0.0068、direct SDSS row9399は未再較正 |
| 2586182156053386240 | MWDD SDSS row978とdirect SDSS row8781は未再較正、DESIとXPはSDSS測光を使用 |
| 1025033665052512000 | MWDD SDSS row1953はPS1アンカーで傾き約0.2260 mag/1000 Å、XPはSDSSアンカー、direct SDSS row9079は未再較正 |

これは既存の[全レコード表](../record_review.csv.gz)のメタデータです。別観測と同じ観測の別表現を同一視せず、較正経路が異なる曲線の形状差を固有変光や化学組成の違いに直結させません。倍率・傾きを都合よく変更してグラフを一致させる処理は、この位置照合にはありません。

4対象はいずれも今回の公式Gaia応答で `phot_variable_flag=NOT_AVAILABLE`、最良クラスは欠測でした。これは一定光度の証明ではありません。

## 再生成とオフライン検証

```bash
# 再取得時のみネットワークが必要
python research/outlier_followup/association_diagnostics.py fetch

# 元の survey cache がある作業環境でヘッダーと位置を再生成
python research/outlier_followup/association_diagnostics.py analyze

# 保存した原FITS圧縮コピーとGaia原CSVだけで再検証
python scripts/verify_research_followup.py --group native
```

検証器は圧縮前の原FITSのSHA256を照合し、抽出済みの座標欄だけを信じず、原ヘッダーから再度距離を計算します。全サーベイの大きな作業キャッシュは不要です。
