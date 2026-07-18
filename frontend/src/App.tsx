import { useState, useCallback } from "react";
import Form, { type FormData, type TouBlock } from "./components/Form";
import MapPicker from "./components/MapPicker";
import Results from "./components/Results";
import EnergyChart from "./components/EnergyChart";

interface DailyRow {
  date: string;
  radiation_mj_m2: number;
  energy_kwh: number;
}

interface Result {
  total_energy_kwh: number;
  daily_estimates: DailyRow[];
  panel_parameters: {
    area_m2: number;
    efficiency: number;
    system_losses: number;
    tracking: string;
    tilt: number | null;
    azimuth: number | null;
  };
  location: {
    latitude: number;
    longitude: number;
    elevation: number | null;
  };
  ev_miles: number | null;
  ev_km: number | null;
  ev_profile_used: string | null;
  payback_years: number | null;
  payback_months: number | null;
  cash_flow: number[] | null;
  cash_flow_table: { month: number; year_label: string; savings: number; maintenance: number; net: number; cumulative: number; bill_covered_pct: number | null; remaining_bill: number | null }[] | null;
  bill_coverage_pct: number | null;
  flat_savings: number | null;
  tou_savings: number | null;
  tou_breakdown: { label: string; kwh: number; rate: number; savings: number }[] | null;
}

type Nullable<T> = T | null;

const orNull = (v: string): number | null => {
  const n = parseFloat(v);
  return isNaN(n) ? null : n;
};

const orNullInt = (v: string): number | null => {
  const n = parseInt(v, 10);
  return isNaN(n) ? null : n;
};

export default function App() {
  const [lat, setLat] = useState(48.8566);
  const [lng, setLng] = useState(2.3522);
  const [result, setResult] = useState<Nullable<Result>>(null);
  const [error, setError] = useState<Nullable<string>>(null);
  const [loading, setLoading] = useState(false);
  const [pricePerKwh, setPricePerKwh] = useState(0.12);

  const handleMapChange = useCallback((newLat: number, newLng: number) => {
    setLat(newLat);
    setLng(newLng);
  }, []);

  const handleSubmit = async (data: FormData) => {
    setLoading(true);
    setError(null);
    setResult(null);

    const consumption = orNull(data.ev_consumption);
    const ev_consumption_val =
      consumption && data.ev_consumption_unit === "kwh_per_100km"
        ? 62.14 / consumption
        : consumption;

    const body = {
      latitude: lat,
      longitude: lng,
      start_date: data.start_date,
      end_date: data.end_date,
      panel_area_m2: parseFloat(data.panel_area_m2) || 1.6,
      efficiency: parseFloat(data.efficiency) || 0.2,
      system_losses: parseFloat(data.system_losses) || 0.14,
      tracking: data.tracking,
      tilt: orNull(data.tilt),
      azimuth: orNull(data.azimuth),
      ev_profile: data.ev_profile || null,
      ev_consumption: ev_consumption_val,
      price_per_kwh: parseFloat(data.price_per_kwh) || 0.12,
      system_cost: orNull(data.system_cost),
      annual_maintenance: orNull(data.annual_maintenance),
      inflation_rate: parseFloat(data.inflation_rate) || 0.025,
      monthly_spend: orNull(data.monthly_spend),
      shading_summer_start: orNullInt(data.shading_summer_start),
      shading_summer_end: orNullInt(data.shading_summer_end),
      shading_winter_start: orNullInt(data.shading_winter_start),
      shading_winter_end: orNullInt(data.shading_winter_end),
      tou_blocks: data.tou_mode === "tou" ? (JSON.parse(data.tou_blocks_json || "[]") as TouBlock[]) : [],
    };
    console.log("[Solarpanels] Submitting request:", JSON.stringify(body, null, 2));
    setPricePerKwh(parseFloat(data.price_per_kwh) || 0.12);

    try {
      const res = await fetch("/api/estimate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      console.log("[Solarpanels] Response status:", res.status, res.statusText);
      if (!res.ok) {
        const text = await res.text();
        console.log("[Solarpanels] Error body:", text);
        let detail = res.statusText;
        try {
          detail = JSON.parse(text).detail ?? detail;
        } catch {
          if (text) detail = text;
        }
        console.log("[Solarpanels] Extracted detail:", detail);
        throw new Error(detail);
      }
      const json: Result = await res.json();
      console.log("[Solarpanels] Success result:", json);
      setResult(json);
    } catch (e) {
      console.log("[Solarpanels] Catch block, error:", e);
      const msg = e instanceof Error ? e.message : "Unknown error";
      console.log("[Solarpanels] Setting error:", msg);
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <header className="app-header">
        <h1>Solar Energy Estimator</h1>
        <p>Click the map to pick a location, then set your date range and optional features below</p>
      </header>

      <details className="guide">
        <summary>How to use this tool</summary>
        <ol>
          <li><strong>Pick a location</strong> — click anywhere on the map or drag the marker</li>
          <li><strong>Set a date range</strong> — choose start and end dates (past or future)</li>
          <li><strong>Configure panels</strong> — area, efficiency, tracking mode, tilt, and azimuth (optional, defaults work well)</li>
          <li><strong>Optional extras</strong> — expand the sections below to add shading, EV charging, payback analysis, or time-of-use rates</li>
          <li><strong>Click Estimate</strong> — view daily energy, charts, and optional financial results</li>
        </ol>
      </details>

      <div className="map-wrapper">
        <MapPicker lat={lat} lng={lng} onChange={handleMapChange} />
      </div>

      <Form lat={lat} lng={lng} onSubmit={handleSubmit} loading={loading} />

      {error && <p className="error">{error}</p>}

      {result && <EnergyChart data={result.daily_estimates} />}
      <Results result={result} price_per_kwh={pricePerKwh} />
    </>
  );
}
