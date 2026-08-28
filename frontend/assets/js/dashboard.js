import { apiRequest, downloadUrl } from "./api.js";
import { dateLabel, initializeCommon, numberLabel, setNotice } from "./common.js";

let catalog;
let trendChart;

const elements = {};

document.addEventListener("DOMContentLoaded", async () => {
  await initializeCommon();
  Object.assign(elements, {
    form: document.querySelector("#dashboard-filters"),
    category: document.querySelector("#category-select"),
    indicator: document.querySelector("#indicator-select"),
    country: document.querySelector("#country-select"),
    yearFrom: document.querySelector("#year-from"),
    notice: document.querySelector("#dashboard-message"),
  });
  try {
    const [catalogPayload, summary] = await Promise.all([
      apiRequest("/catalog"),
      apiRequest("/summary"),
    ]);
    catalog = catalogPayload;
    renderSummary(summary);
    populateFilters();
    elements.form.addEventListener("submit", (event) => { event.preventDefault(); loadDashboard(); });
    elements.category.addEventListener("change", () => { populateIndicators(); loadDashboard(); });
    await loadDashboard();
  } catch (error) {
    setNotice(elements.notice, "データを読み込めませんでした。初回データ更新が完了しているか確認してください。");
    console.error(error);
  }
});

function renderSummary(summary) {
  document.querySelector("#metric-records").textContent = new Intl.NumberFormat("ja-JP").format(summary.data_count || 0);
  document.querySelector("#metric-countries").textContent = summary.country_count || 0;
  document.querySelector("#metric-indicators").textContent = summary.indicator_count || 0;
  document.querySelector("#metric-updated").textContent = dateLabel(summary.last_updated_at);
  document.querySelector("#metric-status").textContent = summary.last_update_status || "ready";
}

function populateFilters() {
  catalog.categories.forEach((category) => elements.category.add(new Option(category, category)));
  populateIndicators();
  catalog.countries.forEach((country) => elements.country.add(new Option(`${country.name_ja} / ${country.name_en}`, country.country_code)));
  const currentYear = new Date().getFullYear();
  for (let year = currentYear; year >= 2000; year -= 1) elements.yearFrom.add(new Option(`${year}年`, year));
  elements.yearFrom.value = "2010";
}

function populateIndicators() {
  const selected = elements.indicator.value || "NY.GDP.MKTP.CD";
  elements.indicator.replaceChildren();
  catalog.indicators
    .filter((item) => !elements.category.value || item.category === elements.category.value)
    .forEach((item) => elements.indicator.add(new Option(`${item.display_name}｜${item.unit}`, item.indicator_code)));
  if ([...elements.indicator.options].some((option) => option.value === selected)) elements.indicator.value = selected;
}

async function loadDashboard() {
  setNotice(elements.notice);
  const params = {
    indicator: elements.indicator.value,
    country: elements.country.value,
    year_from: elements.yearFrom.value,
  };
  try {
    const chart = await apiRequest("/charts/overview", params);
    renderChart(chart);
    renderRanking(chart);
    const indicator = catalog.indicators.find((item) => item.indicator_code === elements.indicator.value);
    document.querySelector("#indicator-description").textContent = indicator?.description || "World Bank Indicators API";
    document.querySelector("#dashboard-xlsx").href = await downloadUrl("/export.xlsx", params);
    document.querySelector("#dashboard-csv").href = await downloadUrl("/export.csv", params);
  } catch (error) {
    setNotice(elements.notice, "選択した条件のデータを表示できませんでした。時間をおいて再度お試しください。");
    console.error(error);
  }
}

function renderChart(chart) {
  document.querySelector("#trend-title").textContent = chart.indicator || "データなし";
  document.querySelector("#trend-unit").textContent = chart.unit || "—";
  const canvas = document.querySelector("#trend-chart");
  if (trendChart) trendChart.destroy();
  trendChart = new Chart(canvas, {
    type: "line",
    data: {
      labels: (chart.time_series || []).map((item) => item.year),
      datasets: [{ label: chart.indicator || "値", data: (chart.time_series || []).map((item) => item.value), borderColor: "#0f6b72", backgroundColor: "rgba(15,107,114,.1)", fill: true, tension: .25, pointRadius: 2, pointHoverRadius: 5 }],
    },
    options: { responsive: true, maintainAspectRatio: false, interaction: { intersect: false, mode: "index" }, plugins: { legend: { display: false }, tooltip: { callbacks: { label: (context) => numberLabel(context.parsed.y, chart.unit) } } }, scales: { x: { grid: { display: false } }, y: { beginAtZero: false, ticks: { callback: (value) => numberLabel(value, "", 1) } } } },
  });
}

function renderRanking(chart) {
  const list = document.querySelector("#ranking-list");
  list.replaceChildren();
  document.querySelector("#ranking-title").textContent = chart.indicator || "国別ランキング";
  document.querySelector("#ranking-year").textContent = chart.latest_year ? `${chart.latest_year}年` : "—";
  (chart.ranking || []).forEach((item) => {
    const row = document.createElement("li");
    const name = document.createElement("strong");
    name.textContent = `${item.country_name} (${item.country_code})`;
    const value = document.createElement("span");
    value.textContent = numberLabel(item.value, chart.unit);
    row.append(name, value);
    list.append(row);
  });
  if (!list.children.length) {
    const row = document.createElement("li");
    row.textContent = "該当データがありません";
    list.append(row);
  }
}
