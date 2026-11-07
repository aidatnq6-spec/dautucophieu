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

test("the CAPM hint starts from Damodaran's premium for Vietnam, takes the owner's in Cài đặt, prices each ticker on its beta; the page lists shareholders and officers", async ({ page }) => {
  await page.goto("/settings");
  const box = page.getByRole("region", { name: "Gợi ý CAPM" });
  await expect(box).toContainText("Chi phí vốn chủ theo CAPM: 12,62%");  // 4,49% + 1 × 8,13% before anything is entered
  await expect(box.getByTestId("erp-damodaran")).toContainText("ERP 8,13% (theo xếp hạng Moody's Ba2)");
  await box.getByLabel("Phần bù rủi ro vốn cổ phần, ERP (%)").fill("7,8");
  await box.getByRole("button", { name: "Lưu ERP" }).click();
  await expect(box).toContainText("Chi phí vốn chủ theo CAPM: 12,29%");  // 4,49% + 1 × 7,8%
  await page.goto("/research/FPT");
  await expect(page.getByRole("group", { name: "CAPM FPT" })).toContainText("Chi phí vốn chủ theo CAPM: 10,18%");  // 4,49% + 0,73 × 7,8%
  await page.goto("/settings");
  await box.getByRole("button", { name: "Dùng số Damodaran" }).click();
  await expect(box).toContainText("Chi phí vốn chủ theo CAPM: 12,62%");
  await page.goto("/research/FPT");
  const people = page.getByRole("region", { name: "Cổ đông lớn và ban lãnh đạo" });
  const holders = people.getByRole("table", { name: "Cổ đông lớn FPT" });
  await expect(holders.getByRole("row", { name: /Trương Gia Bình/ })).toContainText("Chủ tịch Hội đồng Quản trị");  // the officer's role beside the stake
  await expect(holders.getByRole("row", { name: /Khác/ })).toContainText("93,11%");  // 100% − 6,89%
  await expect(people).toContainText("Nước ngoài 22,22% (room tối đa 49,00%)");
  await expect(people).toContainText("Tự do chuyển nhượng chưa có số");
  await expect(people.getByRole("table", { name: "Cơ cấu sở hữu FPT" })).toContainText("Tổ chức nước ngoài");
  const insider = page.getByRole("region", { name: "Giao dịch nội bộ và cổ đông lớn" });
  await expect(insider.getByRole("table", { name: "Giao dịch nội bộ FPT" }).getByRole("row")).toHaveCount(4);
  await expect(insider.getByTestId("insider-year")).toContainText("đã bán 2.000.000 cổ phiếu (1 báo cáo)");  // the registration is not a trade
  await expect(insider.getByTestId("insider-year")).toContainText("1 báo cáo kết quả không ghi loại hoặc khối lượng");
  await expect(insider.getByRole("link", { name: /Bùi Quang Ngọc/ })).toHaveAttribute("href", /^https:\/\/dstock\.vndirect\.com\.vn\//);
  await expect(people.getByRole("table", { name: "Ban lãnh đạo FPT" })).toContainText("Phó Chủ tịch Hội đồng Quản trị");
});

test("Bảng số tài chính gives quarters and years with EBITDA, valuation and checks, and says why a bank has none", async ({ page }) => {
  await page.goto("/research/FPT");
  const box = page.getByRole("region", { name: "Bảng số tài chính" });
  const table = box.getByRole("table");
  await expect(table).toContainText("Doanh thu thuần");
  await expect(table).toContainText("EBITDA");
  await expect(table).toContainText("Q4/25");
  await expect(box.getByRole("button", { name: "8 quý" })).toHaveAttribute("aria-pressed", "true");
  await box.getByRole("radio", { name: "Năm" }).click();
  await expect(box.getByRole("table")).toContainText("EV/EBITDA");
  await expect(box.getByRole("table")).toContainText("2025");
  await expect(box).toContainText("Kiểm tra chéo");  // the synthetic quarters do not add up to the years
  await expect(box).toContainText("không ước lượng");
  await page.goto("/research/VCB");
  await expect(page.getByRole("region", { name: "Bảng số tài chính" })).toContainText("bảng số liệu ngành riêng");
});

test("no horizontal page scroll with the statement table at 375px", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 900 });
  await page.goto("/research/FPT");
  await expect(page.getByRole("region", { name: "Bảng số tài chính" }).getByRole("table")).toBeVisible();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(0);
});

test("the owner enters a year's plan with its source and sees the year-to-date share of it", async ({ page }) => {
  await page.goto("/research/FPT");
  const box = page.getByRole("region", { name: "Bảng số tài chính" });
  await box.getByText(/Kế hoạch năm \(ĐHCĐ\)/).click();
  const form = box.getByRole("form", { name: "Nhập kế hoạch năm" });
  await form.getByLabel("Năm").fill("2025");
  await form.getByLabel("Doanh thu (tỷ đồng)").fill("2180");  // the synthetic 2025 quarters add up to 1,090 tỷ
  await form.getByLabel("Lợi nhuận (tỷ đồng)").fill("2");
  await form.getByRole("button", { name: "Lưu kế hoạch" }).click();
  await expect(box.getByRole("alert")).toContainText("Ghi nguồn của kế hoạch");
  await form.getByLabel("Nguồn (bắt buộc)").fill("Nghị quyết ĐHCĐ 2025");
  await form.getByRole("button", { name: "Lưu kế hoạch" }).click();
  await expect(box).toContainText("DT lũy kế Q4/2025 · % kế hoạch");
  await expect(box).toContainText("50,0%");
  await expect(box).toContainText("1.090 / KH 2.180 tỷ");
  await expect(box).toContainText("nguồn: Nghị quyết ĐHCĐ 2025");
  await box.getByRole("button", { name: "Xóa kế hoạch 2025" }).click();
  await expect(box).not.toContainText("DT lũy kế Q4/2025");
});

