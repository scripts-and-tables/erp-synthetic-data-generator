"""Pricing model: inflation-adjusted unit price with promo discount."""
from __future__ import annotations

from datetime import date

from .items import _round_to_step  # reuse rounding helper


def inflated_list_price(list_price: float, listed_from: date, sale_date: date,
                        annual_inflation: float) -> float:
    delta_days = (sale_date - listed_from).days
    if delta_days <= 0:
        return float(list_price)
    years = delta_days / 365.25
    return float(list_price) * (1.0 + float(annual_inflation)) ** years


def unit_price_at_sale(*, list_price: float, listed_from: date, sale_date: date,
                       annual_inflation: float, promo_pct: float = 0.0,
                       round_to: float = 0.5) -> tuple[float, float]:
    """Return (unit_price_after_inflation_rounded, applied_discount_pct).

    Discount is applied at the line level inside sales.py, NOT folded into
    the unit_price returned here — so unit_price is the gross sticker price
    that customer-facing receipts show.
    """
    raw = inflated_list_price(list_price, listed_from, sale_date, annual_inflation)
    rounded = max(round_to, _round_to_step(raw, round_to))
    discount = max(0.0, min(0.95, float(promo_pct)))
    return float(rounded), float(discount)
