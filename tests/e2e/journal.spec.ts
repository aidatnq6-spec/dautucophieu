import { expect, test } from "@playwright/test";
import { seedOwner, signIn } from "./helpers";

// FPT is held by seedOwner. Entries are append-only, so each test writes a reason of its own and looks for it.
test.describe.configure({ mode: "serial" });
test.beforeEach(async ({ context }) => signIn(context));

test("a buy recorded with a reason and an emotion appears in the journal with its context", async ({ page }) => {
  await seedOwner(page);
  const why = `Mua thêm vì KQKD tốt ${Date.now()}`;
  await page.goto("/portfolio");
  await page.getByRole("button", { name: "Ghi nhận giao dịch" }).click();
  const form = page.getByRole("form", { name: "Ghi nhận giao dịch" });
  await form.getByLabel("Loại giao dịch").selectOption("buy");
  await form.getByLabel("Mã cổ phiếu").fill("FPT");
  await form.getByLabel("Số lượng").fill("10");
  await form.getByLabel("Giá thực hiện (đ/cp)").fill("50000");
  await form.getByLabel("Lý do ra quyết định").fill(why);
  await form.getByLabel("Cảm xúc lúc đó").selectOption("fomo");
  await form.getByLabel("Ghi chú cảm xúc").fill("sợ lỡ sóng");
  await form.getByRole("button", { name: "Ghi vào sổ" }).click();
  await expect(form).toBeHidden();

  await page.goto("/journal");
  const entry = page.getByRole("article").filter({ hasText: why });
  await expect(entry).toContainText("FPT");
  await expect(entry).toContainText("Mua");
  await expect(entry).toContainText("Sợ bỏ lỡ (FOMO)");
  await entry.getByRole("button", { name: "Bối cảnh lúc ghi" }).click();
  await expect(entry.getByRole("list", { name: "Bối cảnh lúc ghi" })).toContainText("VN-Index");
  await expect(page.getByText(/đi thêm 15% so với giá lúc ghi.*nhắc qua Telegram/)).toBeVisible();
  await expect(page.getByRole("navigation", { name: "Điều hướng chính" }).getByRole("link", { name: "Nhật ký" })).toBeVisible();
});

test("a reason for still holding can be written, then notes appended, never edited", async ({ page }) => {
  await seedOwner(page);
  const why = `Giữ vì cổ tức đều ${Date.now()}`;
  await page.goto("/journal");
  const form = page.getByRole("form", { name: "Ghi lý do đang giữ" });
  await form.getByLabel("Mã đang nắm").selectOption("FPT");
  await form.getByLabel("Lý do đang giữ").fill(why);
  await form.getByLabel("Cảm xúc lúc đó").selectOption("calm");
  await form.getByRole("button", { name: "Lưu vào nhật ký" }).click();
  const entry = page.getByRole("article").filter({ hasText: why });
  await expect(entry).toContainText("Đang giữ");
  await entry.getByLabel("Thêm ghi chú").fill("Vẫn giữ sau KQKD quý");
  await entry.getByRole("button", { name: "Thêm ghi chú" }).click();
  await expect(entry).toContainText("Vẫn giữ sau KQKD quý");
  await expect(entry.getByRole("button", { name: /Sửa|Xóa/ })).toHaveCount(0);
});

test("no horizontal scroll on the journal page at 375px", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 900 });
  await page.goto("/journal");
  await expect(page.getByRole("form", { name: "Ghi lý do đang giữ" })).toBeVisible();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(0);
});
