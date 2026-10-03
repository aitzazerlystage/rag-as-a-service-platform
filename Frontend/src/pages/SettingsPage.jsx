import { Link } from "react-router-dom";

export function SettingsPage() {
  return (
    <div>
      <nav className="mb-6 text-sm text-slate-500">
        <Link to="/dashboard" className="hover:text-violet-700">
          Projects
        </Link>
        <span className="mx-2">/</span>
        <span className="text-slate-700">Settings</span>
      </nav>

      <h1 className="font-[family-name:Outfit,sans-serif] text-3xl font-bold text-slate-900">
        Settings
      </h1>
      <p className="mt-1 text-slate-600">
        Account preferences and notifications will live here in a future release.
      </p>

      <div className="glass mt-8 rounded-2xl p-8 text-center">
        <p className="text-slate-600">
          No configurable settings yet. API keys and projects are managed from the{" "}
          <Link to="/dashboard" className="text-violet-700 hover:text-violet-900 hover:underline">
            Projects
          </Link>{" "}
          area.
        </p>
      </div>
    </div>
  );
}
