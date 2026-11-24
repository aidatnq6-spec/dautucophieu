import { expect, test } from "@playwright/test";
import { seedOwner, signIn } from "./helpers";

// Synthetic owner holds FPT from one buy (02/02/2026): one open holding period, no pyramid to compare.
test.describe.configure({ mode: "serial" });
test.beforeEach(async ({ context }) => signIn(context));

test("a suggested basket is created and the FPT period tagged into it", async ({ page }) => {
  await seedOwner(page);
  await page.goto("/portfolio");
  const box = page.getByRole("region", { name: "Giỏ chiến lược" });
  await box.getByRole("button", { name: "+ Dài hạn" }).click();
  await expect(box.getByRole("status").filter({ hasText: "Đã tạo giỏ «Dài hạn»" })).toBeVisible();
  await box.getByRole("combobox", { name: /Giỏ của FPT/ }).selectOption({ label: "Dài hạn" });
  await expect(box.getByRole("status").filter({ hasText: "Đã gắn giỏ." })).toBeVisible();
  const result = box.getByRole("table", { name: "Kết quả theo giỏ" }).getByRole("row", { name: /Dài hạn/ });
  await expect(result).toContainText("0 / 1");
  await expect(box).toContainText("không phải khuyến nghị");
});

test("a basket's own drawdown level is saved and shown under the holding in Kế hoạch sụt giảm", async ({ page }) => {
  await page.goto("/portfolio");
  const box = page.getByRole("region", { name: "Giỏ chiến lược" });
  const levels = box.getByRole("table", { name: "Ngưỡng nhắc theo giỏ" });
  await levels.getByRole("combobox", { name: "Sụt giảm của giỏ Dài hạn" }).selectOption({ label: "Riêng" });
  await levels.getByLabel("Ngưỡng (%)").fill("96");
  await levels.getByRole("button", { name: "Lưu" }).click();
  await expect(levels.getByRole("alert")).toContainText("từ 1% đến 95%");
  await levels.getByLabel("Ngưỡng (%)").fill("12");
  await levels.getByRole("button", { name: "Lưu" }).click();
  await expect(box.getByRole("status").filter({ hasText: "Đã lưu ngưỡng nhắc của giỏ «Dài hạn»" })).toBeVisible();
  await page.reload();
  const drawdown = page.getByRole("region", { name: "Kế hoạch sụt giảm" });
  await expect(drawdown.getByRole("table", { name: "Sụt giảm theo mã" }).getByRole("row", { name: /FPT/ })).toContainText("ngưỡng giỏ Dài hạn: 12%");
  const back = page.getByRole("region", { name: "Giỏ chiến lược" }).getByRole("table", { name: "Ngưỡng nhắc theo giỏ" });
  await back.getByRole("combobox", { name: "Sụt giảm của giỏ Dài hạn" }).selectOption({ label: "Mức chung" });
  await back.getByRole("button", { name: "Lưu" }).click();
  await expect(page.getByRole("status").filter({ hasText: "Đã lưu ngưỡng nhắc của giỏ «Dài hạn»" })).toBeVisible();
});

test("Hậu kiểm shows the pyramid section without advice", async ({ page }) => {
  await page.goto("/journal");
  const box = page.getByRole("region", { name: "Hậu kiểm quyết định" });
  await expect(box.getByRole("heading", { name: "Hình tháp khi mua thêm" })).toBeVisible();
  await expect(box).toContainText("Chỉ mô tả hình dạng, không chấm điểm.");
});

test("no horizontal scroll with the baskets block at 375px", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 900 });
  await page.goto("/portfolio");
  await expect(page.getByRole("region", { name: "Giỏ chiến lược" })).toBeVisible();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(0);
});
