"""Tests for marketing spend, support tickets, and NPS surveys."""
from __future__ import annotations

from datetime import date

import pandas as pd

from erp_synth.customers import generate_customers_df
from erp_synth.marketing import build_marketing_spend_df
from erp_synth.support import build_nps_surveys_df, build_support_tickets_df


def test_marketing_has_required_columns(rngs, market_us):
    df = build_marketing_spend_df(
        date_from=date(2023, 1, 1), date_till=date(2024, 12, 31),
        market_cfg=market_us, rngs=rngs,
    )
    assert {"month", "channel", "spend_amount", "currency", "market"} <= set(df.columns)


def test_marketing_has_one_row_per_month_per_channel(rngs, market_us):
    df = build_marketing_spend_df(
        date_from=date(2023, 1, 1), date_till=date(2023, 12, 31),
        market_cfg=market_us, rngs=rngs,
    )
    # 12 months × 6 channels = 72 rows
    assert len(df) == 72
    grouped = df.groupby(["month", "channel"]).size()
    assert (grouped == 1).all()


def test_marketing_holiday_months_get_boost(rngs, market_us):
    df = build_marketing_spend_df(
        date_from=date(2023, 1, 1), date_till=date(2023, 12, 31),
        market_cfg=market_us, rngs=rngs,
    )
    df["month_dt"] = pd.to_datetime(df["month"])
    nov_total = df[df["month_dt"].dt.month == 11]["spend_amount"].sum()
    feb_total = df[df["month_dt"].dt.month == 2]["spend_amount"].sum()
    assert nov_total > feb_total * 2


def test_marketing_currency_matches_market(rngs, market_eu):
    df = build_marketing_spend_df(
        date_from=date(2023, 1, 1), date_till=date(2023, 12, 31),
        market_cfg=market_eu, rngs=rngs,
    )
    assert (df["currency"] == "EUR").all()


def _small_customers_with_invoices(rngs, market_us, n=20):
    customers = generate_customers_df(
        rngs=rngs, market_cfg=market_us, n_customers=n,
        customers_created_at_start="2023-01-01",
        customers_created_at_end="2023-06-30",
        device_brand_pool=["FreshNest", "AromaDrive", "BreezeLine"],
    )
    # Hand-roll a tiny invoice_headers that can be passed to support builders
    headers = pd.DataFrame([{
        "invoice_id": f"{cid}-20230401-000001",
        "customer_id": cid,
        "order_date": "2023-04-01",
        "is_return": 0,
    } for cid in customers["customer_id"]])
    return customers, headers


def test_support_tickets_has_required_columns(rngs, market_us):
    customers, headers = _small_customers_with_invoices(rngs, market_us, n=30)
    df = build_support_tickets_df(
        customers_df=customers, headers_df=headers, rng=rngs.py,
        date_till=date(2023, 12, 31),
    )
    expected = {"ticket_id", "customer_id", "invoice_id", "channel", "category",
                "priority", "opened_at", "closed_at", "resolution_hours", "csat_score"}
    assert expected <= set(df.columns)


def test_support_tickets_csat_in_range(rngs, market_us):
    customers, headers = _small_customers_with_invoices(rngs, market_us, n=30)
    df = build_support_tickets_df(
        customers_df=customers, headers_df=headers, rng=rngs.py,
        date_till=date(2023, 12, 31),
    )
    closed = df.dropna(subset=["csat_score"])
    if not closed.empty:
        assert closed["csat_score"].between(1, 5).all()


def test_support_tickets_only_reference_known_invoices(rngs, market_us):
    customers, headers = _small_customers_with_invoices(rngs, market_us, n=30)
    df = build_support_tickets_df(
        customers_df=customers, headers_df=headers, rng=rngs.py,
        date_till=date(2023, 12, 31),
    )
    if not df.empty:
        valid = set(headers["invoice_id"]) | {""}
        assert set(df["invoice_id"].fillna("").astype(str)) <= valid


def test_nps_surveys_has_required_columns(rngs, market_us):
    customers, headers = _small_customers_with_invoices(rngs, market_us, n=50)
    df = build_nps_surveys_df(
        customers_df=customers, headers_df=headers, rng=rngs.py,
        date_from=date(2023, 1, 1), date_till=date(2024, 6, 30),
    )
    expected = {"survey_id", "customer_id", "sent_at", "response_at",
                "score", "nps_category"}
    assert expected <= set(df.columns)


def test_nps_score_in_range(rngs, market_us):
    customers, headers = _small_customers_with_invoices(rngs, market_us, n=50)
    df = build_nps_surveys_df(
        customers_df=customers, headers_df=headers, rng=rngs.py,
        date_from=date(2023, 1, 1), date_till=date(2024, 6, 30),
    )
    # Score column may include "" for non-responses (object dtype); coerce.
    scores = pd.to_numeric(df["score"], errors="coerce").dropna()
    if not scores.empty:
        assert scores.between(0, 10).all()
        responded = df[df["score"] != ""]
        if not responded.empty:
            assert set(responded["nps_category"].unique()) <= {
                "Detractor", "Passive", "Promoter"
            }
