import { useState, useRef, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";

const menuItem =
  "block w-full px-4 py-2.5 text-left text-sm text-slate-700 hover:bg-slate-50 first:rounded-t-xl last:rounded-b-xl";

export function UserMenu() {
  const [open, setOpen] = useState(false);
  const containerRef = useRef(null);
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    function handleDocClick(e) {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleDocClick);
    return () => document.removeEventListener("mousedown", handleDocClick);
  }, []);

  const initials = (user?.full_name || user?.username || user?.email || "?")
    .split(/\s+/)
    .map((s) => s[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();

  return (
    <div className="relative" ref={containerRef}>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex h-10 w-10 items-center justify-center rounded-full border border-slate-200 bg-gradient-to-br from-violet-600 to-indigo-700 text-sm font-semibold text-white shadow-md shadow-violet-600/25 ring-2 ring-white transition hover:opacity-95"
        aria-expanded={open}
        aria-haspopup="true"
        aria-label="Account menu"
      >
        {initials}
      </button>

      {open && (
        <div
          className="absolute right-0 z-50 mt-2 w-56 overflow-hidden rounded-xl border border-slate-200/90 bg-white py-1 shadow-xl shadow-slate-900/10"
          role="menu"
        >
          <div className="border-b border-slate-100 px-4 py-3">
            <p className="truncate text-sm font-medium text-slate-900">{user?.full_name}</p>
            <p className="truncate text-xs text-slate-500">{user?.email}</p>
          </div>
          <Link
            to="/dashboard/profile"
            role="menuitem"
            className={menuItem}
            onClick={() => setOpen(false)}
          >
            Profile
          </Link>
          <Link
            to="/dashboard/usage"
            role="menuitem"
            className={menuItem}
            onClick={() => setOpen(false)}
          >
            API usage
          </Link>
          <Link
            to="/dashboard/settings"
            role="menuitem"
            className={menuItem}
            onClick={() => setOpen(false)}
          >
            Settings
          </Link>
          <Link
            to="/dashboard/faq"
            role="menuitem"
            className={menuItem}
            onClick={() => setOpen(false)}
          >
            FAQ
          </Link>
          <button
            type="button"
            role="menuitem"
            className={`${menuItem} border-t border-slate-100 text-red-600 hover:text-red-700`}
            onClick={() => {
              setOpen(false);
              logout();
              navigate("/login");
            }}
          >
            Sign out
          </button>
        </div>
      )}
    </div>
  );
}
