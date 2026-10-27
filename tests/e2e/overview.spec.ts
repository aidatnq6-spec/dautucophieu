import { expect, test } from "@playwright/test";
import { call, seedOwner, signIn } from "./helpers";

// Tổng quan uses the same compact holdings table as the after-close brief, and names the capital the rest of the app uses.
test.describe.configure({ mode: "serial" });
test.beforeEach(async ({ context }) => signIn(context));

test("holdings show signed gains without the weight and scope columns or the stale TWR note", async ({ page }) => {
  await seedOwner(page);
  await page.goto("/");
  const table = page.getByRole("table", { name: "Danh mục đang nắm giữ" });
  await expect(table.getByRole("columnheader", { name: /Tỷ trọng/ })).toHaveCount(0);
  await expect(table.getByRole("columnheader", { name: "Phạm vi" })).toHaveCount(0);
  await expect(table).not.toContainText(/Lãi |Lỗ /);
  await expect(page.getByText(/TWR\/XIRR/)).toHaveCount(0);
});

test("the capital line names the stock budget once a total is entered", async ({ page }) => {
  await seedOwner(page);
  const current = await (await call(page, "GET", "equity-budget")).json();
  if (current.budget.status !== "ok") {
    await call(page, "PUT", "equity-budget", { total: "2000000000", expected_version: current.version, request_id: `ov-eb-${Date.now()}` });
  }
  await page.goto("/");
  await expect(page.getByText(/Vốn dành cho cổ phiếu: [\d.]+ đ · Tiền trong sổ/)).toBeVisible();
});

test("no horizontal scroll on Tổng quan at 1280px and 375px", async ({ page }) => {
  for (const width of [1280, 375]) {
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/");
    await expect(page.getByRole("table", { name: "Danh mục đang nắm giữ" })).toBeVisible();
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    expect(overflow, `${width}px`).toBeLessThanOrEqual(0);
  }
});

test("the page is titled Tổng quan, with quick numbers and one list of things worth a look", async ({ page }) => {
  await seedOwner(page);
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1, name: "Tổng quan" })).toBeVisible();
  await expect(page.getByText("Một góc nhìn rõ ràng sau mỗi phiên.")).toHaveCount(0);
  const numbers = page.getByRole("region", { name: "Số liệu nhanh" });
  await expect(numbers).toContainText("Giá trị danh mục");
  await expect(numbers).toContainText("Lãi/lỗ chưa thực hiện");
  await expect(numbers.getByTestId("kpi-value")).toHaveText(/[\d.]+ đ/);
  const watch = page.getByRole("region", { name: "Cần để ý" });
  await expect(watch).toBeVisible();
  await expect(watch).toContainText(/Không có gì cần để ý hôm nay|Sự kiện|Vượt ngưỡng|Nhật ký/);
});

test("no horizontal scroll with the quick numbers at 375px", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 900 });
  await page.goto("/");
  await expect(page.getByRole("region", { name: "Số liệu nhanh" })).toBeVisible();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(0);
});
