import { Link } from "react-router-dom";

const items = [
  {
    q: "Where do I get an API key?",
    a: "Open a project from the dashboard and use “Generate API key” (or “Create a new API key” if you already have one). The key stays visible on that project page while you’re signed in and is scoped to that project and organization.",
  },
  {
    q: "How do I call upload and query?",
    a: "See API reference for curl examples. Upload uses multipart form data with your file; query sends JSON with query_text. Authenticate with the x-api-key header.",
  },
  {
    q: "Why is my usage chart empty?",
    a: "Usage is recorded when your API key hits vector endpoints (query, insert, upload pipeline). Generate traffic with that key, then refresh the Usage page.",
  },
  {
    q: "What does “characters” mean in usage?",
    a: "The backend stores character counts per request for billing-style metrics (input/output/total). They track load alongside subscription token counters.",
  },
];

export function FaqPage() {
  return (
    <div>
      <nav className="mb-6 text-sm text-slate-500">
        <Link to="/dashboard" className="hover:text-violet-700">
          Projects
        </Link>
        <span className="mx-2">/</span>
        <span className="text-slate-700">FAQ</span>
      </nav>

      <h1 className="font-[family-name:Outfit,sans-serif] text-3xl font-bold text-slate-900">
        FAQ
      </h1>
      <p className="mt-1 text-slate-600">Quick answers about FileFlow console and APIs.</p>

      <ul className="mt-8 space-y-4">
        {items.map((item) => (
          <li key={item.q} className="glass rounded-2xl p-6">
            <h2 className="font-[family-name:Outfit,sans-serif] text-lg font-semibold text-slate-900">
              {item.q}
            </h2>
            <p className="mt-2 text-sm leading-relaxed text-slate-600">{item.a}</p>
          </li>
        ))}
      </ul>

      <p className="mt-8 text-center text-sm text-slate-500">
        Full OpenAPI docs:{" "}
        <a
          href={`${import.meta.env.VITE_API_URL || "http://localhost:8001"}/docs`}
          target="_blank"
          rel="noreferrer"
          className="text-violet-700 hover:text-violet-900 hover:underline"
        >
          /docs
        </a>
      </p>
    </div>
  );
}
