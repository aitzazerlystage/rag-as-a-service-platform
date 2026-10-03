/** @returns {string} */
export function getApiBase() {
  const raw = import.meta.env.VITE_API_URL || "http://localhost:8001";
  return String(raw).replace(/\/$/, "");
}

/**
 * @param {string} path
 * @param {RequestInit} [init]
 */
export async function apiFetch(path, init = {}) {
  const base = getApiBase();
  const url = path.startsWith("http") ? path : `${base}${path.startsWith("/") ? "" : "/"}${path}`;
  const res = await fetch(url, {
    ...init,
    headers: {
      ...init.headers,
    },
  });
  return res;
}

/** application/x-www-form-urlencoded body for FastAPI Form() */
export function formBody(record) {
  const p = new URLSearchParams();
  Object.entries(record).forEach(([k, v]) => {
    if (v != null && v !== "") p.append(k, String(v));
  });
  return p;
}
