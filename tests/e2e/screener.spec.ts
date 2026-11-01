import { expect, test } from "@playwright/test";
import { signIn } from "./helpers";

// Synthetic watchlist and stored data only.
test.describe.configure({ mode: "serial" });
test.beforeEach(async ({ context }) => signIn(context));

test("criteria narrow the watched tickers, missing data is counted apart, and a screen is saved and deleted", async ({ page }) => {
  await page.goto("/watchlist");
  const box = page.getByRole("region", { name: "Bộ lọc tín hiệu" });
  const count = box.getByTestId("screen-count");
  await expect(count).toContainText("mã khớp");
  await box.getByLabel("Rẻ").uncheck();  // no criterion: every watched ticker
  await expect(count).not.toContainText(/^0 mã khớp/);
  await box.locator("fieldset", { hasText: "Khối ngoại 20 phiên" }).getByLabel("Mua ròng").check();
  await expect(count).toContainText("0 mã khớp");
  await expect(count).toContainText("mã thiếu dữ liệu");
  await box.getByText(/Mã thiếu dữ liệu \(/).click();
  await expect(box).toContainText("Chưa đủ 20 phiên khối ngoại");
  const save = box.getByRole("form", { name: "Lưu bộ lọc" });
  await save.getByLabel("Tên bộ lọc").fill("Ngoại mua");
  await save.getByLabel(/Nhắn Telegram/).check();
  await save.getByRole("button", { name: "Lưu bộ lọc" }).click();
  await expect(box.getByRole("group", { name: "Bộ lọc đã lưu" })).toContainText("Ngoại mua · nhắn");
  page.once("dialog", (d) => void d.accept());
  await save.getByRole("button", { name: "Xóa" }).click();
  await expect(box.getByRole("group", { name: "Bộ lọc đã lưu" })).toHaveCount(0);
});

test("the screener has no horizontal page scroll at 375px", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 800 });
  await page.goto("/watchlist");
  await expect(page.getByRole("region", { name: "Bộ lọc tín hiệu" })).toBeVisible();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  expect(overflow).toBeLessThanOrEqual(0);
});
