import { expect, test } from "@playwright/test";
import { seedOwner, signIn } from "./helpers";

test.beforeEach(async ({ context }) => signIn(context));

test("pages are titled as the menu names them", async ({ page }) => {
  await page.goto("/settings");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Cài đặt");
  await page.goto("/portfolio");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Danh mục & Giao dịch");
});

test("on a phone the theme choice lives in Cài đặt, on a computer in the sidebar only", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 800 });
  await page.goto("/");
  await expect(page.getByRole("navigation", { name: "Điều hướng chính" })).toBeVisible();
  await expect(page.getByRole("group", { name: "Giao diện" })).toHaveCount(0);
  await page.goto("/settings");
  const pick = page.getByRole("group", { name: "Giao diện" });
  await expect(pick).toHaveCount(1);
  await pick.getByRole("button", { name: "Tối" }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await page.setViewportSize({ width: 1440, height: 800 });
  await expect(page.getByRole("group", { name: "Giao diện" })).toHaveCount(1);
});

test("a box for a short number does not stretch across the page", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 800 });
  await page.goto("/settings");
  const box = await page.getByLabel("Phí mua/bán (% giá trị lệnh)").boundingBox();
  expect(box!.width).toBeLessThanOrEqual(280);
});

test("a system problem is labelled as such, not as a decision", async ({ page }) => {
  await seedOwner(page);
  await page.goto("/");
  const line = page.getByRole("region", { name: "Cần để ý" }).locator("li").filter({ hasText: "Giá VN-Index" });
  await expect(line.locator(".pill")).toHaveText("Hệ thống");
  await expect(line.getByRole("link")).not.toContainText("Hệ thống ·");
});

test("small print stays readable and links are easy to tap on a phone", async ({ page }) => {
  await page.goto("/trend");
  await expect(page.locator(".tb-when").first()).toHaveCSS("font-size", "11px");
  await page.setViewportSize({ width: 375, height: 800 });
  await page.goto("/watchlist");
  const link = page.locator("main a", { hasText: "FPT" }).first();
  const area = await link.evaluate((a) => { const s = getComputedStyle(a, "::after"); return [s.position, s.top, s.bottom]; });
  expect(area).toEqual(["absolute", "-6px", "-6px"]);  // the tap area reaches past the text without moving anything
});
