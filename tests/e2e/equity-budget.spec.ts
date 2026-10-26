import { expect, test } from "@playwright/test";
import { seedOwner, signIn } from "./helpers";

// seedOwner: risk answers "C" (Cân bằng, 35%), no emergency reserve, FPT bought 100 × 50,000 (cost 5.000.000 đ).
test.describe.configure({ mode: "serial" });
test.beforeEach(async ({ context }) => signIn(context));

test("entering total financial assets shows the money for stocks and room left at cost", async ({ page }) => {
  await seedOwner(page);
  await page.goto("/portfolio");
  await expect(page.getByText("Chưa nhập tổng tài sản tài chính")).toBeVisible();
  await page.goto("/profile");
  const box = page.getByRole("region", { name: "Vốn dành cho cổ phiếu" });
  await box.getByLabel("Tổng tài sản tài chính (đ)").fill("");
  await box.getByLabel("Tổng tài sản tài chính (đ)").pressSequentially("100000000000");
  await expect(box.getByLabel("Tổng tài sản tài chính (đ)")).toHaveValue("100.000.000.000");
  await box.getByRole("button", { name: "Tính vốn cho cổ phiếu" }).click();
  await expect(box).toContainText("Cân bằng");
  await expect(box).toContainText("35%");
  // Other specs may confirm a profile with an emergency reserve: expect (total − shown deduction) × 35%.
  const deducted = BigInt((await box.getByTestId("equity-deductions").innerText()).replace(/\D/g, "") || "0");
  const budget = ((BigInt(100_000_000_000) - deducted) * BigInt(35) / BigInt(100)).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ".");
  await expect(box.getByTestId("equity-budget")).toHaveText(`${budget} đ`);
  await expect(box).toContainText(/Đang nắm \(theo giá mua\): [\d.]+ đ/); // other specs may add FPT buys
  await expect(box).toContainText(/còn có thể mua thêm [\d.]+ đ/);

  await page.goto("/portfolio");
  await expect(page.getByText(`Tỷ trọng trên vốn dành cho cổ phiếu (${budget} đ)`, { exact: false })).toBeVisible();
  await expect(page.getByText("Chưa nhập tổng tài sản tài chính")).toBeHidden();
});

test("no horizontal scroll on the profile page at 375px", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 900 });
  await page.goto("/profile");
  await expect(page.getByRole("region", { name: "Vốn dành cho cổ phiếu" })).toBeVisible();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(0);
});
