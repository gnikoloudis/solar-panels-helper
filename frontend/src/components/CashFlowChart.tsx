import { Chart } from "react-chartjs-2";
import type { ChartData } from "chart.js";

interface Props {
  cashFlow: number[];
  breakEvenYear: number | null;
}

export default function CashFlowChart({ cashFlow, breakEvenYear }: Props) {
  const labels = cashFlow.map((_, i) => `Year ${i + 1}`);

  const chartData: ChartData<"line"> = {
    labels,
    datasets: [
      {
        type: "line" as const,
        label: "Cumulative Cash Flow (€)",
        data: cashFlow,
        borderColor: "#22d3ee",
        backgroundColor: (ctx) => {
          if (!ctx.chart.chartArea) return "transparent";
          const gradient = ctx.chart.ctx.createLinearGradient(0, ctx.chart.chartArea.top, 0, ctx.chart.chartArea.bottom);
          gradient.addColorStop(0, "rgba(34, 211, 238, 0.15)");
          gradient.addColorStop(1, "rgba(34, 211, 238, 0.01)");
          return gradient;
        },
        borderWidth: 2,
        pointRadius: 3,
        pointHitRadius: 6,
        fill: true,
        tension: 0,
      },
      ...(breakEvenYear
        ? [
            {
              type: "line" as const,
              label: "Break-even",
              data: Array(cashFlow.length).fill(0),
              borderColor: "#f59e0b",
              borderWidth: 2,
              borderDash: [8, 4],
              pointRadius: 0,
              fill: false,
            },
          ]
        : []),
    ],
  };

  return (
    <div className="chart-section">
      <div className="chart-header">
        <h3>25-Year Cash Flow</h3>
      </div>
      <div className="chart-container">
        <Chart
          type="line"
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
                    const val = ctx.parsed.y;
                    return `${val >= 0 ? "+" : ""}€${val.toLocaleString(undefined, { minimumFractionDigits: 2 })}`;
                  },
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
                  text: "Cumulative Cash Flow (€)",
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
