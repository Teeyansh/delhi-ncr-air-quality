"""Tests for the OpenAQ download logic using a fake HTTP layer (no network, no API key)."""
from conftest import load_step

fetch = load_step("01_fetch_openaq.py")


class FakeResponse:
    def __init__(self, payload, status=200):
        self._payload, self.status_code = payload, status

    def json(self):
        return self._payload


def test_station_filter_keeps_only_delhi_ncr(monkeypatch):
    stations = [
        {"id": 1, "name": "Delhi", "coordinates": {"latitude": 28.6, "longitude": 77.2}},
        {"id": 2, "name": "Mumbai", "coordinates": {"latitude": 19.1, "longitude": 72.9}},
    ]
    monkeypatch.setattr(fetch, "_get", lambda url, params=None, retries=3:
                        FakeResponse({"meta": {"found": 2}, "results": stations}))
    df = fetch.fetch_delhi_ncr_stations()
    assert df["id"].tolist() == [1]


def test_active_sensor_requires_recent_data(monkeypatch):
    fetch._location_cache.clear()
    details = {"coordinates": {"latitude": 28.6, "longitude": 77.2},
               "sensors": [{"id": 10, "parameter": {"name": "pm10"}},
                           {"id": 11, "parameter": {"name": "pm25"}}]}

    def fake_get(url, params=None, retries=3):
        if url.endswith("/locations/5"):
            return FakeResponse({"results": [details]})
        if url.endswith("/sensors/11"):
            return FakeResponse({"results": [{"datetimeLast": {"utc": "2026-08-31T23:00:00Z"}}]})
        raise AssertionError(f"unexpected url {url}")

    monkeypatch.setattr(fetch, "_get", fake_get)
    assert fetch.get_active_sensor(5, "pm25") == (11, "2026-08-31T23:00:00Z", 28.6, 77.2)
    assert fetch.get_active_sensor(5, "so2")[0] is None  # station has no so2 sensor


def test_measurements_are_paginated(monkeypatch):
    pages = {1: [{"value": i} for i in range(3)], 2: [{"value": 99}]}
    monkeypatch.setattr(fetch, "_get", lambda url, params=None, retries=3:
                        FakeResponse({"results": pages.get(params["page"], [])}))
    monkeypatch.setattr(fetch.time, "sleep", lambda s: None)
    records = fetch.get_all_measurements(1, "a", "b", page_size=3)
    assert [r["value"] for r in records] == [0, 1, 2, 99]
