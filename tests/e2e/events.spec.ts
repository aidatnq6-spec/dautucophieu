import { expect, test } from "@playwright/test";
import { seedOwner, signIn } from "./helpers";

// Synthetic events: FPT (held by seedOwner) cash dividend in 3 days, VCB meeting in 10 days, an FPT insider deal 2 days ago.
test.describe.configure({ mode: "serial" });
test.beforeEach(async ({ context }) => signIn(context));

test("upcoming events by date with held tickers marked; insider deals kept apart", async ({ page }) => {
  await seedOwner(page);
  await page.goto("/events");
  const upcoming = page.getByRole("table", { name: "Sự kiện sắp tới" });
  await expect(upcoming.getByRole("row").nth(1)).toContainText("FPT");
  await expect(upcoming.getByRole("row").nth(1)).toContainText("Đang nắm");
  await expect(upcoming.getByRole("row").nth(1)).toContainText("2.000 đ/cp");
  await expect(upcoming).toContainText("ĐHĐCĐ bất thường 2026");
  await expect(page.getByText(/nhắc qua Telegram trước 5 ngày/)).toBeVisible();
  await expect(page.getByText("Nguyễn Văn A - Đăng kí Mua 10,000 FPT")).toBeHidden();
  await page.getByRole("button", { name: /giao dịch nội bộ/ }).click();
  await expect(page.getByText("Nguyễn Văn A - Đăng kí Mua 10,000 FPT")).toBeVisible();
  await expect(page.getByRole("navigation", { name: "Điều hướng chính" }).getByRole("link", { name: "Lịch sự kiện" })).toBeVisible();
});

test("no horizontal scroll on the events page at 375px", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 900 });
  await page.goto("/events");
  await expect(page.getByRole("table", { name: "Sự kiện sắp tới" })).toBeVisible();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(0);
});
