"""Promotion master + lookup."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import pandas as pd

from .markets import holidays_for_year
from .rng_utils import RNGs


_GENERIC_PROMOS = [
    ("Spring Sale", 3, 14, 0.15),
    ("Summer Refresh", 6, 14, 0.20),
    ("Back to Routine", 9, 10, 0.10),
    ("End of Year Clearance", 1, 10, 0.25),
]
_BLACK_FRIDAY_WINDOW = ("Black Friday Week", 11, 23, 11, 30, 0.30)
_BOXING_WEEK = ("Boxing Week", 12, 26, 12, 31, 0.20)
_RAMADAN_PROMO = ("Ramadan Specials", None, None, 0.20)
_EID_PROMO = ("Eid Sale", None, None, 0.25)
_CATEGORIES = ["DEVICE", "REFILL", "ACCESSORY", "SPARE_PART"]


def _add_promo(rows: list, market: str, name: str, start: date, end: date,
               discount_pct: float, scope: str = "ALL") -> None:
    pid = f"P-{market.upper()}-{start:%Y%m%d}-{name[:6].upper().replace(' ', '')}"
    rows.append({
        "promotion_id": pid,
        "name": name,
        "discount_pct": round(float(discount_pct), 4),
        "category_scope": scope,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "market": market,
    })


def build_promotions_df(*, date_from: date, date_till: date,
                        market_cfg: dict[str, Any],
                        n_per_year: int, rngs: RNGs) -> pd.DataFrame:
    """Generate ~n_per_year promotions per calendar year, anchored to market events.

    Each year always includes (when market matches): Black Friday + Boxing Week
    for US/EU, Ramadan + Eid for GCC. Remaining slots are filled from
    _GENERIC_PROMOS plus a few category-targeted ones.
    """
    rng = rngs.py
    market = market_cfg["key"]
    rows: list[dict[str, Any]] = []

    for year in range(date_from.year, date_till.year + 1):
        added = 0

        if market in ("us", "eu"):
            name, sm, sd, em, ed, disc = _BLACK_FRIDAY_WINDOW
            try:
                _add_promo(rows, market, name, date(year, sm, sd), date(year, em, ed), disc)
                added += 1
            except ValueError:
                pass
            name, sm, sd, em, ed, disc = _BOXING_WEEK
            try:
                _add_promo(rows, market, name, date(year, sm, sd), date(year, em, ed), disc)
                added += 1
            except ValueError:
                pass

        if market == "gcc":
            holidays = holidays_for_year(market_cfg, year)
            ramadan_days = sorted(d for d, m in holidays.items() if 1.3 <= m <= 1.7)
            if ramadan_days:
                _add_promo(rows, market, _RAMADAN_PROMO[0],
                           ramadan_days[0], ramadan_days[-1], _RAMADAN_PROMO[3])
                added += 1
            eid_days = sorted(d for d, m in holidays.items() if m >= 1.95)
            if eid_days:
                _add_promo(rows, market, _EID_PROMO[0],
                           eid_days[0], eid_days[-1], _EID_PROMO[3])
                added += 1

        for name, month, length, disc in _GENERIC_PROMOS:
            if added >= n_per_year:
                break
            try:
                start_day = rng.randrange(1, 22)
                start = date(year, month, start_day)
                end = start + timedelta(days=int(length))
                if start > date_till or end < date_from:
                    continue
                start = max(start, date_from)
                end = min(end, date_till)
                if start > end:
                    continue
                # Random scope: 60% ALL, otherwise a single category
                scope = "ALL" if rng.random() < 0.6 else rng.choice(_CATEGORIES)
                _add_promo(rows, market, name, start, end,
                           disc * rng.uniform(0.85, 1.15), scope)
                added += 1
            except ValueError:
                continue

    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values("start_date", kind="mergesort").reset_index(drop=True)
    return df


def applicable_promo(d: date, category: str,
                     promos_df: pd.DataFrame) -> tuple[str, float]:
    """Return (promotion_id, discount_pct) for the most aggressive active promo
    on `d` that applies to `category`. Empty string + 0.0 if none.
    """
    if promos_df is None or promos_df.empty:
        return "", 0.0
    iso = d.isoformat()
    mask = (promos_df["start_date"] <= iso) & (promos_df["end_date"] >= iso)
    cat_mask = (promos_df["category_scope"] == "ALL") | (promos_df["category_scope"] == category)
    active = promos_df[mask & cat_mask]
    if active.empty:
        return "", 0.0
    best = active.loc[active["discount_pct"].idxmax()]
    return str(best["promotion_id"]), float(best["discount_pct"])


def build_promo_lookup(promos_df: pd.DataFrame, *,
                       date_from: date, date_till: date,
                       categories: list[str]) -> dict[tuple[str, str], tuple[str, float]]:
    """Precompute (date_iso, category) -> (promo_id, discount_pct) for the hot loop.

    Only inserts entries for dates with active promos; missing keys -> no promo.
    """
    lookup: dict[tuple[str, str], tuple[str, float]] = {}
    if promos_df is None or promos_df.empty:
        return lookup
    # Sort by discount_pct descending so first match wins (best promo).
    df = promos_df.sort_values("discount_pct", ascending=False).reset_index(drop=True)
    from datetime import timedelta
    for _, row in df.iterrows():
        s = date.fromisoformat(str(row["start_date"]))
        e = date.fromisoformat(str(row["end_date"]))
        s = max(s, date_from)
        e = min(e, date_till)
        if s > e:
            continue
        scope = str(row["category_scope"])
        applies_to = categories if scope == "ALL" else [scope]
        pid = str(row["promotion_id"])
        pct = float(row["discount_pct"])
        d = s
        while d <= e:
            iso = d.isoformat()
            for cat in applies_to:
                key = (iso, cat)
                if key not in lookup:  # first wins → best discount
                    lookup[key] = (pid, pct)
            d = d + timedelta(days=1)
    return lookup


def lookup_promo(promo_lookup: dict, d: date, category: str) -> tuple[str, float]:
    return promo_lookup.get((d.isoformat(), category), ("", 0.0))
