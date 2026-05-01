# src/items.py
"""Product universe + sampling + enriched item master.

Extends the original universe with:
- subcategory  (e.g. "Home Diffuser", "Refill Small/Bulk", ...)
- standard_cost (for gross margin)
- listed_from_date (anchor for inflation)
- compatible_device_brand (so refills/spares/accessories bind to a device family)
- currency
- is_active flag
- list_price (replaces old `unit_price` column name)
"""
from __future__ import annotations

import random
from datetime import date, timedelta
from typing import Any

import pandas as pd


# ==========================================================
# UNIVERSE SETTINGS
# - Defines the FULL possible catalog space (all combinations)
# ==========================================================
SETTINGS_UNIVERSE = {
    # Brands
    "device_brands": ["AromaDrive", "BreezeLine", "FreshNest"],
    "refill_brands": ["Good Smell", "AromaWave", "FreshNest", "Citrus & Co", "BreezeLine"],

    # Devices (template -> subcategory)
    "devices_catalog": [
        ("Diffuser Machine - Home", "Home Diffuser"),
        ("Diffuser Machine - Compact", "Home Diffuser"),
        ("Nebulizer Machine - Pro", "Pro Diffuser"),
        ("Car Diffuser Machine - Clip", "Car Diffuser"),
        ("Car Diffuser Machine - Mini", "Car Diffuser"),
    ],

    # Accessories (template -> subcategory)
    "accessories_catalog": [
        ("Wall Bracket Mount", "Mount"),
        ("Hanging Strap", "Mount"),
        ("Decor Sticker Pack", "Decor"),
        ("Protective Sleeve", "Cover"),
        ("Travel Pouch", "Cover"),
        ("Cable Organizer Clip", "Cable"),
        ("Adhesive Mount Pad", "Mount"),
        ("Car Vent Holder", "Mount"),
        ("Desk Stand Base", "Mount"),
        ("Cleaning Wipes Pack", "Care"),
    ],

    # Spare parts (template -> subcategory)
    "spare_parts_catalog": [
        ("Replacement Cap", "Cap"),
        ("Nozzle Holder", "Nozzle"),
        ("Scent Cartridge Holder", "Cartridge"),
        ("Seal Ring (O-Ring)", "Seal"),
        ("Diffuser Wick Set", "Wick"),
        ("Power Adapter", "Power"),
        ("USB Cable", "Power"),
        ("Clip Replacement", "Mount"),
    ],

    # Regular refill combinations (cross product)
    "scents": ["Citrus", "Lavender", "Coffee", "Vanilla", "Ocean",
               "Jasmine", "Rose", "Mint", "Pine", "Chocolate"],
    "refill_sizes_g": [10, 20, 30, 50, 100],

    # Bulk refills: special industrial items
    "bulk_refills": [
        {"brand": "Good Smell", "scent": "Citrus",   "gramm_g": 500,  "suffix": "(Industrial)"},
        {"brand": "AromaWave",  "scent": "Lavender", "gramm_g": 500,  "suffix": "(Industrial)"},
        {"brand": "FreshNest",  "scent": "Coffee",   "gramm_g": 1000, "suffix": "(Industrial)"},
    ],
}


# ==========================================================
# PRICING SETTINGS
# - Simple hardcoded model with tunable knobs
# ==========================================================
SETTINGS_PRICING = {
    "base_ranges": {
        "DEVICE": (180.0, 650.0),
        "ACCESSORY": (12.0, 75.0),
        "SPARE_PART": (18.0, 140.0),
        "REFILL": (8.0, 30.0),
    },
    "brand_multiplier": {
        "FreshNest": 1.10,
        "AromaDrive": 1.05,
        "BreezeLine": 1.00,
        "Good Smell": 0.95,
        "AromaWave": 1.00,
        "Citrus & Co": 0.90,
    },
    "price_per_g_small": 0.55,
    "price_per_g_bulk": 0.22,
    "refill_packaging_fee_small": 3.0,
    "refill_packaging_fee_bulk": 12.0,
    "noise_pct": 0.08,
    "round_to": 0.5,
}

# Standard-cost ratio per category (relative to list_price). Drives margin.
COST_RATIO_BY_CATEGORY = {
    "DEVICE": 0.55,
    "REFILL": 0.35,
    "ACCESSORY": 0.45,
    "SPARE_PART": 0.50,
}


def _round_to_step(x: float, step: float) -> float:
    if step <= 0:
        return float(x)
    return round(float(x) / step) * step


def _brand_mult(pricing_settings: dict, brand: str) -> float:
    m = pricing_settings.get("brand_multiplier", {})
    return float(m.get(brand, 1.0))


