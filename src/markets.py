"""Market presets: locale, currency, VAT, holidays, seasonality, payment methods.

A market_cfg dict bundles everything regional so the rest of the pipeline
stays geography-agnostic. Override fields freely after lookup.
"""
from __future__ import annotations

from datetime import date
from typing import Any


# Month-of-year demand multipliers (1.0 = neutral). Index 1..12.
_MONTH_FACTOR_US = {
    1: 0.70, 2: 0.85, 3: 0.95, 4: 1.00, 5: 1.05, 6: 1.00,
    7: 0.85, 8: 0.90, 9: 1.00, 10: 1.10, 11: 1.60, 12: 1.80,
}
_MONTH_FACTOR_EU = {
    1: 0.80, 2: 0.85, 3: 0.95, 4: 1.05, 5: 1.10, 6: 1.05,
    7: 0.90, 8: 0.70, 9: 1.05, 10: 1.10, 11: 1.30, 12: 1.60,
}
# GCC: Ramadan/Eid handled in holiday_bumps; baseline calmer year-round
_MONTH_FACTOR_GCC = {
    1: 1.00, 2: 1.00, 3: 1.05, 4: 1.05, 5: 1.00, 6: 0.85,
    7: 0.80, 8: 0.85, 9: 1.00, 10: 1.05, 11: 1.20, 12: 1.30,
}

# Day-of-week multipliers (Mon=0..Sun=6).
_DOW_WEEKEND_SAT_SUN = {0: 0.95, 1: 0.95, 2: 0.95, 3: 1.00, 4: 1.05, 5: 1.15, 6: 1.15}
_DOW_WEEKEND_FRI_SAT = {0: 0.95, 1: 0.95, 2: 0.95, 3: 1.00, 4: 1.15, 5: 1.15, 6: 1.00}


def _us_holiday_bumps(year: int) -> dict[date, float]:
    """Christmas, Black Friday (day after 4th Thursday of November), Independence Day."""
    bumps: dict[date, float] = {}

    thursdays = [date(year, 11, day) for day in range(1, 31)
                 if date(year, 11, day).weekday() == 3]
    if len(thursdays) >= 4:
        bf = date(year, 11, thursdays[3].day + 1)
        bumps[bf] = 2.5
        cm_day = bf.day + 3
        if cm_day <= 30:
            bumps[date(year, 11, cm_day)] = 1.8

    bumps[date(year, 12, 23)] = 1.6
    bumps[date(year, 12, 24)] = 1.8
    bumps[date(year, 12, 26)] = 1.4
    bumps[date(year, 7, 4)] = 1.3
    return bumps


def _eu_holiday_bumps(year: int) -> dict[date, float]:
    bumps: dict[date, float] = {
        date(year, 12, 23): 1.6,
        date(year, 12, 24): 1.8,
        date(year, 12, 26): 1.3,
        date(year, 11, 29): 1.6,  # rough Black Friday equivalent
    }
    return bumps


# Approximate Eid al-Fitr and Eid al-Adha dates (Gregorian) by year.
# Hand-curated for 2010-2030; adequate for synthetic data.
_EID_AL_FITR = {
    2010: (9, 10), 2011: (8, 30), 2012: (8, 19), 2013: (8, 8),
    2014: (7, 28), 2015: (7, 17), 2016: (7, 6), 2017: (6, 25),
    2018: (6, 15), 2019: (6, 4), 2020: (5, 24), 2021: (5, 13),
    2022: (5, 2), 2023: (4, 21), 2024: (4, 10), 2025: (3, 30),
    2026: (3, 20), 2027: (3, 9), 2028: (2, 26), 2029: (2, 14),
    2030: (2, 4),
}
_EID_AL_ADHA = {
    2010: (11, 16), 2011: (11, 6), 2012: (10, 26), 2013: (10, 15),
    2014: (10, 4), 2015: (9, 23), 2016: (9, 11), 2017: (9, 1),
    2018: (8, 21), 2019: (8, 11), 2020: (7, 31), 2021: (7, 20),
    2022: (7, 9), 2023: (6, 28), 2024: (6, 16), 2025: (6, 6),
    2026: (5, 27), 2027: (5, 16), 2028: (5, 5), 2029: (4, 24),
    2030: (4, 13),
}
# Ramadan start ≈ ~30 days before Eid al-Fitr
def _ramadan_window(year: int) -> tuple[date, date] | None:
    if year not in _EID_AL_FITR:
        return None
    m, d = _EID_AL_FITR[year]
    eid = date(year, m, d)
    start_ord = eid.toordinal() - 30
    end_ord = eid.toordinal() - 1
    return date.fromordinal(start_ord), date.fromordinal(end_ord)


