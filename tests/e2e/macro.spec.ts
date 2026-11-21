import { expect, test } from "@playwright/test";
import { seedOwner, signIn } from "./helpers";

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
  // by its own name: the real deposit rate row names it in its note
  const deposit = page.getByRole("row").filter({ has: page.getByText("Lãi suất tiền gửi VND 12 tháng (NHTM khác)", { exact: true }) });
  await expect(deposit).toContainText("Tự động");
  await expect(deposit.getByRole("button", { name: "Nhập" })).toBeVisible();
  await expect(page.getByRole("row", { name: /Lợi suất trái phiếu 10 năm của Mỹ/ }).getByRole("button", { name: "Nhập" })).toHaveCount(0);
});

test("the owner enters PMI values and sees the trend", async ({ page }) => {
  await openMacro(page);
  const row = () => page.getByRole("row", { name: /PMI sản xuất Việt Nam/ });
  for (const [month, value] of [["2026-09", "52,4"], ["2026-10", "51,9"]]) {
    await row().getByRole("button", { name: "Nhập" }).click();
    const form = page.getByRole("form", { name: "Nhập PMI sản xuất Việt Nam" });
    await form.getByLabel("Tháng số liệu").fill(month);  // a monthly figure is entered by its month
    await form.getByLabel("Giá trị").fill(value);
    await form.getByLabel("Link nguồn").fill("https://example.invalid/pmi");
    await form.getByRole("button", { name: "Lưu" }).click();
    await expect(form).toHaveCount(0);
  }
  for (const text of ["51,9", "Giảm", "Xấu", "Tự động"]) await expect(row()).toContainText(text);
});

test("the impact chain shows five links, says what is missing, and reads inflation once it is entered", async ({ page }) => {
  await openMacro(page);
  const chain = page.getByRole("region", { name: "Chuỗi tác động vĩ mô" });
  const links = chain.getByRole("list", { name: "Các mắt xích, từ giá dầu đến VN-Index" }).locator(":scope > li");  // not the rate rows inside a link
  await expect(links).toHaveText([/Giá dầu/, /Giá xăng trong nước/, /Lạm phát Việt Nam/, /Thanh khoản và chênh lệch VND–USD/, /Lãi suất Việt Nam/, /Khối ngoại/, /VN-Index/]);
  await expect(chain.getByTestId("chain-liquidity")).toContainText("tạo áp lực");  // the synthetic spread is below zero
  await expect(chain.getByTestId("chain-liquidity")).toContainText("bơm 1.500 tỷ đ");
  await expect(chain).toContainText("không phải khuyến nghị");
  // Months before the 03/2026 figure performance.spec enters, so either order leaves CPI rising: 2,0 → 2,9 (→ 3,2).
  for (const [month, value] of [["2026-01", "2,0"], ["2026-02", "2,9"]]) {
    await page.getByRole("row", { name: /Lạm phát Việt Nam/ }).getByRole("button", { name: "Nhập" }).click();
    const form = page.getByRole("form", { name: "Nhập Lạm phát Việt Nam (CPI, so cùng kỳ)" });
    await form.getByLabel("Tháng số liệu").fill(month);
    await form.getByLabel("Giá trị").fill(value);
    await form.getByRole("button", { name: "Lưu" }).click();
    await expect(form).toHaveCount(0);
  }
  await openMacro(page);
  const inflation = page.getByRole("region", { name: "Chuỗi tác động vĩ mô" }).getByTestId("chain-inflation");
  await expect(inflation).toContainText(/2,9%|3,2%/);
  await expect(inflation).toContainText("Tăng");
  await expect(inflation).toContainText("tạo áp lực");
  await expect(page.getByRole("region", { name: "Chuỗi tác động vĩ mô" }).getByTestId("chain-summary")).toContainText(/Đang tạo áp lực:.*lạm phát/);
});

test("oil and dollar sensitivity lists held tickers first and says what the dollar measure is", async ({ page }) => {
  await seedOwner(page);  // holds FPT; the e2e data has no oil or dollar history, so every reading waits for data
  await openMacro(page);
  const box = page.getByRole("region", { name: "Độ nhạy với giá dầu và đồng USD" });
  await expect(box).toContainText("không phải tỷ giá VND");
  await expect(box).toContainText("không phải khuyến nghị");
  const fpt = box.getByRole("row", { name: /FPT/ });
  await expect(fpt).toContainText("đang nắm");
  await expect(fpt).toContainText("chưa đủ dữ liệu");
  // nothing held can be measured yet: no "0% … 0%" shares, only how much is unmeasured
  await expect(box.getByTestId("sensitivity-exposure")).toHaveText("100% vốn ở mã chưa đủ dữ liệu để đo.");
  // the span can be widened; the reading reloads for it
  const spans = box.getByRole("radiogroup", { name: "Khoảng đo" });
  await expect(spans.getByLabel("3 năm")).toBeChecked();
  await spans.getByLabel("Toàn bộ").check();
  await expect(box).toContainText("toàn bộ lịch sử chung");
  await expect(box.getByRole("row", { name: /FPT/ })).toContainText("đang nắm");
});

