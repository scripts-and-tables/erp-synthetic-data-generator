"""Tests for the daily seasonality multiplier."""
from __future__ import annotations

from datetime import date

from erp_synth.seasonality import combined_multiplier


def test_multiplier_is_positive_year_round(market_us):
    for month in range(1, 13):
        m = combined_multiplier(date(2024, month, 15), market_us)
        assert m > 0


def test_us_black_friday_is_a_bump(market_us):
    bf = combined_multiplier(date(2024, 11, 29), market_us)
    plain_tuesday = combined_multiplier(date(2024, 2, 13), market_us)
    assert bf > 2.0
    assert bf > plain_tuesday * 2


def test_us_christmas_eve_is_a_bump(market_us):
    cev = combined_multiplier(date(2024, 12, 24), market_us)
    plain_tuesday = combined_multiplier(date(2024, 2, 13), market_us)
    assert cev > plain_tuesday * 1.5


def test_weekend_uplift_us(market_us):
    # 2024-02-10 is a Saturday; 2024-02-13 is a Tuesday.
    sat = combined_multiplier(date(2024, 2, 10), market_us)
    tue = combined_multiplier(date(2024, 2, 13), market_us)
    assert sat > tue


def test_weekend_uplift_gcc(market_gcc):
    # 2024-02-09 is a Friday (GCC weekend); 2024-02-13 is a Tuesday
    fri = combined_multiplier(date(2024, 2, 9), market_gcc)
    tue = combined_multiplier(date(2024, 2, 13), market_gcc)
    assert fri > tue


def test_gcc_ramadan_window_elevated(market_gcc):
    # Ramadan 2024 starts March 11; mid-window day should have a notable bump
    ramadan_day = combined_multiplier(date(2024, 3, 25), market_gcc)
    plain_february_tue = combined_multiplier(date(2024, 2, 13), market_gcc)
    assert ramadan_day > plain_february_tue


def test_eu_august_dip(market_eu):
    aug = combined_multiplier(date(2024, 8, 13), market_eu)
    nov = combined_multiplier(date(2024, 11, 13), market_eu)
    assert aug < nov  # August holidays in EU
