import { expect, test } from "@playwright/test";
import { signIn } from "./helpers";

test.beforeEach(async ({ context }) => signIn(context));

test("the month summary opens from Danh mục & Giao dịch with the waterfall, the map and the goals, ready to print", async ({ page }) => {
  await page.goto("/portfolio");
  await page.getByRole("link", { name: "Bản tổng kết tháng để in" }).click();
  await expect(page).toHaveURL(/\/monthly/);
  await expect(page.getByRole("heading", { level: 1, name: /Tổng kết tháng/ })).toBeVisible();
  await expect(page.getByRole("region", { name: "Bản đồ danh mục" })).toBeVisible();
  await expect(page.getByRole("region", { name: "Thẻ điểm mục tiêu" })).toBeVisible();
  await expect(page.getByRole("button", { name: "In" })).toBeVisible();
  await page.emulateMedia({ media: "print" });
  await expect(page.getByRole("button", { name: "In" })).toBeHidden();
  await expect(page.getByRole("navigation", { name: "Điều hướng chính" })).toBeHidden();
});
