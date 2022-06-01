from __future__ import annotations

import datetime as dt
import os
import typing as t

import peewee as pw
from dotenv import load_dotenv

if t.TYPE_CHECKING:
    from ppg_log import metrics

load_dotenv()
DB_URL_VARNAME = "DB_URL"
db_url = os.environ.get(DB_URL_VARNAME, "./test_db.db")
flight_db = pw.SqliteDatabase(db_url)


class BaseModel(pw.Model):
    class Meta:
        database = flight_db


class FlightLogEntry(BaseModel):
    flight_log_id = pw.IntegerField(primary_key=True)
    flight_datetime = pw.DateTimeField(unique=True)
    n_flights = pw.IntegerField()
    total_flight_time = pw.FloatField()
    flight_segment_durations = pw.TextField()
    added_on = pw.DateTimeField(default=dt.datetime.now)

    @classmethod
    def from_flight_log(cls, flight_log: metrics.FlightLog) -> FlightLogEntry:
        """
        Build an unsaved model instance from the provided `FlightLog` instance.

        NOTE: Because this model is unsaved, for single logs this must be inserted with `.save()`.
        For batching, `bulk_create()` accepts a list of unsaved instances so the return can be used
        as-is.
        """
        if flight_log.metadata.flight_segments:
            segment_durations = ",".join(
                str(segment.duration.total_seconds())
                for segment in flight_log.metadata.flight_segments
            )
        else:
            segment_durations = ""

        return cls(
            flight_datetime=flight_log.log_datetime,
            n_flights=flight_log.metadata.n_flight_segments,
            total_flight_time=flight_log.metadata.total_flight_time.total_seconds(),
            flight_segment_durations=segment_durations,
        )


class SummaryTuple(t.NamedTuple):
    """Helper container for summary information coming out of the database."""

    n_logs: int
    n_flight_segments: int
    total_flight_time: dt.timedelta
    flight_segments: list[dt.timedelta]


def create_db() -> None:  # pragma: no cover
    with flight_db:
        """Initialize a brand new database."""
        flight_db.create_tables([FlightLogEntry])


def insert_single(flight_log: metrics.FlightLog) -> None:
    """
    Insert a single entry into the database for the provided `FlightLog` instance.

    NOTE: Row insertion is aborted if an integrity error is encountered, likely if the log already
    exists in the database.
    """
    entry = FlightLogEntry.from_flight_log(flight_log)

    try:
        entry.save()
    except pw.IntegrityError:
        # This will mask other integrity issues, but for now we can assume that the inputs are
        # well-formed enough that this is the only issue we're going to run into
        print(
            (
                "Insertion aborted due to an integrity error. "
                "A log with this starting datetime already exists in the database."
            )
        )


def bulk_insert(flight_logs: list[metrics.FlightLog], verbose: bool = True) -> None:
    """
    Bulk insert entries into the database for the provided list of `FlightLog` instances.

    NOTE: Flight logs whose corresponding datetime already exists in the database are ignored.
    """
    entries = []
    for log in flight_logs:
        matching = FlightLogEntry.get_or_none(FlightLogEntry.flight_datetime == log.log_datetime)

        if matching is None:
            entries.append(FlightLogEntry.from_flight_log(log))
        else:
            if verbose:  # pragma: no cover
                print(
                    f"Flight log from {log.log_datetime} already exists in database (ID: {matching})."  # noqa: E501
                )

    FlightLogEntry.bulk_create(entries)


def summary_query() -> SummaryTuple:
    """
    Summary statistics query for the current database.

    A `SummaryTuple` instance is provided for use with downstream metrics calculations.
    """
    # Pull easily queried values from the db
    n_logs, n_flight_segments, total_flight_time = FlightLogEntry.select(
        pw.fn.COUNT(FlightLogEntry.flight_log_id),
        pw.fn.SUM(FlightLogEntry.n_flights),
        pw.fn.SUM(FlightLogEntry.total_flight_time),
    ).scalar(as_tuple=True)

    # Need to deserialize the flight segments to get the rest of the summary information
    raw_segments = FlightLogEntry.select(FlightLogEntry.flight_segment_durations).tuples()
    all_segments = ",".join(row[0] for row in raw_segments if row[0])
    converted_segments = [
        dt.timedelta(seconds=float(segment)) for segment in all_segments.split(",")
    ]

    return SummaryTuple(
        n_logs=n_logs,
        n_flight_segments=n_flight_segments,
        total_flight_time=dt.timedelta(seconds=total_flight_time),
        flight_segments=converted_segments,
    )
