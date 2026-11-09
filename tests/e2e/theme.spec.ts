import { expect, test } from "@playwright/test";
import { signIn } from "./helpers";

const LIGHT_BG = "rgb(243, 246, 248)", DARK_BG = "rgb(16, 23, 30)";
test.beforeEach(async ({ context }) => signIn(context));

test("the dark theme is kept after a reload and printing stays on the light colours", async ({ page }) => {
  await page.goto("/loan");
  const pick = page.getByRole("group", { name: "Giao diện" });
  await pick.getByRole("button", { name: "Tối", exact: true }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await expect(page.locator("body")).toHaveCSS("background-color", DARK_BG);
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await expect(pick.getByRole("button", { name: "Tối", exact: true })).toHaveAttribute("aria-pressed", "true");
  await page.emulateMedia({ media: "print" });
  await expect(page.locator("body")).toHaveCSS("background-color", LIGHT_BG);
});

test("Theo máy follows the machine, and a choice overrides it", async ({ page }) => {
  await page.emulateMedia({ colorScheme: "dark" });
  await page.goto("/loan");
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  const pick = page.getByRole("group", { name: "Giao diện" });
  await expect(pick.getByRole("button", { name: "Theo máy", exact: true })).toHaveAttribute("aria-pressed", "true");
  await pick.getByRole("button", { name: "Sáng", exact: true }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  await pick.getByRole("button", { name: "Theo máy", exact: true }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await page.emulateMedia({ colorScheme: "light" });
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
});

test("the theme buttons add no sideways scroll at 375px", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 800 });
  await page.goto("/loan");
  await expect(page.getByRole("group", { name: "Giao diện" })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)).toBeLessThanOrEqual(0);
});
