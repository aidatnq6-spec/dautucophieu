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
