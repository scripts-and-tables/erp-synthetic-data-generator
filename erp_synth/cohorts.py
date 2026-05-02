"""Persistent customer cohorts.

Each customer is deterministically assigned a cohort label and a bundle of
behavior knobs (replaces the per-customer random.choice block that previously
lived inline in run.py). Determinism is keyed on (seed, customer_id) so the
same customer always gets the same behavior across runs.
"""
from __future__ import annotations

import random
from typing import Any

# Cohort label distribution
_COHORT_WEIGHTS = [
    ("LOYAL_HEAVY", 0.10),
    ("LOYAL_LIGHT", 0.20),
    ("GROWING", 0.20),
    ("DECLINING", 0.20),
    ("ONE_SHOT", 0.20),
    ("CHURN_RISK", 0.10),
]

# Each cohort defines daily-buy probability schedule by year, lost probability,
# multi-invoice schedule, device repurchase decay, refill basket distribution,
# and accessory/spare-part attach rates.
_COHORT_PRESETS: dict[str, dict[str, Any]] = {
    "LOYAL_HEAVY": {
        "p_buy_by_year": [0.06, 0.08, 0.09, 0.10],
        "p_close_day": 0.0001,
        "p_invoice_by_nth": [1.00, 0.40, 0.10, 0.02],
        "p_device_by_nth": [0.95, 0.30, 0.10, 0.02],
        "refill_count_probs": [0.95, 0.85, 0.55, 0.20, 0.05],
        "p_refill_invoice": 0.95,
        "p_accessory_invoice": 0.10,
        "p_spare_part_invoice": 0.10,
        "price_sensitivity": 0.20,
    },
    "LOYAL_LIGHT": {
        "p_buy_by_year": [0.03, 0.04, 0.05, 0.05],
        "p_close_day": 0.0001,
        "p_invoice_by_nth": [1.00, 0.10, 0.02],
        "p_device_by_nth": [0.95, 0.10],
        "refill_count_probs": [0.85, 0.50, 0.15, 0.03],
        "p_refill_invoice": 0.95,
        "p_accessory_invoice": 0.05,
        "p_spare_part_invoice": 0.04,
        "price_sensitivity": 0.40,
    },
    "GROWING": {
        "p_buy_by_year": [0.02, 0.04, 0.06, 0.08],
        "p_close_day": 0.0002,
        "p_invoice_by_nth": [1.00, 0.20, 0.05, 0.01],
        "p_device_by_nth": [0.90, 0.30, 0.10],
        "refill_count_probs": [0.80, 0.55, 0.25, 0.05],
        "p_refill_invoice": 0.92,
        "p_accessory_invoice": 0.07,
        "p_spare_part_invoice": 0.05,
        "price_sensitivity": 0.55,
    },
    "DECLINING": {
        "p_buy_by_year": [0.06, 0.04, 0.02, 0.01],
        "p_close_day": 0.0003,
        "p_invoice_by_nth": [1.00, 0.05, 0.01],
        "p_device_by_nth": [0.85, 0.05],
        "refill_count_probs": [0.65, 0.30, 0.10],
        "p_refill_invoice": 0.85,
        "p_accessory_invoice": 0.04,
        "p_spare_part_invoice": 0.02,
        "price_sensitivity": 0.70,
    },
    "ONE_SHOT": {
        "p_buy_by_year": [0.005, 0.001, 0.0005, 0.0],
        "p_close_day": 0.0008,
        "p_invoice_by_nth": [1.00, 0.00],
        "p_device_by_nth": [0.95, 0.00],
        "refill_count_probs": [0.50, 0.20, 0.05],
        "p_refill_invoice": 0.70,
        "p_accessory_invoice": 0.03,
        "p_spare_part_invoice": 0.01,
        "price_sensitivity": 0.85,
    },
    "CHURN_RISK": {
        "p_buy_by_year": [0.04, 0.02, 0.01, 0.005],
        "p_close_day": 0.0006,
        "p_invoice_by_nth": [1.00, 0.05, 0.01],
        "p_device_by_nth": [0.85, 0.05],
        "refill_count_probs": [0.55, 0.20, 0.05],
        "p_refill_invoice": 0.80,
        "p_accessory_invoice": 0.02,
        "p_spare_part_invoice": 0.01,
        "price_sensitivity": 0.90,
    },
}

COHORT_LABELS = [c for c, _ in _COHORT_WEIGHTS]


def _weighted_pick(rng: random.Random, weights: list[tuple[Any, float]]):
    total = sum(w for _, w in weights)
    x = rng.random() * total
    acc = 0.0
    for v, w in weights:
        acc += w
        if x <= acc:
            return v
    return weights[-1][0]


def assign_cohort(customer_id: int, seed: int,
                  *, brand_pool: list[str] | None = None) -> dict[str, Any]:
    """Deterministically assign a cohort + behavior knobs for a customer.

    Returns a dict with the cohort label, all behavior knobs, a price_sensitivity
    score in [0,1], and a brand_affinity (sampled from brand_pool if provided).
    """
    salt = (seed * 2654435761) ^ (int(customer_id) * 40503)
    rng = random.Random(salt & 0xFFFFFFFFFFFFFFFF)

    label = _weighted_pick(rng, _COHORT_WEIGHTS)
    preset = dict(_COHORT_PRESETS[label])

    base_sens = float(preset.pop("price_sensitivity"))
    price_sensitivity = max(0.0, min(1.0, rng.gauss(base_sens, 0.10)))

    brand_affinity = ""
    if brand_pool:
        brand_affinity = brand_pool[rng.randrange(len(brand_pool))]

    return {
        "cohort": label,
        "price_sensitivity": round(price_sensitivity, 3),
        "brand_affinity": brand_affinity,
        **preset,
    }
