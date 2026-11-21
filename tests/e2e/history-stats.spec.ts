import { expect, test } from "@playwright/test";
import { signIn } from "./helpers";

// Thống kê lịch sử on the fixture's stored VN-Index closes: the page and its horizon switch.
test.beforeEach(async ({ context }) => signIn(context));

test("Thống kê lịch sử shows the P/E groups and the lights' check, and the horizon can be changed", async ({ page }) => {
  await page.goto("/history");
  await expect(page.getByRole("heading", { level: 1, name: "Thống kê lịch sử" })).toBeVisible();
  await expect(page.getByRole("table", { name: "VN-Index sau đó theo nhóm P/E" })).toBeVisible();
  await expect(page.getByTestId("light-history-oil")).toContainText("Giá dầu WTI");
  await page.getByRole("radio", { name: "60 phiên" }).click();
  await expect(page.getByRole("radio", { name: "60 phiên" })).toHaveAttribute("aria-checked", "true");
  await expect(page.getByRole("region", { name: "Số phiên nhìn tới" })).toContainText("VN-Index 60 phiên sau");
  await expect(page.getByRole("navigation", { name: "Điều hướng chính" }).getByRole("link", { name: "Thống kê lịch sử" })).toBeVisible();
});
