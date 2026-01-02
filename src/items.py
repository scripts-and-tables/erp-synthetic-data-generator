# src/generate_items.py
import random
import pandas as pd


# ==========================================================
# UNIVERSE SETTINGS
# - Defines the FULL possible catalog space (all combinations)
# ==========================================================
SETTINGS_UNIVERSE = {
    # Brands
    "device_brands": ["AromaDrive", "BreezeLine", "FreshNest"],
    "refill_brands": ["Good Smell", "AromaWave", "FreshNest", "Citrus & Co", "BreezeLine"],

    # Devices (templates)
    "devices_catalog": [
        "Diffuser Machine - Home",
        "Diffuser Machine - Compact",
        "Nebulizer Machine - Pro",
        "Car Diffuser Machine - Clip",
        "Car Diffuser Machine - Mini",
    ],

    # Accessories (templates)
    "accessories_catalog": [
        "Wall Bracket Mount",
        "Hanging Strap",
        "Decor Sticker Pack",
        "Protective Sleeve",
        "Travel Pouch",
        "Cable Organizer Clip",
        "Adhesive Mount Pad",
        "Car Vent Holder",
        "Desk Stand Base",
        "Cleaning Wipes Pack",
    ],

    # Spare parts (templates)
    "spare_parts_catalog": [
        "Replacement Cap",
        "Nozzle Holder",
        "Scent Cartridge Holder",
        "Seal Ring (O-Ring)",
        "Diffuser Wick Set",
        "Power Adapter",
        "USB Cable",
        "Clip Replacement",
    ],

    # Regular refill combinations (cross product)
    "scents": ["Citrus", "Lavender", "Coffee", "Vanilla", "Ocean", "Jasmine", "Rose", "Mint", "Pine", "Chocolate"],
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
    # Category base price ranges (currency-agnostic)
    # We will sample from these ranges and then apply brand/gramm adjustments + noise.
    "base_ranges": {
        "DEVICE": (180.0, 650.0),
        "ACCESSORY": (12.0, 75.0),
        "SPARE_PART": (18.0, 140.0),
        "REFILL": (8.0, 30.0),  # base component for refills (final comes from gramm model)
    },

    # Brand multipliers (premium/eco)
    # Brands not listed => 1.0
    "brand_multiplier": {
        "FreshNest": 1.10,
        "AromaDrive": 1.05,
        "BreezeLine": 1.00,
        "Good Smell": 0.95,
        "AromaWave": 1.00,
        "Citrus & Co": 0.90,
    },

    # Refill price per gram model:
    # - for small refills (10..100g): use price_per_g_small
    # - for bulk refills (>= 500g): use price_per_g_bulk (cheaper per gram)
    "price_per_g_small": 0.55,   # e.g. 50g => 27.5
    "price_per_g_bulk": 0.22,    # e.g. 500g => 110

    # Extra fixed packaging margin for refills
    "refill_packaging_fee_small": 3.0,
    "refill_packaging_fee_bulk": 12.0,

    # Noise (applied multiplicatively)
    "noise_pct": 0.08,  # ±8%

    # Rounding
    "round_to": 0.5,  # round to 0.5 increments (e.g., 12.0, 12.5, 13.0)
}


