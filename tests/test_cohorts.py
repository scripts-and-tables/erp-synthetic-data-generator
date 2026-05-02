"""Tests for the deterministic cohort assignment."""
from __future__ import annotations

from collections import Counter

import pytest

from erp_synth.cohorts import COHORT_LABELS, assign_cohort

REQUIRED_KEYS = {
    "cohort", "price_sensitivity", "brand_affinity",
    "p_buy_by_year", "p_close_day", "p_invoice_by_nth",
    "p_device_by_nth", "refill_count_probs",
    "p_refill_invoice", "p_accessory_invoice", "p_spare_part_invoice",
}


def test_assign_cohort_returns_required_keys():
    spec = assign_cohort(1, seed=42)
    missing = REQUIRED_KEYS - spec.keys()
    assert not missing, f"missing keys: {missing}"


def test_cohort_label_is_one_of_six():
    spec = assign_cohort(1, seed=42)
    assert spec["cohort"] in COHORT_LABELS


def test_assignment_is_deterministic_per_customer():
    a = assign_cohort(123, seed=42)
    b = assign_cohort(123, seed=42)
    assert a["cohort"] == b["cohort"]
    assert a["price_sensitivity"] == b["price_sensitivity"]


def test_different_customers_can_get_different_cohorts():
    cohorts = {assign_cohort(cid, seed=42)["cohort"] for cid in range(1, 200)}
    assert len(cohorts) >= 4, "expected 4+ distinct cohorts across 200 customers"


def test_all_six_cohorts_realized_in_large_sample():
    counts = Counter(assign_cohort(cid, seed=42)["cohort"] for cid in range(1, 2001))
    assert set(counts) == set(COHORT_LABELS)


def test_price_sensitivity_in_unit_interval():
    for cid in range(1, 100):
        spec = assign_cohort(cid, seed=42)
        assert 0.0 <= spec["price_sensitivity"] <= 1.0


def test_brand_affinity_drawn_from_pool():
    pool = ["FreshNest", "AromaDrive", "BreezeLine"]
    for cid in range(1, 50):
        spec = assign_cohort(cid, seed=42, brand_pool=pool)
        assert spec["brand_affinity"] in pool


def test_brand_affinity_empty_when_no_pool():
    spec = assign_cohort(1, seed=42, brand_pool=None)
    assert spec["brand_affinity"] == ""


def test_changing_seed_changes_cohort_distribution():
    a = Counter(assign_cohort(cid, seed=1)["cohort"] for cid in range(1, 1001))
    b = Counter(assign_cohort(cid, seed=999)["cohort"] for cid in range(1, 1001))
    assert a != b


@pytest.mark.parametrize("cohort_label", COHORT_LABELS)
def test_each_cohort_has_consistent_behavior_knobs(cohort_label):
    """Find a customer with each cohort and check knob shapes."""
    found = None
    for cid in range(1, 5000):
        spec = assign_cohort(cid, seed=42)
        if spec["cohort"] == cohort_label:
            found = spec
            break
    assert found is not None
    assert isinstance(found["p_buy_by_year"], list) and len(found["p_buy_by_year"]) >= 1
    assert 0.0 < found["p_close_day"] < 0.01
    assert 0.0 < found["p_refill_invoice"] <= 1.0
