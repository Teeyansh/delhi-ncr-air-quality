"""Step 3 - attach ERA5 weather (wind, temperature, boundary-layer height) to every PM2.5 reading.

Each reading is matched to the nearest ERA5 grid cell and the nearest full hour, using one
vectorised xarray lookup (much faster than a row-by-row .apply()).

Input : data/delhi_ncr_pm25.csv, data/era5_wind_delhi_ncr_aug2026.nc
Output: data/delhi_ncr_pm25_with_era5.csv  (adds u10, v10, t2m, blh, wind_speed,
        wind_direction, temp_celsius)

wind_direction is the meteorological convention: the direction the wind is coming FROM
(0 = north, 90 = east).
"""
import numpy as np
import pandas as pd
import xarray as xr

import config


def main():
    ds = xr.open_dataset(config.ERA5_FILE)

    df = pd.read_csv(config.DATA_DIR / "delhi_ncr_pm25.csv")
    # ERA5 timestamps carry no timezone, so drop it from the readings too
    df["datetime_utc"] = pd.to_datetime(df["datetime_utc"]).dt.tz_localize(None)
    df["datetime_hour"] = df["datetime_utc"].dt.round("h")

    extracted = ds.sel(
        latitude=xr.DataArray(df["lat"].values, dims="points"),
        longitude=xr.DataArray(df["lon"].values, dims="points"),
        valid_time=xr.DataArray(df["datetime_hour"].values, dims="points"),
        method="nearest",
    )
    for var in ["u10", "v10", "t2m", "blh"]:
        df[var] = extracted[var].values

    df["wind_speed"] = np.sqrt(df["u10"] ** 2 + df["v10"] ** 2)
    df["wind_direction"] = (np.degrees(np.arctan2(-df["u10"], -df["v10"])) + 360) % 360
    df["temp_celsius"] = df["t2m"] - 273.15

    out = config.DATA_DIR / "delhi_ncr_pm25_with_era5.csv"
    df.to_csv(out, index=False)

    print(f"Saved: {out}  ({len(df)} rows)")
    print(df[["station_name", "datetime_utc", "pm25", "wind_speed", "wind_direction"]].head(10))
    print(df["wind_speed"].describe())


if __name__ == "__main__":
    main()
