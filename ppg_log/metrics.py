from __future__ import annotations

import datetime as dt
import typing as t
from collections import deque
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
AIRBORNE_THRESHOLD = 2.235  # Groundspeed, m/s
FLIGHT_LENGTH_THRESHOLD = 15  # seconds

NUMERIC_T = int | float


class FlightMode(IntEnum):  # noqa: D101
    GROUND = 0
    AIRBORNE = 1


@dataclass
class FlightSegment:  # noqa: D101
    start_idx: int
    end_idx: int
    duration: dt.timedelta

    def __str__(self) -> str:  # pragma: no cover
        return (
            f"Start idx: {self.start_idx}\n"
            f"End idx: {self.end_idx}\n"
            f"Duration: {self.duration.seconds} seconds"
        )


@dataclass
class LogMetadata:  # noqa: D101
    log_date: str
    log_time: str

    # Flight quantities are calculated downstream
    n_flight_segments: int | None = None  # If None, no metrics calculations have been done
    total_flight_time: dt.timedelta = dt.timedelta()
    flight_segments: list[FlightSegment] | None = None

    def __str__(self) -> str:  # pragma: no cover
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

    @property
    def log_datetime(self) -> dt.datetime:
        """Generate a `datetime` instance from the `FlightLog`'s metadata."""
        datestr = f"{self.metadata.log_date}_{self.metadata.log_time}"
        return dt.datetime.strptime(datestr, r"%y-%m-%d_%H-%M-%S")


def _classify_flight_mode(groundspeed: float, airborne_threshold: NUMERIC_T) -> FlightMode:
    """Classify inflight vs. on ground based on the provided groundspeed threshold."""
    if groundspeed >= airborne_threshold:
        return FlightMode.AIRBORNE
    else:
        return FlightMode.GROUND


def classify_flight(
    flight_log: pd.DataFrame,
    window_width: int = ROLLING_WINDOW_WIDTH,
    airborne_threshold: NUMERIC_T = AIRBORNE_THRESHOLD,
) -> pd.DataFrame:
    """
    Classify inflight vs. on ground for the provided flight log based on groundspeed.

    To address noise in the groundspeed measurements, a rolling window mean of `window_width`
    groundspeeds is passed to the flight mode classifier.
    """
    flight_log["flight_mode"] = (
        flight_log["groundspeed"]
        .rolling(window_width, min_periods=1)
        .mean()
        .apply(_classify_flight_mode, airborne_threshold=airborne_threshold)
    )

    return flight_log


def _segment_flights(
    flight_data: pd.DataFrame, start_trim: NUMERIC_T
) -> tuple[list[list[int]], list[NUMERIC_T]]:
    """
    Identify candidate flight segments from the provided flight data.

    A list of `[takeoff, landing]` indices is returned along with a list of the time deltas, as
    decimal seconds, from the end of a segment to the beginning of the next segment.
    """
    elapsed_time = flight_data["elapsed_time"]

    # Find the trim index
    trim_idx = (elapsed_time >= start_trim).idxmax()

    # Find consecutive runs of inflight modes & group by start & end indices of each run
    # AKA find takeoffs & landings
    diffs = np.abs(np.diff(flight_data["flight_mode"].iloc[trim_idx:]))
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

    # Cast flights to a list on return so I don't have to deal the huge cascade of mypy errors from
    # trying to use an ndarray with zip_longest
    return flights.tolist(), next_segment_delta


