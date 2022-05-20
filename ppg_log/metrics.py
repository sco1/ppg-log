from __future__ import annotations

import datetime as dt
import typing as t
from dataclasses import dataclass
from enum import IntEnum
from itertools import zip_longest

import humanize
import numpy as np

from ppg_log import parser, viz

if t.TYPE_CHECKING:
    from pathlib import Path

    import pandas as pd

START_TRIM = 45  # seconds
ROLLING_WINDOW_WIDTH = 5
AIRBORNE_THRESHOLD = 2.235  # m/s
FLIGHT_LENGTH_THRESHOLD = 10  # seconds

NUMERIC_T = int | float


class FlightMode(IntEnum):  # noqa: D101
    GROUND = 0
    AIRBORNE = 1


@dataclass
class FlightSegment:  # noqa: D101
    start_idx: int
    end_idx: int
    duration: dt.timedelta


@dataclass
class LogMetadata:  # noqa: D101
    log_date: str
    log_time: str

    # Flight quantities are calculated downstream
    n_flight_segments: int | None = None  # If None, no metrics calculations have been done
    total_flight_time: dt.timedelta | None = None  # If None, no metrics calculations have been done
    flight_segments: list[FlightSegment] | None = None

    def __str__(self) -> str:
        if self.flight_segments:
            humanized_time = humanize.precisedelta(
                self.total_flight_time, minimum_unit="seconds", format="%d"
            )
        else:
            humanized_time = "No flights detected"

        return (
            f"Log Date: {self.log_date} {self.log_time}\n"
            f"Flight Segments: {self.n_flight_segments}\n"
            f"Total Flight Time: {humanized_time}"
        )


@dataclass
class FlightLog:  # noqa: D101
    flight_data: pd.DataFrame
    metadata: LogMetadata


def _classify_flight_mode(total_velocity: float, airborne_threshold: NUMERIC_T) -> FlightMode:
    """Classify inflight vs. on ground based on the provided velocity threshold."""
    if total_velocity >= airborne_threshold:
        return FlightMode.AIRBORNE
    else:
        return FlightMode.GROUND


def classify_flight(
    flight_log: pd.DataFrame,
    window_width: int = ROLLING_WINDOW_WIDTH,
    airborne_threshold: NUMERIC_T = AIRBORNE_THRESHOLD,
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
    flight_log: pd.DataFrame, time_threshold: NUMERIC_T, start_trim: NUMERIC_T
) -> list[FlightSegment] | None:
    """
    Identify start & end indices of flight segments for the provided flight log.

    To account for velocity instabilities (seen primarily during takeoffs), flight segments whose
    length is below the specified minimum `time_threshold` are merged into the next found flight
    segment whose length exceeds the threshold.
    """
    elapsed_time = flight_log["elapsed_time"]

    # Find the trim index
    trim_idx = (elapsed_time >= start_trim).idxmax()

    # Find consecutive runs of inflight modes & group by start & end indices of each run
    # AKA find takeoffs & landings
    diffs = np.abs(np.diff(flight_log["flight_mode"].iloc[trim_idx:]))
    diffs[0] = 0
    # Offset by the trim index since numpy's indices will be relative to the slice
    flights = np.flatnonzero(diffs == 1) + trim_idx

    # Calculate time delta between flight segments, then reshape into nx2 for segment indices
    next_segment_delta = []
    for current_end, next_start in zip(
        elapsed_time.iloc[flights[1:-1:2]], elapsed_time.iloc[flights[2::2]]
    ):
        next_segment_delta.append(next_start - current_end)

    flights = flights.reshape(-1, 2)
    if flights.size == 0:
        return None

    # Iterate through flights & merge takeoff noise into the actual flight segment
    valid_flights = []
    merging = False
    for (segment_start, segment_end), next_delta in zip_longest(flights, next_segment_delta):
        if not merging:
            flight_start = segment_start

        segment_time = elapsed_time.iloc[segment_end] - elapsed_time.iloc[segment_start]

        if segment_time < time_threshold:
            merging = True
            continue

        # Inside a valid flight segment, check delta to next segment to see if this is contains the
        # actual landing or if it's just some other flight mode noise
        # If next_delta is None then we're in the last segment
        if next_delta is None or next_delta >= time_threshold:
            merging = False
        else:
            continue

        flight_duration = dt.timedelta(
            seconds=elapsed_time.iloc[segment_end] - elapsed_time.iloc[flight_start]
        )
        valid_flights.append(
            FlightSegment(start_idx=flight_start, end_idx=segment_end, duration=flight_duration)
        )

    if len(valid_flights) == 0:
        return None
    else:
        return valid_flights


def generate_flight_metrics(
    flight_log: FlightLog,
    airborne_threshold: NUMERIC_T,
    time_threshold: NUMERIC_T,
    start_trim: NUMERIC_T,
) -> FlightLog:
    """Generate flight segment information for the provided `FlightLog` instance."""
    flight_log.flight_data = classify_flight(
        flight_log.flight_data, airborne_threshold=airborne_threshold
    )

    flight_log.metadata.flight_segments = find_flights(
        flight_log.flight_data, time_threshold=time_threshold, start_trim=start_trim
    )
    if flight_log.metadata.flight_segments:
        flight_log.metadata.n_flight_segments = len(flight_log.metadata.flight_segments)
        flight_log.metadata.total_flight_time = sum(
            (segment.duration for segment in flight_log.metadata.flight_segments),
            start=dt.timedelta(),
        )
    else:
        flight_log.metadata.n_flight_segments = 0
        flight_log.metadata.total_flight_time = dt.timedelta()

    return flight_log


def process_log(
    log_file: Path,
    start_trim: NUMERIC_T = START_TRIM,
    airborne_threshold: NUMERIC_T = AIRBORNE_THRESHOLD,
    time_threshold: NUMERIC_T = FLIGHT_LENGTH_THRESHOLD,
) -> FlightLog:
    """Processing pipeline for an individual FlySight log file."""
    # Log files are grouped by date, need to retain this since it's not in the CSV filename
    log_date = log_file.parent.stem
    log_time = log_file.stem
    flight_log = FlightLog(
        flight_data=parser.load_flysight(log_file),
        metadata=LogMetadata(log_date=log_date, log_time=log_time),
    )
    flight_log = generate_flight_metrics(
        flight_log,
        airborne_threshold=airborne_threshold,
        time_threshold=time_threshold,
        start_trim=start_trim,
    )

    return flight_log


def batch_process(
    top_dir: Path,
    log_pattern: str = r"*.CSV",
    start_trim: NUMERIC_T = START_TRIM,
    airborne_threshold: NUMERIC_T = AIRBORNE_THRESHOLD,
    time_threshold: NUMERIC_T = FLIGHT_LENGTH_THRESHOLD,
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
        flight_log = process_log(
            log_file,
            start_trim=start_trim,
            airborne_threshold=airborne_threshold,
            time_threshold=time_threshold,
        )

        save_path = (
            log_file.parent / f"{flight_log.metadata.log_date}_{flight_log.metadata.log_time}.png"
        )
        viz.summary_plot(flight_log, save_path=save_path)
    else:
        print("Done!")
