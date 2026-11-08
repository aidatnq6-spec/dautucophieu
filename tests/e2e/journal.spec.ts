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

test("an older journal file is previewed, imported once into the journal only, and found again by search", async ({ page }) => {
  await seedOwner(page);
  const stamp = Date.now();
  const csv = `STT,Loại tài sản,Ngày giao dịch,Lệnh,Mã,SL tổng,Giá vốn,Giá trị vốn,Lãi/Lỗ,Lý do mua/ bán\n1,Cổ phiếu,2025-03-01,Mua,HPG,1000,20000,,,Định giá rẻ ${stamp}\n2,Vàng,2025-03-02,Mua,,2,8000000,,,Giữ giá trị ${stamp}\n3,Cổ phiếu,31/02/2025,Mua,HPG,1,1,,,hỏng\n`;
  await page.goto("/portfolio");
  const before = await page.getByRole("table", { name: "Giao dịch" }).locator("tbody tr").count();
  await page.goto("/journal");
  const box = page.getByRole("group", { name: "Nhập từ nhật ký cũ" });
  await box.locator("summary").click();
  await box.getByLabel("Chọn file nhật ký").setInputFiles({ name: "cu.csv", mimeType: "text/csv", buffer: Buffer.from(csv, "utf-8") });
  await expect(box.getByRole("status").first()).toContainText("2 mục mới");
  await expect(box.getByRole("list", { name: "Dòng lỗi" })).toContainText("Dòng 4: Ngày không hợp lệ: 31/02/2025");
  await expect(page.getByRole("article").filter({ hasText: `Định giá rẻ ${stamp}` })).toHaveCount(0);  // a preview saves nothing
  await box.getByRole("button", { name: "Nhập 2 mục" }).click();
  const entry = page.getByRole("article").filter({ hasText: `Định giá rẻ ${stamp}` });
  await expect(entry).toContainText("Nhập từ nhật ký cũ");
  await expect(entry).toContainText("20.000.000");
  await expect(entry.getByRole("button", { name: "Bối cảnh lúc ghi" })).toHaveCount(0);  // none was recorded
  // Search, without accents; another asset keeps its class.
  const search = page.getByRole("region", { name: "Tra cứu nhật ký" });
  await search.getByLabel("Từ khóa trong lý do, ghi chú").fill(`dinh gia re ${stamp}`);
  await expect(page.getByRole("article")).toHaveCount(1);
  await search.getByRole("button", { name: "Xóa bộ lọc" }).click();
  await search.getByLabel("Loại tài sản").selectOption("Vàng");
  await expect(page.getByRole("article").filter({ hasText: `Giữ giá trị ${stamp}` })).toContainText("VANG");
  const saved = page.waitForEvent("download");
  await search.getByRole("button", { name: "Xuất Excel" }).click();
  expect((await saved).suggestedFilename()).toBe("nhat-ky-dau-tu.xls");
  // Importing the same file again adds nothing, and the ledger was never touched.
  await box.getByLabel("Chọn file nhật ký").setInputFiles({ name: "cu.csv", mimeType: "text/csv", buffer: Buffer.from(csv, "utf-8") });
  await expect(box.getByRole("status").first()).toContainText("0 mục mới");
  await expect(box.getByRole("status").first()).toContainText("2 mục đã có");
  await page.goto("/portfolio");
  await expect(page.getByRole("table", { name: "Giao dịch" }).locator("tbody tr")).toHaveCount(before);
  await page.getByLabel("Tìm mã").fill("ZZZ");
  await expect(page.getByRole("table", { name: "Giao dịch" }).locator("tbody tr")).toHaveCount(0);
});

test("a long journal is shown a page at a time, while search and totals cover all of it", async ({ page }) => {
  await seedOwner(page);
  const stamp = Date.now();
  const lines = Array.from({ length: 60 }, (_, i) => `${i + 1},Cổ phiếu,2024-01-${String((i % 28) + 1).padStart(2, "0")},Mua,HPG,1,${1000 + i},,,Trang ${stamp} số ${i}`);
  await page.goto("/journal");
  const box = page.getByRole("group", { name: "Nhập từ nhật ký cũ" });
  await box.locator("summary").click();
  await box.getByLabel("Chọn file nhật ký").setInputFiles({ name: "dai.csv", mimeType: "text/csv", buffer: Buffer.from(`STT,Loại tài sản,Ngày giao dịch,Lệnh,Mã,SL tổng,Giá vốn,Giá trị vốn,Lãi/Lỗ,Lý do mua/ bán\n${lines.join("\n")}\n`, "utf-8") });
  await box.getByRole("button", { name: "Nhập 60 mục" }).click();
  const search = page.getByRole("region", { name: "Tra cứu nhật ký" });
  await search.getByLabel("Từ khóa trong lý do, ghi chú").fill(`Trang ${stamp}`);
  await expect(search).toContainText("60/");  // the count is of the whole result
  await expect(page.getByRole("article")).toHaveCount(50);
  const pager = page.getByRole("navigation", { name: "Trang nhật ký" });
  await expect(pager).toContainText("Trang 1/2");
  await pager.getByRole("button", { name: "Sau" }).click();
  await expect(page.getByRole("article")).toHaveCount(10);
  await expect(pager.getByRole("button", { name: "Sau" })).toBeDisabled();
  await search.getByLabel("Từ khóa trong lý do, ghi chú").fill(`Trang ${stamp} số 7`);  // a new search starts from its first page
  await expect(page.getByRole("article")).toHaveCount(1);
  await expect(pager).toHaveCount(0);
});
