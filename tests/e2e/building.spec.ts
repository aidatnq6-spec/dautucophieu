import { expect, test } from "@playwright/test";
import { signIn } from "./helpers";

test.beforeEach(async ({ context }) => signIn(context));
// the building tab only: the other tabs stay on the page (hidden) and share some labels
const tab = (page: import("@playwright/test").Page) => page.getByRole("tabpanel", { name: "Tòa nhà cho thuê: lợi nhuận vận hành" });

// Made-up figures only: 10 rooms, 5 high months at 10m 90% let, 7 low months at 8m 70% let.
test("a building's revenue by season, its costs and the profit of buying or leasing it", async ({ page }) => {
  await page.goto("/building");
  await expect(page).toHaveURL(/\/loan\?tab=toa-nha/);   // the old address arrives at the tab
  await expect(page.getByRole("tab", { name: "Tòa nhà cho thuê: lợi nhuận vận hành" })).toHaveAttribute("aria-selected", "true");
  const fill = async (label: string, value: string) => tab(page).getByLabel(label, { exact: true }).fill(value);
  await fill("Số phòng", "10");
  await fill("Mùa cao điểm: số tháng", "5"); await fill("Giá (đ/phòng/tháng)", "10000000"); await fill("Có khách (%)", "90");
  await fill("Mùa thấp điểm: số tháng", "7"); await fill("Giá thấp điểm (đ/phòng/tháng)", "8000000"); await fill("Có khách thấp điểm (%)", "70");
  await fill("Giá cao nhất môi giới đưa (đ/phòng/tháng)", "12000000");
  await fill("Hoa hồng môi giới, mạng xã hội (%)", "10"); await fill("Thuế GTGT (%)", "5"); await fill("Thuế TNCN (%)", "5");
  await fill("Vệ sinh tổng thể", "8000000");
  const result = page.getByRole("complementary", { name: "Kết quả lợi nhuận tòa nhà" });
  await expect(result).toContainText("70.166.667");             // 842m a year ÷ 12
  await expect(result).toContainText("cao hơn doanh thu thực tế 71,0%");
  await expect(result.getByRole("table", { name: "Chi phí vận hành mỗi tháng" })).toContainText("Tổng chi phí");
  await fill("Tiền thuê nguyên tòa (đ/tháng)", "20000000");
  await expect(result.getByRole("region", { name: "Kết quả nếu thuê lại nguyên tòa" })).toContainText("Doanh thu hòa vốn mỗi tháng");
  await fill("Giá mua (đ)", "5000000000"); await fill("Vốn tự có (đ)", "5000000000");
  await expect(result.getByRole("region", { name: "Kết quả nếu mua tòa" })).toContainText("Lợi suất ròng trên tổng tiền bỏ ra");
  await page.reload();  // the draft is kept in this browser
  await expect(tab(page).getByLabel("Số phòng", { exact: true })).toHaveValue("10");
});


test("scenarios and the sensitivity table follow the entered building", async ({ page }) => {
  await page.goto("/building");
  const fill = async (label: string, value: string) => tab(page).getByLabel(label, { exact: true }).fill(value);
  await fill("Số phòng", "10");
  await fill("Mùa cao điểm: số tháng", "12"); await fill("Giá (đ/phòng/tháng)", "10000000"); await fill("Có khách (%)", "80");
  await fill("Mùa thấp điểm: số tháng", ""); await fill("Giá thấp điểm (đ/phòng/tháng)", ""); await fill("Có khách thấp điểm (%)", "");
  await fill("Vệ sinh tổng thể", "8000000");
  const box = page.getByRole("region", { name: "Kịch bản và độ nhạy" });
  await fill("Kịch bản xấu: có khách ± (điểm %)", "-20");
  await fill("Kịch bản xấu: giá thuê ± (%)", "-10");
  const cases = box.getByRole("table", { name: "Ba kịch bản" });
  await expect(cases.getByRole("row", { name: /Xấu/ })).toContainText("54.000.000");   // 10 × 9m × 60%
  await expect(cases.getByRole("row", { name: /Cơ sở/ })).toContainText("80.000.000");
  const grid = box.getByRole("table", { name: "Bảng độ nhạy theo tỷ lệ có khách và giá thuê" });
  await expect(grid.getByRole("row", { name: /^100%/ })).toContainText("92.000.000");   // 100m full, less 8m cleaning
});


