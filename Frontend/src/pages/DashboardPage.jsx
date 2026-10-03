import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";
import { apiFetch, getApiBase } from "../api/client.js";

const inputCls =
  "w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-slate-900 outline-none focus:border-violet-300 focus:ring-2 focus:ring-violet-500/25";

function TrashIcon({ className }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.5}
      className={className}
      aria-hidden
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0"
      />
    </svg>
  );
}

export function DashboardPage() {
  const { user, organization, token } = useAuth();
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [deletingId, setDeletingId] = useState(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState("");
  const [newDesc, setNewDesc] = useState("");

  const load = useCallback(async () => {
    if (!user?.id) return;
    setError("");
    setLoading(true);
    try {
      const res = await apiFetch(`/api/projects?user_id=${encodeURIComponent(user.id)}`);
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setError(data.detail || `Failed to load projects (${res.status})`);
        setProjects([]);
        return;
      }
      setProjects(data.projects || []);
    } catch (e) {
      setError(e?.message || "Network error — " + getApiBase());
      setProjects([]);
    } finally {
      setLoading(false);
    }
  }, [user?.id]);

  useEffect(() => {
    load();
  }, [load]);

  async function deleteProject(project) {
    if (!user?.id || !project?.project_id) return;
    if (
      !window.confirm(
        `Delete project "${project.name}"? All API keys for this project will be removed. ` +
          "Vectors for every RAG-indexed upload (by doc_id) will be deleted from search, then the project is removed. This cannot be undone."
      )
    ) {
      return;
    }
    setDeletingId(project.project_id);
    setError("");
    try {
      const q = `user_id=${encodeURIComponent(user.id)}`;
      const headers = token ? { Authorization: `Bearer ${token}` } : {};
      const res = await apiFetch(
        `/api/projects/${encodeURIComponent(project.project_id)}?${q}`,
        { method: "DELETE", headers }
      );
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setError(
          typeof data.detail === "string"
            ? data.detail
            : `Delete failed (${res.status})`
        );
        return;
      }
      await load();
    } catch (e) {
      setError(e?.message || "Network error — " + getApiBase());
    } finally {
      setDeletingId(null);
    }
  }

  async function createProject(e) {
    e.preventDefault();
    if (!organization?.id || !user?.id || !newName.trim()) return;
    setCreating(true);
    setError("");
    try {
      const res = await apiFetch("/api/projects/create", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: user.id,
          org_id: organization.id,
          project_name: newName.trim(),
          description: newDesc.trim() || undefined,
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setError(data.detail || `Create failed (${res.status})`);
        return;
      }
      setModalOpen(false);
      setNewName("");
      setNewDesc("");
      await load();
    } catch (e) {
      setError(e?.message || "Network error");
    } finally {
      setCreating(false);
    }
  }

  if (!organization?.id) {
    return (
      <div className="rounded-2xl border border-amber-200 bg-amber-50 p-6 text-amber-900">
        Your account has no organization linked. Try logging out and signing up again, or
        contact support.
      </div>
    );
  }

  return (
    <div>
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="font-[family-name:Outfit,sans-serif] text-3xl font-bold text-slate-900">
            Projects
          </h1>
          <p className="mt-1 text-slate-600">
            Organization{" "}
            <span className="font-mono text-sm text-violet-700">{organization.name}</span>
          </p>
        </div>
        <button
          type="button"
          onClick={() => setModalOpen(true)}
          className="rounded-xl bg-gradient-to-r from-violet-600 to-indigo-600 px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-violet-500/20"
        >
          New project
        </button>
      </div>

      {error && (
        <div className="mt-6 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          {error}
        </div>
      )}

      <div className="mt-10">
        {loading ? (
          <p className="text-slate-500">Loading projects…</p>
        ) : projects.length === 0 ? (
          <div className="glass rounded-2xl border border-dashed border-slate-200 p-12 text-center">
            <p className="text-slate-600">No projects yet. Create one to get an API key.</p>
            <button
              type="button"
              onClick={() => setModalOpen(true)}
              className="mt-4 text-sm font-medium text-violet-700 hover:text-violet-800"
            >
              Create your first project →
            </button>
          </div>
        ) : (
          <ul className="grid gap-4 sm:grid-cols-2">
            {projects.map((p) => (
              <li
                key={p.project_id}
                className="glass flex min-h-[7rem] overflow-hidden rounded-2xl transition hover:border-violet-200 hover:shadow-md"
              >
                <button
                  type="button"
                  title="Delete project"
                  aria-label={`Delete project ${p.name}`}
                  disabled={deletingId === p.project_id}
                  onClick={() => deleteProject(p)}
                  className="flex shrink-0 items-center justify-center border-r border-slate-200/80 bg-white/60 px-3 text-slate-500 transition hover:bg-red-50 hover:text-red-700 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {deletingId === p.project_id ? (
                    <span className="text-xs text-slate-500">…</span>
                  ) : (
                    <TrashIcon className="h-5 w-5" />
                  )}
                </button>
                <Link
                  to={`/dashboard/projects/${p.project_id}`}
                  state={{ project: p }}
                  className="group min-w-0 flex-1 p-6"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <h2 className="font-[family-name:Outfit,sans-serif] text-lg font-semibold text-slate-900 group-hover:text-violet-800">
                        {p.name}
                      </h2>
                      {p.description && (
                        <p className="mt-1 line-clamp-2 text-sm text-slate-500">{p.description}</p>
                      )}
                    </div>
                    <span className="rounded-lg bg-emerald-50 px-2 py-1 text-xs font-medium text-emerald-800 ring-1 ring-emerald-200/80">
                      active
                    </span>
                  </div>
                  <p className="mt-4 font-mono text-xs text-slate-500">{p.project_id}</p>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </div>

      {modalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4 backdrop-blur-sm">
          <div
            className="glass glow-ring w-full max-w-md rounded-2xl p-6"
            role="dialog"
            aria-modal="true"
            aria-labelledby="new-project-title"
          >
            <h2
              id="new-project-title"
              className="font-[family-name:Outfit,sans-serif] text-xl font-semibold text-slate-900"
            >
              New project
            </h2>
            <form onSubmit={createProject} className="mt-6 space-y-4">
              <div>
                <label className="mb-1 block text-xs font-medium uppercase text-slate-500">
                  Name
                </label>
                <input
                  required
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  className={inputCls}
                  placeholder="e.g. Clinical trials RAG"
                />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium uppercase text-slate-500">
                  Description (optional)
                </label>
                <textarea
                  value={newDesc}
                  onChange={(e) => setNewDesc(e.target.value)}
                  rows={3}
                  className={`${inputCls} resize-none`}
                />
              </div>
              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setModalOpen(false)}
                  className="rounded-xl px-4 py-2 text-sm text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creating}
                  className="rounded-xl bg-gradient-to-r from-violet-600 to-indigo-600 px-5 py-2 text-sm font-semibold text-white disabled:opacity-60"
                >
                  {creating ? "Creating…" : "Create"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
