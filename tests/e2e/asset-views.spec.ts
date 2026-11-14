import { expect, test } from "@playwright/test";
import { signIn } from "./helpers";

test.beforeEach(async ({ context }) => signIn(context));

test("Danh mục & Giao dịch shows why the account changed this month and a map of every asset", async ({ page }) => {
  await page.goto("/portfolio");
  const bridge = page.getByRole("region", { name: "Vì sao tài sản tháng này thay đổi" });
  await expect(bridge.getByRole("heading", { name: "Vì sao tài sản tháng này thay đổi?" })).toBeVisible();
  await expect(bridge.getByText("Đang tải…")).toHaveCount(0);
  await expect(bridge).toContainText(/Chưa có giao dịch nào|Tài khoản chứng khoán|Chưa tính được|chưa có phiên/);
  const map = page.getByRole("region", { name: "Bản đồ danh mục" });
  await expect(map.getByText("Đang tải…")).toHaveCount(0);
  await expect(map).toContainText(/Chưa có tài sản nào|Diện tích ô = giá trị/);
  if (await map.getByRole("radio", { name: "Danh sách" }).count()) {
    await map.getByRole("radio", { name: "Danh sách" }).check();
    await expect(map.getByRole("table", { name: "Danh sách tài sản theo lớp" })).toBeVisible();
  }
});

test("the two views add no sideways scroll at 375px", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 800 });
  await page.goto("/portfolio");
  await expect(page.getByRole("region", { name: "Bản đồ danh mục" }).getByText("Đang tải…")).toHaveCount(0);
  expect(await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)).toBeLessThanOrEqual(0);
});


test("the daily calendar shows each session, or says the ledger has none yet", async ({ page }) => {
  await page.goto("/portfolio");
  const box = page.getByRole("region", { name: "Lịch lãi lỗ hằng ngày" });
  await expect(box.getByText("Đang tải…")).toHaveCount(0);
  await expect(box).toContainText(/Chưa có phiên nào|Mỗi ô một phiên/);
});
