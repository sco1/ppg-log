from __future__ import annotations

import typing as t

if t.TYPE_CHECKING:
    from pathlib import Path

    import pandas as pd

KEEP_COLS = ["velN", "velE", "elapsed_time", "groundspeed", "flight_mode"]


def dump_sample_json(
    flight_data: pd.DataFrame,
    out_filepath: Path,
    keep_cols: list[str] = KEEP_COLS,
    start_idx: int | None = None,
    end_idx: int | None = None,
) -> None:  # pragma: no cover
    """
    Dump sample flight data to a JSON file specified by `out_filepath` for use with testing.

    Columns to dump may be specified by `keep_cols`, which defaults to:
        * "velN"
        * "velE"
        * "elapsed_time"
        * "groundspeed"
        * "flight_mode"

    Data to dump may be selected using `start_idx` & `end_idx`, which follow Python's `slice`
    semantics.
    """
    flight_data[keep_cols].iloc[slice(start_idx, end_idx)].to_json(out_filepath)


def dump_sample_csv(
    flight_data: pd.DataFrame,
    out_filepath: Path,
    keep_cols: list[str] = KEEP_COLS,
    start_idx: int | None = None,
    end_idx: int | None = None,
) -> None:  # pragma: no cover
    """
    Dump sample flight data to a CSV file specified by `out_filepath` for use with testing.

    Columns to dump may be specified by `keep_cols`, which defaults to:
        * "velN"
        * "velE"
        * "elapsed_time"
        * "groundspeed"
        * "flight_mode"

    Data to dump may be selected using `start_idx` & `end_idx`, which follow Python's `slice`
    semantics.
    """
    flight_data[keep_cols].iloc[slice(start_idx, end_idx)].to_csv(out_filepath)