test("a plan is saved under a name, compared with the others, reopened and deleted", async ({ page }) => {
  await page.goto("/building");
  const fill = async (label: string, value: string) => tab(page).getByLabel(label, { exact: true }).fill(value);
  await fill("Số phòng", "8"); await fill("Mùa cao điểm: số tháng", "12"); await fill("Giá (đ/phòng/tháng)", "9000000"); await fill("Có khách (%)", "75");
  const name = `Tòa thử ${Date.now() % 100000}`;  // unique: the store is shared and a retry runs again
  // the Lưu button sits at the top of the result panel, right after the boxes are filled
  const result = page.getByRole("complementary", { name: "Kết quả lợi nhuận tòa nhà" });
  await result.getByLabel("Tên phương án").fill(name);
  await result.getByRole("button", { name: "Lưu phương án" }).click();
  await expect(result.getByRole("status")).toContainText(`Đã lưu "${name}"`);
  const saved = page.getByRole("region", { name: "Các phương án đã lưu" });
  const row = saved.getByRole("table", { name: "So sánh các phương án" }).getByRole("row", { name: new RegExp(name) });
  await expect(row).toContainText("54.000.000");   // 8 × 9m × 75%
  const bars = saved.getByRole("img", { name: "So sánh lợi nhuận mỗi tháng của các phương án" });
  await expect(bars).toContainText(name.slice(0, 23));
  await expect(bars.locator("rect").first()).toBeVisible();
  await fill("Số phòng", "20");
  await row.getByRole("button", { name: "Mở" }).click();
  await expect(tab(page).getByLabel("Số phòng", { exact: true })).toHaveValue("8");
  // the opened plan is saved again under its own name
  await expect(result.getByLabel("Tên phương án")).toHaveValue(name);
  await fill("Số phòng", "10");
  await result.getByRole("button", { name: "Lưu thay đổi" }).click();
  await expect(row).toContainText("67.500.000");   // 10 × 9m × 75%
  page.once("dialog", (d) => void d.accept());
  await row.getByRole("button", { name: `Xóa phương án ${name}` }).click();
  await expect(saved.getByRole("row", { name: new RegExp(name) })).toHaveCount(0);
});


test("the recording's figures show under each line and fill only the empty single-value boxes", async ({ page }) => {
  await page.goto("/building");
  await expect(page.getByText("Bài: 8,3–10% (môi giới cá nhân, mạng xã hội)")).toBeVisible();
  await tab(page).getByLabel("Thuế GTGT (%)", { exact: true }).fill("8");
  await page.getByRole("button", { name: "Điền gợi ý từ bài vào ô còn trống" }).click();
  await expect(tab(page).getByLabel("Hoa hồng OTA (%)", { exact: true })).toHaveValue("15");
  await expect(tab(page).getByLabel("Thuế GTGT (%)", { exact: true })).toHaveValue("8");             // typed: kept
  await expect(tab(page).getByLabel("Vệ sinh tổng thể", { exact: true })).toHaveValue("8.000.000");
  await expect(tab(page).getByLabel("Hoa hồng môi giới, mạng xã hội (%)", { exact: true })).toHaveValue("");  // a range: left to the owner
  await expect(tab(page).getByLabel("Tên thiết bị 4")).toHaveValue("Điều hòa");
});


