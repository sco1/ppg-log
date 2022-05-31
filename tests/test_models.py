import datetime as dt

from ppg_log.metrics import FlightLog, LOG_DATETIME_FMT, LogMetadata


def test_log_datetime() -> None:
    log = FlightLog(
        flight_data=None, metadata=LogMetadata(log_date="2022-04-20", log_time="04-20-00")
    )

    assert log.log_datetime == dt.datetime.strptime("2022-04-20_04-20-00", LOG_DATETIME_FMT)
