import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  PieChart,
  Pie,
  Cell,
  Legend,
  LineChart,
  Line,
} from "recharts";
import { useAuth } from "../context/AuthContext.jsx";
import { fetchDashboardUsageKey } from "../api/dashboard.js";

const PIE_COLORS = ["#7c3aed", "#059669", "#0284c7", "#db2777", "#d97706", "#8b5cf6"];

const tooltipStyles = {
  background: "#ffffff",
  border: "1px solid #e2e8f0",
  borderRadius: "8px",
  color: "#334155",
  boxShadow: "0 4px 6px -1px rgb(15 23 42 / 0.08)",
};

export function UsageKeyDetailPage() {
  const { apiKeyId } = useParams();
  const { token, user } = useAuth();
  const [days, setDays] = useState(30);
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    if (!user?.id || !apiKeyId) {
      setLoading(false);
      return;
    }
    setError("");
    setLoading(true);
    try {
      const d = await fetchDashboardUsageKey(token, apiKeyId, days, user.id);
      setData(d);
    } catch (e) {
      setError(e?.message || "Failed to load usage");
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [token, apiKeyId, days, user?.id]);

  useEffect(() => {
    load();
  }, [load]);

  const dailySeries = useMemo(() => data?.daily_series || [], [data]);

  const endpointPie = useMemo(() => {
    const raw = data?.endpoint_breakdown || {};
    return Object.entries(raw).map(([name, v]) => ({
      name,
      value: v.total_chars ?? v.tokens ?? 0,
      requests: v.count,
    }));
  }, [data]);

  const meta = data?.api_key;

  return (
    <div>
      <nav className="mb-6 text-sm text-slate-500">
        <Link to="/dashboard" className="hover:text-violet-700">
          Projects
        </Link>
        <span className="mx-2">/</span>
        <Link to="/dashboard/usage" className="hover:text-violet-700">
          API usage
        </Link>
        <span className="mx-2">/</span>
        <span className="text-slate-700">API key</span>
      </nav>

      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="font-[family-name:Outfit,sans-serif] text-3xl font-bold text-slate-900">
            API key usage
          </h1>
          <p className="mt-1 font-mono text-sm text-slate-600">
            {meta?.masked_key}{" "}
            {meta?.project_name && (
              <span className="text-slate-500">· {meta.project_name}</span>
            )}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <label className="text-xs uppercase text-slate-500">Period</label>
          <select
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
            className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-800 shadow-sm focus:border-violet-300 focus:outline-none focus:ring-2 focus:ring-violet-500/20"
          >
            <option value={7}>7 days</option>
            <option value={30}>30 days</option>
            <option value={90}>90 days</option>
          </select>
        </div>
      </div>

      {error && (
        <div className="mt-6 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          {error}
        </div>
      )}

      {loading && <p className="mt-8 text-slate-500">Loading…</p>}

      {!loading && data && (
        <>
          <div className="mt-8 grid gap-4 sm:grid-cols-3">
            <div className="glass rounded-2xl p-5">
              <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
                Period requests
              </p>
              <p className="mt-2 font-[family-name:Outfit,sans-serif] text-2xl font-bold text-slate-900">
                {data.summary?.total_requests ?? 0}
              </p>
            </div>
            <div className="glass rounded-2xl p-5">
              <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
                Period tokens
              </p>
              <p className="mt-2 font-[family-name:Outfit,sans-serif] text-2xl font-bold text-slate-900">
                {(data.summary?.total_tokens ?? 0).toLocaleString()}
              </p>
            </div>
            <div className="glass rounded-2xl p-5">
              <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
                Cumulative (key)
              </p>
              <p className="mt-2 font-[family-name:Outfit,sans-serif] text-2xl font-bold text-slate-900">
                {(
                  data.api_keys?.[0]?.total_tokens_used_cumulative ?? 0
                ).toLocaleString()}
              </p>
            </div>
          </div>

          <section className="glass mt-10 rounded-2xl p-6">
            <h2 className="font-[family-name:Outfit,sans-serif] text-lg font-semibold text-slate-900">
              Daily tokens
            </h2>
            <p className="text-xs text-slate-500">
              Sum of token usage recorded per day for this key (period: {days} days)
            </p>
            <div className="mt-4 h-80 w-full">
              {dailySeries.length === 0 ? (
                <p className="py-16 text-center text-sm text-slate-500">No data.</p>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={dailySeries}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                    <XAxis
                      dataKey="date"
                      tick={{ fill: "#64748b", fontSize: 10 }}
                      tickFormatter={(v) => (v && v.length >= 10 ? v.slice(5, 10) : v)}
                    />
                    <YAxis tick={{ fill: "#64748b", fontSize: 11 }} />
                    <Tooltip contentStyle={tooltipStyles} />
                    <Line
                      type="monotone"
                      dataKey="tokens"
                      name="Tokens"
                      stroke="#6d28d9"
                      strokeWidth={2}
                      dot={{ r: 2 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              )}
            </div>
          </section>

          <div className="mt-10 grid gap-8 lg:grid-cols-2">
            <section className="glass rounded-2xl p-6">
              <h2 className="font-[family-name:Outfit,sans-serif] text-lg font-semibold text-slate-900">
                Daily requests
              </h2>
              <p className="text-xs text-slate-500">Recorded API calls per day</p>
              <div className="mt-4 h-64 w-full">
                {dailySeries.length === 0 ? (
                  <p className="py-12 text-center text-sm text-slate-500">No data.</p>
                ) : (
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={dailySeries}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                      <XAxis
                        dataKey="date"
                        tick={{ fill: "#64748b", fontSize: 10 }}
                        tickFormatter={(v) => (v && v.length >= 10 ? v.slice(5, 10) : v)}
                      />
                      <YAxis tick={{ fill: "#64748b", fontSize: 11 }} />
                      <Tooltip contentStyle={tooltipStyles} />
                      <Bar dataKey="requests" fill="#8b5cf6" name="Requests" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                )}
              </div>
            </section>

            <section className="glass rounded-2xl p-6">
              <h2 className="font-[family-name:Outfit,sans-serif] text-lg font-semibold text-slate-900">
                By endpoint
              </h2>
              <p className="text-xs text-slate-500">Share of tokens by route</p>
              <div className="mt-4 h-64 w-full">
                {endpointPie.length === 0 ? (
                  <p className="py-12 text-center text-sm text-slate-500">No breakdown yet.</p>
                ) : (
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={endpointPie}
                        dataKey="value"
                        nameKey="name"
                        cx="50%"
                        cy="50%"
                        outerRadius={85}
                        label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                      >
                        {endpointPie.map((_, i) => (
                          <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip contentStyle={tooltipStyles} />
                      <Legend wrapperStyle={{ color: "#475569", fontSize: 12 }} />
                    </PieChart>
                  </ResponsiveContainer>
                )}
              </div>
            </section>
          </div>
        </>
      )}
    </div>
  );
}
