import { getApiBase } from "./client.js";

/**
 * @param {string | null | undefined} accessToken JWT from login (optional if userId is set)
 * @param {number} [days]
 * @param {string | null | undefined} [userId] fallback when JWT is missing or expired
 */
export async function fetchDashboardUsage(accessToken, days = 30, userId = null) {
  const base = getApiBase();
  const q = new URLSearchParams({ days: String(days) });
  if (userId) q.set("user_id", userId);
  const headers = { Accept: "application/json" };
  if (accessToken) headers.Authorization = `Bearer ${accessToken}`;
  const res = await fetch(`${base}/api/dashboard/usage?${q}`, {
    headers,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.detail || `Usage request failed (${res.status})`);
  }
  return data;
}

/**
 * @param {string | null | undefined} accessToken
 * @param {string} apiKeyId
 * @param {number} [days]
 * @param {string | null | undefined} [userId]
 */
export async function fetchDashboardUsageKey(accessToken, apiKeyId, days = 30, userId = null) {
  const base = getApiBase();
  const q = new URLSearchParams({ days: String(days) });
  if (userId) q.set("user_id", userId);
  const headers = { Accept: "application/json" };
  if (accessToken) headers.Authorization = `Bearer ${accessToken}`;
  const res = await fetch(`${base}/api/dashboard/usage/key/${encodeURIComponent(apiKeyId)}?${q}`, {
    headers,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.detail || `Usage request failed (${res.status})`);
  }
  return data;
}
