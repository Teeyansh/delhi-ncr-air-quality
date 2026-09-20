"""Step 7 - build the feature table for the PM2.5 forecasting model.

Features per reading: time (hour, weekday, day of month), PM2.5 lags and a short rolling
mean of previous readings (per station), weather from ERA5, and station coordinates.

KNOWN LIMITATION: lags are counted in *rows*, not in time. Sensors have gaps (about 68% of
the 15-minute grid is present), so ``pm25_lag96`` is "96 readings ago", which is often more
than 24 hours ago. See the README for planned fixes.

Input : data/delhi_ncr_pm25_with_era5.csv
Output: data/delhi_ncr_pm25_features.csv
"""
import pandas as pd

import config


def main():
    df = pd.read_csv(config.DATA_DIR / "delhi_ncr_pm25_with_era5.csv")
    df["datetime_utc"] = pd.to_datetime(df["datetime_utc"])

    # sorting matters: lag features are only correct if rows are in time order per station
    df = df.sort_values(["station_id", "datetime_utc"]).reset_index(drop=True)

    df["hour"] = df["datetime_utc"].dt.hour
    df["day_of_week"] = df["datetime_utc"].dt.dayofweek
    df["day_of_month"] = df["datetime_utc"].dt.day

    by_station = df.groupby("station_id")["pm25"]
    df["pm25_lag1"] = by_station.shift(1)    # previous reading
    df["pm25_lag4"] = by_station.shift(4)    # ~1 hour ago (15-minute readings)
    df["pm25_lag96"] = by_station.shift(96)  # ~24 hours ago if there were no gaps
    df["pm25_rolling_mean_4"] = by_station.transform(lambda x: x.shift(1).rolling(window=4).mean())

    lag_cols = ["pm25_lag1", "pm25_lag4", "pm25_lag96", "pm25_rolling_mean_4"]
    df_model = df.dropna(subset=lag_cols)
    print(f"Original rows: {len(df)}")
    print(f"Rows after dropping lag NaNs: {len(df_model)}")

    out = config.DATA_DIR / "delhi_ncr_pm25_features.csv"
    df_model.to_csv(out, index=False)
    print(f"Saved: {out}")


if __name__ == "__main__":
    main()
