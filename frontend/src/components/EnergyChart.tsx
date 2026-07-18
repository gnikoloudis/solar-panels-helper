import { useMemo, useState } from "react";
import { Chart } from "react-chartjs-2";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  BarController,
  LineElement,
  PointElement,
  LineController,
  Title,
  Tooltip,
  Legend,
  Filler,
} from "chart.js";

ChartJS.register(CategoryScale, LinearScale, BarElement, BarController, LineElement, PointElement, LineController, Title, Tooltip, Legend, Filler);

interface DailyRow {
  date: string;
  radiation_mj_m2: number;
  energy_kwh: number;
}

type Group = "daily" | "weekly" | "monthly";

interface Props {
  data: DailyRow[];
}

function groupKey(date: string, mode: Group): string {
  const d = new Date(date);
  switch (mode) {
    case "daily":
      return date;
    case "weekly": {
      const start = new Date(d);
      start.setDate(d.getDate() - d.getDay());
      return start.toISOString().slice(0, 10);
    }
    case "monthly":
      return date.slice(0, 7);
  }
}

function groupLabel(key: string, mode: Group): string {
  if (mode === "monthly") {
    const d = new Date(key + "-02");
    return d.toLocaleString("default", { month: "short", year: "2-digit" });
  }
  if (mode === "weekly") {
    const d = new Date(key);
    const end = new Date(d);
    end.setDate(d.getDate() + 6);
    return `${d.getDate()}/${d.getMonth() + 1} – ${end.getDate()}/${end.getMonth() + 1}`;
  }
  return key;
}

export default function EnergyChart({ data }: Props) {
  const [mode, setMode] = useState<Group>("monthly");

  const { labels, values, avg } = useMemo(() => {
    const groups: Record<string, number> = {};
    for (const d of data) {
      const k = groupKey(d.date, mode);
      groups[k] = (groups[k] || 0) + d.energy_kwh;
    }
    const keys = Object.keys(groups).sort();
    const vals = keys.map((k) => Math.round(groups[k] * 100) / 100);
    const mean = vals.length > 0 ? vals.reduce((a, b) => a + b, 0) / vals.length : 0;
    return { labels: keys.map((k) => groupLabel(k, mode)), values: vals, avg: Math.round(mean * 100) / 100 };
  }, [data, mode]);

  return (
    <div className="chart-section">
      <div className="chart-header">
        <h3>Energy Breakdown</h3>
        <div className="group-toggle">
          {(["daily", "weekly", "monthly"] as Group[]).map((g) => (
            <button
              key={g}
              className={`group-btn${g === mode ? " active" : ""}`}
              onClick={() => setMode(g)}
            >
              {g.charAt(0).toUpperCase() + g.slice(1)}
            </button>
          ))}
        </div>
      </div>
      <div className="chart-container">
        <Chart
          type="bar"
          data={{
            labels,
            datasets: [
              {
                type: "bar" as const,
                label: "Energy (kWh)",
                data: values,
                backgroundColor: "#f59e0b",
                borderRadius: 4,
                order: 2,
              },
              {
                type: "line" as const,
                label: `Avg ${avg} kWh`,
                data: Array(values.length).fill(avg),
                borderColor: "#22d3ee",
                backgroundColor: "#22d3ee",
                borderWidth: 2,
                borderDash: [6, 4],
                pointRadius: 0,
                fill: false,
                order: 1,
              },
            ],
          }}
          options={{
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
              legend: {
                display: true,
                position: "top",
                align: "end",
                labels: {
                  color: "#94a3b8",
                  boxWidth: 14,
                  boxHeight: 2,
                  font: { size: 11 },
                },
              },
              tooltip: {
                callbacks: {
                  label: (ctx) =>
                    ctx.dataset.label?.startsWith("Avg")
                      ? `Average: ${avg} kWh`
                      : `${ctx.parsed.y} kWh`,
                },
              },
            },
            scales: {
              x: {
                ticks: { color: "#94a3b8", maxRotation: 45 },
                grid: { display: false },
              },
              y: {
                ticks: { color: "#94a3b8" },
                grid: { color: "#334155" },
                title: {
                  display: true,
                  text: "kWh",
                  color: "#94a3b8",
                },
              },
            },
          }}
        />
      </div>
    </div>
  );
}
