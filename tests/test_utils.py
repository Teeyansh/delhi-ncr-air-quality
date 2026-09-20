import numpy as np
import pandas as pd
import pytest

from utils import circular_mean_degrees, cluster_stations, compass_label, composite_pollution_index


def test_circular_mean_wraps_around_north():
    # 350 deg and 10 deg average to north (0/360), not south (180)
    result = circular_mean_degrees([350, 10])
    assert min(result, 360 - result) == pytest.approx(0, abs=1e-6)


def test_circular_mean_ignores_nan_and_handles_empty():
    assert circular_mean_degrees([90, np.nan, 90]) == pytest.approx(90)
    assert np.isnan(circular_mean_degrees([np.nan]))


@pytest.mark.parametrize("degrees, label", [(0, "N"), (90, "E"), (180, "S"), (270, "W"),
                                            (202.5, "SSW"), (359, "N")])
def test_compass_label(degrees, label):
    assert compass_label(degrees) == label


def test_compass_label_nan():
    assert compass_label(np.nan) == "N/A"


def test_cluster_stations_groups_nearby_and_flags_noise():
    # two stations ~1 km apart, one ~40 km away -> one cluster + one noise point
    lat = [28.600, 28.609, 28.950]
    lon = [77.200, 77.200, 77.500]
    labels = cluster_stations(lat, lon, eps_km=3, min_samples=2)
    assert labels[0] == labels[1] != -1
    assert labels[2] == -1


def test_composite_index_is_between_0_and_1_and_skips_missing():
    df = pd.DataFrame({"pm25": [10.0, 50.0, 90.0], "no2": [5.0, np.nan, 25.0]})
    index = composite_pollution_index(df, ["pm25", "no2"])
    assert index.between(0, 1).all()
    assert index.iloc[0] == pytest.approx(0.0)   # lowest value of every pollutant
    assert index.iloc[2] == pytest.approx(1.0)   # highest value of every pollutant
    assert index.iloc[1] == pytest.approx(0.5)   # only pm25 available -> uses that alone
