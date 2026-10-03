import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";
import { getApiBase } from "../api/client.js";

function Copy({ text }) {
  const [done, setDone] = useState(false);
  return (
    <button
      type="button"
      onClick={async () => {
        try {
          await navigator.clipboard.writeText(text);
          setDone(true);
          setTimeout(() => setDone(false), 2000);
        } catch {
          /* ignore */
        }
      }}
      className="shrink-0 rounded-lg border border-slate-200 bg-white px-2 py-1 text-xs text-slate-600 shadow-sm hover:border-slate-300 hover:bg-slate-50"
    >
      {done ? "Copied" : "Copy"}
    </button>
  );
}

function CodeBlock({ title, code }) {
  return (
    <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
      <div className="flex items-center justify-between border-b border-slate-100 bg-slate-50/80 px-4 py-2">
        <span className="text-xs font-medium uppercase tracking-wide text-slate-500">{title}</span>
        <Copy text={code} />
      </div>
      <pre className="overflow-x-auto bg-slate-50 p-4 font-mono text-xs leading-relaxed text-slate-800 sm:text-sm">
        {code}
      </pre>
    </div>
  );
}

export function IntegrationDocsPage() {
  const { user } = useAuth();

  const base = getApiBase();
  const apiKeyPlaceholder = "YOUR_API_KEY";

  const authHeadersJson = useMemo(
    () =>
      JSON.stringify(
        {
          "Content-Type": "application/json",
          "x-api-key": apiKeyPlaceholder,
        },
        null,
        2
      ),
    [apiKeyPlaceholder]
  );

  const uploadEndpoint = useMemo(() => `POST ${base}/api/vectors/upload`, [base]);
  const uploadHeaders = useMemo(
    () => `x-api-key: ${apiKeyPlaceholder}\n(Multipart requests: do not set Content-Type yourself — curl -F sets it.)`,
    [apiKeyPlaceholder]
  );

  const uploadCurl = useMemo(
    () =>
      `curl -X POST "${base}/api/vectors/upload" \\\n  -H "x-api-key: ${apiKeyPlaceholder}" \\\n  -F "files=@/path/to/document.pdf" \\\n  -F "insert_to_rag=true"`,
    [base, apiKeyPlaceholder]
  );

  const queryEndpoint = useMemo(() => `POST ${base}/api/vectors/query`, [base]);
  const queryJson = useMemo(
    () =>
      JSON.stringify(
        {
          query_text: "What are the main findings?",
          top_k: 5,
          thread_id: "thread_abc123",
        },
        null,
        2
      ),
    []
  );

  const queryCurl = useMemo(
    () =>
      `curl -X POST "${base}/api/vectors/query" \\\n  -H "Content-Type: application/json" \\\n  -H "x-api-key: ${apiKeyPlaceholder}" \\\n  -d '${JSON.stringify({
        query_text: "What are the main findings?",
        top_k: 5,
        thread_id: "thread_abc123",
      })}'`,
    [base, apiKeyPlaceholder]
  );

  const queryFetch = useMemo(
    () =>
      `const res = await fetch("${base}/api/vectors/query", {\n  method: "POST",\n  headers: {\n    "Content-Type": "application/json",\n    "x-api-key": "${apiKeyPlaceholder}",\n  },\n  body: JSON.stringify({\n    query_text: "What are the main findings?",\n    top_k: 5,\n    thread_id: "thread_abc123",\n  }),\n});\nconst data = await res.json();`,
    [base, apiKeyPlaceholder]
  );

  const insertEndpoint = useMemo(() => `POST ${base}/api/vectors/insert`, [base]);
  const insertJson = useMemo(
    () =>
      JSON.stringify(
        {
          pdf_text: "Plain text content to embed…",
          metadata: {
            doc_id: "doc-001",
            title: "Example",
            filename: "example.pdf",
          },
        },
        null,
        2
      ),
    []
  );

  const insertCurl = useMemo(
    () =>
      `curl -X POST "${base}/api/vectors/insert" \\\n  -H "Content-Type: application/json" \\\n  -H "x-api-key: ${apiKeyPlaceholder}" \\\n  -d '${JSON.stringify({
        pdf_text: "Your text here",
        metadata: { doc_id: "doc-001", title: "Example" },
      })}'`,
    [base, apiKeyPlaceholder]
  );

  const insertFetch = useMemo(
    () =>
      `const res = await fetch("${base}/api/vectors/insert", {\n  method: "POST",\n  headers: {\n    "Content-Type": "application/json",\n    "x-api-key": "${apiKeyPlaceholder}",\n  },\n  body: JSON.stringify({\n    pdf_text: "Your text here",\n    metadata: {\n      doc_id: "doc-001",\n      title: "Example",\n      filename: "example.pdf",\n    },\n  }),\n});\nconst data = await res.json();`,
    [base, apiKeyPlaceholder]
  );

  return (
    <div>
      <nav className="mb-6 text-sm text-slate-500">
        <Link to="/dashboard" className="hover:text-violet-700">
          Projects
        </Link>
        <span className="mx-2">/</span>
        <span className="text-slate-700">Integration guide</span>
      </nav>

      <h1 className="font-[family-name:Outfit,sans-serif] text-3xl font-bold text-slate-900">
        Integration guide
      </h1>
      <p className="mt-2 max-w-2xl text-slate-600">
        Follow these steps to connect your app to the vector API. Base URL for this environment:{" "}
        <code className="rounded border border-slate-200 bg-slate-50 px-1.5 py-0.5 font-mono text-violet-800">
          {base}
        </code>
        . Dashboard user id (for non-vector dashboard calls):{" "}
        <code className="font-mono text-xs text-slate-600">{user?.id || "—"}</code>
      </p>

      <ol className="mt-10 list-decimal space-y-12 pl-5 marker:font-semibold marker:text-violet-700 sm:pl-6">
        <li className="pl-2">
          <h2 className="font-[family-name:Outfit,sans-serif] text-xl font-semibold text-slate-900">
            Get your API key
          </h2>
          <p className="mt-2 text-sm text-slate-600">
            Vector endpoints use a <strong className="font-medium text-slate-800">project API key</strong>, not
            your login JWT. Open{" "}
            <Link to="/dashboard" className="text-violet-700 underline decoration-violet-300 underline-offset-2">
              Projects
            </Link>
            , choose a project, then copy the key from the API key section. In every example below, replace{" "}
            <code className="rounded bg-slate-100 px-1 font-mono text-xs">{apiKeyPlaceholder}</code> with that key.
          </p>
          <p className="mt-3 text-sm text-slate-600">
            Send the key as an HTTP header on <em>every</em> vector request (shown in the next step). Organization
            and project scope come from this key—you do not pass org or project ids on upload/insert/query.
          </p>
        </li>

        <li className="pl-2">
          <h2 className="font-[family-name:Outfit,sans-serif] text-xl font-semibold text-slate-900">
            Send the API key on each request
          </h2>
          <p className="mt-2 text-sm text-slate-600">
            Use the <code className="font-mono text-emerald-800">x-api-key</code> header. For JSON bodies, also set{" "}
            <code className="font-mono text-xs text-slate-700">Content-Type: application/json</code>.
          </p>
          <div className="mt-4 space-y-3">
            <CodeBlock
              title="Headers (JSON APIs — copy and adapt)"
              code={authHeadersJson}
            />
          </div>
        </li>

        <li className="pl-2">
          <h2 className="font-[family-name:Outfit,sans-serif] text-xl font-semibold text-slate-900">
            Upload and ingest files
          </h2>
          <p className="mt-2 text-sm text-slate-600">
            Multipart form fields: <code className="text-xs">files</code> (one or more), optional{" "}
            <code className="text-xs">insert_to_rag</code>, optional <code className="text-xs">metadata</code> (JSON
            string). Scope matches your key, same as insert.
          </p>
          <div className="mt-4 space-y-3">
            <CodeBlock title="Endpoint (copy)" code={uploadEndpoint} />
            <CodeBlock title="Where to put the API key (header)" code={uploadHeaders} />
            <CodeBlock title="cURL (copy)" code={uploadCurl} />
          </div>
        </li>

        <li className="pl-2">
          <h2 className="font-[family-name:Outfit,sans-serif] text-xl font-semibold text-slate-900">
            Query (RAG chat)
          </h2>
          <p className="mt-2 text-sm text-slate-600">
            JSON body; <code className="text-xs">query_text</code> is required. Optional{" "}
            <code className="text-xs">thread_id</code>: use the same string across requests to continue a
            conversation when <code className="text-xs">history</code> is enabled on the server; omit or use a new
            id for a fresh thread.
          </p>
          <div className="mt-4 space-y-3">
            <CodeBlock title="Endpoint (copy)" code={queryEndpoint} />
            <CodeBlock title="Example body (JSON) — copy" code={queryJson} />
            <CodeBlock title="cURL (copy)" code={queryCurl} />
            <CodeBlock title="JavaScript fetch (copy)" code={queryFetch} />
          </div>
          <p className="mt-3 text-xs text-slate-500">
            In <code className="font-mono">fetch</code>, the API key goes in{" "}
            <code className="font-mono">headers[&quot;x-api-key&quot;]</code> (same value as in cURL).
          </p>
        </li>

        <li className="pl-2">
          <h2 className="font-[family-name:Outfit,sans-serif] text-xl font-semibold text-slate-900">
            Insert raw text
          </h2>
          <p className="mt-2 text-sm text-slate-600">
            JSON body must include <code className="text-xs">pdf_text</code> and{" "}
            <code className="text-xs">metadata.doc_id</code>. Add title, filename, or other metadata as needed.
          </p>
          <div className="mt-4 space-y-3">
            <CodeBlock title="Endpoint (copy)" code={insertEndpoint} />
            <CodeBlock title="Example body (JSON) — copy" code={insertJson} />
            <CodeBlock title="cURL (copy)" code={insertCurl} />
            <CodeBlock title="JavaScript fetch (copy)" code={insertFetch} />
          </div>
        </li>

        <li className="pl-2">
          <div className="rounded-2xl border border-violet-100 bg-violet-50/50 p-6">
            <h2 className="font-[family-name:Outfit,sans-serif] text-lg font-semibold text-violet-900">
              OpenAPI
            </h2>
            <p className="mt-1 text-sm text-slate-600">
              Interactive docs:{" "}
              <a
                href={`${base}/docs`}
                target="_blank"
                rel="noreferrer"
                className="text-violet-700 underline decoration-violet-300 underline-offset-2 hover:text-violet-900"
              >
                {base}/docs
              </a>
            </p>
          </div>
        </li>
      </ol>
    </div>
  );
}
