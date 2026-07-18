import { type FormEvent, useState, useCallback } from "react";

export type Tracking = "fixed" | "vertical" | "dual";

export interface TouBlock {
  start_hour: number;
  end_hour: number;
  rate: number;
}

export interface FormData {
  start_date: string;
  end_date: string;
  panel_area_m2: string;
  efficiency: string;
  system_losses: string;
  tracking: Tracking;
  tilt: string;
  azimuth: string;
  price_per_kwh: string;
  ev_profile: string;
  ev_consumption: string;
  ev_consumption_unit: string;
  system_cost: string;
  annual_maintenance: string;
  inflation_rate: string;
  monthly_spend: string;
  shading_summer_start: string;
  shading_summer_end: string;
  shading_winter_start: string;
  shading_winter_end: string;
  tou_mode: string;
  tou_blocks_json: string;
}

interface Props {
  lat: number;
  lng: number;
  onSubmit: (data: FormData) => void;
  loading: boolean;
}

const DEFAULT_BLOCKS = JSON.stringify([
  { start_hour: 16, end_hour: 21, rate: 0.30 },
]);

const DEFAULTS: FormData = {
  start_date: "",
  end_date: "",
  panel_area_m2: "1.6",
  efficiency: "0.20",
  system_losses: "0.14",
  tracking: "fixed",
  tilt: "",
  azimuth: "",
  price_per_kwh: "0.12",
  ev_profile: "",
  ev_consumption: "",
  ev_consumption_unit: "miles_per_kwh",
  system_cost: "",
  annual_maintenance: "",
  inflation_rate: "0.025",
  monthly_spend: "",
  shading_summer_start: "",
  shading_summer_end: "",
  shading_winter_start: "",
  shading_winter_end: "",
  tou_mode: "flat",
  tou_blocks_json: DEFAULT_BLOCKS,
};

