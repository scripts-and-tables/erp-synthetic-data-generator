"""Tests for promotion master + lookup."""
from __future__ import annotations

from datetime import date

import pandas as pd

from erp_synth.promotions import (
    build_promo_lookup,
    build_promotions_df,
    lookup_promo,
)

CATS = ["DEVICE", "REFILL", "ACCESSORY", "SPARE_PART"]


def test_promotions_df_has_required_columns(rngs, market_us):
    df = build_promotions_df(
        date_from=date(2023, 1, 1), date_till=date(2024, 12, 31),
        market_cfg=market_us, n_per_year=4, rngs=rngs,
    )
    expected = {"promotion_id", "name", "discount_pct", "category_scope",
                "start_date", "end_date", "market"}
    assert expected <= set(df.columns)


def test_promotions_df_includes_us_black_friday(rngs, market_us):
    df = build_promotions_df(
        date_from=date(2024, 1, 1), date_till=date(2024, 12, 31),
        market_cfg=market_us, n_per_year=6, rngs=rngs,
    )
    assert df[df["name"].str.contains("Black Friday")].shape[0] >= 1


def test_promotions_df_gcc_includes_ramadan(rngs, market_gcc):
    df = build_promotions_df(
        date_from=date(2024, 1, 1), date_till=date(2024, 12, 31),
        market_cfg=market_gcc, n_per_year=6, rngs=rngs,
    )
    assert df[df["name"].str.contains("Ramadan")].shape[0] >= 1


def test_lookup_promo_returns_none_outside_window():
    df = pd.DataFrame([{
        "promotion_id": "P-X", "name": "Test", "discount_pct": 0.20,
        "category_scope": "ALL", "start_date": "2023-06-01",
        "end_date": "2023-06-15", "market": "us",
    }])
    lookup = build_promo_lookup(df, date_from=date(2023, 1, 1),
                                date_till=date(2023, 12, 31), categories=CATS)
    pid, pct = lookup_promo(lookup, date(2023, 5, 1), "REFILL")
    assert pid == "" and pct == 0.0


def test_lookup_promo_returns_active_promo():
    df = pd.DataFrame([{
        "promotion_id": "P-X", "name": "Test", "discount_pct": 0.20,
        "category_scope": "ALL", "start_date": "2023-06-01",
        "end_date": "2023-06-15", "market": "us",
    }])
    lookup = build_promo_lookup(df, date_from=date(2023, 1, 1),
                                date_till=date(2023, 12, 31), categories=CATS)
    pid, pct = lookup_promo(lookup, date(2023, 6, 5), "REFILL")
    assert pid == "P-X" and pct == 0.20


def test_lookup_promo_best_discount_wins_when_overlapping():
    df = pd.DataFrame([
        {"promotion_id": "P-LOW", "name": "Low", "discount_pct": 0.10,
         "category_scope": "ALL", "start_date": "2023-06-01",
         "end_date": "2023-06-15", "market": "us"},
        {"promotion_id": "P-HIGH", "name": "High", "discount_pct": 0.30,
         "category_scope": "ALL", "start_date": "2023-06-05",
         "end_date": "2023-06-20", "market": "us"},
    ])
    lookup = build_promo_lookup(df, date_from=date(2023, 1, 1),
                                date_till=date(2023, 12, 31), categories=CATS)
    pid, pct = lookup_promo(lookup, date(2023, 6, 10), "REFILL")
    assert pid == "P-HIGH" and pct == 0.30


def test_lookup_promo_respects_category_scope():
    df = pd.DataFrame([{
        "promotion_id": "P-DEV", "name": "Devices only", "discount_pct": 0.25,
        "category_scope": "DEVICE", "start_date": "2023-06-01",
        "end_date": "2023-06-15", "market": "us",
    }])
    lookup = build_promo_lookup(df, date_from=date(2023, 1, 1),
                                date_till=date(2023, 12, 31), categories=CATS)
    assert lookup_promo(lookup, date(2023, 6, 5), "DEVICE")[1] == 0.25
    assert lookup_promo(lookup, date(2023, 6, 5), "REFILL") == ("", 0.0)


def test_empty_promotions_df_safe_lookup():
    empty = pd.DataFrame(columns=["promotion_id", "discount_pct",
                                  "category_scope", "start_date", "end_date"])
    lookup = build_promo_lookup(empty, date_from=date(2023, 1, 1),
                                date_till=date(2023, 12, 31), categories=CATS)
    assert lookup == {}
    assert lookup_promo(lookup, date(2023, 6, 5), "REFILL") == ("", 0.0)
