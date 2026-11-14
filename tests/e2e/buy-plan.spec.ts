import { expect, test } from "@playwright/test";
import { signIn } from "./helpers";

test.beforeEach(async ({ context }) => signIn(context));

test("a planned tranche is added with its condition, shown against the latest close, then dropped and removed", async ({ page }) => {
  await page.goto("/portfolio");
  const box = page.getByRole("region", { name: "Kế hoạch giải ngân" });
  await box.getByLabel("Mã").fill("FPT");
  await box.getByLabel("Số tiền").fill("20000000");
  await box.getByLabel("Giá trị điều kiện").fill("50,5");
  await box.getByRole("button", { name: "Thêm đợt" }).click();
  const row = box.getByRole("table", { name: "Các đợt mua dự kiến" }).getByRole("row", { name: /FPT/ });
  await expect(row).toContainText("Giá đóng cửa ≤ 50,50");
  await expect(row).toContainText("Chờ");
  await row.getByRole("button", { name: "Bỏ" }).click();
  await expect(row).toContainText("Bỏ");
  page.once("dialog", (d) => d.accept());
  await row.getByRole("button", { name: "Xóa đợt FPT" }).click();
  await expect(box).toContainText("Chưa có đợt mua nào");
});
