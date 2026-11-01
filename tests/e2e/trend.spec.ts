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

test("the price board lists the indices and watched tickers in exchange colours and opens a candle chart with MACD and RSI", async ({ page }) => {
  await openTrend(page);
  const box = page.getByRole("region", { name: "Bảng giá và biểu đồ" });
  const list = box.getByRole("table", { name: "Bảng giá" });
  await expect(list.getByRole("row", { name: /VNINDEX/ })).toContainText("1.741,62−13,99−0,80%");
  await expect(list.getByRole("row", { name: /FPT/ })).toContainText("56,30+3,60+6,83%");
  await expect(list.getByRole("row", { name: /FPT/ }).locator("td").first()).toHaveClass(/tb-ceil/);  // at the ceiling: purple
  await expect(box.getByTestId("tb-status")).toContainText("Chưa có giá: VN30");
  await expect(box.getByRole("group", { name: "Biểu đồ VNINDEX" }).getByTestId("tb-chart-caption")).toContainText("Nến ngày · 60 nến · điểm");
  await list.getByRole("row", { name: /FPT/ }).click();
  const fpt = box.getByRole("group", { name: "Biểu đồ FPT" });
  await expect(fpt.getByTestId("tb-chart-caption")).toContainText("nghìn đồng");
  await expect(fpt.getByTestId("tb-canvas").locator("canvas").first()).toBeVisible();
  await expect(fpt.getByTestId("tb-canvas")).toHaveAttribute("data-live-close", "56.3");  // today's candle follows the board
  await fpt.getByRole("radio", { name: "Tuần" }).click();
  await expect(fpt.getByTestId("tb-chart-caption")).toContainText("Nến tuần");
  await expect(fpt.getByTestId("tb-chart-caption")).toContainText("gộp từ nến ngày");
  await fpt.getByRole("radio", { name: "Tháng" }).click();
  await expect(fpt.getByTestId("tb-chart-caption")).toContainText("Nến tháng");
  await expect(fpt.getByTestId("tb-canvas").locator("canvas").first()).toBeVisible();
  await fpt.getByRole("radio", { name: "1 giờ" }).click();
  await expect(fpt.getByTestId("tb-chart-caption")).toContainText("Nến 1 giờ");
  await expect(box).toContainText("trần 56,30");
  // Vĩ mô rows: closes with their date, Bitcoin live against 24 hours before, missing series without a number.
  await expect(list.getByRole("row", { name: /Bitcoin/ })).toContainText("so với 24 giờ trước77.220,00−780,00−1,00%");
  await expect(list.getByRole("row", { name: /DXY/ })).toContainText("đóng cửa 29/09");
  await expect(list.getByRole("row", { name: /Dầu WTI/ })).toContainText("Dầu WTI———");
  await list.getByRole("row", { name: /DXY/ }).click();
  const dxy = box.getByRole("group", { name: "Biểu đồ DXY" });
  await expect(dxy).toContainText("Nguồn chỉ có giá ngày");  // still on the hourly frame
  await dxy.getByRole("radio", { name: "Ngày" }).click();
  await expect(dxy.getByTestId("tb-chart-caption")).toContainText("Giá đóng cửa theo ngày · 60 điểm · điểm");
});

test("a price level is set for the ticker picked, listed as waiting, and removed", async ({ page }) => {
  await openTrend(page);
  const box = page.getByRole("region", { name: "Bảng giá và biểu đồ" });
  await box.getByRole("table", { name: "Bảng giá" }).getByRole("row", { name: /FPT/ }).click();
  const alerts = box.getByRole("region", { name: "Cảnh báo giá" });
  await alerts.getByLabel("Điều kiện").selectOption("below");
  await alerts.getByLabel("Mức giá FPT").fill("50,5");
  await expect(alerts.getByTestId("alert-preview")).toHaveText("Mức: 50,50");
  await alerts.getByRole("button", { name: "Thêm" }).click();
  const list = alerts.getByRole("list", { name: "Danh sách cảnh báo" });
  await expect(list).toContainText("FPT ≤ 50,50");
  await expect(list).toContainText("đang chờ");
  await list.getByRole("button", { name: "Xóa cảnh báo FPT ≤ 50.5" }).click();
  await expect(alerts.getByRole("list", { name: "Danh sách cảnh báo" })).toHaveCount(0);
  await box.getByRole("table", { name: "Bảng giá" }).getByRole("row", { name: /Bitcoin/ }).click();
  await expect(alerts).toContainText("chưa có cho các biến vĩ mô");
});

