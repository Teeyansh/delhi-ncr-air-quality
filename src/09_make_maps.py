"""Step 9 - build the interactive Folium maps (open the HTML files in a browser).

1. results/maps/delhi_ncr_hotspot_map.html
   Every station coloured by cluster; composite-index hotspots highlighted.
2. results/maps/delhi_ncr_hotspot_comparison_map.html
   Two toggleable layers comparing "PM2.5-only" hotspots with "composite index" hotspots.

Input : results/stations_with_clusters_multipollutant.csv, cluster_summary_multipollutant.csv,
        hotspot_clusters_multipollutant.csv
"""
import folium
import pandas as pd
from folium import MacroElement
from jinja2 import Template

import config

# one colour per cluster id (cycles); must be valid CSS colours
COLORS = ["red", "orange", "purple", "darkred", "blue", "green",
          "cadetblue", "darkgreen", "indigo", "black", "gray"]

LEGEND_TEMPLATE = """
{% macro html(this, kwargs) %}
<div style="position: fixed; bottom: 30px; left: 30px; z-index: 9999; background-color: white;
    padding: 12px 16px; border: 2px solid #444; border-radius: 6px; font-size: 13px;
    line-height: 1.6; box-shadow: 2px 2px 6px rgba(0,0,0,0.3); max-width: 260px;">
    <b>Delhi-NCR Pollution Hotspots</b><br>
    __NOTE__
    <span style="color:purple; font-size:16px;">&#9679;</span>
    <span style="color:green; font-size:16px;">&#9679;</span>
    <span style="color:black; font-size:16px;">&#9679;</span>
    <span style="color:orange; font-size:16px;">&#9679;</span>
    Hotspot clusters <i>(color = cluster ID)</i><br>
    <span style="color:lightblue; font-size:16px;">&#9679;</span> Below hotspot threshold<br>
    <span style="color:lightgray; font-size:16px;">&#9679;</span> Noise (not in any cluster)<br>
    <span style="border: 2px dashed red; padding: 0 6px;">&nbsp;&nbsp;</span> Hotspot boundary (~3 km)
</div>
{% endmacro %}
"""


def marker_style(cluster, hotspot_ids):
    """(colour, radius) of a station marker."""
    if cluster == -1:
        return "lightgray", 4                                   # noise
    if cluster in hotspot_ids:
        return COLORS[int(cluster) % len(COLORS)], 8            # hotspot cluster
    return "lightblue", 5                                        # cluster below threshold


def add_station_markers(layer, station_avg, hotspot_ids):
    for _, row in station_avg.iterrows():
        color, radius = marker_style(row["cluster"], hotspot_ids)
        popup = (f"<b>{row['station_name']}</b><br>Cluster: {row['cluster']}<br>"
                 f"PM2.5: {row['pm25']:.1f}<br>Pollution Index: {row['pollution_index']:.3f}")
        folium.CircleMarker(
            location=[row["lat"], row["lon"]], radius=radius,
            color=color, fill=True, fill_color=color, fill_opacity=0.8,
            popup=folium.Popup(popup, max_width=250),
        ).add_to(layer)


def add_hotspot_boundaries(layer, cluster_summary, hotspot_ids, with_popup=False):
    """Dashed ~3 km circle around the centre of each hotspot cluster."""
    for _, row in cluster_summary[cluster_summary["cluster"].isin(hotspot_ids)].iterrows():
        popup = None
        if with_popup:
            popup = (f"Hotspot Cluster {int(row['cluster'])}<br>"
                     f"Avg Pollution Index: {row['avg_pollution_index']:.3f}")
        folium.Circle(
            location=[row["center_lat"], row["center_lon"]], radius=config.EPS_KM * 1000,
            color="red", fill=False, weight=2, dash_array="5,5", popup=popup,
        ).add_to(layer)


def add_legend(m, note=""):
    legend = MacroElement()
    legend._template = Template(LEGEND_TEMPLATE.replace("__NOTE__", note))
    m.get_root().add_child(legend)


def base_map(station_avg):
    return folium.Map(location=[station_avg["lat"].mean(), station_avg["lon"].mean()],
                      zoom_start=10, tiles="OpenStreetMap")


def build_hotspot_map(station_avg, hotspot_clusters):
    hotspot_ids = set(hotspot_clusters["cluster"])
    m = base_map(station_avg)
    add_station_markers(m, station_avg, hotspot_ids)
    add_hotspot_boundaries(m, hotspot_clusters, hotspot_ids, with_popup=True)
    add_legend(m)
    return m


def build_comparison_map(station_avg, cluster_summary):
    # two definitions of "hotspot cluster" (same clusters, different threshold)
    city_mean_pm25 = station_avg["pm25"].mean()
    pm25_ids = set(cluster_summary.loc[cluster_summary["avg_pm25"] > city_mean_pm25, "cluster"])
    city_mean_index = station_avg["pollution_index"].mean()
    composite_ids = set(cluster_summary.loc[cluster_summary["avg_pollution_index"] > city_mean_index, "cluster"])

    print(f"City-wide average PM2.5: {city_mean_pm25:.2f}")
    print(f"PM2.5-only hotspot clusters:      {sorted(pm25_ids)}")
    print(f"Composite-index hotspot clusters: {sorted(composite_ids)}")
    print(f"Flagged by BOTH methods:          {sorted(pm25_ids & composite_ids)}")
    print(f"Flagged ONLY by PM2.5:            {sorted(pm25_ids - composite_ids)}")
    print(f"Flagged ONLY by composite index:  {sorted(composite_ids - pm25_ids)}")

    m = base_map(station_avg)
    pm25_layer = folium.FeatureGroup(name="PM2.5-only Hotspots", show=True)
    composite_layer = folium.FeatureGroup(name="Composite Index Hotspots", show=False)
    for layer, ids in ((pm25_layer, pm25_ids), (composite_layer, composite_ids)):
        add_station_markers(layer, station_avg, ids)
        add_hotspot_boundaries(layer, cluster_summary, ids)
        layer.add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)
    add_legend(m, "Use the layer control (top-right) to switch between the PM2.5-only and "
                  "composite-index definitions.<br><br>")
    return m


def main():
    station_avg = pd.read_csv(config.RESULTS_DIR / "stations_with_clusters_multipollutant.csv")
    cluster_summary = pd.read_csv(config.RESULTS_DIR / "cluster_summary_multipollutant.csv")
    hotspot_clusters = pd.read_csv(config.RESULTS_DIR / "hotspot_clusters_multipollutant.csv")

    out1 = config.MAPS_DIR / "delhi_ncr_hotspot_map.html"
    build_hotspot_map(station_avg, hotspot_clusters).save(out1)
    print(f"Map saved to: {out1}\n")

    out2 = config.MAPS_DIR / "delhi_ncr_hotspot_comparison_map.html"
    build_comparison_map(station_avg, cluster_summary).save(out2)
    print(f"\nComparison map saved to: {out2}")


if __name__ == "__main__":
    main()
