import { expect, test } from "@playwright/test";
import { signIn } from "./helpers";

// Synthetic fixture data only: two weekly notes kept as they went out over Telegram.
test.beforeEach(async ({ context }) => signIn(context));

test("the newest weekly note shows as sent, and an earlier week can be opened", async ({ page }) => {
  await page.goto("/reports");
  const box = page.getByRole("region", { name: "Bản tin tuần" });
  const text = box.getByLabel("Nội dung bản tin tuần");
  await expect(text).toContainText("BẢN TIN TUẦN 16/11–20/11/2026");
  await expect(text).toContainText("VÀNG TRONG TUẦN");
  await box.getByLabel("Chọn tuần").selectOption("2026-11-13");
  await expect(text).toContainText("BẢN TIN TUẦN 09/11–13/11/2026");
  await expect(box).toContainText("không phải khuyến nghị");
});

test("no horizontal page scroll with a weekly note open at 375px", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 900 });
  await page.goto("/reports");
  await expect(page.getByLabel("Nội dung bản tin tuần")).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)).toBeLessThanOrEqual(0);
});
