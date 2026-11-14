import { expect, test } from "@playwright/test";
import { signIn } from "./helpers";

test.beforeEach(async ({ context }) => signIn(context));

test("three scenarios give the weighted price, and an indicator is graded by the owner's levels", async ({ page }) => {
  await page.goto("/research/FPT");
  const box = page.getByRole("region", { name: "Kịch bản và chỉ báo luận điểm" });
  await box.getByRole("button", { name: /Nhập kịch bản|Sửa kịch bản/ }).click();
  for (const [name, price, prob] of [["Xấu", "50000", "25"], ["Cơ sở", "60000", "50"], ["Tốt", "70000", "25"]]) {
    await box.getByLabel(`Giá ${name}`).fill(price);
    await box.getByLabel(`Xác suất ${name}`).fill(prob);
  }
  await expect(box).toContainText("Giá kỳ vọng: 60.000 đ");
  await box.getByRole("button", { name: "Lưu kịch bản" }).click();
  await expect(box.getByTestId("tm-expected")).toHaveText("60.000 đ");
  await box.getByRole("button", { name: "Thêm chỉ báo" }).click();
  await box.getByLabel("Tên chỉ báo").fill("Sản lượng quý");
  await box.getByLabel("Mức Xấu").fill("100");
  await box.getByLabel("Mức Cơ sở").fill("120");
  await box.getByLabel("Mức Tốt").fill("140");
  await box.getByRole("button", { name: "Lưu chỉ báo" }).click();
  await box.getByLabel("Kỳ Sản lượng quý").fill("2026-Q3");
  await box.getByLabel("Số Sản lượng quý").fill("125");
  await box.getByRole("button", { name: "Ghi số" }).click();
  await expect(box.getByRole("table", { name: "Chỉ báo theo dõi" }).getByRole("row", { name: /Sản lượng quý/ })).toContainText("Tốt");
  await expect(box.getByTestId("tm-lights")).toContainText("1 tốt");
});
