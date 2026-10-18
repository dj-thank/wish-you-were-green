# Data availability, provenance and reuse / データの所在・出典・利用条件

Policy and source checks: **2026-10-18**. [English](#english) · [日本語](#日本語) · [Official sources](#official-sources--公式資料)

## English

### What this project makes reproducible

This project reanalyses existing public white-dwarf observations. It does not
own the original observations, survey catalogues, atmosphere models, or CIE
reference data. The repository's licence notices apply to the original
contributions they identify: [Apache License 2.0](../LICENSE) for original
software and CC BY 4.0 for original writing do **not** relicense third-party data,
figures, publication text, or software dependencies. No copyright assignment
from the original providers is asserted. The detailed scope is in
[LICENSES/README.md](../LICENSES/README.md).

The analysis on 2026-10-18 used the following material. Counts are observations
or catalogue identifiers as specified, not numbers of new stars.

| Input | Recorded scope | Provenance record |
|---|---|---|
| Montreal White Dwarf Database (MWDD) | Catalogue snapshot: 163,279 rows; selected 5,548 stars, primarily Q/Z spectral types plus comparison objects; 8,505 successfully parsed spectra | [Acquisition summary](../mwdd/acquisition_summary.json), [manifest](../mwdd/manifest_enriched.json.gz) and [source checksums](../mwdd/source_checksums.csv.gz) |
| Direct SDSS archive downloads | 1,397 FITS spectra: 1,343 Q/Z selections and 54 DA/DB/DC controls; 1,383 catalogue identifiers, selected using Kepler et al. (2019) [K1](#official-sources--公式資料) | [SDSS manifest with photometry](../sdss/manifest_with_photometry.json.gz) |
| Combined screen | 9,902 spectrum records, of which 9,023 passed the defined format and wavelength conditions; records can share an observation or an object | [Screen summary](../results/screen_summary.json) and [full screening results](../results/all_spectra_screen.csv.gz) |
| Official Gaia DR3 XP follow-up | Original coefficients, formal errors and correlations for source IDs `818833831355548928` and `3204436719718449280` | [Source manifest](../mwdd/gaia_validation/source_manifest.json) and [reconstruction audit](../mwdd/gaia_validation/README.md) |
| Literature and catalogue comparisons | Hollands et al. (2026) comparison tables, related published catalogues, and selected rows from Swan et al. (2026) | Novelty evidence, extraction scripts and source URL/hash records |
| Colour reference | Official CIE 1931 2° colour-matching functions at 1 nm intervals | [CIE CSV](../reference/CIE_xyz_1931_2deg.csv), its [original metadata](../reference/CIE_xyz_1931_2deg.csv_metadata.json) and [download record](../reference/reference_downloads.json) |

The 8,505 MWDD records contain 8,502 numerically distinct wavelength/flux pairs.
The directly downloaded SDSS FITS collection can also overlap MWDD's SDSS
exports. A second filename is not evidence of an independent observation.

### Current Git package and full source cache

The current Git tree is approximately **80 MB before Git compression** and
includes the selected inputs needed to inspect and recompute the principal
results. These files are in the repository itself; **there is no separate
release asset to download** for this package.

| Included location | Contents and purpose |
|---|---|
| Code, documentation and figures | Original analysis scripts, bilingual reports and notebooks, calculation figures, provenance/audit records, and attributed reference material |
| `mwdd/spectra/` and `mwdd/parsed/` | **25 selected original CSV exports and 25 parsed arrays** for candidates, comparison cases and baselines; their identified origins are 10 DESI, 9 Gaia XP and 6 SDSS |
| `sdss/raw/` and `sdss/arrays/` | **54 original FITS control observations and 54 parsed arrays**, comprising 18 each of DA, DB and DC |
| `mwdd/gaia_validation/` | Approximately **21 MB**, including the original two-source coefficient products, full/truncated reconstructions at 1 nm, covariance arrays, source hashes and executable audits |
| `results/`, `mwdd/` and `sdss/` metadata | Candidate calculations and gzip-compressed full screening tables, input manifests, source checksums and quality records; `.csv.gz` and `.json.gz` are the actual bundled filenames |

The complete original spectrum cache is about 2 GB; the MWDD spectrum files
alone total 1,676,766,563 bytes. It is intentionally not copied wholesale into
Git. The full MWDD compilation, full Swan catalogue archives, cached journal or
arXiv HTML/PDFs, and bulk model-plot archives are not part of the compact
package. The checked-out Git tree is authoritative about which selected files
are included. A reference to a cache filename in an audit does not imply
redistribution of that entire source collection.

Use the [frozen-spectrum downloader](../download_frozen_spectra.py), the
recorded manifests and the [reproducibility guide](reproducibility.en.md) to
retrieve the missing full-screen inputs. The original acquisition scripts
also preserve how the selection was constructed. Gzip compression of metadata
does not change the source-file hashes recorded inside those manifests.

For every redistributed or reacquired input, retain its original URL, source
identifier, survey/release or literature reference, byte count and SHA-256.
Acquisition timestamps are recorded where available; a missing timestamp is
not reconstructed from an unrelated file modification time. Downloaded bytes
are kept separate from parsed arrays, calibrated spectra and analysis results.
These derivatives record the operations applied to them. Raw downloads are
not silently normalized or substituted with a newer archive version.

Checksums establish byte identity with the recorded input; they do not certify
scientific correctness, licensing, or future availability. An archive may
update or remove a URL. If a re-download differs, retain it as a new input
version and report the difference instead of treating it as the old snapshot.

### Source-specific reuse status

Public accessibility and permission to apply a new licence are different
questions. The following records what was verified from the provider's own
material; it is not a new licence grant by this project.

| Material | Verified provider policy or status | Treatment here |
|---|---|---|
| **Gaia DR3 data** | The Gaia-specific licence page states **CC BY-NC 3.0 IGO**. ESA's archive terms direct commercial users to seek authorization and require mission-specific credit. [G1–G3](#official-sources--公式資料) | Original coefficient/photometry files and Gaia-derived spectral/covariance arrays retain the Gaia terms. Credit **ESA/Gaia/DPAC**. The repository does not grant commercial data reuse or substitute the generic ESA media licence. |
| **DESI public data** | **CC BY 4.0**. The official page asks for the relevant release paper, disclosure of changes, and its specified acknowledgments. [D1–D2](#official-sources--公式資料) | Preserve DESI attribution and the licence link. Identify MWDD/Warwick conversion, masking, interpolation and photometric recalibration separately from the original measurements. Credit DESI DR1 and the applicable spectrum provider. |
| **SDSS public-release data** | The SDSS-IV data-use policy describes public-release data as **public domain**. Its website images have a separate attribution policy. [S1–S2](#official-sources--公式資料) | Identify the actual archive release from each manifest, including DR17 FITS used here; cite the release, survey and instrument as appropriate. A spectrum's data status is not a blanket licence for unrelated website photographs. |
| **CIE 1931 reference CSV** | The exact dataset metadata specifies **CC BY-SA 4.0**. [C1–C3](#official-sources--公式資料) | Keep CIE's attribution, DOI, metadata and licence. An adapted CIE table must retain the applicable ShareAlike terms and describe changes; it is not covered by the project's original-code/text licences. |
| **Pan-STARRS1 photometry via MAST** | MAST documents public-data reuse and collection-specific exceptions, and publishes PS1 acknowledgment and citation instructions. [P1–P3](#official-sources--公式資料) | Retain the PS1/MAST origin, query/result provenance and applicable terms. No new CC licence is assigned to the source photometry, and no universal licence is inferred for every MAST collection. |
| **CDS/VizieR and SIMBAD records** | CDS requires source/service credit and observance of dataset-specific terms. VizieR explicitly distinguishes scientific use from origin-dependent commercial rights. [V1–V3](#official-sources--公式資料) | Cite the catalogue's authors and publication as well as CDS/VizieR or CDS/SIMBAD. Retain concise identification and audit evidence; do not claim ownership of the complete CDS compilation or metadata system. |
| **MWDD compilation and contributed spectra** | The inspected description explains its paper-by-paper compilation and identifies contributing sources; the inspected pages do not establish one blanket redistribution licence for every component. [M1–M3](#official-sources--公式資料) | Credit MWDD and each underlying survey/paper. Retain URLs, hashes and selection/extraction code. Selected spectra with identified survey provenance keep those survey terms; an unidentified component is not relabelled Apache-2.0 or CC BY merely because MWDD serves it. |
| **Swan/Warwick catalogue and model products** | The Warwick repository provides public downloads and requests citation of Swan et al. (2026). It states that its spectral wavelength/flux/variance/mask columns come from DESI. It does not establish a single separate licence for every author-created table and model plot. [W1–W2](#official-sources--公式資料) | DESI-origin spectral values retain DESI attribution/terms. Cite Swan for the repository, classification and contamination analysis. Keep source URLs/hashes and selected extracted audit values; do not blanket-relicense full author-created catalogues or plots. |
| **Published papers, model images and dependencies** | Rights depend on the particular publication, archive record or software licence. | Link to the original paper/DOI or package; preserve applicable notices for any material actually included. Open access alone does not establish a uniform redistribution licence. |

The practical boundary is narrow: the original code and explanatory writing
can be shared under their stated licences while each input keeps its original
terms. For source components without an established redistribution licence,
the reproducible alternative is a URL, checksum and extraction script rather
than a wholesale copy. This does not imply that scientific reading or reuse
of a publicly served dataset is prohibited.

**CIE attribution:** CIE (2019), *Colour-matching functions of CIE 1931 standard
colorimetric observer*, DOI [10.25039/CIE.DS.xvudnb9b](https://doi.org/10.25039/CIE.DS.xvudnb9b).
The official CSV is unchanged; SHA-256
`fa663e3535a7e0763a745993a1f0a192eb0275ac46ad2d1befd7626841e713c1`.
Computational resampling and integration are documented in the code. The
official metadata's MD5 is `17cca777db64b17170f06f67ce9d3ab7`.

### Credits and publication use

The observations and their processing are credited to **DESI**, **ESA/Gaia/DPAC**,
**SDSS**, and **Pan-STARRS1/MAST**. MWDD, maintained by Patrick Dufour and Simon
Blouin, and **CDS/SIMBAD/VizieR** supplied catalogue organization and access.
Kepler et al. (2019) supplied the catalogue used for the independent SDSS
selection. The original catalogue and atmosphere-model authors retain credit for their
classifications, temperatures, abundances, models and contamination estimates.
The human-colour comparison is credited to **Hollands et al. (2026)**; the DESI
white-dwarf catalogue comparison to **Swan et al. (2026)**; XP calibration uses
**GaiaXPy**; the standard observer data are credited to **CIE**.

The specified provider blocks and relevant release references are included in
[ACKNOWLEDGMENTS.md](../ACKNOWLEDGMENTS.md). Consult the current instructions
when turning these results into a subsequent scholarly publication: [DESI][D1],
[Gaia][G3], [SDSS][S2], [PS1/MAST][P2], and [CDS][V3]. Preserve these credit
instructions when passing the data to others. Acknowledging the original
funders does not imply that they funded, reviewed or endorsed this reanalysis.
See [Research integrity](research-integrity.md) for the scope of the scientific
claims and AI involvement.

## 日本語

### 再現できる内容と、元データの権利

本研究は既存の公開観測を再解析したものです。原観測、サーベイのカタログ、
大気モデル、CIEの標準データを本プロジェクトの所有物として扱いません。
独自コードに対するApache License 2.0表記、独自の解説文に対するCC BY 4.0表記は、第三者の
データ、図、論文本文、依存ソフトウェアまで再ライセンスするものではありません。
原提供者から著作権の譲渡を受けたとも主張していません。
詳細な範囲は[ライセンス案内](../LICENSES/README.md)に記載します。

2026年10月18日の解析では、MWDDの163,279行の公開カタログから主にQ/Z型の
5,548天体を選び、8,505スペクトルを取得しました。さらにSDSSから1,397本の
FITSを直接取得し、合計9,902スペクトル記録を走査しました。形式・波長範囲の
条件を満たした記録は9,023です。これらは新発見の天体数ではありません。
MWDD内の数値的に異なるスペクトルは8,502本で、SDSS直接取得分とMWDDにも
同じ観測が含まれ得ます。詳細は上表のマニフェストと全走査結果に対応します。

現在のGitツリーはGit圧縮前で約80 MBです。コード、日英の解説・ノートブック、
主要な数値結果、出典・監査記録、利用条件を明記した参照データに加え、
MWDDの選択済み原CSV25本と解析配列25本、SDSSの対照FITS54本と配列54本を
同梱します。MWDDの25本はDESI 10本、Gaia XP 9本、SDSS 6本です。
Gaiaの元係数・1 nmの再構成・共分散配列・監査コードも約21 MBを同梱しています。
これらはGitに含まれ、別のリリース資産をダウンロードする必要はありません。
全走査表や大きなマニフェストは、実際の同梱名である`.csv.gz`／`.json.gz`を
使います。上の表から各ファイルへ移動できます。

原スペクトルの全キャッシュは約2 GBで、MWDD分だけで1,676,766,563バイトです。
全MWDDカタログ、Swanの全アーカイブ、取得した論文HTML/PDF、モデル図の
一括アーカイブはGitに含めていません。元の公開URL、SHA-256、
[凍結標本の取得コード](../download_frozen_spectra.py)と抽出コードを使って
再取得できます。監査にキャッシュの名前が
登場しても、元コレクション全体の再配布を意味しません。

取得した原バイト列と、数値配列への変換・測光校正・色計算の結果は分けて記録
します。取得時点で流束を勝手に規格化したり、更新されたファイルを古い版として
置き換えたりしません。元URL、識別子、サーベイ／リリースまたは論文、サイズ、
SHA-256を保持し、取得時刻がある場合はそれも残します。ハッシュは同一性の
検査であり、科学的正しさ、利用許諾、将来も取得できることの証明ではありません。
元サイトの内容が変わった場合は、新しい入力版として扱います。

### 出典ごとの利用条件

| 出典 | 本研究で確認した条件と扱い |
|---|---|
| **Gaia DR3** | Gaia専用の公式ライセンスは **CC BY-NC 3.0 IGO** です。係数・測光の原ファイルとGaia由来のスペクトル／共分散配列には元の条件を残し、**ESA/Gaia/DPAC**を明記します。営利利用についてはESAの案内に従います。本リポジトリから営利利用の許諾を与えたり、一般のESA広報画像のライセンスに置き換えたりしません。[G1–G3](#official-sources--公式資料) |
| **DESI** | 公開データは **CC BY 4.0**。データリリース論文、変更点、指定謝辞の案内を保持します。MWDD／Warwickでの形式変換や、本研究でのマスク・補間・測光校正は原測定と区別します。[D1–D2](#official-sources--公式資料) |
| **SDSS** | SDSS-IVの公式方針では公開リリースのデータをパブリックドメインとしています。使用したDR17等の版と適切な論文を明記します。ウェブサイトの写真には別の条件があり、分光データと一括して扱いません。[S1–S2](#official-sources--公式資料) |
| **CIE** | 取得した等色関数の公式メタデータは **CC BY-SA 4.0**。CIEの出典、DOI、ライセンス、メタデータを残します。改変したCIE表にも適用される継承条件と変更点を明記し、独自コード／解説のライセンスで上書きしません。[C1–C3](#official-sources--公式資料) |
| **Pan-STARRS1／MAST** | 公開測光の出典、取得記録、PS1の謝辞・引用案内を保持します。MASTにはコレクション別の条件があるため、全MAST資料へ一律のライセンスを推定しません。[P1–P3](#official-sources--公式資料) |
| **CDS／VizieR／SIMBAD** | サービスだけでなく原カタログの著者・論文を引用し、データセット別の条件を守ります。VizieRは科学利用と、出典によって異なる営利利用条件を区別しています。[V1–V3](#official-sources--公式資料) |
| **MWDD** | 各論文・サーベイからの編集物です。確認したページでは全構成要素に共通する一括再配布ライセンスを確定できませんでした。MWDDと原提供者を引用し、公開URL・ハッシュ・抽出手順を保持します。出典が確認できた選択済みスペクトルは、その原サーベイの条件で扱います。[M1–M3](#official-sources--公式資料) |
| **Swan／Warwickの資料** | 公開リポジトリはSwan et al. (2026)の引用を求め、分光の主要列がDESI由来と説明しています。一方、著者が作成した全表・全モデル図に共通する別の許諾までは確認していません。原URL・ハッシュ・候補行の抽出結果を残し、全アーカイブへDESIのライセンスを機械的に適用しません。[W1–W2](#official-sources--公式資料) |

原資料の再配布条件を確定していない場合も、研究全体を非公開にする必要がある
という意味ではありません。独自のコード・解説・計算結果を公開し、該当する
原資料はURL、ハッシュ、抽出コードで示すことで、権利の範囲を越えずに追跡可能な
構成にします。「公開されている」ことと「任意のライセンスを付け直せる」ことは
同じではありません。

CIEの原CSVは変更しておらず、DOIは
[10.25039/CIE.DS.xvudnb9b](https://doi.org/10.25039/CIE.DS.xvudnb9b)です。
公式SHA-256とMD5は英語節に記載しました。計算時の補間・積分はコードに残しています。

観測はDESI、ESA/Gaia/DPAC、SDSS、Pan-STARRS1/MASTに、カタログの整理と
提供はMWDDおよびCDSに、分類・温度・組成・大気モデル・混入推定は原著者に
帰属します。MWDDの維持者Patrick Dufour、Simon Blouin、比較研究の
Hollands et al. (2026)、DESI白色矮星カタログのSwan et al. (2026)、
GaiaXPyの開発者、CIEにも謝意を表します。指定謝辞とリリースの引用案内は
[ACKNOWLEDGMENTS.md](../ACKNOWLEDGMENTS.md)に収めています。学術論文等へ発展させる際は、
[DESI][D1]、[Gaia][G3]、[SDSS][S2]、[PS1/MAST][P2]、[CDS][V3]の
最新の指定謝辞と、使用したリリース・装置・カタログの論文を反映してください。
原サーベイの資金提供者を謝辞に挙げることは、本再解析への資金提供、査読、
承認を意味しません。科学的主張とAIの関与は[研究の誠実性](research-integrity.md)に記載します。

## Official sources / 公式資料

These links identify provider policies and source records inspected for this
document. The original policies control their respective material; this
summary does not replace them. / 以下は確認した公式方針と原資料です。各資料には
提供元の原条件が適用され、本要約がそれに代わるものではありません。

- **G1 — Gaia data licence:** <https://www.cosmos.esa.int/web/gaia-users/license>
- **G2 — ESA archive terms:** <https://www.cosmos.esa.int/web/esdc/terms-and-conditions>
- **G3 — Gaia credits and release citations:** <https://www.cosmos.esa.int/web/gaia-users/credits>
- **D1 — DESI data licence and acknowledgments:** <https://data.desi.lbl.gov/doc/acknowledgments/>
- **D2 — DESI DR1:** <https://data.desi.lbl.gov/doc/releases/dr1/>
- **S1 — SDSS-IV data-use policy:** <https://www.sdss4.org/collaboration/#data-use-policy>
- **S2 — Citing SDSS:** <https://www.sdss4.org/collaboration/citing-sdss/>
- **K1 — Kepler et al. (2019) catalogue:** <https://cdsarc.cds.unistra.fr/ftp/J/MNRAS/486/2169/>; dataset DOI <https://doi.org/10.26093/cds/vizier.74862169>
- **C1 — CIE dataset:** <https://cie.co.at/datatable/cie-1931-colour-matching-functions-2-degree-observer>
- **C2 — Original CIE metadata, including licence:** <https://files.cie.co.at/Publications-datasets/CIE_xyz_1931_2deg.csv_metadata.json>
- **C3 — CIE data licence:** <https://creativecommons.org/licenses/by-sa/4.0/>
- **P1 — MAST data-use policy:** <https://archive.stsci.edu/publishing/data-use>
- **P2 — PS1/MAST acknowledgments and citations:** <https://archive.stsci.edu/publishing/mission-acknowledgements>
- **P3 — Pan-STARRS catalogue API:** <https://catalogs.mast.stsci.edu/docs/panstarrs.html>
- **V1 — VizieR usage rules:** <https://cds.unistra.fr/vizier-org/licences_vizier.html>
- **V2 — CDS terms:** <https://cds.unistra.fr/legals/>
- **V3 — CDS acknowledgments:** <https://cds.unistra.fr/help/acknowledgement/>
- **M1 — MWDD:** <https://www.montrealwhitedwarfdatabase.org/>
- **M2 — MWDD description and provenance:** <https://www.montrealwhitedwarfdatabase.org/description.html>
- **M3 — MWDD acknowledgments:** <https://www.montrealwhitedwarfdatabase.org/aknowledgements.html>
- **W1 — Warwick White Dwarf Repository:** <https://cygnus.astro.warwick.ac.uk/phsdaj/WhiteDwarfs/>
- **W2 — Swan et al. (2026):** <https://arxiv.org/html/2609.04314v1>

[D1]: https://data.desi.lbl.gov/doc/acknowledgments/
[G3]: https://www.cosmos.esa.int/web/gaia-users/credits
[S2]: https://www.sdss4.org/collaboration/citing-sdss/
[P2]: https://archive.stsci.edu/publishing/mission-acknowledgements
[V3]: https://cds.unistra.fr/help/acknowledgement/
