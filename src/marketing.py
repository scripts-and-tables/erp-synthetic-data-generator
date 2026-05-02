"""Marketing spend master — monthly spend per channel, per market.

Produces a row per (month, channel, market) with realistic budget patterns:
- total spend grows ~25%/year as the customer base expands
- paid channels ramp later than organic / referral / email
- holiday months get a 2-4x boost (Nov / Dec / Black Friday week)
- modest random noise per month

Useful for computing CAC and marketing efficiency over time.
"""
from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd

from .customers import ACQUISITION_CHANNELS
from .rng_utils import RNGs


# Base monthly spend per channel in year 0 (USD), pre-growth and pre-holiday
_CHANNEL_BASE_USD = {
    "ORGANIC":     200.0,    # SEO content / landing pages — small fixed cost
    "REFERRAL":    300.0,    # referral program incentives
    "PAID_SEARCH": 800.0,    # Google Ads
    "PAID_SOCIAL": 600.0,    # Meta / TikTok
    "EMAIL":       150.0,    # ESP + creative
    "AFFILIATE":   400.0,    # affiliate payouts
}

# Each channel's relative ramp factor — paid channels start smaller and grow faster.
# Values are capped at year 8 so 10+ year runs don't blow up.
_CHANNEL_GROWTH = {
    "ORGANIC":     1.06,
    "REFERRAL":    1.08,
    "PAID_SEARCH": 1.12,
    "PAID_SOCIAL": 1.18,
    "EMAIL":       1.07,
    "AFFILIATE":   1.10,
}
_GROWTH_CAP_YEARS = 8


def build_marketing_spend_df(*, date_from: date, date_till: date,
                             market_cfg: dict[str, Any],
                             rngs: RNGs) -> pd.DataFrame:
    """One row per (month_start, channel)."""
    rng = rngs.np
    rows: list[dict[str, Any]] = []

    # Currency-relative base scaling so EU/GCC budgets stay reasonable
    currency_factor = {"USD": 1.0, "EUR": 0.95, "AED": 3.6}.get(
        market_cfg["currency"], 1.0
    )

    # Build all month_starts in the range
    months = pd.date_range(start=date(date_from.year, date_from.month, 1),
                           end=date_till, freq="MS")

    first_year = date_from.year

    for ts in months:
        m = ts.month
        years_since = ts.year - first_year
        # Holiday boost
        if m == 11:
            holiday_mult = 3.5
        elif m == 12:
            holiday_mult = 2.6
        elif m == 7:
            holiday_mult = 0.85
        elif m == 1:
            holiday_mult = 0.70
        else:
            holiday_mult = 1.0

        capped_years = min(years_since, _GROWTH_CAP_YEARS)
        for channel in ACQUISITION_CHANNELS:
            base = _CHANNEL_BASE_USD[channel]
            growth = _CHANNEL_GROWTH[channel] ** capped_years
            noise = float(rng.normal(1.0, 0.10))
            spend = base * growth * holiday_mult * currency_factor * max(0.5, noise)
            rows.append({
                "month": ts.date().isoformat(),
                "channel": channel,
                "spend_amount": round(spend, 2),
                "currency": market_cfg["currency"],
                "market": market_cfg["key"],
            })

    return pd.DataFrame(rows)