test("commission typed as one month of rent on a one-year lease is 583.333 đ a month for a 7m room", async ({ page }) => {
  await page.goto("/building");
  const fill = async (label: string, value: string) => tab(page).getByLabel(label, { exact: true }).fill(value);
  await fill("Số phòng", "1"); await fill("Mùa cao điểm: số tháng", "12"); await fill("Giá (đ/phòng/tháng)", "7000000"); await fill("Có khách (%)", "100");
  await fill("Hoa hồng môi giới: số tháng tiền thuê mỗi hợp đồng", "1"); await fill("Thời hạn hợp đồng bình quân (tháng)", "12");
  await expect(page.getByTestId("broker-share")).toContainText("= 8,333% doanh thu mỗi tháng");
  const costs = page.getByRole("table", { name: "Chi phí vận hành mỗi tháng" });
  await expect(costs.getByRole("row", { name: /Hoa hồng bán phòng/ })).toContainText("583.333");
});


test("a sum of money typed in the broker's months is refused with what to type instead", async ({ page }) => {
  await page.goto("/building");
  const fill = async (label: string, value: string) => tab(page).getByLabel(label, { exact: true }).fill(value);
  await fill("Số phòng", "1"); await fill("Mùa cao điểm: số tháng", "12"); await fill("Giá (đ/phòng/tháng)", "7000000"); await fill("Có khách (%)", "100");
  await fill("Hoa hồng môi giới: số tháng tiền thuê mỗi hợp đồng", "7000000"); await fill("Thời hạn hợp đồng bình quân (tháng)", "12");
  const result = page.getByRole("complementary", { name: "Kết quả lợi nhuận tòa nhà" });
  await expect(result.getByRole("alert")).toContainText("không phải số tiền");
  await expect(result.getByRole("table", { name: "Chi phí vận hành mỗi tháng" })).toHaveCount(0);
});


test("the breakeven occupancy sits above the table, and the printed page keeps the result and the figures, not the boxes", async ({ page }) => {
  await page.goto("/building");
  const fill = async (label: string, value: string) => tab(page).getByLabel(label, { exact: true }).fill(value);
  await fill("Số phòng", "10"); await fill("Mùa cao điểm: số tháng", "12"); await fill("Giá (đ/phòng/tháng)", "10000000"); await fill("Có khách (%)", "80");
  await fill("Vệ sinh tổng thể", "8000000"); await fill("Tiền thuê nguyên tòa (đ/tháng)", "50000000");
  await expect(page.getByTestId("breakeven")).toContainText("vận hành 8,0%");            // 8m of 100m full
  await expect(page.getByTestId("breakeven")).toContainText("thuê lại (sau tiền thuê tòa) 58,0%");  // (8m + 50m) of 100m
  await expect(page.getByRole("button", { name: "In bản 1 trang" })).toBeVisible();
  await page.emulateMedia({ media: "print" });
  await expect(page.getByRole("region", { name: "Bản in phương án" })).toContainText("Phương án chưa lưu");
  await expect(page.getByRole("table", { name: "Số đầu vào" })).toContainText("Tiền thuê nguyên tòa (đ/tháng)");
  await expect(tab(page).getByLabel("Số phòng", { exact: true })).toBeHidden();
  await expect(page.getByRole("complementary", { name: "Kết quả lợi nhuận tòa nhà" })).toBeVisible();
  await page.emulateMedia({ media: "screen" });
  await expect(page.getByRole("region", { name: "Bản in phương án" })).toBeHidden();
});


test("the profit chart draws one line a model with its breakeven", async ({ page }) => {
  await page.goto("/building");
  const fill = async (label: string, value: string) => tab(page).getByLabel(label, { exact: true }).fill(value);
  await fill("Số phòng", "10"); await fill("Mùa cao điểm: số tháng", "12"); await fill("Giá (đ/phòng/tháng)", "10000000"); await fill("Có khách (%)", "80");
  await fill("Vệ sinh tổng thể", "8000000"); await fill("Tiền thuê nguyên tòa (đ/tháng)", "50000000");
  const chart = page.getByRole("img", { name: "Lợi nhuận mỗi tháng theo tỷ lệ có khách" });
  await expect(chart.locator("polyline")).toHaveCount(2);
  await expect(page.locator(".bt-legend")).toContainText("Thuê lại (sau tiền thuê tòa) (hòa vốn 58,0%)");
});


