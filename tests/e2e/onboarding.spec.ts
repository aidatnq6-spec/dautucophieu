import { expect, test, type Page } from "@playwright/test";

// Synthetic data only. The backend fixture keeps state for the whole run, so steps are serial.
test.describe.configure({ mode: "serial" });

test.beforeEach(async ({ context }) => {
  await context.addCookies([{ name: "investment_session", value: process.env.INVESTMENT_E2E_SESSION!, domain: "127.0.0.1", path: "/" }]);
});

async function addEvent(page: Page, fields: { type: string; day: string; seq?: string; ticker?: string; qty?: string; price?: string; amount?: string }) {
  await page.getByRole("button", { name: "Ghi nhận giao dịch" }).click();
  const form = page.getByRole("form", { name: "Ghi nhận giao dịch" });
  await form.getByLabel("Loại giao dịch").selectOption(fields.type);
  await form.getByLabel("Ngày giao dịch").fill(fields.day);
  await form.getByLabel("Thứ tự trong ngày").fill(fields.seq ?? "0");
  if (fields.ticker) {
    await form.getByLabel("Mã cổ phiếu").fill(fields.ticker);
    await form.getByLabel("Số lượng").fill(fields.qty!);
    await form.getByLabel("Giá thực hiện (đ/cp)").fill(fields.price!);
  } else {
    await form.getByLabel("Số tiền (đ)").fill(fields.amount!);
  }
  await form.getByRole("button", { name: "Ghi vào sổ" }).click();
  await expect(form).toBeHidden();
}

test("unauthenticated visitors are sent to login", async ({ browser }) => {
  const anonymous = await browser.newContext();
  const page = await anonymous.newPage();
  await page.goto("/portfolio");
  await expect(page).toHaveURL(/\/login$/);
  await anonymous.close();
});

test("without profile and survey, personalisation stays locked", async ({ page }) => {
  await page.goto("/portfolio");
  await expect(page.getByTestId("personalization-locked")).toBeVisible();
});

test("a filled but unsubmitted transaction writes nothing", async ({ page }) => {
  await page.goto("/portfolio");
  await page.getByRole("button", { name: "Ghi nhận giao dịch" }).click();
  await page.getByRole("form", { name: "Ghi nhận giao dịch" }).getByLabel("Số tiền (đ)").fill("5.000.000");
  await page.reload();
  await expect(page.getByText("Phiên bản sổ 0")).toBeVisible();
  await expect(page.getByTestId("cash")).toHaveText("0 đ");
});

test("onboarding confirms the reviewed capital breakdown and the 13-question survey", async ({ page }) => {
  await page.goto("/onboarding");
  const form = page.getByRole("form", { name: "Hồ sơ tài chính" });
  await form.getByLabel("Quỹ dự phòng cần giữ (đ)").fill("200.000.000");
  await form.getByLabel("Số tiền (đ)").fill("800.000.000");
  await form.getByLabel("Phần dành cho quỹ dự phòng (đ)").fill("200.000.000");
  await form.getByRole("button", { name: "Xem bảng tính vốn" }).click();
  const table = page.getByRole("table", { name: "Bảng tính vốn có thể đầu tư" });
  await expect(table).toContainText("600.000.000 đ");
  await page.getByRole("button", { name: "Xác nhận bảng tính này" }).click();

  const survey = page.getByRole("form", { name: "Khảo sát rủi ro" });
  await expect(survey).toBeVisible();
  await survey.getByRole("button", { name: "Lưu câu trả lời" }).click();
  await expect(page.locator(".errors[role=alert]")).toContainText("Câu 1 chưa trả lời");
  await expect(page.locator(".errors[role=alert]")).toBeFocused();
  for (let q = 1; q <= 13; q++) await survey.locator(`input[name="q${q}"][value="C"]`).check();
  await survey.getByRole("button", { name: "Lưu câu trả lời" }).click();
  await expect(page.getByRole("link", { name: "Mở sổ giao dịch" })).toBeVisible();

  await page.goto("/profile");
  await expect(page.getByText("Cân bằng · 39 điểm")).toBeVisible();
  await expect(page.getByText("600.000.000 đ").first()).toBeVisible();
});

test("trades show moving-average cost and realised gain; a correction replays the ledger", async ({ page }) => {
  await page.goto("/portfolio");
  await expect(page.getByTestId("personalization-locked")).toHaveCount(0);
  await addEvent(page, { type: "deposit", day: "2026-01-02", amount: "10.000.000" });
  await addEvent(page, { type: "buy", day: "2026-01-05", ticker: "FPT", qty: "100", price: "20000" });
  await addEvent(page, { type: "buy", day: "2026-01-06", ticker: "FPT", qty: "100", price: "30000" });
  await addEvent(page, { type: "sell", day: "2026-01-07", ticker: "FPT", qty: "100", price: "28000" });
  await expect(page.getByTestId("realized")).toHaveText("Lãi 300.000 đ");
  await expect(page.getByTestId("avg-FPT")).toHaveText("25.000");

  const firstBuy = page.getByRole("row").filter({ hasText: "2026-01-05" });
  await firstBuy.getByRole("button", { name: /Sửa/ }).click();
  const edit = page.getByRole("form", { name: "Sửa giao dịch" });
  await edit.getByLabel("Giá thực hiện (đ/cp)").fill("22000");
  await edit.getByLabel("Lý do sửa").fill("Sửa theo sao kê");
  await edit.getByRole("button", { name: "Lưu bản sửa" }).click();
  await expect(page.getByTestId("realized")).toHaveText("Lãi 200.000 đ");
  await expect(page.getByTestId("avg-FPT")).toHaveText("26.000");
  await expect(page.getByText("1 lần sửa/hủy/khôi phục được lưu vết.")).toBeVisible();
});

test("an impossible sale is refused with a field-level message", async ({ page }) => {
  await page.goto("/portfolio");
  await page.getByRole("button", { name: "Ghi nhận giao dịch" }).click();
  const form = page.getByRole("form", { name: "Ghi nhận giao dịch" });
  await form.getByLabel("Loại giao dịch").selectOption("sell");
  await form.getByLabel("Ngày giao dịch").fill("2026-01-08");
  await form.getByLabel("Mã cổ phiếu").fill("FPT");
  await form.getByLabel("Số lượng").fill("1000");
  await form.getByLabel("Giá thực hiện (đ/cp)").fill("30000");
  await form.getByRole("button", { name: "Ghi vào sổ" }).click();
  await expect(page.locator(".errors[role=alert]")).toContainText("Số lượng bán vượt số cổ phiếu đang có.");
});

for (const width of [375, 768, 1440]) {
  test(`no horizontal page scroll at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    for (const path of ["/portfolio", "/onboarding", "/profile"]) {
      await page.goto(path, { waitUntil: "domcontentloaded" });
      await expect(page.locator("body")).toBeVisible();
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
      expect(overflow, path).toBeLessThanOrEqual(0);
    }
  });
}
