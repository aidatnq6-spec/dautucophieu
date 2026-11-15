import { expect, test } from "@playwright/test";
import { signIn } from "./helpers";

test.beforeEach(async ({ context }) => signIn(context));

test("Toàn ngành shows a sector's quarterly heatmap with its layers, and the sector's valuation", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("navigation", { name: "Điều hướng chính" }).getByRole("link", { name: "Ngành theo quý" }).click();
  await expect(page).toHaveURL(/\/sectors/);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Ngành theo quý");
  await page.getByRole("combobox", { name: "Ngành", exact: true }).selectOption({ label: "Công nghệ Thông tin (1 mã)" });
  await expect(page).toHaveURL(/nganh=cong-nghe-thong-tin/);
  const heat = page.getByRole("region", { name: "Bản đồ nhiệt theo quý" });
  await expect(heat.getByRole("table", { name: "Bản đồ nhiệt Công nghệ Thông tin" }).getByRole("row", { name: /FPT/ })).toBeVisible();
  await heat.getByRole("radio", { name: "Dòng tiền kinh doanh (tỷ)" }).check();
  await expect(heat.getByRole("row", { name: /Cả ngành/ })).toBeVisible();
  await expect(page.getByRole("region", { name: "Định giá ngành" })).toContainText("ít nhất 3 mã");  // one ticker: no median, so no table
});

test("a bank sector keeps to the profit layer", async ({ page }) => {
  await page.goto("/sectors?nganh=ngan-hang");
  const heat = page.getByRole("region", { name: "Bản đồ nhiệt theo quý" });
  await expect(heat).toContainText("chỉ có lớp lợi nhuận");
  await expect(heat.getByRole("radio", { name: "Nợ vay so cùng kỳ" })).toBeDisabled();
});

test("Toàn ngành adds no sideways scroll at 375px", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 800 });
  await page.goto("/sectors?nganh=cong-nghe-thong-tin");
  await expect(page.getByRole("region", { name: "Bản đồ nhiệt theo quý" })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)).toBeLessThanOrEqual(0);
});

test("Phân tích ngành is its own menu group, with Chuỗi giá trị and Ngành theo quý", async ({ page }) => {
  await page.goto("/");
  const group = page.getByRole("navigation", { name: "Điều hướng chính" }).getByRole("group", { name: "Phân tích ngành" });
  await expect(group.getByRole("link")).toHaveText(["Chuỗi giá trị", "Ngành theo quý"]);
  await group.getByRole("link", { name: "Chuỗi giá trị" }).click();
  await expect(page).toHaveURL(/\/value-chains$/);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Chuỗi giá trị");
  await expect(page.getByRole("region", { name: "Chuỗi giá trị", exact: true })).toBeVisible();
  await expect(page.getByRole("region", { name: "Bản đồ nhiệt theo quý" })).toHaveCount(0);
  await page.goto("/sectors?tab=chuoi-gia-tri");  // the address of the former tab still arrives
  await expect(page).toHaveURL(/\/value-chains$/);
});

test("the in-session market page no longer carries the value chains, and points to them", async ({ page }) => {
  await page.goto("/market");
  await expect(page.getByRole("region", { name: "Chuỗi giá trị", exact: true })).toHaveCount(0);
  await expect(page.getByRole("link", { name: "Phân tích ngành → Chuỗi giá trị" })).toHaveAttribute("href", "/value-chains");
});
