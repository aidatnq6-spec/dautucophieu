import { expect, test } from "@playwright/test";
import { seedOwner, signIn } from "./helpers";

// Synthetic ledger (seedOwner buys FPT) and synthetic closes only.
test.beforeEach(async ({ context }) => signIn(context));

test("Hậu kiểm quyết định on Nhật ký follows each trade and says when there is not enough to conclude", async ({ page }) => {
  await seedOwner(page);
  await page.goto("/journal");
  const box = page.getByRole("region", { name: "Hậu kiểm quyết định" });
  await expect(box.getByRole("table", { name: "Từng lệnh" })).toContainText("Mua FPT");
  await expect(box.getByRole("table", { name: "Thói quen" })).toContainText("chưa đủ dữ liệu để kết luận");
  await expect(box).toContainText("Không phải khuyến nghị");
});

test("the hindsight section has no horizontal page scroll at 375px", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 800 });
  await seedOwner(page);
  await page.goto("/journal");
  await expect(page.getByRole("region", { name: "Hậu kiểm quyết định" })).toBeVisible();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  expect(overflow).toBeLessThanOrEqual(0);
});
