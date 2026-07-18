import { useState } from "react";
import * as XLSX from "xlsx";
import CashFlowChart from "./CashFlowChart";
import TouChart from "./TouChart";

function downloadExcel(data: Record<string, unknown>[], filename: string) {
  const wb = XLSX.utils.book_new();
  const ws = XLSX.utils.json_to_sheet(data);
  XLSX.utils.book_append_sheet(wb, ws, "Sheet1");
  XLSX.writeFile(wb, filename);
}

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

interface Props {
  result: Result | null;
  price_per_kwh?: number;
}

export default function Results({ result, price_per_kwh = 0.12 }: Props) {
  const [showTable, setShowTable] = useState(true);
  const [showCashFlow, setShowCashFlow] = useState(false);
  if (!result) return null;

  const savings = price_per_kwh > 0 ? (result.total_energy_kwh * price_per_kwh).toFixed(2) : null;

  return (
    <div className="results">
      <div className="total-card">
        <span className="total-label">Total Energy</span>
        <span className="total-value">{result.total_energy_kwh} <small>kWh</small></span>
        {savings && <div className="total-savings">≈ €{savings} at €{price_per_kwh}/kWh</div>}
        {result.ev_miles != null && (
          <div className="total-ev">
            Your solar array can power your EV for <strong>{result.ev_miles.toLocaleString()} miles</strong>
            {result.ev_km != null && <span> ({result.ev_km.toLocaleString()} km)</span>} per year
            {result.ev_profile_used && result.ev_profile_used !== "custom" && <span> · {result.ev_profile_used}</span>}
          </div>
        )}
        {result.payback_years != null && (
          <div className="payback-badge">
            Payback period: <strong>{result.payback_years} years{result.payback_months ? `, ${result.payback_months} months` : ""}</strong>
          </div>
        )}
      </div>

      {result.cash_flow && <CashFlowChart cashFlow={result.cash_flow} breakEvenYear={result.payback_years} />}
      {result.tou_breakdown && result.flat_savings != null && result.tou_savings != null && (
        <TouChart breakdown={result.tou_breakdown} flatSavings={result.flat_savings} touSavings={result.tou_savings} />
      )}

      {result.bill_coverage_pct != null && (
        <div className="total-card" style={{ marginTop: "0.5rem" }}>
          <span className="total-label">Year-1 bill coverage</span>
          <span className="total-value">{result.bill_coverage_pct}%</span>
        </div>
      )}

      {result.cash_flow_table && (
        <>
          <div className="table-toggle" style={{ marginTop: "0.5rem" }}>
            <button className="group-btn" onClick={() => setShowCashFlow((s) => !s)}>
              {showCashFlow ? "Hide" : "Show"} cash flow table
            </button>
            <button className="group-btn" onClick={() => downloadExcel(
              result.cash_flow_table!.map((r) => ({
                Month: r.month,
                Year: r.year_label,
                "Savings (€)": r.savings,
                "Maint. (€)": r.maintenance,
                "Net (€)": r.net,
                "Cumulative (€)": r.cumulative,
                ...(r.bill_covered_pct != null ? { "Bill covered": `${r.bill_covered_pct}%`, "Remaining bill (€)": r.remaining_bill } : {}),
              })),
              "cash_flow.xlsx",
            )}>Download Excel</button>
          </div>
          {showCashFlow && (
            <div style={{ maxHeight: "400px", overflowY: "auto" }}>
              <table>
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Year</th>
                    <th>Savings (€)</th>
                    <th>Maint. (€)</th>
                    <th>Net (€)</th>
                    <th>Cumulative (€)</th>
                    {result.cash_flow_table[0].bill_covered_pct != null && <th>Bill covered</th>}
                    {result.cash_flow_table[0].remaining_bill != null && <th>Remaining bill (€)</th>}
                  </tr>
                </thead>
                <tbody>
                  {result.cash_flow_table.map((r) => (
                    <tr key={r.month}>
                      <td>{r.month}</td>
                      <td>{r.year_label}</td>
                      <td>{r.savings.toFixed(2)}</td>
                      <td>{r.maintenance.toFixed(2)}</td>
                      <td>{r.net.toFixed(2)}</td>
                      <td style={{ color: r.cumulative >= 0 ? "var(--accent)" : undefined }}>{r.cumulative.toFixed(2)}</td>
                      {r.bill_covered_pct != null && <td>{r.bill_covered_pct}%</td>}
                      {r.remaining_bill != null && <td>{r.remaining_bill.toFixed(2)}</td>}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}

      <div className="meta-grid">
        <div>
          <span className="meta-label">Location</span>
          <span className="meta-value">{result.location.latitude}°, {result.location.longitude}°{result.location.elevation != null ? ` · ${result.location.elevation}m` : ""}</span>
        </div>
        <div>
          <span className="meta-label">Panel</span>
          <span className="meta-value">{result.panel_parameters.area_m2} m² · {result.panel_parameters.efficiency * 100}% eff · {result.panel_parameters.system_losses * 100}% loss · {result.panel_parameters.tracking}{result.panel_parameters.tilt != null && result.panel_parameters.tracking === "fixed" ? ` · tilt ${result.panel_parameters.tilt}°` : ""}{result.panel_parameters.azimuth != null && result.panel_parameters.tracking === "fixed" ? ` · azimuth ${result.panel_parameters.azimuth}°` : ""}</span>
        </div>
      </div>

      <div className="table-toggle">
        <button className="group-btn" onClick={() => setShowTable((s) => !s)}>
          {showTable ? "Hide" : "Show"} daily table
        </button>
        <button className="group-btn" onClick={() => downloadExcel(
          result.daily_estimates.map((d) => ({ Date: d.date, "Radiation (MJ/m²)": d.radiation_mj_m2, "Energy (kWh)": d.energy_kwh })),
          "daily_estimates.xlsx",
        )}>Download Excel</button>
      </div>

      {showTable && (
        <table>
          <thead>
            <tr>
              <th>Date</th>
              <th>Radiation (MJ/m²)</th>
              <th>Energy (kWh)</th>
            </tr>
          </thead>
          <tbody>
            {result.daily_estimates.map((d) => (
              <tr key={d.date}>
                <td>{d.date}</td>
                <td>{d.radiation_mj_m2}</td>
                <td>{d.energy_kwh}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