# ==========================================================
# 1) Build FULL universe
# ==========================================================
def build_items_universe_df(universe_settings: dict = SETTINGS_UNIVERSE) -> pd.DataFrame:
    """
    Build the FULL catalog space (all possible combinations).

    Output columns:
      product_name, brand, category, gramm_g

    Internal helper column:
      _is_bulk (0/1)  -> used only for sampling logic
    """
    rows = []

    # Devices: device_brand x device_template
    for brand in universe_settings["device_brands"]:
        for device_name in universe_settings["devices_catalog"]:
            rows.append({
                "product_name": f"{brand} {device_name}",
                "brand": brand,
                "category": "DEVICE",
                "gramm_g": "",
                "_is_bulk": 0,
            })

    # Accessories: device_brand x accessory_template
    for brand in universe_settings["device_brands"]:
        for name in universe_settings["accessories_catalog"]:
            rows.append({
                "product_name": f"{brand} {name}",
                "brand": brand,
                "category": "ACCESSORY",
                "gramm_g": "",
                "_is_bulk": 0,
            })

    # Spare parts: device_brand x spare_part_template
    for brand in universe_settings["device_brands"]:
        for name in universe_settings["spare_parts_catalog"]:
            rows.append({
                "product_name": f"{brand} {name}",
                "brand": brand,
                "category": "SPARE_PART",
                "gramm_g": "",
                "_is_bulk": 0,
            })

    # Regular refills: refill_brand x scent x size
    for brand in universe_settings["refill_brands"]:
        for scent in universe_settings["scents"]:
            for g in universe_settings["refill_sizes_g"]:
                rows.append({
                    "product_name": f"{brand} Refill Liquid {scent} {int(g)}",
                    "brand": brand,
                    "category": "REFILL",
                    "gramm_g": int(g),
                    "_is_bulk": 0,
                })

    # Bulk refills: explicit list
    for br in universe_settings.get("bulk_refills", []):
        brand = br["brand"]
        scent = br["scent"]
        gramm = int(br["gramm_g"])
        suffix = br.get("suffix", "").strip()
        suffix_part = f" {suffix}" if suffix else ""
        rows.append({
            "product_name": f"{brand} Refill Liquid {scent} {gramm}{suffix_part}",
            "brand": brand,
            "category": "REFILL",
            "gramm_g": gramm,
            "_is_bulk": 1,
        })

    return pd.DataFrame(rows)


# ==========================================================
# Pricing helpers
# ==========================================================
def _round_to_step(x: float, step: float) -> float:
    if step <= 0:
        return float(x)
    return round(float(x) / step) * step


def _brand_mult(pricing_settings: dict, brand: str) -> float:
    m = pricing_settings.get("brand_multiplier", {})
    return float(m.get(brand, 1.0))


def _price_for_row(rng: random.Random, row: dict, pricing_settings: dict) -> float:
    """
    Hardcoded price model:
      - DEVICE/ACCESSORY/SPARE_PART: sample base range * brand_multiplier * noise
      - REFILL: gramm-based (small vs bulk) + packaging fee * brand_multiplier * noise
    """
    cat = row["category"]
    brand = row["brand"]

    base_ranges = pricing_settings["base_ranges"]
    noise_pct = float(pricing_settings["noise_pct"])
    step = float(pricing_settings["round_to"])
    bm = _brand_mult(pricing_settings, brand)

    # noise factor in [1-noise, 1+noise]
    noise = 1.0 + rng.uniform(-noise_pct, noise_pct)

    if cat in ("DEVICE", "ACCESSORY", "SPARE_PART"):
        lo, hi = base_ranges[cat]
        base = rng.uniform(float(lo), float(hi))
        price = base * bm * noise
        return max(step, _round_to_step(price, step))

    if cat == "REFILL":
        gramm = row.get("gramm_g", "")
        gramm_int = int(gramm) if gramm != "" else 0

        # Determine small vs bulk by gramm
        if gramm_int >= 500:
            ppg = float(pricing_settings["price_per_g_bulk"])
            fee = float(pricing_settings["refill_packaging_fee_bulk"])
        else:
            ppg = float(pricing_settings["price_per_g_small"])
            fee = float(pricing_settings["refill_packaging_fee_small"])

        base = (gramm_int * ppg) + fee
        price = base * bm * noise
        return max(step, _round_to_step(price, step))

    # Fallback (should not happen)
    return _round_to_step(10.0 * bm * noise, step)


