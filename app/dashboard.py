"""Delhi-NCR air pollution dashboard.

Run locally:  streamlit run app/dashboard.py
It only reads the small precomputed files in results/, so it also runs on Streamlit
Community Cloud straight from the repository.
"""
from pathlib import Path

import folium
import pandas as pd
import plotly.express as px
import streamlit as st
from streamlit_folium import st_folium

RESULTS_DIR = Path(__file__).resolve().parent.parent / "results"

# one colour per cluster id (cycles); must be valid CSS colours
COLORS = ["red", "orange", "purple", "darkred", "blue", "green",
          "cadetblue", "darkgreen", "indigo", "black", "gray"]

st.set_page_config(page_title="Delhi-NCR Air Pollution Dashboard", layout="wide")


@st.cache_data
def load_data():
    daily_hotspots = pd.read_csv(RESULTS_DIR / "daily_hotspots_august.csv")
    daily_hotspots["date"] = pd.to_datetime(daily_hotspots["date"]).dt.date

    predictions = pd.read_csv(RESULTS_DIR / "pm25_predictions.csv")
    predictions["datetime_utc"] = pd.to_datetime(predictions["datetime_utc"])
    return daily_hotspots, predictions


daily_hotspots, predictions = load_data()

st.title("Delhi-NCR Air Pollution Hotspot Dashboard")
st.markdown("Hotspot detection, source direction estimation, and PM2.5 forecasting for August 2026")

# ------------------------------------------------------------ sidebar controls
st.sidebar.header("Controls")

available_dates = sorted(daily_hotspots["date"].unique())
selected_date = st.sidebar.select_slider("Select date", options=available_dates, value=available_dates[0])

pollutant_options = {"Composite Index": "avg_pollution_index", "PM2.5": "avg_pm25"}
selected_label = st.sidebar.selectbox("Hotspot definition", list(pollutant_options.keys()))
selected_col = pollutant_options[selected_label]

# ------------------------------------------------------ data for selected day
day_data = daily_hotspots[daily_hotspots["date"] == selected_date].copy()

if selected_col == "avg_pm25":
    day_data["is_hotspot_display"] = day_data["avg_pm25"] > day_data["avg_pm25"].mean()
else:
    day_data["is_hotspot_display"] = day_data["is_hotspot"]

hotspot_count = int(day_data["is_hotspot_display"].sum())

col1, col2, col3, col4 = st.columns(4)
col1.metric("Date", str(selected_date))
col2.metric("Total Clusters", len(day_data))
col3.metric("Hotspot Clusters", hotspot_count)
col4.metric("Avg PM2.5 (city)", f"{day_data['avg_pm25'].mean():.1f} µg/m³")

# ------------------------------------------------------------------------- map
st.subheader("Hotspot Map")

m = folium.Map(location=[28.6, 77.15], zoom_start=10, tiles="OpenStreetMap")

for _, row in day_data.iterrows():
    is_hot = row["is_hotspot_display"]
    color = COLORS[int(row["cluster"]) % len(COLORS)] if is_hot else "lightblue"

    popup_text = (
        f"<b>Cluster {int(row['cluster'])}</b><br>"
        f"Stations: {row['num_stations']}<br>"
        f"Avg PM2.5: {row['avg_pm25']:.1f}<br>"
        f"Pollution Index: {row['avg_pollution_index']:.3f}<br>"
        f"Wind Speed: {row['avg_wind_speed']:.1f} m/s<br>"
        f"Source Direction: {row['source_direction_compass']}"
    )

    folium.CircleMarker(
        location=[row["center_lat"], row["center_lon"]],
        radius=10 if is_hot else 6,
        color=color, fill=True, fill_color=color, fill_opacity=0.8,
        popup=folium.Popup(popup_text, max_width=250),
        tooltip=f"Cluster {int(row['cluster'])} — {row['source_direction_compass']}",
    ).add_to(m)

    if is_hot:
        folium.Circle(
            location=[row["center_lat"], row["center_lon"]], radius=3000,
            color="red", fill=False, weight=2, dash_array="5,5",
        ).add_to(m)

st_folium(m, height=500, use_container_width=True)

# ------------------------------------------------------------ hotspot details
st.subheader("Hotspot Details")
display_cols = ["cluster", "num_stations", "avg_pm25", "avg_pollution_index",
                "avg_wind_speed", "source_direction_compass", "is_hotspot_display"]
st.dataframe(day_data[display_cols].sort_values("avg_pollution_index", ascending=False), width="stretch")
st.caption("Source direction = average direction the wind blows from over the day (ERA5). "
           "It is a rough indication only.")

# --------------------------------------------------------------- forecast panel
st.subheader("PM2.5 Forecast — Actual vs Predicted")
st.caption("Test period only (Aug 27–31). The model predicts the next 15-minute reading from "
           "recent readings, weather and location.")

station_list = sorted(predictions["station_name"].unique())
selected_station = st.selectbox("Select station for forecast view", station_list)

station_pred = predictions[predictions["station_name"] == selected_station].sort_values("datetime_utc")

if len(station_pred) > 0:
    fig = px.line(
        station_pred, x="datetime_utc", y=["pm25", "pm25_predicted"],
        labels={"value": "PM2.5 (µg/m³)", "datetime_utc": "Date", "variable": "Series"},
        title=f"Actual vs Predicted PM2.5 — {selected_station}",
    )
    st.plotly_chart(fig, width="stretch")
else:
    st.info("No forecast data available for this station (forecast only covers Aug 27-31).")
