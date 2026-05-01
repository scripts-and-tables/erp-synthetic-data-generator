"""Centralized seeded RNGs threaded through every generator."""
from __future__ import annotations

import random
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class RNGs:
    py: random.Random
    np: np.random.Generator
    seed: int


def make_rngs(seed: int) -> RNGs:
    return RNGs(py=random.Random(seed), np=np.random.default_rng(seed), seed=int(seed))


def derive(rngs: RNGs, salt: int) -> RNGs:
    """Deterministic child RNG. Use for per-customer or per-stage isolation."""
    s = (rngs.seed ^ (int(salt) * 2654435761)) & 0xFFFFFFFF
    return make_rngs(s)
