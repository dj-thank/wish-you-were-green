# Contributing

Corrections, reproducibility reports and independently documented follow-up are welcome. English or Japanese issues and pull requests are both suitable. The project is maintained by Shota Moriwaki at [dj-thank/pale-yellow-green-white-dwarf-candidate](https://github.com/dj-thank/pale-yellow-green-white-dwarf-candidate).

The scientific goal is to improve a reproducible colour analysis of known stars. A successful software check does not establish an astronomical discovery, and an unusual RGB value is not sufficient evidence for an intrinsic stellar colour.

## Report a numerical or reproduction issue

Include the version or commit, Python version and environment, exact command, relevant error output, and the file or candidate involved. Describe the expected result and how the observed result differs. For changes involving source data, preserve its full identifier, URL and checksum so another person can distinguish an input change from a calculation change.

Use the recorded Python 3.12 core environment and the substantive verification command:

```bash
python3.12 -m venv .venv-colour
.venv-colour/bin/python -m pip install -r requirements-core.txt
.venv-colour/bin/python scripts/verify_reproduction.py --with-controls
```

The verification uses included inputs without downloading survey data. It recalculates the four DESI representative colours and 54 raw SDSS controls and validates the retained Gaia mean/covariance products. It does not rebuild GaiaXPy products from basis functions or rerun the full survey. See [the reproduction guide](docs/reproducibility.en.md) for those boundaries and tolerances.

## Propose a scientific correction or candidate

Provide evidence that makes the claim reviewable:

- Exact source identity, aliases and coordinate epoch. Preserve Gaia source IDs as strings or exact integers.
- Public spectrum URL, survey and observation identity, wavelength units, flux-density convention, uncertainty or covariance information, and original-file hash.
- Calibration and processing details, including photometric anchors, masks, missing wavelength coverage and treatment of noisy negative flux.
- Both chromaticity and display convention. Distinguish distance from the Planckian locus, RGB channel ordering and the proposed human colour name.
- Checks for neighbouring light, instrumental artefacts, duplicates and prior literature. Explain whether another spectrum is a different observation or the same observation in another archive.
- The uncertainty model and what it leaves out. A conditional per-source interval is not a global discovery probability after searching many records.

Prior classifications, temperature or abundance fits must be credited to their source. An absence from one named-object table or a keyword search does not establish worldwide priority. Independent spectroscopy, a better relative flux calibration, or a documented prior colour measurement can materially improve this study even when it weakens a candidate.

## Make a code or documentation change

Explain the concrete problem, the change, its effect on the results and how it was checked. For changes to scientific calculations, run the reproduction verifier and report any changed values or assumptions. A deliberate result change needs updated provenance and interpretation; do not loosen tolerances or rewrite a frozen baseline merely to make a check pass. Retain the previous input identity when an upstream archive has changed.

Documentation-only corrections need appropriate checks of links, numbers and terminology; they do not require rerunning unrelated calculations. Keep English and Japanese summaries aligned when a scientific conclusion changes. Preserve the distinction between original observations, parsed derivatives, recalibrated spectra and this project's calculations.

If AI tools substantially assist a contribution, briefly describe their role and the checks performed. Assistance is compatible with contribution, but it is not an independent scientific verification. Do not describe an automated review as peer review or imply approval by the original survey authors.

## Attribution and licensing

Original code contributions are made under the project's existing **Apache-2.0** [LICENSE](LICENSE). Original explanatory prose is provided under **CC BY 4.0**. Third-party data, figures, reference material and dependencies keep their own conditions; no contributor should assign the project's licence to material owned by a survey or another author.

For added material, retain its source, attribution, applicable terms and a record of changes. The unchanged CIE data retain CC BY-SA 4.0. Consult [LICENSES/README.md](LICENSES/README.md), [data availability](docs/data-availability.md), [ACKNOWLEDGMENTS.md](ACKNOWLEDGMENTS.md) and [references.bib](docs/references.bib). A public URL or successful checksum alone is not a blanket redistribution licence.

## 日本語での貢献

日本語でのIssueやPull Requestも歓迎します。再現できない場合は、使用した版またはコミット、Pythonと環境、実行コマンド、エラー、対象ファイルや天体を示してください。科学計算に影響する変更では、上記の `--with-controls` 付き検証を実行し、どの値・仮定・解釈が変わったかを説明してください。文章だけの修正では、関連するリンクや数値の確認で十分です。

候補や先行研究の追加には、正確な識別子と座標の時点、原スペクトルのURL・ハッシュ・単位、誤差、校正、近傍天体、別観測との比較、文献の根拠を添えてください。Duvが正であること、RGBのGが最大であること、人間が緑色と呼ぶことは同じではありません。多くの記録を調べた後の条件付き区間を、そのまま世界初の発見の確率として扱わないでください。

既存の分類・モデル・観測は原著者に帰属します。AIを大きく利用した場合は、その役割と実施した確認を明記してください。独自コードはApache-2.0、独自の解説はCC BY 4.0、第三者の資料はそれぞれの元の条件で扱います。科学的結論を修正するときは英語・日本語の要約も揃えてください。
