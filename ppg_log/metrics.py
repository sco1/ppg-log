from __future__ import annotations

import typing as t
from enum import IntEnum

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from ppg_log import parser
from ppg_log.parser import START_TRIM

if t.TYPE_CHECKING:
    from pathlib import Path

pd.options.plotting.backend = "plotly"

ROLLING_WINDOW_WIDTH = 5
AIRBORNE_THRESHOLD_MPS = 2.235
FLIGHT_LENGTH_THRESHOLD = 10


class FlightMode(IntEnum):  # noqa: D101
    GROUND = 0
    AIRBORNE = 1


def _classify_flight_mode(total_velocity: float, airborne_threshold: int | float) -> FlightMode:
    """Classify inflight vs. on ground based on the provided velocity threshold."""
    if total_velocity >= airborne_threshold:
        return FlightMode.AIRBORNE
    else:
        return FlightMode.GROUND


def classify_flight(
    flight_log: pd.DataFrame,
    window_width: int = ROLLING_WINDOW_WIDTH,
    airborne_threshold: int | float = AIRBORNE_THRESHOLD_MPS,
) -> pd.DataFrame:
    """
    Classify inflight vs. on ground for the provided flight log based on total velocity.

    To address noise in the velocity measurements, a rolling window mean of `window_width` total
    velocitiey is passed to the flight mode classifier.
    """
    flight_log["flight_mode"] = (
        flight_log["total_vel"]
        .rolling(window_width, min_periods=1)
        .mean()
        .apply(_classify_flight_mode, airborne_threshold=airborne_threshold)
    )

    return flight_log


def find_flights(
    flight_log: pd.DataFrame, time_threshold: int = FLIGHT_LENGTH_THRESHOLD
) -> list[tuple[int, int]] | None:
    """
    Identify start & end indices of flight segments for the provided flight log.

    To account for velocity instabilities (seen primarily during takeoffs), flight segments whose
    length is below the specified minimum `time_threshold` are merged into the next found flight
    segment whose length exceeds the threshold.
    """
    # Find consecutive runs of inflight modes & group by start & end indices of each run
    # AKA find takeoffs & landings
    diffs = np.abs(np.diff(flight_log["flight_mode"]))
    diffs[0] = 0
    flights = np.flatnonzero(diffs == 1).reshape(-1, 2)

    if flights.size == 0:
        return None

    # Iterate through flights & merge takeoff noise into the actual flight segment
    valid_flights = []
    merging = False
    for segment_start, segment_end in flights:
        if not merging:
            flight_start = segment_start

        segment_time = (
            flight_log["elapsed_time"].iloc[segment_end]
            - flight_log["elapsed_time"].iloc[segment_start]
        )

        # Flight length below threshold, end idx is discarded & we merge this segment into the next
        # actual flight
        if segment_time < time_threshold:
            merging = True
            continue

        valid_flights.append((flight_start, segment_end))
        merging = False

    if len(valid_flights) == 0:
        return None
    else:
        return valid_flights


def build_summary_plot(
    flight_log: pd.DataFrame, save_path: Path | None = None, show_plot: bool = False
) -> None:
    """
    Build a plot for the provided flight log showing basic flight information.

    Currently visualized quantities:
        * Total velocity (m/s)
        * Altitude (m MSL)
        * Derived flight mode

    If `save_path` is specified, the plot is saved as an image file to the specified path. Any
    existing plot is overwritten.

    If `show_plot` is `True`, the plot is displayed on screen.
    """
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(x=flight_log["elapsed_time"], y=flight_log["total_vel"], name="Total Velocity")
    )
    fig.add_trace(
        go.Scatter(
            x=flight_log["elapsed_time"], y=flight_log["hMSL"], name="Altitude (m MSL)", yaxis="y2"
        ),
    )
    fig.add_trace(
        go.Scatter(
            x=flight_log["elapsed_time"],
            y=flight_log["flight_mode"],
            name="Flight Mode",
            yaxis="y3",
        ),
    )

    fig.update_layout(
        xaxis={"title": "Elapsed Time (s)", "domain": [0, 0.75]},
        yaxis={"title": "Total Velocity (m/s)"},
        yaxis2={
            "title": "Altitude (m MSL)",
            "anchor": "x",
            "overlaying": "y",
            "side": "right",
        },
        yaxis3={
            "title": "Flight Mode",
            "anchor": "free",
            "overlaying": "y",
            "side": "right",
            "position": 0.85,
            "nticks": 2,
        },
    )

    if save_path:
        fig.write_image(save_path)

    if show_plot:
        fig.show()


def batch_process(
    top_dir: Path,
    log_pattern: str = r"*.CSV",
    start_trim: int = START_TRIM,
    airborne_threshold: int | float = AIRBORNE_THRESHOLD_MPS,
) -> None:
    """
    Batch process FlySight logs matching the provided `log_pattern` relative to `top_dir`.

    Flight logs are parsed & a summary plot output to the same directory as the parsed FlySight log
    file.
    """
    # Listify flight logs to get a total count
    log_files = list(top_dir.glob(log_pattern))
    print(f"Found {len(log_files)} log files to process ...", end="")

    # Iterate per flight log so we're not loading every log into memory at once
    for log_file in log_files:
        flight_log = parser.load_flysight(log_file, start_trim=start_trim)
        flight_log = classify_flight(flight_log, airborne_threshold=airborne_threshold)

        # Log files are grouped by date, need to retain this since it's not in the CSV filename
        log_date = log_file.parent.stem
        log_time = log_file.stem
        save_path = log_file.parent / f"{log_date}_{log_time}.png"
        build_summary_plot(flight_log, save_path=save_path, show_plot=False)
    else:
        print("Done!")
