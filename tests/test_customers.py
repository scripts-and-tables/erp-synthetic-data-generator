"""Tests for customer master generator."""
from __future__ import annotations

import pandas as pd

from erp_synth.cohorts import COHORT_LABELS
from erp_synth.customers import ACQUISITION_CHANNELS, generate_customers_df
from erp_synth.rng_utils import make_rngs

REQUIRED_COLUMNS = {
    "customer_id", "created_at", "first_name", "last_name", "email", "phone",
    "email_opt_in", "sms_opt_in", "call_opt_in",
    "gender", "birth_year", "marital_status", "occupation", "yearly_income",
    "num_children", "house_owner_flag", "education",
    "country", "region", "city", "postal_code",
    "cohort", "price_sensitivity", "brand_affinity", "market",
    "acquisition_channel",
}


def _gen(rngs, market, n=50):
    return generate_customers_df(
        rngs=rngs, market_cfg=market, n_customers=n,
        customers_created_at_start="2023-01-01",
        customers_created_at_end="2024-12-31",
        device_brand_pool=["FreshNest", "AromaDrive", "BreezeLine"],
    )


def test_customer_count_matches_request(rngs, market_us):
    df = _gen(rngs, market_us, n=100)
    assert len(df) == 100


def test_customers_have_all_required_columns(rngs, market_us):
    df = _gen(rngs, market_us)
    missing = REQUIRED_COLUMNS - set(df.columns)
    assert not missing, f"missing columns: {missing}"


def test_customer_ids_are_sequential_from_one(rngs, market_us):
    df = _gen(rngs, market_us)
    assert df["customer_id"].tolist() == list(range(1, len(df) + 1))


def test_cohort_labels_in_expected_set(rngs, market_us):
    df = _gen(rngs, market_us, n=200)
    assert set(df["cohort"].unique()) <= set(COHORT_LABELS)


def test_acquisition_channel_in_expected_set(rngs, market_us):
    df = _gen(rngs, market_us, n=200)
    assert set(df["acquisition_channel"].unique()) <= set(ACQUISITION_CHANNELS)


def test_price_sensitivity_in_unit_interval(rngs, market_us):
    df = _gen(rngs, market_us, n=200)
    assert (df["price_sensitivity"] >= 0).all()
    assert (df["price_sensitivity"] <= 1).all()


def test_birth_year_reasonable_range(rngs, market_us):
    df = _gen(rngs, market_us, n=200)
    # Customers are 18..75 years old as of run end → birth year roughly 1949..2006
    assert df["birth_year"].min() >= 1940
    assert df["birth_year"].max() <= 2010


def test_yearly_income_positive(rngs, market_us):
    df = _gen(rngs, market_us, n=200)
    assert (df["yearly_income"] > 0).all()


def test_country_drawn_from_market_pool(rngs, market_gcc):
    df = _gen(rngs, market_gcc, n=200)
    pool_countries = {c for c, _ in market_gcc["country_pool"]}
    assert set(df["country"].unique()) <= pool_countries


def test_market_label_set_correctly(rngs, market_eu):
    df = _gen(rngs, market_eu, n=10)
    assert (df["market"] == "eu").all()


def test_seeded_generation_reproducible(market_us):
    a = _gen(make_rngs(123), market_us, n=20)
    b = _gen(make_rngs(123), market_us, n=20)
    # Same customer_id -> same cohort, market label, etc.
    pd.testing.assert_series_equal(a["cohort"], b["cohort"])
    pd.testing.assert_series_equal(a["yearly_income"], b["yearly_income"])
