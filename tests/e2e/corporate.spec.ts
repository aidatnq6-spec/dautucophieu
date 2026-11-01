import { expect, test } from "@playwright/test";
import { seedOwner, signIn } from "./helpers";

// Synthetic events: an FPT cash dividend 30 days ago (2.000 đ/cp) and one in 3 days; seedOwner holds 100 FPT since February.
test.describe.configure({ mode: "serial" });
test.beforeEach(async ({ context }) => signIn(context));

test("a past dividend is drafted for the shares held before the ex-date, set aside and brought back", async ({ page }) => {
  await seedOwner(page);
  await page.goto("/portfolio");
  const box = page.getByRole("region", { name: "Cổ tức và quyền" });
  const list = box.getByRole("list", { name: "Gợi ý cổ tức và quyền" });
  const past = list.getByRole("listitem").filter({ hasText: "ghi quyền vào sổ" });
  await expect(past).toContainText("Cổ tức tiền 2.000 đ/cp");
  await expect(past).toContainText("bạn có 100 cp trước ngày này");
  await expect(list.getByRole("listitem").filter({ hasText: "sắp tới" })).toContainText("bạn đang có 100 cp");
  await past.getByRole("button", { name: "Ghi vào sổ" }).click();
  await expect(past.getByLabel("Loại giao dịch")).toHaveValue("cash_dividend_entitlement");
  await expect(past.getByLabel("Số cổ phiếu hưởng quyền")).toHaveValue("100");
  await expect(past.getByLabel("Cổ tức gộp dự kiến (đ)")).toHaveValue("200000");
  await expect(past.getByLabel("Thuế dự kiến (đ)")).toHaveValue("10000");
  await past.getByRole("button", { name: "Hủy bỏ" }).click();
  page.once("dialog", (d) => void d.accept());
  await past.getByRole("button", { name: /Bỏ qua/ }).click();
  await expect(list.getByRole("listitem").filter({ hasText: "ghi quyền vào sổ" })).toHaveCount(0);
  await box.getByText(/Đã bỏ qua/).click();
  await box.getByRole("button", { name: "Khôi phục" }).click();
  await expect(list.getByRole("listitem").filter({ hasText: "ghi quyền vào sổ" })).toHaveCount(1);
  await expect(page.getByRole("region", { name: "Thuế và phí theo năm" })).toBeVisible();
});

test("the dividend section has no horizontal page scroll at 375px", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 800 });
  await seedOwner(page);
  await page.goto("/portfolio");
  await expect(page.getByRole("region", { name: "Cổ tức và quyền" })).toBeVisible();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  expect(overflow).toBeLessThanOrEqual(0);
});
