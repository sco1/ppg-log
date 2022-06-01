from __future__ import annotations

import datetime as dt
import typing as t
from collections import deque
from dataclasses import dataclass
from enum import IntEnum
from functools import cached_property, partial
from itertools import zip_longest

import humanize
import numpy as np

from ppg_log import parser, viz

if t.TYPE_CHECKING:
    from pathlib import Path

    import pandas as pd

    from ppg_log import db

START_TRIM = 45  # seconds
ROLLING_WINDOW_WIDTH = 5
AIRBORNE_THRESHOLD = 2.235  # Groundspeed, m/s
FLIGHT_LENGTH_THRESHOLD = 15  # seconds

NUMERIC_T = int | float

LOG_DATETIME_FMT = r"%Y-%m-%d_%H-%M-%S"

HUMANIZED_DELTA = partial(humanize.precisedelta, minimum_unit="seconds", format="%d")


class FlightMode(IntEnum):  # noqa: D101
    GROUND = 0
    AIRBORNE = 1


@dataclass(frozen=True, slots=True)
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


@dataclass(slots=True)
class LogMetadata:  # noqa: D101
    log_date: str
    log_time: str

    # Flight quantities are calculated downstream
    n_flight_segments: int | None = None  # If None, no metrics calculations have been done
    total_flight_time: dt.timedelta = dt.timedelta()
    flight_segments: list[FlightSegment] | None = None

    def __str__(self) -> str:  # pragma: no cover
        if self.flight_segments:
            humanized_time = HUMANIZED_DELTA(self.total_flight_time)
        else:
            humanized_time = "No flights detected"

        return (
            f"Log Date: {self.log_date} {self.log_time}\n"
            f"Flight Segments: {self.n_flight_segments}\n"
            f"Total Flight Time: {humanized_time}"
        )


@dataclass  # Can't slot w/cached_property
class FlightLog:  # noqa: D101
    flight_data: pd.DataFrame
    metadata: LogMetadata

    def __str__(self) -> str:  # pragma: no cover
        return str(self.metadata)

    @cached_property
    def log_datetime(self) -> dt.datetime:
        """Generate a `datetime` instance from the `FlightLog`'s metadata."""
        datestr = f"{self.metadata.log_date}_{self.metadata.log_time}"
        return dt.datetime.strptime(datestr, LOG_DATETIME_FMT)

    def summary_plot(
        self, show_plot: bool = True, save_dir: Path | None = None
    ) -> None:  # pragma: no cover
        """Build a summary plot for optional display and/or output to an image file."""
        if save_dir is not None:
            filename = f"{self.metadata.log_date}_{self.metadata.log_time}.png"
            save_path = save_dir / filename
        else:
            save_path = None

        viz.summary_plot(self, save_path=save_path, show_plot=show_plot)


