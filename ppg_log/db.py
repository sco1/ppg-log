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
        """Build a model instance from the provided `FlightLog` instance."""
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


def create_db() -> None:
    with flight_db:
        flight_db.create_tables([FlightLogEntry])


def insert_single(flight_log: metrics.FlightLog) -> None:
    """
    Insert a single entry into the database for the provided `FlightLog` instance.

    NOTE: Row insertion is aborted if an integrity error is encountered, likely if the log already
    exists in the database.
    """
    entry = FlightLogEntry.from_flight_log(flight_log)

    try:
        entry.create()
    except pw.IntegrityError:
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
            if verbose:
                print(
                    f"Flight log from {log.log_datetime} already exists in database (ID: {matching})."  # noqa: E501
                )

    FlightLogEntry.bulk_create(entries)
