import { expect, test } from "@playwright/test";
import { call, seedOwner, signIn } from "./helpers";

test.beforeEach(async ({ context }) => signIn(context));

test("the season page lists results, sectors and a review for a held ticker that is kept", async ({ page }) => {
  await seedOwner(page);  // holds FPT
  await page.goto("/");
  await page.getByRole("navigation", { name: "Điều hướng chính" }).getByRole("link", { name: "Mùa báo cáo" }).click();
  await expect(page).toHaveURL(/\/earnings$/);
  const results = page.getByRole("region", { name: "Kết quả từng mã" });
  await expect(results.getByRole("heading", { level: 2 })).toContainText("mã đã có báo cáo");
  await expect(results.getByTestId("er-FPT")).toContainText("đang nắm");
  await expect(results.getByTestId("er-FPT")).toContainText("chưa có");  // the synthetic FPT stops at Q4/2025; the banks have Q3/2026
  await expect(page.getByRole("region", { name: "Tăng trưởng theo ngành" }).getByRole("table")).toBeVisible();
  await expect(page.getByRole("region", { name: "Lợi nhuận và dòng tiền" })).toBeVisible();
});

test("a held ticker that has reported gets a review, saved on the server", async ({ page }) => {
  await seedOwner(page);
  // the page's first answer is made to show FPT as reported; the review itself goes to the server and comes back in the history
  await page.route("**/api/internal/earnings", async (route) => {
    if (route.request().method() !== "GET") return route.continue();
    try {
      const response = await route.fetch();
      const body = await response.json();
      await route.fulfill({ response, json: { ...body, rows: body.rows.map((r: { symbol: string }) => (r.symbol === "FPT" ? { ...r, reported: true, yoy: "0.1000" } : r)) } });
    } catch { /* the page moved on */ }
  });
  await page.goto("/earnings");
  const review = page.getByRole("region", { name: "Rà luận điểm sau báo cáo" });
  const row = review.getByTestId("rv-FPT");
  await expect(row).toContainText(/chưa rà|đã rà/);  // the e2e store persists between runs
  const note = `chờ quý 4 (${Date.now()})`;
  await row.getByLabel("Kết luận FPT", { exact: true }).selectOption({ label: "Theo dõi thêm" });
  await row.getByLabel("Ghi chú FPT", { exact: true }).fill(note);
  await row.getByRole("button", { name: "Lưu kết luận FPT" }).click();
  await expect(review.getByText(/Các lần rà trước/)).toBeVisible();
  await expect.poll(async () => (await (await call(page, "GET", "earnings")).json()).reviews.find((r: { symbol: string }) => r.symbol === "FPT")?.note).toBe(note);
});

test("the season page adds no sideways scroll at 375px", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 800 });
  await page.goto("/earnings");
  await expect(page.getByRole("region", { name: "Kết quả từng mã" })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)).toBeLessThanOrEqual(0);
});
