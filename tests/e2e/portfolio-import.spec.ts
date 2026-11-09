import path from "node:path";
import { expect, test } from "@playwright/test";
import { seedOwner, signIn } from "./helpers";

// A synthetic TCInvest export: one matched buy of FPT and one line with an impossible date.
test.beforeEach(async ({ context }) => signIn(context));

test("a TCBS statement is previewed, added once to Sổ giao dịch, and offered no second time", async ({ page }) => {
  await seedOwner(page);
  await page.goto("/portfolio");
  const file = path.join(__dirname, "fixtures", "tcbs-mau.xlsx");
  const box = page.getByRole("group", { name: "Nhập sao kê TCBS" });
  await box.locator("summary").click();
  await box.getByLabel("Chọn file sao kê TCBS").setInputFiles(file);
  await expect(box.getByRole("status").first()).toContainText("1 lệnh mới");
  await expect(box.getByRole("list", { name: "Dòng lỗi sao kê" })).toContainText("31/02/2026");
  await expect(box.getByRole("table", { name: "Xem trước sao kê" })).toContainText("Sẽ thêm");
  const before = await page.getByRole("table", { name: "Giao dịch" }).locator("tbody tr").count();
  await box.getByRole("button", { name: "Thêm 1 lệnh vào sổ" }).click();
  await expect(box.getByRole("status").first()).toContainText("Đã thêm 1 lệnh");
  await expect(page.getByRole("table", { name: "Giao dịch" }).locator("tbody tr")).toHaveCount(before + 1);
  await box.getByLabel("Chọn file sao kê TCBS").setInputFiles(file);
  await expect(box.getByRole("status").first()).toContainText("0 lệnh mới");
  await expect(box.getByRole("table", { name: "Xem trước sao kê" })).toContainText("Đã nhập trước đó");
  await expect(box.getByRole("button", { name: /Thêm \d+ lệnh/ })).toHaveCount(0);
});
