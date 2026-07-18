import datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from solarpanels.client import fetch_hourly_weather
from solarpanels.models import (
    DailyEstimate,
    EstimateRequest,
    EstimateResponse,
    LocationInfo,
    PanelParameters,
)
from solarpanels.solar import compute_daily_estimates, compute_ev_miles, compute_payback

app = FastAPI(title="Solarpanels Energy Estimator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/estimate")
async def estimate(req: EstimateRequest) -> EstimateResponse:
    if req.end_date < req.start_date:
        raise HTTPException(400, "end_date must be after start_date")

    azimuth: float | str | None = req.azimuth
    if req.tracking == "vertical":
        azimuth = None

    try:
        times, ghi, dni, dhi, temp_air, elevation = await fetch_hourly_weather(
            req.latitude,
            req.longitude,
            req.start_date,
            req.end_date,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    except Exception as exc:
        raise HTTPException(502, f"Open-Meteo request failed: {exc}")

    try:
        daily_rows, tou_result = compute_daily_estimates(
            times,
            ghi,
            dni,
            dhi,
            temp_air,
            req.latitude,
            req.longitude,
            elevation,
            req.panel_area_m2,
            req.efficiency,
            req.system_losses,
            req.tracking,
            req.tilt,
            azimuth if req.tracking == "fixed" else None,
            shading_summer_start=req.shading_summer_start,
            shading_summer_end=req.shading_summer_end,
            shading_winter_start=req.shading_winter_start,
            shading_winter_end=req.shading_winter_end,
            tou_blocks=[b.model_dump() for b in req.tou_blocks] if req.tou_blocks else None,
            flat_rate=req.price_per_kwh,
        )
    except Exception as exc:
        raise HTTPException(500, f"Calculation failed: {exc}")

    daily: list[DailyEstimate] = []
    for r in daily_rows:
        d = r["date"]
        if isinstance(d, datetime.date):
            d = d.isoformat()
        daily.append(
            DailyEstimate(
                date=datetime.date.fromisoformat(d),
                radiation_mj_m2=r["radiation_mj_m2"],
                energy_kwh=r["energy_kwh"],
            )
        )

    total = round(sum(d.energy_kwh for d in daily), 2)

    ev_miles, ev_profile_used, ev_km = compute_ev_miles(
        total, req.ev_profile, req.ev_consumption
    )

    days_in_range = (req.end_date - req.start_date).days + 1
    annual_kwh = total / days_in_range * 365 if days_in_range > 0 else 0
    payback_years, payback_months, cash_flow, cash_flow_table = compute_payback(
        annual_kwh,
        req.price_per_kwh,
        req.system_cost,
        req.annual_maintenance,
        req.inflation_rate,
        req.monthly_spend,
    )

    flat_savings = tou_result[0] if tou_result else None
    tou_savings = tou_result[1] if tou_result else None
    tou_breakdown = tou_result[2] if tou_result else None

    return EstimateResponse(
        total_energy_kwh=total,
        daily_estimates=daily,
        panel_parameters=PanelParameters(
            area_m2=req.panel_area_m2,
            efficiency=req.efficiency,
            system_losses=req.system_losses,
            tracking=req.tracking,
            tilt=req.tilt,
            azimuth=req.azimuth,
        ),
        location=LocationInfo(
            latitude=req.latitude,
            longitude=req.longitude,
            elevation=elevation,
        ),
        ev_miles=ev_miles,
        ev_km=ev_km,
        ev_profile_used=ev_profile_used,
        payback_years=payback_years,
        payback_months=payback_months,
        cash_flow=cash_flow,
        cash_flow_table=cash_flow_table,
        bill_coverage_pct=cash_flow_table[0]["bill_covered_pct"] if cash_flow_table else None,
        flat_savings=flat_savings,
        tou_savings=tou_savings,
        tou_breakdown=tou_breakdown,
    )


@app.get("/health")
async def health():
    return {"status": "ok"}
