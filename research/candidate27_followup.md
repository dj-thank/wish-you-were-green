# Follow-up synthesis for the initial 27 candidates

This report preserves the **initial 27-object candidate set**. It is not the final census after the flux-convention audit, and it does not assign confirmed/discovery labels or combine probabilities.

## Results that survive explicit bookkeeping

There are **25 DESI conditional intervals**, including **12 newly anchored objects**, and **26 objects with both full and truncated native-coefficient Gaia intervals**. J1323−0129 has no available native Gaia XP result. These counts come from [standardized DESI colours](precision/candidate_recalibration/standardized_colours.csv) and [formal Gaia results](precision/gaia_expanded/formal_colour_results.csv), joined against the [frozen initial set](external_validation/gaia_extended_input.csv).

**9 objects** have DESI and both Gaia central 95% intervals entirely beyond the same signed exploratory |Duv|=0.01 boundary. All nine lie on the negative-Duv side. This is a descriptive intersection of conditional intervals, not a joint significance. One of these, Gaia DR3 761677269868775040, has a Gaia neighbour with G-band flux ratio 417.90 at 9.268 arcsec. Keeping that field concern separate leaves **8 objects without this particular >10× neighbour flag**, not eight confirmed or contamination-free discoveries. The broader [field audit](external_validation/results/gaia_extended_quality.csv) and [neighbour table](external_validation/results/gaia_extended_neighbours.csv) remain necessary.

Full versus truncated Gaia point estimates switch sides of the exploration boundary in **5 objects**. Whether the Gaia 95% interval is wholly beyond that boundary differs between reconstructions for **5 objects**. The maximum nominal two-dimensional uv separation among available DESI/full-Gaia/truncated-Gaia estimates is at least 0.003 for **17 objects**. This last quantity is a sensitivity diagnostic, not an error-normalized statistic.

![All initial 27 objects and their conditional uncertainty intervals](candidate27_uncertainty_comparison.png)

## Definitions and limitations

The plot shows MC medians and central 2.5–97.5 percentile intervals. DESI uses the supplied 6,000-draw conditional spectral-noise/PS1-anchor calculation; the independent resampled-pixel assumption does not include the full spectral covariance or coherent calibration errors. Gaia uses 200,000 draws per reconstruction with native coefficient covariance propagated to colour. Cross-BP/RP covariance is unavailable and set to zero; calibration, contamination, truncation bias and selection are not fully modelled. **Full and truncated Gaia are reconstructions of the same observations.** A narrow truncated interval can accompany substantial reconstruction bias. These intervals must not be pooled as independent evidence. See [reconstruction metadata](precision/gaia_expanded/reconstruction.json) and the model caveats in the source result tables.

The photometric pipeline applies max(quoted error, 0.02 mag). Swan's quoted PS1 errors already include the rounded native DR1 error and 0.01 mag in quadrature; the latter is not added again. The means of the four headline stars agree with the checked PS1 entries, while error definitions/releases differ from the original calculation. J0913's new standardized nominal Duv is +0.019058 rather than exactly the v0.1 headline value. This is a change in calibration/error treatment, not evidence of a stellar change. See [the photometry-definition audit](literature/swan_photometry_definition.md). Original v0.1 headline results are retained.

“Max Δuv” is the largest Euclidean distance in CIE 1960 (u,v) among the available nominal DESI, full Gaia and truncated Gaia points. The full/truncated-only distance and both DESI–Gaia distances are also stored individually in [CSV](candidate27_followup.csv). A missing measurement is left unavailable; it is not evidence for constancy or absence of an effect. The complete definitions and hashed inputs are in [JSON](candidate27_followup.json).

## Cases that change the interpretation

