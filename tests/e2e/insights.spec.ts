import { expect, test } from "@playwright/test";
import { signIn } from "./helpers";

// Synthetic fixture records only: two ACBS-shaped reports (Công nghệ benefits; Ngân hàng split) and one SSI title.
test.beforeEach(async ({ context }) => signIn(context));

async function openPage(page: import("@playwright/test").Page) {
  await page.goto("/insights");
  await expect(page.getByText("Đang tải…")).toHaveCount(0);
}

test("macro verdicts, sectors linked to watched tickers, reports read and SSI titles", async ({ page }) => {
  await openPage(page);
  const now = page.getByRole("region", { name: "Vĩ mô hiện tại" });
  await expect(now).toContainText("Thuận lợi");
  await expect(now).toContainText("2/2 báo cáo");
  await expect(now).toContainText("Tăng trưởng GDP vững (mau-1)");
  await expect(page.getByRole("region", { name: "Triển vọng 6–12 tháng" })).toContainText("Trung tính");
  const table = page.getByRole("table", { name: "Ngành hưởng lợi và bất lợi" });
  await expect(table.getByRole("row", { name: /Công nghệ Thông tin/ })).toContainText("FPT");
  await expect(table.getByRole("row", { name: /Công nghệ Thông tin/ })).toContainText("Đắt");
  await expect(table.getByRole("row", { name: /Ngân hàng/ })).toContainText("Các nguồn khác ý");
  await expect(page.getByRole("list", { name: "Báo cáo đã đọc" })).toContainText("Báo cáo mẫu mau-1");
  await expect(page.getByRole("link", { name: "Cập nhật Ngành Thép mẫu" })).toBeVisible();
  await expect(page.getByText(/không phải khuyến nghị/)).toBeVisible();
  await expect(page.getByText(/1 báo cáo chưa đọc được.*không tải được tệp/)).toBeVisible();
});

test("no horizontal scroll on the insights page at 375px", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 900 });
  await openPage(page);
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(0);
  const scrollers = await page.evaluate(() => [...document.querySelectorAll("main *")]
    .filter((el) => el.scrollWidth > el.clientWidth + 1 && ["auto", "scroll"].includes(getComputedStyle(el).overflowX)).length);
  expect(scrollers).toBe(0);
});
