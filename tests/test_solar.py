import datetime

import numpy as np
import pandas as pd
import pytest
from pvlib.atmosphere import get_relative_airmass
from pvlib.inverter import pvwatts as pvwatts_inverter
from pvlib.irradiance import get_extra_radiation, get_total_irradiance
from pvlib.location import Location
from pvlib.pvsystem import pvwatts_dc

from solarpanels.models import EstimateRequest
from solarpanels.solar import _cell_temperature, compute_daily_estimates, compute_ev_miles, compute_payback


def _parse_ts(s: str) -> datetime.datetime:
    return datetime.datetime.fromisoformat(s).replace(tzinfo=datetime.UTC)


def _cell_temp_ref(poa, t_air, eff=0.20):
    return t_air + (45.0 - 20.0) * poa / 800 * (1 - eff / 0.9)


# ── Reference values from pvlib test suite ──────────────────────────

REF_PVWATTS_DC = [
    pytest.param(900, 30, 100, -0.003, 88.65, id="pvlib-test-scalar"),
    pytest.param(1000, 30, 5000, -0.004, 4900.0, id="pvlib-doc-pvsystem"),
    pytest.param(1000, 25, 5000, -0.004, 5000.0, id="stc-no-temp-loss"),
    pytest.param(200, 25, 5000, -0.004, 1000.0, id="low-irradiance"),
    pytest.param(100, 30, 100, -0.003, 9.85, id="low-irradiance-no-k"),
    pytest.param(100, 30, 100, -0.003, 8.9125, id="with-k-factor"),
]

_800 = np.array([800.0])
_1000 = np.array([1000.0])
_20 = np.array([20.0])
_25 = np.array([25.0])
_3944 = np.array([39.44444444444444])
_4931 = np.array([49.30555555555556])

REF_CELL_TEMP = [
    pytest.param(_800, _20, _3944, id="noct-baseline"),
    pytest.param(_1000, _25, _4931, id="stc+noon"),
]


# ── Test: pvwatts_dc with upstream reference values ────────────────


class TestPvwattsDcReference:
    @pytest.mark.parametrize(
        "poa,tcell,pdc0,gamma_pdc,expected",
        [r for r in REF_PVWATTS_DC if r.id != "with-k-factor"],
    )
    def test_scalar(self, poa, tcell, pdc0, gamma_pdc, expected):
        result = pvwatts_dc(poa, tcell, pdc0, gamma_pdc=gamma_pdc)
        assert result == pytest.approx(expected, rel=1e-4)

    def test_with_k_factor(self):
        result = pvwatts_dc(100, 30, 100, gamma_pdc=-0.003, k=0.01)
        assert result == pytest.approx(8.9125, rel=1e-4)


# ── Test: cell temperature model ────────────────────────────────────


class TestCellTemperature:
    @pytest.mark.parametrize("poa,temp_air,expected", REF_CELL_TEMP)
    def test_known_values(self, poa, temp_air, expected):
        result = _cell_temperature(poa, temp_air)
        np.testing.assert_allclose(result, expected, rtol=1e-10)

    def test_zero_poa(self):
        result = _cell_temperature(np.array([0.0]), np.array([10.0]))
        assert result[0] == pytest.approx(10.0)

    def test_array_broadcast(self):
        poa = np.array([0.0, 400.0, 800.0, 1000.0])
        air = np.array([20.0, 25.0, 30.0, 35.0])
        expected = _cell_temp_ref(poa, air)
        np.testing.assert_allclose(_cell_temperature(poa, air), expected, rtol=1e-10)

    def test_panel_area_scales(self):
        lat, lon = 48.85, 2.35
        times = [f"2026-06-01T{i:02d}:00" for i in range(10, 15)]
        ghi = [700.0, 800.0, 820.0, 780.0, 680.0]
        dni = [850.0, 900.0, 920.0, 900.0, 850.0]
        dhi = [160.0, 180.0, 190.0, 190.0, 170.0]
        temp = [30.0] * 5
        daily_a, _ = compute_daily_estimates(
            times,
            ghi,
            dni,
            dhi,
            temp,
            latitude=lat,
            longitude=lon,
            elevation=50.0,
            panel_area_m2=1.0,
            efficiency=0.20,
            system_losses=0.14,
            tracking="fixed",
            tilt=35.0,
            azimuth=180.0,
        )
        daily_b, _ = compute_daily_estimates(
            times,
            ghi,
            dni,
            dhi,
            temp,
            latitude=lat,
            longitude=lon,
            elevation=50.0,
            panel_area_m2=2.0,
            efficiency=0.20,
            system_losses=0.14,
            tracking="fixed",
            tilt=35.0,
            azimuth=180.0,
        )
        ratio = daily_b[0]["energy_kwh"] / daily_a[0]["energy_kwh"]
        assert ratio == pytest.approx(2.0, rel=1e-4)