- **J1323−0129 / 3638333660492606976:** DESI colour remains available, but native Gaia XP is unavailable and the legacy SDSS flux convention is unresolved. Independent SDSS colour support is withdrawn; this is a DESI-only colour candidate pending a spectrum with verified units.
- **1245262790370992256:** already a Gaia variable, with CV as its catalogue best classifier class; the classifier score is not a posterior classification probability. The legacy SDSS convention is unresolved and no standardized DESI interval is available. Obtain epoch-resolved classification and colour.
- **PSO J186.4406+47.1036 / 1542337839923130624:** the SDSS F_lambda convention is verified against original row 9539. Two archive representations of the same SDSS observation do not add an independent observation. Gaia supplies a second instrument, but the external calibrated DESI interval remains unavailable. These unit decisions follow the [initial27 SDSS impact table](precision/flux_units/candidate27_sdss_convention_impact.json); none of its three SDSS entries is among the positively identified F_nu set.
- **J0913+4434 / 818833831355548928:** full Gaia has a positive interval beyond +0.01, but the truncated lower bound is +0.009956, just below the exploratory threshold. It is consequently outside the nine-object interval intersection, despite its strong positive DESI result. This near-boundary bookkeeping is not a physical verdict on colour or novelty.
- **1182083542272959232:** truncated Gaia moves the nominal Duv close to zero, and a neighbour is 11.30 times brighter in Gaia G. Both reconstruction sensitivity and the actual field require follow-up.
- **Separate-night checks:** the independently extracted complete DESI colours for 2482684508055379584 are −0.009529 and −0.011147, straddling the point-estimate threshold. For 1691957732959636608 they are −0.010579 and −0.006955, also straddling it. For 1078624858218235776 they are +0.010261 and +0.013296, both above +0.01. These nights use the same PS1 anchors and incomplete covariance models, so the differences do not establish intrinsic variability. J1329's extra retrieved night lacks valid z-arm coverage and cannot supply a second full colour. See [six accepted night results](literature/outputs/desi_additional_nights_summary.csv) and [J1329's failed full-colour validation](literature/outputs/j1329_second_epoch_comparison.json).
- **Prior work:** 25/27 have exact-ID matches to prior atmosphere-fit tables. Missing table matches do not establish novelty. The [prior inventory](literature/outputs/candidate27_prior_inventory.csv) supplies fitted composition, temperature, gravity, mass and citations; these are inherited model results, not independent measurements performed here. For DZ fits with other metal ratios fixed to CI chondrites, test flexible Na/Ca/Mg rather than treating Na as already measured. Very low-mass DQ single-star fits should be tested against unresolved-companion alternatives.

- **Held-out PS1 z:** 10/25 have |predicted minus observed z| >0.05 mag, including two of the eight interval-subset objects without the >10× neighbour flag. The z band was not fitted in the gri calibration. J0429 has residual −0.06098 mag, J0913 +0.03434, J1329 +0.00311 and J1323 −0.08149. These are additional shape/calibration diagnostics, not total-error significances; no Z-flag source is automatically rejected or corrected. See [held-out residuals](precision/candidate_recalibration/heldout_z.csv).

## Every-object comparison

Intervals below are signed Duv median [2.5%, 97.5%]. Flags are follow-up requirements, not a ranking. G = DESI interval unavailable; X = native Gaia unavailable; V = known variable; B = neighbour G flux ratio >10; R = full/truncated point-boundary switch; C = full/truncated interval-boundary-status switch; D = max pair Δuv ≥0.003; N = observed-night threshold disagreement; Z = held-out |z residual| >0.05 mag; U = unresolved SDSS convention; E = legacy positional identity. A dash means none of these selected flags, not clean data.

