"""Tests for inflation + discount pricing math."""
from __future__ import annotations

from datetime import date

import pytest

from erp_synth.pricing import inflated_list_price, unit_price_at_sale


def test_inflated_price_unchanged_at_listing_date():
    p = inflated_list_price(100.0, listed_from=date(2020, 1, 1),
                            sale_date=date(2020, 1, 1), annual_inflation=0.03)
    assert p == pytest.approx(100.0)


def test_inflation_grows_price_over_a_year():
    p = inflated_list_price(100.0, listed_from=date(2020, 1, 1),
                            sale_date=date(2021, 1, 1), annual_inflation=0.03)
    assert p == pytest.approx(103.0, rel=0.01)


def test_inflation_compounds_multi_year():
    p = inflated_list_price(100.0, listed_from=date(2020, 1, 1),
                            sale_date=date(2030, 1, 1), annual_inflation=0.03)
    # 1.03**10 = 1.3439
    assert p == pytest.approx(134.39, rel=0.01)


def test_zero_inflation_no_change():
    p = inflated_list_price(50.0, listed_from=date(2020, 1, 1),
                            sale_date=date(2025, 1, 1), annual_inflation=0.0)
    assert p == pytest.approx(50.0)


def test_sale_before_listing_returns_list_price():
    """Edge case: simulator sometimes hits a sale_date before listing — should not blow up."""
    p = inflated_list_price(100.0, listed_from=date(2025, 1, 1),
                            sale_date=date(2020, 1, 1), annual_inflation=0.03)
    assert p == 100.0


def test_unit_price_at_sale_returns_rounded_price():
    price, _ = unit_price_at_sale(
        list_price=100.0, listed_from=date(2020, 1, 1),
        sale_date=date(2020, 1, 1), annual_inflation=0.03,
        promo_pct=0.10, round_to=0.5,
    )
    assert price % 0.5 == 0


def test_unit_price_at_sale_returns_promo_pct_unchanged():
    _, pct = unit_price_at_sale(
        list_price=100.0, listed_from=date(2020, 1, 1),
        sale_date=date(2020, 1, 1), annual_inflation=0.03,
        promo_pct=0.20,
    )
    assert pct == 0.20


def test_unit_price_at_sale_clamps_promo_to_max():
    """promo_pct above 0.95 must be clipped (avoids negative line totals)."""
    _, pct = unit_price_at_sale(
        list_price=100.0, listed_from=date(2020, 1, 1),
        sale_date=date(2020, 1, 1), annual_inflation=0.03,
        promo_pct=1.50,
    )
    assert pct == 0.95


def test_unit_price_at_sale_clamps_negative_promo():
    _, pct = unit_price_at_sale(
        list_price=100.0, listed_from=date(2020, 1, 1),
        sale_date=date(2020, 1, 1), annual_inflation=0.03,
        promo_pct=-0.10,
    )
    assert pct == 0.0


def test_unit_price_never_below_round_to_step():
    """Tiny base price + rounding should still produce a positive price."""
    price, _ = unit_price_at_sale(
        list_price=0.10, listed_from=date(2020, 1, 1),
        sale_date=date(2020, 1, 1), annual_inflation=0.03,
        round_to=0.5,
    )
    assert price >= 0.5