def _gcc_holiday_bumps(year: int) -> dict[date, float]:
    bumps: dict[date, float] = {}
    rw = _ramadan_window(year)
    if rw:
        s, e = rw
        # Ramadan: gentle bump across all days, stronger in last 10 days
        for ord_ in range(s.toordinal(), e.toordinal() + 1):
            d = date.fromordinal(ord_)
            days_left = (e.toordinal() - ord_) + 1
            bumps[d] = 1.4 if days_left > 10 else 1.7

    if year in _EID_AL_FITR:
        m, d = _EID_AL_FITR[year]
        eid_start = date(year, m, d)
        for delta in range(-2, 1):  # eve and 2 days before
            bumps[date.fromordinal(eid_start.toordinal() + delta)] = 2.0
    if year in _EID_AL_ADHA:
        m, d = _EID_AL_ADHA[year]
        bumps[date(year, m, d)] = 1.8
        bumps[date.fromordinal(date(year, m, d).toordinal() - 1)] = 1.6

    bumps[date(year, 12, 2)] = 1.5  # UAE National Day
    return bumps


# Per-market builders for holidays-by-year (lazy, one cache per process)
_HOLIDAY_BUILDERS = {
    "us": _us_holiday_bumps,
    "eu": _eu_holiday_bumps,
    "gcc": _gcc_holiday_bumps,
}


MARKETS: dict[str, dict[str, Any]] = {
    "us": {
        "name": "US",
        "faker_locale": "en_US",
        "currency": "USD",
        "vat_rate": 0.0875,
        "freight_flat": 5.0,
        "freight_free_above": 50.0,
        "inflation_default": 0.03,
        "country_pool": [("US", 1.0)],
        "payment_methods": [
            ("Card", 0.55), ("ApplePay", 0.10), ("Cash", 0.15),
            ("Transfer", 0.05), ("PayPal", 0.10), ("COD", 0.05),
        ],
        "month_factor": _MONTH_FACTOR_US,
        "dow_factor": _DOW_WEEKEND_SAT_SUN,
        "holiday_builder": _us_holiday_bumps,
    },
    "eu": {
        "name": "EU",
        "faker_locale": "de_DE",
        "currency": "EUR",
        "vat_rate": 0.20,
        "freight_flat": 4.5,
        "freight_free_above": 60.0,
        "inflation_default": 0.025,
        "country_pool": [("DE", 0.4), ("FR", 0.3), ("IT", 0.15), ("ES", 0.15)],
        "payment_methods": [
            ("Card", 0.50), ("Transfer", 0.20), ("Cash", 0.10),
            ("PayPal", 0.15), ("COD", 0.05),
        ],
        "month_factor": _MONTH_FACTOR_EU,
        "dow_factor": _DOW_WEEKEND_SAT_SUN,
        "holiday_builder": _eu_holiday_bumps,
    },
    "gcc": {
        "name": "GCC",
        "faker_locale": "ar_AA",
        "currency": "AED",
        "vat_rate": 0.05,
        "freight_flat": 15.0,
        "freight_free_above": 200.0,
        "inflation_default": 0.025,
        "country_pool": [("AE", 0.5), ("SA", 0.35), ("QA", 0.05), ("KW", 0.05), ("OM", 0.05)],
        "payment_methods": [
            ("Card", 0.35), ("Mada", 0.20), ("ApplePay", 0.10),
            ("Cash", 0.15), ("COD", 0.15), ("Transfer", 0.05),
        ],
        "month_factor": _MONTH_FACTOR_GCC,
        "dow_factor": _DOW_WEEKEND_FRI_SAT,
        "holiday_builder": _gcc_holiday_bumps,
    },
}


def get_market(key: str, *, vat_rate: float | None = None,
               currency: str | None = None,
               annual_inflation: float | None = None) -> dict[str, Any]:
    """Lookup market preset and apply CLI overrides."""
    if key not in MARKETS:
        raise ValueError(f"Unknown market '{key}'. Available: {sorted(MARKETS)}")
    cfg = dict(MARKETS[key])
    cfg["key"] = key
    if vat_rate is not None:
        cfg["vat_rate"] = float(vat_rate)
    if currency is not None:
        cfg["currency"] = str(currency)
    if annual_inflation is not None:
        cfg["inflation_default"] = float(annual_inflation)
    cfg["_holiday_cache"] = {}
    return cfg


def holidays_for_year(market_cfg: dict[str, Any], year: int) -> dict[date, float]:
    cache = market_cfg.setdefault("_holiday_cache", {})
    if year not in cache:
        cache[year] = market_cfg["holiday_builder"](year)
    return cache[year]
