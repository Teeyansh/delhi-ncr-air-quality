"""Step 1 - download Delhi-NCR air-quality measurements from the OpenAQ v3 API.

For every station inside the Delhi-NCR bounding box it finds the sensor of each
pollutant that is still active, downloads all measurements in the study period
(paginated) and writes:

    data/delhi_ncr_stations.csv                 station metadata
    data/delhi_ncr_<pollutant>.csv              one file per pollutant (pm25, pm10, no2, so2, co, o3)
    data/delhi_ncr_all_pollutants_merged.csv    the six pollutants joined on station + timestamp

Needs an API key in the OPENAQ_API_KEY environment variable (see .env.example).
The script sleeps 1 s between requests to stay inside OpenAQ's rate limit, so a full
run takes a while.
"""
import time

import numpy as np
import pandas as pd
import requests

import config

HEADERS: dict = {}          # filled in main() so the key is never stored in the code
_location_cache: dict = {}  # station_id -> location details (avoids one request per pollutant)


def _get(url, params=None, retries=3):
    """GET with a timeout and a simple retry on connection problems. Returns None on failure."""
    for attempt in range(1, retries + 1):
        try:
            return requests.get(url, headers=HEADERS, params=params, timeout=15)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as exc:
            print(f"  Connection issue on {url} (attempt {attempt}/{retries}): {exc}")
            time.sleep(3)
    return None


def fetch_delhi_ncr_stations(limit=1000) -> pd.DataFrame:
    """All OpenAQ stations in India, filtered to the Delhi-NCR bounding box."""
    r = _get(f"{config.OPENAQ_BASE_URL}/locations",
             params={"countries_id": config.INDIA_COUNTRY_ID, "limit": limit})
    if r is None or r.status_code != 200:
        status = None if r is None else r.status_code
        raise SystemExit(f"Could not fetch the station list (HTTP status: {status}). Check your API key.")

    payload = r.json()
    found = payload.get("meta", {}).get("found")
    if str(found).startswith(">") or (isinstance(found, int) and found > limit):
        print(f"WARNING: OpenAQ reports {found} stations for India but only the first {limit} "
              f"were fetched; some Delhi-NCR stations may be missing.")

    b = config.BBOX
    in_box = [
        s for s in payload["results"]
        if b["lat_min"] <= s["coordinates"]["latitude"] <= b["lat_max"]
        and b["lon_min"] <= s["coordinates"]["longitude"] <= b["lon_max"]
    ]
    print(f"Total Delhi-NCR stations found: {len(in_box)}")
    return pd.DataFrame(in_box)


def get_location_details(station_id):
    if station_id not in _location_cache:
        r = _get(f"{config.OPENAQ_BASE_URL}/locations/{station_id}")
        if r is None or r.status_code != 200:
            return None  # not cached, so the next pollutant will try again
        _location_cache[station_id] = r.json()["results"][0]
    return _location_cache[station_id]


def get_active_sensor(station_id, parameter):
    """Find the station's sensor for `parameter` that reported after MIN_LAST_DATE.

    Returns (sensor_id, last_date, lat, lon); sensor_id is None if there is no active sensor.
    """
    details = get_location_details(station_id)
    if details is None:
        return None, None, None, None
    lat, lon = details["coordinates"]["latitude"], details["coordinates"]["longitude"]

    for sensor in details["sensors"]:
        if sensor["parameter"]["name"] != parameter:
            continue
        sr = _get(f"{config.OPENAQ_BASE_URL}/sensors/{sensor['id']}")
        if sr is None or sr.status_code != 200:
            continue
        datetime_last = sr.json()["results"][0].get("datetimeLast")
        if datetime_last is None:
            continue
        last_date = datetime_last["utc"]
        if last_date >= config.MIN_LAST_DATE:  # ISO strings compare correctly
            return sensor["id"], last_date, lat, lon
    return None, None, lat, lon


def get_all_measurements(sensor_id, date_from, date_to, page_size=1000):
    """Download every measurement of one sensor, page by page."""
    records, page = [], 1
    while True:
        r = _get(f"{config.OPENAQ_BASE_URL}/sensors/{sensor_id}/measurements",
                 params={"datetime_from": date_from, "datetime_to": date_to,
                         "limit": page_size, "page": page})
        if r is None or r.status_code != 200:
            break  # keep what we already have
        data = r.json()["results"]
        if not data:
            break
        records.extend(data)
        if len(data) < page_size:
            break
        page += 1
        time.sleep(1)
    return records


def pull_pollutant(parameter, stations: pd.DataFrame) -> pd.DataFrame:
    """One pollutant across all stations -> long table (one row per measurement)."""
    print(f"\n--- Pulling {parameter} ---")
    rows, active, dead = [], 0, 0
    for i, (station_id, name) in enumerate(zip(stations["id"], stations["name"])):
        sensor_id, _, lat, lon = get_active_sensor(station_id, parameter)
        if sensor_id:
            active += 1
            records = get_all_measurements(sensor_id, config.DATE_FROM, config.DATE_TO)
            rows.extend({
                "station_id": station_id, "station_name": name, "lat": lat, "lon": lon,
                "datetime_utc": rec["period"]["datetimeFrom"]["utc"], parameter: rec["value"],
            } for rec in records)
            print(f"  {name}: {len(records)} {parameter} records pulled")
        else:
            dead += 1
        if (i + 1) % 20 == 0:
            print(f"  Checked {i + 1}/{len(stations)} stations...")
        time.sleep(1)
    print(f"{parameter}: {active} active stations, {dead} dead/no sensor")
    return pd.DataFrame(rows, columns=["station_id", "station_name", "lat", "lon", "datetime_utc", parameter])


def merge_pollutants(pollutant_dfs: dict) -> pd.DataFrame:
    """Left-join every pollutant onto the PM2.5 table (station + timestamp)."""
    pollutants = config.POLLUTANTS
    master = pollutant_dfs[pollutants[0]]
    for p in pollutants[1:]:
        df_p = pollutant_dfs[p]
        if df_p.empty:
            master[p] = np.nan
        else:
            master = master.merge(df_p[["station_id", "datetime_utc", p]],
                                  on=["station_id", "datetime_utc"], how="left")
    return master


def main():
    HEADERS["X-API-KEY"] = config.get_openaq_key()

    stations = fetch_delhi_ncr_stations()
    stations.to_csv(config.DATA_DIR / "delhi_ncr_stations.csv", index=False)

    pollutant_dfs = {}
    for p in config.POLLUTANTS:
        df_p = pull_pollutant(p, stations)
        df_p.to_csv(config.DATA_DIR / f"delhi_ncr_{p}.csv", index=False)
        pollutant_dfs[p] = df_p
        print(f"Saved delhi_ncr_{p}.csv with {len(df_p)} rows")

    master = merge_pollutants(pollutant_dfs)
    master.to_csv(config.DATA_DIR / "delhi_ncr_all_pollutants_merged.csv", index=False)
    print(f"\nMaster merged file saved. Total rows: {len(master)}")
    print("Missing values per pollutant:")
    print(master[config.POLLUTANTS].isna().sum())


if __name__ == "__main__":
    main()
