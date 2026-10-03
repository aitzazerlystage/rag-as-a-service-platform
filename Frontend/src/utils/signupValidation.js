/**
 * Client-side signup field rules (keep in sync with backend signup_login.py).
 */

const USERNAME_RE = /^[a-zA-Z][a-zA-Z0-9_-]{2,31}$/;

/** Printable ASCII without control characters */
function isPrintableAscii(str) {
  for (let i = 0; i < str.length; i++) {
    const c = str.charCodeAt(i);
    if (c < 32 || c > 126) return false;
  }
  return true;
}

function hasUnicodeLetter(ch) {
  return /\p{L}/u.test(ch);
}
function hasUnicodeNumber(ch) {
  return /\p{N}/u.test(ch);
}

export function isValidFullName(raw) {
  const t = raw.trim();
  if (t.length < 2 || t.length > 100) return false;
  let hasLetter = false;
  for (const ch of t) {
    if (hasUnicodeLetter(ch)) {
      hasLetter = true;
      continue;
    }
    if (ch === " " || ch === "-" || ch === "'" || ch === ".") continue;
    return false;
  }
  return hasLetter;
}

/** Collapse internal whitespace for consistent checks and display. */
export function collapseOrgWhitespace(raw) {
  return String(raw || "")
    .trim()
    .replace(/\s+/g, " ");
}

/** Names that look like placeholders or tests (lowercase, no spaces). */
const ORG_BLOCKLIST = new Set([
  "test",
  "tests",
  "testing",
  "asdf",
  "qwerty",
  "qwer",
  "abc",
  "abcd",
  "abcdef",
  "xxx",
  "foo",
  "bar",
  "sample",
  "demo",
  "demos",
  "placeholder",
  "none",
  "null",
  "random",
  "organization",
  "organisation",
  "org",
  "orgs",
  "company",
  "companies",
  "default",
  "admin",
  "username",
  "user",
  "idk",
  "lol",
  "lorem",
  "ipsum",
  "hello",
  "hey",
  "hi",
  "yes",
  "no",
  "ok",
  "okay",
  "stuff",
  "things",
  "thing",
  "aaa",
  "zzz",
  "blah",
  "whatever",
  "something",
  "anything",
  "nothing",
  "myorg",
  "mycompany",
  "neworg",
  "newcompany",
  "temp",
  "temporary",
  "trial",
  "na",
]);

function lettersOnlyLower(s) {
  return [...s].filter((ch) => hasUnicodeLetter(ch)).join("").toLowerCase();
}

function maxConsecutiveLetterRun(s) {
  let run = 0;
  let maxRun = 0;
  for (const ch of s) {
    if (hasUnicodeLetter(ch)) {
      run += 1;
      maxRun = Math.max(maxRun, run);
    } else {
      run = 0;
    }
  }
  return maxRun;
}

/** True if every letter in s is ASCII A–Z / a–z. */
function orgLettersAreAllAscii(s) {
  for (const ch of s) {
    if (hasUnicodeLetter(ch) && ch.codePointAt(0) > 127) return false;
  }
  return true;
}

export function isValidOrganizationName(raw) {
  const t = collapseOrgWhitespace(raw);
  if (t.length < 3 || t.length > 80) return false;

  const punct = "&.,'-()";
  let hasLetter = false;
  for (const ch of t) {
    if (hasUnicodeLetter(ch)) {
      hasLetter = true;
      continue;
    }
    if (hasUnicodeNumber(ch)) continue;
    if (ch === " " || punct.includes(ch)) continue;
    return false;
  }
  if (!hasLetter) return false;

  // At least one real word fragment (blocks "A 1", "x-y", "!!A!!")
  if (maxConsecutiveLetterRun(t) < 3) return false;

  const slug = t.toLowerCase();
  if (ORG_BLOCKLIST.has(slug)) return false;

  const compactLetters = lettersOnlyLower(t);
  if (compactLetters.length > 0 && ORG_BLOCKLIST.has(compactLetters)) return false;

  if (compactLetters.length >= 3 && /^(.)\1+$/.test(compactLetters)) return false;

  const letterCount = compactLetters.length;
  if (orgLettersAreAllAscii(t) && letterCount >= 4) {
    if (!/[aeiouy]/i.test(t)) return false;
  }

  return true;
}

export function isValidEmail(raw) {
  const email = raw.trim().toLowerCase();
  if (!email || email.length > 254) return false;
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return false;
  const at = email.indexOf("@");
  const local = email.slice(0, at);
  const domain = email.slice(at + 1);
  if (local.length > 64 || domain.length > 253) return false;
  if (domain.startsWith(".") || domain.endsWith(".") || domain.includes("..")) return false;
  return true;
}

export function isValidPassword(raw) {
  if (raw.length < 8 || raw.length > 128) return false;
  if (!isPrintableAscii(raw)) return false;
  if (raw !== raw.trim()) return false;
  const hasLetter = /[A-Za-z]/.test(raw);
  const hasDigit = /\d/.test(raw);
  return hasLetter && hasDigit;
}

export function isValidUsername(raw) {
  const u = raw.trim();
  return USERNAME_RE.test(u);
}

/**
 * @param {{ username: string, fullName: string, email: string, password: string, organizationName: string }} fields
 * @returns {{ ok: true } | { ok: false, errors: Record<string, string> }}
 */
export function validateSignupFields(fields) {
  const errors = {};

  if (!isValidUsername(fields.username)) {
    errors.username =
      "3–32 characters, start with a letter, then letters, numbers, underscore, or hyphen only.";
  }
  if (!isValidFullName(fields.fullName)) {
    errors.fullName =
      "2–100 characters, letters (any language), spaces, hyphen, apostrophe, or period. At least one letter.";
  }
  if (!isValidOrganizationName(fields.organizationName)) {
    errors.organizationName =
      "Use a real organization name (3–80 characters): include at least 3 letters in a row; " +
      "only letters, numbers, spaces, and & . , ' - ( ). Placeholder names (e.g. “test”, “asdf”) and gibberish are not allowed.";
  }
  if (!isValidEmail(fields.email)) {
    errors.email = "Enter a valid email address.";
  }
  if (!isValidPassword(fields.password)) {
    errors.password =
      "8–128 characters, letters and numbers required, ASCII printable only, no leading or trailing spaces.";
  }

  if (Object.keys(errors).length) return { ok: false, errors };
  return { ok: true };
}
