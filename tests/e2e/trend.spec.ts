import { expect, test } from "@playwright/test";
import { signIn } from "./helpers";

// Synthetic fixture snapshot only.
test.beforeEach(async ({ context }) => signIn(context));

async function openTrend(page: import("@playwright/test").Page) {
  await page.goto("/trend");
  await expect(page.getByText("Đang tải…")).toHaveCount(0);
}

test("the board shows MACD and RSI by frame and highlights what changed", async ({ page }) => {
  await openTrend(page);
  const fpt = page.getByRole("table", { name: "FPT" });
  await expect(fpt.getByRole("row", { name: /MACD/ })).toContainText("up,>0");
  await expect(fpt.getByRole("row", { name: /RSI/ })).toContainText("63");
  await expect(fpt).toContainText("trước: down,<0");
  await expect(fpt).toContainText("trước: trung tính");
  await expect(fpt).toContainText("Chưa có giá của phiên");
  await expect(page.getByRole("table", { name: "VN10Y" })).toContainText("Không có nguồn miễn phí hợp lệ");
  await expect(page.getByText(/so với phiên 2026-10-22/)).toBeVisible();
  await expect(page.getByText(/không phải khuyến nghị/)).toBeVisible();
});

test("no horizontal page scroll on the trend page at 375px", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 900 });
  await openTrend(page);
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(0);
});
