import { loadConfig } from "./common.js";

export async function apiRequest(path, params = {}) {
  const config = await loadConfig();
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") query.set(key, value);
  });
  const url = `${config.api_base_path}${path}${query.size ? `?${query}` : ""}`;
  const response = await fetch(url, { headers: { Accept: "application/json" } });
  if (!response.ok) throw new Error(`API request failed (${response.status})`);
  return response.json();
}

export async function downloadUrl(path, params = {}) {
  const config = await loadConfig();
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") query.set(key, value);
  });
  return `${config.api_base_path}${path}${query.size ? `?${query}` : ""}`;
}
