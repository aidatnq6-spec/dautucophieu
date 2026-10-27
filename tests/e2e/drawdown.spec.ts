import { expect, test } from "@playwright/test";
import { seedOwner, signIn } from "./helpers";

// Synthetic owner holds FPT; the fixture has weekday closes for FPT and VN-Index from 02/2026.
test.describe.configure({ mode: "serial" });
test.beforeEach(async ({ context }) => signIn(context));

test("Danh mục shows the deepest fall, the fall now and price against cost for VN-Index and each holding", async ({ page }) => {
  await seedOwner(page);
  await page.goto("/portfolio");
  const box = page.getByRole("region", { name: "Kế hoạch sụt giảm" });
  const table = box.getByRole("table", { name: "Sụt giảm theo mã" });
  await expect(table.getByRole("row", { name: /VN-Index/ })).toBeVisible();
  await expect(table.getByRole("row", { name: /FPT/ })).toContainText(/[+−]\d+,\d%/);
  await expect(box).toContainText("ngưỡng 30% dưới giá vốn");
  await expect(box).toContainText("không phải khuyến nghị");
});

test("the threshold is set in Cài đặt", async ({ page }) => {
  await page.goto("/settings");
  await expect(page.getByLabel("Kế hoạch sụt giảm: nhắc khi giá thấp hơn giá vốn (%)")).toHaveValue("30");
});

test("no horizontal scroll with the drawdown block at 375px", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 900 });
  await page.goto("/portfolio");
  await expect(page.getByRole("region", { name: "Kế hoạch sụt giảm" })).toBeVisible();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(0);
});
