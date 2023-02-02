from __future__ import annotations

from pathlib import Path

import pytest

from ppg_log import metrics

SAMPLE_DATA_DIR = Path(__file__).parent / "sample_data"
SAMPLE_LOG_PATTERN = "21*.CSV"  # Limit to a subset of the sample data
SAMPLE_LOG = SAMPLE_DATA_DIR / "13-46-02.CSV"


def test_single_log_process() -> None:
    flight_log = metrics.process_log(SAMPLE_LOG)

    assert flight_log.metadata.n_flight_segments == 1


def test_batch_process() -> None:
    flight_logs = metrics.batch_process(
        SAMPLE_DATA_DIR, log_pattern=SAMPLE_LOG_PATTERN, classify_segments=False, verbose=False
    )

    assert len(flight_logs) == 2


def test_batch_process_verbose(capsys: pytest.CaptureFixture) -> None:
    metrics.batch_process(
        SAMPLE_DATA_DIR, log_pattern=SAMPLE_LOG_PATTERN, classify_segments=False, verbose=True
    )
    assert "Found 2 log files to process" in capsys.readouterr().out
