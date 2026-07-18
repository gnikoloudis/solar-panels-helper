"""Compare our simplified model against a more complete PVWatts-like
chain using pvlib's fuller model set (SAPM cell temp, inverter model).
No external API calls — all local pvlib."""

import datetime

import numpy as np
import pandas as pd
from pvlib.inverter import pvwatts as pvwatts_inverter
from pvlib.location import Location
from pvlib.pvsystem import pvwatts_dc

from solarpanels.solar import _cell_temperature, compute_daily_estimates


def _full_model_chain(
    times_iso: list[str],
    ghi: list[float],
    dni: list[float],
    dhi: list[float],
    temp_air: list[float],
    wind_speed: list[float],
    latitude: float,
    longitude: float,
    elevation: float,
    panel_area_m2: float,
    efficiency: float,
    system_losses: float,
    tilt: float,
    azimuth: float,
) -> list[dict]:
    """Replicate PVWatts more closely with SAM NOCT cell temp + inverter."""
    from pvlib.atmosphere import get_relative_airmass
    from pvlib.irradiance import get_extra_radiation, get_total_irradiance
    from pvlib.temperature import noct_sam

    loc = Location(latitude, longitude, tz="UTC", altitude=elevation)
    index = pd.DatetimeIndex([datetime.datetime.fromisoformat(t) for t in times_iso], tz="UTC")
    sp = loc.get_solarposition(index)

    st = np.full(len(index), tilt)
    sa = np.full(len(index), azimuth)

    de = get_extra_radiation(index)
    am = get_relative_airmass(sp["apparent_zenith"])
    poa = get_total_irradiance(
        st,
        sa,
        sp["apparent_zenith"],
        sp["azimuth"],
        pd.Series(dni, index=index),
        pd.Series(ghi, index=index),
        pd.Series(dhi, index=index),
        dni_extra=de,
        airmass=am,
        model="perez",
    )
    pg = np.asarray(poa["poa_global"])

    tcell = noct_sam(
        pg,
        np.array(temp_air),
        np.array(wind_speed),
        noct=45,
        module_efficiency=efficiency,
    )

    pdc0 = panel_area_m2 * 1000 * efficiency
    dc = pvwatts_dc(pg, tcell, pdc0, gamma_pdc=-0.004)
    dc_lossy = np.asarray(dc) * (1 - system_losses)
    ac = np.asarray(pvwatts_inverter(dc_lossy, pdc0))
    ac = np.nan_to_num(ac, nan=0.0, posinf=0.0, neginf=0.0)

    dates = pd.Series([ts.date() for ts in index])
    df = pd.DataFrame({"date": dates, "ac_power": ac, "poa": pg})
    daily = []
    for day_date, group in df.groupby("date"):
        total_wh = group["ac_power"].sum()
        total_poa_mj = group["poa"].sum() / 1000 * 3.6
        daily.append(
            {
                "date": day_date,
                "energy_kwh": total_wh / 1000,
                "radiation_mj_m2": total_poa_mj,
            }
        )
    return daily


JUNE_DAY = {
    "times": [f"2026-06-21T{i:02d}:00" for i in range(5, 20)],
    "ghi": [
        0.0,
        80.0,
        250.0,
        450.0,
        650.0,
        780.0,
        850.0,
        880.0,
        860.0,
        790.0,
        660.0,
        480.0,
        280.0,
        100.0,
        0.0,
    ],
    "dni": [
        0.0,
        150.0,
        450.0,
        700.0,
        850.0,
        900.0,
        920.0,
        930.0,
        910.0,
        860.0,
        750.0,
        550.0,
        300.0,
        120.0,
        0.0,
    ],
    "dhi": [
        0.0,
        40.0,
        100.0,
        150.0,
        180.0,
        190.0,
        200.0,
        200.0,
        190.0,
        170.0,
        140.0,
        100.0,
        60.0,
        20.0,
        0.0,
    ],
    "temp": [18.0] * 15,
    "wind": [2.0] * 15,
}


class TestPvwattsComparison:
    def test_simplified_vs_full_chain(self):
        d = JUNE_DAY
        lat, lon, elev = 48.85, 2.35, 50.0
        area, eff, losses = 1.6, 0.20, 0.14
        tilt, az = 35.0, 180.0

        simple, _ = compute_daily_estimates(
            d["times"],
            d["ghi"],
            d["dni"],
            d["dhi"],
            d["temp"],
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

        full = _full_model_chain(
            d["times"],
            d["ghi"],
            d["dni"],
            d["dhi"],
            d["temp"],
            d["wind"],
            latitude=lat,
            longitude=lon,
            elevation=elev,
            panel_area_m2=area,
            efficiency=eff,
            system_losses=losses,
            tilt=tilt,
            azimuth=az,
        )

        assert len(simple) == 1
        assert len(full) == 1

        ratio = simple[0]["energy_kwh"] / full[0]["energy_kwh"]
        # Both models now use efficiency-aware cell temp + inverter +
        # DC-side losses; remaining gap is wind-speed effect in SAM model (~0.1%)
        assert 0.99 < ratio < 1.01, f"energy ratio {ratio:.5f} outside [0.99, 1.01]"

    def test_cell_temp_difference(self):
        d = JUNE_DAY
        from pvlib.temperature import noct_sam

        poa = np.array(
            [
                0.0,
                100.0,
                300.0,
                500.0,
                700.0,
                800.0,
                870.0,
                900.0,
                880.0,
                800.0,
                680.0,
                500.0,
                300.0,
                120.0,
                0.0,
            ]
        )
        t_air = np.array(d["temp"])
        wind = np.array(d["wind"])

        t_simple = _cell_temperature(poa, t_air)
        t_full = noct_sam(poa, t_air, wind, noct=45, module_efficiency=0.20)

        diff = np.abs(t_simple - t_full)
        assert diff.max() < 10.0, f"max cell temp diff {diff.max():.1f}°C"

    def test_inverter_efficiency_curve(self):
        """Verify the inverter model clips at P_ac0 and has reasonable η."""
        pdc0 = 320.0
        for p_dc in [10, 50, 100, 200, 320, 400]:
            p_ac = pvwatts_inverter(np.array([p_dc]), pdc0)[0]
            eta = p_ac / p_dc if p_dc > 0 and not np.isnan(p_ac) else 0
            assert eta >= 0, f"negative η at P_dc={p_dc}"
            assert np.isnan(p_ac) or p_ac <= pdc0, f"P_ac > P_dc0 at P_dc={p_dc}"
