import { expect, test } from "@playwright/test";
import { seedOwner, signIn } from "./helpers";

// Synthetic ledger (seedOwner holds FPT) and synthetic closes only.
test.describe.configure({ mode: "serial" });
test.beforeEach(async ({ context }) => signIn(context));

const inDays = (n: number) => new Date(Date.now() + n * 86_400_000).toISOString().slice(0, 10);

test("a thesis needs a loss limit when bought out of fear of missing out, shows a broken condition, and holding on needs a reason", async ({ page }) => {
  await seedOwner(page);
  await page.goto("/portfolio");
  const box = page.getByRole("region", { name: "Luận điểm đầu tư" });
  const missing = box.getByTestId("thesis-missing-FPT");
  await missing.getByRole("button", { name: "Đặt luận điểm" }).click();
  const form = box.getByRole("form", { name: "Luận điểm FPT" });
  await form.getByLabel("Sợ bỏ lỡ").check();
  await form.getByLabel("Vì sao mua, điều gì xảy ra thì bạn đã sai").fill("Ai cũng mua, sợ lỡ sóng");
  await form.getByRole("combobox").first().selectOption("close_below");
  await form.getByLabel("mức giá (nghìn đồng)").fill("1.000");
  await expect(form.getByRole("alert")).toContainText("cần đặt điều kiện “Lỗ so với giá vốn”");
  await expect(form.getByRole("button", { name: "Lưu luận điểm" })).toBeDisabled();
  await form.getByRole("button", { name: "Thêm điều kiện" }).click();
  await form.getByRole("combobox").nth(1).selectOption("loss_vs_cost");
  await form.getByLabel("%").fill("10");
  await form.getByRole("button", { name: "Lưu luận điểm" }).click();

  const card = box.getByRole("article", { name: "Luận điểm FPT" });
  await expect(card).toContainText("“Ai cũng mua, sợ lỡ sóng”");
  const below = card.getByRole("listitem").filter({ hasText: "Giá đóng cửa dưới mức (mức 1.000,00)" });
  await expect(below).toContainText("Bị phá từ");  // the stored closes are far below 1.000: broken the moment it was set
  await below.getByRole("button", { name: "Giữ tiếp, có lý do" }).click();
  const hold = card.getByRole("form", { name: "Giữ tiếp FPT" });
  await expect(hold.getByRole("button", { name: "Giữ tiếp" })).toBeDisabled();  // no silent snooze
  await hold.getByLabel("Vì sao vẫn giữ").fill("Mức đặt sai, chờ kết quả quý");
  await hold.getByLabel("Ngày xem lại", { exact: true }).fill(inDays(30));
  await hold.getByRole("button", { name: "Giữ tiếp" }).click();
  await expect(below).toContainText("Giữ tiếp đến");
  await expect(below.getByRole("button", { name: "Giữ tiếp, có lý do" })).toHaveCount(0);

  await page.goto("/journal");
  await expect(page.getByText("Mức đặt sai, chờ kết quả quý", { exact: false })).toBeVisible();
});

test("the thesis section has no horizontal scroll at 375px", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 800 });
  await seedOwner(page);
  await page.goto("/portfolio");
  await expect(page.getByRole("region", { name: "Luận điểm đầu tư" })).toBeVisible();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  expect(overflow).toBeLessThanOrEqual(0);
});