test("the owner's assumptions for the next quarter add a yellow F column, and blank ones leave their lines blank", async ({ page }) => {
  await page.goto("/research/FPT");
  const box = page.getByRole("region", { name: "Bảng số tài chính" });
  const form = box.getByRole("form", { name: "Giả định dự phóng quý tới" });
  await expect(box).toContainText("Dự phóng Q1/2026 (giả định của bạn) · chưa nhập");
  await form.getByLabel("Doanh thu so cùng kỳ (%)").fill("10");
  await form.getByLabel("Biên gộp (%)").fill("40");
  await form.getByRole("button", { name: "Lưu giả định" }).click();
  const table = box.getByRole("table");
  await expect(table.getByRole("columnheader", { name: "Q1/26F" })).toBeVisible();
  await expect(table.getByRole("row", { name: /^Doanh thu thuần/ })).toContainText("298");  // 271 tỷ in Q1/2025 × 1.1
  await expect(table.getByRole("row", { name: /^Lợi nhuận gộp/ })).toContainText("119");  // 40 %
  await expect(box).toContainText("không phải dự báo của ứng dụng");
});

test("the owner defines an operating group, enters periods with sources and sees totals, shares and growth", async ({ page }) => {
  await page.goto("/research/FPT");
  const box = page.getByRole("region", { name: "Số liệu vận hành" });
  const add = box.getByRole("form", { name: "Thêm nhóm số liệu vận hành" });
  await add.getByLabel("Tên nhóm").fill("Sản lượng bán");
  await add.getByLabel("Đơn vị").fill("nghìn tấn");
  await add.getByLabel("Các dòng (cách nhau dấu phẩy)").fill("Thép XD, HRC");
  await add.getByRole("button", { name: "Thêm nhóm" }).click();
  const group = box.getByRole("group", { name: "Sản lượng bán" });
  const entry = group.getByRole("form", { name: "Nhập Sản lượng bán" });
  for (const [period, a, b] of [["2025-Q3", "1060", "1270"], ["2026-Q3", "1340", "2100"]]) {
    await entry.getByLabel(/^Kỳ/).fill(period);
    await entry.getByLabel("Thép XD (nghìn tấn)").fill(a);
    await entry.getByLabel("HRC (nghìn tấn)").fill(b);
    await entry.getByLabel("Nguồn (bắt buộc)").fill(`Bản tin SXKD ${period}`);
    await entry.getByRole("button", { name: "Lưu kỳ" }).click();
    await expect(group.getByRole("table")).toContainText(period === "2025-Q3" ? "Q3/25" : "Q3/26");
  }
  const latest = group.getByRole("row", { name: /^Q3\/26/ });
  await expect(latest).toContainText("3.440");
  await expect(latest).toContainText("+47,6%");  // 3,440 against 2,330
  await expect(latest).toContainText("Bản tin SXKD 2026-Q3");
  await expect(group.getByRole("img", { name: "Sản lượng bán (nghìn tấn)" })).toBeVisible();
  await group.getByRole("button", { name: "Xóa nhóm" }).click();
  await expect(box.getByRole("group", { name: "Sản lượng bán" })).toHaveCount(0);
});

test("a public PDF bulletin proposes each line's figure with its page and text, and nothing is kept until the owner saves", async ({ page }) => {
  await page.goto("/research/FPT");
  const box = page.getByRole("region", { name: "Số liệu vận hành" });
  await expect(box).toContainText("ô “Đọc từ PDF công khai” sẽ hiện trong nhóm vừa tạo");  // where to find it before any group exists
  const add = box.getByRole("form", { name: "Thêm nhóm số liệu vận hành" });
  await add.getByLabel("Tên nhóm").fill("Sản lượng bán PDF");
  await add.getByLabel("Đơn vị").fill("tấn");
  await add.getByLabel("Các dòng (cách nhau dấu phẩy)").fill("Thép xây dựng, HRC, Tôn mạ");
  await add.getByRole("button", { name: "Thêm nhóm" }).click();
  const group = box.getByRole("group", { name: "Sản lượng bán PDF" });
  await group.getByLabel("Đọc từ PDF công khai (link https)").fill("https://example.invalid/ban-tin-10-2026.pdf");
  await group.getByRole("button", { name: "Đọc PDF" }).click();
  const proposal = group.getByRole("region", { name: "Số đề xuất từ PDF cho Sản lượng bán PDF" });
  await expect(proposal).toContainText("Không thấy: Tôn mạ");
  await expect(proposal.getByRole("button", { name: "412.300 · trang 2" })).toHaveAttribute("aria-pressed", "true");
  await expect(proposal).toContainText("thép xây dựng đạt 412.300 tấn");
  const entry = group.getByRole("form", { name: "Nhập Sản lượng bán PDF" });
  await expect(entry.getByLabel("Thép xây dựng (tấn)")).toHaveValue("412300");
  await expect(entry.getByLabel("Nguồn (bắt buộc)")).toHaveValue("https://example.invalid/ban-tin-10-2026.pdf (trang 2)");
  await entry.getByLabel(/^Kỳ/).fill("2026-Q3");
  await entry.getByRole("button", { name: "Lưu kỳ" }).click();
  await expect(group.getByRole("row", { name: /^Q3\/26/ })).toContainText("412.300");
  await group.getByRole("button", { name: "Xóa nhóm" }).click();
});
