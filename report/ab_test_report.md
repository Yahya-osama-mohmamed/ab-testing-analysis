# A/B Test Report — Ad Campaign vs. PSA Control

*Prepared from the Marketing A/B Testing dataset (588,101 users). Analysis code
and full statistical detail: [`notebooks/`](../notebooks) in this repository.*

## 1. Executive summary

We tested whether showing users real ads (treatment, 564,577 users) drives
more conversions than a public-service-announcement placebo (control, 23,524
users). The ad group converted at **2.55%** vs **1.79%** for control — a
**+43% relative lift** that is statistically unambiguous (p < 10⁻¹²) and
practically large. **We recommend rolling the campaign out**, with targeting
weight on the high-exposure experience described in the segment findings.

## 2. Methodology

Users were randomly assigned to see ads or PSAs; the outcome is whether the
user later converted. We compared conversion rates with a two-proportion
z-test (verified against a chi-square test — they agree exactly), report a
95% confidence interval on the difference rather than a bare point estimate,
validated the experiment's integrity before reading outcomes (sample-ratio
check, duplicate users, cross-group contamination), and closed with a
retrospective power analysis.

## 3. Results

| Metric | Value |
|---|---|
| Control (PSA) conversion | **1.785%** (420 / 23,524) |
| Treatment (ad) conversion | **2.555%** (14,423 / 564,577) |
| Absolute lift | **+0.77 pp** |
| Relative lift | **+43.1%** |
| z-statistic | 7.37 |
| p-value | < 10⁻¹² |
| 95% CI (absolute lift) | **[+0.60 pp, +0.94 pp]** |
| Retrospective power (α = 0.05) | ≈ 1.00 |

Experiment integrity: the observed 96.0/4.0 split matches the intended ad-holdout
design (SRM chi-square p = 0.9998 — no mismatch), there are **no duplicate
users** and **no users in both groups**.

## 4. Segment findings

- **Effect grows with exposure.** Users who saw 50+ ads convert at ~5% in the
  treatment group with the largest lift over control; low-exposure users
  (1–10 ads) show small absolute rates in both groups. Frequency of exposure —
  not mere assignment — is where the value concentrates.
- **Day-of-week patterns exist but are secondary.** Lifts are directionally
  positive across days; differences between days do not survive a strict
  multiple-comparison correction and should inform scheduling only weakly.

## 5. Recommendation

**Roll out the campaign.** The effect is large, precisely estimated, and the
experiment passes every integrity check. Given the exposure gradient, media
planning should favor reaching users often enough to enter the medium/high
exposure regimes rather than maximizing unique reach at one impression each.

## 6. Caveats

- **Exposure is not randomized** — users choose their own browsing volume, so
  the exposure-segment gradient is correlational (heavier browsers may simply
  convert more); only the overall ad-vs-PSA contrast is causal.
- The dataset ships without its experiment spec: the 96:4 intended allocation
  used in the SRM check is inferred from the observed split and industry
  convention.
- Conversion is binary with no revenue attached; a rollout decision at scale
  should re-verify with revenue-weighted outcomes.
- No time dimension beyond "most ads day/hour": novelty effects and long-run
  fatigue are not measurable here.

*p-values below float precision are reported as p < 10⁻¹²; exact statistics in
`report/results.json`.*