# ── Test: full pipeline vs independent pvlib computation ────────────


class TestFullPipelineReference:
    def test_matches_independent_calculation(self):
        times = [
            "2026-06-01T05:00",
            "2026-06-01T06:00",
            "2026-06-01T07:00",
            "2026-06-01T08:00",
            "2026-06-01T09:00",
            "2026-06-01T10:00",
            "2026-06-01T11:00",
            "2026-06-01T12:00",
            "2026-06-01T13:00",
            "2026-06-01T14:00",
            "2026-06-01T15:00",
            "2026-06-01T16:00",
            "2026-06-01T17:00",
            "2026-06-01T18:00",
            "2026-06-01T19:00",
        ]
        ghi = [
            0.0,
            50.0,
            200.0,
            400.0,
            600.0,
            750.0,
            800.0,
            820.0,
            780.0,
            680.0,
            520.0,
            320.0,
            150.0,
            40.0,
            0.0,
        ]
        dni = [
            0.0,
            100.0,
            400.0,
            700.0,
            850.0,
            900.0,
            920.0,
            930.0,
            900.0,
            850.0,
            700.0,
            450.0,
            200.0,
            60.0,
            0.0,
        ]
        dhi = [
            0.0,
            30.0,
            80.0,
            120.0,
            160.0,
            180.0,
            190.0,
            200.0,
            190.0,
            170.0,
            140.0,
            100.0,
            50.0,
            20.0,
            0.0,
        ]
        temp = [15.0] * 15
        lat, lon, elev = 48.85, 2.35, 50.0
        area, eff, losses = 1.6, 0.20, 0.14
        tilt, az = 35.0, 180.0

        result, _ = compute_daily_estimates(
            times,
            ghi,
            dni,
            dhi,
            temp,
            latitude=lat,
            longitude=lon,
            elevation=elev,
            panel_area_m2=area,
            efficiency=eff,
            system_losses=losses,
            tracking="fixed",
            tilt=tilt,
            azimuth=az,
        )

        loc = Location(lat, lon, tz="UTC", altitude=elev)
        index = [_parse_ts(t) for t in times]
        pd_idx = pd.DatetimeIndex(index)
        sp = loc.get_solarposition(pd_idx)
        zen_a = np.asarray(sp["apparent_zenith"])
        az_a = np.asarray(sp["azimuth"])
        st = np.full_like(zen_a, tilt)
        sa = np.full_like(az_a, az)
        de = get_extra_radiation(pd_idx)
        am = get_relative_airmass(sp["apparent_zenith"])
        poa = get_total_irradiance(
            st,
            sa,
            sp["apparent_zenith"],
            sp["azimuth"],
            pd.Series(dni, index=pd_idx),
            pd.Series(ghi, index=pd_idx),
            pd.Series(dhi, index=pd_idx),
            dni_extra=de,
            airmass=am,
            model="perez",
        )
        pg = np.asarray(poa["poa_global"])
        tc = _cell_temp_ref(pg, np.array(temp), eff)
        pdc0 = area * 1000 * eff
        dc = pvwatts_dc(pg, tc, pdc0, gamma_pdc=-0.004)
        dc_lossy = np.asarray(dc) * (1 - losses)
        ac = np.asarray(pvwatts_inverter(dc_lossy, pdc0))
        ac = np.nan_to_num(ac, nan=0.0, posinf=0.0, neginf=0.0)

        assert len(result) == 1
        assert result[0]["energy_kwh"] == pytest.approx(np.nansum(ac) / 1000, rel=1e-4)
        assert result[0]["radiation_mj_m2"] == pytest.approx(np.nansum(pg) / 1000 * 3.6, rel=1e-4)


