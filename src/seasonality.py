"""Daily seasonality multiplier: month × day-of-week × holiday bump."""
from __future__ import annotations

from datetime import date
from typing import Any

from .markets import holidays_for_year


def combined_multiplier(d: date, market_cfg: dict[str, Any]) -> float:
    """Multiply baseline daily buy probability by this factor."""
    month_factor = market_cfg["month_factor"][d.month]
    dow_factor = market_cfg["dow_factor"][d.weekday()]
    holiday_factor = holidays_for_year(market_cfg, d.year).get(d, 1.0)
    return float(month_factor) * float(dow_factor) * float(holiday_factor)