export default function Form({ lat, lng, onSubmit, loading }: Props) {
  const [data, setData] = useState<FormData>(DEFAULTS);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    onSubmit(data);
  };

  const set = (field: keyof FormData) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    setData((prev) => ({ ...prev, [field]: e.target.value }));

  return (
    <form onSubmit={handleSubmit}>
      <div className="coords-display">
        <span>📍 {lat.toFixed(4)}°, {lng.toFixed(4)}°</span>
      </div>

      <div className="field-row">
        <label>
          Start date
          <input type="date" value={data.start_date} onChange={set("start_date")} required />
        </label>
        <label>
          End date
          <input type="date" value={data.end_date} onChange={set("end_date")} required />
        </label>
      </div>

      <details open>
        <summary>Panel &amp; pricing <span className="badge">optional</span></summary>
        <div className="field-row">
          <label>
            Area (m²)
            <input type="number" step="any" min="0.01" value={data.panel_area_m2} onChange={set("panel_area_m2")} />
          </label>
          <label>
            Efficiency
            <input type="number" step="any" min="0" max="1" value={data.efficiency} onChange={set("efficiency")} />
          </label>
          <label>
            Losses
            <input type="number" step="any" min="0" max="1" value={data.system_losses} onChange={set("system_losses")} />
          </label>
          <label>
            Price (€/kWh)
            <input type="number" step="any" min="0" value={data.price_per_kwh} onChange={set("price_per_kwh")} />
          </label>
          <label>
            Tracking
            <select value={data.tracking} onChange={set("tracking")}>
              <option value="fixed">Fixed</option>
              <option value="vertical">Vertical tracker (E–W)</option>
              <option value="dual">Dual-axis (full tracking)</option>
            </select>
          </label>
          {data.tracking === "fixed" && (
            <>
              <label>
                Tilt (°)
                <input type="number" step="any" min="0" max="90" value={data.tilt} onChange={set("tilt")} placeholder="0" />
              </label>
              <label>
                Azimuth (°)
                <input type="number" step="any" min="0" max="360" value={data.azimuth} onChange={set("azimuth")} placeholder="0" />
              </label>
            </>
          )}
        </div>
      </details>

      <details>
        <summary>Shading <span className="badge">optional</span></summary>
        <div className="field-row">
          <label>
            Summer start hour
            <input type="number" min="0" max="23" value={data.shading_summer_start} onChange={set("shading_summer_start")} placeholder="e.g. 6" />
          </label>
          <label>
            Summer end hour
            <input type="number" min="0" max="23" value={data.shading_summer_end} onChange={set("shading_summer_end")} placeholder="e.g. 20" />
          </label>
          <label>
            Winter start hour
            <input type="number" min="0" max="23" value={data.shading_winter_start} onChange={set("shading_winter_start")} placeholder="e.g. 9" />
          </label>
          <label>
            Winter end hour
            <input type="number" min="0" max="23" value={data.shading_winter_end} onChange={set("shading_winter_end")} placeholder="e.g. 16" />
          </label>
          <p className="field-hint">Hours in local time. Shoulder months (spring/autumn) interpolate between summer and winter. Leave all blank if no shading.</p>
        </div>
      </details>

      <details>
        <summary>Time-of-Use (TOU) <span className="badge">optional</span></summary>
        <div className="field-row">
          <label>
            Pricing mode
            <select value={data.tou_mode} onChange={(e) => setData((p) => ({ ...p, tou_mode: e.target.value }))}>
              <option value="flat">Flat Rate</option>
              <option value="tou">Time-of-Use (TOU)</option>
            </select>
          </label>
        </div>
        {data.tou_mode === "tou" && <TouBlockEditor value={data.tou_blocks_json} onChange={(v) => setData((p) => ({ ...p, tou_blocks_json: v }))} />}
      </details>

      <details>
        <summary>Financial Setup <span className="badge">optional</span></summary>
        <div className="field-row">
          <label>
            System cost (€)
            <input type="number" step="any" min="0" value={data.system_cost} onChange={set("system_cost")} placeholder="e.g. 8000" />
          </label>
          <label>
            Annual maint. (€)
            <input type="number" step="any" min="0" value={data.annual_maintenance} onChange={set("annual_maintenance")} placeholder="e.g. 150" />
          </label>
            <label>
            Inflation rate
            <input type="number" step="any" min="0" max="1" value={data.inflation_rate} onChange={set("inflation_rate")} placeholder="0.025" />
          </label>
          <label>
            Monthly bill (€)
            <input type="number" step="any" min="0" value={data.monthly_spend} onChange={set("monthly_spend")} placeholder="e.g. 120" />
          </label>
        </div>
      </details>

      <details>
        <summary>EV Integration <span className="badge">optional</span></summary>
        <div className="field-row">
          <label>
            Vehicle type
            <select value={data.ev_profile} onChange={set("ev_profile")}>
              <option value="">None</option>
              <option value="sedan">Sedan (~4 mi/kWh)</option>
              <option value="suv">SUV (~3 mi/kWh)</option>
              <option value="truck">Truck (~2 mi/kWh)</option>
              <option value="custom">Custom</option>
            </select>
          </label>
          {data.ev_profile === "custom" && (
            <label>
              Consumption
              <select className="unit-select" value={data.ev_consumption_unit ?? "miles_per_kwh"} onChange={(e) => setData(p => ({ ...p, ev_consumption_unit: e.target.value }))}>
                <option value="miles_per_kwh">mi/kWh</option>
                <option value="kwh_per_100km">kWh/100km</option>
              </select>
              <input type="number" step="any" min="0.1" value={data.ev_consumption} onChange={set("ev_consumption")} placeholder="4.0" />
            </label>
          )}
        </div>
      </details>

      <button className="btn-primary" type="submit" disabled={loading}>
        {loading ? "Calculating..." : "Estimate Energy"}
      </button>
    </form>
  );
}

interface BlockEditorProps {
  value: string;
  onChange: (json: string) => void;
}

function TouBlockEditor({ value, onChange }: BlockEditorProps) {
  const blocks: TouBlock[] = JSON.parse(value || "[]");
  const update = (i: number, field: keyof TouBlock, v: number) => {
    const next = blocks.map((b, idx) => (idx === i ? { ...b, [field]: v } : b));
    onChange(JSON.stringify(next));
  };
  const add = () => onChange(JSON.stringify([...blocks, { start_hour: 0, end_hour: 6, rate: 0.08 }]));
  const remove = (i: number) => onChange(JSON.stringify(blocks.filter((_, idx) => idx !== i)));
  return (
    <div className="tou-editor">
      {blocks.map((b, i) => (
        <div key={i} className="tou-block-row">
          <label>From <input type="number" min="0" max="23" value={b.start_hour} onChange={(e) => update(i, "start_hour", +e.target.value)} /></label>
          <label>To <input type="number" min="0" max="23" value={b.end_hour} onChange={(e) => update(i, "end_hour", +e.target.value)} /></label>
          <label>€<input type="number" step="any" min="0" value={b.rate} onChange={(e) => update(i, "rate", +e.target.value)} /></label>
          <button type="button" className="btn-remove" onClick={() => remove(i)}>✕</button>
        </div>
      ))}
      <button type="button" className="btn-add" onClick={add}>+ Add block</button>
      <p className="tou-hint">Hours not covered by any block use the flat rate (€{/*placeholder*/}).</p>
    </div>
  );
}
