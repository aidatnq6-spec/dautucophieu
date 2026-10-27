import { expect, test } from "@playwright/test";
import { call, seedOwner, signIn } from "./helpers";

// Synthetic owner bought 100 FPT at 50.000 on 02/02/2026; the fixture has weekday closes to 30/04/2026 for FPT and VN-Index.
test.describe.configure({ mode: "serial" });
test.beforeEach(async ({ context }) => signIn(context));

async function openPerf(page: import("@playwright/test").Page) {
  await seedOwner(page);
  await page.goto("/portfolio");
  const box = page.getByRole("region", { name: "Hiệu quả danh mục" });
  await expect(box).toBeVisible();
  return box;
}

test("portfolio vs VN-Index rebased to 100, monthly returns and gains by ticker", async ({ page }) => {
  const box = await openPerf(page);
  await expect(box.getByRole("img", { name: /Danh mục và VN-Index/ })).toBeVisible();
  await expect(box).toContainText("Danh mục");
  await expect(box).toContainText("VN-Index");
  await expect(box.getByRole("table", { name: "Lợi nhuận theo tháng" })).toContainText("02/2026");
  await expect(box.getByRole("table", { name: "Lãi/lỗ theo giá vốn" }).getByRole("row", { name: /FPT/ })).toContainText(/[+−]/);
  await expect(box).toContainText("loại trừ tiền nạp/rút");
});

test("saving and inflation over the same period, and the real return after inflation", async ({ page }) => {
  await seedOwner(page);
  // Entered by hand here; in use CPI comes from news headlines and the deposit rate from Topi.
  expect((await call(page, "POST", "macro/vn_cpi_yoy/observations", { date: "2026-03-31", value: "3,2" })).ok()).toBe(true);
  expect((await call(page, "POST", "macro/deposit_12m/observations", { date: "2026-04-30", value: "5,6" })).ok()).toBe(true);
  const box = await openPerf(page);
  const rows = box.getByRole("list", { name: "So với gửi tiết kiệm và lạm phát" });
  await expect(rows).toContainText("Gửi tiết kiệm 12 tháng (5,6%/năm)");
  await expect(rows).toContainText("Lạm phát (CPI 3,2% so cùng kỳ, tháng 03/2026)");
  await expect(rows.getByTestId("real-return")).toHaveText(/^[+−]\d+,\d{2}%$/);
});

test("no horizontal scroll with the performance block at 375px", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 900 });
  await openPerf(page);
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(0);
});
