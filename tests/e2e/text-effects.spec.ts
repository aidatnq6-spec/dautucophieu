import { expect, test } from "@playwright/test";
import { signIn } from "./helpers";

// Three approved text effects (colorion text-effects, MIT): brand gradient, loading shimmer, glow on changed trend cells.
test.beforeEach(async ({ context }) => signIn(context));

const animation = (sel: string) => (page: import("@playwright/test").Page) =>
  page.locator(sel).first().evaluate((el) => getComputedStyle(el).animationName);

test("the brand drifts, changed trend cells glow briefly, loading text shimmers", async ({ page }) => {
  await page.route("**/api/internal/trend", async (route) => { await new Promise((r) => setTimeout(r, 600)); await route.continue(); });
  await page.goto("/trend");
  const loading = 'p.fx-loading:text-is("Đang tải…")';  // the MACD/RSI board's; the price board has its own loading lines
  await expect(page.locator(loading)).toHaveCount(1);
  expect(await animation(loading)(page)).toBe("fx-shimmer");
  await expect(page.locator(loading)).toHaveCount(0);
  expect(await animation(".brand span")(page)).toBe("fx-aurora");
  expect(await animation(".trend-table td.changed")(page)).toBe("fx-glow");
  const iterations = await page.locator(".trend-table td.changed").first().evaluate((el) => getComputedStyle(el).animationIterationCount);
  expect(iterations).toBe("3");  // a few pulses on open, then still
});

test("with reduced motion every effect stays still", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/trend");
  await expect(page.locator(".trend-table td.changed").first()).toBeVisible();
  expect(await animation(".brand span")(page)).toBe("none");
  expect(await animation(".trend-table td.changed")(page)).toBe("none");
  await expect(page.locator(".brand span")).toHaveCSS("color", "rgb(36, 94, 219)");  // plain brand blue, still readable
});
