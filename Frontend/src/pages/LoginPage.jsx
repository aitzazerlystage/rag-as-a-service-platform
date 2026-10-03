import { useState } from "react";
import { Link, useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";
import { apiFetch, formBody, getApiBase } from "../api/client.js";

const inputCls =
  "w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-slate-900 outline-none ring-violet-500/30 placeholder:text-slate-400 focus:border-violet-300 focus:ring-2";

export function LoginPage() {
  const { setSession } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from = location.state?.from?.pathname || "/dashboard";

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function onSubmit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await apiFetch("/login", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: formBody({ email, password }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setError(data.detail || `Login failed (${res.status})`);
        return;
      }
      setSession(data);
      navigate(from, { replace: true });
    } catch (err) {
      setError(err?.message || "Network error — is the API running at " + getApiBase() + "?");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mesh-bg flex min-h-screen items-center justify-center px-4 py-16">
      <div className="glass glow-ring w-full max-w-md rounded-3xl p-8 sm:p-10">
        <div className="mb-8 text-center">
          <Link
            to="/"
            className="font-[family-name:Outfit,sans-serif] text-2xl font-bold bg-gradient-to-r from-violet-700 to-emerald-600 bg-clip-text text-transparent"
          >
            FileFlow
          </Link>
          <h1 className="mt-4 font-[family-name:Outfit,sans-serif] text-2xl font-semibold text-slate-900">
            Welcome back
          </h1>
          <p className="mt-1 text-sm text-slate-600">
            Sign in to manage projects and API keys.
          </p>
        </div>

        <form onSubmit={onSubmit} className="space-y-5">
          {error && (
            <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
              {error}
            </div>
          )}
          <div>
            <label className="mb-1.5 block text-xs font-medium uppercase tracking-wide text-slate-500">
              Email
            </label>
            <input
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className={inputCls}
              placeholder="you@company.com"
            />
          </div>
          <div>
            <label className="mb-1.5 block text-xs font-medium uppercase tracking-wide text-slate-500">
              Password
            </label>
            <input
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className={inputCls}
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-xl bg-gradient-to-r from-violet-600 to-indigo-600 py-3.5 text-sm font-semibold text-white shadow-lg shadow-violet-500/20 disabled:opacity-60"
          >
            {loading ? "Signing in…" : "Sign in"}
          </button>
        </form>

        <p className="mt-8 text-center text-sm text-slate-600">
          No account?{" "}
          <Link to="/signup" className="font-medium text-violet-700 hover:text-violet-800">
            Create one
          </Link>
        </p>
      </div>
    </div>
  );
}
