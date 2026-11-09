import { expect, test } from "@playwright/test";
import { seedOwner, signIn } from "./helpers";

test.beforeEach(async ({ context }) => signIn(context));
const tabs = (page: import("@playwright/test").Page) => page.getByRole("tablist", { name: "Các phần của hồ sơ" });

test("the profile opens on Rủi ro and shows one part at a time", async ({ page }) => {
  await seedOwner(page);
  await page.goto("/profile");
  await expect(tabs(page).getByRole("tab")).toHaveText(["Rủi ro", "Tài sản", "Dòng tiền & mục tiêu", "Kế hoạch"]);
  await expect(tabs(page).getByRole("tab", { name: "Rủi ro" })).toHaveAttribute("aria-selected", "true");
  await expect(page.getByRole("region", { name: "Khảo sát rủi ro" })).toBeVisible();
  await expect(page.getByRole("region", { name: "Tháp tài sản" })).toHaveCount(0);
  for (const [tab, region] of [["Tài sản", "Tháp tài sản"], ["Tài sản", "Sổ tài sản"], ["Tài sản", "Bất động sản và khoản vay"], ["Tài sản", "Mục đích từng khoản tiền"], ["Dòng tiền & mục tiêu", "Sức khỏe tài chính"], ["Dòng tiền & mục tiêu", "Mục tiêu dòng tiền thụ động"], ["Kế hoạch", "Góp vốn đều"], ["Kế hoạch", "Kế hoạch tích sản"], ["Kế hoạch", "Tiền mới tháng này đi đâu"]]) {
    await tabs(page).getByRole("tab", { name: tab, exact: true }).click();
    await expect(page.getByRole("region", { name: region, exact: true })).toBeVisible();
  }
  await expect(page.getByRole("region", { name: "Khảo sát rủi ro" })).toHaveCount(0);
});

test("the open part is in the address, survives a reload, and an unknown one falls back to the first", async ({ page }) => {
  await page.goto("/profile");
  await tabs(page).getByRole("tab", { name: "Kế hoạch" }).click();
  await expect(page).toHaveURL(/\/profile\?tab=ke-hoach$/);
  await page.reload();
  await expect(tabs(page).getByRole("tab", { name: "Kế hoạch" })).toHaveAttribute("aria-selected", "true");
  await page.goto("/profile?tab=khong-co");
  await expect(tabs(page).getByRole("tab", { name: "Rủi ro" })).toHaveAttribute("aria-selected", "true");
});

test("arrow keys move between parts, what is typed stays, and shortcuts list only the open part", async ({ page }) => {
  await page.goto("/profile?tab=ke-hoach");
  const name = page.getByRole("region", { name: "Kế hoạch tích sản" }).getByLabel("Tên kế hoạch");
  await expect(name).toBeEnabled();
  await name.fill("Đang gõ dở");
  const jumps = page.getByRole("navigation", { name: "Trên trang này" });
  await expect(jumps).toContainText("Kế hoạch tích sản");
  await expect(jumps).not.toContainText("Tháp tài sản");
  await tabs(page).getByRole("tab", { name: "Kế hoạch" }).focus();
  await page.keyboard.press("ArrowLeft");
  await expect(tabs(page).getByRole("tab", { name: "Dòng tiền & mục tiêu" })).toBeFocused();
  await expect(tabs(page).getByRole("tab", { name: "Dòng tiền & mục tiêu" })).toHaveAttribute("aria-selected", "true");
  await tabs(page).getByRole("tab", { name: "Kế hoạch" }).click();
  await expect(name).toHaveValue("Đang gõ dở");
});

test("the tabs add no sideways scroll at 375px", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 800 });
  await page.goto("/profile");
  await expect(tabs(page)).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)).toBeLessThanOrEqual(0);
});

test("the menu is grouped, and every link fits a laptop screen", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");
  const nav = page.getByRole("navigation", { name: "Điều hướng chính" });
  for (const [group, link] of [["Tài sản", "Hồ sơ & rủi ro"], ["Thị trường", "Vĩ mô"], ["Công cụ", "Định giá"]]) {
    await expect(nav.getByRole("group", { name: group }).getByRole("link", { name: link })).toBeVisible();
  }
  await expect(nav.getByRole("link")).toHaveCount(14);
  await expect(nav.getByRole("link", { name: "Cài đặt" })).toBeInViewport({ ratio: 1 });
  await page.setViewportSize({ width: 375, height: 800 });
  await expect(nav.getByText("Thị trường", { exact: true })).toBeHidden();
});
