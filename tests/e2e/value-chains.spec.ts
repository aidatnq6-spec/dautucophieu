import { expect, test } from "@playwright/test";
import { signIn } from "./helpers";

// The committed chains (all drafts) read against synthetic oil and rubber series from the fixture backend.
test.beforeEach(async ({ context }) => signIn(context));

async function openSection(page: import("@playwright/test").Page) {
  await page.goto("/value-chains");
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

test("the owner approves a chain in the app and can withdraw it", async ({ page }) => {
  const section = await openSection(page);
  const rubber = section.getByRole("button", { name: /Cao su tự nhiên/ });
  await rubber.click();
  const diagram = page.getByRole("region", { name: "Chuỗi giá trị Cao su tự nhiên" });
  await diagram.getByLabel("Ghi chú khi duyệt (không bắt buộc)").fill("Đã đọc ACBS");
  await diagram.getByRole("button", { name: "Duyệt chuỗi này" }).click();
  await expect(diagram).toContainText("Đã duyệt ngày");
  await expect(diagram).toContainText("Đã đọc ACBS");
  await expect(diagram).not.toContainText("Chưa duyệt:");
  await expect(rubber).toContainText("Thuận gió");  // rubber reads tốt 100% in the fixture
  await diagram.getByRole("button", { name: "Bỏ duyệt" }).click();
  await expect(rubber).toContainText("Chưa duyệt");
  await expect(diagram.getByRole("button", { name: "Duyệt chuỗi này" })).toBeVisible();
});

test("a factor without a stored series says so instead of guessing", async ({ page }) => {
  const section = await openSection(page);
  await section.getByRole("button", { name: /^Thép/ }).click();
  const steel = page.getByRole("region", { name: "Chuỗi giá trị Thép" });
  await expect(steel).toContainText("Giá than luyện thép: chưa đánh giá được");
  await expect(steel).toContainText("Ứng dụng chưa có chuỗi số liệu cho yếu tố này.");
});

test("tariffs are events: off the bar, with a link to the macro calendar, beside the measured cá tra exports", async ({ page }) => {
  const section = await openSection(page);
  const seafood = section.getByRole("button", { name: /Thủy sản/ });
  await expect(seafood).not.toContainText("Chưa có yếu tố đo được bằng số liệu");  // Xuất khẩu cá tra is measured; the tariff is not
  await seafood.click();
  const diagram = page.getByRole("region", { name: "Chuỗi giá trị Thủy sản" });
  await expect(diagram).toContainText("Thuế quan và phòng vệ thương mại Mỹ: sự kiện");
  await expect(diagram).toContainText("Xuất khẩu cá tra:");
  await expect(diagram.getByRole("link", { name: "Lịch và nhật ký vĩ mô" })).toHaveAttribute("href", "/macro#lich-vi-mo");
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
