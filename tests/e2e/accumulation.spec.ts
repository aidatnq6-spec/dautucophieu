import { expect, test } from "@playwright/test";
import { call, seedOwner, signIn } from "./helpers";

test.describe.configure({ mode: "serial" });
test.beforeEach(async ({ context }) => signIn(context));
const region = (page: import("@playwright/test").Page) => page.getByRole("region", { name: "Kế hoạch tích sản" });

test("a plan is set, a buy is recorded and the average cost is worked out", async ({ page }) => {
  await seedOwner(page);
  const stored = await (await call(page, "GET", "accumulation")).json();
  await call(page, "PUT", "accumulation", { plans: [], buys: [], expected_version: stored.version, request_id: `ac-r-${Date.now()}` });
  await page.goto("/profile");
  const box = region(page);
  await expect(box.getByLabel("Tên kế hoạch")).toBeEnabled();
  await box.getByLabel("Tên kế hoạch").fill("Vàng thử");
  await box.getByLabel("Số chỉ mỗi tháng").fill("1");
  await box.getByLabel("Ngày mua trong tháng").fill("5");
  await box.getByLabel("Bắt đầu từ tháng").fill("2026-01");
  await box.getByRole("button", { name: "Lưu kế hoạch tích sản" }).click();
  const card = box.getByRole("article", { name: "Vàng thử" });
  await expect(card).toBeVisible();
  await card.getByLabel("Ngày mua", { exact: true }).fill("2026-01-06");
  await card.getByLabel("Tiền bỏ ra (đ)").fill("20000000");
  await card.getByLabel("Số chỉ mua").fill("2");
  await card.getByRole("button", { name: "Ghi lần mua" }).click();
  await expect(card.getByTestId("ta-average")).toHaveText("10.000.000 đ");
  await expect(card.getByTestId("ta-month-2026-01")).toContainText("đã mua");
  await page.reload();
  await expect(region(page).getByRole("article", { name: "Vàng thử" }).getByTestId("ta-average")).toHaveText("10.000.000 đ");
});

test("the section adds no sideways scroll at 375px", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 800 });
  await page.goto("/profile");
  await expect(region(page).getByLabel("Tên kế hoạch")).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)).toBeLessThanOrEqual(0);
});


// The suite shares one store and other specs need it to have no Sổ tài sản, so the book side is answered here; the write itself is tested in the backend.
test("a buy is sent to the chosen row of the book after a confirmation, and is then marked", async ({ page }) => {
  await seedOwner(page);
  const buy = { id: "b1", plan: "p1", on: "2026-01-06", amount: "20000000", quantity: "2", book_row: null };
  const stored = await (await call(page, "GET", "accumulation")).json();
  const saved = await (await call(page, "PUT", "accumulation", { plans: [{ id: "p1", name: "Vàng nút", asset: "gold", day: 5, start: "2026-01", chi: "1", kind: null, fund: null }], buys: [buy], expected_version: stored.version, request_id: `ac-p-${Date.now()}` })).json();
  const rows = (v: typeof saved) => ({ ...v, book_exists: true, plans: v.plans.map((s: object) => ({ ...s, book_rows: [{ id: "r1", name: "Dòng vàng" }] })) });
  let sent: Record<string, unknown> | null = null;
  await page.route("**/api/internal/accumulation", async (route) => { const response = await route.fetch(); await route.fulfill({ response, json: rows(await response.json()) }); });
  await page.route("**/api/internal/accumulation/post", async (route) => {
    sent = route.request().postDataJSON();
    await route.fulfill({ json: rows({ ...saved, data: { ...saved.data, buys: [{ ...buy, book_row: "r1" }] } }) });
  });
  page.on("dialog", (d) => d.accept());
  await page.goto("/profile");
  const card = region(page).getByRole("article", { name: "Vàng nút" });
  await expect(card.getByLabel("Cộng vào dòng")).toHaveValue("r1");
  await card.getByRole("button", { name: "Cộng vào Sổ tài sản" }).click();
  await expect(card.getByText("đã cộng vào Sổ")).toBeVisible();
  await expect(card.getByRole("button", { name: "Cộng vào Sổ tài sản" })).toHaveCount(0);
  expect(sent).toMatchObject({ buy: "b1", row: "r1" });
});
