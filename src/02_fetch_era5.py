"""Step 2 - download ERA5 hourly weather for Delhi-NCR from the Copernicus Climate Data Store.

Variables: 10 m wind (u, v), 2 m temperature and boundary-layer height for the study month.
Output: data/era5_wind_delhi_ncr_aug2026.nc

One-time setup: create a free account at https://cds.climate.copernicus.eu, accept the
licence of the "ERA5 hourly data on single levels" dataset, and put your API credentials in
~/.cdsapirc (see the cdsapi documentation). The key is read from that file, never from this repo.
"""
import cdsapi

import config


def main():
    if config.ERA5_FILE.exists():
        print(f"{config.ERA5_FILE} already exists - delete it to download again.")
        return

    client = cdsapi.Client()
    client.retrieve(
        "reanalysis-era5-single-levels",
        {
            "product_type": "reanalysis",
            "variable": [
                "10m_u_component_of_wind",
                "10m_v_component_of_wind",
                "2m_temperature",
                "boundary_layer_height",
            ],
            "year": config.ERA5_YEAR,
            "month": config.ERA5_MONTH,
            "day": [f"{d:02d}" for d in range(1, 32)],
            "time": [f"{h:02d}:00" for h in range(24)],
            "area": config.ERA5_AREA,  # North, West, South, East
            "format": "netcdf",
        },
        str(config.ERA5_FILE),
    )
    print(f"Download complete: {config.ERA5_FILE}")


if __name__ == "__main__":
    main()
