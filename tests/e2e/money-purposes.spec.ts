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
