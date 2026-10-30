import { expect, test } from "@playwright/test";
import { signIn } from "./helpers";

// Synthetic fixture data only: FPT has statements, closes and sector insights; VCB has no statements.
test.beforeEach(async ({ context }) => signIn(context));

test("a ticker's profile gathers quick facts, valuation, events and sector insights", async ({ page }) => {
  await page.goto("/research/FPT");
  const facts = page.getByRole("region", { name: "Thông tin nhanh" });
  await expect(facts).toContainText("Vốn hoá");
  await expect(facts).toContainText("Cao / thấp 52 tuần");
  const valuation = page.getByRole("region", { name: "Định giá tham khảo" });
  await expect(valuation).toContainText("Đắt");
  await expect(valuation.getByRole("region", { name: "Phương án định giá FPT" })).toContainText("P/E lịch sử");
  await expect(page.getByRole("figure", { name: "P/E lịch sử FPT" })).toBeVisible();
  await expect(page.getByRole("region", { name: "Sự kiện" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Nhận định về ngành: Công nghệ Thông tin" })).toBeVisible();
  await expect(page.getByRole("button", { name: /^Mua/ })).toHaveCount(0);
});

test("ticker symbols on Định giá open the profile", async ({ page }) => {
  await page.goto("/fair-value");
  await page.getByRole("table", { name: "Định giá tham khảo" }).getByRole("link", { name: "FPT" }).click();
  await expect(page).toHaveURL(/\/research\/FPT$/);
  await expect(page.getByRole("region", { name: "Thông tin nhanh" })).toBeVisible();
});

test("a ticker without statements says what is missing", async ({ page }) => {
  await page.goto("/research/VCB");
  await expect(page.getByRole("region", { name: "Định giá tham khảo" })).toContainText("Chưa có báo cáo tài chính");
  await expect(page.getByRole("region", { name: "Thông tin nhanh" })).toContainText("—");
});

test("no horizontal scroll on a profile at 375px", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 900 });
  await page.goto("/research/FPT");
  await expect(page.getByRole("figure", { name: "P/E lịch sử FPT" })).toBeVisible();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(0);
});
