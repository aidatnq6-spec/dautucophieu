import { describe, expect, it } from "vitest";
import { contentSecurityPolicy, cspReportLine } from "./csp";

describe("contentSecurityPolicy", () => {
  it("allows this site and Google sign-in, nothing else, and reports what it would block", () => {
    const p = contentSecurityPolicy(false);
    expect(p).toContain("default-src 'self'");
    expect(p).toContain("object-src 'none'");
    expect(p).toContain("frame-ancestors 'none'");
    expect(p).toContain("https://apis.google.com");
    expect(p).toMatch(/frame-src [^;]*https:\/\/\*\.firebaseapp\.com/);
    expect(p).toMatch(/connect-src [^;]*https:\/\/\*\.googleapis\.com/);
    expect(p).toContain("report-uri /api/csp-report");
    expect(p).not.toContain("unsafe-eval");
    expect(contentSecurityPolicy(true)).toContain("'unsafe-eval'");  // next dev needs it
  });
});

describe("cspReportLine", () => {
  it("keeps the directive and only the origin of what was blocked, never a path or query", () => {
    const line = cspReportLine({ "csp-report": { "effective-directive": "script-src-elem", "blocked-uri": "https://evil.example/x.js?token=abc", "document-uri": "http://127.0.0.1:3000/portfolio?x=1" } }, "2026-11-10T10:00:00Z");
    expect(line).toBe("2026-11-10T10:00:00Z script-src-elem https://evil.example page=/portfolio");
  });
  it("reads the newer report format and names inline code without its content", () => {
    expect(cspReportLine([{ type: "csp-violation", body: { effectiveDirective: "script-src", blockedURL: "inline", documentURL: "http://127.0.0.1:3000/" } }], "t"))
      .toBe("t script-src inline page=/");
  });
  it("ignores anything that is not a report", () => {
    expect(cspReportLine({ hello: 1 }, "t")).toBeNull();
    expect(cspReportLine("x", "t")).toBeNull();
  });
});
