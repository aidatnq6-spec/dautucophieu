import { expect, test } from "@playwright/test";
import { signIn } from "./helpers";

// Thống kê lịch sử on the fixture's stored VN-Index closes: the page and its horizon switch.
test.beforeEach(async ({ context }) => signIn(context));

test("Thống kê lịch sử shows the P/E groups and the lights' check, and the horizon can be changed", async ({ page }) => {
  await page.goto("/history");
  await expect(page.getByRole("heading", { level: 1, name: "Thống kê lịch sử" })).toBeVisible();
  await expect(page.getByRole("table", { name: "VN-Index sau đó theo nhóm P/E" })).toBeVisible();
  await expect(page.getByTestId("light-history-oil")).toContainText("Giá dầu WTI");
  await expect(page.getByTestId("history-summary")).toContainText("không phải dự báo hay khuyến nghị");
  await expect(page.getByTestId("history-summary")).toContainText("không dùng AI");
  await expect(page.getByRole("table", { name: "VN-Index sau cú sốc", exact: true })).toContainText("VN-Index giảm từ 3% trong một phiên");
  await expect(page.getByRole("table", { name: "VN-Index sau đó theo nhóm P/E" })).toContainText("Giảm sâu nhất trong kỳ: tệ nhất");
  await expect(page.getByRole("table", { name: "VN-Index sau cú sốc chồng cú sốc" })).toContainText("khi đang dưới trung bình 200 phiên");
  await page.getByRole("radio", { name: "500 phiên" }).click();
  await expect(page.getByRole("table", { name: "VN-Index sau đó theo nhóm P/E" })).toContainText(/không đủ dữ liệu cho kỳ này|chưa có mẫu/);  // the fixture's history is short for 500 sessions
  await page.getByRole("radio", { name: "60 phiên" }).click();
  await expect(page.getByRole("radio", { name: "60 phiên" })).toHaveAttribute("aria-checked", "true");
  await expect(page.getByRole("region", { name: "Số phiên nhìn tới" })).toContainText("VN-Index 60 phiên sau");
  await expect(page.getByRole("navigation", { name: "Điều hướng chính" }).getByRole("link", { name: "Thống kê lịch sử" })).toBeVisible();
});

test("two conditions can be chosen and the four combinations are shown with today's conditions", async ({ page }) => {
  await page.goto("/history");
  const box = page.getByRole("region", { name: "Trạng thái vĩ mô hai điều kiện" });
  await expect(box.getByRole("table", { name: "Vĩ mô hôm nay" })).toContainText("Lạm phát (CPI) tăng so với 3 tháng trước");
  await box.getByLabel("Điều kiện B").selectOption("oil_up");
  const table = box.getByRole("table", { name: "VN-Index sau đó theo hai điều kiện" });
  await expect(table.getByRole("row")).toHaveCount(6);  // header, four combinations, every day
  await expect(box).toContainText("B: Giá dầu tăng trong 3 tháng");
  await box.getByRole("radio", { name: "2%" }).click();
  await expect(box.getByRole("table", { name: "Vĩ mô hôm nay" })).toContainText("Tỷ giá USD/VND tăng hơn 2% trong 3 tháng");
});
