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


test("a question gets its answer and a gap, a catalyst is added and marked as happened", async ({ page }) => {
  await page.goto("/research/FPT");
  const box = page.getByRole("region", { name: "Kịch bản và chỉ báo luận điểm" });
  const card = box.getByRole("article", { name: "Câu 1: Doanh nghiệp kiếm tiền thế nào" });
  await card.getByRole("button", { name: "Sửa câu 1" }).click();
  await card.getByLabel("Trạng thái câu 1").selectOption("good");
  await card.getByLabel("Trả lời câu 1").fill("Dịch vụ CNTT xuất khẩu tăng đều");
  await card.getByRole("button", { name: "Lưu" }).click();
  await expect(card).toContainText("Dịch vụ CNTT xuất khẩu tăng đều");
  const gap = `Tách doanh thu theo thị trường ${Date.now()}`;  // unique: the store is shared and a retry runs again
  await card.getByLabel("Chỗ trống mới câu 1").fill(gap);
  await card.getByRole("button", { name: "Thêm chỗ trống" }).click();
  await expect(box.getByTestId("tq-gaps")).toContainText(/[1-9]\d*\/\d+ việc mở/);
  await card.getByLabel(`Xong: ${gap}`).click();  // saved, then shown ticked
  await expect(card.getByLabel(`Xong: ${gap}`)).toBeChecked();
  await box.getByLabel("Thời điểm mốc").fill("Q1/2027");
  const text = `Ký hợp đồng lớn ${Date.now()}`;
  await box.getByLabel("Nội dung mốc").fill(text);
  await box.getByRole("button", { name: "Thêm mốc" }).click();
  const row = box.getByRole("table", { name: "Mốc và chất xúc tác" }).getByRole("row", { name: new RegExp(text) });
  await row.getByRole("button", { name: "Đã xảy ra" }).click();
  await expect(row.getByRole("button", { name: "Mở lại" })).toBeVisible();
});


test("an own valuation range joins the bars, and the one-page thesis opens ready to print", async ({ page }) => {
  await page.goto("/research/FPT");
  const box = page.getByRole("region", { name: "Kịch bản và chỉ báo luận điểm" });
  await box.getByRole("button", { name: "Sửa tiêu đề và tóm tắt" }).click();
  await box.getByLabel("Tiêu đề luận điểm").fill("Xuất khẩu phần mềm tăng đều");
  await box.getByRole("button", { name: "Lưu", exact: true }).first().click();
  await expect(box).toContainText("Xuất khẩu phần mềm tăng đều");
  const name = `CTCK ${Date.now() % 100000}`;
  await box.getByLabel("Tên cách định giá").fill(name);
  await box.getByLabel("Giá thấp").fill("50000");
  await box.getByLabel("Giá cao").fill("70000");
  await box.getByRole("button", { name: "Thêm khoảng" }).click();
  await expect(box.getByRole("img", { name: /Dải định giá/ })).toContainText(name);
  await box.getByRole("link", { name: "Trang luận điểm 1 trang để in" }).click();
  await expect(page).toHaveURL(/\/thesis\/FPT/);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Xuất khẩu phần mềm tăng đều");
  await expect(page.getByRole("region", { name: "Dải định giá" })).toContainText(name);
  await page.emulateMedia({ media: "print" });
  await expect(page.getByRole("button", { name: "In" })).toBeHidden();
});


test("the one-page thesis is reachable from the top of a company's page", async ({ page }) => {
  await page.goto("/research/FPT");
  await page.getByRole("navigation", { name: "Luận điểm của mã" }).getByRole("link", { name: "Trang luận điểm 1 trang để in" }).click();
  await expect(page).toHaveURL(/\/thesis\/FPT/);
  await expect(page.getByRole("button", { name: "In" })).toBeVisible();
});
