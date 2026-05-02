"""Tests for item universe + sampler."""
from __future__ import annotations

from datetime import date

import pandas as pd

from erp_synth.items import sample_items_dataset_df

REQUIRED_COLUMNS = [
    "product_id", "product_name", "brand", "category", "subcategory",
    "gramm_g", "list_price", "standard_cost", "currency",
    "listed_from_date", "compatible_device_brand", "is_active",
]


def test_universe_has_all_four_categories(items_universe):
    cats = set(items_universe["category"].unique())
    assert cats == {"DEVICE", "REFILL", "ACCESSORY", "SPARE_PART"}


def test_universe_refills_have_non_empty_gramm_g(items_universe):
    refills = items_universe[items_universe["category"] == "REFILL"]
    assert (refills["gramm_g"] != "").all()


def test_universe_devices_have_blank_gramm_g(items_universe):
    devices = items_universe[items_universe["category"] == "DEVICE"]
    assert (devices["gramm_g"] == "").all()


def test_sample_respects_counts(rngs, items_universe, market_us):
    df = sample_items_dataset_df(
        items_universe,
        n_devices=3, n_accessories=4, n_spare_parts=2,
        n_refills=10, n_bulk_refills=1,
        rng=rngs.py, currency=market_us["currency"],
        listed_from_floor=date(2020, 1, 1), listing_window_days=30,
    )
    counts = df["category"].value_counts().to_dict()
    assert counts.get("DEVICE", 0) == 3
    assert counts.get("ACCESSORY", 0) == 4
    assert counts.get("SPARE_PART", 0) == 2
    assert counts.get("REFILL", 0) == 11  # regular + bulk


def test_sample_has_required_columns(items_df):
    assert items_df.columns.tolist() == REQUIRED_COLUMNS


def test_list_price_strictly_greater_than_standard_cost(items_df):
    diff = items_df["list_price"] - items_df["standard_cost"]
    assert (diff > 0).all()


def test_product_id_is_sequential_starting_at_one(items_df):
    ids = items_df["product_id"].tolist()
    assert ids == list(range(1, len(items_df) + 1))


def test_refill_subcategory_is_small_or_bulk(items_df):
    refills = items_df[items_df["category"] == "REFILL"]
    assert set(refills["subcategory"].unique()) <= {"Refill Small", "Refill Bulk"}


def test_currency_propagated_from_market(items_df, market_us):
    assert (items_df["currency"] == market_us["currency"]).all()


def test_listed_from_date_within_listing_window(items_df):
    floor = date(2023, 1, 1)
    cap = date(2023, 1, 30)
    for ds in items_df["listed_from_date"]:
        d = date.fromisoformat(str(ds))
        assert floor <= d <= cap, f"{d} outside [{floor}, {cap}]"


def test_seeded_sampling_is_reproducible(items_universe, market_us):
    from erp_synth.rng_utils import make_rngs
    a = sample_items_dataset_df(
        items_universe, n_devices=3, n_accessories=4, n_spare_parts=2,
        n_refills=10, n_bulk_refills=1, rng=make_rngs(42).py,
        currency=market_us["currency"],
        listed_from_floor=date(2020, 1, 1), listing_window_days=30,
    )
    b = sample_items_dataset_df(
        items_universe, n_devices=3, n_accessories=4, n_spare_parts=2,
        n_refills=10, n_bulk_refills=1, rng=make_rngs(42).py,
        currency=market_us["currency"],
        listed_from_floor=date(2020, 1, 1), listing_window_days=30,
    )
    pd.testing.assert_frame_equal(a, b)
