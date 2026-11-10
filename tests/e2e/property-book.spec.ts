import { expect, test } from "@playwright/test";
import { call, seedOwner, signIn } from "./helpers";

test.describe.configure({ mode: "serial" });
test.beforeEach(async ({ context }) => signIn(context));
const region = (page: import("@playwright/test").Page) => page.getByRole("region", { name: "Bất động sản, khoản vay và bảo hiểm" });

test("a property and a loan are entered, and the loan's monthly payment is worked out", async ({ page }) => {
  await seedOwner(page);
  const { version } = await (await call(page, "GET", "property-book")).json();  // the suite shares one store: start from an empty book, also on a retry
  await call(page, "PUT", "property-book", { properties: [], loans: [], ceiling: "70", expected_version: version, request_id: `pb-reset-${Date.now()}` });
  await page.goto("/profile?tab=tai-san");
  const box = region(page);
  await expect(box.getByRole("button", { name: "Thêm bất động sản" })).toBeEnabled();
  await box.getByRole("button", { name: "Thêm bất động sản" }).click();
  await box.getByLabel("Tên bất động sản").fill("Căn hộ thử");
  await box.getByLabel("Giá trị tự ước tính (đ)").fill("3000000000");
  await expect(box.getByLabel("Giá trị tự ước tính (đ)")).toHaveValue("3.000.000.000");
  await box.getByRole("button", { name: "Lưu" }).click();
  await expect(box.getByRole("table", { name: "Bất động sản" })).toContainText("3.000.000.000 đ");
  await expect(box.getByTestId("nw-stale")).toContainText("Căn hộ thử");  // no valuation date entered
  await box.getByRole("button", { name: "Thêm khoản vay" }).click();
  await box.getByLabel("Tên khoản vay").fill("Vay thử");
  await box.getByLabel("Dư nợ hiện tại (đ)").fill("1200000000");
  await box.getByLabel("Lãi hiện tại (%/năm)").fill("12");
  await box.getByLabel("Số tháng còn lại").fill("120");
  await box.getByRole("button", { name: "Lưu" }).click();
  await expect(box.getByRole("table", { name: "Khoản vay" })).toContainText("22.000.000 đ");
  await expect(box.getByTestId("nw-debt")).toHaveText("1.200.000.000 đ");
  await box.getByRole("link", { name: "Mở Vay thử ở Tính khoản vay" }).click();
  await expect(page).toHaveURL(/\/loan\?loan=/);
  const result = page.getByRole("complementary", { name: "Kết quả khoản vay" });
  await expect(result.getByTestId("ln-first")).toHaveText("22.000.000 đ");
  await expect(page.getByTestId("ln-from-book")).toContainText("Vay thử");
});

test("the section adds no sideways scroll at 375px", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 800 });
  await page.goto("/profile?tab=tai-san");
  await expect(region(page).getByRole("button", { name: "Thêm bất động sản" })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)).toBeLessThanOrEqual(0);
});

test("the yield of a let flat and the split of what is lived in and invested", async ({ page }) => {
  await seedOwner(page);
  const { version } = await (await call(page, "GET", "property-book")).json();
  const row = { kind: "apartment", legal: "certificate", valued_on: "2026-10-01" };
  await call(page, "PUT", "property-book", { properties: [{ ...row, id: "y", name: "Căn thuê", purpose: "rent", value: "2000000000", rent_monthly: "10000000" }, { ...row, id: "z", name: "Nhà ở", purpose: "live", value: "3000000000" }],
    loans: [], ceiling: "70", expected_version: version, request_id: `pb-y-${Date.now()}` });
  await page.goto("/profile?tab=tai-san");
  await expect(region(page).getByRole("table", { name: "Bất động sản" })).toContainText("6,00%/năm");
  await expect(region(page).getByRole("region", { name: "Cấu trúc tài sản" }).or(page.getByTestId("nw-reason")).first()).toBeVisible();
});


test("an insurance policy is entered; life cover counts at its account value, said to be before the surrender charge", async ({ page }) => {
  await seedOwner(page);
  const { version } = await (await call(page, "GET", "property-book")).json();
  await call(page, "PUT", "property-book", { properties: [], loans: [], policies: [], ceiling: "70", expected_version: version, request_id: `pb-ins-${Date.now()}` });
  await page.goto("/profile?tab=tai-san");
  const box = region(page);
  await expect(box.getByRole("button", { name: "Thêm bảo hiểm" })).toBeEnabled();
  await box.getByRole("button", { name: "Thêm bảo hiểm" }).click();
  await box.getByLabel("Tên hợp đồng").fill("Nhân thọ thử");
  await box.getByLabel("Phí mỗi kỳ (đ)").fill("12000000");
  await box.getByLabel("Một ngày đóng phí (kỳ bất kỳ)").fill("2026-06-16");
  await box.getByLabel("Giá trị tài khoản (đ, nhân thọ)").fill("50000000");
  await box.getByLabel("Ngày cập nhật giá trị").fill("2026-06-16");
  await box.getByRole("button", { name: "Lưu" }).click();
  const table = box.getByRole("table", { name: "Bảo hiểm" });
  await expect(table).toContainText("Nhân thọ thử");
  await expect(table).toContainText("tài khoản, chưa trừ phí hủy");
  await expect(table).toContainText("16/06/2027");
  await expect(box.getByTestId("nw-insurance")).toHaveText("50.000.000 đ");
  await expect(box.getByTestId("nw-premiums")).toHaveText("12.000.000 đ");
  await expect(box).toContainText("chưa trừ phí hủy (rút ra sẽ nhận ít hơn)");
});
