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

test("So sánh cùng ngành sets a sector's tickers side by side: best and worst marked, sorted, another quarter, a chart", async ({ page }) => {
  await page.goto("/research/VCB");
  const box = page.getByRole("region", { name: "So sánh cùng ngành" });
  const table = box.getByRole("table", { name: "So sánh ngành Ngân hàng, Q3/2026" });  // the latest quarter both banks have: VCB has a Q4, ACB does not
  const cell = (symbol: string, column: string) => table.getByRole("row", { name: new RegExp(`^${symbol}`) }).locator(`td[data-label="${column}"]`);
  const firstTicker = () => table.locator("tbody tr").first().locator('td[data-label="Mã"]');
  await expect(table.getByRole("row", { name: /^VCB/ })).toHaveClass(/peer-focus/);
  await expect(cell("VCB", "P/B")).toHaveText("0,60x");
  await expect(cell("ACB", "P/B")).toHaveText("0,30x");
  await expect(cell("ACB", "P/B")).toHaveClass(/positive/);  // the lower P/B is the better
  await expect(cell("VCB", "P/B")).toHaveClass(/negative/);
  await expect(cell("VCB", "NPL")).toHaveText("0,71%");
  await expect(cell("VCB", "NPL")).toHaveClass(/positive/);  // the lower NPL is the better: the direction turns with the column
  await expect(cell("ACB", "NPL")).toHaveClass(/negative/);
  await expect(cell("ACB", "CASA")).toHaveText("32,0%");  // from Vietcap's notes
  await expect(table.getByRole("columnheader", { name: /CAR cuối năm 2025/ })).toBeVisible();
  await expect(cell("ACB", "CAR cuối năm")).toHaveText("12,45%");
  await expect(cell("VCB", "CAR cuối năm")).toHaveText("—");
  await expect(cell("ACB", "Giá so với giá hợp lý")).toHaveText(/^[+-]?\d+,\d%$/);  // the column that was empty without prices
  await expect(cell("VCB", "Giá so với giá hợp lý")).toHaveText("—");  // no price stored: blank, not zero
  await expect(cell("ACB", "P/B theo giá")).toHaveText("0,20x");  // the latest close, unlike the 0,30x at the quarter's end
  await expect(table.getByRole("row", { name: /Trung vị ngành/ }).locator("td").nth(1)).toBeVisible();
  await expect(table.getByRole("row", { name: /Trung vị ngành/ })).toContainText("0,96%");  // NPL between 0,71% and 1,20%
  // Sorting: the first click puts the better end on top, the second turns it round.
  await expect(firstTicker()).toContainText("ACB");
  await table.getByRole("button", { name: "NPL", exact: true }).click();
  await expect(firstTicker()).toContainText("VCB");
  await table.getByRole("button", { name: "NPL", exact: true }).click();
  await expect(firstTicker()).toContainText("ACB");
  // A chart of one column.
  await table.getByRole("button", { name: "Vẽ biểu đồ: NPL" }).click();
  const chart = box.getByRole("figure", { name: "Biểu đồ NPL" });
  await expect(chart).toContainText("VCB");
  await expect(chart).toContainText("1,20%");
  await chart.getByRole("button", { name: "Ẩn biểu đồ" }).click();
  await expect(chart).toHaveCount(0);
  // Another quarter: VCB has no ratios for it, so its NPL is blank rather than taken from Q3.
  await box.getByLabel("Kỳ so sánh").selectOption("2026-Q2");
  const q2 = box.getByRole("table", { name: "So sánh ngành Ngân hàng, Q2/2026" });
  await expect(q2.getByRole("row", { name: /^ACB/ }).locator('td[data-label="NPL"]')).toHaveText("1,50%");
  await expect(q2.getByRole("row", { name: /^ACB/ }).locator('td[data-label="P/B"]')).toHaveText("0,20x");
  await expect(q2.getByRole("row", { name: /^VCB/ }).locator('td[data-label="NPL"]')).toHaveText("—");
  await q2.getByRole("row", { name: /^ACB/ }).getByRole("link", { name: "ACB" }).click();
  await expect(page).toHaveURL(/\/research\/ACB$/);
  // A sector with one watched ticker says why there is no table.
  await page.goto("/research/FPT");
  await expect(page.getByRole("region", { name: "So sánh cùng ngành" })).toContainText("Chỉ có 1 mã ngành Công nghệ Thông tin trong danh sách theo dõi");
  // From Định giá, the chosen sector opens the comparison.
  await page.goto("/fair-value");
  await page.getByLabel("Ngành").selectOption("Ngân hàng");
  await page.getByRole("link", { name: "So sánh ngành này" }).click();
  await expect(page).toHaveURL(/\/research\/ACB#so-sanh-cung-nganh$/);
  await expect(page.getByRole("region", { name: "So sánh cùng ngành" }).getByRole("table", { name: /So sánh ngành Ngân hàng/ })).toBeVisible();
});

test("a bank's Bảng số tài chính holds its sector ratios with its valuation under one chart, and every watched ticker its dividend history", async ({ page }) => {
  await page.goto("/research/VCB");
  // One block as for a company: chart on top, period buttons, then the sector ratios and the scale and valuation group in one table.
  const box = page.getByRole("region", { name: "Bảng số tài chính" });
  const table = box.getByRole("table", { name: /quý, cũ bên trái/ });
  await expect(table).toContainText("Chỉ số ngân hàng");
  await expect(table).toContainText("Quy mô và định giá");
  await expect(table).toContainText("Q3/26");
  await expect(table.getByRole("row", { name: /Tỷ lệ nợ xấu/ })).toContainText("0,71%");  // VNDirect's ratio to two places
  await expect(table.getByRole("row", { name: /^P\/B/ })).toContainText("0,6x");  // 60,000 đ × 1 million shares = 60 tỷ ÷ 100 tỷ
  await expect(table.getByRole("row", { name: /Giá trị sổ sách/ })).toContainText("100.000 đ");
  await expect(box.getByRole("button", { name: "8 quý" })).toHaveAttribute("aria-pressed", "true");
  await expect(box.getByRole("button", { name: "Vẽ biểu đồ: P/B" })).toHaveAttribute("aria-pressed", "true");
  await box.getByRole("button", { name: "Vẽ biểu đồ: Tỷ lệ nợ xấu (NPL)" }).click();
  await expect(box.getByRole("button", { name: "Vẽ biểu đồ: Tỷ lệ nợ xấu (NPL)" })).toHaveAttribute("aria-pressed", "true");
  await expect(box.getByRole("button", { name: "Vẽ biểu đồ: P/B" })).toHaveAttribute("aria-pressed", "false");  // the earliest makes room
  await box.getByRole("radio", { name: "Năm" }).click();
  await expect(box).toContainText("Chỉ số ngân hàng chỉ có theo quý");
  await page.goto("/research/FPT");
  await expect(page.getByRole("region", { name: "Bảng số tài chính" })).not.toContainText("Chỉ số ngân hàng");
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

test("Bảng số tài chính gives quarters and years with EBITDA, valuation and checks, and gives a bank its ratios and valuation in the same block", async ({ page }) => {
  await page.goto("/research/FPT");
  const box = page.getByRole("region", { name: "Bảng số tài chính" });
  const table = box.getByRole("table");
  await expect(table).toContainText("Doanh thu thuần");
  await expect(table).toContainText("EBITDA");
  await expect(table).toContainText("Q4/25");
  await expect(table).toContainText("Quy mô và định giá");  // the valuation block shows by quarter too
  await expect(box.getByRole("button", { name: "8 quý" })).toHaveAttribute("aria-pressed", "true");
  await box.getByRole("radio", { name: "Năm" }).click();
  await expect(box.getByRole("table")).toContainText("EV/EBITDA");
  await expect(box.getByRole("table")).toContainText("2025");
  await expect(box).toContainText("Kiểm tra chéo");  // the synthetic quarters do not add up to the years
  await expect(box).toContainText("không ước lượng");
  await page.goto("/research/VCB");
  await expect(page.getByRole("region", { name: "Bảng số tài chính" })).toContainText("Chỉ số ngân hàng");
});

test("Bảng số tài chính draws picked rows: revenue with gross margin first, a third row replaces the earliest, numbers behind it", async ({ page }) => {
  await page.goto("/research/FPT");
  const box = page.getByRole("region", { name: "Bảng số tài chính" });
  const legend = box.getByLabel("Dòng đang vẽ");
  await expect(legend.getByRole("button")).toHaveText([/Doanh thu thuần/, /Biên gộp/]);
  await expect(box.getByRole("img", { name: "Biểu đồ Doanh thu thuần và Biên gộp" })).toBeVisible();
  await expect(box.getByRole("columnheader", { name: "Xu hướng" })).toBeVisible();
  await box.getByRole("button", { name: "Vẽ biểu đồ: LNST công ty mẹ", exact: true }).click();
  await expect(legend.getByRole("button")).toHaveText([/Biên gộp/, /LNST công ty mẹ/]);
  await expect(box.getByRole("button", { name: "Vẽ biểu đồ: Doanh thu thuần", exact: true })).toHaveAttribute("aria-pressed", "false");
  await box.getByText("Xem số liệu").click();
  await expect(box.getByRole("table", { name: "Số liệu biểu đồ bảng số tài chính" })).toContainText("Q4/25");
  await legend.getByRole("button", { name: "Bỏ Biên gộp khỏi biểu đồ" }).click();
  await expect(legend.getByRole("button")).toHaveText([/LNST công ty mẹ/]);
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

test("Bảng đèn chỉ báo sớm colours an indicator against thresholds the owner sets, in either direction", async ({ page }) => {
  await page.goto("/research/ACB");
  const box = page.getByRole("region", { name: "Bảng đèn chỉ báo sớm" });
  const form = box.getByRole("form", { name: "Thêm chỉ báo" });
  await form.getByLabel("Chỉ báo").selectOption("macro:wti");  // the fixture's oil ends at 66
  await form.getByLabel("Ngưỡng Xấu").fill("55");
  await form.getByLabel("Ngưỡng Tốt").fill("75");
  await form.getByRole("button", { name: "Thêm" }).click();
  const row = box.getByRole("row", { name: /Giá dầu WTI/ });
  await expect(row).toContainText("Theo dõi");
  await expect(row).toContainText("≥ 75");
  await form.getByLabel("Chỉ báo").selectOption("stock:BAD_LOANS_RATIO_AQ");  // ACB's NPL: 1,20%
  await form.getByLabel("Ngưỡng Xấu").fill("3");
  await form.getByLabel("Ngưỡng Tốt").fill("2");
  await form.getByRole("button", { name: "Thêm" }).click();
  await expect(box.getByRole("row", { name: /NPL/ })).toContainText("Tốt");
  await box.getByRole("button", { name: "Bỏ Giá dầu WTI" }).click();
  await expect(box.getByRole("row", { name: /Giá dầu WTI/ })).toHaveCount(0);
  await box.getByRole("button", { name: "Bỏ NPL" }).click();
});
