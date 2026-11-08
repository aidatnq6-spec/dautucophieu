import { expect, test } from "@playwright/test";
import { call, seedOwner, signIn } from "./helpers";

// Synthetic ledger (seedOwner buys FPT) and synthetic closes only.
test.beforeEach(async ({ context }) => signIn(context));

test("Hậu kiểm quyết định on Nhật ký follows each trade and says when there is not enough to conclude", async ({ page }) => {
  await seedOwner(page);
  await page.goto("/journal");
  const box = page.getByRole("region", { name: "Hậu kiểm quyết định" });
  await expect(box.getByRole("table", { name: "Từng lệnh", exact: true })).toContainText("Mua FPT");
  await expect(box.getByRole("table", { name: "Thói quen", exact: true })).toContainText("chưa đủ dữ liệu để kết luận");
  await expect(box).toContainText("Không phải khuyến nghị");
});

test("the hindsight section has no horizontal page scroll at 375px", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 800 });
  await seedOwner(page);
  await page.goto("/journal");
  await expect(page.getByRole("region", { name: "Hậu kiểm quyết định" })).toBeVisible();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  expect(overflow).toBeLessThanOrEqual(0);
});

test("orders imported from an older journal are followed apart from the ledger's, and a ticker without prices is named", async ({ page }) => {
  await seedOwner(page);
  const csv = `STT,Loại tài sản,Ngày giao dịch,Lệnh,Mã,SL tổng,Giá vốn,Giá trị vốn,Lãi/Lỗ,Lý do mua/ bán\n1,Cổ phiếu,2026-03-02,Mua,FPT,100,50000,,,Hậu kiểm cũ\n2,Cổ phiếu,2026-03-03,Mua,ZZZ,100,10000,,,Hậu kiểm cũ\n`;
  expect((await call(page, "POST", "journal/import", { content: csv, commit: true, request_id: `hk-${Date.now()}` })).ok()).toBe(true);
  await page.goto("/journal");
  const box = page.getByRole("region", { name: "Hậu kiểm quyết định" });
  await expect(box.getByRole("table", { name: "Từng lệnh cũ" })).toContainText("Mua FPT");
  await expect(box.getByRole("table", { name: "Từng lệnh cũ" })).toContainText("Mua ZZZ");
  await expect(box).toContainText("Chưa có giá đã lưu của 1 mã");
  await expect(box.getByRole("table", { name: "Thói quen lệnh cũ" })).toContainText("Bán khi đang lãi");
  await expect(box.getByRole("table", { name: "Từng lệnh", exact: true })).not.toContainText("ZZZ");  // the ledger's own list stays the ledger's
});
