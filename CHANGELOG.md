# Changelog

This log records changes to the research, its interpretation and the reproducible package. A software or documentation release is not a peer-review or discovery-certification milestone.

## 0.2.0 — 2026-10-18

### Corrected flux interpretation and research status

- Corrected a substantive input-unit error: comparison with original SDSS pixels identifies 149 MWDD-hosted SDSS records as proportional to Fnu and 504 as Flambda. Another 1,579 remain unresolved; they are retained for audit and excluded from the current physical-colour screen. Evidence requires matching wavelength grids and the expected wavelength-squared transformation, not a continuum-slope guess.
- Recalculated all 3,629 SDSS records. The corrected screen has **7,473 eligible records, 395 strong-outlier records and 308 strong-outlier entity keys**. The earlier 9,023 eligible records and 337 strong-outlier entity keys describe the historical audit, not the current sample. Entity keys are catalogue identifiers, not a guarantee that every physical star has been uniquely resolved.
- **Withdrew independent SDSS colour corroboration for WD J1323−0129.** Its archived SDSS flux convention is unresolved; the target remains a DESI colour candidate and has no available native Gaia XP spectrum in this retrieval. It was not one of the 149 positively identified Fnu records.
- Preserved the version 0.1 headline tables, original report bodies and notebook numerical outputs. Prominent banners distinguish those snapshots from the current [research report](research/README.md), [corrected screen](research/precision/flux_units/corrected_colour_plane.png) and [initial-27 follow-up table](research/candidate27_followup.md). Small changes in the current four DESI estimates reflect standardized photometric inputs and uncertainty definitions, not measured stellar evolution.

### Additional work executed

- Audited all 9,902 original records and 2,344 review entity keys; checked 4,355 recovered raw-file hashes and reproduced 4,353 historical colour calculations. Recorded two pre-existing invalid-XYZ cases. Inspected all 337 historical strong-outlier objects across 22 spectrum contact sheets, retaining object-level notes and raw evidence.
- Reconstructed native Gaia XP coefficients for 26 of the initial 27 candidates, preserving full and recommended truncated bases, their shared provenance and formal coefficient-noise intervals. Added 12 photometric anchors and recalibrated 25 DESI candidates; 10 of 25 have absolute held-out z residuals above 0.05 mag, a diagnostic rather than a complete significance test.
- Calculated exact-gri-preserving calibration perturbations, numerical integration and wavelength-mask sensitivity, with explicit limits on interpreting these stress tests as real error distributions. Integrated the initial 27 into one follow-up table without pooling a discovery probability or declaring confirmed candidates.
- Retrieved seven additional public DESI exposures for four targets. Three targets have six usable additional-night colour measurements; the additional J1329+0033 exposure lacks usable Z-arm pixels for a full colour estimate. Analysed 2,473 ZTF measurements and 4,646 control measurements without establishing new intrinsic variability. Retained the J1323−0129 positional outlier in the raw data and documented its epoch-corrected rejection.
- Examined Gaia neighbours and source quality, prior atmosphere analyses, and PEWDD source joins. Three suspicious PEWDD cases were checked against original papers; the broader 236-row designation-coordinate discrepancy group remains quarantined, not collectively declared to contain incorrect Gaia identifiers.
- Added bilingual research reports, a research-extension notebook, auditable figures and tables, test coverage for flux interpretation and numerical invariants, and an offline extension verifier. The core test command now discovers all `test_*.py` files; the extension verifier complements the preserved compact-result verifier.

### Scientific status

This remains an unreviewed, ChatGPT-assisted investigation led by project initiator and maintainer Shota Moriwaki. The most concrete new result is a verified correction and its consequences for candidate evidence. Formal and conditional intervals omit material systematic effects; selection bias and global false-discovery rates are not yet quantified. The reports separate work actually executed from proposed atmospheric fits and future observing tests.

## 0.1.0 — 2026-10-18 (historical snapshot)

### Initial research package

- Reported WD J0913+4434 and WD J0429−0354 as additional pale yellow-green colour candidates, alongside pink WD J1329+0033 and unusually yellow WD J1323−0129. The stars themselves and their atmospheric classifications are prior work.
- Preserved a scan of 9,902 public spectrum records: 8,505 MWDD records and 1,397 direct SDSS observations, with duplicates and deliberate Q/Z selection documented.
- Added representative DESI+Pan-STARRS chromaticities, 6,000-draw conditional uncertainty intervals, calibration alternatives and sensitivity checks.
- Reconstructed the original Gaia XP coefficients for the two green candidates and propagated their supplied covariance. Retained both full and recommended truncated basis results and the limits on a definite green colour label.
- Added 54 DA/DB/DC controls, known-colour comparisons, source-quality checks and documented rejected cases, including the contaminated LP616−53 system.
- Compared candidate identities with all 236 unique names in Hollands et al. (2026) and the 231-object Hollands et al. (2017) parent catalogue. Recorded bounded prior-literature evidence without asserting global priority.
- Added the official Swan et al. (2026) candidate classifications and contamination estimates, with the Gaussian-model and Na-feature follow-up qualifications.
- Provided English and Japanese READMEs, reports and executed notebooks, bibliographic records, acknowledgments, provenance and data-reuse documentation.
- Added an offline reproduction verifier. `scripts/verify_reproduction.py --with-controls` recalculates the principal DESI values and all 54 raw SDSS controls, and verifies the included Gaia mean/covariance products.
- Preserved the repository's Apache-2.0 licence for original code, specified CC BY 4.0 for original prose, and retained source-specific conditions for third-party material.

