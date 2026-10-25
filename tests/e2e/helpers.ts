import type { Page } from "@playwright/test";

// Shared by browser specs. Synthetic data only; seeding is idempotent so specs run in any order.
const ORIGIN = "http://127.0.0.1:3100";

export async function call(page: Page, method: "GET" | "POST" | "PUT", path: string, data?: unknown) {
  const { csrfToken } = await (await page.request.get("/api/session")).json();
  return page.request.fetch(`/api/internal/${path}`, { method, data, headers: { "x-csrf-token": csrfToken, origin: ORIGIN } });
}

export async function seedOwner(page: Page) {
  if ((await call(page, "GET", "profile")).status() === 404) {
    const profile = { as_of: "2026-10-24", emergency_reserve: "0", assets: [{ asset_id: "cash", kind: "deposit", amount: "1000000000", liquidity: "liquid" }] };
    const preview = await (await call(page, "POST", "profile/assessment", { profile, ledger_value: null })).json();
    await call(page, "PUT", "profile", { profile, ledger_value: null, reviewed_net: preview.net, expected_version: 0, request_id: "seed-p" });
  }
  if ((await call(page, "GET", "risk")).status() === 404) {
    const answers = Array.from({ length: 13 }, (_, i) => ({ question: i + 1, answer: "C" }));
    await call(page, "PUT", "risk", { answers, confirmed_conflicts: [], expected_version: 0, request_id: "seed-r" });
  }
  const ledger = await (await call(page, "GET", "ledger")).json();
  if (!ledger.state.positions.some((p: { security_id: string }) => p.security_id === "FPT")) {
    await call(page, "POST", "ledger/events", { event: { event_id: "seed-d", type: "deposit", effective_at: "2026-02-01", sequence: 0, amount: "100000000" },
      expected_version: ledger.version, request_id: "seed-l1" });
    await call(page, "POST", "ledger/events", { event: { event_id: "seed-b", type: "buy", effective_at: "2026-02-02", sequence: 0, security_id: "FPT",
      quantity: 100, price: "50000", fee: "0", tax: "0" }, expected_version: ledger.version + 1, request_id: "seed-l2" });
  }
}

export async function signIn(context: import("@playwright/test").BrowserContext) {
  await context.addCookies([{ name: "investment_session", value: process.env.INVESTMENT_E2E_SESSION!, domain: "127.0.0.1", path: "/" }]);
}
