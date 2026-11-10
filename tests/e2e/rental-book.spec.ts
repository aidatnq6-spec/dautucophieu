import { expect, test } from "@playwright/test";
import { call, seedOwner, signIn } from "./helpers";

test.describe.configure({ mode: "serial" });
test.beforeEach(async ({ context }) => signIn(context));
const region = (page: import("@playwright/test").Page) => page.getByRole("region", { name: "Sổ cho thuê căn hộ" });

test("a room is added with its deposit taken as one month's rent, then a payment marks the month", async ({ page }) => {
  await seedOwner(page);
  const { version } = await (await call(page, "GET", "rental-book")).json();
  await call(page, "PUT", "rental-book", { units: [], payments: [], expected_version: version, request_id: `rb-reset-${Date.now()}` });
  await page.goto("/profile?tab=tai-san");
  const box = region(page);
  await expect(box.getByRole("button", { name: "Thêm phòng" })).toBeEnabled();
  await box.getByRole("button", { name: "Thêm phòng" }).click();
  await box.getByLabel("Tên phòng").fill("999");
  await box.getByLabel("Khách thuê").fill("Khách thử");
  await box.getByLabel("Giá thuê mỗi tháng (đ)").fill("7000000");
  await box.getByLabel("Ngày thu hằng tháng").fill("1");
  await box.getByLabel("Ngày bắt đầu hợp đồng").fill(new Date().toLocaleDateString("en-CA", { timeZone: "Asia/Ho_Chi_Minh" }).slice(0, 8) + "01");
  await box.getByRole("button", { name: "Lưu phòng" }).click();
  await expect(box.getByRole("table", { name: "Các phòng cho thuê" })).toContainText("Khách thử");
  await expect(box).toContainText("Tiền cọc đang giữ7.000.000 đ");
  await expect(box.getByTestId("rb-now-999")).toContainText("chưa thu 7.000.000 đ");
  await box.getByRole("button", { name: "Ghi thu phòng 999" }).click();
  await expect(box.getByLabel("Số tiền đã thu (đ)")).toHaveValue("7.000.000");
  await box.getByRole("button", { name: "Lưu lần thu" }).click();
  await expect(box.getByTestId("rb-now-999")).toContainText("đã thu");
  await expect(box.getByTestId("rb-owed")).toHaveText("0 đ");
});

test("the section adds no sideways scroll at 375px", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 800 });
  await page.goto("/profile?tab=tai-san");
  await expect(region(page).getByRole("button", { name: "Thêm phòng" })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)).toBeLessThanOrEqual(0);
});