| Initial # / source | DESI conditional 95% | Gaia full formal 95% | Gaia truncated formal 95% | Max Δuv | z pred−obs (mag) | Flags | Prior atmosphere fit |
|---|---|---|---|---:|---:|---|---|
| 1. WDJ110541.59+724751.14<br>1078624858218235776 | +0.01201 [+0.01071, +0.01340] | +0.01339 [+0.00719, +0.01958] | +0.01743 [+0.01242, +0.02245] | 0.00837 | +0.01062 | C,D | DZ [logCa/He=-9.97]+[logH/He=-4.0] |
| 2. WDJ071637.37+621710.78<br>1099452803904038272 | -0.01182 [-0.01286, -0.01079] | -0.01252 [-0.01675, -0.00832] | -0.01308 [-0.01652, -0.00966] | 0.00156 | -0.05573 | Z | DQ [logC/He=-7.86] |
| 3. WDJ150038.15+134301.74<br>1182083542272959232 | +0.01552 [+0.01460, +0.01643] | +0.01173 [+0.00584, +0.01758] | +0.00087 [-0.00010, +0.00186] | 0.01754 | +0.05126 | B,R,D,Z | DZ [logCa/He=-9.70]+[logH/He=-6.0] |
| 4. Gaia DR3 1245262790370992256<br>1245262790370992256 | Unavailable | -0.01045 [-0.01257, -0.00834] | -0.01050 [-0.01260, -0.00839] | 0.00013 | Unavailable | G,V,U | No exact-ID fit in checked table |
| 5. WDJ155929.64+332431.72<br>1323443938325221376 | -0.02150 [-0.02299, -0.01996] | -0.02249 [-0.02831, -0.01675] | -0.02350 [-0.02925, -0.01790] | 0.00202 | +0.03293 | — | DQ [logC/He=-5.66] |
| 6. WDJ140155.42+390326.47<br>1496016553207149952 | -0.02255 [-0.02447, -0.02066] | -0.02098 [-0.02878, -0.01326] | -0.02318 [-0.03080, -0.01564] | 0.00452 | -0.03997 | D | DQ [logC/He=-6.00] |
| 7. PSO J186.4406+47.1036<br>1542337839923130624 | Unavailable | -0.02620 [-0.02974, -0.02270] | -0.02614 [-0.02965, -0.02265] | 0.00016 | Unavailable | G,E | No exact-ID fit in checked table |
| 8. WDJ125552.90+671244.24<br>1679189040001914880 | -0.02434 [-0.02585, -0.02281] | -0.02504 [-0.03118, -0.01902] | -0.02503 [-0.03101, -0.01913] | 0.00133 | -0.08967 | Z | DQH [logC/He=-5.82] |
| 9. WDJ125207.43+745756.93<br>1691957732959636608 | -0.01024 [-0.01116, -0.00934] | -0.01291 [-0.01999, -0.00586] | -0.01683 [-0.02224, -0.01138] | 0.00782 | +0.04040 | C,D,N | DQ [logC/He=-7.16] |
| 10. WDJ184104.75+483848.89<br>2119909923600264960 | -0.01388 [-0.01582, -0.01194] | -0.01306 [-0.02167, -0.00456] | -0.00313 [-0.00357, -0.00270] | 0.01075 | -0.01272 | R,D | DQ [logC/He=-6.35] |
| 11. WDJ014711.92-135843.93<br>2453225705329412480 | -0.02343 [-0.02429, -0.02255] | -0.01928 [-0.02783, -0.01094] | -0.02067 [-0.02908, -0.01249] | 0.00429 | +0.00040 | D | DQ [logC/He=-6.16] |
| 12. WDJ011124.78-053318.52<br>2482684508055379584 | -0.01075 [-0.01128, -0.01020] | -0.00854 [-0.01795, +0.00069] | -0.00218 [-0.00272, -0.00159] | 0.00858 | -0.06793 | D,N,Z | DQ [logC/He=-6.78] |
| 13. WDJ021739.29+011641.13<br>2513256394506328832 | -0.01118 [-0.01191, -0.01045] | -0.00910 [-0.01434, -0.00391] | -0.01145 [-0.01614, -0.00680] | 0.00442 | +0.09904 | R,D,Z | DQ [logC/He=-4.23] |
| 14. WDJ000602.95+025745.18<br>2739231150982741760 | +0.00614 [+0.00567, +0.00661] | +0.01055 [+0.00671, +0.01435] | +0.01070 [+0.00701, +0.01435] | 0.00455 | -0.01316 | D | DZ [logCa/He=-7.96]+[logH/He=-5.0] |
| 15. WDJ042944.71-035422.00<br>3204436719718449280 | +0.01280 [+0.01197, +0.01365] | +0.01300 [+0.00869, +0.01730] | +0.01493 [+0.01139, +0.01847] | 0.00322 | -0.06098 | C,D,Z | DZ [logCa/He=-9.56]+[logH/He=-6.0] |
| 16. WDJ132312.76-012923.67<br>3638333660492606976 | +0.02349 [+0.02094, +0.02599] | Unavailable | Unavailable | Unavailable | -0.08149 | X,Z,U | DZ: [logCa/He=-11.87]+[logH/He=-1.0] |
| 17. WDJ125802.76+050040.26<br>3705179706854089856 | -0.01117 [-0.01260, -0.00970] | -0.00746 [-0.01310, -0.00185] | -0.00954 [-0.01514, -0.00406] | 0.00404 | -0.06889 | D,Z | DQ [logC/He=-5.39] |
| 18. WDJ132942.69+003336.60<br>3711047662972690688 | -0.02267 [-0.02481, -0.02048] | -0.02444 [-0.03276, -0.01623] | -0.02234 [-0.03028, -0.01458] | 0.00676 | +0.00311 | D | DQ [logC/He=-6.14] |
| 19. WDJ134118.69+022737.01<br>3713218786120541824 | -0.01474 [-0.01507, -0.01440] | -0.01662 [-0.01792, -0.01532] | -0.01659 [-0.01788, -0.01531] | 0.00295 | -0.02131 | — | DQ [logC/He=-5.97] |
| 20. WDJ103113.86-013925.39<br>3782527364866017664 | -0.02399 [-0.02569, -0.02233] | -0.02612 [-0.03571, -0.01678] | -0.03229 [-0.04077, -0.02389] | 0.00865 | +0.06443 | D,Z | DQ [logC/He=-5.60] |
| 21. WDJ164234.26+080436.90<br>4445170067643613312 | -0.01073 [-0.01169, -0.00976] | -0.00869 [-0.01316, -0.00428] | -0.01071 [-0.01461, -0.00689] | 0.00260 | -0.03489 | R | DQ [logC/He=-5.97] |
| 22. WDJ170738.96+145320.12<br>4545191991882663936 | +0.01264 [+0.01111, +0.01411] | +0.01261 [+0.00635, +0.01879] | +0.01522 [+0.01019, +0.02027] | 0.00425 | -0.01608 | C,D | DZ: [logCa/He=-10.17]+[logH/He=-2.0] |
| 23. WDJ170205.24+150734.88<br>4545912820537587328 | -0.01012 [-0.01170, -0.00864] | -0.00757 [-0.01258, -0.00264] | -0.00032 [-0.00085, +0.00023] | 0.01017 | -0.08956 | D,Z | DQ [logC/He=-5.86] |
| 24. WDJ172725.31+211651.95<br>4555293235271174016 | -0.01860 [-0.01946, -0.01769] | -0.02008 [-0.02489, -0.01530] | -0.02004 [-0.02485, -0.01529] | 0.00198 | -0.04305 | — | DQ [logC/He=-5.69] |
| 25. WDJ110848.77+342536.63<br>761677269868775040 | -0.01818 [-0.01876, -0.01760] | -0.01769 [-0.02129, -0.01412] | -0.01803 [-0.02159, -0.01446] | 0.00247 | -0.04807 | B | DQ [logC/He=-5.67] |
| 26. WDJ091336.37+443405.41<br>818833831355548928 | +0.01908 [+0.01698, +0.02123] | +0.01927 [+0.01238, +0.02614] | +0.01637 [+0.00996, +0.02274] | 0.00489 | +0.03434 | C,D | DZ [logCa/He=-9.12]+[logH/He=-2.0] |
| 27. WDJ085113.75+424502.91<br>913810126798863232 | -0.01190 [-0.01397, -0.00988] | -0.01098 [-0.01862, -0.00342] | -0.00416 [-0.00458, -0.00374] | 0.00778 | -0.01475 | R,D | DQ [logC/He=-7.42] |

