"""Reusable statistics for A/B test analysis.

Everything returns plain dictionaries so notebooks can display results as
tables, and every function states its assumptions in the docstring.
"""

import numpy as np
from scipy import stats
from statsmodels.stats.power import NormalIndPower
from statsmodels.stats.proportion import (
    confint_proportions_2indep, proportion_effectsize, proportions_ztest,
)


def srm_check(n_a: int, n_b: int, expected_ratio: float = 0.5) -> dict:
    """Sample Ratio Mismatch check (chi-square goodness of fit).

    Tests whether the observed group split matches the intended allocation.
    A failing SRM check means the assignment mechanism itself is broken
    (bot filtering, logging loss, redirect bugs) and the experiment's outcome
    comparison cannot be trusted, no matter how significant it looks.
    """
    total = n_a + n_b
    expected = [total * expected_ratio, total * (1 - expected_ratio)]
    chi2, p = stats.chisquare([n_a, n_b], expected)
    return {
        "n_a": n_a, "n_b": n_b,
        "observed_ratio": round(n_a / total, 4),
        "expected_ratio": expected_ratio,
        "chi2": round(float(chi2), 2),
        "p_value": float(p),
        "srm_detected": bool(p < 0.001),  # conventional strict alpha for SRM
    }


def two_proportion_ztest(conv_a: int, n_a: int, conv_b: int, n_b: int) -> dict:
    """Two-proportion z-test (pooled), with a 95% CI on the difference.

    Appropriate when n*p and n*(1-p) are large (thousands here). The CI uses
    the Newcombe/statsmodels unpooled method — the interval a stakeholder can
    read as "the true lift is somewhere in here".
    """
    z, p = proportions_ztest([conv_a, conv_b], [n_a, n_b])
    rate_a, rate_b = conv_a / n_a, conv_b / n_b
    ci_low, ci_high = confint_proportions_2indep(
        conv_a, n_a, conv_b, n_b, method="wald")
    return {
        "rate_a": rate_a, "rate_b": rate_b,
        "abs_diff": rate_a - rate_b,
        "rel_lift": (rate_a - rate_b) / rate_b if rate_b else np.nan,
        "z_stat": float(z), "p_value": float(p),
        "ci95_low": float(ci_low), "ci95_high": float(ci_high),
    }


def chi_square_independence(conv_a: int, n_a: int, conv_b: int, n_b: int) -> dict:
    """Chi-square test of independence on the 2x2 outcome table.

    Mathematically equivalent to the two-sided pooled z-test (chi2 = z^2) for
    a 2x2 table — we run both to demonstrate the equivalence. Prefer the
    z-test when you need a one-sided alternative or a CI on the difference;
    prefer chi-square when comparing more than two groups.
    """
    table = np.array([[conv_a, n_a - conv_a], [conv_b, n_b - conv_b]])
    chi2, p, dof, _ = stats.chi2_contingency(table, correction=False)
    return {"chi2": float(chi2), "p_value": float(p), "dof": int(dof)}


def retrospective_power(rate_control: float, rate_test: float,
                        n_control: int, n_test: int, alpha: float = 0.05) -> dict:
    """Retrospective power: probability this design detects the observed
    effect size if it is real. Low power on a null result means "we couldn't
    have seen it anyway", not "there is no effect"."""
    effect = proportion_effectsize(rate_test, rate_control)
    power = NormalIndPower().solve_power(
        effect_size=effect, nobs1=n_test, ratio=n_control / n_test, alpha=alpha)
    return {"effect_size_h": float(effect), "power": float(power), "alpha": alpha}


def required_sample_size(rate_control: float, mde_rel: float,
                         alpha: float = 0.05, power: float = 0.8) -> dict:
    """Per-group sample size needed to detect a relative lift of `mde_rel`."""
    rate_target = rate_control * (1 + mde_rel)
    effect = proportion_effectsize(rate_target, rate_control)
    n = NormalIndPower().solve_power(effect_size=effect, alpha=alpha,
                                     power=power, ratio=1.0)
    return {"mde_rel": mde_rel, "n_per_group": int(np.ceil(n))}
