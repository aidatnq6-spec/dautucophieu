/**
 * Content-Security-Policy, enforced (14/11/2026) after a week and more of report-only use left logs/csp-report.log empty. The browser
 * still reports what it blocks to /api/csp-report, one line per report in logs/csp-report.log. CSP_REPORT_ONLY=1 in .env.local sends
 * it as Content-Security-Policy-Report-Only again (next.config.ts).
 *
 * Scripts and styles stay 'unsafe-inline' for now: Next.js and the theme script are inline. What the policy closes is loading code,
 * frames or plugins from anywhere other than this site and Google sign-in, and being framed by another site.
 */
const GOOGLE_SIGN_IN = ["https://apis.google.com", "https://www.gstatic.com"];

export function contentSecurityPolicy(dev: boolean): string {
  return [
    "default-src 'self'",
    `script-src 'self' 'unsafe-inline'${dev ? " 'unsafe-eval'" : ""} ${GOOGLE_SIGN_IN.join(" ")}`,
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data: blob: https://*.googleusercontent.com",
    "font-src 'self' data:",
    "connect-src 'self' https://*.googleapis.com https://*.firebaseio.com https://apis.google.com",
    "frame-src https://*.firebaseapp.com https://accounts.google.com https://apis.google.com",
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "frame-ancestors 'none'",
    "report-uri /api/csp-report",
  ].join("; ");
}

type Report = Record<string, unknown>;

function origin(raw: unknown): string | null {
  if (typeof raw !== "string" || !raw) return null;
  if (!/^[a-z][a-z0-9+.-]*:/i.test(raw)) return raw.slice(0, 20).replace(/[^a-z-]/gi, "") || null;  // "inline", "eval", "self"
  try { const u = new URL(raw); return u.origin !== "null" ? u.origin : u.protocol.replace(":", ""); } catch { return null; }
}

function page(raw: unknown): string {
  try { return new URL(String(raw)).pathname.slice(0, 80); } catch { return "?"; }
}

/** One log line from a browser report (old "csp-report" or newer Reporting API format): the directive, only the origin of what was
 * blocked and the page's path. No query strings, no code samples: they could hold personal figures. */
export function cspReportLine(body: unknown, at: string): string | null {
  const first = Array.isArray(body) ? body[0] : body;
  if (!first || typeof first !== "object") return null;
  const old = (first as Report)["csp-report"] as Report | undefined;
  const now = (first as Report).type === "csp-violation" ? ((first as Report).body as Report | undefined) : undefined;
  const r = old ?? now;
  if (!r || typeof r !== "object") return null;
  const directive = String(r["effective-directive"] ?? r["violated-directive"] ?? r.effectiveDirective ?? "").split(" ")[0].replace(/[^a-z-]/gi, "");
  if (!directive) return null;
  const blocked = origin(r["blocked-uri"] ?? r.blockedURL) ?? "?";
  return `${at} ${directive} ${blocked} page=${page(r["document-uri"] ?? r.documentURL)}`;
}