def find_flights(
    flight_data: pd.DataFrame, time_threshold: NUMERIC_T, start_trim: NUMERIC_T
) -> list[FlightSegment] | None:
    """
    Identify start & end indices of flight segments for the provided flight log.

    Some basic filtering is done on candidate flight segments to help mitigate false positives from
    groundspeed instability.

    There are 2 classifications for short-duration segments:
        1. Transient spike while firmly on the ground, these should be discarded
        2. Noise while taking off, in flight, or while landing, these should be retained

    `time_threshold`, in seconds, is used to help classify short-duration segments as well as
    identify when the pilot has landed.

    `start_trim`, in seconds, is used to exclude segments from the beginning of the data file.
    """
    elapsed_time = flight_data["elapsed_time"]

    flight_segments, next_segment_delta = _segment_flights(flight_data, start_trim)
    if len(flight_segments) == 0:
        return None

    valid_flights = []
    flight_indices: deque[int] = deque()
    for (segment_start, segment_end), next_delta in zip_longest(
        flight_segments, next_segment_delta
    ):
        segment_duration = elapsed_time.iloc[segment_end] - elapsed_time.iloc[segment_start]
        if next_delta is not None and (segment_duration < time_threshold):
            # Check for transient spikes
            # These are below the duration threshold & distant from the next flight segment
            if not flight_indices and (next_delta >= time_threshold):
                flight_indices.clear()
                continue
            else:
                # Otherwise, we'll consider this segment as part of the current flight segment
                flight_indices.extend((segment_start, segment_end))
        else:
            # This is a valid flight segment and/or the last segment in the file
            flight_indices.extend((segment_start, segment_end))

        # Now check the time to the next flight segment to see if we've landed
        if next_delta is None or (next_delta >= time_threshold):
            takeoff_idx = flight_indices[0]
            landing_idx = flight_indices[-1]
            flight_indices.clear()

            # Transient spikes may be close enough to combine into a segment that's shorter than the
            # time threshold, or may end up at the very end of the file
            # This can be discarded
            flight_duration = dt.timedelta(
                seconds=elapsed_time.iloc[landing_idx] - elapsed_time.iloc[takeoff_idx]
            )
            if flight_duration.total_seconds() < time_threshold:
                continue

            valid_flights.append(FlightSegment(takeoff_idx, landing_idx, flight_duration))

    if len(valid_flights) == 0:
        return None
    else:
        return valid_flights


def generate_flight_metrics(
    flight_log: FlightLog,
    airborne_threshold: NUMERIC_T,
    time_threshold: NUMERIC_T,
    start_trim: NUMERIC_T,
    classify_segments: bool,
) -> FlightLog:
    """Generate flight segment information for the provided `FlightLog` instance."""
    flight_log.flight_data = classify_flight(
        flight_log.flight_data, airborne_threshold=airborne_threshold
    )

    if classify_segments:
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
    classify_segments: bool = True,
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
        classify_segments=classify_segments,
    )

    return flight_log


def batch_process(
    top_dir: Path,
    save_dir: Path | None = None,
    log_pattern: str = r"*.CSV",
    start_trim: NUMERIC_T = START_TRIM,
    airborne_threshold: NUMERIC_T = AIRBORNE_THRESHOLD,
    time_threshold: NUMERIC_T = FLIGHT_LENGTH_THRESHOLD,
    classify_segments: bool = True,
) -> None:
    """
    Batch process FlySight logs matching the provided `log_pattern` relative to `top_dir`.

    Flight logs are parsed & a summary plot output generated. If `save_dir` is specified, it is used
    as the base directory for the plot outputs, otherwise the outputs are saved to the same
    directory as the parsed log file.
    """
    # Listify flight logs to get a total count
    log_files = list(top_dir.glob(log_pattern))
    print(f"Found {len(log_files)} log files to process.")

    # Iterate per flight log so we're not loading every log into memory at once
    for log_file in log_files:
        print(f"Processing {log_file.parent.stem}/{log_file.name} ... ", end="")

        flight_log = process_log(
            log_file,
            start_trim=start_trim,
            airborne_threshold=airborne_threshold,
            time_threshold=time_threshold,
            classify_segments=classify_segments,
        )

        if save_dir is None:
            parent = log_file.parent
        else:
            parent = save_dir

        save_path = parent / f"{flight_log.metadata.log_date}_{flight_log.metadata.log_time}.png"
        viz.summary_plot(flight_log, save_path=save_path)

        print("Done")
