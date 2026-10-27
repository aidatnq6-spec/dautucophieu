import { expect, test } from "@playwright/test";
import { call, seedOwner, signIn } from "./helpers";

// seedOwner deposits 100 tr on 01/02/2026; contributions are read from the ledger's deposits less withdrawals each month.
test.describe.configure({ mode: "serial" });
test.beforeEach(async ({ context }) => signIn(context));

test("a monthly plan shows each month from the ledger, the streak and the totals", async ({ page }) => {
  await seedOwner(page);
  // The shared test ledger is written by other specs too, so this one records its own deposit in a month nobody else uses.
  const ledger = await (await call(page, "GET", "ledger")).json();
  if (!ledger.events.some((e: { event_id: string }) => e.event_id === "contrib-d")) {
    expect((await call(page, "POST", "ledger/events", { event: { event_id: "contrib-d", type: "deposit", effective_at: "2026-09-15", sequence: 7,
      amount: "8000000" }, expected_version: ledger.version, request_id: "contrib-d" })).ok()).toBe(true);
  }
  await page.goto("/profile");
  const box = page.getByRole("region", { name: "Góp vốn đều" });
  await expect(box.getByLabel("Số tiền góp mỗi tháng (đ)")).toBeEnabled();
  await box.getByLabel("Số tiền góp mỗi tháng (đ)").fill("");
  await box.getByLabel("Số tiền góp mỗi tháng (đ)").pressSequentially("8000000");
  await box.getByLabel("Ngày góp trong tháng").fill("1");
  await box.getByLabel("Bắt đầu từ tháng").fill("2026-09");
  await box.getByRole("button", { name: "Lưu kế hoạch" }).click();
  const months = box.getByRole("list", { name: "Các tháng góp vốn" });
  await expect(months.getByTestId("month-2026-09")).toContainText("đã góp");
  await expect(box.getByTestId("contrib-streak")).toHaveText(/^\d+ tháng$/);
  await expect(box).toContainText(/Tổng đã góp: [\d.]+ đ \/ kế hoạch [\d.]+ đ/);
});

test("no horizontal scroll on the profile page at 375px with the plan", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 900 });
  await page.goto("/profile");
  await expect(page.getByRole("region", { name: "Góp vốn đều" })).toBeVisible();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(0);
});