# ── Test: request defaults ──────────────────────────────────────────

# ── Test: physical sanity bounds ────────────────────────────────────


class TestPhysicalSanity:
    def test_energy_reasonable_for_summer_day(self):
        times = [f"2026-06-21T{i:02d}:00" for i in range(4, 21)]
        tail_gh = [700.0, 550.0, 350.0, 150.0, 0.0]
        tail_dn = [700.0, 550.0, 350.0, 200.0, 0.0]
        tail_dh = [160.0, 120.0, 80.0, 50.0, 0.0]
        ghi = [0.0] * 4 + [150.0, 350.0, 550.0, 700.0, 800.0, 850.0, 850.0, 820.0] + tail_gh * 2
        ghi = ghi[:17]
        dni = [0.0] * 4 + [300.0, 550.0, 700.0, 800.0, 850.0, 870.0, 870.0, 850.0] + tail_dn * 2
        dni = dni[:17]
        dhi = [0.0] * 4 + [80.0, 120.0, 160.0, 180.0, 190.0, 200.0, 200.0, 190.0] + tail_dh * 2
        dhi = dhi[:17]
        temp = [25.0] * 17
        daily, _ = compute_daily_estimates(
            times,
            ghi,
            dni,
            dhi,
            temp,
            latitude=48.85,
            longitude=2.35,
            elevation=50.0,
            panel_area_m2=1.6,
            efficiency=0.20,
            system_losses=0.14,
            tracking="fixed",
            tilt=35.0,
            azimuth=180.0,
        )
        assert len(daily) == 1
        assert 0.5 < daily[0]["energy_kwh"] < 10
        assert 2 < daily[0]["radiation_mj_m2"] < 50

    def test_no_energy_at_night(self):
        times = ["2026-06-21T00:00", "2026-06-21T01:00", "2026-06-21T02:00", "2026-06-21T03:00"]
        ghi = [0.0, 0.0, 0.0, 0.0]
        dni = [0.0, 0.0, 0.0, 0.0]
        dhi = [0.0, 0.0, 0.0, 0.0]
        temp = [15.0] * 4
        daily, _ = compute_daily_estimates(
            times,
            ghi,
            dni,
            dhi,
            temp,
            latitude=48.85,
            longitude=2.35,
            elevation=50.0,
            panel_area_m2=1.6,
            efficiency=0.20,
            system_losses=0.14,
            tracking="fixed",
            tilt=35.0,
            azimuth=180.0,
        )
        assert daily[0]["energy_kwh"] == 0.0
        assert daily[0]["radiation_mj_m2"] == 0.0

    def test_daily_aggregation_multiple_days(self):
        times = [f"2026-06-01T{i:02d}:00" for i in range(10, 15)] + [
            f"2026-06-02T{i:02d}:00" for i in range(10, 15)
        ]
        ghi = [700.0, 800.0, 820.0, 780.0, 680.0] * 2
        dni = [850.0, 900.0, 920.0, 900.0, 850.0] * 2
        dhi = [160.0, 180.0, 190.0, 190.0, 170.0] * 2
        temp = [30.0] * 10
        daily, _ = compute_daily_estimates(
            times,
            ghi,
            dni,
            dhi,
            temp,
            latitude=48.85,
            longitude=2.35,
            elevation=50.0,
            panel_area_m2=1.6,
            efficiency=0.20,
            system_losses=0.14,
            tracking="fixed",
            tilt=35.0,
            azimuth=180.0,
        )
        assert len(daily) == 2
        assert daily[0]["date"] == datetime.date(2026, 6, 1)
        assert daily[1]["date"] == datetime.date(2026, 6, 2)


class TestRequestDefaults:
    def test_defaults(self):
        req = EstimateRequest(
            latitude=48.85,
            longitude=2.35,
            start_date=datetime.date(2026, 6, 1),
            end_date=datetime.date(2026, 6, 7),
        )
        assert req.panel_area_m2 == 1.6
        assert req.efficiency == 0.20
        assert req.system_losses == 0.14
        assert req.tracking == "fixed"
        assert req.tilt is None
        assert req.azimuth is None


