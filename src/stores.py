"""Store master generator."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import pandas as pd

from .rng_utils import RNGs


_CITY_POOL = {
    "US": [("New York", "NY"), ("Los Angeles", "CA"), ("Chicago", "IL"),
           ("Houston", "TX"), ("Phoenix", "AZ"), ("Philadelphia", "PA"),
           ("San Antonio", "TX"), ("San Diego", "CA"), ("Dallas", "TX"),
           ("Austin", "TX"), ("Seattle", "WA"), ("Boston", "MA")],
    "DE": [("Berlin", "BE"), ("Munich", "BY"), ("Hamburg", "HH"),
           ("Frankfurt", "HE"), ("Cologne", "NW")],
    "FR": [("Paris", "IDF"), ("Lyon", "ARA"), ("Marseille", "PAC"),
           ("Toulouse", "OCC"), ("Nice", "PAC")],
    "IT": [("Rome", "LAZ"), ("Milan", "LOM"), ("Naples", "CAM"), ("Turin", "PIE")],
    "ES": [("Madrid", "MAD"), ("Barcelona", "CAT"), ("Valencia", "VLC"), ("Seville", "AND")],
    "AE": [("Dubai", "DU"), ("Abu Dhabi", "AZ"), ("Sharjah", "SH"), ("Ajman", "AJ")],
    "SA": [("Riyadh", "RD"), ("Jeddah", "MK"), ("Dammam", "EP"), ("Mecca", "MK")],
    "QA": [("Doha", "DA")],
    "KW": [("Kuwait City", "KU")],
    "OM": [("Muscat", "MA")],
}

_STORE_TYPES = [("Flagship", 0.10), ("Standard", 0.55), ("Kiosk", 0.20), ("Online", 0.15)]


def _weighted(rng, weights):
    total = sum(w for _, w in weights)
    x = rng.random() * total
    acc = 0.0
    for v, w in weights:
        acc += w
        if x <= acc:
            return v
    return weights[-1][0]


def build_stores_df(*, market_cfg: dict[str, Any], n_stores: int,
                    rngs: RNGs, opened_floor: date) -> pd.DataFrame:
    """Build n_stores rows aligned to the market's country pool."""
    rng = rngs.py
    rows = []
    countries = market_cfg["country_pool"]

    for i in range(int(n_stores)):
        country = _weighted(rng, countries)
        city, region = rng.choice(_CITY_POOL.get(country, [("Unknown", "")]))
        store_type = _weighted(rng, _STORE_TYPES)
        opened = opened_floor + timedelta(days=rng.randrange(0, 365 * 5))
        rows.append({
            "store_id": 100 + i + 1,
            "store_name": f"{market_cfg['key'].upper()}-{store_type[:3].upper()}-{i+1:03d} {city}",
            "country": country,
            "region": region,
            "city": city,
            "opened_date": opened.isoformat(),
            "store_type": store_type,
        })
    return pd.DataFrame(rows)
