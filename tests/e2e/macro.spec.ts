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
  // Read from a web page, so a manual value stays possible when the page changes.
  const deposit = page.getByRole("row", { name: /Lãi suất tiền gửi VND 12 tháng/ });
  await expect(deposit).toContainText("Tự động");
  await expect(deposit.getByRole("button", { name: "Nhập" })).toBeVisible();
  await expect(page.getByRole("row", { name: /Lợi suất trái phiếu 10 năm của Mỹ/ }).getByRole("button", { name: "Nhập" })).toHaveCount(0);
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
  for (const text of ["51,9", "Giảm", "Xấu", "Tự động"]) await expect(row()).toContainText(text);
});

test("no horizontal page scroll on the macro page at 375px", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 900 });
  await openMacro(page);
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(0);
});

test("automated rows with a manual fallback, and US PMI entered by hand", async ({ page }) => {
  await openMacro(page);
  for (const label of [/Cung tiền M2/, /PMI sản xuất Việt Nam/, /10 năm của Việt Nam/, /liên ngân hàng VN qua đêm/]) {
    const row = page.getByRole("row", { name: label });
    await expect(row).toContainText("Tự động");
    await expect(row.getByRole("button", { name: "Nhập" })).toBeVisible();
  }
  // Since 26/10/2026 the US PMI publishers block automated reading: hand entry only.
  const us = page.getByRole("row", { name: /PMI sản xuất Mỹ/ });
  await expect(us).toContainText("Nhập tay");
  await expect(us.getByRole("button", { name: "Nhập" })).toBeVisible();
});

test("the rate cycle line says which rates it reads and waits for six months of Vietnam data", async ({ page }) => {
  await openMacro(page);
  const box = page.getByRole("region", { name: "Mốc chu kỳ lãi suất" });
  await expect(box).toBeVisible();
  await expect(box).toContainText("chưa đủ 6 tháng dữ liệu Việt Nam");
  await expect(box).toContainText("không phải khuyến nghị");
});
