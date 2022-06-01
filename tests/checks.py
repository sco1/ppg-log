from __future__ import annotations

import typing as t

import pytest
from pytest_check import check_func

if t.TYPE_CHECKING:
    import datetime as dt

    import pandas as pd

    from ppg_log import metrics


@check_func  # type: ignore[misc]  # fine with this untyped decorator
def is_col(df: pd.DataFrame, col_name: str) -> None:
    assert col_name in df.columns


@check_func  # type: ignore[misc]  # fine with this untyped decorator
def is_dtype(df: pd.DataFrame, col_name: str, type_check: t.Callable) -> None:
    """
    Check that the query dataframe matches the correct type.

    `type_check` is assumed to be a callable function that returns a boolean. The intent is to use
    pandas` built-in `pandas.api.types.is_*` functions.
    """
    assert type_check(df[col_name])


@check_func  # type: ignore[misc]  # fine with this untyped decorator
def segment_isclose(
    flight: metrics.FlightSegment,
    truth: metrics.FlightSegment,
    idx_tol: int,
    duration_tol: dt.timedelta,
) -> None:
    flight_duration = flight.duration.total_seconds()
    truth_duration = truth.duration.total_seconds()
    tol = duration_tol.total_seconds()
    duration_msg = f"Duration check failed. Segment: {flight_duration}, Truth: {truth_duration}, Tolerance: {tol}"  # noqa: E501
    assert flight_duration == pytest.approx(truth_duration, abs=tol), duration_msg

    start_idx_msg = f"Start idx check failed. Segment: {flight.start_idx}, Truth: {truth.start_idx}, Tolerance: {idx_tol}"  # noqa: E501
    end_idx_msg = f"End idx check failed. Segment: {flight.end_idx}, Truth: {truth.end_idx}, Tolerance: {idx_tol}"  # noqa: E501
    assert flight.start_idx == pytest.approx(truth.start_idx, abs=idx_tol), start_idx_msg
    assert flight.end_idx == pytest.approx(truth.end_idx, abs=idx_tol), end_idx_msg
