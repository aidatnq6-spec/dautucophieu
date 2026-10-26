import { expect, test } from "@playwright/test";
import { signIn } from "./helpers";

// Synthetic fixture data only: FPT has statements (P/E 12 every year, cash dividends), VCB has none.
test.beforeEach(async ({ context }) => signIn(context));

async function openPage(page: import("@playwright/test").Page) {
  await page.goto("/fair-value");
  await expect(page.getByText("Đang tải…")).toHaveCount(0);
}

test("each watched ticker gets a fair-value range and a verdict, with the methods behind it", async ({ page }) => {
  await openPage(page);
  const table = page.getByRole("table", { name: "Định giá tham khảo" });
  const fpt = table.getByRole("row", { name: /FPT/ });
  await expect(fpt).toContainText("Đắt");
  await expect(table.getByRole("row", { name: /VCB/ })).toContainText("Chưa có báo cáo tài chính");
  await fpt.getByRole("button", { name: "Chi tiết FPT" }).click();
  const detail = page.getByRole("region", { name: "Phương án định giá FPT" });
  await expect(detail).toContainText("P/E lịch sử");
  await expect(detail).toContainText("12.000");
  await expect(detail).toContainText("Cần ít nhất 3 mã cùng ngành có số liệu");
  await expect(page.getByText(/không phải khuyến nghị/)).toBeVisible();
  await expect(page.getByText(/Lợi suất yêu cầu 13,0%/)).toBeVisible();
});

test("no horizontal scroll on the valuation page at 375px", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 900 });
  await openPage(page);
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(0);
  const scrollers = await page.evaluate(() => [...document.querySelectorAll("main *")]
    .filter((el) => el.scrollWidth > el.clientWidth + 1 && ["auto", "scroll"].includes(getComputedStyle(el).overflowX)).length);
  expect(scrollers).toBe(0);
});