class TestEvMiles:
    def test_sedan_profile(self):
        miles, profile, km = compute_ev_miles(100, "sedan", None)
        assert miles == 400
        assert profile == "sedan"
        assert km == 644  # 400 * 1.60934 = 643.736 → rounds to 644

    def test_suv_profile(self):
        miles, profile, km = compute_ev_miles(100, "suv", None)
        assert miles == 300
        assert profile == "suv"
        assert km == 483  # 300 * 1.60934 = 482.802 → rounds to 483

    def test_truck_profile(self):
        miles, profile, km = compute_ev_miles(100, "truck", None)
        assert miles == 200
        assert profile == "truck"
        assert km == 322  # 200 * 1.60934 = 321.868 → rounds to 322

    def test_custom_consumption(self):
        miles, profile, km = compute_ev_miles(100, "custom", 3.5)
        assert miles == 350
        assert profile == "custom"
        assert km == 563

    def test_no_profile(self):
        miles, profile, km = compute_ev_miles(100, None, None)
        assert miles is None
        assert profile is None
        assert km is None

    def test_empty_profile(self):
        miles, profile, km = compute_ev_miles(100, "", None)
        assert miles is None
        assert profile is None
        assert km is None

    def test_custom_missing_consumption(self):
        miles, profile, km = compute_ev_miles(100, "custom", None)
        assert miles is None
        assert profile is None
        assert km is None

    def test_unknown_profile(self):
        miles, profile, km = compute_ev_miles(100, "hypercar", None)
        assert miles is None
        assert profile is None
        assert km is None

    def test_zero_energy(self):
        miles, profile, km = compute_ev_miles(0, "sedan", None)
        assert miles == 0
        assert profile == "sedan"
        assert km == 0

    def test_rounding(self):
        miles, _, km = compute_ev_miles(1.23456, "sedan", None)
        assert miles == 5  # 1.23456 * 4.0 = 4.93824, rounds to 5
        assert km == 8  #  5 * 1.60934 = 8.0467, rounds to 8


class TestPayback:
    def test_no_system_cost(self):
        years, months, cf, tbl = compute_payback(3000, 0.12, None, None, None)
        assert years is None
        assert months is None
        assert cf is None
        assert tbl is None

    def test_zero_system_cost(self):
        years, months, cf, tbl = compute_payback(3000, 0.12, 0, None, None)
        assert years is None
        assert months is None
        assert cf is None
        assert tbl is None

    def test_payback_basic(self):
        years, months, cf, tbl = compute_payback(3000, 0.12, 5000, 0, 0)
        # 3000 kWh * €0.12 = €360/year, €5000 / €360 ≈ 13.89 years
        assert years == 14
        assert months == 11
        assert cf is not None
        assert len(cf) == 25
        assert round(cf[-1], 0) == 4000  # €360*25 - €5000 = €4000
        assert tbl is not None
        assert len(tbl) == 300  # 25 years * 12 months
        assert tbl[0]["month"] == 1
        assert tbl[0]["year_label"] == "Year 1"
        assert tbl[0]["savings"] == 30.0  # €360 / 12
        assert tbl[0]["cumulative"] == -4970.0  # -€5000 + €30

    def test_payback_with_inflation(self):
        years, months, cf, _ = compute_payback(3000, 0.12, 5000, 0, 0.025)
        assert years == 13  # inflation speeds up payback from 14 → 13
        assert months == 1
        assert cf is not None
        assert len(cf) == 25
        assert cf[-1] > 4000  # more total savings with inflation

    def test_payback_with_maintenance(self):
        years, months, cf, _ = compute_payback(3000, 0.12, 5000, 100, 0)
        # €3000*0.12 - €100 = €260/year, €5000 / €260 ≈ 19.23 years
        assert years == 20
        assert months == 3
        assert cf is not None

    def test_payback_fast(self):
        years, months, cf, _ = compute_payback(10000, 0.30, 5000, 0, 0)
        # €3000/year, payback in ~1.67 years
        assert years == 2
        assert months == 8
        assert cf is not None

    def test_cash_flow_starts_negative(self):
        _, _, cf, _ = compute_payback(3000, 0.12, 5000, 0, 0)
        assert cf is not None
        assert cf[0] < 0  # first year still negative

    def test_cash_flow_ends_positive(self):
        _, _, cf, _ = compute_payback(3000, 0.12, 5000, 0, 0)
        assert cf is not None
        assert cf[-1] > 0  # final year positive

    def test_custom_inflation_rate(self):
        y1, _, _, _ = compute_payback(3000, 0.12, 5000, 0, 0)
        y2, _, _, _ = compute_payback(3000, 0.12, 5000, 0, 0.10)
        assert y2 is not None and y1 is not None and y2 < y1

    def test_table_with_monthly_spend(self):
        _, _, _, tbl = compute_payback(3000, 0.12, 5000, 0, 0, monthly_spend=100)
        assert tbl is not None
        assert tbl[0]["bill_covered_pct"] is not None
        assert tbl[0]["remaining_bill"] is not None
        # monthly bill = €100, monthly savings = €30, so 30% covered
        assert tbl[0]["bill_covered_pct"] == 30.0
        assert tbl[0]["remaining_bill"] == 70.0


