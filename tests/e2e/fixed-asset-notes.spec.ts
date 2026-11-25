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
