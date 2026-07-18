import datetime

from pydantic import BaseModel, Field


class TouBlock(BaseModel):
    start_hour: int = Field(..., ge=0, le=23)
    end_hour: int = Field(..., ge=0, le=23)
    rate: float = Field(..., ge=0)


class EstimateRequest(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    start_date: datetime.date
    end_date: datetime.date
    panel_area_m2: float = Field(default=1.6, gt=0)
    efficiency: float = Field(default=0.20, gt=0, le=1)
    system_losses: float = Field(default=0.14, ge=0, le=1)
    tracking: str = Field(default="fixed", pattern=r"^(fixed|vertical|dual)$")
    tilt: float | None = Field(default=None, ge=0, le=90)
    azimuth: float | None = Field(default=None, ge=0, le=360)
    price_per_kwh: float = Field(default=0.12, ge=0)
    ev_profile: str | None = Field(default=None, pattern=r"^(sedan|suv|truck|custom)$|^$")
    ev_consumption: float | None = Field(default=None, gt=0)
    system_cost: float | None = Field(default=None, ge=0)
    annual_maintenance: float | None = Field(default=None, ge=0)
    inflation_rate: float | None = Field(default=None, ge=0, le=1)
    monthly_spend: float | None = Field(default=None, ge=0)
    shading_summer_start: int | None = Field(default=None, ge=0, le=23)
    shading_summer_end: int | None = Field(default=None, ge=0, le=23)
    shading_winter_start: int | None = Field(default=None, ge=0, le=23)
    shading_winter_end: int | None = Field(default=None, ge=0, le=23)
    tou_blocks: list[TouBlock] = Field(default_factory=list)


class DailyEstimate(BaseModel):
    date: datetime.date
    radiation_mj_m2: float
    energy_kwh: float


class PanelParameters(BaseModel):
    area_m2: float
    efficiency: float
    system_losses: float
    tracking: str = "fixed"
    tilt: float | str | None = None
    azimuth: float | str | None = None


class LocationInfo(BaseModel):
    latitude: float
    longitude: float
    elevation: float | None = None


class EstimateResponse(BaseModel):
    total_energy_kwh: float
    daily_estimates: list[DailyEstimate]
    panel_parameters: PanelParameters
    location: LocationInfo
    ev_miles: float | None = None
    ev_km: float | None = None
    ev_profile_used: str | None = None
    payback_years: int | None = None
    payback_months: int | None = None
    cash_flow: list[float] | None = None
    cash_flow_table: list[dict] | None = None
    bill_coverage_pct: float | None = None
    flat_savings: float | None = None
    tou_savings: float | None = None
    tou_breakdown: list[dict] | None = None
