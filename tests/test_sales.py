"""Tests for the day-by-day sales loop."""
from __future__ import annotations

import random
from datetime import date

import pandas as pd

from erp_synth.cohorts import assign_cohort
from erp_synth.promotions import build_promo_lookup, build_promotions_df
from erp_synth.sales import generate_customer_sales


def _items_index(items_df: pd.DataFrame) -> dict[int, dict]:
    idx = {}
    for rec in items_df.to_dict("records"):
        rec["_listed_from_date_obj"] = date.fromisoformat(str(rec["listed_from_date"]))
        idx[int(rec["product_id"])] = rec
    return idx


def _ids(items_df: pd.DataFrame, cat: str) -> list[int]:
    return items_df[items_df.category == cat].product_id.tolist()


def _make_promo_lookup(rngs, market):
    df = build_promotions_df(date_from=date(2023, 1, 1), date_till=date(2023, 12, 31),
                             market_cfg=market, n_per_year=4, rngs=rngs)
    return build_promo_lookup(df, date_from=date(2023, 1, 1),
                              date_till=date(2023, 12, 31),
                              categories=["DEVICE", "REFILL", "ACCESSORY", "SPARE_PART"])


def test_generate_customer_sales_returns_three_tuple(rngs, market_us, items_df):
    cohort = assign_cohort(1, seed=rngs.seed,
                           brand_pool=sorted(items_df.brand.unique()))
    out = generate_customer_sales(
        customer_id=1, sales_start_date="2023-06-01", sales_end_date="2023-09-30",
        items_index=_items_index(items_df),
        device_product_ids=_ids(items_df, "DEVICE"),
        refill_product_ids=_ids(items_df, "REFILL"),
        accessory_product_ids=_ids(items_df, "ACCESSORY"),
        spare_part_product_ids=_ids(items_df, "SPARE_PART"),
        store_ids=[101, 102, 103],
        market_cfg=market_us,
        promo_lookup=_make_promo_lookup(rngs, market_us),
        annual_inflation=0.03, p_return=0.03, enable_returns=False,
        cohort_spec=cohort, rng=random.Random(42),
    )
    headers, lines, next_line_id = out
    assert isinstance(headers, list)
    assert isinstance(lines, list)
    assert isinstance(next_line_id, int)


def test_every_invoice_has_at_least_one_line(rngs, market_us, items_df):
    cohort = assign_cohort(1, seed=rngs.seed,
                           brand_pool=sorted(items_df.brand.unique()))
    headers, lines, _ = generate_customer_sales(
        customer_id=1, sales_start_date="2023-01-01", sales_end_date="2023-12-31",
        items_index=_items_index(items_df),
        device_product_ids=_ids(items_df, "DEVICE"),
        refill_product_ids=_ids(items_df, "REFILL"),
        accessory_product_ids=_ids(items_df, "ACCESSORY"),
        spare_part_product_ids=_ids(items_df, "SPARE_PART"),
        store_ids=[101], market_cfg=market_us,
        promo_lookup=_make_promo_lookup(rngs, market_us),
        annual_inflation=0.03, p_return=0.0, enable_returns=False,
        cohort_spec=cohort, rng=random.Random(42),
    )
    if not headers:
        return
    line_invoice_ids = {line["invoice_id"] for line in lines}
    for header in headers:
        assert header["invoice_id"] in line_invoice_ids


def test_line_total_matches_extended_minus_discount(rngs, market_us, items_df):
    cohort = assign_cohort(1, seed=rngs.seed,
                           brand_pool=sorted(items_df.brand.unique()))
    _, lines, _ = generate_customer_sales(
        customer_id=1, sales_start_date="2023-01-01", sales_end_date="2023-12-31",
        items_index=_items_index(items_df),
        device_product_ids=_ids(items_df, "DEVICE"),
        refill_product_ids=_ids(items_df, "REFILL"),
        accessory_product_ids=_ids(items_df, "ACCESSORY"),
        spare_part_product_ids=_ids(items_df, "SPARE_PART"),
        store_ids=[101], market_cfg=market_us,
        promo_lookup=_make_promo_lookup(rngs, market_us),
        annual_inflation=0.03, p_return=0.0, enable_returns=False,
        cohort_spec=cohort, rng=random.Random(42),
    )
    for line in lines:
        expected = round(line["extended_amount"] - line["discount_amount"], 2)
        assert abs(expected - line["line_total"]) < 0.01


def test_one_shot_cohort_generates_few_invoices(rngs, market_us, items_df):
    """Sanity: ONE_SHOT cohort should generate a small number of invoices over a year."""
    one_shot_spec = None
    for cid in range(1, 5000):
        spec = assign_cohort(cid, seed=rngs.seed,
                             brand_pool=sorted(items_df.brand.unique()))
        if spec["cohort"] == "ONE_SHOT":
            one_shot_spec = spec
            break
    assert one_shot_spec is not None

    headers, _, _ = generate_customer_sales(
        customer_id=999, sales_start_date="2023-01-01", sales_end_date="2023-12-31",
        items_index=_items_index(items_df),
        device_product_ids=_ids(items_df, "DEVICE"),
        refill_product_ids=_ids(items_df, "REFILL"),
        accessory_product_ids=_ids(items_df, "ACCESSORY"),
        spare_part_product_ids=_ids(items_df, "SPARE_PART"),
        store_ids=[101], market_cfg=market_us,
        promo_lookup=_make_promo_lookup(rngs, market_us),
        annual_inflation=0.03, p_return=0.0, enable_returns=False,
        cohort_spec=one_shot_spec, rng=random.Random(42),
    )
    # ONE_SHOT: spike then near-zero — total invoices over a year should be small
    assert len(headers) <= 5