def _price_for_row(rng: random.Random, row: dict, pricing_settings: dict) -> float:
    cat = row["category"]
    brand = row["brand"]

    base_ranges = pricing_settings["base_ranges"]
    noise_pct = float(pricing_settings["noise_pct"])
    step = float(pricing_settings["round_to"])
    bm = _brand_mult(pricing_settings, brand)
    noise = 1.0 + rng.uniform(-noise_pct, noise_pct)

    if cat in ("DEVICE", "ACCESSORY", "SPARE_PART"):
        lo, hi = base_ranges[cat]
        base = rng.uniform(float(lo), float(hi))
        price = base * bm * noise
        return max(step, _round_to_step(price, step))

    if cat == "REFILL":
        gramm = row.get("gramm_g", "")
        gramm_int = int(gramm) if gramm != "" else 0
        if gramm_int >= 500:
            ppg = float(pricing_settings["price_per_g_bulk"])
            fee = float(pricing_settings["refill_packaging_fee_bulk"])
        else:
            ppg = float(pricing_settings["price_per_g_small"])
            fee = float(pricing_settings["refill_packaging_fee_small"])
        base = (gramm_int * ppg) + fee
        price = base * bm * noise
        return max(step, _round_to_step(price, step))

    return _round_to_step(10.0 * bm * noise, step)


def _refill_subcategory(gramm_g: int) -> str:
    return "Refill Bulk" if gramm_g >= 500 else "Refill Small"


# ==========================================================
# 1) Build FULL universe
# ==========================================================
def build_items_universe_df(universe_settings: dict = SETTINGS_UNIVERSE) -> pd.DataFrame:
    """Build the FULL catalog space (all possible combinations).

    Output columns: product_name, brand, category, subcategory, gramm_g,
    compatible_device_brand, _is_bulk (helper).
    """
    rows = []

    # Devices: device_brand x device_template
    for brand in universe_settings["device_brands"]:
        for name, sub in universe_settings["devices_catalog"]:
            rows.append({
                "product_name": f"{brand} {name}",
                "brand": brand,
                "category": "DEVICE",
                "subcategory": sub,
                "gramm_g": "",
                "compatible_device_brand": brand,  # devices are their own family
                "_is_bulk": 0,
            })

    # Accessories: device_brand x accessory_template
    for brand in universe_settings["device_brands"]:
        for name, sub in universe_settings["accessories_catalog"]:
            rows.append({
                "product_name": f"{brand} {name}",
                "brand": brand,
                "category": "ACCESSORY",
                "subcategory": sub,
                "gramm_g": "",
                "compatible_device_brand": brand,
                "_is_bulk": 0,
            })

    # Spare parts: device_brand x spare_part_template
    for brand in universe_settings["device_brands"]:
        for name, sub in universe_settings["spare_parts_catalog"]:
            rows.append({
                "product_name": f"{brand} {name}",
                "brand": brand,
                "category": "SPARE_PART",
                "subcategory": sub,
                "gramm_g": "",
                "compatible_device_brand": brand,
                "_is_bulk": 0,
            })

    # Regular refills: refill_brand x scent x size
    refill_brands = universe_settings["refill_brands"]
    device_brands = universe_settings["device_brands"]
    for brand in refill_brands:
        # Refill brand binds to a device brand if same name; otherwise free-floating ""
        compat = brand if brand in device_brands else ""
        for scent in universe_settings["scents"]:
            for g in universe_settings["refill_sizes_g"]:
                rows.append({
                    "product_name": f"{brand} Refill Liquid {scent} {int(g)}",
                    "brand": brand,
                    "category": "REFILL",
                    "subcategory": _refill_subcategory(int(g)),
                    "gramm_g": int(g),
                    "compatible_device_brand": compat,
                    "_is_bulk": 0,
                })

    # Bulk refills
    for br in universe_settings.get("bulk_refills", []):
        brand = br["brand"]
        scent = br["scent"]
        gramm = int(br["gramm_g"])
        suffix = br.get("suffix", "").strip()
        suffix_part = f" {suffix}" if suffix else ""
        compat = brand if brand in device_brands else ""
        rows.append({
            "product_name": f"{brand} Refill Liquid {scent} {gramm}{suffix_part}",
            "brand": brand,
            "category": "REFILL",
            "subcategory": _refill_subcategory(gramm),
            "gramm_g": gramm,
            "compatible_device_brand": compat,
            "_is_bulk": 1,
        })

    return pd.DataFrame(rows)


