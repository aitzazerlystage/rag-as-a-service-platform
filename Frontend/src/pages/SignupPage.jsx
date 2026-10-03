import { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";
import { apiFetch, formBody, getApiBase } from "../api/client.js";
import { validateSignupFields, collapseOrgWhitespace } from "../utils/signupValidation.js";

const inputBase =
  "w-full rounded-xl border px-4 py-3 text-slate-900 outline-none placeholder:text-slate-400 focus:ring-2";
const inputDefault =
  "border-slate-200 bg-white ring-violet-500/30 focus:border-violet-300 focus:ring-violet-200";
const inputInvalid =
  "border-red-500 bg-rose-50/90 ring-red-200 focus:border-red-600 focus:ring-red-200";

function inputClassName(invalid) {
  return `${inputBase} ${invalid ? inputInvalid : inputDefault}`;
}

const labelBase = "mb-1.5 block text-xs font-medium uppercase tracking-wide";
function labelClassName(invalid) {
  return `${labelBase} ${invalid ? "text-red-700" : "text-slate-500"}`;
}

/** Field order for focusing the first invalid control after submit. */
const FIELD_ORDER = ["organizationName", "username", "fullName", "email", "password"];
const VALIDATION_BANNER = "Fix the highlighted fields, then try again.";
const FIELD_DOM_ID = {
  organizationName: "signup-field-organization",
  username: "signup-field-username",
  fullName: "signup-field-fullname",
  email: "signup-field-email",
  password: "signup-field-password",
};

/** Keeps browser password managers from treating this form like /login (email → “username”, saved password, etc.). */
const ac = (token) => `section-fileflow-signup ${token}`;

export function SignupPage() {
  const { setSession } = useAuth();
  const navigate = useNavigate();

  const [username, setUsername] = useState("");
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [organizationName, setOrganizationName] = useState("");
  const [error, setError] = useState("");
  const [fieldErrors, setFieldErrors] = useState({});
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (Object.keys(fieldErrors).length === 0) {
      setError((msg) => (msg === VALIDATION_BANNER ? "" : msg));
    }
  }, [fieldErrors]);

  function touchField(fieldKey, nextValueSetter) {
    return (e) => {
      nextValueSetter(e.target.value);
      setFieldErrors((prev) => {
        if (!prev[fieldKey]) return prev;
        const next = { ...prev };
        delete next[fieldKey];
        return next;
      });
    };
  }

  async function onSubmit(e) {
    e.preventDefault();
    setError("");
    setFieldErrors({});
    const trimmedUser = username.trim();
    const trimmedFull = fullName.trim();
    const trimmedEmail = email.trim();
    const normalizedOrg = collapseOrgWhitespace(organizationName);
    const validation = validateSignupFields({
      username: trimmedUser,
      fullName: trimmedFull,
      email: trimmedEmail,
      password,
      organizationName: normalizedOrg,
    });
    if (!validation.ok) {
      setFieldErrors(validation.errors);
      setError(VALIDATION_BANNER);
      queueMicrotask(() => {
        const firstKey = FIELD_ORDER.find((k) => validation.errors[k]);
        if (firstKey) document.getElementById(FIELD_DOM_ID[firstKey])?.focus();
      });
      return;
    }
    setLoading(true);
    try {
      const res = await apiFetch("/signup", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: formBody({
          username: trimmedUser,
          full_name: trimmedFull,
          email: trimmedEmail.toLowerCase(),
          password,
          organization_name: normalizedOrg,
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setFieldErrors({});
        let msg =
          typeof data.detail === "string"
            ? data.detail
            : Array.isArray(data.detail)
              ? data.detail.map((d) => d.msg || d).join("; ")
              : data.detail?.msg;
        setError(msg || `Signup failed (${res.status})`);
        return;
      }
      setSession(data);
      navigate("/dashboard", { replace: true });
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
            Create your workspace
          </h1>
          <p className="mt-1 text-sm text-slate-600">
            One organization · unlimited experimentation
          </p>
        </div>

        <form onSubmit={onSubmit} autoComplete="off" className="space-y-4">
          {error && (
            <div
              className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800"
              role="alert"
            >
              {error}
            </div>
          )}
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="sm:col-span-2">
              <label htmlFor={FIELD_DOM_ID.organizationName} className={labelClassName(!!fieldErrors.organizationName)}>
                Organization
              </label>
              <input
                id={FIELD_DOM_ID.organizationName}
                name="signup_organization"
                required
                maxLength={80}
                value={organizationName}
                onChange={touchField("organizationName", setOrganizationName)}
                className={inputClassName(!!fieldErrors.organizationName)}
                placeholder="Acme Research"
                autoComplete={ac("organization")}
                aria-invalid={fieldErrors.organizationName ? "true" : "false"}
                aria-describedby={fieldErrors.organizationName ? "err-organization" : undefined}
              />
              {fieldErrors.organizationName && (
                <p id="err-organization" className="mt-1 text-xs font-medium text-red-700">
                  {fieldErrors.organizationName}
                </p>
              )}
            </div>
            <div>
              <label htmlFor={FIELD_DOM_ID.username} className={labelClassName(!!fieldErrors.username)}>
                Username
              </label>
              <input
                id={FIELD_DOM_ID.username}
                name="signup_username"
                type="text"
                required
                maxLength={32}
                value={username}
                onChange={touchField("username", setUsername)}
                className={inputClassName(!!fieldErrors.username)}
                placeholder="e.g. jane_doe"
                autoComplete={ac("username")}
                aria-invalid={fieldErrors.username ? "true" : "false"}
                aria-describedby={fieldErrors.username ? "err-username" : undefined}
              />
              {fieldErrors.username && (
                <p id="err-username" className="mt-1 text-xs font-medium text-red-700">
                  {fieldErrors.username}
                </p>
              )}
            </div>
            <div>
              <label htmlFor={FIELD_DOM_ID.fullName} className={labelClassName(!!fieldErrors.fullName)}>
                Full name
              </label>
              <input
                id={FIELD_DOM_ID.fullName}
                name="signup_full_name"
                type="text"
                required
                maxLength={100}
                value={fullName}
                onChange={touchField("fullName", setFullName)}
                className={inputClassName(!!fieldErrors.fullName)}
                placeholder="Your name"
                autoComplete={ac("name")}
                aria-invalid={fieldErrors.fullName ? "true" : "false"}
                aria-describedby={fieldErrors.fullName ? "err-fullname" : undefined}
              />
              {fieldErrors.fullName && (
                <p id="err-fullname" className="mt-1 text-xs font-medium text-red-700">
                  {fieldErrors.fullName}
                </p>
              )}
            </div>
            <div className="sm:col-span-2">
              <label htmlFor={FIELD_DOM_ID.email} className={labelClassName(!!fieldErrors.email)}>
                Email
              </label>
              <input
                id={FIELD_DOM_ID.email}
                name="signup_email"
                type="email"
                required
                maxLength={254}
                value={email}
                onChange={touchField("email", setEmail)}
                className={inputClassName(!!fieldErrors.email)}
                placeholder="you@company.com"
                autoComplete={ac("email")}
                aria-invalid={fieldErrors.email ? "true" : "false"}
                aria-describedby={fieldErrors.email ? "err-email" : undefined}
              />
              {fieldErrors.email && (
                <p id="err-email" className="mt-1 text-xs font-medium text-red-700">
                  {fieldErrors.email}
                </p>
              )}
            </div>
            <div className="sm:col-span-2">
              <label htmlFor={FIELD_DOM_ID.password} className={labelClassName(!!fieldErrors.password)}>
                Password
              </label>
              <input
                id={FIELD_DOM_ID.password}
                name="signup_new_password"
                type="password"
                required
                minLength={8}
                maxLength={128}
                value={password}
                onChange={touchField("password", setPassword)}
                className={inputClassName(!!fieldErrors.password)}
                placeholder="8+ chars, letters and numbers"
                autoComplete={ac("new-password")}
                aria-invalid={fieldErrors.password ? "true" : "false"}
                aria-describedby={fieldErrors.password ? "err-password" : undefined}
              />
              {fieldErrors.password && (
                <p id="err-password" className="mt-1 text-xs font-medium text-red-700">
                  {fieldErrors.password}
                </p>
              )}
            </div>
          </div>
          <button
            type="submit"
            disabled={loading}
            className="mt-2 w-full rounded-xl bg-gradient-to-r from-violet-600 to-indigo-600 py-3.5 text-sm font-semibold text-white shadow-lg shadow-violet-500/20 disabled:opacity-60"
          >
            {loading ? "Creating account…" : "Create account"}
          </button>
        </form>

        <p className="mt-8 text-center text-sm text-slate-600">
          Already registered?{" "}
          <Link to="/login" className="font-medium text-violet-700 hover:text-violet-800">
            Log in
          </Link>
        </p>
      </div>
    </div>
  );
}
