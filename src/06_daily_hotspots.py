"""Step 6 - repeat the hotspot detection for every day and attach wind to each cluster.

This is precomputed (instead of clustering inside the dashboard) so the Streamlit date slider
responds instantly.

Input : data/delhi_ncr_all_pollutants_merged.csv, data/delhi_ncr_pm25_with_era5.csv
Output: results/daily_hotspots_august.csv  (one row per cluster per day)

Note: days are split on UTC timestamps, so a "day" runs 05:30-05:30 Indian Standard Time.
"""
import pandas as pd

import config
from utils import circular_mean_degrees, cluster_stations, compass_label, composite_pollution_index

POLLUTANTS = config.POLLUTANTS


def read_with_utc(path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["datetime_utc"] = pd.to_datetime(df["datetime_utc"]).dt.tz_localize(None)
    return df


def daily_cluster_summary(day_df: pd.DataFrame, date) -> pd.DataFrame | None:
    """Cluster the stations of one day; returns None if fewer than 3 stations reported."""
    station_avg = day_df.groupby(["station_id", "station_name", "lat", "lon"]).agg(
        {**{p: "mean" for p in POLLUTANTS},
         "wind_speed": "mean", "wind_direction": circular_mean_degrees}
    ).reset_index()

    if len(station_avg) < 3:
        return None  # not enough stations that day

    station_avg["pollution_index"] = composite_pollution_index(station_avg, POLLUTANTS, fill_missing=True)
    station_avg["cluster"] = cluster_stations(station_avg["lat"], station_avg["lon"])
    city_mean_index = station_avg["pollution_index"].mean()

    summary = (
        station_avg[station_avg["cluster"] != -1]
        .groupby("cluster")
        .agg(
            num_stations=("station_id", "count"),
            avg_pm25=("pm25", "mean"),
            avg_pollution_index=("pollution_index", "mean"),
            avg_wind_speed=("wind_speed", "mean"),
            avg_wind_direction=("wind_direction", circular_mean_degrees),
            center_lat=("lat", "mean"),
            center_lon=("lon", "mean"),
        )
        .reset_index()
    )
    summary["is_hotspot"] = summary["avg_pollution_index"] > city_mean_index
    summary["source_direction_compass"] = summary["avg_wind_direction"].apply(compass_label)
    summary["date"] = date
    return summary


def main():
    df_all = read_with_utc(config.DATA_DIR / "delhi_ncr_all_pollutants_merged.csv")
    df_wind = read_with_utc(config.DATA_DIR / "delhi_ncr_pm25_with_era5.csv")

    # bring the wind columns onto the full pollutant table (station + timestamp match)
    wind_cols = df_wind[["station_id", "datetime_utc", "wind_speed", "wind_direction"]]
    df_all = pd.merge(df_all, wind_cols, on=["station_id", "datetime_utc"], how="left")
    df_all["date"] = df_all["datetime_utc"].dt.date

    dates = sorted(df_all["date"].unique())
    print(f"Processing {len(dates)} days...")

    results = []
    for d in dates:
        summary = daily_cluster_summary(df_all[df_all["date"] == d], d)
        if summary is not None:
            results.append(summary)

    daily = pd.concat(results, ignore_index=True)
    daily.to_csv(config.RESULTS_DIR / "daily_hotspots_august.csv", index=False)
    print(f"\nSaved daily_hotspots_august.csv: {len(daily)} cluster-day rows across {len(dates)} days")
    print(daily.head(10))


if __name__ == "__main__":
    main()
