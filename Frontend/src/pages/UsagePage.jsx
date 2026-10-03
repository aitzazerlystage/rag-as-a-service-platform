import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
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
import { fetchDashboardUsage } from "../api/dashboard.js";

const PIE_COLORS = ["#7c3aed", "#059669", "#0284c7", "#db2777", "#d97706", "#8b5cf6"];

const tooltipStyles = {
  background: "#ffffff",
  border: "1px solid #e2e8f0",
  borderRadius: "8px",
  color: "#334155",
  boxShadow: "0 4px 6px -1px rgb(15 23 42 / 0.08)",
};

function pct(used, limit) {
  if (limit == null || limit === 0) return null;
  return Math.min(100, Math.round((used / limit) * 100));
}

export function UsagePage() {
  const { token, user } = useAuth();
  const [days, setDays] = useState(30);
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    if (!user?.id) {
      setLoading(false);
      return;
    }
    setError("");
    setLoading(true);
    try {
      const d = await fetchDashboardUsage(token, days, user.id);
      setData(d);
    } catch (e) {
      setError(e?.message || "Failed to load usage");
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [token, days, user?.id]);

  useEffect(() => {
    load();
  }, [load]);

  const dailySeries = useMemo(() => data?.daily_series || [], [data]);

  const dailyChart = useMemo(() => {
    const raw = data?.daily_usage || {};
    return Object.entries(raw)
      .map(([date, v]) => ({
        date,
        requests: v.count,
        characters: v.total_chars,
        tokens: v.tokens ?? v.total_chars,
      }))
      .sort((a, b) => a.date.localeCompare(b.date));
  }, [data]);

  const endpointPie = useMemo(() => {
    const raw = data?.endpoint_breakdown || {};
    return Object.entries(raw).map(([name, v]) => ({
      name,
      value: v.total_chars,
      requests: v.count,
    }));
  }, [data]);

  const sub = data?.subscription;

  return (
    <div>
      <nav className="mb-6 text-sm text-slate-500">
        <Link to="/dashboard" className="hover:text-violet-700">
          Projects
        </Link>
        <span className="mx-2">/</span>
        <span className="text-slate-700">API usage</span>
      </nav>

      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="font-[family-name:Outfit,sans-serif] text-3xl font-bold text-slate-900">
            API usage
          </h1>
          <p className="mt-1 text-slate-600">
            Token usage from recorded API calls across all keys you own (rolling period below).
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

      {loading && <p className="mt-8 text-slate-500">Loading usage…</p>}

      {!loading && data && (
        <>
          {sub && (
            <div className="mt-8 grid gap-4 sm:grid-cols-3">
              <QuotaCard
                label="Tokens (org)"
                used={sub.used_tokens}
                limit={sub.monthly_limit_tokens}
              />
              <QuotaCard
                label="Queries (org)"
                used={sub.used_queries}
                limit={sub.monthly_limit_queries}
              />
              <QuotaCard
                label="Ingest (org)"
                used={sub.used_ingest}
                limit={sub.monthly_limit_ingest}
              />
            </div>
          )}

          <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard
              label="Requests (period)"
              value={data.summary?.total_requests ?? 0}
            />
            <StatCard
              label="Period tokens"
              value={(data.summary?.total_tokens ?? data.summary?.total_characters ?? 0).toLocaleString()}
            />
            <StatCard
              label="Input characters"
              value={(data.summary?.total_input_characters ?? 0).toLocaleString()}
            />
            <StatCard
              label="Output characters"
              value={(data.summary?.total_output_characters ?? 0).toLocaleString()}
            />
          </div>

          <section className="glass mt-10 rounded-2xl p-6">
            <h2 className="font-[family-name:Outfit,sans-serif] text-lg font-semibold text-slate-900">
              Daily tokens (full period)
            </h2>
            <p className="text-xs text-slate-500">
              Each day sums token usage from all your API keys (zeros on idle days).
            </p>
            <div className="mt-4 h-80 w-full">
              {dailySeries.length === 0 ? (
                <p className="py-16 text-center text-sm text-slate-500">
                  No usage in this period yet.
                </p>
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
                Daily activity
              </h2>
              <p className="text-xs text-slate-500">Requests and token-equivalent volume per day</p>
              <div className="mt-4 h-72 w-full">
                {dailyChart.length === 0 ? (
                  <p className="py-16 text-center text-sm text-slate-500">
                    No usage in this period yet.
                  </p>
                ) : (
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={dailyChart}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                      <XAxis dataKey="date" tick={{ fill: "#64748b", fontSize: 11 }} />
                      <YAxis
                        yAxisId="left"
                        tick={{ fill: "#64748b", fontSize: 11 }}
                        label={{ value: "Requests", fill: "#7c3aed", fontSize: 10 }}
                      />
                      <YAxis
                        yAxisId="right"
                        orientation="right"
                        tick={{ fill: "#64748b", fontSize: 11 }}
                        label={{ value: "Tokens", fill: "#059669", fontSize: 10 }}
                      />
                      <Tooltip contentStyle={tooltipStyles} />
                      <Bar
                        yAxisId="left"
                        dataKey="requests"
                        fill="#8b5cf6"
                        name="Requests"
                        radius={[4, 4, 0, 0]}
                      />
                      <Bar
                        yAxisId="right"
                        dataKey="tokens"
                        fill="#10b981"
                        name="Tokens"
                        radius={[4, 4, 0, 0]}
                      />
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
              <div className="mt-4 h-72 w-full">
                {endpointPie.length === 0 ? (
                  <p className="py-16 text-center text-sm text-slate-500">
                    No endpoint breakdown yet.
                  </p>
                ) : (
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={endpointPie}
                        dataKey="value"
                        nameKey="name"
                        cx="50%"
                        cy="50%"
                        outerRadius={90}
                        label={({ name, percent }) =>
                          `${name} ${(percent * 100).toFixed(0)}%`
                        }
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

          <section className="glass mt-8 rounded-2xl overflow-hidden">
            <div className="border-b border-slate-100 bg-slate-50/50 px-6 py-4">
              <h2 className="font-[family-name:Outfit,sans-serif] text-lg font-semibold text-slate-900">
                Per API key
              </h2>
              <p className="text-xs text-slate-500">
                Click a row for per-key charts. Cumulative + period totals.
              </p>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-slate-200 text-xs uppercase text-slate-500">
                    <th className="px-6 py-3">Project</th>
                    <th className="px-6 py-3">Key</th>
                    <th className="px-6 py-3 text-right">Cumulative tokens</th>
                    <th className="px-6 py-3 text-right">Period requests</th>
                    <th className="px-6 py-3 text-right">Period tokens</th>
                  </tr>
                </thead>
                <tbody>
                  {(data.api_keys || []).length === 0 ? (
                    <tr>
                      <td colSpan={5} className="px-6 py-8 text-center text-slate-500">
                        No API keys yet. Create a project and generate a key.
                      </td>
                    </tr>
                  ) : (
                    data.api_keys.map((row) => (
                      <tr
                        key={row.api_key_id}
                        className="border-b border-slate-100 text-slate-700 transition-colors hover:bg-violet-50/60"
                      >
                        <td className="px-6 py-3">
                          <Link
                            to={`/dashboard/usage/keys/${row.api_key_id}`}
                            className="font-medium text-violet-800 underline-offset-2 hover:underline"
                          >
                            {row.project_name}
                          </Link>
                        </td>
                        <td className="px-6 py-3 font-mono text-xs text-slate-500">
                          <Link
                            to={`/dashboard/usage/keys/${row.api_key_id}`}
                            className="hover:text-violet-800"
                          >
                            {row.masked_key}
                          </Link>
                        </td>
                        <td className="px-6 py-3 text-right tabular-nums">
                          {(row.total_tokens_used_cumulative ?? 0).toLocaleString()}
                        </td>
                        <td className="px-6 py-3 text-right tabular-nums">
                          {row.period_requests}
                        </td>
                        <td className="px-6 py-3 text-right tabular-nums">
                          {(
                            row.period_tokens ??
                            row.period_total_characters ??
                            0
                          ).toLocaleString()}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </section>
        </>
      )}
    </div>
  );
}

function StatCard({ label, value }) {
  return (
    <div className="glass rounded-2xl p-5">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-2 font-[family-name:Outfit,sans-serif] text-2xl font-bold text-slate-900">
        {value}
      </p>
    </div>
  );
}

function QuotaCard({ label, used, limit }) {
  const p = pct(used, limit);
  return (
    <div className="glass rounded-2xl p-5">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-2 text-lg font-semibold text-slate-900">
        {(used ?? 0).toLocaleString()}
        {limit != null && (
          <span className="text-slate-500"> / {limit.toLocaleString()}</span>
        )}
      </p>
      {p != null && (
        <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-200">
          <div
            className="h-full rounded-full bg-gradient-to-r from-violet-600 to-emerald-500"
            style={{ width: `${p}%` }}
          />
        </div>
      )}
    </div>
  );
}