## Per-object next checks

| Source | Next work |
|---|---|
| 1078624858218235776 | Model reconstruction/continuum bias with held-out spectral features; Compare prior atmosphere fit with free abundances and calibration nuisance terms |
| 1099452803904038272 | Held-out PS1 z residual: inspect red shape, masks, and calibration beyond fitted gri; Compare prior atmosphere fit with free abundances and calibration nuisance terms |
| 1182083542272959232 | Field-image and PSF-wing contamination test; Held-out PS1 z residual: inspect red shape, masks, and calibration beyond fitted gri; Model reconstruction/continuum bias with held-out spectral features; Compare prior atmosphere fit with free abundances and calibration nuisance terms |
| 1245262790370992256 | Epoch-resolved classification and colour; Resolve original SDSS flux convention; Quality-checked independent photometric anchors; Resolve physical classification before atmosphere interpretation |
| 1323443938325221376 | Compare prior atmosphere fit with free abundances and calibration nuisance terms |
| 1496016553207149952 | Model reconstruction/continuum bias with held-out spectral features; Compare prior atmosphere fit with free abundances and calibration nuisance terms |
| 1542337839923130624 | Quality-checked independent photometric anchors; Proper-motion/epoch identity verification; Resolve physical classification before atmosphere interpretation |
| 1679189040001914880 | Held-out PS1 z residual: inspect red shape, masks, and calibration beyond fitted gri; Compare prior atmosphere fit with free abundances and calibration nuisance terms |
| 1691957732959636608 | Repeat-night calibration and correlated-noise model; Model reconstruction/continuum bias with held-out spectral features; Compare prior atmosphere fit with free abundances and calibration nuisance terms |
| 2119909923600264960 | Model reconstruction/continuum bias with held-out spectral features; Compare prior atmosphere fit with free abundances and calibration nuisance terms |
| 2453225705329412480 | Model reconstruction/continuum bias with held-out spectral features; Compare prior atmosphere fit with free abundances and calibration nuisance terms |
| 2482684508055379584 | Repeat-night calibration and correlated-noise model; Held-out PS1 z residual: inspect red shape, masks, and calibration beyond fitted gri; Model reconstruction/continuum bias with held-out spectral features; Compare prior atmosphere fit with free abundances and calibration nuisance terms |
| 2513256394506328832 | Held-out PS1 z residual: inspect red shape, masks, and calibration beyond fitted gri; Model reconstruction/continuum bias with held-out spectral features; Compare prior atmosphere fit with free abundances and calibration nuisance terms |
| 2739231150982741760 | Model reconstruction/continuum bias with held-out spectral features; Compare prior atmosphere fit with free abundances and calibration nuisance terms |
| 3204436719718449280 | Held-out PS1 z residual: inspect red shape, masks, and calibration beyond fitted gri; Model reconstruction/continuum bias with held-out spectral features; Compare prior atmosphere fit with free abundances and calibration nuisance terms |
| 3638333660492606976 | Resolve original SDSS flux convention; Independent ground spectrum with verified units; Held-out PS1 z residual: inspect red shape, masks, and calibration beyond fitted gri; Compare prior atmosphere fit with free abundances and calibration nuisance terms |
| 3705179706854089856 | Held-out PS1 z residual: inspect red shape, masks, and calibration beyond fitted gri; Model reconstruction/continuum bias with held-out spectral features; Compare prior atmosphere fit with free abundances and calibration nuisance terms |
| 3711047662972690688 | Model reconstruction/continuum bias with held-out spectral features; Compare prior atmosphere fit with free abundances and calibration nuisance terms |
| 3713218786120541824 | Compare prior atmosphere fit with free abundances and calibration nuisance terms |
| 3782527364866017664 | Held-out PS1 z residual: inspect red shape, masks, and calibration beyond fitted gri; Model reconstruction/continuum bias with held-out spectral features; Compare prior atmosphere fit with free abundances and calibration nuisance terms |
| 4445170067643613312 | Model reconstruction/continuum bias with held-out spectral features; Compare prior atmosphere fit with free abundances and calibration nuisance terms |
| 4545191991882663936 | Model reconstruction/continuum bias with held-out spectral features; Compare prior atmosphere fit with free abundances and calibration nuisance terms |
| 4545912820537587328 | Held-out PS1 z residual: inspect red shape, masks, and calibration beyond fitted gri; Model reconstruction/continuum bias with held-out spectral features; Compare prior atmosphere fit with free abundances and calibration nuisance terms |
| 4555293235271174016 | Compare prior atmosphere fit with free abundances and calibration nuisance terms |
| 761677269868775040 | Field-image and PSF-wing contamination test; Compare prior atmosphere fit with free abundances and calibration nuisance terms |
| 818833831355548928 | Model reconstruction/continuum bias with held-out spectral features; Compare prior atmosphere fit with free abundances and calibration nuisance terms |
| 913810126798863232 | Model reconstruction/continuum bias with held-out spectral features; Compare prior atmosphere fit with free abundances and calibration nuisance terms |

## Reproduction

Run from the repository root:

    MPLCONFIGDIR=/tmp/wish_green_mpl .venv-research/bin/python research/candidate_followup.py

The script performs only local string-ID joins, arithmetic diagnostics and plotting. It reads the listed upstream source files and writes the CSV, JSON, PNG, SVG and this report; it does not alter the upstream analysis or retrieve new data. The original source inputs and this script are SHA256-recorded in JSON. The counts are conditional on the frozen input snapshots and the stated exploration rules.

### 日本語の要点

初期27候補を全件保持し、DESIの条件付き95%区間とGaiaのfull/truncated両再構成の形式的95%区間を並べた。3区間とも同じ側で|Duv|>0.01となる9件は、発見確率を統合した結果ではない。Gaia明るい近傍1件を注意対象として分けると8件で、すべて負Duv側である。XP再構成依存、別夜の閾値不一致、既知変光、SDSS単位未解決、先行大気モデルを天体ごとに明記した。較正に使わなかったPS1 zでは25件中10件に0.05 magを超える残差があり、8件の中にも2件含まれる。これは追加較正診断であり、有意差や棄却判定ではない。J1323は独立SDSS色支持を取り下げ、DESI単独候補として次の観測を要求する。
