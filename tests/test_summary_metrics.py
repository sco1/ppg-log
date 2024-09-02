import datetime as dt
from functools import partial

import pytest

from ppg_log import db
from ppg_log.metrics import FlightLog, FlightSegment, LogMetadata, LogSummary

DUMMY_DURATION = dt.timedelta(seconds=5)
PARTIAL_SEGMENT = partial(FlightSegment, start_idx=-1, end_idx=-1)
PARTIAL_META = partial(LogMetadata, log_date="2022-04-20", log_time="04-20-00")
PARTIAL_LOG = partial(FlightLog, flight_data=None)


METADATA_CASES = (
    (
        PARTIAL_LOG(metadata=PARTIAL_META()),  # No metrics calculated
        LogSummary(
            n_logs=1,
            n_flight_segments=None,
            total_flight_time=None,
            avg_flight_time=None,
            shortest_flight=None,
            longest_flight=None,
        ),
    ),
    (
        PARTIAL_LOG(
            metadata=PARTIAL_META(
                n_flight_segments=1,
                total_flight_time=DUMMY_DURATION,
                flight_segments=[PARTIAL_SEGMENT(duration=DUMMY_DURATION)],
            )
        ),
        LogSummary(
            n_logs=1,
            n_flight_segments=1,
            total_flight_time=DUMMY_DURATION,
            avg_flight_time=DUMMY_DURATION,
            shortest_flight=DUMMY_DURATION,
            longest_flight=DUMMY_DURATION,
        ),
    ),
    (
        PARTIAL_LOG(
            metadata=PARTIAL_META(
                n_flight_segments=2,
                total_flight_time=DUMMY_DURATION,
                flight_segments=[
                    PARTIAL_SEGMENT(duration=DUMMY_DURATION),
                    PARTIAL_SEGMENT(duration=dt.timedelta(seconds=3)),
                ],
            )
        ),
        LogSummary(
            n_logs=1,
            n_flight_segments=2,
            total_flight_time=dt.timedelta(seconds=8),
            avg_flight_time=dt.timedelta(seconds=4),
            shortest_flight=dt.timedelta(seconds=3),
            longest_flight=DUMMY_DURATION,
        ),
    ),
)


@pytest.mark.parametrize(("flight_log, truth_summary"), METADATA_CASES)
def test_log_summary(flight_log: FlightLog, truth_summary: LogSummary) -> None:
    assert LogSummary.from_flight_log(flight_log) == truth_summary


BATCH_METADATA_CASES = (
    (
        [
            PARTIAL_LOG(
                metadata=PARTIAL_META(
                    n_flight_segments=1,
                    total_flight_time=DUMMY_DURATION,
                    flight_segments=[PARTIAL_SEGMENT(duration=DUMMY_DURATION)],
                )
            ),
            PARTIAL_LOG(
                metadata=PARTIAL_META(
                    n_flight_segments=None,
                    flight_segments=None,
                )
            ),
        ],
        LogSummary(
            n_logs=2,
            n_flight_segments=1,
            total_flight_time=DUMMY_DURATION,
            avg_flight_time=DUMMY_DURATION,
            shortest_flight=DUMMY_DURATION,
            longest_flight=DUMMY_DURATION,
        ),
    ),
    (
        [
            PARTIAL_LOG(
                metadata=PARTIAL_META(
                    n_flight_segments=1,
                    total_flight_time=DUMMY_DURATION,
                    flight_segments=[PARTIAL_SEGMENT(duration=DUMMY_DURATION)],
                )
            ),
            PARTIAL_LOG(
                metadata=PARTIAL_META(
                    n_flight_segments=1,
                    total_flight_time=DUMMY_DURATION,
                    flight_segments=[PARTIAL_SEGMENT(duration=DUMMY_DURATION)],
                )
            ),
        ],
        LogSummary(
            n_logs=2,
            n_flight_segments=2,
            total_flight_time=dt.timedelta(seconds=10),
            avg_flight_time=DUMMY_DURATION,
            shortest_flight=DUMMY_DURATION,
            longest_flight=DUMMY_DURATION,
        ),
    ),
)


@pytest.mark.parametrize(("flight_logs", "truth_summary"), BATCH_METADATA_CASES)
def test_batch_log_summary(flight_logs: list[FlightLog], truth_summary: LogSummary) -> None:
    assert LogSummary.from_flight_logs(flight_logs) == truth_summary


def test_empty_batch_summary_raises() -> None:
    with pytest.raises(ValueError):
        LogSummary.from_flight_logs([])


DB_METADATA_CASES = (
    (
        db.SummaryTuple(
            n_logs=1,
            n_flight_segments=1,
            total_flight_time=DUMMY_DURATION,
            flight_segments=[DUMMY_DURATION],
        ),
        LogSummary(
            n_logs=1,
            n_flight_segments=1,
            total_flight_time=DUMMY_DURATION,
            avg_flight_time=DUMMY_DURATION,
            shortest_flight=DUMMY_DURATION,
            longest_flight=DUMMY_DURATION,
        ),
    ),
    (
        db.SummaryTuple(
            n_logs=1,
            n_flight_segments=2,
            total_flight_time=dt.timedelta(seconds=8),
            flight_segments=[dt.timedelta(seconds=3), DUMMY_DURATION],
        ),
        LogSummary(
            n_logs=1,
            n_flight_segments=2,
            total_flight_time=dt.timedelta(seconds=8),
            avg_flight_time=dt.timedelta(seconds=4),
            shortest_flight=dt.timedelta(seconds=3),
            longest_flight=DUMMY_DURATION,
        ),
    ),
    (
        db.SummaryTuple(
            n_logs=1,
            n_flight_segments=3,
            total_flight_time=dt.timedelta(seconds=12),
            flight_segments=[dt.timedelta(seconds=3), DUMMY_DURATION, dt.timedelta(seconds=4)],
        ),
        LogSummary(
            n_logs=1,
            n_flight_segments=3,
            total_flight_time=dt.timedelta(seconds=12),
            avg_flight_time=dt.timedelta(seconds=4),
            shortest_flight=dt.timedelta(seconds=3),
            longest_flight=DUMMY_DURATION,
        ),
    ),
)


@pytest.mark.parametrize(("db_response", "truth_summary"), DB_METADATA_CASES)
def test_db_summary(db_response: db.SummaryTuple, truth_summary: LogSummary) -> None:
    assert LogSummary.from_db_query(db_response) == truth_summary
