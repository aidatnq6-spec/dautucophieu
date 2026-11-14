import { expect, test } from "@playwright/test";
import { signIn } from "./helpers";

// Synthetic fixture data only: FPT has a 21-session history, VCB has no stored price.
test.beforeEach(async ({ context }) => signIn(context));

async function openWatchlist(page: import("@playwright/test").Page) {
  await page.goto("/watchlist");
  await expect(page.getByText("Đang tải…")).toHaveCount(0);
}

test("the watchlist shows prices and changes without recommendations", async ({ page }) => {
  await openWatchlist(page);
  const table = page.getByRole("table", { name: "Danh sách theo dõi" });
  const fpt = table.getByRole("row", { name: /FPT/ });
  await expect(fpt).toContainText("57.000");
  await expect(fpt).toContainText("+3,64%");
  await expect(fpt).toContainText("+14,00%");
  await expect(table.getByRole("row", { name: /VCB/ })).toContainText("Chưa có giá");
  await expect(page.getByText(/không phải khuyến nghị/)).toBeVisible();
});

test("filters by index group", async ({ page }) => {
  await openWatchlist(page);
  const table = page.getByRole("table", { name: "Danh sách theo dõi" });
  await page.getByRole("radio", { name: "VN30" }).check();
  await expect(table.getByRole("row", { name: /FPT/ })).toBeVisible();
  await expect(table.getByRole("row", { name: /VCB/ })).toHaveCount(0);
});

test("each index group shows its own date, and VN100 is flagged after VN30 changed", async ({ page }) => {
  await openWatchlist(page);
  await expect(page.getByTestId("groups-caption")).toContainText("VN100: danh sách lưu ngày 20/10/2026 (không có nguồn tự động");
  await expect(page.getByTestId("vn100-review")).toContainText("VN30 đổi thành phần ngày 25/10/2026");
});

for (const width of [375, 1440]) {
  test(`no horizontal page scroll on the watchlist at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await openWatchlist(page);
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    expect(overflow).toBeLessThanOrEqual(0);
  });
}
