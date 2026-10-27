import { expect, test } from "@playwright/test";
import { seedOwner, signIn } from "./helpers";

// A buy is checked before it is saved: concentration and the asset pyramid after it, and a three-month run-up. It never blocks.
test.describe.configure({ mode: "serial" });
test.beforeEach(async ({ context }) => signIn(context));

test("a large buy shows the check with numbers and the question, and can still be saved", async ({ page }) => {
  await seedOwner(page);
  await page.goto("/portfolio");
  await page.getByRole("button", { name: "Ghi nhận giao dịch" }).click();
  const form = page.getByRole("form", { name: "Ghi nhận giao dịch" });
  await form.getByLabel("Loại giao dịch").selectOption("buy");
  await form.getByLabel("Mã cổ phiếu").fill("FPT");
  await form.getByLabel("Số lượng").fill("20000");
  await form.getByLabel("Giá thực hiện (đ/cp)").fill("50000");  // 1 tỷ
  const check = form.getByRole("region", { name: "Kiểm tra trước khi mua" });
  await expect(check).toContainText(/FPT sẽ chiếm [\d,]+% (vốn dành cho cổ phiếu|vốn có thể đầu tư) \(ngưỡng 25%\)/);
  await expect(check).toContainText("Đây là quyết định đầu tư theo kế hoạch, hay mua vì sợ lỡ cơ hội?");
  await expect(form.getByRole("button", { name: "Ghi vào sổ" })).toBeEnabled();
});

test("the check is only for buys", async ({ page }) => {
  await page.goto("/portfolio");
  await page.getByRole("button", { name: "Ghi nhận giao dịch" }).click();
  const form = page.getByRole("form", { name: "Ghi nhận giao dịch" });
  await form.getByLabel("Loại giao dịch").selectOption("sell");
  await form.getByLabel("Mã cổ phiếu").fill("FPT");
  await form.getByLabel("Số lượng").fill("1");
  await form.getByLabel("Giá thực hiện (đ/cp)").fill("50000");
  await expect(form.getByRole("region", { name: "Kiểm tra trước khi mua" })).toHaveCount(0);
});
