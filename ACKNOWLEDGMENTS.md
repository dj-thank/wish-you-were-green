# Acknowledgments / 謝辞

This research note reanalyses public observations. The original surveys,
catalogue authors, archive teams and software developers deserve credit for
the measurements, processing and tools on which it depends. Provider wording
was checked against the linked official instructions on **2026-10-18**.

The **20 October 2026 follow-up** adds the SkyMapper, J-PLUS and SVO credits
below and an explicit citation for a previously identified AM CVn system.
Earlier provider blocks retain their recorded source-check date.

The block quotations below reproduce the providers' requested acknowledgment
text. They are **third-party credit notices**, excluded from this project's
original-text licence grant. A survey's funding acknowledgment is not a claim
that the same agencies funded, reviewed or endorsed this project. Data reuse
terms are recorded separately in [LICENSES/README.md](LICENSES/README.md) and
[data availability](docs/data-availability.md).

## DESI

DESI public data are provided under CC BY 4.0. This work uses DESI-origin
spectra supplied through MWDD and compares selected results with the public
white-dwarf catalogue of Swan et al. (2026). The relevant release is
[DESI DR1](https://data.desi.lbl.gov/doc/releases/dr1/); its release paper is
_Data Release 1 of the Dark Energy Spectroscopic Instrument_ (DESI
Collaboration et al., 2026), as listed in the official instructions. The
original downloaded spectra are retained as supplied. Subsequent parsing,
invalid-pixel and narrow sky-window treatment, interpolation, photometric
slope correction, uncertainty propagation and colour integration are
documented project transformations.

**Provider acknowledgment**, from the [official DESI
instructions](https://data.desi.lbl.gov/doc/acknowledgments/):

> This research used data obtained with the Dark Energy Spectroscopic Instrument (DESI). DESI construction and operations is managed by the Lawrence Berkeley National Laboratory. This material is based upon work supported by the U.S. Department of Energy, Office of Science, Office of High-Energy Physics, under Contract No. DE–AC02–05CH11231, and by the National Energy Research Scientific Computing Center, a DOE Office of Science User Facility under the same contract. Additional support for DESI was provided by the U.S. National Science Foundation (NSF), Division of Astronomical Sciences under Contract No. AST-0950945 to the NSF’s National Optical-Infrared Astronomy Research Laboratory; the Science and Technology Facilities Council of the United Kingdom; the Gordon and Betty Moore Foundation; the Heising-Simons Foundation; the French Alternative Energies and Atomic Energy Commission (CEA); the National Council of Humanities, Science and Technology of Mexico (CONAHCYT); the Ministry of Science and Innovation of Spain (MICINN), and by the DESI Member Institutions: www.desi.lbl.gov/collaborating-institutions. The DESI collaboration is honored to be permitted to conduct scientific research on I’oligam Du’ag (Kitt Peak), a mountain with particular significance to the Tohono O’odham Nation. Any opinions, findings, and conclusions or recommendations expressed in this material are those of the author(s) and do not necessarily reflect the views of the U.S. National Science Foundation, the U.S. Department of Energy, or any of the listed funding agencies.

## ESA / Gaia / DPAC

This project uses Gaia DR3 astrometry and photometry, MWDD-rendered XP spectra,
and official XP continuous coefficients, errors and correlations for the two
principal candidates. GaiaXPy 2.1.5 was used for coefficient reconstruction.
The project is responsible for its own truncation comparisons, covariance
propagation and colour interpretation.

**Provider acknowledgment**, from the [Gaia DR3 credit and citation
instructions](https://gea.esac.esa.int/archive/documentation/GDR3/Miscellaneous/sec_credit_and_citation_instructions/):

> This work has made use of data from the European Space Agency (ESA) mission Gaia (https://www.cosmos.esa.int/gaia), processed by the Gaia Data Processing and Analysis Consortium (DPAC, https://www.cosmos.esa.int/web/gaia/dpac/consortium). Funding for the DPAC has been provided by national institutions, in particular the institutions participating in the Gaia Multilateral Agreement.

The same instructions require the mission paper, **Gaia Collaboration et al.
(2016), _The Gaia mission_**, and the release paper, **Gaia Collaboration et al.
(2023), _Gaia Data Release 3: Summary of the contents and survey properties_**.
The [official DR3 paper list](https://www.cosmos.esa.int/web/gaia/dr3-papers)
also identifies the relevant XP processing, calibration and validation
papers. Gaia's [data-specific licence](https://www.cosmos.esa.int/web/gaia-users/license)
is CC BY-NC 3.0 IGO; this acknowledgment does not change those terms.

## Sloan Digital Sky Survey

The analysis uses spectra served by the SDSS DR17 archive, photometric
catalogue queries, and SDSS-origin exports served by MWDD. The target
selection also uses **Kepler et al. (2019), _White dwarf and subdwarf stars in
the Sloan Digital Sky Survey Data Release 14_**, DOI
[10.1093/mnras/stz960](https://doi.org/10.1093/mnras/stz960).
Archive release and original observing programme are distinct: a DR17
download can contain observations obtained in earlier SDSS phases. The
[SDSS citation guidance](https://www.sdss4.org/collaboration/citing-sdss/)
lists the appropriate survey, release and instrument references, including
the DR17 paper **Abdurro'uf et al. (2022)**. The recorded FITS URLs and headers
preserve the provenance needed to identify those observations.

**SDSS-IV provider acknowledgment**, from the [official SDSS-IV
collaboration page](https://www.sdss4.org/collaboration/):

> Funding for the Sloan Digital Sky Survey IV has been provided by the Alfred P. Sloan Foundation, the U.S. Department of Energy Office of Science, and the Participating Institutions. SDSS acknowledges support and resources from the Center for High-Performance Computing at the University of Utah. The SDSS web site is www.sdss4.org.
>
> SDSS is managed by the Astrophysical Research Consortium for the Participating Institutions of the SDSS Collaboration including the Brazilian Participation Group, the Carnegie Institution for Science, Carnegie Mellon University, Center for Astrophysics | Harvard & Smithsonian (CfA), the Chilean Participation Group, the French Participation Group, Instituto de Astrofísica de Canarias, The Johns Hopkins University, Kavli Institute for the Physics and Mathematics of the Universe (IPMU) / University of Tokyo, the Korean Participation Group, Lawrence Berkeley National Laboratory, Leibniz Institut für Astrophysik Potsdam (AIP), Max-Planck-Institut für Astronomie (MPIA Heidelberg), Max-Planck-Institut für Astrophysik (MPA Garching), Max-Planck-Institut für Extraterrestrische Physik (MPE), National Astronomical Observatories of China, New Mexico State University, New York University, University of Notre Dame, Observatório Nacional / MCTI, The Ohio State University, Pennsylvania State University, Shanghai Astronomical Observatory, United Kingdom Participation Group, Universidad Nacional Autónoma de México, University of Arizona, University of Colorado Boulder, University of Oxford, University of Portsmouth, University of Utah, University of Virginia, University of Washington, University of Wisconsin, Vanderbilt University, and Yale University.

## Pan-STARRS1 / MAST

Pan-STARRS1 catalogue photometry, accessed through MAST, supplies an external
g/r/i calibration check. Credit the survey description **Chambers et al.
(2016)** and the database description **Flewelling et al. (2020)**, as directed
by the [PS1/MAST citation
instructions](https://archive.stsci.edu/publishing/mission-acknowledgements).

**Provider acknowledgment**, from those instructions:

> The Pan-STARRS1 Surveys (PS1) and the PS1 public science archive have been made possible through contributions by the Institute for Astronomy, the University of Hawaii, the Pan-STARRS Project Office, the Max-Planck Society and its participating institutes, the Max Planck Institute for Astronomy, Heidelberg and the Max Planck Institute for Extraterrestrial Physics, Garching, The Johns Hopkins University, Durham University, the University of Edinburgh, the Queen's University Belfast, the Harvard-Smithsonian Center for Astrophysics, the Las Cumbres Observatory Global Telescope Network Incorporated, the National Central University of Taiwan, the Space Telescope Science Institute, the National Aeronautics and Space Administration under Grant No. NNX08AR22G issued through the Planetary Science Division of the NASA Science Mission Directorate, the National Science Foundation Grant No. AST–1238877, the University of Maryland, Eotvos Lorand University (ELTE), the Los Alamos National Laboratory, and the Gordon and Betty Moore Foundation.

## MWDD, CDS and catalogue authors

The [Montreal White Dwarf Database](https://www.montrealwhitedwarfdatabase.org/),
maintained by Patrick Dufour and Simon Blouin, made the broad source selection
and source-linked spectral access possible. Its reference is **Dufour et al.
(2017), _The Montreal White Dwarf Database: A Tool for the Community_**,
[arXiv:1610.00986](https://arxiv.org/abs/1610.00986). Every contributing survey
and original catalogue/model author retains credit for their own data and
interpretation; MWDD access is not a new authorship claim by this project.

**CDS provider acknowledgments**, from the [official CDS
instructions](https://cds.unistra.fr/help/acknowledgement/):

> This research has made use of the SIMBAD database, CDS, Strasbourg Astronomical Observatory, France

> This research has made use of the VizieR catalogue access tool, CDS, Strasbourg Astronomical Observatory, France (DOI : 10.26093/cds/vizier).

The associated service references are **Wenger et al. (2000)** for SIMBAD and
**Ochsenbein et al. (2000)** for VizieR. The original authors and publications
of the retrieved catalogues are cited in [references.bib](docs/references.bib),
including Kepler et al. (2019), Hollands et al. (2017), Kilic et al.
(2020/2025/2026), Vincent et al. (2023/2024) and Swan et al. (2026).

## CIE and the prior colour study

Human-vision colour integration uses **CIE (2019), _Colour-matching functions
of CIE 1931 standard colorimetric observer_**, DOI
[10.25039/CIE.DS.xvudnb9b](https://doi.org/10.25039/CIE.DS.xvudnb9b), under
[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/). The original
CSV and metadata are retained in [reference/](reference/). Reformatting,
integration and the calculated reference locus are documented in the code.

**Hollands et al. (2026), _Any colour you like: The diverse chromaticities of
white dwarfs_**, DOI [10.1093/rasti/rzag069](https://doi.org/10.1093/rasti/rzag069),
motivated the search and supplied the published colour comparisons and
exclusion list. The current note does not claim that study's authors
participated in or endorsed this reanalysis.

## SkyMapper DR4 — added 20 October 2026

The additional imaging photometry and individual detection records are from
the SkyMapper Southern Survey, provided by the SkyMapper Team and the
Australian National University through the NCI/ASVO public service. We cite
**Onken et al. (2024)**, DOI
[10.1017/pasa.2024.53](https://doi.org/10.1017/pasa.2024.53), and the DR4 dataset
DOI [10.25914/5M47-S621](https://doi.org/10.25914/5M47-S621), as requested by the
[official citation instructions](https://skymapper.anu.edu.au/how-to-cite/).
The downloaded provider acknowledgment wording is retained in
[the original citation page](research/independent_photometry/raw/skymapper_citation.html)
for use in subsequent publications. Catalogue matching, stricter quality
selection and passband comparison are this project's documented operations.

## J-PLUS / CEFCA — added 20 October 2026

The J-PLUS measurements were obtained with JAST80/T80Cam at the Observatorio
Astrofísico de Javalambre in Teruel, operated by the Centro de Estudios de
Física del Cosmos de Aragón (CEFCA). We credit the J-PLUS collaboration,
**Cenarro et al. (2019)**, DOI
[10.1051/0004-6361/201833036](https://doi.org/10.1051/0004-6361/201833036), and
the [DR4 public archive](https://archive.cefca.es/catalogues/jplus-dr4).
Use the [provider's publication acknowledgments](https://www.j-plus.es/datareleases/acknowledgements)
when publishing from these observations.

The independent source photons do not imply fully independent calibration:
Gaia/BEST standards, white-dwarf-locus adjustments and PS1 r contribute shared
information. The original DR3 outlier classifications for three matched
candidates remain credited to **López-Sanjuan et al. (2025)**, DOI
[10.1051/0004-6361/202555286](https://doi.org/10.1051/0004-6361/202555286), and
[their CDS catalogue](https://cdsarc.cds.unistra.fr/viz-bin/cat/J/A+A/701/A273).

## SVO passband profiles — added 20 October 2026

We used the [SVO Filter Profile Service “Carlos Rodrigo”](https://svo2.cab.inta-csic.es/svo/theory/fps/)
and credit **Rodrigo, Cruz, Aguilar et al. (2024)**, DOI
[10.1051/0004-6361/202449998](https://doi.org/10.1051/0004-6361/202449998).
The service acknowledges MCIN/AEI support, identifier
10.13039/501100011033, through grant PID2023-146210NB-I00. This is service
funding, not a funding claim for this project.

The [profile manifest](research/measurement_design/profile_manifest.json)
retains each original filter provider/reference, response samples, components,
URL and hash. The saved SkyMapper/J-PLUS profiles include the instrument and
atmosphere, not only the filters. Added mathematical zero endpoints and their
sensitivity comparisons are identified as project transformations. We do not
claim authorship of the original transmission curves.

## Prior AM CVn identification — added 20 October 2026

**Carter et al. (2014)**, DOI
[10.1093/mnras/stu142](https://doi.org/10.1093/mnras/stu142), previously
identified SDSS J113732.32+405458.3 as an AM CVn binary. The repository's
unusual emission-line record for this object (row 6462) is a re-identification
of that known system. Its spectrum is not a new DQ, quasar or AM CVn discovery.
The original authors retain credit; no participation in this reanalysis is
implied.

## Software and project contribution

The computations use the public Python ecosystem, including NumPy, SciPy,
pandas, Astropy, Matplotlib, Colour, speclite, GaiaXPy and Jupyter/nbformat.
Dependency versions and their roles are recorded in the requirements files,
the Gaia audit and the [reproducibility guide](docs/reproducibility.en.md).
These dependencies retain their own licences and authorship.

ChatGPT carried out the data acquisition, programming, numerical analysis,
literature checks and drafting at **Shota Moriwaki's direction**. The analysis
and documentation include internal computational checks; independent
external expert review and peer review have **not** been established. See
[research integrity](docs/research-integrity.md) for the bounded novelty claim
and the remaining measurement limitations.

## 日本語

原観測と処理基盤を提供したDESI、ESA/Gaia/DPAC、SDSS、Pan-STARRS1/MAST、
天体の情報と原スペクトルへのアクセスを整理したMWDD、SIMBAD、VizieR/CDS、
原カタログ・大気モデル・先行する色研究の著者、CIEおよび利用ソフトウェアの
開発者に謝意を表します。上の引用部分は、各提供元の指定する第三者の謝辞です。
原サーベイの資金提供先・所属機関を記載しても、本プロジェクトが同じ支援や
承認を受けたことを意味しません。

10月20日の追加研究では、SkyMapper Team／ANU／NCI・ASVO、J-PLUS／CEFCA、
SVO Filter Profile Serviceと元の応答関数の提供者にも謝意を表します。
SkyMapper DR4論文とデータDOI、J-PLUSの原カタログと既報外れ分類、SVOの
サービス論文・元フィルター出典を上に記載しました。SDSS J113732.32+405458.3は
Carter et al. (2014)が公刊した既知AM CVnです。本解析による再同定を新発見と
しておらず、原著者の成果として引用します。

公開データの取得・計算・調査・原稿作成は、Shota Moriwakiの指示のもとで
ChatGPTが実施しました。内部での計算検証と外部の専門家査読は区別し、
外部査読や原著者による承認を受けたとの主張はしていません。
