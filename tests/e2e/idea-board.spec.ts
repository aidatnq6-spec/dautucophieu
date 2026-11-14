import { expect, test } from "@playwright/test";
import { signIn } from "./helpers";

test.beforeEach(async ({ context }) => signIn(context));

test("a ticker goes on the board as an idea and moves column by column", async ({ page }) => {
  await page.goto("/journal");
  const board = page.getByRole("region", { name: "Quy trình đầu tư" });
  await board.getByLabel("Mã mới").fill("mwg");
  await board.getByRole("button", { name: "Thêm vào Ý tưởng" }).click();
  await expect(board.getByRole("group", { name: "Ý tưởng" }).getByRole("article", { name: "Thẻ MWG" })).toBeVisible();
  await board.getByRole("button", { name: "Chuyển MWG sang phải" }).click();
  const card = board.getByRole("group", { name: "Đang nghiên cứu" }).getByRole("article", { name: "Thẻ MWG" });
  await expect(card).toContainText("0 ngày");
  await card.getByRole("button", { name: "Sửa MWG" }).click();
  await card.getByLabel("Ghi chú MWG").fill("Đọc báo cáo quý");
  await card.getByRole("button", { name: "Lưu" }).click();
  await expect(card).toContainText("Đọc báo cáo quý");
  page.once("dialog", (d) => d.accept());
  await card.getByRole("button", { name: "Xóa MWG" }).click();
  await expect(board.getByRole("article", { name: "Thẻ MWG" })).toHaveCount(0);
});

test("the board adds no sideways scroll at 375px", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 800 });
  await page.goto("/journal");
  await expect(page.getByRole("region", { name: "Quy trình đầu tư" }).getByText("Đang tải…")).toHaveCount(0);
  expect(await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)).toBeLessThanOrEqual(0);
});
