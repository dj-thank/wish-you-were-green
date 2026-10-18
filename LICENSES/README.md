# Licence scope and third-party material / ライセンスの適用範囲

Provider-policy checks: **2026-10-18**. These notices distinguish the project's
original contributions from the data and reference material used to produce
them. They do not assert ownership of survey observations or grant rights on
behalf of their providers.

## Original code and writing

- **Original analysis code:** [Apache License 2.0](../LICENSE), preserving the
  licence already selected for this repository by its owner. This applies to
  the original Python scripts and original code cells contributed to this
  project. Software dependencies keep their own licences; installing a
  dependency does not place it under this repository's licence.
- **Original explanatory text:** [Creative Commons Attribution 4.0
  International (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/).
  This covers original prose in the README files, reports, research notes and
  notebook narrative. Attribute **Shota Moriwaki, _Pale yellow-green white
  dwarf candidates_**, link to [this
  repository](https://github.com/dj-thank/pale-yellow-green-white-dwarf-candidate),
  retain source citations, and indicate changes.
- **Excluded from the original-text grant:** quoted provider acknowledgment
  wording, licence texts, third-party publication extracts, survey/catalogue
  records, CIE tables, dependency documentation, and other externally authored
  material. Their original notices and applicable terms remain in force.

These grants apply to the project's own contributions to the extent rights
exist in them. No transfer of third-party copyright is claimed. The
[AI involvement statement](../docs/research-integrity.md#ai-involvement-and-responsibility)
explains how the work was produced; listing a person or institution as a data
provider does not make them an author of, or an endorser of, this reanalysis.

## Data, reference tables and derived products

The root Apache licence is **not a blanket licence for the research dataset**.
The following source-specific notices accompany the files, including values
carried forward into mixed tables, arrays and figures.

| Material in this repository | Provider terms and attribution | Scope and changes |
|---|---|---|
| Gaia DR3 photometry, MWDD Gaia XP exports, original XP coefficients, and Gaia-derived spectral/covariance products | **[CC BY-NC 3.0 IGO](https://creativecommons.org/licenses/by-nc/3.0/igo/)** as stated on the [Gaia-specific licence page](https://www.cosmos.esa.int/web/gaia-users/license); credit **ESA/Gaia/DPAC**. [ESA archive terms](https://www.cosmos.esa.int/web/esdc/terms-and-conditions) give the procedure for commercial-use authorization. | Includes the Gaia data components of `mwdd/gaia_validation/`, selected MWDD spectra and source photometry in manifests. Our reconstructions, covariance propagation and colour measurements are identified as derived products. The project does not grant commercial reuse of Gaia data. |
| DESI-origin spectra and derived numerical products | **[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)** under the [DESI data licence and acknowledgment instructions](https://data.desi.lbl.gov/doc/acknowledgments/). | Credit DESI and the relevant release paper, plus MWDD or the Warwick repository when they supplied the export. Parsing, masking, interpolation, photometric slope correction and colour integration are project processing, not new survey observations. |
| Public SDSS spectra and catalogue photometry | The [SDSS-IV data-use policy](https://www.sdss4.org/collaboration/#data-use-policy) places publicly released SDSS data in the **public domain**. Retain the [requested survey/release credits](https://www.sdss4.org/collaboration/citing-sdss/). | Includes direct DR17 FITS controls and selected MWDD SDSS exports. The status of released measurements does not establish the rights for unrelated SDSS website photographs, logos or publication text. |
| `reference/CIE_xyz_1931_2deg.csv`, its metadata, and the reformatted CIE table | CIE (2019), _Colour-matching functions of CIE 1931 standard colorimetric observer_, DOI **[10.25039/CIE.DS.xvudnb9b](https://doi.org/10.25039/CIE.DS.xvudnb9b)**, **[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/)**, as recorded in the [official metadata](../reference/CIE_xyz_1931_2deg.csv_metadata.json). | The official CSV is retained unchanged. `reference/cie1931_2deg.csv` is a reformatted computational table. Retain the attribution and applicable ShareAlike conditions for adaptations of the CIE material; describe any further changes. |
| Pan-STARRS1 photometry obtained through MAST | Follow the [MAST data-use policy](https://archive.stsci.edu/publishing/data-use) and [PS1 acknowledgment/citation instructions](https://archive.stsci.edu/publishing/mission-acknowledgements). MAST describes most holdings as public domain but also documents collection-specific exceptions. | Preserve PS1/MAST origin and query provenance. This project does not assign a new licence to source photometry or infer one uniform licence for all MAST collections. |
| MWDD compilation, CDS/SIMBAD/VizieR records, and literature-derived audit rows | Credit the original authors/catalogues and access service. [MWDD provenance](https://www.montrealwhitedwarfdatabase.org/description.html), [CDS terms](https://cds.unistra.fr/legals/), and [VizieR usage rules](https://cds.unistra.fr/vizier-org/licences_vizier.html) apply to their respective material. | Public access does not establish one licence for all components. The 25 selected MWDD raw exports included here have identified origins: **10 DESI, 9 Gaia XP and 6 SDSS**. Full MWDD and bulk author-created catalogue/model archives are not included. |
| Swan et al. (2026) catalogue-derived classification and contamination audit values | Cite [Swan et al. (2026)](https://arxiv.org/html/2609.04314v1) and the [Warwick White Dwarf Repository](https://cygnus.astro.warwick.ac.uk/phsdaj/WhiteDwarfs/). | Selected extracted audit values, source URLs, checksums and extraction code are retained. DESI-origin measurements keep DESI terms; no separate blanket licence is inferred for all author-created tables and model plots. |

### Figures and mixed results

The figures were generated for this project from the recorded spectra and
reference data. They are calculated plots and colour swatches, not survey
photographs. The original explanatory labels and design contributions may be
reused under the original-text CC BY 4.0 notice above, while the underlying
Gaia, DESI, CIE and other data components retain their applicable terms.
No single unrestricted licence is asserted for a complete composite figure,
notebook output or mixed-source result table. In particular, publishing a Gaia
reconstruction as a plot does not replace the Gaia data licence with Apache
2.0 or CC BY 4.0.

The same distinction applies to the calculated Planckian reference locus:
its generating code is original code, and its use of the attributed CIE
observer data remains documented. Nothing here asserts new exclusive rights
over physical facts or otherwise unrestricted numerical values.

## Provenance and provider notices

The selected raw data, derived arrays, 54 SDSS controls, Gaia audit products,
and gzip-compressed scan metadata are in the current Git tree, approximately
**80 MB** in total before Git compression. No separate release download is
needed for those bundled inputs. See
[data availability](../docs/data-availability.md) for the exact scope and
manifests, and [ACKNOWLEDGMENTS.md](../ACKNOWLEDGMENTS.md) for the provider
acknowledgment blocks and release references. A checksum identifies a file;
it does not substitute for a licence.

## 日本語

独自の解析コードと独自のノートブックのコードセルには、リポジトリ所有者が
選択した **Apache License 2.0** を適用します。独自の解説文には
**CC BY 4.0** を適用します。文章の再利用時は、Shota Moriwaki、研究名、
本リポジトリへのリンクを示し、原資料への引用を保持し、変更を明記してください。

原観測や第三者の表・文章・指定謝辞は、この独自コード／文章の許諾の対象外です。
特に、**Gaia DR3はCC BY-NC 3.0 IGO、DESIはCC BY 4.0、CIE等色関数は
CC BY-SA 4.0** という元の条件を保持します。SDSSの公開データには公式の
パブリックドメイン方針があり、PS1、CDS、MWDDなどは上表に記した出典と
該当する提供元の条件に従います。

計算図や混合データ表にも元データの条件が残ります。原データから作った図の
全体へ一律にApache 2.0やCC BY 4.0を付け直すものではありません。
本プロジェクトが第三者から著作権の譲渡や営利利用の許諾を受けたとの主張も
ありません。提供元の謝辞は原観測・サービスへの貢献を示すもので、本再解析の
査読、資金提供、承認を意味しません。
