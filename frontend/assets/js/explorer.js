import { apiRequest, downloadUrl } from "./api.js";
import { initializeCommon, numberLabel, setNotice } from "./common.js";

let catalog;
let page = 1;
let pages = 1;

const elements = {};

document.addEventListener("DOMContentLoaded", async () => {
  await initializeCommon();
  Object.assign(elements, {
    form: document.querySelector("#explorer-filters"), category: document.querySelector("#filter-category"), indicator: document.querySelector("#filter-indicator"), country: document.querySelector("#filter-country"), yearFrom: document.querySelector("#filter-year-from"), yearTo: document.querySelector("#filter-year-to"), sort: document.querySelector("#filter-sort"), order: document.querySelector("#filter-order"), body: document.querySelector("#data-body"), notice: document.querySelector("#explorer-message"), prev: document.querySelector("#page-prev"), next: document.querySelector("#page-next"),
  });
  try {
    catalog = await apiRequest("/catalog");
    populateFilters();
    elements.form.addEventListener("submit", (event) => { event.preventDefault(); page = 1; loadData(); });
    elements.category.addEventListener("change", () => { populateIndicators(); page = 1; loadData(); });
    document.querySelector("#reset-filters").addEventListener("click", resetFilters);
    elements.prev.addEventListener("click", () => { if (page > 1) { page -= 1; loadData(); } });
    elements.next.addEventListener("click", () => { if (page < pages) { page += 1; loadData(); } });
    await loadData();
  } catch (error) {
    setNotice(elements.notice, "データカタログを読み込めませんでした。初回データ更新を確認してください。");
    console.error(error);
  }
});

function populateFilters() {
  catalog.categories.forEach((category) => elements.category.add(new Option(category, category)));
  populateIndicators();
  catalog.countries.forEach((country) => elements.country.add(new Option(`${country.name_ja} / ${country.name_en}`, country.country_code)));
  elements.yearFrom.value = "2010";
  elements.yearTo.value = new Date().getFullYear();
}

function populateIndicators() {
  const selected = elements.indicator.value || "NY.GDP.MKTP.CD";
  elements.indicator.replaceChildren();
  catalog.indicators.filter((item) => !elements.category.value || item.category === elements.category.value).forEach((item) => elements.indicator.add(new Option(`${item.display_name}｜${item.unit}`, item.indicator_code)));
  if ([...elements.indicator.options].some((option) => option.value === selected)) elements.indicator.value = selected;
}

function params() {
  return { indicator: elements.indicator.value, country: elements.country.value, year_from: elements.yearFrom.value, year_to: elements.yearTo.value, sort: elements.sort.value, order: elements.order.value, page, page_size: 50 };
}

async function loadData() {
  setNotice(elements.notice);
  elements.body.innerHTML = '<tr><td colspan="7"><div class="loading-state">データを読み込んでいます…</div></td></tr>';
  try {
    const query = params();
    const result = await apiRequest("/data", query);
    page = result.page;
    pages = result.pages;
    renderRows(result.records);
    document.querySelector("#result-total").textContent = new Intl.NumberFormat("ja-JP").format(result.total);
    const indicator = catalog.indicators.find((item) => item.indicator_code === elements.indicator.value);
    document.querySelector("#result-caption").textContent = `${indicator?.display_name || "指標"} / ${elements.country.selectedOptions[0]?.textContent || "すべての国"}`;
    document.querySelector("#page-state").textContent = `${page} / ${pages} ページ`;
    elements.prev.disabled = page <= 1;
    elements.next.disabled = page >= pages;
    const exportParams = { ...query }; delete exportParams.page; delete exportParams.page_size;
    document.querySelector("#xlsx-download").href = await downloadUrl("/export.xlsx", exportParams);
    document.querySelector("#csv-download").href = await downloadUrl("/export.csv", exportParams);
  } catch (error) {
    elements.body.innerHTML = '<tr><td colspan="7"><div class="empty-state">データを取得できませんでした。</div></td></tr>';
    setNotice(elements.notice, "検索に失敗しました。条件を確認してもう一度お試しください。");
    console.error(error);
  }
}

function renderRows(records) {
  elements.body.replaceChildren();
  records.forEach((item) => {
    const row = document.createElement("tr");
    const country = cell("country-cell");
    const countryName = document.createElement("strong"); countryName.textContent = item.country_name;
    const countryCode = document.createElement("small"); countryCode.textContent = item.country_code;
    country.append(countryName, countryCode);
    const category = cell(); const tag = document.createElement("span"); tag.className = "category-tag"; tag.textContent = item.category || "その他"; category.append(tag);
    const indicator = cell("indicator-cell"); const indicatorName = document.createElement("strong"); indicatorName.textContent = item.indicator_name; const indicatorCode = document.createElement("small"); indicatorCode.textContent = item.indicator_code; indicator.append(indicatorName, indicatorCode);
    const year = cell(); year.textContent = item.year;
    const value = cell("numeric"); value.textContent = numberLabel(item.value, "", 2);
    const unit = cell(); unit.textContent = item.unit;
    const source = cell(); const link = document.createElement("a"); link.className = "source-link"; link.href = item.source_url; link.target = "_blank"; link.rel = "noopener noreferrer"; link.textContent = "World Bank ↗"; source.append(link);
    row.append(country, category, indicator, year, value, unit, source);
    elements.body.append(row);
  });
  if (!records.length) elements.body.innerHTML = '<tr><td colspan="7"><div class="empty-state">条件に一致するデータがありません。</div></td></tr>';
}

function cell(className = "") { const node = document.createElement("td"); if (className) node.className = className; return node; }

function resetFilters() {
  elements.category.value = "";
  populateIndicators();
  elements.indicator.value = "NY.GDP.MKTP.CD";
  elements.country.value = "";
  elements.yearFrom.value = "2010";
  elements.yearTo.value = new Date().getFullYear();
  elements.sort.value = "year";
  elements.order.value = "desc";
  page = 1;
  loadData();
}
