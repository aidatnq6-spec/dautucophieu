import { expect, test } from "@playwright/test";
import { signIn } from "./helpers";

// Synthetic fixture data only: US 10-year yield 4.91 → 4.96 (automatic); every manual indicator starts empty.
test.describe.configure({ mode: "serial" });
test.beforeEach(async ({ context }) => signIn(context));

async function openMacro(page: import("@playwright/test").Page) {
  await page.goto("/macro");
  await expect(page.getByText("Đang tải…")).toHaveCount(0);
}

test("automatic indicators show value, trend and the owner's assessment", async ({ page }) => {
  await openMacro(page);
  const row = page.getByRole("table", { name: "Chỉ số vĩ mô" }).getByRole("row", { name: /Lợi suất trái phiếu 10 năm của Mỹ/ });
  for (const text of ["4,96", "Tăng", "Xấu", "Tự động"]) await expect(row).toContainText(text);
  await expect(page.getByRole("row", { name: /PMI sản xuất Việt Nam/ })).toContainText("Chưa có số liệu");
});

test("the owner enters PMI values and sees the trend", async ({ page }) => {
  await openMacro(page);
  const row = () => page.getByRole("row", { name: /PMI sản xuất Việt Nam/ });
  for (const [day, value] of [["2026-09-01", "52,4"], ["2026-10-01", "51,9"]]) {
    await row().getByRole("button", { name: "Nhập" }).click();
    const form = page.getByRole("form", { name: "Nhập PMI sản xuất Việt Nam" });
    await form.getByLabel("Ngày số liệu").fill(day);
    await form.getByLabel("Giá trị").fill(value);
    await form.getByLabel("Link nguồn").fill("https://example.invalid/pmi");
    await form.getByRole("button", { name: "Lưu" }).click();
    await expect(form).toHaveCount(0);
  }
  for (const text of ["51,9", "Giảm", "Xấu", "Nhập tay"]) await expect(row()).toContainText(text);
});

test("no horizontal page scroll on the macro page at 375px", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 900 });
  await openMacro(page);
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(0);
});
