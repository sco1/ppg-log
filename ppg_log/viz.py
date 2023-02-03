from __future__ import annotations

from pathlib import Path

import humanize
import numpy as np
import pandas as pd
import plotly.graph_objects as go

from ppg_log import metrics

pd.options.plotting.backend = "plotly"


def summary_plot(
    flight_log: metrics.FlightLog,
    save_path: Path | None = None,
    show_plot: bool = False,
    show_flight_mode: bool = False,
) -> None:  # pragma: no cover
    """
    Build a plot for the provided flight log showing basic flight information.

    Currently visualized quantities:
        * Groundspeed (m/s)
        * Altitude (m MSL)
        * Flight Segments

    If `save_path` is specified, the plot is saved as an image file to the specified path. Any
    existing plot is overwritten.

    If `show_plot` is `True`, the plot is displayed on screen.

    If `show_flight_mode` is True, the Flight Mode classification is added (useful for debugging).
    """
    fig = go.Figure()
    elapsed_time = flight_log.flight_data["elapsed_time"]
    fig.add_trace(
        go.Scatter(
            x=elapsed_time,
            y=flight_log.flight_data["groundspeed"],
            name="Groundspeed",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=elapsed_time,
            y=flight_log.flight_data["hMSL"],
            name="Altitude (m MSL)",
            yaxis="y2",
        ),
    )

    # Plot Flight Segments
    if flight_log.metadata.flight_segments is not None:
        for idx, segment in enumerate(flight_log.metadata.flight_segments, start=1):
            # Build an array of ones for the y values
            n_values = len(elapsed_time.iloc[segment.start_idx : segment.end_idx + 1])
            const_array = np.ones(n_values) * 1.2

            fig.add_trace(
                go.Scatter(
                    x=elapsed_time.iloc[segment.start_idx : segment.end_idx + 1],
                    y=const_array,
                    name=f"Flight {idx}",
                    yaxis="y3",
                )
            )

    if show_flight_mode:
        fig.add_trace(
            go.Scatter(
                x=elapsed_time,
                y=flight_log.flight_data["flight_mode"],
                name="Flight Mode",
                yaxis="y4",
            ),
        )

    humanized_time = humanize.precisedelta(
        flight_log.metadata.total_flight_time, minimum_unit="seconds", format="%d"
    )
    title_str = (
        f"{flight_log.metadata.log_date} {flight_log.metadata.log_time}<br>"
        f"Total Flights: {flight_log.metadata.n_flight_segments}, "
        f"Total Flight Time: {humanized_time}"
    )

    fig.update_layout(
        title={"text": title_str, "x": 0.5, "y": 0.9, "xanchor": "center", "yanchor": "top"},
        xaxis={"title": "Elapsed Time (s)", "domain": [0, 0.75]},
        yaxis={"title": "Groundspeed (m/s)"},
        yaxis2={
            "title": "Altitude (m MSL)",
            "anchor": "x",
            "overlaying": "y",
            "side": "right",
        },
        yaxis3={
            "title": "Flight Segments",
            "anchor": "free",
            "overlaying": "y",
            "side": "right",
            "position": 0.85,
            "nticks": 2,
            "range": (0, 1.25),
        },
        yaxis4={
            "title": "Flight Mode",
            "anchor": "free",
            "overlaying": "y",
            "side": "right",
            "position": 0.90,
            "nticks": 2,
            "range": (0, 1.25),
        },
    )

    if save_path:
        # Make sure output directory exists
        save_path.parent.mkdir(parents=True, exist_ok=True)

        fig.write_image(save_path)

    if show_plot:
        fig.show()
