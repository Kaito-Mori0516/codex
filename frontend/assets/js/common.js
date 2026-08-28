const DEFAULT_CONFIG = Object.freeze({
  api_base_path: "/api",
  operator_name: "",
  contact_email: "",
  business_price_label: "個別設定",
  business_checkout_url: "",
  enterprise_contact_url: "",
  sponsor_text: "",
  sponsor_url: "",
  adsense_client_id: "",
  adsense_slot_id: "",
});

let configPromise;

export function loadConfig() {
  if (!configPromise) {
    configPromise = fetch("/config.json", { cache: "no-store" })
      .then((response) => response.ok ? response.json() : {})
      .catch(() => ({}))
      .then((value) => ({ ...DEFAULT_CONFIG, ...value }));
  }
  return configPromise;
}

export async function initializeCommon() {
  const config = await loadConfig();
  document.querySelectorAll("[data-current-year]").forEach((node) => {
    node.textContent = new Date().getFullYear();
  });

  const toggle = document.querySelector(".nav-toggle");
  const nav = document.querySelector(".site-nav");
  if (toggle && nav) {
    toggle.addEventListener("click", () => {
      const expanded = toggle.getAttribute("aria-expanded") === "true";
      toggle.setAttribute("aria-expanded", String(!expanded));
      nav.classList.toggle("open", !expanded);
    });
  }

  if (config.operator_name) {
    document.querySelectorAll("[data-operator-name]").forEach((node) => {
      node.textContent = config.operator_name;
    });
  }
  if (config.contact_email) {
    document.querySelectorAll("[data-contact-link]").forEach((node) => {
      node.textContent = config.contact_email;
      node.href = `mailto:${config.contact_email}`;
    });
  }

  document.querySelectorAll("[data-sponsor]").forEach((slot) => {
    if (!config.sponsor_text || !config.sponsor_url) return;
    const link = document.createElement("a");
    link.href = config.sponsor_url;
    link.target = "_blank";
    link.rel = "sponsored noopener noreferrer";
    const label = document.createElement("small");
    label.textContent = "SPONSORED";
    const text = document.createElement("strong");
    text.textContent = config.sponsor_text;
    link.append(label, text);
    slot.replaceChildren(link);
    slot.hidden = false;
  });

  if (config.adsense_client_id && config.adsense_slot_id) {
    enableAds(config);
  }
  return config;
}

function enableAds(config) {
  if (!document.querySelector("script[data-world-data-lens-ads]")) {
    const script = document.createElement("script");
    script.async = true;
    script.crossOrigin = "anonymous";
    script.dataset.worldDataLensAds = "true";
    script.src = `https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=${encodeURIComponent(config.adsense_client_id)}`;
    document.head.append(script);
  }
  document.querySelectorAll("[data-ad-slot]").forEach((slot) => {
    const label = document.createElement("span");
    label.className = "ad-label";
    label.textContent = "ADVERTISEMENT";
    const ad = document.createElement("ins");
    ad.className = "adsbygoogle";
    ad.style.display = "block";
    ad.dataset.adClient = config.adsense_client_id;
    ad.dataset.adSlot = config.adsense_slot_id;
    ad.dataset.adFormat = "auto";
    ad.dataset.fullWidthResponsive = "true";
    slot.replaceChildren(label, ad);
    slot.hidden = false;
    try { (window.adsbygoogle = window.adsbygoogle || []).push({}); } catch (_) { /* provider loads asynchronously */ }
  });
}

export function numberLabel(value, unit = "", decimals = 2) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return "—";
  const formatter = new Intl.NumberFormat("ja-JP", {
    notation: Math.abs(numeric) >= 1_000_000_000 ? "compact" : "standard",
    maximumFractionDigits: decimals,
  });
  return `${formatter.format(numeric)}${unit ? ` ${unit}` : ""}`;
}

export function dateLabel(value) {
  if (!value) return "未取得";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? String(value) : new Intl.DateTimeFormat("ja-JP", { year: "numeric", month: "short", day: "numeric" }).format(date);
}

export function setNotice(element, message = "") {
  if (!element) return;
  element.textContent = message;
  element.hidden = !message;
}

document.addEventListener("DOMContentLoaded", () => initializeCommon());
