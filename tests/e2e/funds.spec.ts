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
  await expect(table.getByRole("row", { name: /QCP/ })).toContainText("Quỹ duy nhất trong nhóm");  // alone in its kind: no score
  await board.getByRole("radio", { name: /Trái phiếu/ }).check();
  await expect(table.getByRole("row", { name: /QCP/ })).toHaveCount(0);
  await expect(board.getByTestId("fund-benchmark")).toContainText("VN-Index");
  await expect(page.getByRole("region", { name: "Quỹ của bạn theo nhóm" })).toContainText("Chưa có dòng quỹ nào");
  await expect(page.getByRole("region", { name: "Cổ phiếu bạn nắm qua quỹ" })).toContainText("Chưa có");  // the shared store has no fund row
});

test("Quỹ mở adds no sideways scroll at 375px", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 800 });
  await page.goto("/funds");
  await expect(page.getByRole("region", { name: "Bảng quỹ mở" })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)).toBeLessThanOrEqual(0);
});

test("Kiểm tra mua đỉnh places a fund among its kind, on Quỹ mở and while typing a fund row in Sổ tài sản", async ({ page }) => {
  await page.goto("/funds");
  const check = page.getByRole("region", { name: "Kiểm tra mua đỉnh" });
  await check.getByRole("combobox", { name: "Quỹ định mua" }).selectOption("QCP");
  await expect(check.getByTestId("fund-check")).toContainText("12 tháng +18,20%, cao thứ 1/1 quỹ cổ phiếu");
  await page.goto("/profile?tab=tai-san");
  const book = page.getByRole("region", { name: "Sổ tài sản" });
  await book.getByRole("button", { name: "Thêm dòng trái phiếu" }).click();
  await book.getByLabel("Mã quỹ").fill("qtp");
  await expect(book.getByTestId("fund-check")).toContainText("QTP 6 tháng —; 12 tháng +3,90%, cao thứ 1/1 quỹ trái phiếu");
});
