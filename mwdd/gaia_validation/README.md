# Independent Gaia XP verification of J0913 and J0429

This audit retrieves the original public Gaia DR3 XP coefficients and their
correlations, reconstructs the spectra with GaiaXPy 2.1.5, and propagates the
coefficient covariance to CIE colour. It validates the two candidate spectra;
it does not establish a new-star discovery or a secure human colour label.

## Results at 1 nm sampling

Flux is integrated with the official CIE 1931 2° colour matching functions over
360–830 nm. No flux clipping, photometric adjustment, sky masking, or illuminant
adaptation is applied. Display RGB is normalized to its largest linear channel
before the sRGB transfer function. Duv here is the signed distance to the
Planckian locus in CIE 1960 u,v, positive on the green side.

| Source and basis choice | CIE x | CIE y | Display sRGB | Duv | Formal 95% Duv interval | Formal probability G is largest |
|---|---:|---:|---|---:|---|---:|
| J0913 full, 55 BP + 55 RP | 0.345393 | 0.392851 | #F7FFBF | +0.019235 ± 0.003515 | +0.01236 to +0.02612 | 85.0% |
| J0913 truncated, 10 BP + 2 RP | 0.341019 | 0.382534 | #F9FFC9 | +0.016351 ± 0.003267 | +0.00995 to +0.02274 | 77.8% |
| J0429 full, 55 BP + 55 RP | 0.333227 | 0.368282 | #FAFFD7 | +0.012993 ± 0.002204 | +0.00867 to +0.01730 | 82.3% |
| J0429 truncated, 4 BP + 2 RP | 0.333260 | 0.372494 | #F7FFD3 | +0.014928 ± 0.001801 | +0.01141 to +0.01846 | 96.5% |

The ± values are one formal standard deviation. The truncation levels are
Gaia's published `bp_n_relevant_bases` and `rp_n_relevant_bases`; GaiaXPy's
function default is **no truncation**. Both mean spectra stay on the green side
of the thermal locus after recommended truncation. Green exceeding red is much
less certain: the full-basis G−R statistic is only 1.04σ for J0913 and 0.93σ for
J0429. The positive Duv is better supported than a strict “green star” label.

These intervals describe the supplied coefficient noise model only. They
exclude unprovided calibration systematics, BP/RP cross-band calibration
covariance, blend contamination and truncation bias. Screening thousands of
spectra also means these per-source uncertainties are not discovery p-values.

## Identity, native units and the MWDD export

| Short name | Gaia DR3 source_id | Original coefficient CSV SHA-256 |
|---|---|---|
| J0913 | 818833831355548928 | `0391068af60bbf6ba38ef13619a8999807ee8a1a25d9d98698d6fa6e7acb3bd9` |
| J0429 | 3204436719718449280 | `998a0e77ed2dbbd88dd02b28fda55ddadc37a40fdda1695f318522b9c414d546` |

ESA DataLink discovery endpoints:

- https://gea.esac.esa.int/data-server/datalink/links?ID=Gaia+DR3+818833831355548928
- https://gea.esac.esa.int/data-server/datalink/links?ID=Gaia+DR3+3204436719718449280

The downloaded XML supplies these coefficient access URLs; the documented
`FORMAT=CSV` option was appended:

- https://gea.esac.esa.int/data-server/data?ID=Gaia+DR3+818833831355548928&RETRIEVAL_TYPE=XP_CONTINUOUS&LINKING_PARAMETER=SOURCE_ID&FORMAT=CSV
- https://gea.esac.esa.int/data-server/data?ID=Gaia+DR3+3204436719718449280&RETRIEVAL_TYPE=XP_CONTINUOUS&LINKING_PARAMETER=SOURCE_ID&FORMAT=CSV

Exact URLs, UTC retrieval times, sizes and hashes for both XML and CSV products
are in `source_manifest.json`. Source URLs and checksums for the matching MWDD
exports are in `mwdd_xp_sources.json`.

The MWDD exports match the **full-basis** GaiaXPy reconstruction sampled at
`numpy.geomspace(330, 1050, 361)` nm. Their fractional RMS flux discrepancies are
6.9×10⁻⁷ for J0913 and 2.0×10⁻⁶ for J0429, consistent with the MWDD text rounding.
The unfitted median data/model ratios are 0.999999924 and 0.999999956. This
directly verifies that these MWDD XP fluxes retain GaiaXPy's **Fλ in W m⁻² nm⁻¹**;
the MWDD wavelength column is in Å. Conversion to erg s⁻¹ cm⁻² Å⁻¹ would multiply
flux by 100, which does not change colour. These exports are not the separate
343-sample ESA `XP_SAMPLED` data product.

## Covariance calculation and verification

