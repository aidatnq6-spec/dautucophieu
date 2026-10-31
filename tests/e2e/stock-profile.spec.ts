import { expect, test } from "@playwright/test";
import { signIn } from "./helpers";

// Synthetic fixture data only: FPT has statements, closes and sector insights; VCB has no statements.
test.beforeEach(async ({ context }) => signIn(context));

test("a ticker's profile gathers quick facts, valuation, events and sector insights", async ({ page }) => {
  await page.goto("/research/FPT");
  const facts = page.getByRole("region", { name: "Thông tin nhanh" });
  await expect(facts).toContainText("Vốn hoá");
  await expect(facts).toContainText("Cao / thấp 52 tuần");
  const valuation = page.getByRole("region", { name: "Định giá tham khảo" });
  await expect(valuation).toContainText("Đắt");
  await expect(valuation.getByRole("region", { name: "Phương án định giá FPT" })).toContainText("P/E lịch sử");
  await expect(page.getByRole("figure", { name: "P/E lịch sử FPT" })).toBeVisible();
  await expect(page.getByRole("region", { name: "Sự kiện" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Nhận định về ngành: Công nghệ Thông tin" })).toBeVisible();
  await expect(page.getByRole("button", { name: /^Mua/ })).toHaveCount(0);
});

test("ticker symbols on Định giá open the profile", async ({ page }) => {
  await page.goto("/fair-value");
  await page.getByRole("table", { name: "Định giá tham khảo" }).getByRole("link", { name: "FPT" }).click();
  await expect(page).toHaveURL(/\/research\/FPT$/);
  await expect(page.getByRole("region", { name: "Thông tin nhanh" })).toBeVisible();
});

test("a ticker without statements says what is missing", async ({ page }) => {
  await page.goto("/research/VCB");
  await expect(page.getByRole("region", { name: "Định giá tham khảo" })).toContainText("Chưa có báo cáo tài chính");
  await expect(page.getByRole("region", { name: "Thông tin nhanh" })).toContainText("—");
});

test("no horizontal scroll on a profile at 375px", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 900 });
  await page.goto("/research/FPT");
  await expect(page.getByRole("figure", { name: "P/E lịch sử FPT" })).toBeVisible();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(0);
});

test("a watched bank's page takes quarterly loan groups, deposits and CAR, and shows NPL and CASA", async ({ page }) => {
  await page.goto("/research/VCB");
  const box = page.getByRole("region", { name: "Số liệu ngân hàng" });
  await expect(box.getByLabel("Quý")).toBeEnabled();
  const quarter = `20${10 + (Date.now() % 15)}-Q${1 + (Date.now() % 4)}`;  // the e2e store persists between runs: a fresh quarter each time
  await box.getByLabel("Quý").fill(quarter);
  for (const [label, value] of [["Nợ nhóm 1 (đủ tiêu chuẩn) (tỷ đồng)", "447734"], ["Nợ nhóm 2 (cần chú ý) (tỷ đồng)", "7808"],
    ["Nợ nhóm 3 (dưới tiêu chuẩn) (tỷ đồng)", "1517"], ["Nợ nhóm 4 (nghi ngờ) (tỷ đồng)", "1220"], ["Nợ nhóm 5 (có khả năng mất vốn) (tỷ đồng)", "2293"],
    ["Tiền gửi không kỳ hạn (tỷ đồng)", "166971"], ["Tiền gửi ký quỹ (tỷ đồng)", "10354"], ["Tiền gửi của khách hàng (tỷ đồng)", "537304,578"], ["CAR (%)", "11,5"]]) {
    await box.getByLabel(label).fill(value);
  }
  await box.getByRole("button", { name: "Lưu quý này" }).click();
  const row = box.getByRole("table", { name: "Số liệu ngân hàng VCB" }).getByRole("row", { name: new RegExp(quarter) });
  await expect(row).toContainText("1,09%");  // NPL
  await expect(row).toContainText("33,00%");  // CASA
  await expect(row).toContainText("11,50%");  // CAR
  page.once("dialog", (d) => d.accept());
  await row.getByRole("button", { name: `Xóa ${quarter}` }).click();
  await expect(box.getByRole("row", { name: new RegExp(quarter) })).toHaveCount(0);
});

