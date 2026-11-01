import { expect, test } from "@playwright/test";
import { seedOwner, signIn } from "./helpers";

// Synthetic ledger (seedOwner holds FPT) and synthetic closes only.
test.beforeEach(async ({ context }) => signIn(context));

test("a scenario is priced on the holdings with what could not be counted named", async ({ page }) => {
  await seedOwner(page);
  await page.goto("/portfolio");
  const box = page.getByRole("region", { name: "Kiểm tra sức chịu đựng" });
  await box.getByRole("button", { name: "Dầu +30%" }).click();
  await expect(box.getByLabel("Giá dầu (%)")).toHaveValue("30");
  await expect(box.getByTestId("stress-total")).toContainText("Danh mục cổ phiếu:");
  await expect(box.getByRole("table", { name: "Kịch bản theo mã" })).toContainText("FPT");
  await box.getByLabel("VN-Index (%)").fill("abc");
  await expect(box.getByText("Nhập số phần trăm")).toBeVisible();
  await expect(box).toContainText("không phải dự báo");
});

test("the stress section has no horizontal page scroll at 375px", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 800 });
  await seedOwner(page);
  await page.goto("/portfolio");
  await expect(page.getByRole("region", { name: "Kiểm tra sức chịu đựng" })).toBeVisible();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  expect(overflow).toBeLessThanOrEqual(0);
});
