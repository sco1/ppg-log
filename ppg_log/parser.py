from __future__ import annotations

import datetime as dt
import typing as t
import xml.etree.ElementTree as ETree
from collections import defaultdict
from pathlib import Path

import pandas as pd

N_HEADER_LINES = 2


def _calc_derived_vals(flight_log: pd.DataFrame, skip_gs: bool = False) -> pd.DataFrame:
    """
    Calculate derived columns from the provided flight log data.

    The following derived columns are added to the output `DataFrame`:
        * `elapsed_time`
        * `groundspeed` (m/s)

    If the `skip_gs` flag is `True`, groundspeed is assumed to already be present (e.g. Gaggle logs)
    and is not recalculated.
    """
    flight_log["time"] = pd.to_datetime(flight_log["time"])
    flight_log["elapsed_time"] = (flight_log["time"] - flight_log["time"][0]).dt.total_seconds()

    if not skip_gs:
        flight_log["groundspeed"] = (flight_log["velN"] ** 2 + flight_log["velE"] ** 2).pow(1 / 2)

    return flight_log


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
    flight_log = _calc_derived_vals(flight_log)

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


class GaggleTrack(t.TypedDict):  # noqa: D101
    time: list[str]
    lat: list[float]
    lon: list[float]
    hMSL: list[float]
    groundspeed: list[float]


def _validated_get(point: ETree.Element, attribute: str) -> str:
    """Attempt to get the specified attribute from a GPX trackpoint and raise if not found."""
    val = point.get(attribute)
    if not val:
        raise ValueError(f"Could not locate attribute '{attribute}' for the current trackpoint.")

    return val


def _validated_find_text(point: ETree.Element, element: str) -> str:
    """Attempt to get the specified element text from a GPX trackpoint and raise if not found."""
    subelement = point.find(element)
    if subelement is None:
        raise ValueError(f"Could not locate element '{element}' for the current trackpoint.")

    if not subelement.text:
        raise ValueError(f"Subelement '{element}' has no text data.")

    return subelement.text


def load_gaggle(filepath: Path) -> tuple[pd.DataFrame, dt.datetime]:
    """
    Parse the provided Gaggle GPX log into a `DataFrame`.

    The log's UTC timestamp is also parsed from the GPX file and returned. By default, Gaggle uses
    local time in its file naming convention, so the UTC timestamp needs to be extracted from the
    log itself.

    Gaggle's GPX files contain a subset of the information that a Flysight provides, but still
    contains enough information to conduct the downstream metrics calculations.
    """
    tree = ETree.parse(filepath)
    root = tree.getroot()

    log_datetime = dt.datetime.fromisoformat(_validated_find_text(root, "metadata/time"))

    flight_log = GaggleTrack(time=[], lat=[], lon=[], hMSL=[], groundspeed=[])
    points = root.findall(".*//trkseg/trkpt")
    for point in points:
        flight_log["lat"].append(float(_validated_get(point, "lat")))
        flight_log["lon"].append(float(_validated_get(point, "lon")))
        flight_log["time"].append(_validated_find_text(point, "time"))
        flight_log["hMSL"].append(float(_validated_find_text(point, "ele")))
        flight_log["groundspeed"].append(float(_validated_find_text(point, "extensions/speed")))

    flight_df = pd.DataFrame(flight_log)
    flight_df = _calc_derived_vals(flight_df, skip_gs=True)

    return flight_df, log_datetime


def logpath2datetime(log_filepath: Path) -> dt.datetime:
    """
    Generate a `datetime` instance from the provided FlySight log filepath.

    It is assumed that the log file is named `HH-MM-SS.CSV` and contained in a parent directory
    named `YY-mm-dd`.
    """
    datestr = f"{log_filepath.parent.stem}_{log_filepath.stem}"
    return dt.datetime.strptime(datestr, r"%y-%m-%d_%H-%M-%S")
