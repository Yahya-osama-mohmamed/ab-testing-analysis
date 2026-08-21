"""Tests for the statistics the report's conclusions rest on.

These are pure functions, so they can be checked against cases where the right
answer is known independently: a perfectly balanced split must not trigger SRM,
an obviously broken one must, identical conversion rates must not be
significant, and a confidence interval must bracket the difference it describes.

The value here is guarding the claims, not the code. If `two_proportion_ztest`
silently changed, the headline "+43.1% lift, 95% CI [+0.60pp, +0.94pp]" would
change with it and nothing would say so.
"""

import math

import pytest

from src.stats_utils import (
    chi_square_independence,
    required_sample_size,
    retrospective_power,
    srm_check,
    two_proportion_ztest,
)


class TestSrmCheck:
    def test_even_split_is_not_a_mismatch(self):
        r = srm_check(50_000, 50_000)
        assert r["srm_detected"] is False
        assert r["p_value"] > 0.99
        assert r["observed_ratio"] == pytest.approx(0.5)

    def test_broken_assignment_is_detected(self):
        """A 60/40 split from an intended 50/50 at this scale is not chance."""
        r = srm_check(60_000, 40_000)
        assert r["srm_detected"] is True
        assert r["p_value"] < 1e-10

    def test_intended_uneven_split_passes(self):
        """The real experiment is a 96/4 ad-holdout. Judged against a 50/50
        expectation it looks catastrophic; against its own design it is fine."""
        assert srm_check(96_000, 4_000, expected_ratio=0.5)["srm_detected"] is True
        assert srm_check(96_000, 4_000, expected_ratio=0.96)["srm_detected"] is False

    def test_small_imbalance_is_tolerated(self):
        r = srm_check(50_100, 49_900)
        assert r["srm_detected"] is False


class TestTwoProportionZtest:
    def test_identical_rates_are_not_significant(self):
        r = two_proportion_ztest(1_000, 50_000, 1_000, 50_000)
        assert r["p_value"] == pytest.approx(1.0)
        assert r["abs_diff"] == pytest.approx(0.0)
        assert r["z_stat"] == pytest.approx(0.0)

    def test_large_clear_difference_is_significant(self):
        r = two_proportion_ztest(2_000, 50_000, 1_000, 50_000)
        assert r["p_value"] < 1e-10
        assert r["rel_lift"] == pytest.approx(1.0)  # double the rate

    def test_confidence_interval_brackets_the_difference(self):
        r = two_proportion_ztest(2_000, 50_000, 1_000, 50_000)
        assert r["ci95_low"] < r["abs_diff"] < r["ci95_high"]
        # A significant result must not have an interval straddling zero.
        assert r["ci95_low"] > 0

    def test_direction_is_signed_not_absolute(self):
        """A worse treatment must report a negative lift, not its magnitude."""
        r = two_proportion_ztest(500, 50_000, 1_000, 50_000)
        assert r["abs_diff"] < 0
        assert r["rel_lift"] < 0

    def test_reproduces_the_published_headline(self):
        """The numbers the report and the README quote."""
        r = two_proportion_ztest(14_423, 564_577, 420, 23_524)
        assert r["rate_a"] * 100 == pytest.approx(2.555, abs=0.001)
        assert r["rate_b"] * 100 == pytest.approx(1.785, abs=0.001)
        assert r["rel_lift"] * 100 == pytest.approx(43.1, abs=0.1)
        assert r["p_value"] < 1e-10
        assert r["ci95_low"] * 100 == pytest.approx(0.60, abs=0.02)
        assert r["ci95_high"] * 100 == pytest.approx(0.94, abs=0.02)


class TestChiSquareIndependence:
    def test_agrees_with_the_ztest(self):
        """On a 2x2 table chi-square and the pooled z-test are the same test:
        chi2 should equal z squared."""
        z = two_proportion_ztest(2_000, 50_000, 1_000, 50_000)
        c = chi_square_independence(2_000, 50_000, 1_000, 50_000)
        assert c["chi2"] == pytest.approx(z["z_stat"] ** 2, rel=0.01)
        assert c["dof"] == 1

    def test_identical_rates_are_not_significant(self):
        assert chi_square_independence(1_000, 50_000, 1_000, 50_000)["p_value"] > 0.9


class TestRetrospectivePower:
    def test_large_effect_and_sample_is_fully_powered(self):
        r = retrospective_power(0.01785, 0.02555, 23_524, 564_577)
        assert r["power"] > 0.99

    def test_tiny_sample_is_underpowered(self):
        """The case that matters: a null result here means "we could not have
        seen it anyway", not "there is no effect"."""
        r = retrospective_power(0.01785, 0.02555, 50, 50)
        assert r["power"] < 0.3

    def test_no_effect_gives_no_power_beyond_alpha(self):
        r = retrospective_power(0.02, 0.02, 10_000, 10_000)
        assert r["effect_size_h"] == pytest.approx(0.0, abs=1e-12)
        assert r["power"] == pytest.approx(r["alpha"], abs=0.01)


class TestRequiredSampleSize:
    def test_smaller_effects_need_more_users(self):
        big = required_sample_size(0.02, 0.20)["n_per_group"]
        small = required_sample_size(0.02, 0.05)["n_per_group"]
        assert small > big

    def test_quartering_the_effect_roughly_multiplies_n_by_16(self):
        """Sample size scales with 1/effect^2, so a 4x smaller effect needs
        about 16x the users."""
        n1 = required_sample_size(0.02, 0.20)["n_per_group"]
        n2 = required_sample_size(0.02, 0.05)["n_per_group"]
        assert 12 < n2 / n1 < 20

    def test_returns_a_whole_number_of_users(self):
        n = required_sample_size(0.02, 0.10)["n_per_group"]
        assert isinstance(n, int)
        assert n > 0
        assert not math.isnan(n)
