import { expect, test } from "@playwright/test";
import { signIn } from "./helpers";

// The committed chains (all drafts) read against synthetic oil and rubber series from the fixture backend.
test.beforeEach(async ({ context }) => signIn(context));

async function openSection(page: import("@playwright/test").Page) {
  await page.goto("/market");
  const section = page.getByRole("region", { name: "Chuỗi giá trị" });
  await expect(section.getByRole("button", { name: /Cao su tự nhiên/ })).toBeVisible();
  return section;
}

test("each chain is a card; a card opens its sourced Đầu vào → Trung gian → Đầu ra", async ({ page }) => {
  const section = await openSection(page);
  const rubber = section.getByRole("button", { name: /Cao su tự nhiên/ });
  await expect(rubber).toContainText("Chưa duyệt");
  await expect(rubber).toContainText("tốt 100%");
  await rubber.click();
  await expect(rubber).toHaveAttribute("aria-expanded", "true");
  // The diagram opens right under the card that was clicked, not after all the cards.
  await expect(section.locator('button[aria-expanded="true"] + section')).toHaveAttribute("aria-label", "Chuỗi giá trị Cao su tự nhiên");
  const diagram = page.getByRole("region", { name: "Chuỗi giá trị Cao su tự nhiên" });
  for (const stage of ["Đầu vào", "Trung gian", "Đầu ra"]) await expect(diagram.getByRole("heading", { name: stage })).toBeVisible();
  await expect(diagram).toContainText("Giá cao su: tốt");
  await expect(diagram.getByRole("link", { name: /ACBS, 17\/06\/2026, tr\. 2/ }).first()).toHaveAttribute("href", /acbs\.com\.vn/);
  await diagram.getByRole("link", { name: "GVR" }).click();
  await expect(page).toHaveURL(/\/research\/GVR$/);
});

test("a factor without a stored series says so instead of guessing", async ({ page }) => {
  const section = await openSection(page);
  await section.getByRole("button", { name: /^Thép/ }).click();
  const steel = page.getByRole("region", { name: "Chuỗi giá trị Thép" });
  await expect(steel).toContainText("Giá than luyện thép: chưa đánh giá được");
  await expect(steel).toContainText("Ứng dụng chưa có chuỗi số liệu cho yếu tố này.");
});

test("no horizontal scroll with a chain open at 375px", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 900 });
  const section = await openSection(page);
  await section.getByRole("button", { name: /Phân bón/ }).click();
  const fertiliser = page.getByRole("region", { name: "Chuỗi giá trị Phân bón" });
  await expect(fertiliser).toContainText("70–80% giá thành");  // a reported share shows as whole percents
  await fertiliser.scrollIntoViewIfNeeded();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(0);
});
