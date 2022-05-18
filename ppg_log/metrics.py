from __future__ import annotations

import typing as t
from enum import IntEnum

if t.TYPE_CHECKING:
    import pandas as pd

ROLLING_WINDOW_WIDTH = 5
LANDED_THRESHOLD_MPS = 2.235


class FlightMode(IntEnum):  # noqa: D101
    GROUND = 0
    AIRBORNE = 1


def _classify_flight_mode(
    total_velocity: float, airborne_threshold: float = LANDED_THRESHOLD_MPS
) -> FlightMode:
    """"""
    if total_velocity >= airborne_threshold:
        return FlightMode.AIRBORNE
    else:
        return FlightMode.GROUND


def classify_flight(
    flight_log: pd.DataFrame, window_width: int = ROLLING_WINDOW_WIDTH
) -> pd.DataFrame:
    """"""
    flight_log["flight_mode"] = (
        flight_log["total_vel"].rolling(window_width).mean().apply(_classify_flight_mode)
    )

    return flight_log
