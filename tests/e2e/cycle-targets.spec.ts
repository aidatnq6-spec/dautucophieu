import { expect, test } from "@playwright/test";
import { seedOwner, signIn } from "./helpers";

test.beforeEach(async ({ context }) => signIn(context));
const region = (page: import("@playwright/test").Page) => page.getByRole("region", { name: "Phân bổ mục tiêu theo chu kỳ" });

test("a mix must add up to 100%, and a saved one stays after a reload", async ({ page }) => {
  await seedOwner(page);
  await page.goto("/profile?tab=ke-hoach");
  const box = region(page);
  const cell = (phase: string, layer: string) => box.getByLabel(`${phase}: ${layer} (%)`);
  await expect(cell("Lãi suất giảm", "Cổ phiếu")).toBeEnabled();
  for (const [layer, value] of [["Tiền gửi", "40"], ["Trái phiếu", "10"], ["Vàng", "10"], ["Cổ phiếu", "30"], ["Tiền số", "5"]]) await cell("Lãi suất giảm", layer).fill(value);
  await box.getByRole("button", { name: "Lưu mục tiêu" }).click();
  await expect(box.getByRole("alert")).toContainText("Lãi suất giảm");
  await expect(box.getByRole("alert")).toContainText("100");
  await cell("Lãi suất giảm", "Cổ phiếu").fill("35");
  await box.getByRole("button", { name: "Lưu mục tiêu" }).click();
  await expect(box.getByRole("status").filter({ hasText: "Đã lưu" })).toBeVisible();
  await page.reload();
  await expect(cell("Lãi suất giảm", "Cổ phiếu")).toHaveValue("35");
});

test("the section adds no sideways scroll at 375px", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 800 });
  await page.goto("/profile?tab=ke-hoach");
  await expect(region(page).getByRole("button", { name: "Lưu mục tiêu" })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)).toBeLessThanOrEqual(0);
});
