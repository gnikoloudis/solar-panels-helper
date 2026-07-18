# Solar Energy Estimator

A full-stack web application that estimates solar panel energy output using real weather data, with EV integration, financial payback analysis, time-of-use rate simulation, and seasonal shading.

**[View full application overview →](docs/application_overview.md)**

---

## Quick Start

### Prerequisites
- Python 3.12+
- Node.js 20+
- `uv` package manager (`pip install uv`)

### Backend

```bash
uv sync
uv run uvicorn solarpanels.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 in your browser.

---

## Features

| Feature | Description |
|---|---|
| **Location** | Click any point on an interactive Leaflet map |
| **Date range** | Past or future dates — auto-selects Open-Meteo forecast/archive |
| **Panel config** | Fixed, vertical (E-W), or dual-axis tracking |
| **Seasonal shading** | Summer/winter time windows with interpolation |
| **EV estimation** | Miles/km per year from solar production (sedan, SUV, truck, custom) |
| **TOU rates** | Compare flat vs time-of-use pricing with custom blocks |
| **Payback analysis** | 25-year cash flow, monthly table, bill coverage, Excel export |
| **Data source** | Open-Meteo (free, no API key) — GHI, DNI, DHI, temperature |
| **PV engine** | pvlib — Perez transposition, NOCT cell temp, PVWatts DC/inverter |

---

## Tech Stack

| Layer | Stack |
|---|---|
| Frontend | React 19 + TypeScript, Vite, Leaflet, Chart.js, SheetJS |
| Backend | Python 3.12+, FastAPI, Pydantic V2, pvlib |
| Package mgmt | uv, npm |
| Lint/type | ruff, pyright, TypeScript |

---

## Project Structure

```
solarpanels/
├── src/solarpanels/
│   ├── main.py          # FastAPI app — POST /api/estimate
│   ├── solar.py          # PV engine, payback, EV, TOU, shading
│   ├── client.py         # Open-Meteo HTTP client
│   └── models.py         # Pydantic request/response schemas
├── frontend/
│   └── src/
│       ├── App.tsx        # State management + API orchestration
│       ├── components/
│       │   ├── Form.tsx          # User inputs + validation
│       │   ├── Results.tsx       # Tables, downloads, charts
│       │   ├── EnergyChart.tsx   # Daily energy bar chart
│       │   ├── CashFlowChart.tsx # Payback line chart
│       │   ├── TouChart.tsx      # TOU comparison chart
│       │   └── MapPicker.tsx     # Leaflet location picker
│       └── index.css
├── tests/
├── docs/
│   └── application_overview.md  # Architecture + diagrams
└── start.ps1 / start.py         # Dev launcher scripts
```

---

## API

### `POST /api/estimate`

Request body includes location, date range, panel config, and optional features (EV, TOU, payback, shading). Returns daily energy estimates, financial analysis, and TOU breakdown.

See [models.py](src/solarpanels/models.py) for the full schema.

### `GET /health`

Returns `{"status": "ok"}`.
