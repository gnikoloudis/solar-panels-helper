# [Solar Energy Calculator] (v1)

## Rule Compliance Reference
- [00_antigravity_protocol.md](.agents/rules/00_antigravity_protocol.md) — Mode C workflow
- [01_agent_planning.md](.agents/rules/01_agent_planning.md) — versioned plan, halt for approval
- [20_python_tooling.md](.agents/rules/20_python_tooling.md) — uv, ruff, ty constraints

## Overview
Full-stack web app (FastAPI + React) that calculates potential solar energy for a given coordinate and date range using the free Open-Meteo API.

**Open-Meteo data source:**
- Forecast API: `api.open-meteo.com/v1/forecast` (past 92 days to +16 days)
- Archive API: `archive-api.open-meteo.com/v1/archive` (older historical dates)
- Daily `shortwave_radiation_sum` (MJ/m²) as base solar resource
- Hourly `global_tilted_irradiance` (W/m²) when tilt/azimuth specified

**Energy formula:**
```
Daily energy (kWh) = daily_radiation (MJ/m²) × panel_area (m²) × efficiency × (1 - losses) / 3.6
```

## Files to Create

### Backend: `pyproject.toml`, `src/solarpanels/`
| File | Purpose |
|------|---------|
| `[NEW] pyproject.toml` | Project metadata, deps (FastAPI, httpx, uvicorn) |
| `[NEW] src/solarpanels/__init__.py` | Package init |
| `[NEW] src/solarpanels/main.py` | FastAPI app, CORS, single `/api/estimate` endpoint |
| `[NEW] src/solarpanels/models.py` | Pydantic v2 models for request/response |
| `[NEW] src/solarpanels/solar.py` | Core calculation: radiation → energy conversion |
| `[NEW] src/solarpanels/client.py` | httpx-based Open-Meteo API client |

### Tests: `tests/`
| File | Purpose |
|------|---------|
| `[NEW] tests/__init__.py` | Test package |
| `[NEW] tests/test_solar.py` | Unit tests for calculation logic (mock API) |

### Frontend: `frontend/`
| File | Purpose |
|------|---------|
| `[NEW] frontend/package.json` | Vite + React + TypeScript deps |
| `[NEW] frontend/vite.config.ts` | Vite config with proxy to backend |
| `[NEW] frontend/tsconfig.json` | TypeScript config |
| `[NEW] frontend/index.html` | HTML entry |
| `[NEW] frontend/src/main.tsx` | React entry |
| `[NEW] frontend/src/App.tsx` | Main app component |
| `[NEW] frontend/src/components/Form.tsx` | Input form (coords, dates, panel params) |
| `[NEW] frontend/src/components/Results.tsx` | Results display (daily table + totals) |

## API Design

### `POST /api/estimate`
**Request:**
```json
{
  "latitude": 48.8566,
  "longitude": 2.3522,
  "start_date": "2026-01-01",
  "end_date": "2026-12-31",
  "panel_area_m2": 1.6,
  "efficiency": 0.20,
  "system_losses": 0.14,
  "tilt": null,
  "azimuth": null
}
```

**Response:**
```json
{
  "total_energy_kwh": 452.3,
  "daily_estimates": [
    {"date": "2026-01-01", "radiation_mj_m2": 1.2, "energy_kwh": 0.27},
    ...
  ],
  "panel_parameters": {
    "area_m2": 1.6,
    "efficiency": 0.20,
    "system_losses": 0.14,
    "tilt": null,
    "azimuth": null
  },
  "location": {
    "latitude": 48.86,
    "longitude": 2.35
  }
}
```

## Execution Plan
1. Bootstrap backend: `pyproject.toml`, `uv sync`
2. Implement `models.py` — Pydantic schemas
3. Implement `client.py` — Open-Meteo API fetcher
4. Implement `solar.py` — energy calculation
5. Implement `main.py` — FastAPI endpoint
6. Write tests in `test_solar.py`
7. Bootstrap frontend: `package.json`, configs
8. Build `Form.tsx` and `Results.tsx`
9. Wire up `App.tsx`
10. Verify: `ruff check`, `ty check`, `pytest`, build frontend
