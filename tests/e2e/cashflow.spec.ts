import { expect, test } from "@playwright/test";
import { seedOwner, signIn } from "./helpers";

test.beforeEach(async ({ context }) => signIn(context));
const region = (page: import("@playwright/test").Page) => page.getByRole("region", { name: "Thu chi hằng tháng" });
const FIXTURE = "../../tests/e2e/fixtures/thu-chi-mau.xlsx";  // made-up figures in the layout of the owner's workbook

test("an uploaded workbook is previewed before anything is kept, then its months are shown", async ({ page }) => {
  await seedOwner(page);
  // the suite shares one store and other specs need it without imported months: saving is answered here, the preview is real
  await page.route("**/api/internal/cashflow/import", async (route) => {
    const body = route.request().postDataJSON();
    if (!body.commit) return route.continue();
    const months = Array.from({ length: 10 }, (_, i) => ({ month: `2026-${String(i + 1).padStart(2, "0")}`, income: String(61_000_000 + i * 1_000_000), spending: String(40_500_000 + i * 500_000),
      saved: String(20_500_000 + i * 500_000), rate: "0.3500", passive: "23000000", current: false }));
    await route.fulfill({ json: { version: 1, months, sources: [{ label: "Căn hộ cho thuê", group: "business", passive: true }], age: 41, imported_at: "2026-11-10T09:00:00+07:00",
      average: { months: ["2026-08", "2026-09", "2026-10"], income: "69000000", spending: "44500000", passive: "23000000", rate: "0.3551" } } });
  });
  await page.goto("/profile?tab=dong-tien");
  const box = region(page);
  await expect(box.getByLabel("File Excel thu chi")).toBeEnabled();
  await box.getByLabel("File Excel thu chi").setInputFiles(FIXTURE);
  await expect(box.getByTestId("cf-preview")).toContainText("năm 2026, đọc được 10 tháng");
  await box.getByRole("button", { name: "Lưu vào phần mềm" }).click();
  await expect(box.getByTestId("cf-passive")).toHaveText("23.000.000 đ");
  await expect(box.getByTestId("cf-rate")).toHaveText("35,5%");
  await expect(box.getByRole("img", { name: /Thu nhập và chi tiêu 10 tháng/ })).toBeVisible();
});

test("a file that is not the workbook is refused with a reason", async ({ page }) => {
  await page.goto("/profile?tab=dong-tien");
  const box = region(page);
  await expect(box.getByLabel("File Excel thu chi")).toBeEnabled();
  await box.getByLabel("File Excel thu chi").setInputFiles({ name: "khac.xlsx", mimeType: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", buffer: Buffer.from("khong phai excel") });
  await expect(box.getByRole("alert")).toContainText("Không đọc được file");
});

test("the section adds no sideways scroll at 375px", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 800 });
  await page.goto("/profile?tab=dong-tien");
  await expect(region(page)).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)).toBeLessThanOrEqual(0);
});
