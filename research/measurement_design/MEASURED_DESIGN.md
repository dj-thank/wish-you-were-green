# New observed photometry: analysis decisions

This diagnostic is separate from the prospective filter-selection experiment
in DESIGN.md. The full frozen 25-candidate cohort is retained, with all 450
survey/band availability and quality decisions from independent_photometry.

1. First predict each fully covered natural passband from the frozen DESI + PS1
   gri spectrum, before fitting any SkyMapper/J-PLUS measurement. Retain signed
   valid pixels, the previous narrow sky mask, and every tabulated passband
   sample. Missing/sentinel magnitudes are never upper limits. Incomplete
   spectral coverage is never repaired by extrapolation.
2. Primary adoption uses the upstream strict quality flag, which is independent
   of colour residuals. J-PLUS's recommended zero-point error is already added
   to the measurement error; its published zero-point offset is already applied
   to the magnitude and must not be applied twice. SkyMapper uses the published
   PSF mean error unchanged. The two surveys have different photon observations,
   while Gaia calibration and J-PLUS's PS1-r/white-dwarf-locus anchors prevent
   interpreting the full collection as statistically independent data.
3. Compute minimum continuous cubic-spline multiplicative shape changes to fit
   all original PS1 griz boxes, and to fit those boxes plus the adopted additional
   measurements. Use 400, 800 and 1600 Å knots. Compute unconstrained photometry,
   strict green, and the two strict opposite-colour branches with the same
   normalized 0.005 guard as the prospective design. Allow an optimization cap
   of 95% only to record a minimum or a clearly unavailable bounded solution;
   large minima do not imply a plausible instrument error or a plausible
   physical stellar atmosphere.
4. Repeat joint fits with an additional 0.02 mag half-width added to every
   additional-survey error box, leaving the original PS1 boxes unchanged. This
   is an explicit stress test of the bounds, not an estimated zero-point error,
   posterior or joint confidence level. Per-band boxes permit correlated shifts
   but do not estimate or constrain their covariance.
5. For the predeclared primary target J0429−0354 only, also run a labelled
   sensitivity case admitting SkyMapper's official-good g mean, which fails
   the stricter all-zero masked-pixel rule. Never relabel it as strict quality.
6. Every combined fit consumes the new measurements. Those bands cease to be
   held-out validation of that fitted spectrum. Baseline predictions remain
   the distinct pre-fit check. A mismatch can reflect flux calibration, spectral
   noise, filter response/zero-point error, blending, epoch differences or an
   inadequate smooth shape family; it is not automatically variability or new
   opacity physics.

Publish source/code hashes, all actual measurements and exclusions, direct
pre-fit predictions, optimization attempts, analytic-extrema witnesses and
numerical dual lower bounds. Review the plotted measurements object by object.
