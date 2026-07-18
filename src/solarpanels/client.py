import datetime

from httpx import AsyncClient

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

_HOURLY_PARAMS = "shortwave_radiation,direct_normal_irradiance,diffuse_radiation,temperature_2m"


def _pick_api(start: datetime.date, end: datetime.date) -> str:
    today = datetime.date.today()
    days_ago = (today - start).days
    days_ahead = (end - today).days
    if days_ago <= 92 and days_ahead <= 16:
        return FORECAST_URL
    if end <= today:
        return ARCHIVE_URL
    raise ValueError(
        f"Date range [{start}, {end}] out of supported bounds: max 92 days past, max 16 days future"
    )


async def fetch_hourly_weather(
    latitude: float,
    longitude: float,
    start_date: datetime.date,
    end_date: datetime.date,
) -> tuple[list[str], list[float], list[float], list[float], list[float], float | None]:
    url = _pick_api(start_date, end_date)
    params: dict[str, str | int | float] = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": _HOURLY_PARAMS,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "timezone": "UTC",
    }

    async with AsyncClient(timeout=30) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()

    hourly = data["hourly"]
    times: list[str] = hourly["time"]
    ghi: list[float] = hourly["shortwave_radiation"]
    dni: list[float] = hourly["direct_normal_irradiance"]
    dhi: list[float] = hourly["diffuse_radiation"]
    temp: list[float] = hourly["temperature_2m"]
    elevation: float | None = data.get("elevation")
    return times, ghi, dni, dhi, temp, elevation
