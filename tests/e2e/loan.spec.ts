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

test("the payment after the promotion and each part's share are shown beside the first payment", async ({ page }) => {
  await page.goto("/loan");
  const result = page.getByRole("complementary", { name: "Kết quả khoản vay" });
  await expect(result.getByTestId("ln-after")).toHaveText("24.266.667 đ");
  await expect(result).toContainText("Sau ưu đãi · tháng 13");
  await expect(result.getByTestId("ln-rise")).toHaveText("Tăng 5.558.333 đ (+29,7%) so với tháng liền trước");
  await expect(result).toContainText("42,6%");
  await expect(result).toContainText("57,4%");
  await expect(result).not.toContainText("Cần trả trước");  // nothing to show when the whole amount is borrowed
  await page.getByRole("textbox", { name: "Thời gian ưu đãi" }).fill("0");
  await expect(result.getByTestId("ln-after")).toHaveCount(0);
  await expect(result).toContainText("Thanh toán tháng đầu");
  await page.getByLabel("Giá trị bất động sản").first().check();
  await expect(result).toContainText("Cần trả trước");
});

test("the page's actions sit where they act: schedule and print by the result, reset in the form", async ({ page }) => {
  await page.goto("/loan");
  const result = page.getByRole("complementary", { name: "Kết quả khoản vay" });
  await expect(result.getByRole("button", { name: "Thanh toán từng tháng" })).toBeVisible();
  await expect(result.getByRole("button", { name: "In" })).toBeVisible();
  await expect(page.getByRole("region", { name: "Thông tin khoản vay" }).getByRole("button", { name: "Đặt lại" })).toBeVisible();
});

test("trying higher rates shows each payment, and income shows whether the loan can be carried", async ({ page }) => {
  await page.goto("/loan");
  const stress = page.getByRole("table", { name: "Thử sức chịu lãi suất" });
  await expect(stress.locator("tbody tr")).toHaveCount(4);
  await expect(stress.locator("tbody tr").nth(0)).toContainText("24.266.667 đ");
  await expect(stress.locator("tbody tr").nth(1)).toContainText("27.466.667 đ");
  await expect(stress.locator("tbody tr").nth(1)).toContainText("1,43 lần");
  await page.getByLabel("Mức lãi tự chọn (%/năm)").fill("15");
  await expect(stress.locator("tbody tr")).toHaveCount(5);
  const flow = page.getByRole("region", { name: "Dòng tiền sau khi vay" });
  await expect(flow).toContainText("Nhập thu nhập");
  await flow.getByLabel("Thu nhập mỗi tháng (triệu đ)").fill("30");
  await expect(flow.getByTestId("ln-ratio")).toContainText("80,9%");
  await expect(flow.getByTestId("ln-over")).toContainText("vượt ngưỡng 40%");
  await expect(flow.getByTestId("ln-left")).toContainText("Chưa nhập chi tiêu");
  await flow.getByLabel("Chi tiêu mỗi tháng (triệu đ)").fill("10");
  await expect(flow.getByTestId("ln-left")).toContainText("833.333 đ");
  await expect(flow.getByTestId("ln-negative")).toHaveText("Tháng 13");
  await flow.getByLabel("Tiền dự phòng (triệu đ)").fill("10");
  await expect(flow.getByTestId("ln-reserve")).toHaveText("Trụ được 2 tháng, hết vào tháng 15");
  await flow.getByLabel("Ngưỡng cảnh báo trả nợ (% thu nhập)").fill("90");
  await expect(flow.getByTestId("ln-over")).toHaveCount(0);
  await expect(stress.locator("tbody tr").nth(0)).toContainText("80,9%");
  await page.getByRole("button", { name: "Đặt lại" }).click();
  await expect(flow.getByLabel("Thu nhập mỗi tháng (triệu đ)")).toHaveValue("");
});

test("the printout uses the whole page width, states the loan and leaves out the controls", async ({ page }, info) => {
  await page.setViewportSize({ width: 794, height: 1123 });  // A4 at 96 dpi
  await page.goto("/loan");
  await expect(page.getByRole("complementary", { name: "Kết quả khoản vay" }).getByTestId("ln-first")).toHaveText("19.166.667 đ");
  await page.getByRole("button", { name: "Thanh toán từng tháng" }).click();
  await page.emulateMedia({ media: "print" });
  const main = await page.locator("main.content").boundingBox();
  expect(main!.width).toBeGreaterThan(700);
  const facts = page.locator(".ln-print");
  await expect(facts).toBeVisible();
  await expect(facts).toContainText("Giá trị khoản vay");
  await expect(facts).toContainText("7,5%/năm trong 1 năm");
  await expect(facts).toContainText("Dư nợ giảm dần");
  for (const hidden of [".side", ".page-jumps", ".ln-controls", ".to-top"]) await expect(page.locator(hidden)).toBeHidden();
  await expect(page.getByRole("table", { name: "Lịch thanh toán" })).toBeVisible();
  await page.screenshot({ path: info.outputPath("in-khoan-vay.png"), fullPage: false });
  const pdf = await page.pdf({ format: "A4", path: info.outputPath("in-khoan-vay.pdf") });
  expect(pdf.length).toBeGreaterThan(0);
});

test("no horizontal page scroll on Tính khoản vay at 375px", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 800 });
  await page.goto("/loan");
  await expect(page.getByRole("complementary", { name: "Kết quả khoản vay" })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBeLessThanOrEqual(0);
});
