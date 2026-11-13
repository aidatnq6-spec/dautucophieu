import { expect, test } from "@playwright/test";
import { signIn } from "./helpers";

test.beforeEach(async ({ context }) => signIn(context));

test("Quỹ mở lists the funds by kind with their returns, and an empty split before any fund row", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("navigation", { name: "Điều hướng chính" }).getByRole("link", { name: "Quỹ mở" }).click();
  await expect(page).toHaveURL(/\/funds/);
  const board = page.getByRole("region", { name: "Bảng quỹ mở" });
  const table = board.getByRole("table", { name: "Danh sách quỹ mở" });
  await expect(table.getByRole("row", { name: /QCP/ })).toContainText("+18,20%");
  await expect(table.getByRole("row", { name: /QTP/ })).toContainText("Trái phiếu");
  await board.getByRole("radio", { name: /Trái phiếu/ }).check();
  await expect(table.getByRole("row", { name: /QCP/ })).toHaveCount(0);
  await expect(board.getByTestId("fund-benchmark")).toContainText("VN-Index");
  await expect(page.getByRole("region", { name: "Quỹ của bạn theo nhóm" })).toContainText("Chưa có dòng quỹ nào");
});

test("Quỹ mở adds no sideways scroll at 375px", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 800 });
  await page.goto("/funds");
  await expect(page.getByRole("region", { name: "Bảng quỹ mở" })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)).toBeLessThanOrEqual(0);
});
