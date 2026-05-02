"""Tests for return-invoice generation."""
from __future__ import annotations

import random
from datetime import date

from erp_synth.returns import maybe_generate_return


def _sample_header():
    return {
        "invoice_id": "1-20230101-000001",
        "customer_id": 1,
        "store_id": 101,
        "order_date": "2023-01-01",
        "ship_date": "2023-01-02",
        "due_date": "2023-02-01",
        "subtotal": 100.0,
        "discount_total": 10.0,
        "tax_amount": 7.88,
        "freight": 5.0,
        "grand_total": 102.88,
        "vat_rate": 0.0875,
        "currency": "USD",
        "payment_method": "Card",
        "promotion_id": "",
        "is_return": 0,
        "reference_invoice_id": "",
        "n_lines": 2,
    }


def _sample_lines():
    return [
        {"line_id": 1, "invoice_id": "1-20230101-000001", "product_id": 5,
         "quantity": 2, "unit_price": 30.0, "discount_pct": 0.0,
         "discount_amount": 0.0, "extended_amount": 60.0, "line_total": 60.0,
         "unit_standard_cost": 12.0, "line_cost": 24.0, "gross_margin": 36.0},
        {"line_id": 2, "invoice_id": "1-20230101-000001", "product_id": 10,
         "quantity": 1, "unit_price": 40.0, "discount_pct": 0.25,
         "discount_amount": 10.0, "extended_amount": 40.0, "line_total": 30.0,
         "unit_standard_cost": 18.0, "line_cost": 18.0, "gross_margin": 12.0},
    ]


def test_p_return_zero_returns_none():
    rng = random.Random(0)
    result = maybe_generate_return(
        header=_sample_header(), lines=_sample_lines(), rng=rng,
        p_return=0.0, end_date=date(2023, 12, 31), next_invoice_seq=2,
    )
    assert result is None


def test_p_return_one_always_produces_return():
    rng = random.Random(0)
    result = maybe_generate_return(
        header=_sample_header(), lines=_sample_lines(), rng=rng,
        p_return=1.0, end_date=date(2023, 12, 31), next_invoice_seq=2,
    )
    assert result is not None
    ret_header, ret_lines = result
    assert ret_header["is_return"] == 1
    assert ret_header["reference_invoice_id"] == "1-20230101-000001"


def test_return_negates_quantities_and_money():
    rng = random.Random(0)
    _, ret_lines = maybe_generate_return(
        header=_sample_header(), lines=_sample_lines(), rng=rng,
        p_return=1.0, end_date=date(2023, 12, 31), next_invoice_seq=2,
    )
    for line in ret_lines:
        assert line["quantity"] < 0
        assert line["line_total"] < 0
        assert line["gross_margin"] < 0


def test_return_date_is_in_window():
    rng = random.Random(0)
    ret_header, _ = maybe_generate_return(
        header=_sample_header(), lines=_sample_lines(), rng=rng,
        p_return=1.0, end_date=date(2023, 12, 31), next_invoice_seq=2,
    )
    orig = date(2023, 1, 1)
    ret = date.fromisoformat(ret_header["order_date"])
    delta = (ret - orig).days
    assert 1 <= delta <= 30


def test_return_clipped_when_no_room_in_window():
    """End date 1 day after the original — most return delays > 1 → return is suppressed often."""
    rng = random.Random(7)
    suppressed = 0
    for _ in range(50):
        out = maybe_generate_return(
            header=_sample_header(), lines=_sample_lines(), rng=rng,
            p_return=1.0, end_date=date(2023, 1, 1), next_invoice_seq=2,
        )
        if out is None:
            suppressed += 1
    assert suppressed >= 40


def test_return_lines_are_subset_of_originals():
    rng = random.Random(0)
    _, ret_lines = maybe_generate_return(
        header=_sample_header(), lines=_sample_lines(), rng=rng,
        p_return=1.0, end_date=date(2023, 12, 31), next_invoice_seq=2,
    )
    assert 1 <= len(ret_lines) <= 2


def test_return_reuses_payment_method_and_currency():
    rng = random.Random(0)
    h = _sample_header()
    h["payment_method"] = "Mada"
    h["currency"] = "AED"
    ret_header, _ = maybe_generate_return(
        header=h, lines=_sample_lines(), rng=rng,
        p_return=1.0, end_date=date(2023, 12, 31), next_invoice_seq=2,
    )
    assert ret_header["payment_method"] == "Mada"
    assert ret_header["currency"] == "AED"
