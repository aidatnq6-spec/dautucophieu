import { expect, test } from "@playwright/test";
import { seedOwner, signIn } from "./helpers";

// Synthetic owner holds FPT (bought 02/02/2026); the fixture has stored FPT closes in trend-sources.
test.describe.configure({ mode: "serial" });
test.beforeEach(async ({ context }) => signIn(context));

test("Danh mục shows the peak gain and what went back for each holding, without advice", async ({ page }) => {
  await seedOwner(page);
  await page.goto("/portfolio");
  const box = page.getByRole("region", { name: "Lãi đã trả lại thị trường" });
  await expect(box.getByRole("table", { name: "Lãi đã trả lại theo mã" }).getByRole("row", { name: /FPT/ })).toBeVisible();
  await expect(box).toContainText("Chưa nhắc: đặt hai ngưỡng trong Cài đặt");
  await expect(box).toContainText("không phải khuyến nghị");
});

test("a spending goal is added and can be closed", async ({ page }) => {
  await page.goto("/portfolio");
  const box = page.getByRole("region", { name: "Lãi đã trả lại thị trường" });
  await box.getByLabel("Tên mục tiêu").fill("Mua xe e2e");
  await box.getByLabel("Số tiền (đ)").fill("1000000");
  await box.getByRole("button", { name: "Thêm mục tiêu" }).click();
  const row = box.getByRole("table", { name: "Các mục tiêu" }).getByRole("row", { name: /Mua xe e2e/ });
  await expect(row).toContainText("1.000.000 đ");
  await row.getByRole("button", { name: "Bỏ mục tiêu" }).click();
  await expect(row).toContainText("Đã bỏ ngày");
});

test("the two thresholds are set together in Cài đặt", async ({ page }) => {
  await page.goto("/settings");
  const first = page.getByLabel("Lãi đã trả lại: mã từng lãi ít nhất (% giá vốn)");
  await expect(first).toHaveValue("");
  await first.fill("30");
  await page.getByRole("button", { name: "Lưu ngưỡng" }).click();
  await expect(page.getByRole("status").filter({ hasText: "nhập cả hai ngưỡng" })).toBeVisible();
});

test("no horizontal scroll with the giveback block at 375px", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 900 });
  await page.goto("/portfolio");
  await expect(page.getByRole("region", { name: "Lãi đã trả lại thị trường" })).toBeVisible();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(0);
});
