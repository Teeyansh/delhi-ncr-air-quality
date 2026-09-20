"""Central configuration: paths, study area/period and model settings.

* Large raw / intermediate files go to ``DATA_DIR`` (git-ignored, re-creatable).
* Small final outputs used by the README and the dashboard go to ``RESULTS_DIR``
  (committed to git).

Set the ``AQ_DATA_DIR`` environment variable to keep the data somewhere else.
"""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("AQ_DATA_DIR", ROOT / "data"))
RESULTS_DIR = ROOT / "results"
MAPS_DIR = RESULTS_DIR / "maps"
FIGURES_DIR = RESULTS_DIR / "figures"

for _d in (DATA_DIR, RESULTS_DIR, MAPS_DIR, FIGURES_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------- study area
OPENAQ_BASE_URL = "https://api.openaq.org/v3"
INDIA_COUNTRY_ID = 9  # OpenAQ country id for India
BBOX = {"lat_min": 28.4, "lat_max": 28.9, "lon_min": 76.8, "lon_max": 77.5}  # Delhi-NCR
ERA5_AREA = [29.0, 76.5, 28.0, 77.8]  # North, West, South, East (slightly larger than BBOX)

# -------------------------------------------------------------- study period
DATE_FROM = "2026-08-01T00:00:00Z"
DATE_TO = "2026-08-31T23:59:59Z"
ERA5_YEAR, ERA5_MONTH = "2026", "08"
MIN_LAST_DATE = "2026-01-01"  # ignore sensors that stopped reporting before this date

POLLUTANTS = ["pm25", "pm10", "no2", "so2", "co", "o3"]

# ------------------------------------------------------------ hotspot search
EPS_KM = 3            # DBSCAN neighbourhood radius between stations
MIN_SAMPLES = 2       # stations needed to form a cluster
EARTH_RADIUS_KM = 6371.0

# ------------------------------------------------------------------ forecast
SPLIT_DATE = "2026-08-27"  # everything from this date on is the test set
TARGET_COL = "pm25"
FEATURE_COLS = [
    "hour", "day_of_week", "day_of_month",
    "pm25_lag1", "pm25_lag4", "pm25_lag96", "pm25_rolling_mean_4",
    "wind_speed", "wind_direction", "temp_celsius", "blh",
    "lat", "lon",
]
XGB_PARAMS = dict(
    n_estimators=300, max_depth=6, learning_rate=0.05,
    subsample=0.8, colsample_bytree=0.8, random_state=42,
)

# ----------------------------------------------------------------- filenames
ERA5_FILE = DATA_DIR / "era5_wind_delhi_ncr_aug2026.nc"


def get_openaq_key() -> str:
    """Read the OpenAQ API key from the environment (or a local ``.env`` file)."""
    try:
        from dotenv import load_dotenv

        load_dotenv(ROOT / ".env")
    except ImportError:  # python-dotenv is optional
        pass
    key = os.environ.get("OPENAQ_API_KEY")
    if not key:
        raise SystemExit(
            "OPENAQ_API_KEY is not set. Copy .env.example to .env and paste your key "
            "(free at https://explore.openaq.org/register)."
        )
    return key
