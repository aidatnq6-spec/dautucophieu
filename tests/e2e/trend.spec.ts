import { expect, test } from "@playwright/test";
import { signIn } from "./helpers";

// Synthetic fixture snapshot only.
test.beforeEach(async ({ context }) => signIn(context));

async function openTrend(page: import("@playwright/test").Page) {
  await page.goto("/trend");
  await expect(page.getByText("Đang tải…")).toHaveCount(0);
}

test("the board shows MACD and RSI by frame and highlights what changed", async ({ page }) => {
  await openTrend(page);
  const fpt = page.getByRole("table", { name: "FPT" });
  await expect(fpt.getByRole("row", { name: /MACD/ })).toContainText("up,>0");
  await expect(fpt.getByRole("row", { name: /RSI/ })).toContainText("63");
  await expect(page.getByRole("region", { name: "FPT" })).toContainText("D1 MACD trước: down,<0");
  await expect(page.getByRole("region", { name: "FPT" })).toContainText("D1 RSI trước: trung tính");
  // Reasons for empty cells sit once under the card, naming their frames, not inside the narrow cells.
  await expect(page.getByRole("region", { name: "FPT" })).toContainText("H1: Chưa có giá của phiên");
  await expect(page.getByRole("region", { name: "VN10Y" })).toContainText("M, W, D1, H4, H1: Không có nguồn miễn phí hợp lệ");
  await expect(page.getByText(/so với phiên 2026-10-22/)).toBeVisible();
  await expect(page.getByText(/không phải khuyến nghị/)).toBeVisible();
});

for (const width of [375, 1440]) {
  test(`the trend page has no horizontal scroll, on the page or inside any card, at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await openTrend(page);
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    expect(overflow).toBeLessThanOrEqual(0);
    const wider = await page.evaluate(() => [...document.querySelectorAll(".trend-card")]
      .filter((card) => [...card.querySelectorAll("*")].some((el) => el.scrollWidth > el.clientWidth + 1 && ["auto", "scroll"].includes(getComputedStyle(el).overflowX)))
      .map((card) => card.getAttribute("aria-label")));
    expect(wider).toEqual([]);
    const tooWide = await page.evaluate(() => [...document.querySelectorAll(".trend-card table")]
      .filter((t) => t.getBoundingClientRect().width > (t.closest(".trend-card") as HTMLElement).getBoundingClientRect().width + 1).length);
    expect(tooWide).toBe(0);
  });
}
