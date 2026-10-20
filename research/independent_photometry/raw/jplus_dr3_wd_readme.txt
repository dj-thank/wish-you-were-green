J/A+A/701/A273      J-PLUS DR3 white dwarf catalog        (Lopez-Sanjuan+, 2025)
================================================================================
J-PLUS: Understanding outlier white dwarfs in the third data release via
dimensionality reduction.
    Lopez-Sanjuan C., Tremblay P.-E., del Pino A., Dominguez Sanchez H.,
    Vazquez Ramio H., Ederoclite A., Cenarro A.J., Marin-Franch A., Anguiano B.,
    Civera T., Cruz P., Fernandez-Ontiveros J.A., Jimenez-Esteban F.M.,
    Rebassa-Mansergas A., Vega-Ferrero J., Alcaniz J., Angulo R.E.,
    Cristobal-Hornillos D., Dupke R.A., Hernandez-Monteagudo C., Moles M.,
    Sodre L.Jr, Varela J.
    <Astron. Astrophys. 701, A273 (2025)>
    =2025A&A...701A.273L        (SIMBAD/NED BibCode)
================================================================================
ADC_Keywords: Stars, white dwarf; Effective temperatures; Stars, masses
Keywords: methods: statistical - catalogs - white dwarfs

Abstract:
    We present the white dwarf catalog derived from the third data release
    of the Javalambre Photometric Local Universe Survey (J-PLUS DR3),
    which covers 3284deg^2^ using 12 optical filters. A particular focus
    is given to the classification of outlier sources, those largely
    incompatible with the theoretical models used in the analysis, through
    dimensionality reduction techniques. We applied a Bayesian fitting
    process to the 12-band J-PLUS photometry of white dwarf candidates
    from Gaia EDR3. The derived parameters were effective temperature,
    surface gravity, and parallax. We used theoretical models from H- and
    He-dominated atmospheres, with priors applied to parallax and spectral
    type. From the posteriors, we derived the probability of an
    H-dominated atmosphere and of calcium absorption for each source.
    Outliers were identified as sources with chi^2^>=23.2, indicating
    significant deviations from the best-fitting model. We analyzed the
    residuals from the fits using the uniform manifold approximation and
    projection (UMAP) technique, which enables the classification of
    outliers into distinct categories. The catalog includes 14844 white
    dwarfs with r<20mag and 1<plx<100mas, with 72% of the sources lacking
    spectroscopic (R>500) classification. The application of UMAP to the
    residuals identified three main types of outliers: random measurement
    fluctuations (391 sources), metal-polluted white dwarfs (98 sources),
    and two-component systems (282 sources). The last category also
    includes white dwarfs with strong carbon absorption lines. We
    validated the reliability of J-PLUS classifications by comparison with
    spectroscopy from the Sloan Digital Sky Survey and the Dark Energy
    Spectroscopic Instrument, and with Gaia BP/RP low-resolution spectra,
    confirming a one-to-one correspondence between J-PLUS photometric and
    spectroscopic classifications. The J-PLUS DR3 white dwarf catalog
    provides a robust dataset for statistical studies. The use of
    dimensionality reduction techniques enhances the identification of
    peculiar objects, making this catalog a valuable resource for the
    selection of interesting targets such as metal-polluted white dwarfs
    or binary systems.

Description:
    The catalog presents the inferred atmospheric parameters, calcium
    absorption properties and outlier type for the 14844 white dwarfs with
    r<20.0mag in common between the white dwarf catalog defined from Gaia
    EDR3 in Gentile Fusillo et al. (2021MNRAS.508.3877G) and J-PLUS DR3
    (Lopez-Sanjuan et al., 2024A&A...683A..29L). The J-PLUS twelve-band
    photometry is compared with theoretical models to derive the
    probability density functions (PDFs) for the effective temperature
    (Teff), the surface gravity, and the parallax by assuming H- and
    He-dominated atmospheres. We used pure-H models to describe
    H-dominated atmospheres (Tremblay et al., 2011ApJ...730..128T,
    2013A&A...559A.104T), while mixed models with H/He=10^-5^ at
    Teff>6500K and pure-He models at Teff<6500K were used to describe
    He-dominated atmospheres (Cukanovaite et al., 2018MNRAS.481.1522C,
    2019MNRAS.490.1010C). The mass-radius relation of Fontaine et al.
    (2001PASP..113..409F) for thick (H-atmospheres) and thin
    (He-atmospheres) hydrogen layers was assumed in the modeling. We
    obtained the summary statistics for each parameter by marginalizing
    the PDFs over the other parameters at a fixed atmospheric composition
    and performing a Gaussian fit to the resulting distribution. The
    reported parameters and their uncertainties are the median and the
    dispersion of the best-fitting Gaussian. The probabilities of having
    H-dominated atmosphere and calcium absorption were also computed.
    Further details can be found in Lopez-Sanjuan et al.
    (2022A&A...658A..79L, 2024A&A...691A.211L). The error-normalized
    residuals from the best-fitting model in the 12 J-PLUS filters were
    reduced with UMAP (McInnes et al., 2018arXiv180203426M) to a 2D
    manifold. The outlier sources with chi^2^>23.2 where classified in
    three categories (Typeout): random fluctuations, metal-polluted
    white dwarfs, and two component systems.

