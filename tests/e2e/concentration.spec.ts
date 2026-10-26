import { expect, test } from "@playwright/test";
import { seedOwner, signIn } from "./helpers";

// Synthetic owner (seedOwner): 100 FPT at 60.000 đ, a few percent of investable capital; FPT is "Công nghệ Thông tin" in the fixture.
test.describe.configure({ mode: "serial" });
test.beforeEach(async ({ context }) => signIn(context));

async function openPortfolio(page: import("@playwright/test").Page) {
  await seedOwner(page);
  await page.goto("/portfolio");
  await expect(page.getByRole("region", { name: "Phân bổ và rủi ro tập trung" })).toBeVisible();
}

test("weights by ticker and sector on investable capital, with cash, against the 25% limit", async ({ page }) => {
  await openPortfolio(page);
  const box = page.getByRole("region", { name: "Phân bổ và rủi ro tập trung" });
  await expect(box).toContainText("ngưỡng 25%");
  await expect(box).toContainText("tính theo giá mua");
  await expect(box.getByRole("table", { name: "Tỷ trọng theo mã" }).getByRole("columnheader", { name: "Giá vốn" })).toBeVisible();
  await expect(box.getByRole("table", { name: "Tỷ trọng theo mã" }).getByRole("row", { name: /FPT/ })).toContainText(/\d+(,\d)?%/);
  // One ticker per sector: the sector table would repeat the ticker table, so it is replaced by a one-line note.
  await expect(box.getByRole("table", { name: "Tỷ trọng theo ngành" })).toHaveCount(0);
  await expect(box).toContainText("Mỗi ngành chỉ có 1 mã nên tỷ trọng ngành bằng tỷ trọng mã.");
  await expect(box.getByRole("row", { name: /Còn trống/ })).toContainText(/chưa dùng của vốn (cho cổ phiếu|có thể đầu tư)/);
  await expect(box).not.toContainText("Tiền mặt");
  await expect(box).not.toContainText("vượt 25%");
});

test("what-if shows the weights after a buy without recording it", async ({ page }) => {
  await openPortfolio(page);
  const box = page.getByRole("region", { name: "Phân bổ và rủi ro tập trung" });
  await box.getByLabel("Mã", { exact: true }).fill("FPT");
  await box.getByLabel("Số tiền (đ, âm là bán)").fill("300000000");
  await box.getByRole("button", { name: "Thử" }).click();
  await expect(box.getByRole("table", { name: "Tỷ trọng theo mã" }).getByRole("row", { name: /FPT/ })).toContainText("vượt 25%");
  await expect(box).toContainText("Chỉ là thử");
  await page.reload();
  await expect(page.getByRole("region", { name: "Phân bổ và rủi ro tập trung" })).not.toContainText("vượt 25%");
});

test("the limit is set in Cài đặt", async ({ page }) => {
  await page.goto("/settings");
  await expect(page.getByLabel("Ngưỡng tập trung một mã hoặc một ngành (%)")).toHaveValue("25");
});

test("no horizontal scroll on the portfolio page with the concentration block at 375px", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 900 });
  await openPortfolio(page);
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(0);
});
