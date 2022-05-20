from __future__ import annotations

import datetime as dt
import typing as t
from collections import defaultdict

import pandas as pd

if t.TYPE_CHECKING:
    from pathlib import Path

N_HEADER_LINES = 2


def load_flysight(filepath: Path, n_header_lines: int = N_HEADER_LINES) -> pd.DataFrame:
    """
    Parse the provided FlySight log into a `DataFrame`.

    FlySight logs are assumed to contain 2 header rows, one for labels and the other for units. By
    default, the units row is discarded.

    The following derived columns are added to the output `DataFrame`:
        * `elapsed_time`
        * `groundspeed` (m/s)
    """
    flight_log = pd.read_csv(filepath, header=0, skiprows=range(1, n_header_lines))

    flight_log["time"] = pd.to_datetime(flight_log["time"])
    flight_log["elapsed_time"] = (flight_log["time"] - flight_log["time"][0]).dt.total_seconds()
    flight_log["groundspeed"] = (flight_log["velN"].pow(2) + flight_log["velE"].pow(2)).pow(1 / 2)

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


def logpath2datetime(log_filepath: Path) -> dt.datetime:
    """
    Generate a `datetime` instance from the provided FlySight log filepath.

    It is assumed that the log file is named `HH-MM-SS.CSV` and contained in a parent directory
    named `YY-mm-dd`.
    """
    datestr = f"{log_filepath.parent.stem}_{log_filepath.stem}"
    return dt.datetime.strptime(datestr, r"%y-%m-%d_%H-%M-%S")
