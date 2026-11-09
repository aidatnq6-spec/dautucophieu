import { expect, test } from "@playwright/test";
import { signIn } from "./helpers";

test.beforeEach(async ({ context }) => signIn(context));
const region = (page: import("@playwright/test").Page) => page.getByRole("region", { name: "Mua nhà cho thuê hay giữ tiền gửi" });

// Worked by hand: 2 tỷ all from own money, 5 tr rent less 1 tr costs, deposit 6%, held 1 year.
test("the growth a home needs to match the deposit is worked out from what is typed", async ({ page }) => {
  await page.goto("/loan");
  const box = region(page);
  await expect(box.getByTestId("rc-empty")).toBeVisible();
  await box.getByLabel("Giá nhà (đ)").fill("2000000000");
  await expect(box.getByLabel("Giá nhà (đ)")).toHaveValue("2.000.000.000");
  await box.getByLabel("Vốn tự có (đ)").fill("2000000000");
  await box.getByLabel("Chi phí mua ban đầu (đ)").fill("0");
  await box.getByLabel("Tiền thuê mỗi tháng (đ)").fill("5000000");
  await box.getByLabel("Chi phí giữ nhà mỗi tháng (đ)").fill("1000000");
  await box.getByLabel("Lãi tiền gửi (%/năm)").fill("6");
  await box.getByLabel("Số năm nắm giữ").fill("1");
  await expect(box.getByTestId("rc-gross")).toHaveText("3,00%");
  await expect(box.getByTestId("rc-net")).toHaveText("2,40%");
  await expect(box.getByTestId("rc-growth")).toContainText("3,70%");
});

test("own money above the price and costs is refused", async ({ page }) => {
  await page.goto("/loan");
  const box = region(page);
  await box.getByLabel("Giá nhà (đ)").fill("1000000000");
  await box.getByLabel("Vốn tự có (đ)").fill("2000000000");
  await box.getByLabel("Chi phí mua ban đầu (đ)").fill("0");
  await box.getByLabel("Tiền thuê mỗi tháng (đ)").fill("5000000");
  await box.getByLabel("Chi phí giữ nhà mỗi tháng (đ)").fill("0");
  await box.getByLabel("Lãi tiền gửi (%/năm)").fill("6");
  await box.getByLabel("Số năm nắm giữ").fill("1");
  await expect(box.getByRole("alert")).toContainText("Vốn tự có");
});

test("the section adds no sideways scroll at 375px", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 800 });
  await page.goto("/loan");
  await expect(region(page).getByLabel("Giá nhà (đ)")).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)).toBeLessThanOrEqual(0);
});
