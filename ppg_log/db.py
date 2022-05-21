from __future__ import annotations

import datetime as dt
import os
import typing as t

import peewee as pw
from dotenv import load_dotenv

if t.TYPE_CHECKING:
    from ppg_log import metrics

load_dotenv()
db_url = os.environ.get("DB_URL", "./test_db.db")
flight_db = pw.SqliteDatabase(db_url)


class BaseModel(pw.Model):
    class Meta:
        database = flight_db


class FlightLogEntry(BaseModel):
    flight_id = pw.IntegerField(primary_key=True)
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


def bulk_insert(flight_logs: list[metrics.FlightLog]) -> None:
    """
    Bulk insert entries into the database for the provided list of `FlightLog` instances.

    NOTE: Bulk insertion is aborted completely if an integrity error is encountered, likely if the
    one or more logs already exist in the database.
    """
    entries = [FlightLogEntry.from_flight_log(flight_log) for flight_log in flight_logs]

    try:
        FlightLogEntry.bulk_create(entries)
    except pw.IntegrityError:
        print(
            (
                "Bulk Insertion aborted due to an integrity error. "
                "One or more logs matching their starting datetime already exists in the database."
            )
        )
