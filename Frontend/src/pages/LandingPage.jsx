import { Link } from "react-router-dom";

export function LandingPage() {
  return (
    <div className="mesh-bg min-h-screen flex flex-col">
      <header className="mx-auto flex w-full max-w-6xl items-center justify-between px-6 py-8">
        <span className="font-[family-name:Outfit,sans-serif] text-2xl font-bold tracking-tight bg-gradient-to-r from-violet-700 to-emerald-600 bg-clip-text text-transparent">
          FileFlow
        </span>
        <div className="flex gap-3">
          <Link
            to="/login"
            className="rounded-xl px-4 py-2 text-sm font-medium text-slate-600 hover:text-slate-900"
          >
            Log in
          </Link>
          <Link
            to="/signup"
            className="rounded-xl bg-gradient-to-r from-violet-600 to-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow-lg shadow-violet-500/20 hover:opacity-95"
          >
            Get started
          </Link>
        </div>
      </header>

      <section className="mx-auto flex max-w-6xl flex-1 flex-col items-center justify-center px-6 pb-24 text-center">
        <p className="mb-4 inline-flex items-center gap-2 rounded-full border border-violet-200/80 bg-white/80 px-4 py-1.5 text-xs font-medium uppercase tracking-wider text-violet-700 shadow-sm">
          RAG · Pinecone · LangGraph
        </p>
        <h1 className="font-[family-name:Outfit,sans-serif] max-w-3xl text-4xl font-extrabold leading-tight tracking-tight text-slate-900 sm:text-6xl">
          Ship document AI with a{" "}
          <span className="bg-gradient-to-r from-emerald-600 via-teal-600 to-violet-700 bg-clip-text text-transparent">
            production API
          </span>
        </h1>
        <p className="mt-6 max-w-xl text-lg text-slate-600">
          Upload PDFs, embed into vectors, and query with retrieval-augmented
          generation. Manage orgs, projects, and API keys from one console.
        </p>
        <div className="mt-10 flex flex-wrap items-center justify-center gap-4">
          <Link
            to="/signup"
            className="glow-ring rounded-2xl bg-gradient-to-r from-violet-600 to-indigo-600 px-8 py-3.5 text-base font-semibold text-white shadow-lg shadow-violet-500/20 hover:opacity-95"
          >
            Create free account
          </Link>
          <Link
            to="/login"
            className="rounded-2xl border border-slate-200 bg-white px-8 py-3.5 text-base font-medium text-slate-700 shadow-sm hover:border-slate-300 hover:bg-slate-50"
          >
            I have an account
          </Link>
        </div>

        <div className="mt-20 grid w-full max-w-4xl gap-4 sm:grid-cols-3">
          {[
            {
              t: "Projects",
              d: "Isolate namespaces per product or client.",
            },
            {
              t: "API keys",
              d: "Issue keys bound to org and project scope.",
            },
            {
              t: "Integration",
              d: "Copy-paste upload & query examples.",
            },
          ].map((x, i) => (
            <div
              key={x.t}
              className="glass animate-float rounded-2xl p-6 text-left"
              style={{ animationDelay: `${i * 0.15}s` }}
            >
              <h3 className="font-[family-name:Outfit,sans-serif] text-lg font-semibold text-slate-900">
                {x.t}
              </h3>
              <p className="mt-2 text-sm leading-relaxed text-slate-600">{x.d}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
