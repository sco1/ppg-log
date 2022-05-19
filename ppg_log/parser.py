from __future__ import annotations

import typing as t
from collections import defaultdict

import pandas as pd

if t.TYPE_CHECKING:
    from pathlib import Path

N_HEADER_LINES = 2
START_TRIM = 20


def load_flysight(
    filepath: Path, n_header_lines: int = N_HEADER_LINES, start_trim: int = START_TRIM
) -> pd.DataFrame:
    """
    Parse the provided FlySight log into a `DataFrame`.

    FlySight logs are assumed to contain 2 header rows, one for labels and the other for units. By
    default, the units row is discarded.

    As a quick & dirty method to avoid start of file weirdness, the first `start_trim` seconds of
    the data file is discarded.

    The following derived columns are added to the output `DataFrame`:
        * `elapsed_time`
        * `total_vel` (m/s)
    """
    flight_log = pd.read_csv(filepath, header=0, skiprows=range(1, n_header_lines))

    flight_log["time"] = pd.to_datetime(flight_log["time"])
    flight_log["elapsed_time"] = (flight_log["time"] - flight_log["time"][0]).dt.total_seconds()
    flight_log["total_vel"] = (flight_log["velN"].pow(2) + flight_log["velE"].pow(2)).pow(1 / 2)

    # Trim beginning of flight log
    # For now we're assuming that the FlySight spends at least a few minutes on the ground after
    # it's turned on.
    trim_idx = (flight_log["elapsed_time"] >= start_trim).idxmax()
    flight_log = flight_log.drop(flight_log.index[:trim_idx]).reset_index(drop=True)

    return flight_log


def batch_load_flysight(
    top_dir: Path, pattern: str = r"*.CSV"
) -> dict[str, dict[str, pd.DataFrame]]:
    """
    Batch parse a directory of FlySight logs into a dictionary of `DataFrame`s.

    Because the FlySight hardware groups logs by date & the log CSV name does not contain date
    information, the date is inferred from the log's parent directory name & the output dictionary
    is of the form `{log date: {log_time: DataFrame}}`.

    Log file discovery is not recursive by default, the `pattern` kwarg can be adjusted to support
    a recursive glob.

    NOTE: File case sensitivity is deferred to the OS; `pattern` is passed to glob as-is so matches
    may or may not be case-sensitive.
    """
    parsed_logs: dict[str, dict[str, pd.DataFrame]] = defaultdict(dict)
    for log_file in top_dir.glob(pattern):
        # Log files are grouped by date, need to retain this since it's not in the CSV filename
        log_date = log_file.parent.stem
        parsed_logs[log_date][log_file.stem] = load_flysight(log_file)

    return parsed_logs
