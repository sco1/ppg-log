import datetime as dt
from functools import partial

import peewee as pw
import pytest

from ppg_log import db
from ppg_log.metrics import FlightLog, FlightSegment, LogMetadata

TEST_DB = pw.SqliteDatabase(":memory:")


DUMMY_DURATION = dt.timedelta(seconds=5)
PARTIAL_SEGMENT = partial(FlightSegment, start_idx=-1, end_idx=-1)
PARTIAL_META = partial(LogMetadata, log_date="2022-04-20", log_time="04-20-00")

DUMMY_FLIGHT_LOG = FlightLog(
    flight_data=None,
    metadata=PARTIAL_META(
        n_flight_segments=1,
        total_flight_time=DUMMY_DURATION,
        flight_segments=[PARTIAL_SEGMENT(duration=DUMMY_DURATION)],
    ),
)

DUMMY_BULK_LOGS = [
    DUMMY_FLIGHT_LOG,
    FlightLog(
        flight_data=None,
        metadata=PARTIAL_META(
            log_date="2022-04-21",
            n_flight_segments=1,
            total_flight_time=DUMMY_DURATION,
            flight_segments=[PARTIAL_SEGMENT(duration=DUMMY_DURATION)],
        ),
    ),
]

DUMMY_FLIGHT_LOG_NO_FLIGHTS = FlightLog(
    flight_data=None,
    metadata=PARTIAL_META(),
)


@pytest.fixture
def session(request: pytest.FixtureRequest) -> None:
    # We only have one table so we don't need to bind references
    TEST_DB.bind([db.FlightLogEntry], bind_refs=False, bind_backrefs=False)

    TEST_DB.connect()
    db.create_db()

    def teardown() -> None:
        TEST_DB.drop_tables(db.FlightLogEntry)
        TEST_DB.close()

    request.addfinalizer(teardown)


def test_single_insert(session: None) -> None:
    db.insert_single(DUMMY_FLIGHT_LOG)

    n_rows = db.FlightLogEntry.select(pw.fn.COUNT(db.FlightLogEntry.flight_log_id)).scalar()
    assert n_rows == 1


@pytest.mark.xfail(reason="Check not implemented, see #10")
def test_insert_log_empty_segments(session: None) -> None:
    db.insert_single(DUMMY_FLIGHT_LOG_NO_FLIGHTS)

    n_rows = db.FlightLogEntry.select(pw.fn.COUNT(db.FlightLogEntry.flight_log_id)).scalar()
    assert n_rows == 1


def test_single_insert_duplicate_aborts(session: None, capsys: pytest.CaptureFixture) -> None:
    db.insert_single(DUMMY_FLIGHT_LOG)
    db.insert_single(DUMMY_FLIGHT_LOG)

    assert "Insertion aborted" in capsys.readouterr().out

    n_rows = db.FlightLogEntry.select(pw.fn.COUNT(db.FlightLogEntry.flight_log_id)).scalar()
    assert n_rows == 1


def test_bulk_insert(session: None) -> None:
    db.bulk_insert(DUMMY_BULK_LOGS)

    n_rows = db.FlightLogEntry.select(pw.fn.COUNT(db.FlightLogEntry.flight_log_id)).scalar()
    assert n_rows == 2


@pytest.mark.xfail(reason="Check not implemented, see #10")
def test_bulk_insert_empty_flight(session: None) -> None:
    db.bulk_insert([DUMMY_FLIGHT_LOG, DUMMY_FLIGHT_LOG_NO_FLIGHTS])

    n_rows = db.FlightLogEntry.select(pw.fn.COUNT(db.FlightLogEntry.flight_log_id)).scalar()
    assert n_rows == 2


def test_bulk_insert_ignore_duplicates(session: None) -> None:
    db.insert_single(DUMMY_FLIGHT_LOG)
    db.bulk_insert(DUMMY_BULK_LOGS, verbose=False)

    n_rows = db.FlightLogEntry.select(pw.fn.COUNT(db.FlightLogEntry.flight_log_id)).scalar()
    assert n_rows == 2


@pytest.mark.xfail(reason="Check not implemented, see #8")
def test_bulk_insert_ignore_duplicates_empty_db(session: None) -> None:
    db.bulk_insert([DUMMY_FLIGHT_LOG, DUMMY_FLIGHT_LOG], verbose=False)

    n_rows = db.FlightLogEntry.select(pw.fn.COUNT(db.FlightLogEntry.flight_log_id)).scalar()
    assert n_rows == 1


def test_flight_log_empty_segments() -> None:
    entry = db.FlightLogEntry.from_flight_log(DUMMY_FLIGHT_LOG_NO_FLIGHTS)

    assert entry.flight_segment_durations == ""


@pytest.mark.xfail(reason="Check not implemented, see #9")
def test_summary_empty_db(session: None) -> None:
    truth_summary = db.SummaryTuple(
        n_logs=0, n_flight_segments=0, total_flight_time=dt.timedelta(), flight_segments=[]
    )

    assert db.summary_query() == truth_summary


SUMMARY_QUERIES = (
    (
        [DUMMY_FLIGHT_LOG],
        db.SummaryTuple(
            n_logs=1,
            n_flight_segments=1,
            total_flight_time=DUMMY_DURATION,
            flight_segments=[DUMMY_DURATION],
        ),
    ),
    (
        DUMMY_BULK_LOGS,
        db.SummaryTuple(
            n_logs=2,
            n_flight_segments=2,
            total_flight_time=dt.timedelta(seconds=10),
            flight_segments=[DUMMY_DURATION, DUMMY_DURATION],
        ),
    ),
    # (
    #     [DUMMY_FLIGHT_LOG, DUMMY_FLIGHT_LOG_NO_FLIGHTS],
    #     db.SummaryTuple(
    #         n_logs=2,
    #         n_flight_segments=1,
    #         total_flight_time=DUMMY_DURATION,
    #         flight_segments=[DUMMY_DURATION],
    #     ),
    # ),
)


@pytest.mark.parametrize(("flight_logs, truth_summary"), SUMMARY_QUERIES)
def test_summary_query(
    flight_logs: list[FlightLog], truth_summary: db.SummaryTuple, session: None
) -> None:
    db.bulk_insert(flight_logs)

    assert db.summary_query() == truth_summary
