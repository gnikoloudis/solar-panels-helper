"""Back-to-back comparison against NREL PVWatts V8 API.

Requires network access and a valid API key.
Skipped automatically when the API is unreachable.

NOTE: PVWatts uses NSRDB TMY weather data internally, while we fetch
real Open-Meteo data.  Differences in weather → differences in output,
so tolerances here are intentionally wide (~50 %)."""

import datetime

import httpx
import pytest

from solarpanels.client import fetch_hourly_weather
from solarpanels.solar import compute_daily_estimates

API_KEY = "xb0lrsluAwb70GDsEcELsMangLvQmFmsHe1nPbF6"
PVWATTS_URL = "https://developer.nrel.gov/api/pvwatts/v8.json"

# Use PVWatts defaults where possible
LAT, LON = 40.0, -105.0
AREA, EFF = 1.6, 0.20  # → pdc0 = 320 W
TILT, AZ = 35.0, 180.0


def _pvwatts_params(system_losses: float):
    return {
        "api_key": API_KEY,
        "lat": LAT,
        "lon": LON,
        "system_capacity": AREA * 1000 * EFF,
        "module_type": 0,
        "array_type": 0,
        "tilt": TILT,
        "azimuth": AZ,
        "losses": int(system_losses * 100),
        "dataset": "nsrdb",
    }


@pytest.fixture(scope="module")
def pvwatts_outputs():
    params = _pvwatts_params(0.14)
    try:
        r = httpx.get(PVWATTS_URL, params=params, timeout=60)
        r.raise_for_status()
        return r.json()["outputs"]
    except (httpx.HTTPError, OSError):
        pytest.skip("NREL PVWatts API unreachable")


class TestNrelPvwatts:
    @pytest.mark.asyncio
    async def test_annual_ac_same_order_of_magnitude(self, pvwatts_outputs):
        today = datetime.date.today()
        start = today - datetime.timedelta(days=365)
        try:
            times, ghi, dni, dhi, temp, _ = await fetch_hourly_weather(
                LAT,
                LON,
                start,
                today,
            )
        except Exception:
            pytest.skip("Open-Meteo unreachable")

        daily, _ = compute_daily_estimates(
            times,
            ghi,
            dni,
            dhi,
            temp,
            latitude=LAT,
            longitude=LON,
            elevation=0,
            panel_area_m2=AREA,
            efficiency=EFF,
            system_losses=0.14,
            tracking="fixed",
            tilt=TILT,
            azimuth=AZ,
        )
        ours = sum(d["energy_kwh"] for d in daily)
        ref = pvwatts_outputs["ac_annual"]
        ratio = ours / ref if ref else 0
        assert 0.5 < ratio < 1.5, (
            f"Our annual {ours:.1f} kWh vs PVWatts {ref:.1f} kWh (ratio={ratio:.2f})"
        )

    def test_poa_monthly_same_magnitude(self, pvwatts_outputs):
        """POA monthly from PVWatts should be in a similar ballpark."""
        for i, poa_ref in enumerate(pvwatts_outputs["poa_monthly"], 1):
            assert 0 < poa_ref < 300, f"Month {i} POA {poa_ref:.1f} kWh/m² implausible"

    def test_capacity_factor_plausible(self, pvwatts_outputs):
        """PVWatts capacity factor at this location should be 10-30%."""
        cf = pvwatts_outputs["capacity_factor"]
        assert 10 < cf < 30, f"Capacity factor {cf:.1f}% outside expected range"
