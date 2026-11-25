import { expect, test } from "@playwright/test";
import { signIn } from "./helpers";

test.beforeEach(async ({ context }) => signIn(context));

test("the owner notes a construction project from the statements and moves its quarter only by postponing", async ({ page }) => {
  await page.goto("/research/FPT");
  const box = page.getByRole("region", { name: "Thuyết minh TSCĐ (nhập tay)" });
  await box.getByRole("button", { name: "Thêm dự án" }).click();
  const form = box.getByRole("form", { name: "Dự án XDCB" });
  await form.getByLabel("Tên dự án").fill("Trung tâm dữ liệu mẫu");
  await form.getByLabel("Quý hoàn thành dự kiến").fill("Q4/2027");
  await form.getByRole("button", { name: "Lưu dự án" }).click();
  const row = box.getByTestId("fan-project");
  await expect(row).toContainText("Đang làm, dự kiến xong Q4/2027");
  const answers = ["Q2/2028", "chậm thiết bị"];  // the new quarter, then the reason
  page.on("dialog", (d) => d.accept(answers.shift()));
  await row.getByRole("button", { name: "Lùi hạn Trung tâm dữ liệu mẫu" }).click();
  await expect(row).toContainText("dự kiến xong Q2/2028 · đã lùi 1 lần");
  await expect(row).toContainText("Q4/2027 → Q2/2028 (chậm thiết bị)");
});

test("a bank's page has no fixed-asset notes", async ({ page }) => {
  await page.goto("/research/VCB");
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await expect(page.getByRole("region", { name: "Thuyết minh TSCĐ (nhập tay)" })).toHaveCount(0);
});

test("the owner writes a year's prepaid allocation from the notes", async ({ page }) => {
  await page.goto("/research/FPT");
  const box = page.getByRole("region", { name: "Thuyết minh TSCĐ (nhập tay)" });
  await box.getByRole("button", { name: "Thêm năm phân bổ" }).click();
  const form = box.getByRole("form", { name: "Phân bổ chi phí trả trước" });
  await form.getByLabel("Năm").fill("2021");
  await form.getByLabel("Công cụ dụng cụ (tỷ đồng)").fill("109");
  await form.getByLabel("Sửa chữa lớn (tỷ đồng)").fill("139");
  await form.getByRole("button", { name: "Lưu phân bổ" }).click();
  const row = box.getByTestId("fan-prepaid");
  await expect(row).toContainText("248");
  await expect(row).toContainText("cộng các loại đã nhập");
});

test("the owner writes a deal and sees its goodwill by the lesson's formula", async ({ page }) => {
  await page.goto("/research/FPT");
  const box = page.getByRole("region", { name: "Thuyết minh TSCĐ (nhập tay)" });
  await box.getByRole("button", { name: "Thêm thương vụ" }).click();
  const form = box.getByRole("form", { name: "Thương vụ mua bán" });
  await form.getByLabel("Công ty được mua", { exact: true }).fill("Công ty mẫu B");
  await form.getByLabel("Ngày mua").fill("15/03/2024");
  await form.getByLabel("Tỷ lệ mua (%)").fill("60");
  await form.getByLabel("Giá mua (tỷ đồng)").fill("1000");
  await form.getByLabel(/Giá trị hợp lý tài sản thuần/).fill("1000");
  await form.getByLabel("Số năm phân bổ (tối đa 10)").fill("10");
  await form.getByRole("button", { name: "Lưu thương vụ" }).click();
  await expect(box.getByTestId("fan-deal")).toContainText("Lợi thế thương mại 400 tỷ, phân bổ 40 tỷ/năm vào chi phí đến 15/03/2034");
  await expect(box.getByTestId("fan-charging")).toContainText("40 tỷ mỗi năm");
});

test("a bargain purchase with the notes' figure shows the gap and a profit line without cash", async ({ page }) => {
  await page.goto("/research/FPT");
  const box = page.getByRole("region", { name: "Thuyết minh TSCĐ (nhập tay)" });
  await box.getByRole("button", { name: "Thêm thương vụ" }).click();
  const form = box.getByRole("form", { name: "Thương vụ mua bán" });
  await form.getByLabel("Công ty được mua", { exact: true }).fill("Công ty mẫu mua rẻ");
  await form.getByLabel("Ngày mua").fill("30/06/2021");
  await form.getByLabel("Tỷ lệ mua (%)").fill("99,98");
  await form.getByLabel("Giá mua (tỷ đồng)").fill("5598");
  await form.getByLabel(/Giá trị hợp lý tài sản thuần/).fill("7315");
  await form.getByLabel(/Lợi thế thương mại theo thuyết minh/).fill("-1670");
  await form.getByRole("button", { name: "Lưu thương vụ" }).click();
  await expect(box.getByTestId("fan-deal").filter({ hasText: "Công ty mẫu mua rẻ" })).toContainText("lệch −45,5 tỷ, dùng số thuyết minh");
  await expect(box.getByTestId("fan-bargain")).toContainText("Năm 2021: lãi mua rẻ 1.670 tỷ (không có tiền đi kèm)");
});
