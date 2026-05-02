"""Tests for store master generator."""
from __future__ import annotations

from datetime import date

from erp_synth.stores import build_stores_df

REQUIRED_COLUMNS = {
    "store_id", "store_name", "country", "region", "city",
    "latitude", "longitude", "opened_date", "store_type",
}


def test_store_count_matches_request(rngs, market_us):
    df = build_stores_df(market_cfg=market_us, n_stores=8, rngs=rngs,
                         opened_floor=date(2020, 1, 1))
    assert len(df) == 8


def test_stores_have_required_columns(rngs, market_us):
    df = build_stores_df(market_cfg=market_us, n_stores=5, rngs=rngs,
                         opened_floor=date(2020, 1, 1))
    missing = REQUIRED_COLUMNS - set(df.columns)
    assert not missing


def test_store_ids_unique(rngs, market_us):
    df = build_stores_df(market_cfg=market_us, n_stores=20, rngs=rngs,
                         opened_floor=date(2020, 1, 1))
    assert df["store_id"].is_unique


def test_lat_lon_within_valid_ranges(rngs, market_us):
    import pandas as pd
    df = build_stores_df(market_cfg=market_us, n_stores=20, rngs=rngs,
                         opened_floor=date(2020, 1, 1))
    lat = pd.to_numeric(df["latitude"], errors="coerce").dropna()
    lon = pd.to_numeric(df["longitude"], errors="coerce").dropna()
    assert not lat.empty, "expected at least one numeric latitude"
    assert lat.between(-90, 90).all()
    assert lon.between(-180, 180).all()


def test_country_drawn_from_market_pool(rngs, market_gcc):
    df = build_stores_df(market_cfg=market_gcc, n_stores=20, rngs=rngs,
                         opened_floor=date(2020, 1, 1))
    pool = {c for c, _ in market_gcc["country_pool"]}
    assert set(df["country"].unique()) <= pool


def test_store_type_in_expected_set(rngs, market_us):
    df = build_stores_df(market_cfg=market_us, n_stores=30, rngs=rngs,
                         opened_floor=date(2020, 1, 1))
    assert set(df["store_type"].unique()) <= {"Flagship", "Standard", "Kiosk", "Online"}