test("buying is weighed against the deposit over the years held: the price the building must reach and its yearly rise", async ({ page }) => {
  await page.goto("/loan?tab=toa-nha");
  const fill = async (label: string, value: string) => tab(page).getByLabel(label, { exact: true }).fill(value);
  await fill("Số phòng", "1"); await fill("Mùa cao điểm: số tháng", "12"); await fill("Giá (đ/phòng/tháng)", "12000000"); await fill("Có khách (%)", "100");
  await fill("Khác", "2000000");
  await fill("Giá mua (đ)", "3000000000"); await fill("Thuế phí sang tên (đ)", "100000000"); await fill("Vốn tự có (đ)", "1600000000");
  await fill("Lãi vay (%/năm)", "9"); await fill("Thời hạn vay (năm)", "15");
  await fill("Số năm nắm giữ (để so với gửi tiết kiệm)", "10"); await fill("Lãi tiền gửi để so (%/năm)", "6");
  const buy = page.getByRole("region", { name: "Kết quả nếu mua tòa" });
  await expect(buy).toContainText("Giá tòa cần đạt sau 10 năm để bằng gửi tiết kiệm");
  await expect(buy).toContainText("Nếu giữ vốn tự có ở tiền gửi 10 năm");
  // the same figures as the one-flat tab for the same flat
  const flat = page.getByRole("region", { name: "Mua nhà cho thuê hay giữ tiền gửi" });
  await page.getByRole("tab", { name: "Căn hộ lẻ: mua hay gửi tiết kiệm" }).click();
  for (const [label, value] of [["Giá nhà (đ)", "3000000000"], ["Vốn tự có (đ)", "1600000000"], ["Chi phí mua ban đầu (đ)", "100000000"],
    ["Tiền thuê mỗi tháng (đ)", "12000000"], ["Chi phí giữ nhà mỗi tháng (đ)", "2000000"], ["Lãi vay (%/năm)", "9"], ["Thời hạn vay (năm)", "15"],
    ["Lãi tiền gửi (%/năm)", "6"], ["Số năm nắm giữ", "10"]]) await flat.getByLabel(label, { exact: true }).fill(value);
  await flat.getByLabel("Cách trả khoản vay mua nhà").selectOption("annuity");
  const flatText = await flat.textContent();
  await page.getByRole("tab", { name: "Tòa nhà cho thuê: lợi nhuận vận hành" }).click();
  const needed = (await buy.locator("dt:has-text('Giá tòa cần đạt') + dd").textContent())!.trim();
  expect(flatText).toContain(needed);
});


test("the purchase loan opens in the Khoản vay tab with its figures filled in", async ({ page }) => {
  await page.goto("/loan?tab=toa-nha");
  const fill = async (label: string, value: string) => tab(page).getByLabel(label, { exact: true }).fill(value);
  await fill("Số phòng", "10"); await fill("Mùa cao điểm: số tháng", "12"); await fill("Giá (đ/phòng/tháng)", "10000000"); await fill("Có khách (%)", "80");
  await fill("Giá mua (đ)", "5000000000"); await fill("Vốn tự có (đ)", "2500000000"); await fill("Lãi vay (%/năm)", "9,5"); await fill("Thời hạn vay (năm)", "15");
  await page.getByRole("button", { name: "Xem lịch trả nợ chi tiết" }).click();
  await expect(page.getByRole("tab", { name: "Khoản vay" })).toHaveAttribute("aria-selected", "true");
  const loan = page.getByRole("tabpanel", { name: "Khoản vay" });
  await expect(loan).toContainText("Đang xem khoản vay mua tòa đang tính (vay 2.500.000.000 đ, 9,5%/năm, 15 năm)");
  await expect(loan.getByRole("complementary", { name: "Kết quả khoản vay" })).toContainText("2.500.000.000");
});
