import datetime as dt
import typing as t
from functools import partial
from pathlib import Path

import pandas as pd
import pytest

from ppg_log import metrics
from tests import checks

SAMPLE_DATA_DIR = Path(__file__).parent / "sample_data"


TEST_THRESHOLD = 5
FLIGHT_MODE_CASES = [
    (0, metrics.FlightMode.GROUND),
    (1, metrics.FlightMode.GROUND),
    (1.1, metrics.FlightMode.GROUND),
    (4.99, metrics.FlightMode.GROUND),
    (5, metrics.FlightMode.AIRBORNE),
    (5.0, metrics.FlightMode.AIRBORNE),
    (5.1, metrics.FlightMode.AIRBORNE),
    (9999, metrics.FlightMode.AIRBORNE),
]


@pytest.mark.parametrize(("speed", "truth_mode"), FLIGHT_MODE_CASES)
def test_mode_classification(speed: int | float, truth_mode: metrics.FlightMode) -> None:
    assert metrics._classify_flight_mode(speed, TEST_THRESHOLD) == truth_mode


class DataTruthMap(t.NamedTuple):
    json_path: Path
    flight_segments: list[metrics.FlightSegment] | None


DURATION_TOL = dt.timedelta(seconds=1)
IDX_TOL = DURATION_TOL.total_seconds() // 0.2  # Sample rate assumed to be 5 Hz

PARTIAL_LOG = partial(
    metrics.FlightLog, metadata=metrics.LogMetadata(log_date="2022-04-20", log_time="04-20-00")
)
CLASSIFICATION_TEST_CASES = (
    (
        DataTruthMap(
            json_path=SAMPLE_DATA_DIR / "single_segment_no_noise.json",
            flight_segments=[
                metrics.FlightSegment(
                    start_idx=605,
                    end_idx=4052,
                    duration=dt.timedelta(seconds=691),
                )
            ],
        ),
    ),
    (
        DataTruthMap(
            json_path=SAMPLE_DATA_DIR / "no_flights.json",
            flight_segments=None,
        ),
    ),
    (
        DataTruthMap(
            json_path=SAMPLE_DATA_DIR / "only_noise.json",
            flight_segments=None,
        ),
    ),
)


@pytest.mark.parametrize(("data_mapping",), CLASSIFICATION_TEST_CASES)
def test_flight_classification(data_mapping: DataTruthMap) -> None:
    flight_log = PARTIAL_LOG(flight_data=pd.read_json(data_mapping.json_path))
    flight_log = metrics.generate_flight_metrics(flight_log)

    if data_mapping.flight_segments is None:
        assert flight_log.metadata.flight_segments is None
    else:
        # For mypy: ignore the case of optional flight segments, they're present in this block
        assert len(flight_log.metadata.flight_segments) == len(data_mapping.flight_segments)  # type: ignore[arg-type]  # noqa: E501
        for flight_segment, truth_segment in zip(
            flight_log.metadata.flight_segments, data_mapping.flight_segments  # type: ignore[arg-type]
        ):
            checks.segment_isclose(
                flight_segment, truth_segment, idx_tol=IDX_TOL, duration_tol=DURATION_TOL
            )
