import { Link, NavLink } from "react-router-dom";
import { UserMenu } from "./UserMenu.jsx";

const navCls =
  "rounded-lg px-3 py-2 text-sm font-medium transition-colors text-slate-600 hover:text-slate-900";

const activeNav =
  "bg-slate-100 text-slate-900 border border-slate-200/80 shadow-sm";

export function Shell({ children }) {
  return (
    <div className="mesh-bg min-h-screen flex flex-col">
      <header className="border-b border-slate-200/80 bg-white/80 backdrop-blur-md sticky top-0 z-40 shadow-sm shadow-slate-900/5">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-4 px-4 sm:px-6">
          <Link to="/dashboard" className="flex shrink-0 items-center gap-2">
            <span className="font-[family-name:var(--font-display)] text-xl font-bold tracking-tight bg-gradient-to-r from-violet-700 to-indigo-600 bg-clip-text text-transparent">
              FileFlow
            </span>
            <span className="hidden sm:inline text-xs font-medium uppercase tracking-widest text-slate-400">
              Console
            </span>
          </Link>
          <nav className="flex flex-1 flex-wrap items-center justify-center gap-1 sm:gap-2 md:justify-start">
            <NavLink
              to="/dashboard"
              end
              className={({ isActive }) => `${navCls} ${isActive ? activeNav : ""}`}
            >
              Projects
            </NavLink>
            <NavLink
              to="/dashboard/usage"
              className={({ isActive }) => `${navCls} ${isActive ? activeNav : ""}`}
            >
              Usage
            </NavLink>
            <NavLink
              to="/dashboard/integration"
              className={({ isActive }) => `${navCls} ${isActive ? activeNav : ""}`}
            >
              Integration
            </NavLink>
          </nav>
          <div className="flex shrink-0 items-center gap-2">
            <UserMenu />
          </div>
        </div>
      </header>
      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8 sm:px-6">
        {children}
      </main>
      <footer className="border-t border-slate-200/80 py-6 text-center text-xs text-slate-500">
        FileFlow · RAG API dashboard
      </footer>
    </div>
  );
}
