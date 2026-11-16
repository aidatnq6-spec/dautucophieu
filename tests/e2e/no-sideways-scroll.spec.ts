import { expect, test } from "@playwright/test";
import { signIn } from "./helpers";

test.beforeEach(async ({ context }) => signIn(context));
// Every page, on a phone and on a wide screen: no box that scrolls sideways (tables read as cards on a phone, bars wrap).
const PAGES = ["/", "/portfolio", "/profile", "/macro", "/market", "/trend", "/value-chains", "/sectors", "/watchlist", "/fair-value", "/earnings", "/events",
  "/funds", "/insights", "/reports", "/loan", "/journal", "/settings", "/research/FPT", "/thesis/FPT", "/monthly"];
for (const width of [375, 1440]) {
  test(`no sideways scroll at ${width}px`, async ({ page }) => {
    test.setTimeout(240000);
    await page.setViewportSize({ width, height: 900 });
    const found: string[] = [];
    for (const path of PAGES) {
      await page.goto(path);
      await page.waitForLoadState("networkidle");
      const boxes = await page.evaluate(() => [...document.querySelectorAll("main *")].filter((el) => {
        const s = getComputedStyle(el);
        return (s.overflowX === "auto" || s.overflowX === "scroll") && el.scrollWidth > el.clientWidth + 2 && !el.closest("svg, canvas, [data-sideways-ok]");
      }).map((el) => el.querySelector("table")?.getAttribute("aria-label") ?? el.className));
      const whole = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1);
      found.push(...boxes.map((b) => `${path}: ${b}`), ...(whole ? [`${path}: the page`] : []));
    }
    expect(found).toEqual([]);
  });
}
