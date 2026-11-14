import { expect, test } from "@playwright/test";

test("every page answers with the protective headers, and a Google sign-in popup stays allowed", async ({ page }) => {
  const headers = (await page.goto("/login"))!.headers();
  expect(headers["x-frame-options"]).toBe("DENY");
  expect(headers["x-content-type-options"]).toBe("nosniff");
  expect(headers["referrer-policy"]).toBe("same-origin");
  expect(headers["permissions-policy"]).toContain("camera=()");
  expect(headers["cross-origin-opener-policy"]).toBe("same-origin-allow-popups");
});

test("pages carry an enforced content policy, do not name the framework, and the report address takes a report", async ({ page, request }) => {
  const errors: string[] = [];
  page.on("console", (m) => { if (m.type() === "error" && /Content.Security.Policy/i.test(m.text())) errors.push(m.text()); });
  const headers = (await page.goto("/login"))!.headers();
  expect(headers["content-security-policy"]).toContain("default-src 'self'");
  expect(headers["content-security-policy"]).toContain("frame-ancestors 'none'");
  expect(headers["content-security-policy"]).toContain("report-uri /api/csp-report");
  expect(headers["content-security-policy-report-only"]).toBeUndefined();
  expect(headers["x-powered-by"]).toBeUndefined();
  const r = await request.post("/api/csp-report", { headers: { "content-type": "application/csp-report" },
    data: JSON.stringify({ "csp-report": { "effective-directive": "img-src", "blocked-uri": "https://example.com/a.png", "document-uri": "http://127.0.0.1/login" } }) });
  expect(r.status()).toBe(204);
  expect(errors).toEqual([]);  // the login page itself breaks no rule
});

test("the busiest pages load under the enforced policy without a blocked script, style, image or call", async ({ page, context }) => {
  const { signIn } = await import("./helpers");
  await signIn(context);
  const errors: string[] = [];
  page.on("console", (m) => { if (/Content.Security.Policy/i.test(m.text())) errors.push(m.text()); });
  for (const path of ["/", "/funds", "/research/FPT", "/trend", "/macro", "/profile?tab=tai-san"]) {
    await page.goto(path);
    await expect(page.getByText("Đang tải…")).toHaveCount(0);
  }
  expect(errors).toEqual([]);
});
