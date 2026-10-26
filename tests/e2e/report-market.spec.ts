import { expect, test } from "@playwright/test";
import { seedOwner, signIn } from "./helpers";

// Synthetic fixture snapshot for session 2026-10-23 (data/brief/2026-10-23.json in the fixture backend).
test.describe.configure({ mode: "serial" });
test.beforeEach(async ({ context }) => signIn(context));

async function openBrief(page: import("@playwright/test").Page) {
  await seedOwner(page);
  await page.goto("/reports");
  await expect(page.getByText("Đang tải…")).toHaveCount(0);
  await page.getByLabel("Ngày phiên").fill("2026-10-23");
  await page.getByRole("button", { name: "Tạo bản tin" }).click();
  await expect(page.getByRole("status")).toContainText(/Đã phát hành|Thiếu dữ liệu/);
  await page.getByRole("link", { name: "Phiên 2026-10-23" }).first().click();
  await expect(page.getByRole("heading", { name: "Thị trường phiên 23/10" })).toBeVisible();
}

test("the brief opens with the session's market: indices, liquidity, breadth, foreign, proprietary, sectors, tickers, news", async ({ page }) => {
  await openBrief(page);
  const m = page.getByRole("region", { name: "Thị trường phiên" });
  await expect(m).toContainText("VN-Index 1.658,52 +12,30 điểm (+0,75%)");
  await expect(m).toContainText("VN30: chưa có số liệu (Chưa có giá chỉ số phiên này)");
  await expect(m).toContainText("17.010,24 tỷ đồng");
  await expect(m).toContainText("180 tăng · 150 giảm · 50 đứng giá · 27 không giao dịch");
  await expect(m).toContainText("Bán ròng mạnh: VHM −210,50 tỷ");
  await expect(m).toContainText("Tự doanhChưa có số liệu (Chưa có nguồn miễn phí)");
  await expect(m).toContainText("Công nghệ Thông tin +1,20%");
  const fpt = m.getByRole("list", { name: "Mã đang theo dõi" }).getByRole("listitem").first();  // FPT is held in the fixture: listed first
  await expect(fpt).toContainText("FPT");
  await expect(fpt).toContainText("Đang nắm");
  await expect(fpt).toContainText("57.000 +2.000 (+3,64%)");
  await expect(m.getByRole("link", { name: "FPT ký hợp đồng AI lớn" })).toBeVisible();
  await expect(page.getByRole("columnheader", { name: "Phạm vi" })).toHaveCount(0);
});

test("no horizontal scroll on the brief at 375px", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 900 });
  await openBrief(page);
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(0);
});

for (const width of [1280, 375]) {
  test(`the brief's holdings table: signed coloured gains, no weight column, no scroller at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await openBrief(page);
    const table = page.getByRole("table", { name: "Danh mục đang nắm giữ" });
    await expect(table.getByRole("columnheader", { name: /Tỷ trọng/ })).toHaveCount(0);
    const gain = table.locator("td.gain").first();
    await expect(gain).toHaveText(/^[+−]\d/);  // a sign, no "Lãi"/"Lỗ" word
    for (const cell of await table.locator("td.gain").all()) await expect(cell).not.toHaveText(/Lãi|Lỗ/);
    const scrollers = await page.evaluate(() => [...document.querySelectorAll("main *")]
      .filter((el) => el.scrollWidth > el.clientWidth + 1 && ["auto", "scroll"].includes(getComputedStyle(el).overflowX)).length);
    expect(scrollers).toBe(0);
  });
}

