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

for (const width of [375, 1440]) {
  test(`no horizontal page scroll on the watchlist at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await openWatchlist(page);
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    expect(overflow).toBeLessThanOrEqual(0);
  });
}