For each BP or RP band, the archive provides formal coefficient errors `e` and
the packed coefficient correlation `R`. We expand the latter symmetrically,
with unit diagonal, and form `C = diag(e) R diag(e)`. The formal errors already
have the band fit scale incorporated; applying that scale again would double
count it.

Let `D` be GaiaXPy's calibrated basis matrix, with basis functions in rows and
wavelength samples in columns, and `w` its BP/RP merging weight. We form
`A = D diag(w)`. The reconstructed flux and propagated covariance are:

```text
f = c_BP @ A_BP + c_RP @ A_RP
C_f = A_BP.T @ C_BP @ A_BP + A_RP.T @ C_RP @ A_RP
```

For truncation, coefficient vectors, covariance matrices, and basis rows are
sliced to the corresponding recommended number of bases. BP and RP coefficient
errors are treated as independent across bands, consistent with the available
data and GaiaXPy's flux-error calculation.

The direct reconstruction and the square root of the propagated diagonal agree
with GaiaXPy's returned flux and flux errors to better than 2×10⁻¹⁶ relative to
the largest absolute value. The resulting covariance is symmetric and positive
semidefinite to floating precision.

We do **not** use GaiaXPy's returned packed *sampled* correlations for this
audit. In this installed version and these inputs, expanding the truncated
sampled correlations gives substantially negative eigenvalues (−3.61 for J0913
and −4.66 for J0429 at 1 nm). They also differ from the direct linear propagation
with both merge weights. This is an observed validation discrepancy; its
upstream cause has not been independently established. The untouched returned
packed arrays are retained in each NPZ under
`gaiaxpy_output_packed_correlation` so the discrepancy can be investigated.
Only the directly propagated `covariance_w2_m4_nm2` is used for inference.

The CIE integral is linear: using a quadrature/colour-matching matrix `B`,
`XYZ = B.T @ f` and `C_XYZ = B.T @ C_f @ B`. We draw 200,000 correlated Gaussian
XYZ realizations with seed 20261018 for nonlinear chromaticity intervals and
channel-order probabilities. No individual sampled wavelengths are assumed
independent. Both 1 nm and 2 nm integrations were checked; the largest Duv
difference is 1.9×10⁻⁵, small compared with formal uncertainty.

## Files and reproduction

`gaia_candidate_summary.json` contains the four 1 nm cases. The per-source
`*_colour_covariance_audit.json` files contain full metrics, 3×3 XYZ covariance,
2×2 u,v covariance, and the MWDD comparison. Each `*_1nm.npz` contains native
flux, errors, wavelengths and the full sampled covariance. The original
coefficient CSVs preserve every archived coefficient, error and correlation.

The scripts resolve files relative to their own directory. Keep this directory
at `mwdd/gaia_validation/`, the parent project's `colour_pipeline.py` at the
project root, its CIE reference at `reference/CIE_xyz_1931_2deg.csv`, and the two
MWDD raw exports at the relative paths in `mwdd_xp_sources.json`. No full MWDD
catalogue or acquisition manifest is needed to rerun this audit.

From the project root, using Python 3.12:

```bash
python -m venv .venv-gaia
.venv-gaia/bin/pip install -r mwdd/gaia_validation/requirements-gaia.txt
python -m venv .venv-colour
.venv-colour/bin/pip install -r mwdd/gaia_validation/requirements-colour.txt

# Optional: retrieve the public originals again if not already cached.
.venv-gaia/bin/python mwdd/gaia_validation/fetch_official_gaia_xp.py 818833831355548928 j0913
.venv-gaia/bin/python mwdd/gaia_validation/fetch_official_gaia_xp.py 3204436719718449280 j0429

.venv-gaia/bin/python mwdd/gaia_validation/reconstruct_j0913.py j0913
.venv-gaia/bin/python mwdd/gaia_validation/reconstruct_j0913.py j0429
.venv-colour/bin/python mwdd/gaia_validation/audit_j0913_colours.py j0913
.venv-colour/bin/python mwdd/gaia_validation/audit_j0913_colours.py j0429
```

Despite their initial J0913 filenames, the two analysis scripts accept either
source prefix. Reconstruction also regenerates the 2 nm and logarithmic grid
files needed for the rounding/identity checks; only the 1 nm products need be
included in the compact deliverable. The exact environments originally used
are recorded in `gaia_environment.json` and `colour_environment.json`.

Primary documentation:

- Gaia DataLink: https://www.cosmos.esa.int/web/gaia-users/archive/datalink-products
- GaiaXPy: https://gaia-dpci.github.io/GaiaXPy-website/
- Sampled-spectrum units: https://gea.esac.esa.int/archive/documentation/GDR3/Gaia_archive/chap_datamodel/sec_dm_spectroscopic_tables/ssec_dm_xp_sampled_mean_spectrum.html