test("five risk lights with their thresholds; missing data is said, not shown as green", async ({ page }) => {
  await openMacro(page);
  const box = page.getByRole("region", { name: "Đèn tín hiệu rủi ro vĩ mô" });
  const lights = box.getByRole("list", { name: "Các đèn tín hiệu" }).getByRole("listitem");
  await expect(lights).toHaveText([/Giá dầu WTI/, /Đồng USD/, /Tỷ giá tự do/, /Tỷ giá Vietcombank so với trần/, /Lợi suất trái phiếu Mỹ/,
    /Khối ngoại/, /Lãi suất liên ngân hàng/, /P\/E VN-Index/, /PMI sản xuất Việt Nam/]);
  await expect(box.getByTestId("signal-pmi")).toContainText("cảnh báo < 50 · nguy hiểm < 48");
  await expect(box.getByTestId("signal-oil")).toContainText("cảnh báo ≥ +10% · nguy hiểm ≥ +20%");
  await expect(box.getByTestId("signal-interbank")).toContainText("cảnh báo ≥ 5%/năm · nguy hiểm ≥ 7%/năm");
  await expect(box).toContainText("không phải khuyến nghị");
  await expect(box.getByLabel("Tóm tắt các đèn")).toContainText(/\d nguy hiểm · \d cảnh báo · \d bình thường/);
  await expect(box.getByTestId("signal-oil")).not.toContainText("giảm:");  // oil falling is not a risk (owner, 21/11/2026)
  await expect(box.getByRole("link", { name: "Giá dầu WTI" })).toHaveAttribute("href", "#chi-so-wti");
  await expect(page.locator("#chi-so-wti")).toHaveCount(1);  // the light leads to its row of the table
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
  await us.getByRole("button", { name: "Nhập" }).click();
  await expect(page.getByLabel("Tháng số liệu")).toBeVisible();  // a monthly figure asks for its month, not the day it is typed
  await expect(page.getByLabel("Ngày số liệu")).toHaveCount(0);
});

test("the rate cycle line says which rates it reads and waits for six months of Vietnam data", async ({ page }) => {
  await openMacro(page);
  const box = page.getByRole("region", { name: "Mốc chu kỳ lãi suất" });
  await expect(box).toBeVisible();
  await expect(box).toContainText("chưa đủ 6 tháng dữ liệu Việt Nam");
  await expect(box).toContainText("không phải khuyến nghị");
});

test("the indicator table fits its box on a laptop screen and writes the day in full", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 800 });
  await openMacro(page);
  const table = page.getByRole("table", { name: "Chỉ số vĩ mô" });
  const row = table.getByRole("row", { name: /Lợi suất trái phiếu 10 năm của Mỹ/ });
  await expect(row).toContainText(/\d{2}\/\d{2}\/\d{4}/);
  await expect(row).toContainText(/hôm nay|hôm qua|ngày trước/);
  const [tableWidth, boxWidth] = await table.evaluate((t) => [t.scrollWidth, t.parentElement!.clientWidth]);
  expect(tableWidth).toBeLessThanOrEqual(boxWidth);
});

test("the VND–USD spread warns below zero and the swap calculator prices a swap", async ({ page }) => {
  await openMacro(page);
  const spread = page.getByRole("region", { name: "Chênh lệch lãi suất VND–USD" });
  await expect(spread.getByTestId("spread-latest")).toContainText("−0,30 điểm %");
  await expect(spread).toContainText("Chênh lệch đang âm");
  const swap = page.getByRole("region", { name: "Chi phí hoán đổi ngoại tệ" });
  await expect(swap.getByLabel("Lãi suất USD")).toHaveValue("3,9");
  await swap.getByLabel("Tỷ giá giao ngay").fill("24.399");
  await swap.getByLabel("Tỷ giá kỳ hạn").fill("24.704");
  await swap.getByLabel("Lãi suất USD").fill("3,89");
  const out = swap.getByRole("list", { name: "Kết quả hoán đổi" });
  await expect(out).toContainText("2,50%/năm");
  await expect(out).toContainText("6,39%/năm");
});

