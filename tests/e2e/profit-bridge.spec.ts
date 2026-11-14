import { expect, test } from "@playwright/test";
import { signIn } from "./helpers";

test.beforeEach(async ({ context }) => signIn(context));

test("a watched company's page explains its quarter's profit against the same quarter last year", async ({ page }) => {
  await page.goto("/research/FPT");
  const box = page.getByRole("region", { name: "Vì sao lợi nhuận quý thay đổi" });
  await expect(box.getByRole("combobox", { name: "Quý" })).toHaveValue("2025-Q4");
  await expect(box.getByTestId("profit-summary")).toContainText("Q4/2025");
  await expect(box.getByRole("img", { name: "Thác nước lợi nhuận FPT Q4/2025" })).toBeVisible();
  await box.getByRole("combobox", { name: "Quý" }).selectOption("2025-Q1");
  await expect(box.getByTestId("profit-summary")).toContainText("Q1/2025");
});

test("a bank's page has no profit waterfall", async ({ page }) => {
  await page.goto("/research/VCB");
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await expect(page.getByRole("region", { name: "Vì sao lợi nhuận quý thay đổi" })).toHaveCount(0);
});
