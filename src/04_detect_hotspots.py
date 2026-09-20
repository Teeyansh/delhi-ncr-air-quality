"""Step 4 - find pollution hotspots for the whole study period.

1. Average every pollutant per station.
2. Build a composite pollution index (each pollutant scaled 0-1, then averaged).
3. Group stations that are close together with DBSCAN (haversine distance, eps = 3 km).
4. A cluster is a "hotspot" if its mean composite index is above the city-wide mean.

Input : data/delhi_ncr_all_pollutants_merged.csv
Output: results/stations_with_clusters_multipollutant.csv
        results/cluster_summary_multipollutant.csv
        results/hotspot_clusters_multipollutant.csv
"""
import pandas as pd

import config
from utils import cluster_stations, composite_pollution_index

POLLUTANTS = config.POLLUTANTS


def summarize_clusters(station_avg: pd.DataFrame) -> pd.DataFrame:
    """One row per real cluster (noise excluded): size, mean PM2.5, mean index, centre point."""
    return (
        station_avg[station_avg["cluster"] != -1]
        .groupby("cluster")
        .agg(
            num_stations=("station_id", "count"),
            avg_pm25=("pm25", "mean"),
            avg_pollution_index=("pollution_index", "mean"),
            center_lat=("lat", "mean"),
            center_lon=("lon", "mean"),
        )
        .reset_index()
        .sort_values("avg_pollution_index", ascending=False)
    )


def main():
    df = pd.read_csv(config.DATA_DIR / "delhi_ncr_all_pollutants_merged.csv")

    station_avg = (
        df.groupby(["station_id", "station_name", "lat", "lon"])[POLLUTANTS].mean().reset_index()
    )
    print(f"Number of stations: {len(station_avg)}")

    station_avg["pollution_index"] = composite_pollution_index(station_avg, POLLUTANTS)
    station_avg["cluster"] = cluster_stations(station_avg["lat"], station_avg["lon"])
    # How many of the 6 pollutants each station actually reports (index quality indicator)
    station_avg["pollutants_available"] = station_avg[POLLUTANTS].notna().sum(axis=1)

    n_clusters = station_avg.loc[station_avg["cluster"] != -1, "cluster"].nunique()
    n_noise = int((station_avg["cluster"] == -1).sum())
    print(f"\nClusters: {n_clusters}, Noise: {n_noise}")

    cluster_summary = summarize_clusters(station_avg)
    print("\nCluster summary (sorted by composite pollution index):")
    print(cluster_summary)

    city_mean_index = station_avg["pollution_index"].mean()
    print(f"\nCity-wide average pollution index: {city_mean_index:.3f}")
    hotspot_clusters = cluster_summary[cluster_summary["avg_pollution_index"] > city_mean_index].copy()
    print("\nHotspot clusters (above city average):")
    print(hotspot_clusters)

    station_avg.to_csv(config.RESULTS_DIR / "stations_with_clusters_multipollutant.csv", index=False)
    cluster_summary.to_csv(config.RESULTS_DIR / "cluster_summary_multipollutant.csv", index=False)
    hotspot_clusters.to_csv(config.RESULTS_DIR / "hotspot_clusters_multipollutant.csv", index=False)
    print("\nSaved all outputs to results/.")


if __name__ == "__main__":
    main()
