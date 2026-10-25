import { expect, test } from "@playwright/test";
import { seedOwner, signIn } from "./helpers";

// Synthetic fixture data only: after-close report from the reports page (C layout).
test.describe.configure({ mode: "serial" });
test.beforeEach(async ({ context }) => signIn(context));

// The list loads from an effect, so once it has rendered the page is hydrated and inputs keep what we type.
async function openReports(page: import("@playwright/test").Page) {
  await page.goto("/reports");
  await expect(page.getByText("Đang tải…")).toHaveCount(0);
}

test("creating an after-close report shows progress and a readable brief", async ({ page }) => {
  await seedOwner(page);
  await openReports(page);
  await page.getByLabel("Ngày phiên").fill("2026-10-23");
  await page.getByRole("button", { name: "Tạo bản tin" }).click();
  await expect(page.getByRole("status")).toContainText(/Đã phát hành|Thiếu dữ liệu/);
  await page.getByRole("link", { name: "Phiên 2026-10-23" }).first().click();
  await expect(page.getByRole("heading", { name: "Bản tin phiên 2026-10-23" })).toBeVisible();
  for (const heading of ["Kết luận", "Danh mục", "Cơ hội và cảnh báo", "Kiểm tra dữ liệu"]) {
    await expect(page.getByRole("heading", { name: heading })).toBeVisible();
  }
  await expect(page.getByText("market_provenance:synthetic")).toBeVisible();
  await expect(page.getByText("(số liệu đã kiểm chứng, không dùng AI)")).toBeVisible();
});

test("re-running the same session does not create a second report", async ({ page }) => {
  await openReports(page);
  await expect(page.getByRole("link", { name: "Phiên 2026-10-23" }).first()).toBeVisible();
  const before = await page.getByRole("link", { name: "Phiên 2026-10-23" }).count();
  await page.getByLabel("Ngày phiên").fill("2026-10-23");
  await page.getByRole("button", { name: "Tạo bản tin" }).click();
  await expect(page.getByRole("status")).toContainText(/Đã phát hành|Thiếu dữ liệu/);
  await expect(page.getByRole("link", { name: "Phiên 2026-10-23" })).toHaveCount(before);
});

test("a future session is refused", async ({ page }) => {
  await openReports(page);
  await page.getByLabel("Ngày phiên").fill("2099-01-02");
  await page.getByRole("button", { name: "Tạo bản tin" }).click();
  await expect(page.getByRole("alert").filter({ hasText: "Phiên chưa diễn ra" })).toBeVisible();
});
