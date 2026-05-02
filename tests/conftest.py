"""Shared pytest fixtures."""
from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from erp_synth.items import build_items_universe_df, sample_items_dataset_df
from erp_synth.markets import get_market
from erp_synth.rng_utils import make_rngs


@pytest.fixture
def seed() -> int:
    return 42


@pytest.fixture
def rngs(seed: int):
    return make_rngs(seed)


@pytest.fixture
def market_us() -> dict:
    return get_market("us")


@pytest.fixture
def market_gcc() -> dict:
    return get_market("gcc")


@pytest.fixture
def market_eu() -> dict:
    return get_market("eu")


@pytest.fixture
def date_from() -> date:
    return date(2023, 1, 1)


@pytest.fixture
def date_till() -> date:
    return date(2024, 12, 31)


@pytest.fixture
def items_universe() -> pd.DataFrame:
    return build_items_universe_df()


@pytest.fixture
def items_df(items_universe, rngs, market_us, date_from) -> pd.DataFrame:
    """Small items dataset for unit tests."""
    return sample_items_dataset_df(
        items_universe,
        n_devices=5, n_accessories=10, n_spare_parts=8,
        n_refills=20, n_bulk_refills=1,
        rng=rngs.py,
        currency=market_us["currency"],
        listed_from_floor=date_from,
        listing_window_days=30,
    )
