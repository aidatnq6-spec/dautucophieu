import { expect, test } from "@playwright/test";
import { seedOwner, signIn } from "./helpers";

// Capital needed for a monthly income at an assumed rate, income today, and time to the goal with monthly contributions.
test.describe.configure({ mode: "serial" });
test.beforeEach(async ({ context }) => signIn(context));

test("a monthly income goal shows the capital needed and the estimate, in today's money", async ({ page }) => {
  await seedOwner(page);
  await page.goto("/profile");
  const box = page.getByRole("region", { name: "Mục tiêu dòng tiền thụ động" });
  await expect(box.getByLabel("Dòng tiền mong muốn mỗi tháng (đ)")).toBeEnabled();
  await box.getByLabel("Dòng tiền mong muốn mỗi tháng (đ)").fill("");
  await box.getByLabel("Dòng tiền mong muốn mỗi tháng (đ)").pressSequentially("10000000");
  await box.getByLabel("Tỷ suất dòng tiền giả định (%/năm)").fill("6");
  await box.getByRole("button", { name: "Tính mục tiêu" }).click();
  await expect(box.getByTestId("pi-required")).toHaveText("2.000.000.000 đ");  // 10 tr × 12 / 6%
  await expect(box.getByTestId("pi-when")).toHaveText(/Đã đạt|khoảng \d+ năm|khoảng \d+ tháng|Chưa đạt trong 50 năm/);
  await expect(box).toContainText("chưa tính lạm phát");
});

test("no horizontal scroll on the profile page at 375px with the goal", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 900 });
  await page.goto("/profile");
  await expect(page.getByRole("region", { name: "Mục tiêu dòng tiền thụ động" })).toBeVisible();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(0);
});

test("income today is counted layer by layer: deposits, bonds at their coupon, last year's cash dividends", async ({ page }) => {
  await seedOwner(page);
  const { call } = await import("./helpers");
  expect((await call(page, "POST", "macro/deposit_12m/observations", { date: "2026-04-30", value: "5,6" })).ok()).toBe(true);
  const current = await (await call(page, "GET", "equity-budget")).json();
  await call(page, "PUT", "equity-budget", { layers: { deposit: "600000000", bond: "120000000", gold: "50000000", crypto: "0" }, reserve: "0",
    expected_version: current.version, request_id: `pi-eb-${Date.now()}` });
  await page.goto("/profile");
  const box = page.getByRole("region", { name: "Mục tiêu dòng tiền thụ động" });
  await expect(box.getByLabel("Lãi suất trái phiếu (%/năm)")).toBeEnabled();
  await box.getByLabel("Lãi suất trái phiếu (%/năm)").fill("7");
  await box.getByRole("button", { name: "Tính mục tiêu" }).click();
  const lines = box.getByRole("list", { name: "Dòng tiền hiện tại theo lớp" });
  await expect(lines).toContainText("Trái phiếu (7%/năm): 700.000 đ/tháng");
  await expect(lines).toContainText(/Tiền gửi \([\d,]+%\/năm\): [\d.]+ đ\/tháng/);
  await expect(lines).toContainText(/Cổ tức tiền mặt 12 tháng: [\d.]+ đ\/tháng/);
  await expect(lines).toContainText("Vàng, tiền mặt, tiền số: không tạo dòng tiền");
  await expect(box).toContainText(/~[\d.]+ đ\/tháng · đạt \d{1,3}(,\d)?% mục tiêu/);  // e.g. "đạt 22% mục tiêu", never "0,22%"
});