class TestTou:
    def test_hour_in_block_normal(self):
        from solarpanels.solar import _hour_in_block
        b = {"start_hour": 16, "end_hour": 21, "rate": 0.30}
        assert _hour_in_block(16, b)
        assert _hour_in_block(20, b)
        assert not _hour_in_block(15, b)
        assert not _hour_in_block(21, b)

    def test_hour_in_block_wrap(self):
        from solarpanels.solar import _hour_in_block
        b = {"start_hour": 22, "end_hour": 6, "rate": 0.08}
        assert _hour_in_block(22, b)
        assert _hour_in_block(23, b)
        assert _hour_in_block(0, b)
        assert _hour_in_block(5, b)
        assert not _hour_in_block(6, b)
        assert not _hour_in_block(12, b)

    def test_compute_tou_breakdown(self):
        from solarpanels.solar import compute_tou_breakdown
        times = [f"2026-07-10T{h:02d}:00:00" for h in range(24)]
        # 1 kW every hour = 24 kWh total
        hourly_wh = [1000.0] * 24
        blocks = [{"start_hour": 16, "end_hour": 21, "rate": 0.30}]
        flat, tou, breakdown = compute_tou_breakdown(hourly_wh, times, blocks, 0.12)
        # Flat: 24 kWh * 0.12 = 2.88
        assert flat == 2.88
        # Peak (hours 16-20): 5 kWh * 0.30 = 1.50
        # Off-peak: 19 kWh * 0.12 = 2.28
        # TOU total: 1.50 + 2.28 = 3.78
        assert tou == 3.78
        assert len(breakdown) == 2
        assert breakdown[0]["label"] == "16:00–21:00"
        assert breakdown[0]["kwh"] == 5.0
        assert breakdown[0]["rate"] == 0.30
        assert breakdown[0]["savings"] == 1.50

    def test_compute_tou_via_pipeline(self):
        from solarpanels.solar import compute_daily_estimates
        times = [f"2026-06-15T{h:02d}:00:00" for h in range(24)]
        ghi = [0.0] * 6 + [200.0] * 6 + [500.0] * 6 + [100.0] * 6
        dni = [0.0] * 6 + [300.0] * 6 + [700.0] * 6 + [150.0] * 6
        dhi = [0.0] * 6 + [80.0] * 6 + [150.0] * 6 + [50.0] * 6
        temp = [20.0] * 24
        blocks = [{"start_hour": 10, "end_hour": 16, "rate": 0.35}]
        daily, tou_result = compute_daily_estimates(
            times, ghi, dni, dhi, temp,
            latitude=48.85, longitude=2.35, elevation=50.0,
            panel_area_m2=1.6, efficiency=0.20, system_losses=0.14,
            tracking="fixed", tilt=35.0, azimuth=180.0,
            tou_blocks=blocks, flat_rate=0.12,
        )
        assert tou_result is not None
        flat_savings, tou_savings, breakdown = tou_result
        assert flat_savings > 0
        assert tou_savings > flat_savings  # TOU should be higher with peak rate
        assert len(breakdown) >= 1


