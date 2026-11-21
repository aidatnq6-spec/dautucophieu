import { expect, test } from "@playwright/test";
import { signIn } from "./helpers";

// Sử dụng phần mềm: each page opened is counted on this computer and shown on Cài đặt.
test.beforeEach(async ({ context }) => signIn(context));

test("a page opened is counted and listed by its menu name on Cài đặt", async ({ page }) => {
  const counted = page.waitForResponse((r) => r.url().includes("/usage/visit") && r.request().method() === "POST");
  await page.goto("/macro");
  expect((await counted).status()).toBe(200);
  await page.goto("/settings");
  const box = page.getByRole("region", { name: "Sử dụng phần mềm" });
  const visits = box.getByRole("table", { name: "Lượt mở trang" });
  await expect(visits.getByRole("row", { name: /Vĩ mô/ })).toBeVisible();
  await expect(box).toContainText("Đã ghi từ");
  await expect(box).toContainText("đã che mã cổ phiếu và số tiền");
});
