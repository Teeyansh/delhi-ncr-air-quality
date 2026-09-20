"""Step 5 - estimate the upwind ("source") direction of each hotspot cluster.

For every hotspot cluster this takes the circular mean of the wind direction over the study
period. Because ``wind_direction`` is the direction the wind comes FROM, that mean points
towards the area the pollution is most likely arriving from.

LIMITATIONS (see README): this is a monthly average over the monsoon, ERA5 is a ~28 km grid so
neighbouring clusters share almost the same wind, and the average is not weighted by pollution
level. Treat it as a rough indication, not a source attribution.

Input : data/delhi_ncr_pm25_with_era5.csv, results/stations_with_clusters_multipollutant.csv,
        results/hotspot_clusters_multipollutant.csv
Output: results/hotspot_source_directions.csv
"""
import pandas as pd

import config
from utils import circular_mean_degrees, compass_label


def main():
    df = pd.read_csv(config.DATA_DIR / "delhi_ncr_pm25_with_era5.csv")
    stations = pd.read_csv(config.RESULTS_DIR / "stations_with_clusters_multipollutant.csv")
    hotspots = pd.read_csv(config.RESULTS_DIR / "hotspot_clusters_multipollutant.csv")

    df["cluster"] = df["station_id"].map(dict(zip(stations["station_id"], stations["cluster"])))
    hotspot_ids = sorted(set(hotspots["cluster"]))
    df_hotspots = df[df["cluster"].isin(hotspot_ids)]

    rows = []
    for cluster_id in hotspot_ids:
        data = df_hotspots[df_hotspots["cluster"] == cluster_id]
        wind_from = circular_mean_degrees(data["wind_direction"])
        rows.append({
            "cluster": cluster_id,
            "avg_pm25": data["pm25"].mean(),
            "avg_wind_speed": data["wind_speed"].mean(),
            "estimated_source_direction_deg": wind_from,
            "estimated_source_direction_compass": compass_label(wind_from),
        })

    result = pd.DataFrame(rows).sort_values("avg_pm25", ascending=False)
    print(result)
    result.to_csv(config.RESULTS_DIR / "hotspot_source_directions.csv", index=False)
    print("\nSaved: results/hotspot_source_directions.csv")


if __name__ == "__main__":
    main()
