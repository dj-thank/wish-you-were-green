# Independent numerical review of the coupled colour-set design

This review independently reconstructs **six declared J0429−0354 design cases**
from the frozen spectral pixels and responses. All six replayed successfully
after the correction that separates a dual lower bound from a continuous
witness upper bound. It is a numerical and code review within this
ChatGPT-assisted project, not external astronomical peer review or a new
physical observation. The complete records, actual source/code hashes and
environment are in [review_results.json](review_results.json).

## Scope and what is independent

The cases use Gaia DR3 3204436719718449280, 400 or 800 Å cubic-spline spacing,
a 5% multiplicative-shape budget, a 0.005 channel-ordering guard, and the original
measured PS1 griz boxes on **both** spectra. The proposed measurements are the
ten fully covered J-PLUS bands, those ten bands plus PS1 griz, or ideal X/Y/Z
integrals. Only the feasible G−R opposite branch is numerically reconstructed
here. The [full production verifier](../verify_outputs.py) retains responsibility
for the complete design census and the infeasible G−B branches.

[run_review.py](run_review.py) separately assembles the two spectrum blocks,
transforms magnitude intervals to flux inequalities, computes the CIE integrals
with direct trapezoidal quadrature, reintegrates each accepted spectrum through
the response curves, checks analytic derivative roots and endpoints, checks
the stored primal/dual residuals and signs, and solves a fresh dual-simplex LP
on each saved outer constraint grid. It does not call the production constraint
assembler or coupled solver.

The target loader, cleaned pixels, spline knots, response tables, SciPy and
speclite are shared. Consequently this review can find assembly, sign,
integration and reporting inconsistencies, but cannot independently establish
the absolute spectrum, passband accuracy, calibration-error distribution or
adequacy of the selected spline space.

## Replayed bounds

All numbers below are **fractions of fixed baseline band flux**, not magnitude
errors or probabilities. The numerical uniform-error sufficient half-width is
taken from the nonnegative dual lower bound divided by two; values at or below
the stated `2e-7` separation-check tolerance are reported as unseparated.

| Knot spacing | Proposed measurement set | Outer dual lower bound | Direct continuous-witness distance | Sufficient numerical half-width |
|---|---|---:|---:|---:|
| 400 Å | J-PLUS, ten covered bands | 0 | 6.66e−16 | 0; unseparated |
| 400 Å | PS1 griz plus those ten bands | 0 | 1.03e−11 | 0; unseparated |
| 400 Å | Ideal XYZ | 0.001349300853 | 0.001349300876 | 0.000674650427 |
| 800 Å | J-PLUS, ten covered bands | 0.002592829490 | 0.002592829490 | 0.001296414745 |
| 800 Å | PS1 griz plus those ten bands | 0.003028430483 | 0.003028430483 | 0.001514215241 |
| 800 Å | Ideal XYZ | 0.001349300856 | 0.001349300856 | 0.000674650428 |

The largest independently reconstructed primal residual was `7.01e-11`,
dual stationarity residual `1.22e-11`, and absolute primal–dual objective gap
`2.07e-12`. The stored 800 Å J-PLUS witnesses exceed the nominal 5% continuous
budget by at most approximately `1.65e-9`, within the explicitly declared
numerical tolerance. These are floating-point residual checks; they are not
formal interval-arithmetic certificates.

## Review findings and reporting correction

No sign error was found in the PS1 box transformation, strict-colour blocks,
free spline-coefficient duals, or the nonnegative distance bound. The optional
coefficient-hull solve supplies a continuous feasible witness while retaining
the original outer dual lower bound. Its failure is not used to declare the
full continuous problem infeasible.

The first review identified a reporting distinction: a feasible witness gives
an **upper** bound on the minimum separation. A sufficient uniform-error
condition must use a **lower** bound. The production branch records now expose
both halves, and the main summary uses the dual side and reports zero when the
separation is below numerical checking tolerance. This review explicitly
rechecks those current fields. The mathematical objective and the selected
observations did not change.

For interpretation, the guard is relative to a fixed baseline linear-RGB scale,
not a perceptual discrimination threshold. A zero minimum demonstrates that
one common vector of proposed fluxes admits both strict colours; it does not
make every future measurement ambiguous. Positive separation applies only to
the declared continuous spectral set, original measured boxes and hard error
bounds. Ideal XYZ is a mathematical control, not a real survey measurement.
The per-band boxes are not a simultaneous confidence region. No universal
precision requirement, novelty claim, posterior probability or empirical
calibration guarantee follows from this calculation. See the full
[prospective design](../DESIGN.md) and the separate
[actually measured constraints](../MEASURED_DESIGN.md).

## Reproduction

From the repository root in the project's core numerical environment:

```bash
python research/measurement_design/independent_review/run_review.py
```

The module also exposes `verify(root)`, which checks the saved input hashes and
replays the six cases, returning `summary` and `verified_file_sha256` for the
project's combined offline verification. It requires the stored compact target,
profile and certificate files and makes no network requests.

The rerun reviewed `design_full.json` SHA-256
`7ebce807c18b9f975717c650fa223e71c2bc8223bd88b843ff75cbaa0ac23b49`.
The earlier temporary review used
`4848068e8878d05cba79c2f2000f07c03905e7f7a3f93435b43ef20c3a562a2e`
before the reporting correction. The current JSON retains the exact reviewed
code/data identities so later changes can be detected.