test("a level and a trend line are drawn on the price pane, kept per frame, and cleared", async ({ page }) => {
  await openTrend(page);
  const box = page.getByRole("region", { name: "Bảng giá và biểu đồ" });
  await box.getByRole("table", { name: "Bảng giá" }).getByRole("row", { name: /FPT/ }).click();
  const fpt = box.getByRole("group", { name: "Biểu đồ FPT" });
  const canvas = fpt.getByTestId("tb-canvas");
  await expect(canvas.locator("canvas").first()).toBeVisible();
  const tools = fpt.getByRole("toolbar", { name: "Công cụ vẽ" });
  const size = (await canvas.boundingBox())!;
  await tools.getByRole("button", { name: "Đường ngang" }).click();
  await canvas.click({ position: { x: size.width * 0.5, y: 120 } });
  const list = fpt.getByRole("list", { name: "Hình vẽ" });
  await expect(list).toContainText("Đường ngang");
  await expect(canvas).toHaveAttribute("data-drawings", "1");
  await fpt.getByRole("radio", { name: "1 giờ" }).click();
  await expect(fpt.getByTestId("tb-chart-caption")).toContainText("Nến 1 giờ");
  await expect(list).toContainText("Đường ngang");  // a level shows on both frames
  await expect(tools.getByRole("button", { name: "Con trỏ" })).toHaveAttribute("aria-pressed", "true");  // back to the pointer once drawn
  await tools.getByRole("button", { name: "Đường xu hướng" }).click();
  // Press on one candle, drag to another, let go.
  await page.mouse.move(size.x + size.width * 0.4, size.y + 150);
  await page.mouse.down();
  await page.mouse.move(size.x + size.width * 0.55, size.y + 125, { steps: 5 });
  await page.mouse.move(size.x + size.width * 0.7, size.y + 100, { steps: 5 });
  await page.mouse.up();
  await expect(list).toContainText("Đường xu hướng");
  await expect(canvas).toHaveAttribute("data-drawings", "2");
  // A press let go on the same candle draws nothing.
  await tools.getByRole("button", { name: "Đường xu hướng" }).click();
  await canvas.click({ position: { x: size.width * 0.3, y: 140 } });
  await expect(canvas).toHaveAttribute("data-drawings", "2");
  await page.keyboard.press("Escape");
  await fpt.getByRole("radio", { name: "Ngày" }).click();
  await expect(fpt.getByTestId("tb-chart-caption")).toContainText("Nến ngày");
  await expect(list).not.toContainText("Đường xu hướng");  // the hourly trend line stays on the hourly frame
  page.once("dialog", (d) => void d.accept());
  await tools.getByRole("button", { name: "Xóa hết" }).click();
  await expect(fpt.getByRole("list", { name: "Hình vẽ" })).toHaveCount(0);
});

test("the MACD and RSI panes keep a readable height under the candles", async ({ page }) => {
  await openTrend(page);
  const canvas = page.getByRole("region", { name: "Bảng giá và biểu đồ" }).getByTestId("tb-canvas");
  await expect(canvas.locator("canvas").first()).toBeVisible();
  // One table row per pane, with a thin separator row between them.
  const panes = async () => (await canvas.locator("table > tr, table > tbody > tr").evaluateAll((rows) => rows.map((r) => r.getBoundingClientRect().height)))
    .filter((h) => h > 5);
  await expect.poll(async () => (await panes()).length).toBe(4);  // price, MACD, RSI, time axis
  const [price, macd, rsi] = await panes();
  expect(price).toBeGreaterThan(250);
  expect(macd).toBeGreaterThan(80);
  expect(rsi).toBeGreaterThan(70);
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
