import os
import tkinter as tk
from pathlib import Path
from tkinter import filedialog

import click
import typer
from dotenv import load_dotenv

from ppg_log import db, metrics
from ppg_log.cli_db import db_cli
from ppg_log.exceptions import FlightSegmentationError

ppglog_cli = typer.Typer(add_completion=False)
ppglog_cli.add_typer(db_cli, name="db", help="Interact with a PPG Log database instance.")


load_dotenv()
start_dir = os.environ.get("PROMPT_START_DIR", ".")
PROMPT_START_DIR = Path(start_dir)


def _prompt_for_file(title: str, start_dir: Path = PROMPT_START_DIR) -> Path:  # pragma: no cover
    """Open a Tk file selection dialog to prompt the user to select a single file for processing."""
    root = tk.Tk()
    root.withdraw()

    picked = filedialog.askopenfilename(  # type: ignore[call-arg]  # stub issue
        title=title,
        initialdir=start_dir,
        multiple=False,
        filetypes=[
            ("FlySight Flight Log", "*.csv"),
            ("Gaggle Flight Log", "*.gpx"),
            ("All Files", "*.*"),
        ],
    )

    if not picked:
        raise click.ClickException("No file selected for parsing, aborting.")

    return Path(picked)


def _prompt_for_dir(start_dir: Path = PROMPT_START_DIR) -> Path:  # pragma: no cover
    """Open a Tk file selection dialog to prompt the user to select a directory for processing."""
    root = tk.Tk()
    root.withdraw()

    picked = filedialog.askdirectory(
        title="Select directory for batch processing",
        initialdir=start_dir,
    )

    if not picked:
        raise click.ClickException("No directory selected for parsing, aborting.")

    return Path(picked)


@ppglog_cli.command()
def single(
    log_filepath: Path = typer.Option(None, exists=True, file_okay=True, dir_okay=False),
    start_trim: float = typer.Option(metrics.START_TRIM),
    airborne_threshold: float = typer.Option(metrics.AIRBORNE_THRESHOLD),
    time_threshold: float = typer.Option(metrics.FLIGHT_LENGTH_THRESHOLD),
    midair_start: bool = typer.Option(False),
    show_plot: bool = typer.Option(True),
    plot_save_dir: Path = typer.Option(None, file_okay=False, dir_okay=True),
    db_insert: bool = typer.Option(False),
) -> None:
    """Single flight log processing pipeline."""
    if log_filepath is None:
        log_filepath = _prompt_for_file(title="Select Flight Log")

    try:
        flight_log = metrics.process_log(
            log_file=log_filepath,
            start_trim=start_trim,
            airborne_threshold=airborne_threshold,
            time_threshold=time_threshold,
            midair_start=midair_start,
        )
    except FlightSegmentationError:
        raise click.ClickException("Could not propertly segment flights, aborting.")

    flight_log.summary_plot(show_plot=show_plot, save_dir=plot_save_dir)

    if db_insert:
        db.insert_single(flight_log)


@ppglog_cli.command()
def batch(
    log_dir: Path = typer.Option(None, exists=True, file_okay=False, dir_okay=True),
    log_pattern: str = typer.Option("*.CSV"),
    start_trim: float = typer.Option(metrics.START_TRIM),
    airborne_threshold: float = typer.Option(metrics.AIRBORNE_THRESHOLD),
    time_threshold: float = typer.Option(metrics.FLIGHT_LENGTH_THRESHOLD),
    plot_save_dir: Path = typer.Option(None, file_okay=False, dir_okay=True),
    db_insert: bool = typer.Option(False),
    verbose: bool = typer.Option(True),
) -> None:
    """Batch flight log processing pipeline."""
    if log_dir is None:
        log_dir = _prompt_for_dir()

    flight_logs = metrics.batch_process(
        top_dir=log_dir,
        log_pattern=log_pattern,
        start_trim=start_trim,
        airborne_threshold=airborne_threshold,
        time_threshold=time_threshold,
        verbose=verbose,
    )

    for log in flight_logs:
        log.summary_plot(show_plot=False, save_dir=plot_save_dir)

    if db_insert:
        db.bulk_insert(flight_logs, verbose=verbose)


if __name__ == "__main__":  # pragma: no cover
    ppglog_cli()