# ==========================================================
# 2) Sample a dataset from universe
# ==========================================================
def sample_items_dataset_df(
    universe_df: pd.DataFrame,
    *,
    n_devices: int,
    n_accessories: int,
    n_spare_parts: int,
    n_refills: int,
    n_bulk_refills: int,
    rng: random.Random,
    currency: str,
    listed_from_floor: date,
    listing_window_days: int = 365,
    pricing_settings: dict = SETTINGS_PRICING,
) -> pd.DataFrame:
    """Sample an items dataset and add list_price/standard_cost/listed_from_date.

    Output columns: product_id, product_name, brand, category, subcategory,
    gramm_g, list_price, standard_cost, currency, listed_from_date,
    compatible_device_brand, is_active.
    """
    n_devices = int(n_devices)
    n_accessories = int(n_accessories)
    n_spare_parts = int(n_spare_parts)
    n_refills = int(n_refills)
    n_bulk_refills = int(n_bulk_refills)

    if min(n_devices, n_accessories, n_spare_parts, n_refills, n_bulk_refills) < 0:
        raise ValueError("All n_* parameters must be >= 0.")

    devices_pool = universe_df[universe_df["category"] == "DEVICE"].copy()
    accessories_pool = universe_df[universe_df["category"] == "ACCESSORY"].copy()
    spare_pool = universe_df[universe_df["category"] == "SPARE_PART"].copy()
    refills_pool = universe_df[(universe_df["category"] == "REFILL") & (universe_df["_is_bulk"] == 0)].copy()
    bulk_pool = universe_df[(universe_df["category"] == "REFILL") & (universe_df["_is_bulk"] == 1)].copy()

    if len(devices_pool) < n_devices:
        raise ValueError(f"Universe has {len(devices_pool)} DEVICE rows, requested n_devices={n_devices}.")
    if len(accessories_pool) < n_accessories:
        raise ValueError(f"Universe has {len(accessories_pool)} ACCESSORY rows, requested n_accessories={n_accessories}.")
    if len(spare_pool) < n_spare_parts:
        raise ValueError(f"Universe has {len(spare_pool)} SPARE_PART rows, requested n_spare_parts={n_spare_parts}.")
    if len(refills_pool) < n_refills:
        raise ValueError(f"Universe has {len(refills_pool)} regular REFILL rows, requested n_refills={n_refills}.")
    if len(bulk_pool) < n_bulk_refills:
        raise ValueError(f"Universe has {len(bulk_pool)} bulk REFILL rows, requested n_bulk_refills={n_bulk_refills}.")

    # Sample using the seeded RNG state via .sample(random_state=...)
    seed_state = rng.randrange(0, 2**31 - 1)

    devices_pick = devices_pool.sample(n=n_devices, replace=False, random_state=seed_state) if n_devices else devices_pool.iloc[0:0]
    accessories_pick = accessories_pool.sample(n=n_accessories, replace=False, random_state=seed_state + 1) if n_accessories else accessories_pool.iloc[0:0]
    spare_pick = spare_pool.sample(n=n_spare_parts, replace=False, random_state=seed_state + 2) if n_spare_parts else spare_pool.iloc[0:0]
    bulk_pick = bulk_pool.sample(n=n_bulk_refills, replace=False, random_state=seed_state + 3) if n_bulk_refills else bulk_pool.iloc[0:0]

    refill_picks: list[pd.DataFrame] = []
    if n_refills:
        refill_brands = sorted(refills_pool["brand"].unique().tolist())
        base = n_refills // len(refill_brands)
        remainder = n_refills % len(refill_brands)
        quotas = {b: base for b in refill_brands}
        for b in refill_brands[:remainder]:
            quotas[b] += 1
        for i, (brand, qty) in enumerate(quotas.items()):
            if qty <= 0:
                continue
            brand_pool = refills_pool[refills_pool["brand"] == brand]
            replace = qty > len(brand_pool)
            refill_picks.append(brand_pool.sample(n=qty, replace=replace, random_state=seed_state + 100 + i))
    refills_pick = pd.concat(refill_picks, ignore_index=True) if refill_picks else refills_pool.iloc[0:0]

    df = pd.concat([devices_pick, accessories_pick, spare_pick, bulk_pick, refills_pick], ignore_index=True)

    rows = df.to_dict("records")
    rng.shuffle(rows)

    out_rows: list[dict[str, Any]] = []
    cost_noise_pct = 0.05
    for r in rows:
        if r.get("gramm_g", "") != "":
            r["gramm_g"] = int(r["gramm_g"])
        else:
            r["gramm_g"] = ""

        list_price = float(_price_for_row(rng, r, pricing_settings))

        cat = r["category"]
        cost_ratio = COST_RATIO_BY_CATEGORY.get(cat, 0.5)
        noise = 1.0 + rng.uniform(-cost_noise_pct, cost_noise_pct)
        standard_cost = round(list_price * cost_ratio * noise, 2)

        listed_from = listed_from_floor + timedelta(days=rng.randrange(0, max(1, int(listing_window_days))))

        r["list_price"] = list_price
        r["standard_cost"] = standard_cost
        r["currency"] = currency
        r["listed_from_date"] = listed_from.isoformat()
        r["is_active"] = 1
        out_rows.append(r)

    out = pd.DataFrame(out_rows)
    out.insert(0, "product_id", range(1, len(out) + 1))

    out = out[[
        "product_id", "product_name", "brand", "category", "subcategory",
        "gramm_g", "list_price", "standard_cost", "currency",
        "listed_from_date", "compatible_device_brand", "is_active",
    ]].copy()
    return out
