import { expect, test } from "@playwright/test";
import { signIn } from "./helpers";

// Figures worked out by hand: a loan of 2 tỷ, 25 years, 7,5% for a year then 11%, equal principal.
test.beforeEach(async ({ context }) => signIn(context));

test("Tính khoản vay gives the first payment, totals, schedule, grace and early repayment", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("navigation", { name: "Điều hướng chính" }).getByRole("link", { name: "Tính khoản vay" }).click();
  await expect(page).toHaveURL(/\/loan$/);
  const result = page.getByRole("complementary", { name: "Kết quả khoản vay" });
  await expect(result.getByTestId("ln-first")).toHaveText("19.166.667 đ");
  await expect(result).toContainText("Tỉ lệ vay 100% · 25 năm · 7,5%/năm");
  await expect(result).toContainText("2.690.450.000 đ");
  // From the value of a property: the rest is paid up front; the middle of the ring is what goes to the bank.
  await page.getByLabel("Giá trị bất động sản").first().check();
  await expect(result.getByTestId("ln-first")).toHaveText("20.125.000 đ");
  await expect(result).toContainText("Tỉ lệ vay 70%");
  await expect(result).toContainText("900.000.000 đ");
  await expect(result.getByRole("img")).toHaveAttribute("aria-label", /Trả ngân hàng 4\.924\.972\.500 đ/);
  await expect(result.getByTestId("ln-all")).toHaveText("5.824.972.500 đ");
  await page.getByRole("button", { name: "Đặt lại" }).click();
  await expect(result.getByTestId("ln-first")).toHaveText("19.166.667 đ");
  // A decimal typed with a point stays a decimal.
  await page.getByRole("textbox", { name: "Giá trị khoản vay" }).fill("1.5");
  await expect(result).toContainText("1.500.000.000 đ");
  await page.getByRole("button", { name: "Đặt lại" }).click();
  // The schedule, month by month, and its export.
  await page.getByRole("button", { name: "Thanh toán từng tháng" }).click();
  const schedule = page.getByRole("table", { name: "Lịch thanh toán" });
  await expect(schedule.locator("tbody tr")).toHaveCount(300);
  const saved = page.waitForEvent("download");
  await page.getByRole("button", { name: "Xuất Excel" }).click();
  expect((await saved).suggestedFilename()).toBe("lich-tra-no.xls");
  // Equal payments, a grace on principal, repaying early, and a term that cannot work.
  await page.getByLabel("Trả đều hàng tháng").check();
  await expect(schedule.locator("tbody tr").nth(1).locator("td").nth(4)).toHaveText(await schedule.locator("tbody tr").first().locator("td").nth(4).innerText());
  await page.getByRole("textbox", { name: "Ân hạn nợ gốc" }).fill("6");
  await expect(schedule.locator("tbody tr").nth(5).locator("td").nth(2)).toHaveText("0 đ");
  await page.getByLabel("Trả hết nợ trước hạn").check();
  await expect(schedule.locator("tbody tr")).toHaveCount(60);
  await expect(result.getByTestId("ln-saved")).toHaveText(/^[\d.]+ đ$/);
  await page.getByRole("textbox", { name: "Thời gian ưu đãi" }).fill("99");
  await expect(result.getByRole("alert")).toContainText("không dài hơn thời hạn vay");
});

test("no horizontal page scroll on Tính khoản vay at 375px", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 800 });
  await page.goto("/loan");
  await expect(page.getByRole("complementary", { name: "Kết quả khoản vay" })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBeLessThanOrEqual(0);
});
