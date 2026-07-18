import datetime

import numpy as np
import pandas as pd
from pvlib.atmosphere import get_relative_airmass
from pvlib.inverter import pvwatts as pvwatts_inverter
from pvlib.irradiance import get_extra_radiation, get_total_irradiance
from pvlib.location import Location
from pvlib.pvsystem import pvwatts_dc
from pvlib.tracking import singleaxis

NOCT = 45.0

TouBlockDict = dict  # {"start_hour": int, "end_hour": int, "rate": float}


def _hour_in_block(hour: int, block: TouBlockDict) -> bool:
    start = block["start_hour"]
    end = block["end_hour"]
    if end > start:
        return start <= hour < end
    return hour >= start or hour < end


def compute_tou_breakdown(
    hourly_wh: list[float],
    times_iso: list[str],
    blocks: list[TouBlockDict],
    flat_rate: float,
) -> tuple[float, float, list[dict]]:
    block_wh: dict[int, float] = {i: 0.0 for i in range(len(blocks))}
    off_peak_wh = 0.0
    for i, (wh, ts) in enumerate(zip(hourly_wh, times_iso)):
        dt = datetime.datetime.fromisoformat(ts)
        h = dt.hour
        matched = False
        for bi, block in enumerate(blocks):
            if _hour_in_block(h, block):
                block_wh[bi] += wh
                matched = True
                break
        if not matched:
            off_peak_wh += wh

    total_flat = sum(hourly_wh) / 1000 * flat_rate
    breakdown: list[dict] = []
    tou_total = 0.0
    for bi, block in enumerate(blocks):
        kwh = block_wh[bi] / 1000
        savings = kwh * block["rate"]
        tou_total += savings
        breakdown.append({
            "label": f"{block['start_hour']:02d}:00–{block['end_hour']:02d}:00",
            "kwh": round(kwh, 4),
            "rate": block["rate"],
            "savings": round(savings, 2),
        })
    off_kwh = off_peak_wh / 1000
    off_savings = off_kwh * flat_rate
    if off_kwh > 0:
        tou_total += off_savings
        breakdown.append({
            "label": "Off-peak (other hours)",
            "kwh": round(off_kwh, 4),
            "rate": flat_rate,
            "savings": round(off_savings, 2),
        })
    return round(total_flat, 2), round(tou_total, 2), breakdown

EV_PROFILES: dict[str, float] = {
    "sedan": 4.0,
    "suv": 3.0,
    "truck": 2.0,
}


def compute_ev_miles(
    energy_kwh: float,
    profile: str | None,
    custom_miles_per_kwh: float | None,
) -> tuple[float | None, str | None, float | None]:
    if not profile:
        return None, None, None
    if profile == "custom":
        if not custom_miles_per_kwh:
            return None, None, None
        miles = round(energy_kwh * custom_miles_per_kwh)
        return miles, "custom", round(miles * 1.60934)
    miles_per_kwh = EV_PROFILES.get(profile)
    if miles_per_kwh is None:
        return None, None, None
    miles = round(energy_kwh * miles_per_kwh)
    return miles, profile, round(miles * 1.60934)


def compute_payback(
    annual_energy_kwh: float,
    price_per_kwh: float,
    system_cost: float | None,
    annual_maintenance: float | None,
    inflation_rate: float | None,
    monthly_spend: float | None = None,
) -> tuple[int | None, int | None, list[float] | None, list[dict] | None]:
    if not system_cost or system_cost <= 0:
        return None, None, None, None
    maint = annual_maintenance if annual_maintenance is not None else 0
    infl = inflation_rate if inflation_rate is not None else 0.025
    annual_net = annual_energy_kwh * price_per_kwh

    # --- Annual pass (payback period + chart series) ---
    cash_flow: list[float] = []
    cumulative = -system_cost
    result_years: int | None = None
    result_months: int | None = None
    for year in range(1, 26):
        savings = annual_net * (1 + infl) ** (year - 1)
        net = savings - maint
        cumulative += net
        cash_flow.append(round(cumulative, 2))
        if cumulative >= 0 and result_years is None:
            result_years = year
            prev_cumulative = cash_flow[-2] if len(cash_flow) >= 2 else -system_cost
            fraction = -prev_cumulative / net if net > 0 else 0
            result_months = round(fraction * 12)
            if result_months >= 12:
                result_years += 1
                result_months = 0

    # --- Monthly pass (detailed table) ---
    monthly_maint = maint / 12
    monthly_bill = monthly_spend or 0
    table: list[dict] = []
    cumulative = -system_cost
    for month in range(1, 301):
        year = (month - 1) // 12 + 1
        annual_savings = annual_net * (1 + infl) ** (year - 1)
        monthly_savings = annual_savings / 12
        net = monthly_savings - monthly_maint
        cumulative += net
        if monthly_bill > 0:
            bill_covered = min(monthly_savings / monthly_bill * 100, 100)
            remaining = max(monthly_bill - monthly_savings, 0)
        else:
            bill_covered = None
            remaining = None
        table.append({
            "month": month,
            "year_label": f"Year {year}",
            "savings": round(monthly_savings, 2),
            "maintenance": round(monthly_maint, 2),
            "net": round(net, 2),
            "cumulative": round(cumulative, 2),
            "bill_covered_pct": round(bill_covered, 1) if bill_covered is not None else None,
            "remaining_bill": round(remaining, 2) if remaining is not None else None,
        })
    return result_years, result_months, cash_flow, table


