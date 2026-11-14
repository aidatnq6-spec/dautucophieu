import { expect, test } from "@playwright/test";
import { signIn } from "./helpers";

test.beforeEach(async ({ context }) => signIn(context));

test("the assistant answers a quick button, a ticker and a page name, on this machine", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Mở trợ lý" }).click();
  const panel = page.getByRole("dialog", { name: "Trợ lý" });
  await expect(panel).toContainText("không gửi gì ra ngoài");
  await panel.getByRole("button", { name: "Hệ thống có lỗi không" }).click();
  await expect(panel).toContainText(/Hệ thống ổn|vấn đề|Chưa đọc được/);
  await panel.getByLabel("Câu hỏi cho trợ lý").fill("FPT");
  await panel.getByRole("button", { name: "Gửi" }).click();
  await expect(panel.locator(".as-bot").last()).toContainText("FPT");
  await panel.getByLabel("Câu hỏi cho trợ lý").fill("mở quỹ mở");
  await panel.getByRole("button", { name: "Gửi" }).click();
  await panel.getByRole("link", { name: "Quỹ mở →" }).click();
  await expect(page).toHaveURL(/\/funds/);
});

test("the assistant fits a phone screen", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 760 });
  await page.goto("/");
  await page.getByRole("button", { name: "Mở trợ lý" }).click();
  await expect(page.getByRole("dialog", { name: "Trợ lý" })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)).toBeLessThanOrEqual(0);
});
