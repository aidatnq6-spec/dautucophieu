import { expect, test } from "@playwright/test";
import { signIn } from "./helpers";

// Synthetic fixture data only: VN-Index 1,700 for 20 sessions then 1,774.15; FPT (IT) up, VCB (banks) unpriced.
test.beforeEach(async ({ context }) => signIn(context));

async function openMarket(page: import("@playwright/test").Page) {
  await page.goto("/market");
  await expect(page.getByText("Đang tải…")).toHaveCount(0);
}

test("market page shows the index, breadth and sectors, and says macro data is missing", async ({ page }) => {
  await openMarket(page);
  const index = page.getByRole("region", { name: "Thị trường chung" });
  await expect(index).toContainText("1.774,15");
  await expect(index).toContainText("+4,36%");
  await expect(index).toContainText("trên đường trung bình 20 phiên (1.703,71)");
  await expect(index).toContainText("1 mã tăng");

  const sectors = page.getByRole("table", { name: "Diễn biến theo ngành" });
  await expect(sectors.getByRole("row", { name: /Công nghệ Thông tin/ })).toContainText("+14,00%");
  await expect(sectors.getByRole("row", { name: /Ngân hàng/ })).toContainText("—");

  await expect(page.getByRole("region", { name: "Vĩ mô" })).toContainText("Chưa có dữ liệu vĩ mô");
  await expect(page.getByText(/không phải khuyến nghị/)).toBeVisible();
});

test("no horizontal page scroll on the market page at 375px", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 900 });
  await openMarket(page);
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(0);
});
