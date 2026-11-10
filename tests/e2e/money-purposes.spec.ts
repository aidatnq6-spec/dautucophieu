import { expect, test } from "@playwright/test";
import { call, seedOwner, signIn } from "./helpers";

test.describe.configure({ mode: "serial" });
test.beforeEach(async ({ context }) => signIn(context));
const region = (page: import("@playwright/test").Page) => page.getByRole("region", { name: "Mục đích từng khoản tiền" });

// The suite shares one store and other specs need it to have no Sổ tài sản, so the book's row is added to the response here; what it adds up to is tested in the backend.
test("a purpose is added and a row's tag stays after a reload", async ({ page }) => {
  await seedOwner(page);
  const stored = await (await call(page, "GET", "money-purposes")).json();
  await call(page, "PUT", "money-purposes", { purposes: [], tags: {}, expected_version: stored.version, request_id: `mp-r-${Date.now()}` });
  await page.route("**/api/internal/money-purposes", async (route) => {
    const response = await route.fetch();
    await route.fulfill({ response, json: { ...(await response.json()), rows: [{ id: "mp-a", kind: "account", name: "TK cho con", value: "100000000", at_cost: false }] } });
  });
  await page.goto("/profile?tab=tai-san");
  const box = region(page);
  await expect(box.getByLabel("Tên mục đích")).toBeEnabled();
  await box.getByLabel("Tên mục đích").fill("Cho con");
  await box.getByLabel("Xem như đã chi").check();
  await box.getByRole("button", { name: "Thêm mục đích" }).click();
  await expect(box.getByRole("table", { name: "Tổng theo mục đích" })).toContainText("Cho con");
  await box.getByLabel("Mục đích của TK cho con").selectOption({ label: "Cho con" });
  await expect(box.getByLabel("Mục đích của TK cho con")).toBeEnabled();
  await page.reload();
  await expect(region(page).getByLabel("Mục đích của TK cho con").locator("option:checked")).toHaveText("Cho con");
});

test("the section adds no sideways scroll at 375px", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 800 });
  await page.goto("/profile?tab=tai-san");
  await expect(region(page).getByLabel("Tên mục đích")).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)).toBeLessThanOrEqual(0);
});

const ROWS = [{ id: "mp-a", kind: "account", name: "TK cho con", value: "100000000", at_cost: false }, { id: "mp-b", kind: "deposit", name: "Sổ thử, đáo hạn 01/01/2027", value: "50000000", at_cost: false }];

async function freshWithRows(page: import("@playwright/test").Page) {
  await seedOwner(page);
  const stored = await (await call(page, "GET", "money-purposes")).json();
  await call(page, "PUT", "money-purposes", { purposes: [], tags: {}, expected_version: stored.version, request_id: `mp-r-${Date.now()}` });
  await page.route("**/api/internal/money-purposes", async (route) => {
    try {
      const response = await route.fetch();
      await route.fulfill({ response, json: { ...(await response.json()), rows: ROWS } });
    } catch { /* the page moved on before the answer came back */ }
  });
}

test("with no purpose yet the section says how to make one, and one is made from the row's own list", async ({ page }) => {
  await freshWithRows(page);
  await page.goto("/profile?tab=tai-san");
  const box = region(page);
  await expect(box.getByTestId("mp-empty")).toContainText("Chưa có mục đích nào");
  page.once("dialog", (d) => d.accept("Quỹ du học thử"));
  await box.getByLabel("Mục đích của TK cho con").selectOption({ label: "+ Tạo mục đích mới…" });
  await expect(box.getByRole("table", { name: "Tổng theo mục đích" })).toContainText("Quỹ du học thử");
  await expect(box.getByLabel("Mục đích của TK cho con").locator("option:checked")).toHaveText("Quỹ du học thử");
});

