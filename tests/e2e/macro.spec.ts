import { expect, test } from "@playwright/test";
import { seedOwner, signIn } from "./helpers";

// Synthetic fixture data only: US 10-year yield 4.91 → 4.96 (automatic); every manual indicator starts empty.
test.describe.configure({ mode: "serial" });
test.beforeEach(async ({ context }) => signIn(context));

async function openMacro(page: import("@playwright/test").Page) {
  await page.goto("/macro");
  await expect(page.getByText("Đang tải…")).toHaveCount(0);
}

test("automatic indicators show value, trend and the owner's assessment", async ({ page }) => {
  await openMacro(page);
  const row = page.getByRole("table", { name: "Chỉ số vĩ mô" }).getByRole("row", { name: /Lợi suất trái phiếu 10 năm của Mỹ/ });
  for (const text of ["4,96", "Tăng", "Xấu", "Tự động"]) await expect(row).toContainText(text);
  await expect(page.getByRole("row", { name: /PMI sản xuất Việt Nam/ })).toContainText("Chưa có số liệu");
  // Read from a web page, so a manual value stays possible when the page changes.
  const deposit = page.getByRole("row", { name: /Lãi suất tiền gửi VND 12 tháng/ });
  await expect(deposit).toContainText("Tự động");
  await expect(deposit.getByRole("button", { name: "Nhập" })).toBeVisible();
  await expect(page.getByRole("row", { name: /Lợi suất trái phiếu 10 năm của Mỹ/ }).getByRole("button", { name: "Nhập" })).toHaveCount(0);
});

test("the owner enters PMI values and sees the trend", async ({ page }) => {
  await openMacro(page);
  const row = () => page.getByRole("row", { name: /PMI sản xuất Việt Nam/ });
  for (const [day, value] of [["2026-09-01", "52,4"], ["2026-10-01", "51,9"]]) {
    await row().getByRole("button", { name: "Nhập" }).click();
    const form = page.getByRole("form", { name: "Nhập PMI sản xuất Việt Nam" });
    await form.getByLabel("Ngày số liệu").fill(day);
    await form.getByLabel("Giá trị").fill(value);
    await form.getByLabel("Link nguồn").fill("https://example.invalid/pmi");
    await form.getByRole("button", { name: "Lưu" }).click();
    await expect(form).toHaveCount(0);
  }
  for (const text of ["51,9", "Giảm", "Xấu", "Tự động"]) await expect(row()).toContainText(text);
});

test("the impact chain shows five links, says what is missing, and reads inflation once it is entered", async ({ page }) => {
  await openMacro(page);
  const chain = page.getByRole("region", { name: "Chuỗi tác động vĩ mô" });
  const links = chain.getByRole("list", { name: "Các mắt xích, từ giá dầu đến VN-Index" }).locator(":scope > li");  // not the rate rows inside a link
  await expect(links).toHaveText([/Giá dầu/, /Lạm phát Việt Nam/, /Lãi suất Việt Nam/, /Khối ngoại/, /VN-Index/]);
  await expect(chain).toContainText("không phải khuyến nghị");
  // Months before the 03/2026 figure performance.spec enters, so either order leaves CPI rising: 2,0 → 2,9 (→ 3,2).
  for (const [day, value] of [["2026-01-31", "2,0"], ["2026-02-28", "2,9"]]) {
    await page.getByRole("row", { name: /Lạm phát Việt Nam/ }).getByRole("button", { name: "Nhập" }).click();
    const form = page.getByRole("form", { name: "Nhập Lạm phát Việt Nam (CPI, so cùng kỳ)" });
    await form.getByLabel("Ngày số liệu").fill(day);
    await form.getByLabel("Giá trị").fill(value);
    await form.getByRole("button", { name: "Lưu" }).click();
    await expect(form).toHaveCount(0);
  }
  await openMacro(page);
  const inflation = page.getByRole("region", { name: "Chuỗi tác động vĩ mô" }).getByTestId("chain-inflation");
  await expect(inflation).toContainText(/2,9%|3,2%/);
  await expect(inflation).toContainText("Tăng");
  await expect(inflation).toContainText("tạo áp lực");
  await expect(page.getByRole("region", { name: "Chuỗi tác động vĩ mô" }).getByTestId("chain-summary")).toContainText(/Đang tạo áp lực:.*lạm phát/);
});

test("oil and dollar sensitivity lists held tickers first and says what the dollar measure is", async ({ page }) => {
  await seedOwner(page);  // holds FPT; the e2e data has no oil or dollar history, so every reading waits for data
  await openMacro(page);
  const box = page.getByRole("region", { name: "Độ nhạy với giá dầu và đồng USD" });
  await expect(box).toContainText("không phải tỷ giá VND");
  await expect(box).toContainText("không phải khuyến nghị");
  const fpt = box.getByRole("row", { name: /FPT/ });
  await expect(fpt).toContainText("đang nắm");
  await expect(fpt).toContainText("chưa đủ dữ liệu");
  // nothing held can be measured yet: no "0% … 0%" shares, only how much is unmeasured
  await expect(box.getByTestId("sensitivity-exposure")).toHaveText("100% vốn ở mã chưa đủ dữ liệu để đo.");
  // the span can be widened; the reading reloads for it
  const spans = box.getByRole("radiogroup", { name: "Khoảng đo" });
  await expect(spans.getByLabel("3 năm")).toBeChecked();
  await spans.getByLabel("Toàn bộ").check();
  await expect(box).toContainText("toàn bộ lịch sử chung");
  await expect(box.getByRole("row", { name: /FPT/ })).toContainText("đang nắm");
});

test("no horizontal page scroll on the macro page at 375px", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 900 });
  await openMacro(page);
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(0);
});

test("automated rows with a manual fallback, and US PMI entered by hand", async ({ page }) => {
  await openMacro(page);
  for (const label of [/Cung tiền M2/, /PMI sản xuất Việt Nam/, /10 năm của Việt Nam/, /liên ngân hàng VN qua đêm/]) {
    const row = page.getByRole("row", { name: label });
    await expect(row).toContainText("Tự động");
    await expect(row.getByRole("button", { name: "Nhập" })).toBeVisible();
  }
  // Since 26/10/2026 the US PMI publishers block automated reading: hand entry only.
  const us = page.getByRole("row", { name: /PMI sản xuất Mỹ/ });
  await expect(us).toContainText("Nhập tay");
  await expect(us.getByRole("button", { name: "Nhập" })).toBeVisible();
});

test("the rate cycle line says which rates it reads and waits for six months of Vietnam data", async ({ page }) => {
  await openMacro(page);
  const box = page.getByRole("region", { name: "Mốc chu kỳ lãi suất" });
  await expect(box).toBeVisible();
  await expect(box).toContainText("chưa đủ 6 tháng dữ liệu Việt Nam");
  await expect(box).toContainText("không phải khuyến nghị");
});
