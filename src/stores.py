"""Store master generator."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import pandas as pd

from .rng_utils import RNGs


# (city, region, lat, lon) — hand-curated for the cities used by markets
_CITY_POOL = {
    "US": [
        ("New York", "NY", 40.7128, -74.0060),
        ("Los Angeles", "CA", 34.0522, -118.2437),
        ("Chicago", "IL", 41.8781, -87.6298),
        ("Houston", "TX", 29.7604, -95.3698),
        ("Phoenix", "AZ", 33.4484, -112.0740),
        ("Philadelphia", "PA", 39.9526, -75.1652),
        ("San Antonio", "TX", 29.4241, -98.4936),
        ("San Diego", "CA", 32.7157, -117.1611),
        ("Dallas", "TX", 32.7767, -96.7970),
        ("Austin", "TX", 30.2672, -97.7431),
        ("Seattle", "WA", 47.6062, -122.3321),
        ("Boston", "MA", 42.3601, -71.0589),
    ],
    "DE": [
        ("Berlin", "BE", 52.5200, 13.4050),
        ("Munich", "BY", 48.1351, 11.5820),
        ("Hamburg", "HH", 53.5511, 9.9937),
        ("Frankfurt", "HE", 50.1109, 8.6821),
        ("Cologne", "NW", 50.9375, 6.9603),
    ],
    "FR": [
        ("Paris", "IDF", 48.8566, 2.3522),
        ("Lyon", "ARA", 45.7640, 4.8357),
        ("Marseille", "PAC", 43.2965, 5.3698),
        ("Toulouse", "OCC", 43.6047, 1.4442),
        ("Nice", "PAC", 43.7102, 7.2620),
    ],
    "IT": [
        ("Rome", "LAZ", 41.9028, 12.4964),
        ("Milan", "LOM", 45.4642, 9.1900),
        ("Naples", "CAM", 40.8518, 14.2681),
        ("Turin", "PIE", 45.0703, 7.6869),
    ],
    "ES": [
        ("Madrid", "MAD", 40.4168, -3.7038),
        ("Barcelona", "CAT", 41.3851, 2.1734),
        ("Valencia", "VLC", 39.4699, -0.3763),
        ("Seville", "AND", 37.3891, -5.9845),
    ],
    "AE": [
        ("Dubai", "DU", 25.2048, 55.2708),
        ("Abu Dhabi", "AZ", 24.4539, 54.3773),
        ("Sharjah", "SH", 25.3463, 55.4209),
        ("Ajman", "AJ", 25.4052, 55.5136),
    ],
    "SA": [
        ("Riyadh", "RD", 24.7136, 46.6753),
        ("Jeddah", "MK", 21.4858, 39.1925),
        ("Dammam", "EP", 26.4207, 50.0888),
        ("Mecca", "MK", 21.3891, 39.8579),
    ],
    "QA": [("Doha", "DA", 25.2854, 51.5310)],
    "KW": [("Kuwait City", "KU", 29.3759, 47.9774)],
    "OM": [("Muscat", "MA", 23.5880, 58.3829)],
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
        city, region, lat, lon = rng.choice(_CITY_POOL.get(country, [("Unknown", "", 0.0, 0.0)]))
        store_type = _weighted(rng, _STORE_TYPES)
        opened = opened_floor + timedelta(days=rng.randrange(0, 365 * 5))
        # Online stores have null geo
        if store_type == "Online":
            lat, lon = None, None
        else:
            # tiny jitter so multiple stores in the same city aren't identical
            lat = round(lat + rng.uniform(-0.05, 0.05), 4)
            lon = round(lon + rng.uniform(-0.05, 0.05), 4)
        rows.append({
            "store_id": 100 + i + 1,
            "store_name": f"{market_cfg['key'].upper()}-{store_type[:3].upper()}-{i+1:03d} {city}",
            "country": country,
            "region": region,
            "city": city,
            "latitude": lat if lat is not None else "",
            "longitude": lon if lon is not None else "",
            "opened_date": opened.isoformat(),
            "store_type": store_type,
        })
    return pd.DataFrame(rows)
