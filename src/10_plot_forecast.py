"""Step 10 - plot actual vs predicted PM2.5 for one station over the test week.

Usage:  python src/10_plot_forecast.py [--station "Teri Gram, Gurugram - HSPCB"] [--show]

Input : results/pm25_predictions.csv
Output: results/figures/actual_vs_predicted_pm25_<station>.png

Where a sensor has a gap of more than an hour, the line is broken instead of joining the two
sides with a misleading straight segment.
"""
import argparse
import re

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import config

DEFAULT_STATION = "Teri Gram, Gurugram - HSPCB"


def break_lines_at_gaps(station_data: pd.DataFrame, max_gap="1h") -> pd.DataFrame:
    """Insert NaN rows where readings are missing so matplotlib leaves the gap empty."""
    gap_starts = station_data["datetime_utc"].diff() > pd.Timedelta(max_gap)
    filler = station_data.loc[gap_starts].copy()
    filler["datetime_utc"] = filler["datetime_utc"] - pd.Timedelta(minutes=1)
    filler[["pm25", "pm25_predicted"]] = np.nan
    return pd.concat([station_data, filler]).sort_values("datetime_utc")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--station", default=DEFAULT_STATION, help="station_name to plot")
    parser.add_argument("--show", action="store_true", help="open a window as well as saving")
    args = parser.parse_args()

    df = pd.read_csv(config.RESULTS_DIR / "pm25_predictions.csv")
    df["datetime_utc"] = pd.to_datetime(df["datetime_utc"])
    data = df[df["station_name"] == args.station].sort_values("datetime_utc")
    if data.empty:
        raise SystemExit(f"No rows for station '{args.station}'. Available: "
                         f"{sorted(df['station_name'].unique())[:5]} ...")

    print(f"Rows for {args.station}: {len(data)}  ({data['datetime_utc'].min()} to {data['datetime_utc'].max()})")
    plot_data = break_lines_at_gaps(data)

    fig, ax = plt.subplots(figsize=(16, 6))
    ax.plot(plot_data["datetime_utc"], plot_data["pm25"], label="Actual PM2.5", color="black", linewidth=1.2)
    ax.plot(plot_data["datetime_utc"], plot_data["pm25_predicted"], label="Predicted PM2.5",
            color="red", linestyle="--", linewidth=1.2)
    ax.set_xlabel("Date (UTC)")
    ax.set_ylabel("PM2.5 (µg/m³)")
    ax.set_title(f"Actual vs Predicted PM2.5 - {args.station} (test week: Aug 27-31, 2026)")
    ax.legend()
    ax.xaxis.set_major_locator(mdates.DayLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    ax.xaxis.set_minor_locator(mdates.HourLocator(interval=12))
    ax.tick_params(axis="x", rotation=45)
    ax.grid(alpha=0.3)
    fig.tight_layout()

    slug = re.sub(r"[^a-z0-9]+", "_", args.station.split(",")[0].lower()).strip("_")
    out = config.FIGURES_DIR / f"actual_vs_predicted_pm25_{slug}.png"
    fig.savefig(out, dpi=150)
    print(f"Saved plot: {out}")
    if args.show:
        plt.show()


if __name__ == "__main__":
    main()
