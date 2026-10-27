import { expect, test } from "@playwright/test";
import { seedOwner, signIn } from "./helpers";

// Long pages get a strip of shortcuts to their sections, built from the section headings; short pages get none.
test.describe.configure({ mode: "serial" });
test.beforeEach(async ({ context }) => signIn(context));

const jumps = (page: import("@playwright/test").Page) => page.getByRole("navigation", { name: "Trên trang này" });

test("Danh mục lists its sections and a shortcut scrolls to one", async ({ page }) => {
  await seedOwner(page);
  await page.setViewportSize({ width: 1280, height: 700 });
  await page.goto("/portfolio");
  const strip = jumps(page);
  await expect(strip.getByRole("button", { name: "Phân bổ và rủi ro tập trung" })).toBeVisible();
  await expect(strip.getByRole("button", { name: "Sổ giao dịch" })).toBeVisible();
  await strip.getByRole("button", { name: "Sổ giao dịch" }).click();
  await expect(page.getByRole("heading", { level: 2, name: "Sổ giao dịch" })).toBeInViewport();
  await expect.poll(() => page.evaluate(() => window.scrollY)).toBeGreaterThan(0);
});

test("a page with fewer than three sections has no shortcut strip", async ({ page }) => {
  await page.goto("/journal");
  await expect(page.getByRole("form", { name: "Ghi lý do đang giữ" })).toBeVisible();
  await expect(jumps(page)).toHaveCount(0);
});

test("on a phone the shortcut lands below the sticky menu bar, with no horizontal scroll", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 760 });
  await page.goto("/settings");
  await jumps(page).getByRole("button", { name: "Telegram" }).click();
  const heading = page.getByRole("heading", { level: 2, name: "Telegram" });
  await expect(heading).toBeInViewport();
  const [headingTop, barBottom] = await Promise.all([
    heading.evaluate((h) => h.getBoundingClientRect().top),
    page.locator("aside.side").evaluate((a) => a.getBoundingClientRect().bottom),
  ]);
  expect(headingTop).toBeGreaterThanOrEqual(barBottom - 1);
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(0);
});
