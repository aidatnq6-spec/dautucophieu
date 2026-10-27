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
