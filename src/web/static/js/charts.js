(function () {
  "use strict";

  const script = document.getElementById("analysis-chart-data");
  if (!script || !window.Chart) return;

  let payload;
  try {
    payload = JSON.parse(script.textContent);
  } catch (error) {
    console.error("Chart data could not be parsed", error);
    return;
  }
  if (!payload.indicator) return;

  const green = "#0b694e";
  const orange = "#ee8a3a";
  const mint = "#a9d9c6";
  const grid = "rgba(16, 42, 45, 0.10)";
  const text = "#52666a";
  const format = (value) => new Intl.NumberFormat("ja-JP", { notation: "compact", maximumFractionDigits: 2 }).format(value);
  const tooltip = (context) => `${context.dataset.label}: ${Number(context.raw).toLocaleString("ja-JP")} ${payload.unit}`;
  const baseOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { display: false }, tooltip: { callbacks: { label: tooltip } } },
    scales: {
      x: { grid: { display: false }, ticks: { color: text } },
      y: { grid: { color: grid }, ticks: { color: text, callback: format }, beginAtZero: false }
    }
  };

  const line = document.getElementById("timeSeriesChart");
  if (line) {
    new Chart(line, {
      type: "line",
      data: {
        labels: payload.time_series.map((row) => row.year),
        datasets: [{
          label: payload.indicator,
          data: payload.time_series.map((row) => row.value),
          borderColor: green,
          backgroundColor: "rgba(11, 105, 78, 0.12)",
          borderWidth: 2.5,
          pointRadius: 2,
          fill: true,
          tension: 0.25
        }]
      },
      options: baseOptions
    });
  }

  const region = document.getElementById("regionChart");
  if (region) {
    new Chart(region, {
      type: "bar",
      data: {
        labels: payload.region_comparison.map((row) => row.region),
        datasets: [{
          label: payload.indicator,
          data: payload.region_comparison.map((row) => row.value),
          backgroundColor: [green, orange, mint, "#6a8f7b", "#d8ee8d", "#92a3c4"],
          borderRadius: 5
        }]
      },
      options: baseOptions
    });
  }

  const ranking = document.getElementById("rankingChart");
  if (ranking) {
    new Chart(ranking, {
      type: "bar",
      data: {
        labels: payload.ranking.map((row) => row.country_name),
        datasets: [{
          label: payload.indicator,
          data: payload.ranking.map((row) => row.value),
          backgroundColor: orange,
          borderRadius: 5
        }]
      },
      options: {
        ...baseOptions,
        indexAxis: "y",
        scales: {
          x: { grid: { color: grid }, ticks: { color: text, callback: format }, beginAtZero: true },
          y: { grid: { display: false }, ticks: { color: text } }
        }
      }
    });
  }
})();
