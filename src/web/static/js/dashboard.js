(function () {
  "use strict";

  const colors = {
    green: "#0b694e",
    greenFill: "rgba(11, 105, 78, 0.12)",
    grid: "rgba(16, 42, 45, 0.10)",
    text: "#52666a"
  };

  function parseData(id) {
    const element = document.getElementById(id);
    if (!element) return null;
    try {
      return JSON.parse(element.textContent);
    } catch (error) {
      console.error("Chart data could not be parsed", error);
      return null;
    }
  }

  function compact(value) {
    return new Intl.NumberFormat("ja-JP", { notation: "compact", maximumFractionDigits: 2 }).format(value);
  }

  function drawLine(canvasId, payload) {
    const canvas = document.getElementById(canvasId);
    if (!canvas || !payload || !payload.time_series || !window.Chart) return;
    new Chart(canvas, {
      type: "line",
      data: {
        labels: payload.time_series.map((row) => row.year),
        datasets: [{
          label: `${payload.indicator || "値"}（${payload.unit || ""}）`,
          data: payload.time_series.map((row) => row.value),
          borderColor: colors.green,
          backgroundColor: colors.greenFill,
          borderWidth: 2.5,
          pointRadius: 2,
          pointHoverRadius: 5,
          fill: true,
          tension: 0.28
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { intersect: false, mode: "index" },
        plugins: {
          legend: { display: false },
          tooltip: { callbacks: { label: (context) => `${context.dataset.label}: ${Number(context.raw).toLocaleString("ja-JP")}` } }
        },
        scales: {
          x: { grid: { display: false }, ticks: { color: colors.text, maxTicksLimit: 12 } },
          y: { grid: { color: colors.grid }, ticks: { color: colors.text, callback: compact }, beginAtZero: false }
        }
      }
    });
  }

  drawLine("dashboardTrend", parseData("dashboard-chart-data"));
  drawLine("filteredTrend", parseData("filtered-chart-data"));
})();
