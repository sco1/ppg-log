import datetime as dt
from pathlib import Path

import pytest

from ppg_log import parser

SAMPLE_FILEPATHS = [
    (
        Path("21-12-13/12-17-30.CSV"),
        dt.datetime(year=2021, month=12, day=13, hour=12, minute=17, second=30),
    ),
]


@pytest.mark.parametrize(("filepath, truth_datetime"), SAMPLE_FILEPATHS)
def test_logpath2datetime(filepath: Path, truth_datetime: dt.datetime) -> None:
    assert parser.logpath2datetime(filepath) == truth_datetime
