"""Helpers shared by several pipeline steps (previously copy-pasted between scripts)."""
import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import MinMaxScaler

from config import EARTH_RADIUS_KM, EPS_KM, MIN_SAMPLES

COMPASS_POINTS = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                  "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]


def circular_mean_degrees(degrees) -> float:
    """Mean of angles in degrees. 350 and 10 average to 0, not 180 (NaNs are ignored)."""
    deg = pd.Series(degrees).dropna()
    if deg.empty:
        return np.nan
    rad = np.radians(deg.to_numpy(dtype=float))
    mean_rad = np.arctan2(np.sin(rad).mean(), np.cos(rad).mean())
    return (np.degrees(mean_rad) + 360) % 360


def compass_label(degrees) -> str:
    """Convert degrees (0 = N, 90 = E) to a 16-point compass label."""
    if pd.isna(degrees):
        return "N/A"
    return COMPASS_POINTS[int(round(degrees / 22.5)) % 16]


def cluster_stations(lat, lon, eps_km: float = EPS_KM, min_samples: int = MIN_SAMPLES):
    """DBSCAN on station coordinates using great-circle (haversine) distance.

    Returns one label per station; -1 means "noise" (not in any cluster).
    """
    coords_rad = np.radians(np.column_stack([np.asarray(lat), np.asarray(lon)]))
    db = DBSCAN(eps=eps_km / EARTH_RADIUS_KM, min_samples=min_samples, metric="haversine")
    return db.fit_predict(coords_rad)


def composite_pollution_index(station_avg: pd.DataFrame, pollutants,
                              fill_missing: bool = False) -> pd.Series:
    """Composite index in 0-1: min-max scale each pollutant, then average across pollutants.

    fill_missing=False: average over the pollutants a station actually has (NaNs skipped).
    fill_missing=True : first fill missing values with the column mean (used for daily data).
    """
    data = station_avg[list(pollutants)]
    if fill_missing:
        data = data.fillna(data.mean())
        return pd.Series(MinMaxScaler().fit_transform(data).mean(axis=1), index=station_avg.index)
    normalized = pd.DataFrame(MinMaxScaler().fit_transform(data),
                              columns=list(pollutants), index=station_avg.index)
    return normalized.mean(axis=1, skipna=True)