# ==========================================================
# 2) Sample a dataset from universe (explicit parameters)
# ==========================================================
def sample_items_dataset_df(
    universe_df: pd.DataFrame,
    *,
    seed: int,
    n_devices: int,
    n_accessories: int,
    n_spare_parts: int,
    n_refills: int,
    n_bulk_refills: int,
    pricing_settings: dict = SETTINGS_PRICING,
) -> pd.DataFrame:
    """
    Sample an items dataset from the FULL universe.

    Parameters:
      universe_df
        Output of build_items_universe_df().

      seed
        Random seed for deterministic sampling and shuffling.

      n_devices / n_accessories / n_spare_parts
        How many rows to pick for each non-refill category.

      n_refills
        How many REGULAR (non-bulk) refills to pick.

      n_bulk_refills
        How many BULK refills to pick (0 or 1 typically).

      pricing_settings
        Price model knobs (base ranges, brand multipliers, gramm pricing, noise, rounding).

    Output columns:
      product_id, product_name, brand, category, gramm_g, unit_price
    """
    rng = random.Random(int(seed))

    n_devices = int(n_devices)
    n_accessories = int(n_accessories)
    n_spare_parts = int(n_spare_parts)
    n_refills = int(n_refills)
    n_bulk_refills = int(n_bulk_refills)

    if n_devices < 0 or n_accessories < 0 or n_spare_parts < 0 or n_refills < 0 or n_bulk_refills < 0:
        raise ValueError("All n_* parameters must be >= 0.")

    # Pools
    devices_pool = universe_df[universe_df["category"] == "DEVICE"].copy()
    accessories_pool = universe_df[universe_df["category"] == "ACCESSORY"].copy()
    spare_pool = universe_df[universe_df["category"] == "SPARE_PART"].copy()

    refills_pool = universe_df[(universe_df["category"] == "REFILL") & (universe_df["_is_bulk"] == 0)].copy()
    bulk_pool = universe_df[(universe_df["category"] == "REFILL") & (universe_df["_is_bulk"] == 1)].copy()

    # Sanity checks
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

    # Sample fixed categories (no replacement)
    devices_pick = devices_pool.sample(n=n_devices, replace=False, random_state=seed) if n_devices else devices_pool.iloc[0:0]
    accessories_pick = accessories_pool.sample(n=n_accessories, replace=False, random_state=seed + 1) if n_accessories else accessories_pool.iloc[0:0]
    spare_pick = spare_pool.sample(n=n_spare_parts, replace=False, random_state=seed + 2) if n_spare_parts else spare_pool.iloc[0:0]

    # Bulk pick: exactly N bulk refills
    bulk_pick = bulk_pool.sample(n=n_bulk_refills, replace=False, random_state=seed + 100) if n_bulk_refills else bulk_pool.iloc[0:0]

    # Regular refills: distribute across refill brands (business-like)
    refill_picks = []
    if n_refills:
        refill_brands = sorted(refills_pool["brand"].unique().tolist())
        base = n_refills // len(refill_brands)
        remainder = n_refills % len(refill_brands)

        quotas = {b: base for b in refill_brands}
        for b in refill_brands[:remainder]:
            quotas[b] += 1

        for brand, qty in quotas.items():
            if qty <= 0:
                continue
            brand_pool = refills_pool[refills_pool["brand"] == brand]
            replace = qty > len(brand_pool)
            brand_seed = seed + (abs(hash(brand)) % 10_000) + 10
            refill_picks.append(brand_pool.sample(n=qty, replace=replace, random_state=brand_seed))

    refills_pick = pd.concat(refill_picks, ignore_index=True) if refill_picks else refills_pool.iloc[0:0]

    # Combine
    df = pd.concat([devices_pick, accessories_pick, spare_pick, bulk_pick, refills_pick], ignore_index=True)

    # Mix order + assign product_id sequential after mixing
    rows = df.to_dict("records")
    rng.shuffle(rows)

    out_rows = []
    for r in rows:
        # Ensure gramm_g is int or ""
        if r.get("gramm_g", "") != "":
            r["gramm_g"] = int(r["gramm_g"])
        else:
            r["gramm_g"] = ""

        # Add price on sampling stage
        r["unit_price"] = float(_price_for_row(rng, r, pricing_settings))
        out_rows.append(r)

    out = pd.DataFrame(out_rows)

    out.insert(0, "product_id", range(1, len(out) + 1))

    # Final column order
    out = out[["product_id", "product_name", "brand", "category", "gramm_g", "unit_price"]].copy()

    return out
