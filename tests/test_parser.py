import datetime as dt
from pathlib import Path

import pytest
from pandas.api import types as pdt

from ppg_log import parser
from tests import checks

SAMPLE_DATA_DIR = Path(__file__).parent / "sample_data"
BATCH_LOG_STEMS = {
    "21-04-20",
    "21-05-20",
}

DERIVED_COLS = {
    "time": pdt.is_datetime64_any_dtype,
    "elapsed_time": pdt.is_float_dtype,
    "groundspeed": pdt.is_float_dtype,
}


SAMPLE_FILEPATHS = [
    (
        Path("./21-12-13/12-17-30.CSV"),
        dt.datetime(year=2021, month=12, day=13, hour=12, minute=17, second=30),
    ),
]


@pytest.mark.parametrize(("filepath, truth_datetime"), SAMPLE_FILEPATHS)
def test_logpath2datetime(filepath: Path, truth_datetime: dt.datetime) -> None:
    assert parser.logpath2datetime(filepath) == truth_datetime


def test_log_parse() -> None:
    sample_flight_log = SAMPLE_DATA_DIR / "21-04-20.CSV"
    flight_data = parser.load_flysight(sample_flight_log)

    # Check that derived columns are calculated and with correct dtype
    for col_name, pd_type_check in DERIVED_COLS.items():
        checks.is_col(flight_data, col_name)
        checks.is_dtype(flight_data, col_name, pd_type_check)


def test_batch_log_parse() -> None:
    sample_log_pattern = "21*.CSV"  # Limit to a subset of the sample data
    flight_logs = parser.batch_load_flysight(SAMPLE_DATA_DIR, pattern=sample_log_pattern)

    # Check top level dir name
    assert "sample_data" in flight_logs

    # Check that the log files are loaded & keyed correctly
    assert set(flight_logs["sample_data"]) == BATCH_LOG_STEMS
