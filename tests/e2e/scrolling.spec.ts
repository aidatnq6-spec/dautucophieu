import { expect, test } from "@playwright/test";
import { seedOwner, signIn } from "./helpers";

// Long pages: the menu stays reachable, a back-to-top button appears once scrolled, and the scrollbar matches the app.
test.describe.configure({ mode: "serial" });
test.beforeEach(async ({ context }) => signIn(context));

const nav = (page: import("@playwright/test").Page) => page.getByRole("navigation", { name: "Điều hướng chính" });
// Synthetic data keeps pages short; stretch the content so the page really scrolls, then go to the bottom.
async function scrollToBottomOfALongPage(page: import("@playwright/test").Page) {
  await page.waitForLoadState("networkidle");  // stretch only after React has hydrated, so the test itself causes no mismatch
  await page.evaluate(() => { (document.querySelector("main") as HTMLElement).style.minHeight = "4000px"; window.scrollTo(0, document.body.scrollHeight); });
  await expect.poll(() => page.evaluate(() => window.scrollY)).toBeGreaterThan(2000);
}

test("the side menu stays in view at the bottom of a long page", async ({ page }) => {
  await seedOwner(page);
  await page.setViewportSize({ width: 1280, height: 700 });
  await page.goto("/portfolio");
  await scrollToBottomOfALongPage(page);
  await expect(nav(page).getByRole("link", { name: "Tổng quan" })).toBeInViewport();
  await expect(nav(page).getByRole("link", { name: "Danh mục & Giao dịch" })).toBeInViewport();
});

test("a back-to-top button appears after scrolling and returns to the top", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 700 });
  await page.goto("/portfolio");
  const up = page.getByRole("button", { name: "Lên đầu trang" });
  await expect(up).toBeHidden();
  await scrollToBottomOfALongPage(page);
  await expect(up).toBeVisible();
  await up.click();
  await expect.poll(() => page.evaluate(() => window.scrollY)).toBe(0);
  await expect(up).toBeHidden();
});

test("on a phone the menu bar stays at the top while scrolling, without horizontal scroll", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 760 });
  await page.goto("/portfolio");
  await scrollToBottomOfALongPage(page);
  await expect(nav(page).getByRole("link", { name: "Tổng quan" })).toBeInViewport();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(0);
});

test("the page scrollbar uses the app's colours", async ({ page }) => {
  await page.goto("/");
  const color = await page.evaluate(() => getComputedStyle(document.documentElement).scrollbarColor);
  expect(color).not.toBe("auto");
});
