"""Tests for market presets and overrides."""
from __future__ import annotations

from datetime import date

import pytest

from erp_synth.markets import MARKETS, get_market, holidays_for_year

REQUIRED_KEYS = {
    "name", "faker_locale", "currency", "vat_rate", "freight_flat",
    "freight_free_above", "inflation_default", "country_pool",
    "payment_methods", "month_factor", "dow_factor", "holiday_builder",
}


@pytest.mark.parametrize("market_key", ["us", "gcc", "eu"])
def test_each_market_has_required_keys(market_key):
    cfg = get_market(market_key)
    missing = REQUIRED_KEYS - cfg.keys()
    assert not missing, f"{market_key} missing keys: {missing}"


def test_unknown_market_raises():
    with pytest.raises(ValueError, match="Unknown market"):
        get_market("antarctica")


def test_vat_override():
    cfg = get_market("us", vat_rate=0.123)
    assert cfg["vat_rate"] == 0.123


def test_currency_override():
    cfg = get_market("us", currency="JPY")
    assert cfg["currency"] == "JPY"


def test_inflation_override():
    cfg = get_market("us", annual_inflation=0.05)
    assert cfg["inflation_default"] == 0.05


@pytest.mark.parametrize("market_key", ["us", "gcc", "eu"])
def test_month_factor_covers_all_months(market_key):
    cfg = get_market(market_key)
    for month in range(1, 13):
        assert month in cfg["month_factor"]
        assert cfg["month_factor"][month] > 0


def test_us_black_friday_is_a_holiday():
    cfg = get_market("us")
    bumps = holidays_for_year(cfg, 2024)
    # Black Friday 2024 is Nov 29
    assert date(2024, 11, 29) in bumps
    assert bumps[date(2024, 11, 29)] >= 2.0


def test_gcc_has_eid_bump():
    cfg = get_market("gcc")
    bumps = holidays_for_year(cfg, 2024)
    # Eid al-Fitr 2024 starts April 10 — eve days should have bumps
    eid_dates = [d for d, m in bumps.items() if d.month == 4 and m >= 1.5]
    assert eid_dates, "expected Eid al-Fitr bumps in April 2024"


def test_holidays_cached_per_year():
    cfg = get_market("us")
    a = holidays_for_year(cfg, 2024)
    b = holidays_for_year(cfg, 2024)
    assert a is b  # same dict instance, came from cache


def test_markets_dict_is_immutable_to_callers():
    """get_market must return a copy, not a reference into MARKETS."""
    get_market("us", vat_rate=0.01)
    assert MARKETS["us"]["vat_rate"] != 0.01
