import { expect, test } from "@playwright/test";
import { signIn } from "./helpers";

test.beforeEach(async ({ context }) => signIn(context));

// Made-up figures only: 10 rooms, 5 high months at 10m 90% let, 7 low months at 8m 70% let.
test("a building's revenue by season, its costs and the profit of buying or leasing it", async ({ page }) => {
  await page.goto("/building");
  await expect(page.getByRole("link", { name: "Lợi nhuận tòa nhà" })).toBeVisible();
  const fill = async (label: string, value: string) => page.getByLabel(label, { exact: true }).fill(value);
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
  await expect(page.getByLabel("Số phòng", { exact: true })).toHaveValue("10");
});


test("scenarios and the sensitivity table follow the entered building", async ({ page }) => {
  await page.goto("/building");
  const fill = async (label: string, value: string) => page.getByLabel(label, { exact: true }).fill(value);
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
  const fill = async (label: string, value: string) => page.getByLabel(label, { exact: true }).fill(value);
  await fill("Số phòng", "8"); await fill("Mùa cao điểm: số tháng", "12"); await fill("Giá (đ/phòng/tháng)", "9000000"); await fill("Có khách (%)", "75");
  const name = `Tòa thử ${Date.now() % 100000}`;  // unique: the store is shared and a retry runs again
  const saved = page.getByRole("region", { name: "Các phương án đã lưu" });
  await saved.getByLabel("Tên phương án").fill(name);
  await saved.getByRole("button", { name: "Lưu phương án này" }).click();
  const row = saved.getByRole("table", { name: "So sánh các phương án" }).getByRole("row", { name: new RegExp(name) });
  await expect(row).toContainText("54.000.000");   // 8 × 9m × 75%
  await fill("Số phòng", "20");
  await row.getByRole("button", { name: "Mở" }).click();
  await expect(page.getByLabel("Số phòng", { exact: true })).toHaveValue("8");
  page.once("dialog", (d) => void d.accept());
  await row.getByRole("button", { name: `Xóa phương án ${name}` }).click();
  await expect(saved.getByRole("row", { name: new RegExp(name) })).toHaveCount(0);
});
