import { expect, test } from "@playwright/test";
import { call, seedOwner, signIn } from "./helpers";

// Lạm phát lối sống reads the monthly figures kept by Sức khỏe tài chính; Tài sản vô hình is an editable log at the base of the pyramid.
test.describe.configure({ mode: "serial" });
test.beforeEach(async ({ context }) => signIn(context));

test("the lifestyle check waits for six months of figures and says when", async ({ page }) => {
  await seedOwner(page);
  const wc = await (await call(page, "GET", "wealth-check")).json();
  await call(page, "PUT", "wealth-check", { income: "30000000", expenses: "20000000", birth_year: 1989, expected_version: wc.version, request_id: `ls-${Date.now()}` });
  await page.goto("/profile");
  const box = page.getByRole("region", { name: "Lạm phát lối sống" });
  await expect(box).toContainText("cần ít nhất 6 tháng số liệu");
  await expect(box.getByRole("table", { name: "Thu nhập và chi tiêu theo tháng" })).toContainText("20.000.000");
});

test("money put into oneself is logged, summed for the year and shown at the base of the pyramid", async ({ page }) => {
  await page.goto("/profile");
  const box = page.getByRole("region", { name: "Tài sản vô hình" });
  await expect(box.getByLabel("Nội dung")).toBeEnabled();
  const title = `Khóa AI ${Date.now()}`;
  await box.getByLabel("Loại").selectOption("course");
  await box.getByLabel("Nội dung").fill(title);
  await box.getByLabel("Số tiền (đ)").pressSequentially("5000000");
  await box.getByLabel("Kỹ năng thu được").fill("Dùng AI tổng hợp số liệu");
  await box.getByRole("button", { name: "Thêm vào sổ" }).click();
  await expect(box.getByRole("table", { name: "Sổ tài sản vô hình" })).toContainText(title);
  await expect(box).toContainText(/Năm \d{4}: đã đầu tư [\d.]+ đ \/ mục tiêu [\d.]+ đ \(10% thu nhập năm\)/);
  await expect(page.getByRole("region", { name: "Tháp tài sản" }).getByTestId("pyramid-intangibles")).toContainText(/Tài sản vô hình: năm nay [\d.]+ đ/);
});

test("a line of the intangibles log can be edited in place and deleted", async ({ page }) => {
  await page.goto("/profile");
  const box = page.getByRole("region", { name: "Tài sản vô hình" });
  await expect(box.getByLabel("Nội dung")).toBeEnabled();
  const title = `Sách định giá ${Date.now()}`;
  await box.getByLabel("Nội dung").fill(title);
  await box.getByLabel("Số tiền (đ)").pressSequentially("300000");
  await box.getByRole("button", { name: "Thêm vào sổ" }).click();
  const table = box.getByRole("table", { name: "Sổ tài sản vô hình" });
  await expect(table).toContainText(title);

  await table.getByRole("button", { name: `Sửa ${title}` }).click();
  const row = table.getByRole("row", { name: `Sửa dòng ${title}` });
  await row.getByLabel("Nội dung").fill(`${title} (bản sửa)`);
  await row.getByLabel("Số tiền (đ)").fill("450000");
  await row.getByRole("button", { name: "Lưu" }).click();
  await expect(table).toContainText(`${title} (bản sửa)`);
  await expect(table.getByRole("row", { name: new RegExp(`${title} \\(bản sửa\\)`) })).toContainText("450.000 đ");

  page.once("dialog", (d) => d.accept());
  await table.getByRole("button", { name: `Xóa ${title} (bản sửa)` }).click();
  await expect(table).not.toContainText(title);
});

test("no horizontal scroll on the profile page at 375px with both blocks", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 900 });
  await page.goto("/profile");
  await expect(page.getByRole("region", { name: "Tài sản vô hình" })).toBeVisible();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(0);
});