@dataclass(frozen=True, slots=True)
class LogSummary:  # noqa: D101
    n_logs: int

    # If these are None, no metrics calculations have been done
    n_flight_segments: int | None
    total_flight_time: dt.timedelta | None
    avg_flight_time: dt.timedelta | None
    shortest_flight: dt.timedelta | None
    longest_flight: dt.timedelta | None

    def __str__(self) -> str:  # pragma: no cover
        if self.total_flight_time:
            total_time = HUMANIZED_DELTA(self.total_flight_time)
            avg_time = HUMANIZED_DELTA(self.avg_flight_time)
            shortest_time = HUMANIZED_DELTA(self.shortest_flight)
            longest_time = HUMANIZED_DELTA(self.longest_flight)

            humanized_time = (
                f"    Total Flight Time: {total_time}\n"
                f"    Average Flight Time: {avg_time}\n"
                f"    Shortest Flight: {shortest_time}\n"
                f"    Longest Flight: {longest_time}\n"
            )
        else:
            humanized_time = "    No flights detected or flight metrics not yet calculated."

        return f"Log Summary:\n    Flight Logs: {self.n_logs}\n{humanized_time}"

    @classmethod
    def from_flight_logs(cls, flight_logs: t.Collection[FlightLog]) -> LogSummary:
        """Generate a `LogSummary` instance from the provided `FlightLog` instances."""
        if not flight_logs:
            raise ValueError("No flight logs provided.")

        n_segments = 0
        flight_time = dt.timedelta()
        shortest = dt.timedelta()
        longest = dt.timedelta()
        for log in flight_logs:
            if log.metadata.n_flight_segments is not None:
                n_segments += log.metadata.n_flight_segments

                if log.metadata.flight_segments:  # pragma: no branch
                    for segment in log.metadata.flight_segments:
                        flight_time += segment.duration

                        if shortest == dt.timedelta() or segment.duration < shortest:
                            shortest = segment.duration

                        if segment.duration > longest:
                            longest = segment.duration
        else:
            if flight_time == dt.timedelta():
                total_flight_time = None
            else:
                total_flight_time = flight_time

        if total_flight_time is not None and n_segments is not None:
            avg_flight_time = dt.timedelta(seconds=total_flight_time.total_seconds() / n_segments)
            shortest_flight = shortest
            longest_flight = longest
        else:
            avg_flight_time = None
            shortest_flight = None
            longest_flight = None

        return cls(
            n_logs=len(flight_logs),
            n_flight_segments=n_segments if n_segments else None,
            total_flight_time=total_flight_time,
            avg_flight_time=avg_flight_time,
            shortest_flight=shortest_flight,
            longest_flight=longest_flight,
        )

    @classmethod
    def from_flight_log(cls, flight_log: FlightLog) -> LogSummary:
        """Generate a `LogSummary` instance from the provided `FlightLog` instance."""
        return cls.from_flight_logs([flight_log])

    @classmethod
    def from_db_query(cls, db_data: db.SummaryTuple) -> LogSummary:
        """Generate a `LogSummary` instance from the provided DB query response."""
        avg_flight_time = dt.timedelta(
            seconds=db_data.total_flight_time.total_seconds() / db_data.n_flight_segments
        )

        shortest = dt.timedelta()
        longest = dt.timedelta()
        for segment in db_data.flight_segments:
            if shortest == dt.timedelta() or segment < shortest:
                shortest = segment

            if segment > longest:
                longest = segment

        return cls(
            n_logs=db_data.n_logs,
            n_flight_segments=db_data.n_flight_segments,
            total_flight_time=db_data.total_flight_time,
            avg_flight_time=avg_flight_time,
            shortest_flight=shortest,
            longest_flight=longest,
        )


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
    airborne_threshold: NUMERIC_T = AIRBORNE_THRESHOLD,
    time_threshold: NUMERIC_T = FLIGHT_LENGTH_THRESHOLD,
    start_trim: NUMERIC_T = START_TRIM,
    classify_segments: bool = True,
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
    log_pattern: str = r"*.CSV",
    start_trim: NUMERIC_T = START_TRIM,
    airborne_threshold: NUMERIC_T = AIRBORNE_THRESHOLD,
    time_threshold: NUMERIC_T = FLIGHT_LENGTH_THRESHOLD,
    classify_segments: bool = True,
    verbose: bool = True,
) -> list[FlightLog]:
    """
    Batch process pipeline for a directory of FlySight logs.

    Log file discovery is not recursive by default, the `log_pattern` kwarg can be adjusted to
    support a recursive glob.

    NOTE: File case sensitivity is deferred to the OS; `log_pattern` is passed to glob as-is so
    matches may or may not be case-sensitive.
    """
    # Listify flight logs to get a total count
    log_files = list(top_dir.glob(log_pattern))
    if verbose:
        print(f"Found {len(log_files)} log files to process.")

    parsed_logs = []
    for log_file in log_files:
        if verbose:
            print(f"Processing {log_file.parent.stem}/{log_file.name} ... ", end="")

        flight_log = process_log(
            log_file,
            start_trim=start_trim,
            airborne_threshold=airborne_threshold,
            time_threshold=time_threshold,
            classify_segments=classify_segments,
        )
        parsed_logs.append(flight_log)

        if verbose:
            print("Done")

    return parsed_logs