def _surface_orientation(
    solar_zenith: np.ndarray,
    solar_azimuth: np.ndarray,
    tracking: str,
    tilt: float | None,
    azimuth: float | None,
):
    if tracking == "fixed":
        return np.full_like(solar_zenith, tilt or 0), np.full_like(solar_azimuth, azimuth or 180)
    if tracking == "vertical":
        tracker = singleaxis(
            solar_zenith, solar_azimuth, axis_tilt=int(tilt or 0), axis_azimuth=180, max_angle=90
        )
        return np.asarray(tracker["surface_tilt"]), np.asarray(tracker["surface_azimuth"])
    tracker = singleaxis(  # type: ignore[call-overload]
        solar_zenith, solar_azimuth, axis_tilt=0, axis_azimuth=0, max_angle=90
    )
    return np.asarray(tracker["surface_tilt"]), np.asarray(tracker["surface_azimuth"])


def _cell_temperature(
    poa: np.ndarray, temp_air: np.ndarray, efficiency: float = 0.20
) -> np.ndarray:
    return temp_air + (NOCT - 20) * poa / 800 * (1 - efficiency / 0.9)


def _local_hour(ts: str, longitude: float) -> int:
    dt = datetime.datetime.fromisoformat(ts)
    offset = round(longitude / 15)
    local_dt = dt + datetime.timedelta(hours=offset)
    return local_dt.hour


def _season_factor(month: int) -> float:
    if month in (6, 7, 8):
        return 1.0
    if month in (12, 1, 2):
        return 0.0
    if month in (3, 4, 5):
        return (month - 3) / 2.0
    return (11 - month) / 2.0


def compute_daily_estimates(
    times_iso: list[str],
    ghi: list[float],
    dni: list[float],
    dhi: list[float],
    temp_air: list[float],
    latitude: float,
    longitude: float,
    elevation: float | None,
    panel_area_m2: float,
    efficiency: float,
    system_losses: float,
    tracking: str,
    tilt: float | None,
    azimuth: float | None,
    shading_summer_start: int | None = None,
    shading_summer_end: int | None = None,
    shading_winter_start: int | None = None,
    shading_winter_end: int | None = None,
    tou_blocks: list[TouBlockDict] | None = None,
    flat_rate: float = 0.12,
) -> tuple[list[dict], tuple[float, float, list[dict]] | None]:
    loc = Location(latitude, longitude, tz="UTC", altitude=elevation or 0)
    index = pd.DatetimeIndex([datetime.datetime.fromisoformat(t) for t in times_iso], tz="UTC")

    solar_pos = loc.get_solarposition(index)
    zen = np.asarray(solar_pos["apparent_zenith"])
    az = np.asarray(solar_pos["azimuth"])

    st, sa = _surface_orientation(zen, az, tracking, tilt, azimuth)

    dni_extra = get_extra_radiation(index)
    airmass = get_relative_airmass(solar_pos["apparent_zenith"])

    poa = get_total_irradiance(
        st,
        sa,
        solar_pos["apparent_zenith"],
        solar_pos["azimuth"],
        pd.Series(dni, index=index),
        pd.Series(ghi, index=index),
        pd.Series(dhi, index=index),
        dni_extra=dni_extra,
        airmass=airmass,
        model="perez",
    )

    poa_global = np.asarray(poa["poa_global"]).copy()
    if shading_summer_start is not None and shading_summer_end is not None and shading_winter_start is not None and shading_winter_end is not None:
        poa_sky = np.asarray(poa["poa_sky_diffuse"])
        poa_ground = np.asarray(poa["poa_ground_diffuse"])
        for i, ts in enumerate(times_iso):
            dt = datetime.datetime.fromisoformat(ts)
            sf = _season_factor(dt.month)
            start = round(shading_summer_start * sf + shading_winter_start * (1 - sf))
            end = round(shading_summer_end * sf + shading_winter_end * (1 - sf))
            h = _local_hour(ts, longitude)
            if not (start <= h < end):
                poa_global[i] = poa_sky[i] + poa_ground[i]
    tcell = _cell_temperature(poa_global, np.array(temp_air), efficiency)

    pdc0 = panel_area_m2 * 1000 * efficiency
    dc_power = pvwatts_dc(poa_global, tcell, pdc0, gamma_pdc=-0.004)
    dc_lossy = np.asarray(dc_power) * (1 - system_losses)
    ac_power = np.asarray(pvwatts_inverter(dc_lossy, pdc0))
    ac_power = np.nan_to_num(ac_power, nan=0.0, posinf=0.0, neginf=0.0)

    tou_result = None
    if tou_blocks:
        flat_savings, tou_savings, breakdown = compute_tou_breakdown(
            ac_power.tolist(), times_iso, tou_blocks, flat_rate
        )
        tou_result = (flat_savings, tou_savings, breakdown)

    dates = pd.Series([ts.date() for ts in index], name="date")
    df = pd.DataFrame(
        {
            "date": dates,
            "poa": poa_global,
            "ac_power": ac_power,
        }
    )

    daily = []
    for day_date, group in df.groupby("date"):
        total_wh = group["ac_power"].sum()
        total_poa_wh = group["poa"].sum()
        total_poa_mj = total_poa_wh / 1000 * 3.6
        daily.append(
            {
                "date": day_date,
                "radiation_mj_m2": round(total_poa_mj, 2),
                "energy_kwh": round(total_wh / 1000, 4),
            }
        )

    return daily, tou_result