class TestShading:
    def test_shading_reduces_energy(self):
        times = [f"2026-06-15T{h:02d}:00:00" for h in range(24)]
        ghi = [0.0] * 5 + [300.0] * 14 + [0.0] * 5
        dni = [0.0] * 5 + [600.0] * 14 + [0.0] * 5
        dhi = [0.0] * 5 + [100.0] * 14 + [0.0] * 5
        temp = [20.0] * 24
        lat, lon = 48.85, 2.35
        unshaded, _ = compute_daily_estimates(
            times, ghi, dni, dhi, temp, lat, lon, 50.0,
            1.6, 0.20, 0.14, "fixed", 35.0, 180.0,
        )
        # June 15 = summer, so summer window applies: 10-17
        shaded, _ = compute_daily_estimates(
            times, ghi, dni, dhi, temp, lat, lon, 50.0,
            1.6, 0.20, 0.14, "fixed", 35.0, 180.0,
            shading_summer_start=10, shading_summer_end=17,
            shading_winter_start=10, shading_winter_end=15,
        )
        total_unshaded = sum(d["energy_kwh"] for d in unshaded)
        total_shaded = sum(d["energy_kwh"] for d in shaded)
        assert total_shaded < total_unshaded
        assert total_shaded > 0

    def test_shading_all_day_reduces_by_diffuse_only(self):
        times = [f"2026-06-15T{h:02d}:00:00" for h in range(24)]
        ghi = [0.0] * 5 + [300.0] * 14 + [0.0] * 5
        dni = [0.0] * 5 + [600.0] * 14 + [0.0] * 5
        dhi = [0.0] * 5 + [100.0] * 14 + [0.0] * 5
        temp = [20.0] * 24
        lat, lon = 48.85, 2.35
        # block everything — only diffuse should remain
        shaded, _ = compute_daily_estimates(
            times, ghi, dni, dhi, temp, lat, lon, 50.0,
            1.6, 0.20, 0.14, "fixed", 35.0, 180.0,
            shading_summer_start=0, shading_summer_end=0,
            shading_winter_start=0, shading_winter_end=0,
        )
        total = sum(d["energy_kwh"] for d in shaded)
        assert total > 0  # still some diffuse contribution

    def test_shading_seasonal_difference(self):
        # Summer day: wide window, winter day: same window (simulating tree that drops leaves)
        summer_times = [f"2026-06-15T{h:02d}:00:00" for h in range(24)]
        winter_times = [f"2026-01-15T{h:02d}:00:00" for h in range(24)]
        ghi = [50.0] * 6 + [500.0] * 12 + [50.0] * 6
        dni = [0.0] * 6 + [700.0] * 12 + [0.0] * 6
        dhi = [50.0] * 6 + [150.0] * 12 + [50.0] * 6
        temp = [25.0] * 24
        lat, lon = 48.85, 2.35
        # narrow window blocks midday for winter but not summer
        summer_result, _ = compute_daily_estimates(
            summer_times, ghi, dni, dhi, temp, lat, lon, 50.0,
            1.6, 0.20, 0.14, "fixed", 35.0, 180.0,
            shading_summer_start=6, shading_summer_end=20,
            shading_winter_start=12, shading_winter_end=13,
        )
        winter_result, _ = compute_daily_estimates(
            winter_times, ghi, dni, dhi, temp, lat, lon, 50.0,
            1.6, 0.20, 0.14, "fixed", 35.0, 180.0,
            shading_summer_start=6, shading_summer_end=20,
            shading_winter_start=12, shading_winter_end=13,
        )
        summer_energy = sum(d["energy_kwh"] for d in summer_result)
        winter_energy = sum(d["energy_kwh"] for d in winter_result)
        assert summer_energy > 0
        assert winter_energy > 0
        # Winter is heavily restricted (only hour 12 unshaded) — less than summer
        # which has almost full day unshaded with the synthetic data
        assert winter_energy < summer_energy
