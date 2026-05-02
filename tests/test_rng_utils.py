"""Tests for the seeded RNG plumbing."""
from __future__ import annotations

from erp_synth.rng_utils import RNGs, derive, make_rngs


def test_make_rngs_returns_rngs_dataclass():
    r = make_rngs(42)
    assert isinstance(r, RNGs)
    assert r.seed == 42


def test_same_seed_produces_same_outputs():
    a, b = make_rngs(7), make_rngs(7)
    assert a.py.random() == b.py.random()
    assert (a.np.random(10) == b.np.random(10)).all()


def test_different_seeds_produce_different_outputs():
    a, b = make_rngs(1), make_rngs(2)
    # Vanishingly unlikely both first draws coincide
    assert a.py.random() != b.py.random()


def test_derive_deterministic():
    base = make_rngs(42)
    a = derive(base, 100)
    b = derive(base, 100)
    assert a.py.random() == b.py.random()


def test_derive_isolated_from_base():
    base = make_rngs(42)
    child = derive(base, 999)
    assert child.seed != base.seed
