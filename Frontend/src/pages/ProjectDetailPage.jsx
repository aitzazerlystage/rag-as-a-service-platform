import { useEffect, useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";
import { apiFetch, getApiBase } from "../api/client.js";

function ClipboardIcon({ className }) {
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
        d="M8.25 7.5V6.108c0-1.135.845-2.098 1.976-2.192.373-.03.748-.057 1.123-.08M15.75 18H18a2.25 2.25 0 002.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 00-1.123-.08M15.75 18.75v-1.875a3.375 3.375 0 00-3.375-3.375h-1.5a3.375 3.375 0 00-3.375 3.375V18.75M6 10.5h.008v.008H6V10.5zm3 0h.008v.008H9V10.5zm3 0h.008v.008h-.008V10.5zm0-3h.008v.008H12V7.5zm-3 0h.008v.008H9V7.5zm-3 0h.008v.008H6V7.5z"
      />
    </svg>
  );
}

function CheckIcon({ className }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      className={className}
      aria-hidden
    >
      <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
    </svg>
  );
}

export function ProjectDetailPage() {
  const { projectId } = useParams();
  const location = useLocation();
  const { token, user, organization } = useAuth();
  const fromState = location.state?.project;

  const [apiKeys, setApiKeys] = useState([]);
  const [apiKeysLoading, setApiKeysLoading] = useState(true);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [projectMeta, setProjectMeta] = useState(fromState || null);
  const [uploads, setUploads] = useState([]);
  const [uploadsLoading, setUploadsLoading] = useState(true);
  const [apiKeyCopied, setApiKeyCopied] = useState(false);

  const latestKey = apiKeys[0]?.api_key ?? null;

  useEffect(() => {
    if (fromState?.project_id === projectId) {
      setProjectMeta(fromState);
      return;
    }
    if (!user?.id || !projectId) return;
    let cancelled = false;
    (async () => {
      try {
        const res = await apiFetch(`/api/projects?user_id=${encodeURIComponent(user.id)}`);
        const data = await res.json().catch(() => ({}));
        if (!res.ok || cancelled) return;
        const p = (data.projects || []).find((x) => x.project_id === projectId);
        if (p) setProjectMeta(p);
      } catch {
        /* ignore */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [user?.id, projectId, fromState]);

  useEffect(() => {
    if (!user?.id || !organization?.id || !projectId) {
      setApiKeysLoading(false);
      return;
    }
    let cancelled = false;
    (async () => {
      setApiKeysLoading(true);
      try {
        const q = new URLSearchParams({
          org_id: organization.id,
          user_id: user.id,
        });
        const res = await apiFetch(`/api/projects/${projectId}/api_keys?${q.toString()}`);
        const data = await res.json().catch(() => ({}));
        if (!res.ok || cancelled) return;
        setApiKeys(data.api_keys || []);
      } catch {
        if (!cancelled) setApiKeys([]);
      } finally {
        if (!cancelled) setApiKeysLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [user?.id, organization?.id, projectId]);

  useEffect(() => {
    if (!user?.id || !projectId) {
      setUploadsLoading(false);
      return;
    }
    let cancelled = false;
    (async () => {
      setUploadsLoading(true);
      try {
        const res = await apiFetch(
          `/api/projects/${encodeURIComponent(projectId)}/uploads?user_id=${encodeURIComponent(user.id)}`
        );
        const data = await res.json().catch(() => ({}));
        if (!res.ok || cancelled) return;
        setUploads(data.uploads || []);
      } catch {
        if (!cancelled) setUploads([]);
      } finally {
        if (!cancelled) setUploadsLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [user?.id, projectId]);

  const projectName = projectMeta?.name || "Project";
  const projectKey = projectMeta?.project_key;

  async function deleteUpload(uploadId) {
    if (!projectId || !user?.id) return;
    if (
      !confirm(
        "Remove this upload from the project and delete its vectors from search (RAG)?"
      )
    ) {
      return;
    }
    setError("");
    try {
      const q = `user_id=${encodeURIComponent(user.id)}`;
      const headers = token ? { Authorization: `Bearer ${token}` } : {};
      const res = await apiFetch(
        `/api/projects/${encodeURIComponent(projectId)}/uploads/${encodeURIComponent(uploadId)}?${q}`,
        {
          method: "DELETE",
          headers,
        }
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
      setUploads((prev) => prev.filter((u) => u.id !== uploadId));
    } catch (e) {
      setError(e?.message || "Network error — " + getApiBase());
    }
  }

  async function copyApiKeyToClipboard() {
    if (!latestKey) return;
    try {
      await navigator.clipboard.writeText(latestKey);
      setApiKeyCopied(true);
      window.setTimeout(() => setApiKeyCopied(false), 2000);
    } catch {
      setError("Could not copy — try selecting the key manually.");
    }
  }

  async function createOrRotateApiKey() {
    if (!user?.id || !organization?.id || !projectId) return;
    setError("");
    setLoading(true);
    try {
      const q = new URLSearchParams({
        org_id: organization.id,
        user_id: user.id,
      });
      const res = await apiFetch(
        `/api/projects/${projectId}/generate_api_key?${q.toString()}`,
        { method: "POST" }
      );
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setError(data.detail || `Failed (${res.status})`);
        return;
      }
      const listRes = await apiFetch(
        `/api/projects/${projectId}/api_keys?${q.toString()}`
      );
      const listData = await listRes.json().catch(() => ({}));
      if (listRes.ok) {
        setApiKeys(listData.api_keys || []);
      } else {
        setApiKeys((prev) => [{ id: "new", api_key: data.api_key, created_at: null }, ...prev]);
      }
    } catch (e) {
      setError(e?.message || "Network error — " + getApiBase());
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <nav className="mb-6 text-sm text-slate-500">
        <Link to="/dashboard" className="hover:text-violet-700">
          Projects
        </Link>
        <span className="mx-2">/</span>
        <span className="text-slate-700">{projectName}</span>
      </nav>

      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <h1 className="font-[family-name:Outfit,sans-serif] text-3xl font-bold text-slate-900">
            {projectName}
          </h1>
          <p className="mt-1 font-mono text-xs font-normal text-slate-400">
            {projectKey || "—"}
          </p>
          <p className="mt-2 font-mono text-xs text-slate-500">{projectId}</p>
        </div>
        <Link
          to="/dashboard/integration"
          state={{ projectId, orgId: organization?.id }}
          className="shrink-0 rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 shadow-sm hover:border-slate-300 hover:bg-slate-50"
        >
          Integration guide →
        </Link>
      </div>

      {error && (
        <div className="mt-6 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          {error}
        </div>
      )}

      <section className="mt-10 space-y-6">
        <div className="glass rounded-2xl p-6">
          <h2 className="font-[family-name:Outfit,sans-serif] text-lg font-semibold text-slate-900">
            API key
          </h2>
          <p className="mt-1 text-sm text-slate-600">
            Send as <code className="text-violet-700">x-api-key</code> on upload, insert, and query
            requests. Keep it secret outside the dashboard.
          </p>
          {apiKeysLoading ? (
            <p className="mt-6 text-sm text-slate-500">Loading API keys…</p>
          ) : (
            <div className="mt-6 space-y-4">
              {latestKey && (
                <div className="space-y-2">
                  <div className="flex items-start gap-2 rounded-xl border border-emerald-200 bg-emerald-50/80 p-3">
                    <code className="min-w-0 flex-1 break-all py-1 pr-1 font-mono text-sm leading-relaxed text-emerald-900">
                      {latestKey}
                    </code>
                    <button
                      type="button"
                      onClick={copyApiKeyToClipboard}
                      title={apiKeyCopied ? "Copied" : "Copy API key"}
                      aria-label={apiKeyCopied ? "Copied" : "Copy API key to clipboard"}
                      className="shrink-0 rounded-lg border border-emerald-200/80 bg-white p-2 text-emerald-800 shadow-sm hover:bg-emerald-100/80"
                    >
                      {apiKeyCopied ? (
                        <CheckIcon className="h-5 w-5 text-emerald-600" />
                      ) : (
                        <ClipboardIcon className="h-5 w-5" />
                      )}
                    </button>
                  </div>
                  {apiKeys.length > 1 && (
                    <p className="text-xs text-slate-500">
                      Showing your newest key. Older keys for this project remain valid until you
                      stop using them.
                    </p>
                  )}
                </div>
              )}
              <button
                type="button"
                onClick={createOrRotateApiKey}
                disabled={loading}
                className="rounded-xl bg-gradient-to-r from-violet-600 to-indigo-600 px-5 py-2.5 text-sm font-semibold text-white shadow-md shadow-violet-500/15 disabled:opacity-60"
              >
                {loading
                  ? "Working…"
                  : latestKey
                    ? "Create a new API key"
                    : "Generate API key"}
              </button>
            </div>
          )}
        </div>

        <div className="glass rounded-2xl p-6">
          <h2 className="font-[family-name:Outfit,sans-serif] text-lg font-semibold text-slate-900">
            Uploaded files
          </h2>
          <p className="mt-1 text-sm text-slate-600">
            Files ingested via <code className="text-violet-700">POST /api/vectors/upload</code>{" "}
            using an API key for this project (new uploads are listed after each successful run).
          </p>
          {uploadsLoading ? (
            <p className="mt-4 text-sm text-slate-500">Loading…</p>
          ) : uploads.length === 0 ? (
            <p className="mt-4 text-sm text-slate-500">
              No uploads recorded yet. Use your API client or TestApp to upload documents.
            </p>
          ) : (
            <ul className="mt-4 divide-y divide-slate-100 rounded-xl border border-slate-200 bg-white">
              {uploads.map((u) => (
                <li
                  key={u.id}
                  className="flex flex-wrap items-center justify-between gap-2 px-4 py-3 text-sm"
                >
                  <div className="min-w-0 flex-1">
                    <span className="font-medium text-slate-800">{u.original_filename}</span>
                    {u.doc_id && (
                      <p className="mt-0.5 font-mono text-[10px] text-slate-400">
                        doc_id: {u.doc_id}
                      </p>
                    )}
                  </div>
                  <div className="flex shrink-0 items-center gap-2">
                    <span className="text-xs text-slate-500">
                      {(u.created_at || "").replace("T", " ").slice(0, 19)}
                      {u.rag_inserted ? (
                        <span className="ml-2 rounded-md bg-emerald-50 px-1.5 py-0.5 text-emerald-800">
                          RAG
                        </span>
                      ) : (
                        <span className="ml-2 rounded-md bg-amber-50 px-1.5 py-0.5 text-amber-800">
                          No RAG insert
                        </span>
                      )}
                    </span>
                    <button
                      type="button"
                      onClick={() => deleteUpload(u.id)}
                      className="rounded-lg border border-red-200 bg-white px-2.5 py-1 text-xs font-medium text-red-700 hover:bg-red-50"
                    >
                      Delete
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </section>
    </div>
  );
}