test("a ticker that is not a bank has no bank figures section", async ({ page }) => {
  await page.goto("/research/FPT");
  await expect(page.getByRole("region", { name: "Định giá tham khảo" })).toBeVisible();
  await expect(page.getByRole("region", { name: "Số liệu ngân hàng" })).toHaveCount(0);
});

test("a growth scenario prices forward EPS on the ticker's own P/E and P/B bands, with ±2 and ±3 SD on the charts", async ({ page }) => {
  await page.goto("/research/FPT");
  const box = page.getByRole("region", { name: "Định giá dự phóng" });
  await expect(box).toContainText("Năm gốc 2025: EPS 1.000 đ");  // fixture: profit 1 tỷ, EPS 1.000 every year
  await box.getByLabel("Tăng trưởng lợi nhuận năm 1").fill("10");
  await box.getByLabel("Tăng trưởng vốn chủ năm 1").fill("10");
  for (const i of [2, 3]) {
    await box.getByLabel(`Tăng trưởng lợi nhuận năm ${i}`).fill("");
    await box.getByLabel(`Tăng trưởng vốn chủ năm ${i}`).fill("");
    await box.getByLabel(`Pha loãng cổ phiếu năm ${i}`).fill("");
  }
  await box.getByLabel("Giả sử P/E =").fill("10");
  await box.getByRole("button", { name: "Tính và lưu kịch bản" }).click();
  await expect(box).toContainText("Năm 2026: EPS 1.100 đ");
  await expect(box).toContainText("Với P/E 10: 11.000 đ");
  const table = box.getByRole("table", { name: "Giá dự phóng năm 2026" });
  await expect(table.getByRole("row")).toHaveCount(8);  // header and seven levels, −3 to +3 SD
  await expect(table).toContainText("Trung vị");
  await expect(page.getByRole("figure", { name: "P/E lịch sử FPT" })).toContainText("±2:");
  await expect(page.getByRole("figure", { name: "P/E lịch sử FPT" }).getByTestId("mc-sd").first()).toBeAttached();
});

test("a bank's page shows its sector ratios by quarter, and every watched ticker its dividend history", async ({ page }) => {
  await page.goto("/research/VCB");
  const ratios = page.getByRole("region", { name: "Chỉ số ngành theo quý" });
  await expect(ratios).toContainText("Chỉ số ngân hàng theo quý");
  const table = ratios.getByRole("table", { name: "Chỉ số theo quý VCB" });
  await expect(table).toContainText("Q3/2026");
  await expect(table.getByRole("row", { name: /Tỷ lệ nợ xấu/ })).toContainText("0,71%");
  await page.goto("/research/FPT");
  await expect(page.getByRole("region", { name: "Chỉ số ngành theo quý" })).toHaveCount(0);
  const div = page.getByRole("region", { name: "Lịch sử cổ tức" });
  await expect(div).toContainText("Cổ tức tiền (đ/cp)");
  await expect(div.getByRole("table", { name: "Lịch sử cổ tức FPT" }).getByRole("row", { name: /^2025/ })).toContainText("500");
  await expect(div).toContainText(/12 tháng gần nhất: cổ tức tiền [\d.]+ đ\/cp/);
});

test("the CAPM hint takes the owner's risk premium in Cài đặt and prices each ticker on its beta; the page lists shareholders and officers", async ({ page }) => {
  await page.goto("/settings");
  const box = page.getByRole("region", { name: "Gợi ý CAPM" });
  await box.getByLabel("Phần bù rủi ro vốn cổ phần, ERP (%)").fill("7,8");
  await box.getByRole("button", { name: "Lưu ERP" }).click();
  await expect(box).toContainText("Chi phí vốn chủ theo CAPM: 12,29%");  // 4,49% + 1 × 7,8%
  await page.goto("/research/FPT");
  await expect(page.getByRole("group", { name: "CAPM FPT" })).toContainText("Chi phí vốn chủ theo CAPM: 10,18%");  // 4,49% + 0,73 × 7,8%
  const people = page.getByRole("region", { name: "Cổ đông lớn và ban lãnh đạo" });
  await expect(people.getByRole("table", { name: "Cổ đông lớn FPT" })).toContainText("Trương Gia Bình");
  await expect(people.getByRole("table", { name: "Ban lãnh đạo FPT" })).toContainText("Phó Chủ tịch Hội đồng Quản trị");
});