test("a suggested name is made with one click, several rows get it at once, and it can be counted as spent", async ({ page }) => {
  await freshWithRows(page);
  await page.goto("/profile?tab=tai-san");
  const box = region(page);
  await expect(box.getByRole("button", { name: "+ Quỹ dự phòng" })).toBeEnabled();
  await box.getByRole("button", { name: "+ Quỹ dự phòng" }).click();
  await expect(box.getByRole("button", { name: "+ Quỹ dự phòng" })).toHaveCount(0);
  await box.getByLabel("Chọn TK cho con").check();
  await box.getByLabel("Chọn Sổ thử, đáo hạn 01/01/2027").check();
  await box.getByLabel("Mục đích cho các khoản đã chọn").selectOption({ label: "Quỹ dự phòng" });
  await box.getByRole("button", { name: "Gắn cho 2 khoản" }).click();
  await expect(box.getByLabel("Mục đích của Sổ thử, đáo hạn 01/01/2027").locator("option:checked")).toHaveText("Quỹ dự phòng");
  await expect(box.getByLabel("Mục đích của TK cho con").locator("option:checked")).toHaveText("Quỹ dự phòng");
  await box.getByLabel("Tính là đã chi: Quỹ dự phòng").click();  // saved first, then shown ticked
  await expect(box.getByLabel("Tính là đã chi: Quỹ dự phòng")).toBeChecked();
  await page.reload();
  await expect(region(page).getByLabel("Tính là đã chi: Quỹ dự phòng")).toBeChecked();
});

test("a purpose is chosen while editing a row of Sổ tài sản", async ({ page }) => {
  await freshWithRows(page);
  const before = await (await call(page, "GET", "money-purposes")).json();
  await call(page, "PUT", "money-purposes", { purposes: [{ id: "p-house", name: "Quỹ mua nhà", given: false }], tags: {}, expected_version: before.version, request_id: `mp-h-${Date.now()}` });
  // the suite needs no Sổ tài sản: the book's answer is made up here and its save is answered too; the purpose itself is really saved
  let book: Record<string, unknown> | null = null;
  await page.route("**/api/internal/deposit-book", async (route) => {
    if (route.request().method() === "PUT") return route.fulfill({ json: book });
    const response = await route.fetch();
    const body = await response.json();
    book = { ...body, version: 1, book: { ...body.book, accounts: [{ id: "db-a", name: "TK thử", amount: "1000000", liquid: true }] } };
    await route.fulfill({ json: book });
  });
  await page.goto("/profile?tab=tai-san");
  const deposits = page.getByRole("region", { name: "Sổ tài sản" });
  await deposits.getByRole("button", { name: "Sửa tài khoản 1" }).click();
  await deposits.getByLabel("Mục đích tài khoản 1").selectOption({ label: "Quỹ mua nhà" });
  await deposits.getByRole("button", { name: "Lưu" }).click();
  await expect(deposits.getByRole("button", { name: "Sửa tài khoản 1" })).toBeVisible();  // the row is no longer being edited
  await expect(deposits.getByRole("table", { name: "Tài khoản tiền mặt" }).getByRole("combobox")).toHaveCount(0);
  await expect(deposits.getByRole("table", { name: "Tài khoản tiền mặt" })).toContainText("Quỹ mua nhà");
  await expect.poll(async () => (await (await call(page, "GET", "money-purposes")).json()).data.tags["db-a"]).toBe("p-house");
});

test("picking rows without a purpose says what to do instead of greying the button out", async ({ page }) => {
  await freshWithRows(page);
  await page.goto("/profile?tab=tai-san");
  const box = region(page);
  await expect(box.getByLabel("Chọn TK cho con")).toBeEnabled();
  await box.getByRole("button", { name: "+ Quỹ dự phòng" }).click();
  await expect(box.getByRole("table", { name: "Tổng theo mục đích" })).toContainText("Quỹ dự phòng");
  await box.getByLabel("Chọn tất cả").check();
  await expect(box.getByTestId("mp-bulk-note")).toContainText("Chọn mục đích ở ô bên trái");
  const button = box.getByRole("button", { name: "Gắn cho 2 khoản" });
  await expect(button).toBeEnabled();
  await button.click();
  await expect(box.getByTestId("mp-bulk-note")).toContainText("Chọn mục đích ở ô bên trái");
  await box.getByLabel("Mục đích cho các khoản đã chọn").selectOption({ label: "Quỹ dự phòng" });
  await expect(box.getByTestId("mp-bulk-note")).toHaveCount(0);
  await button.click();
  await expect(box.getByLabel("Mục đích của TK cho con").locator("option:checked")).toHaveText("Quỹ dự phòng");
});
