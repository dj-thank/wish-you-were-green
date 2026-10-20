# Additional photometry and colour identifiability: fixed analysis design

Started 2026-10-19 UTC / 2026-10-20 JST, from commit
`70f0d592d880ead69b5b6623e3c4ceec4affcd43`.

This is a follow-up to the retained measured-PS1 error-box experiment, not a
new population sample or an estimate of the true calibration-error distribution.
The primary object is the previously declared J0429−0354 (Gaia
3204436719718449280). J0913+4434 is a comparison object. Original spectra,
photometry, masks and numerical products remain unchanged.

## Questions

1. Do independently observed catalogue measurements, in their actual natural
   passbands and with explicit quality/coverage rules, reduce the colour set?
2. Can proposed extra filters distinguish *all* permitted strict opposite-colour
   pairs, rather than merely distinguish the two previously saved witnesses?

## Data and selection

- Use the frozen calibrated DESI arrays and original PS1 griz reported-error
  boxes from `research/calibration_followup/`.
- Obtain total-system SkyMapper and J-PLUS responses from the public SVO Filter
  Profile Service. Select SkyMapper's six named filters and the twelve J-PLUS
  system responses; do not substitute the separate `_filter` transmission-only
  entries for total system throughput.
- Retain the entire tabulated response. If the observed wavelength interval
  cannot bracket its support, mark that band unavailable; do not extend the
  observed spectrum or silently trim throughput tails.
- The SVO J-PLUS tables stop at small nonzero responses (0.0001–0.0006).
  Preserve every table sample and append zero response 1 Å outside each end,
  closing only the finite response table. Repeat the primary joint-band
  calculations with 10 Å closure. This numerical convention is explicit and
  is not a claim about unmeasured physical throughput tails. Spectrum coverage
  must include the closure too. SkyMapper tables already have zero endpoints.
- Independent catalogue records are acquired by the separate
  `research/independent_photometry/` investigation, using exact IDs, epoch-aware
  position checks and documented flags. An independent exposure does not imply
  an independent photometric zero point. Measured and hypothetical data are
  always labelled separately.

## Conditional spectral space

Use positive multiplicative cubic B-splines, keeping signed finite input pixels,
the existing narrow-sky mask, and positive integrated XYZ. Primary knot spacing
is 800 Å; 400 and 1600 Å are sensitivity cases. Relative shape budgets are 5%
and 10%; these are experimental assumptions, not measured error quantiles.

Strict green means both `(G-R)/S0 >= h` and `(G-B)/S0 >= h`, where `S0` is the
fixed baseline maximum absolute linear-sRGB component. Strict opposite colour
is the union `(R-G)/S0 >= h` or `(B-G)/S0 >= h`. Use `h=0.005`; the interval
between these strict classes is deliberately left undecided. This is a channel
ordering guard band, not a human colour-discrimination threshold.

## Whole-set measurement design

For two independently variable spectra in the green and opposite sets, minimize
the largest absolute difference of their proposed band fluxes, each normalized
to the same baseline band flux. This is a coupled linear programme, with the
original PS1 error boxes imposed on both spectra. The two opposite branches
must be solved separately and their union handled explicitly.

Call the minimum `d`. A result `d=0` supplies a strict opposite-colour pair that
even exact proposed-band fluxes cannot distinguish at that common flux vector.
It does not say every possible future measurement is ambiguous. For `d>0`,
uniform additional-flux error boxes with half-width less than `d/2` cannot
intersect both strict classes. This is conditional on the declared spectral
space, guard band and hard error bounds. It is not a posterior, survey
performance forecast, or universal observational requirement.

Use real single bands and system band sets. Existing PS1 griz measured again
is a control. Ideal directly measured X/Y/Z integrals are a separate mathematical
positive control, explicitly not a catalogue or a real survey passband.

Bound each spline at analytic derivative roots and endpoints, adding any
violating extrema to the linear programme. Reintegrate accepted witnesses.
As a numerical acceleration, a coefficient-bounded spline may supply a
continuous feasible witness at the finite-grid lower bound. This coefficient
condition is sufficient, not necessary; a failure in that smaller space is
never treated as failure of the full spectral set. The lower bound must still
come from the original outer problem's dual. If a solver reports a numerical
failure, retry a documented HiGHS algorithm/presolve configuration without
changing the scientific constraints or tolerances.
Record primal residuals, dual stationarity/sign/objective residuals, the
finite-constraint lower bound and continuous feasible-witness upper bound.
Floating-point checks are not formal interval-arithmetic certificates.

## Interpretation and reproducibility

Publish all attempted bands and exclusions, both feasible and unavailable
cases, measured catalogue provenance, source/code hashes, witness coefficients
and read-only offline verification. A proposed filter is selected analytically;
its performance is not subsequently described as an independent discovery.
