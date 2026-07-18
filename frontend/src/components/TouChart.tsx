import { Chart } from "react-chartjs-2";
import type { ChartData } from "chart.js";

interface TouBlockDisplay {
  label: string;
  kwh: number;
  rate: number;
  savings: number;
}

interface Props {
  breakdown: TouBlockDisplay[];
  flatSavings: number;
  touSavings: number;
}

export default function TouChart({ breakdown, flatSavings, touSavings }: Props) {
  const labels = breakdown.map((b) => b.label);
  const kwhData = breakdown.map((b) => b.kwh);
  const savingsData = breakdown.map((b) => b.savings);

  const chartData: ChartData<"bar"> = {
    labels,
    datasets: [
      {
        type: "bar" as const,
        label: "Energy (kWh)",
        data: kwhData,
        backgroundColor: "#f59e0b",
        borderRadius: 4,
        order: 2,
        yAxisID: "y",
      },
      {
        type: "bar" as const,
        label: "Savings (€)",
        data: savingsData,
        backgroundColor: "#22d3ee",
        borderRadius: 4,
        order: 1,
        yAxisID: "y1",
      },
    ],
  };

  return (
    <div className="chart-section">
      <div className="chart-header">
        <h3>TOU Breakdown</h3>
        <div className="tou-summary">
          <span>Flat: €{flatSavings.toFixed(2)}</span>
          <span>TOU: <strong>€{touSavings.toFixed(2)}</strong></span>
          <span className={touSavings >= flatSavings ? "positive" : "negative"}>
            {touSavings >= flatSavings ? "+" : ""}€{(touSavings - flatSavings).toFixed(2)}
          </span>
        </div>
      </div>
      <div className="chart-container">
        <Chart
          type="bar"
          data={chartData}
          options={{
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
              legend: {
                display: true,
                position: "top",
                align: "end",
                labels: { color: "#94a3b8", boxWidth: 14, boxHeight: 2, font: { size: 11 } },
              },
              tooltip: {
                callbacks: {
                  label: (ctx) => {
                    if (ctx.dataset.label?.startsWith("Energy")) return `${ctx.parsed.y.toFixed(2)} kWh`;
                    return `€${ctx.parsed.y.toFixed(2)}`;
                  },
                },
              },
            },
            scales: {
              x: { ticks: { color: "#94a3b8", maxRotation: 45 }, grid: { display: false } },
              y: {
                type: "linear",
                display: true,
                position: "left",
                ticks: { color: "#94a3b8" },
                grid: { color: "#334155" },
                title: { display: true, text: "kWh", color: "#94a3b8" },
              },
              y1: {
                type: "linear",
                display: true,
                position: "right",
                ticks: { color: "#94a3b8" },
                grid: { display: false },
                title: { display: true, text: "€", color: "#94a3b8" },
              },
            },
          }}
        />
      </div>
    </div>
  );
}
