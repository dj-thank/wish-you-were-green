# Changelog

This log records changes to the research, its interpretation and the reproducible package. A software or documentation release is not a peer-review or discovery-certification milestone.

## 0.1.0 — 2026-10-18

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

### 0.1.0 — 2026年10月18日

公開データ9,902スペクトル記録の再解析をまとめた初版です。追加の淡い黄緑色候補2天体、ピンク色候補1天体、通常の黒体から外れた黄色候補1天体を報告し、DESIの条件付き区間、Gaia共分散、対照54観測、混入推定、先行研究の照合を記録しました。天体自体や既存の大気の物理機構を新発見として扱ってはいません。

英語・日本語の説明と実行済みノートブック、再現検証コード、出典・謝辞・利用条件を追加しました。独自コードは既存のApache-2.0を保持し、独自の解説文はCC BY 4.0、第三者資料は元の条件を保持します。本版はChatGPTを用いた探索的な研究ノートであり、査読や世界的優先権の確認が完了したことを意味しません。

再現検証の環境依存性を修正しました。SDSSの対数波長から `10**loglam` で復元する波長だけに、float64で隣り合う表現可能な数値の間隔を単位として最大2 ULPの丸め差を認めます。CPUの計算経路を変えた比較で観測された差は最大1 ULP、約 `1.82e-12` Åでした。検証時に実際の差を表示し、許容幅を超える差は失敗として扱います。元ファイルのSHA-256とフラックス・逆分散・マスクの完全一致確認は維持し、保存データ、色計算、代表値、実行済みノートブックは変更していません。