File Summary:
--------------------------------------------------------------------------------
 FileName      Lrecl  Records   Explanations
--------------------------------------------------------------------------------
ReadMe            80        .   This file
catalog.dat      274    14844   Atmospheric parameters, calcium absorption and
                                 outlier type for J-PLUS DR3 white dwarfs
--------------------------------------------------------------------------------

See also:
   J/A+A/658/A79  : J-PLUS white dwarf atmospheric parameters
                                                         (Lopez-Sanjuan+, 2022)
   J/A+A/691/A211 : J-PLUS DR2 white dwarfs calcium absorption
                                                         (Lopez-Sanjuan+, 2024)

   http://archive.cefca.es/catalogues/jplus-dr3 : J-PLUS DR3 Home Page

Byte-by-byte Description of file: catalog.dat
--------------------------------------------------------------------------------
   Bytes Format Units     Label     Explanations
--------------------------------------------------------------------------------
   1-  6  I6    ---       TileID    Identifier of the J-PLUS Tile image in the
                                     r band where the object was detected
   8- 13  I6    ---       Number    Number identifier assigned by SExtractor
                                     for the object in the r band image
  15- 22  F8.4  deg       RAdeg     Right ascension (J2000)
  24- 30  F7.4  deg       DEdeg     Declination (J2000)
  32- 36  F5.2  mag       rmag      De-reddened total r-band apparent magnitude
  38- 41  F4.2  mag     e_rmag      Uncertainty in rmag
  43- 46  F4.2  ---       psel      Selection probability for rmag<=19.5mag
                                     and 1<=parallax<=100mas
  48- 52  F5.3  ---       pH        Probability of having a H-dominated
                                     atmosphere
  54- 61  F8.1  K         TeffH     Effective temperature for a H-dominated
                                     atmosphere
  63- 70  F8.1  K       e_TeffH     Uncertainty in TeffH
  72- 75  F4.2  [cm/s2]   loggH     Decimal logarithm of the surface gravity
                                     for a H-dominated atmosphere
  77- 80  F4.2  [cm/s2] e_loggH     Uncertainty in loggH
  82- 86  F5.2  mas       plxH      Parallax for a H-dominated atmosphere
  88- 91  F4.2  mas     e_plxH      Uncertainty in plxH
  93- 97  F5.3  Msun      MassH     Mass for a H-dominated atmosphere
  99-103  F5.3  Msun    e_MassH     Uncertainty in MassH
 105-116  F12.2 pc3       VH        Effective volume at 10<=d<=1000pc for
                                     a H-dominated atmosphere
 118-125  F8.1  K         TeffHe    Effective temperature for a He-dominated
                                     atmosphere
 127-133  F7.1  K       e_TeffHe    Uncertainty in TeffHe
 135-138  F4.2  [cm/s2]   loggHe    Decimal logarithm of the surface gravity
                                     for a He-dominated atmosphere
 140-143  F4.2  [cm/s2] e_loggHe    Uncertainty in loggHe
 145-149  F5.2  mas       plxHe     Parallax for a He-dominated atmosphere
 151-154  F4.2  mas     e_plxHe     Uncertainty in plxHe
 156-160  F5.3  Msun      MassHe    Mass for a He-dominated atmosphere
 162-166  F5.3  Msun    e_MassHe    Uncertainty in MassHe
 168-179  F12.2 pc3       VHe       Effective volume at 10<=d<=1000pc for
                                     a He-dominated atmosphere
 181-185  F5.3  ---       pca       Probability of having calcium absorption
 187-193  F7.2  A         EWJ0395   Equivalent width in the J0395 passband
 195-200  F6.2  A       e_EWJ0395  Unvertainty in EWJ0395
 202-209  F8.1  K         TeffCa    Effective temperature from the calcium
                                     absorption analysis
 211-218  F8.1  K       e_TeffCa    Uncertainty in TeffCa
 220-224  F5.2  [cm/s2]   loggCa    Decimal logarithm of the surface gravity
                                     from the calcium absorption analysis
 226-229  F4.2  [cm/s2] e_loggCa    Uncertainty in loggCa
 231-235  F5.2  mas       plxCa     Parallax from the calcium absorption
                                     analysis
 237-240  F4.2  mas     e_plxCa     Uncertainty in plxCa
 242-246  F5.3  Msun      MassCa    Mass from the calcium absorption analysis
 248-252  F5.3  Msun    e_MassCa    Uncertainty in MassCa
 254-260  F7.2  ---       chi2      Chi2 from the best-fitting model
 262-266  F5.2  ---       UMAP1     First dimension of the UMAP manifold
 268-272  F5.2  ---       UMAP2     Second dimension of the UMAP manifold
     274  I1    ---       Typeout   Outlier type (Tout)
--------------------------------------------------------------------------------

Acknowledgements:
    Carlos Lopez San Juan, clsj(at)cefca.es

================================================================================
(End)    Carlos Lopez San Juan [CEFCA], Patricia Vannier [CDS]       22-Aug-2025
