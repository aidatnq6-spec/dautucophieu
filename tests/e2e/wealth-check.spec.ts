import { expect, test } from "@playwright/test";
import { seedOwner, signIn } from "./helpers";

// Savings rate against the rule of thumb "at least your age in percent" (VWA); inputs are the owner's own.
test.describe.configure({ mode: "serial" });
test.beforeEach(async ({ context }) => signIn(context));

const group = (n: number) => String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ".");

test("income, spending and birth year give the savings rate against the age rule", async ({ page }) => {
  await seedOwner(page);
  await page.goto("/profile");
  const box = page.getByRole("region", { name: "Sức khỏe tài chính" });
  await expect(box.getByLabel("Thu nhập hằng tháng (đ)")).toBeEnabled();  // enabled once the saved figures have loaded
  await box.getByLabel("Thu nhập hằng tháng (đ)").fill("");
  await box.getByLabel("Chi tiêu hằng tháng (đ)").fill("");
  await box.getByLabel("Thu nhập hằng tháng (đ)").pressSequentially("25000000");
  await expect(box.getByLabel("Thu nhập hằng tháng (đ)")).toHaveValue("25.000.000");
  await box.getByLabel("Chi tiêu hằng tháng (đ)").pressSequentially("17000000");
  await box.getByLabel("Năm sinh").fill("1989");
  await box.getByRole("button", { name: "Kiểm tra" }).click();
  const age = new Date().getFullYear() - 1989;
  await expect(box.getByTestId("wc-savings")).toHaveText("8.000.000 đ");
  await expect(box.getByTestId("wc-rate")).toHaveText("32%");
  await expect(box.getByTestId("wc-target")).toHaveText(`≥ ${age}%`);
  await expect(box.getByTestId("wc-result")).toHaveText(`Chưa đạt: cần tích lũy thêm ${group(25_000_000 * age / 100 - 8_000_000)} đ/tháng`);
  await expect(box).toContainText("quy tắc kinh nghiệm");
});

test("no horizontal scroll on the profile page at 375px with the check", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 900 });
  await page.goto("/profile");
  await expect(page.getByRole("region", { name: "Sức khỏe tài chính" })).toBeVisible();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(0);
});
