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
