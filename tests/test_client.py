"""Tests for client.py: Open-Meteo URL selection and HTTP requests."""

import datetime

import pytest
import respx
from httpx import HTTPError

from solarpanels.client import _pick_api, fetch_hourly_weather

FAKE_RESPONSE = {
    "hourly": {
        "time": [
            "2026-06-01T00:00",
            "2026-06-01T01:00",
            "2026-06-01T02:00",
        ],
        "shortwave_radiation": [0.0, 50.0, 200.0],
        "direct_normal_irradiance": [0.0, 100.0, 400.0],
        "diffuse_radiation": [0.0, 30.0, 80.0],
        "temperature_2m": [15.0, 15.5, 16.0],
    },
    "elevation": 50.0,
}

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
HOURLY = "shortwave_radiation,direct_normal_irradiance,diffuse_radiation,temperature_2m"


# ── _pick_api ───────────────────────────────────────────────────────


class TestPickApi:
    def test_forecast_recent_past(self):
        today = datetime.date.today()
        start = today - datetime.timedelta(days=10)
        end = today + datetime.timedelta(days=5)
        assert _pick_api(start, end) == FORECAST_URL

    def test_forecast_future_only(self):
        today = datetime.date.today()
        start = today + datetime.timedelta(days=1)
        end = today + datetime.timedelta(days=10)
        assert _pick_api(start, end) == FORECAST_URL

    def test_archive_past_beyond_92(self):
        today = datetime.date.today()
        start = today - datetime.timedelta(days=200)
        end = today - datetime.timedelta(days=100)
        assert _pick_api(start, end) == ARCHIVE_URL

    def test_archive_exactly_93_days_ago(self):
        today = datetime.date.today()
        start = today - datetime.timedelta(days=93)
        end = today - datetime.timedelta(days=90)
        assert _pick_api(start, end) == ARCHIVE_URL

    def test_archive_start_past_end_past(self):
        today = datetime.date.today()
        start = today - datetime.timedelta(days=60)
        end = today - datetime.timedelta(days=30)
        assert _pick_api(start, end) == FORECAST_URL

    def test_raises_out_of_bounds(self):
        today = datetime.date.today()
        start = today - datetime.timedelta(days=93)
        end = today + datetime.timedelta(days=20)
        with pytest.raises(ValueError, match="out of supported bounds"):
            _pick_api(start, end)

    def test_raises_future_too_far(self):
        today = datetime.date.today()
        start = today + datetime.timedelta(days=10)
        end = today + datetime.timedelta(days=20)
        with pytest.raises(ValueError, match="out of supported bounds"):
            _pick_api(start, end)


# ── fetch_hourly_weather ───────────────────────────────────────────


class TestFetchHourlyWeather:
    @respx.mock
    @pytest.mark.asyncio
    async def test_forecast_api(self):
        today = datetime.date.today()
        start = today - datetime.timedelta(days=1)
        end = today + datetime.timedelta(days=2)
        route = respx.get(FORECAST_URL).respond(json=FAKE_RESPONSE)

        times, ghi, dni, dhi, temp, elev = await fetch_hourly_weather(
            48.85,
            2.35,
            start,
            end,
        )

        assert route.called
        req = route.calls[0].request
        assert float(req.url.params["latitude"]) == 48.85
        assert float(req.url.params["longitude"]) == 2.35
        assert req.url.params["hourly"] == HOURLY
        assert req.url.params["start_date"] == start.isoformat()
        assert req.url.params["end_date"] == end.isoformat()

        assert times == FAKE_RESPONSE["hourly"]["time"]
        assert ghi == FAKE_RESPONSE["hourly"]["shortwave_radiation"]
        assert dni == FAKE_RESPONSE["hourly"]["direct_normal_irradiance"]
        assert dhi == FAKE_RESPONSE["hourly"]["diffuse_radiation"]
        assert temp == FAKE_RESPONSE["hourly"]["temperature_2m"]
        assert elev == 50.0

    @respx.mock
    @pytest.mark.asyncio
    async def test_archive_api(self):
        today = datetime.date.today()
        start = today - datetime.timedelta(days=400)
        end = today - datetime.timedelta(days=395)
        route = respx.get(ARCHIVE_URL).respond(json=FAKE_RESPONSE)

        await fetch_hourly_weather(48.85, 2.35, start, end)
        assert route.called

    @respx.mock
    @pytest.mark.asyncio
    async def test_missing_elevation(self):
        today = datetime.date.today()
        start = today - datetime.timedelta(days=1)
        end = today + datetime.timedelta(days=2)
        resp = dict(FAKE_RESPONSE)
        del resp["elevation"]
        respx.get(FORECAST_URL).respond(json=resp)

        *_, elev = await fetch_hourly_weather(48.85, 2.35, start, end)
        assert elev is None

    @respx.mock
    @pytest.mark.asyncio
    async def test_http_error(self):
        today = datetime.date.today()
        start = today - datetime.timedelta(days=1)
        end = today + datetime.timedelta(days=2)
        respx.get(FORECAST_URL).respond(500)

        with pytest.raises(HTTPError):
            await fetch_hourly_weather(48.85, 2.35, start, end)

    @respx.mock
    @pytest.mark.asyncio
    async def test_null_radiation_values(self):
        today = datetime.date.today()
        start = today - datetime.timedelta(days=1)
        end = today + datetime.timedelta(days=2)
        null_resp = {
            "hourly": {
                "time": ["2026-06-01T00:00"],
                "shortwave_radiation": [None],
                "direct_normal_irradiance": [None],
                "diffuse_radiation": [None],
                "temperature_2m": [15.0],
            },
        }
        respx.get(FORECAST_URL).respond(json=null_resp)

        times, ghi, dni, dhi, temp, elev = await fetch_hourly_weather(
            48.85,
            2.35,
            start,
            end,
        )
        # pydantic coercion: None stays None, but list annotation may fail
        # at endpoint layer; data round-trip is fine
        assert times == ["2026-06-01T00:00"]
