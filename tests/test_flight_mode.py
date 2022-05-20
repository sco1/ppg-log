import pytest

from ppg_log import metrics

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