### Verification portability correction

- Replaced bitwise equality only for SDSS wavelengths derived as `10**loglam` with a maximum allowance of two float64 representable steps (ULPs). Different CPU dispatch paths produced a measured difference of one ULP, at most approximately `1.82e-12` Å. The verifier now reports the observed rounding differences and rejects larger discrepancies.
- Kept raw-file SHA-256 checks and the exact comparisons for flux, inverse variance and masks. The stored data, colour calculations, headline measurements and executed notebooks are unchanged.

### Scientific status of this version

This is an exploratory, unreviewed public-data analysis with ChatGPT assistance. Per-source intervals exclude material systematic effects and are not global discovery significance. Colour patches are standard-observer display calculations, not photographs. The complete ranking is a follow-up list, not confirmed discoveries.

## 日本語

### 0.2.0 — 2026年10月18日

**入力フラックスの単位解釈に実際の誤りを確認し、修正しました。** 原SDSSの同一波長画素との比較から、MWDD経由SDSSの149記録をFnu、504記録をFlambdaと確認しました。残る1,579記録は未確定として保存し、現在の物理的な色の判定から除外しています。見た目の傾きだけでは分類せず、波長グリッドの一致と波長の2乗に対応する変換を確認しています。

SDSS全3,629記録を再計算し、修正後は**適格7,473記録、強外れ395記録・308天体キー**になりました。旧9,023適格記録・337強外れ天体キーは過去の監査対象数です。天体キーはカタログ上の識別単位であり、全ての実天体の同定が完全に解決したことを意味しません。**WD J1323−0129はSDSSの単位を確定できないため、独立したSDSSによる色の裏付けを撤回しました。** DESIの色候補としては残りますが、今回の取得では元Gaia XPがありません。このSDSS記録をFnu確定149件に含めてはいません。

元の9,902記録を台帳化し、要確認2,344天体キーを整理しました。回収した原ファイル4,355件のハッシュを照合し、4,353件の旧色計算を再現、既存のXYZ不正2件を記録しました。旧強外れ337天体は22枚のスペクトル一覧を全て目視確認し、個別の注意点を残しています。初期27候補のうち26天体について元Gaia XP共分散を伝播し、DESIは新たな測光アンカー12件を加えて25天体を再校正しました。フィットに使わないzバンドの残差は25件中10件で絶対値0.05等級を超え、これは追加の校正診断として記録しています。

g・r・iを厳密に保存する校正変形、積分・波長マスクへの感度を実際に計算しました。公開DESIの追加7露出・4対象を取得し、3対象の6夜分の有効な色を比較しました。J1329+0033の追加露出はZアームの有効画素がなく、全可視域の独立した色を主張していません。ZTFの対象2,473測定と対照4,646測定から新たな固有変光を確立してはいません。J1323−0129の外れ測光点は固有運動を考慮した位置基準で除外し、生データと画像を保持しました。Gaiaの近傍・品質、先行大気解析、PEWDDの結合整合性も検証しました。PEWDDの疑わしい3例は原論文で確認しましたが、広い座標不一致群236行を一律に誤IDと断定してはいません。

日英の[現行研究報告](research/README.ja.md)、追加ノートブック、修正済み図、初期27候補の総合表、単位解釈・数値不変条件のテスト、追加研究のオフライン検証を追加しました。旧v0.1の数値ファイル、レポート本文、元ノートブックの数値出力は保存し、冒頭に保存版の表示を加えました。現在の代表4天体の小さな数値差は測光入力と誤差定義を統一した結果であり、星の変化の検出ではありません。

研究の発起人・管理者はShota Moriwakiです。本版はChatGPTを利用した未査読研究であり、発見の確定や完全な誤差評価を意味しません。新たに実行した検証と、今後必要な大気モデルのフィット・観測の提案を分けています。選択バイアスと全探索の偽発見率は未評価です。

### 0.1.0 — 2026年10月18日（保存版）

公開データ9,902スペクトル記録の再解析をまとめた初版です。追加の淡い黄緑色候補2天体、ピンク色候補1天体、通常の黒体から外れた黄色候補1天体を報告し、DESIの条件付き区間、Gaia共分散、対照54観測、混入推定、先行研究の照合を記録しました。天体自体や既存の大気の物理機構を新発見として扱ってはいません。

英語・日本語の説明と実行済みノートブック、再現検証コード、出典・謝辞・利用条件を追加しました。独自コードは既存のApache-2.0を保持し、独自の解説文はCC BY 4.0、第三者資料は元の条件を保持します。本版はChatGPTを用いた探索的な研究ノートであり、査読や世界的優先権の確認が完了したことを意味しません。

再現検証の環境依存性を修正しました。SDSSの対数波長から `10**loglam` で復元する波長だけに、float64で隣り合う表現可能な数値の間隔を単位として最大2 ULPの丸め差を認めます。CPUの計算経路を変えた比較で観測された差は最大1 ULP、約 `1.82e-12` Åでした。検証時に実際の差を表示し、許容幅を超える差は失敗として扱います。元ファイルのSHA-256とフラックス・逆分散・マスクの完全一致確認は維持し、保存データ、色計算、代表値、実行済みノートブックは変更していません。