test("the owner logs a macro event with its source and removes it", async ({ page }) => {
  await openMacro(page);
  const cal = page.getByRole("region", { name: "Lịch và nhật ký vĩ mô" });
  const form = cal.getByRole("form", { name: "Thêm sự kiện vĩ mô" });
  await form.getByLabel("Ngày sự kiện").fill("2099-01-02");
  await form.getByLabel("Loại sự kiện").selectOption("fed");
  await form.getByLabel("Nội dung sự kiện").fill("Họp chính sách thử nghiệm");
  await form.getByLabel("Nguồn sự kiện").fill("https://example.invalid/fed");
  await form.getByRole("button", { name: "Thêm sự kiện" }).click();
  const coming = cal.getByRole("table", { name: "Sự kiện vĩ mô sắp tới" });
  await expect(coming.getByRole("row", { name: /Họp chính sách thử nghiệm/ })).toContainText("Nhắc trước 1 ngày");
  await coming.getByRole("button", { name: "Xóa Họp chính sách thử nghiệm" }).click();
  await expect(cal).toContainText("Chưa có sự kiện sắp tới.");
});

test("the central rate shows its band, the open market its latest session, and the month's trade and FDI", async ({ page }) => {
  await openMacro(page);
  const fx = page.getByRole("region", { name: "Tỷ giá trung tâm và biên độ" });
  await expect(fx.getByTestId("fx-central")).toContainText("25.000 đ/USD");
  await expect(fx).toContainText("sàn 23.750 – trần 26.250");
  await expect(fx).toContainText("Tỷ giá Vietcombank chỉ còn cách trần 0,19%");
  await expect(fx).toContainText("Chưa có tỷ giá trung tâm đầu năm");
  const omo = page.getByRole("region", { name: "Thanh khoản hệ thống" });
  await expect(omo.getByTestId("omo-latest")).toContainText("bơm 1.500 tỷ đ");
  await expect(omo.getByRole("table", { name: "Kết quả thị trường mở phiên mới nhất" }).getByRole("row")).toHaveCount(2);  // the empty 91-day row is left out
  await expect(omo).toContainText("cần đủ phiên của 91 ngày");
  const ext = page.getByRole("region", { name: "Cán cân ngoại tệ" }).getByRole("list", { name: "Cán cân và FDI" });
  await expect(ext).toContainText("nhập siêu 1,5 tỷ USD");
  await expect(ext).toContainText("20 tỷ USD (+8,5% so cùng kỳ)");
});


test("the US macro calendar of the Fed and BLS sits above the owner's own macro calendar", async ({ page }) => {
  await page.goto("/macro");
  const us = page.getByRole("region", { name: "Lịch vĩ mô Mỹ" });
  await expect(us).toContainText("giờ Việt Nam");
  await expect(us.getByRole("status")).toHaveCount(0);
  const box = await us.boundingBox(), own = await page.getByRole("region", { name: "Lịch và nhật ký vĩ mô" }).boundingBox();
  expect(box!.y).toBeLessThan(own!.y);
});


test("the week chain from US inflation to the dong sits below the domestic chain, each link labelled", async ({ page }) => {
  await page.goto("/macro");
  const box = page.getByRole("region", { name: "Chuỗi liên thị trường trong tuần" });
  await expect(box.getByTestId("us-chain-us_cpi")).toBeVisible();
  await expect(box.getByTestId("us-chain-usd_vnd")).toContainText(/khớp chuỗi|ngược chuỗi|đi ngang|chưa có số|chưa có chiều|mở đầu chuỗi/);
  await expect(box.getByTestId("us-chain-summary")).not.toBeEmpty();
});


test("the SJC gap section takes a threshold and turns the alert off again", async ({ page }) => {
  await page.goto("/macro");
  const box = page.getByRole("region", { name: "Chênh lệch vàng SJC so với thế giới" });
  await box.getByLabel("Ngưỡng chênh lệch vàng").fill("12,5");
  await box.getByRole("button", { name: "Lưu ngưỡng" }).click();
  await expect(box).toContainText("Đang nhắc khi từ 12,5% trở lên.");
  await box.getByLabel("Ngưỡng chênh lệch vàng").fill("");
  await box.getByRole("button", { name: "Tắt nhắc" }).click();
  await expect(box).toContainText("Chưa đặt ngưỡng: không nhắc.");
  // the fixture has a world gold series (PAXG) but no SJC history: that row and the 30-day line say so rather than show a number
  const moves = box.getByRole("group", { name: "Vàng: sụt từ đỉnh và độ truyền giá" });
  await expect(moves.getByRole("row", { name: /Vàng thế giới/ })).toContainText("−12,5%");  // PAXG 4000 → 3500 in the fixture
  await expect(moves.getByRole("row", { name: /Vàng miếng SJC/ })).toContainText("Chưa có số liệu.");
  await expect(moves).toContainText("Chưa có ngày nào có cả giá SJC và giá thế giới quy ra đồng.");
});


test("the Asian markets section and the fuel link of the chain are on the macro page", async ({ page }) => {
  await page.goto("/macro");
  await expect(page.getByRole("region", { name: "Chứng khoán châu Á" })).toContainText(/VNDirect/);
  await expect(page.getByRole("region", { name: "Chuỗi tác động vĩ mô" }).getByTestId("chain-fuel")).toContainText("Giá xăng trong nước");
});
