import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";

export function ProfilePage() {
  const { user, organization, subscription } = useAuth();

  return (
    <div>
      <nav className="mb-6 text-sm text-slate-500">
        <Link to="/dashboard" className="hover:text-violet-700">
          Projects
        </Link>
        <span className="mx-2">/</span>
        <span className="text-slate-700">Profile</span>
      </nav>

      <h1 className="font-[family-name:Outfit,sans-serif] text-3xl font-bold text-slate-900">
        Profile
      </h1>
      <p className="mt-1 text-slate-600">Your account and organization details.</p>

      <div className="mt-8 grid gap-6 sm:grid-cols-2">
        <section className="glass rounded-2xl p-6">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            User
          </h2>
          <dl className="mt-4 space-y-3 text-sm">
            <div>
              <dt className="text-slate-500">Name</dt>
              <dd className="font-medium text-slate-900">{user?.full_name || "—"}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Username</dt>
              <dd className="font-mono text-slate-800">{user?.username || "—"}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Email</dt>
              <dd className="text-slate-700">{user?.email || "—"}</dd>
            </div>
            <div>
              <dt className="text-slate-500">User ID</dt>
              <dd className="break-all font-mono text-xs text-slate-500">{user?.id}</dd>
            </div>
          </dl>
        </section>

        <section className="glass rounded-2xl p-6">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Organization
          </h2>
          {organization ? (
            <dl className="mt-4 space-y-3 text-sm">
              <div>
                <dt className="text-slate-500">Name</dt>
                <dd className="font-medium text-slate-900">{organization.name}</dd>
              </div>
              <div>
                <dt className="text-slate-500">Organization ID</dt>
                <dd className="break-all font-mono text-xs text-slate-500">{organization.id}</dd>
              </div>
            </dl>
          ) : (
            <p className="mt-4 text-sm text-slate-500">No organization linked.</p>
          )}
        </section>

        <section className="glass rounded-2xl p-6 sm:col-span-2">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Subscription (quotas)
          </h2>
          {subscription ? (
            <dl className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3 text-sm">
              <div>
                <dt className="text-slate-500">Plan</dt>
                <dd className="font-medium capitalize text-violet-800">{subscription.plan}</dd>
              </div>
              <div>
                <dt className="text-slate-500">Query limit</dt>
                <dd className="text-slate-800">
                  {subscription.limit_queries != null
                    ? subscription.limit_queries.toLocaleString()
                    : "—"}
                </dd>
              </div>
              <div>
                <dt className="text-slate-500">Ingest limit</dt>
                <dd className="text-slate-800">
                  {subscription.limit_ingest != null
                    ? subscription.limit_ingest.toLocaleString()
                    : "—"}
                </dd>
              </div>
            </dl>
          ) : (
            <p className="mt-4 text-sm text-slate-500">
              Sign in again to refresh subscription info, or check the database if missing.
            </p>
          )}
        </section>
      </div>
    </div>
  );
}
