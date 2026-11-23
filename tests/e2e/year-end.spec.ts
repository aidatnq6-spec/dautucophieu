import { expect, test, type Page } from "@playwright/test";
import { signIn } from "./helpers";

test.beforeEach(async ({ context }) => signIn(context));

// Việc cuối năm opens on 1 December by the server's clock, which also checks each request's signature: the page is shown as the server
// would answer in December, not by moving any clock (owner, 23/11/2026). The server's December rules have their own tests.
const item = (id: string, label: string, auto: boolean, done: boolean | null, detail: string | null = null) => ({ id, label, auto, done, detail });
const items = (dividends: boolean) => [
  item("theses", "Rà luận điểm các mã đang giữ", true, false, "chưa rà trong 90 ngày: AAA"),
  item("tower", "Cân lại Tháp tài sản", true, null, "không đọc được (KeyError)"),
  item("calendar", "Lịch giao dịch HOSE năm sau đã có", true, false, "chưa có lịch 2027; HOSE thường công bố cuối tháng 12"),
  item("drill", "Diễn tập khôi phục trong 30 ngày qua", true, true, "lần gần nhất 18/11/2026"),
  item("goals", "Đặt mục tiêu năm sau", true, true, "đã đặt mục tiêu 2027"),
  item("dividends", "Đối chiếu cổ tức và thuế khấu trừ cả năm với chứng từ công ty chứng khoán", false, dividends),
  item("cashflow", "Nhập Thu chi tháng 12", false, false),
];
const view = (dividends: boolean, version: number) => ({ open: true, version, year: 2026, items: items(dividends), left: dividends ? 4 : 5 });

async function december(page: Page, ticks: unknown[]) {
  await page.route("**/api/internal/year-end", (route) => route.fulfill({ json: view(false, 3) }));
  await page.route("**/api/internal/year-end/tick", async (route) => {
    ticks.push(route.request().postDataJSON());
    await route.fulfill({ json: view(true, 4) });
  });
}

test("Việc cuối năm in December: each check says how it stands, an unreadable one is not done, and the owner ticks a manual item", async ({ page }) => {
  const ticks: { item: string; done: boolean; expected_version: number }[] = [];
  await december(page, ticks);
  await page.goto("/year");
  const box = page.getByRole("region", { name: "Việc cuối năm" });
  await expect(box.getByRole("heading", { name: "Việc cuối năm 2026" })).toBeVisible();
  await expect(box).toContainText("Còn 5 việc.");
  const row = (label: string) => box.getByRole("listitem").filter({ hasText: label });
  await expect(row("Diễn tập khôi phục")).toContainText("đã xong (tự kiểm)");
  await expect(row("Rà luận điểm")).toContainText("chưa xong (tự kiểm)");
  await expect(row("Cân lại Tháp tài sản")).toContainText("chưa kiểm được");  // never counted as done
  await expect(row("Lịch giao dịch HOSE")).toContainText("HOSE thường công bố cuối tháng 12");
  await expect(row("Rà luận điểm").getByRole("checkbox")).toHaveCount(0);  // the app's checks are not ticked by hand
  const dividends = row("Đối chiếu cổ tức").getByRole("checkbox");
  await expect(dividends).not.toBeChecked();
  await dividends.click();
  await expect(dividends).toBeChecked();
  await expect(row("Đối chiếu cổ tức")).toContainText("đã xong");
  await expect(box).toContainText("Còn 4 việc.");
  expect(ticks).toHaveLength(1);
  expect(ticks[0]).toMatchObject({ item: "dividends", done: true, expected_version: 3 });
});

test("Việc cuối năm reads without a sideways scroll on a phone", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 800 });
  await december(page, []);
  await page.goto("/year");
  await expect(page.getByRole("region", { name: "Việc cuối năm" })).toContainText("Còn 5 việc.");
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1)).toBe(true);
});
