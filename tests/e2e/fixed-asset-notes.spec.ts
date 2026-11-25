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

test("the automatic notes show borrowings and fixed-asset movements read from Vietcap", async ({ page }) => {
  await page.goto("/research/FPT");
  const auto = page.getByRole("region", { name: "Thuyết minh TSCĐ (nhập tay)" }).getByTestId("fan-auto");
  await expect(auto.getByRole("table", { name: "Vay theo loại FPT" })).toContainText("Vay dài hạn đến hạn trả");
  await expect(auto.getByRole("table", { name: "Vay theo loại FPT" })).toContainText("350");  // 300 + 50
  await expect(auto.getByRole("table", { name: "Biến động TSCĐ hữu hình FPT" })).toContainText("120");
  await expect(auto.getByRole("table", { name: "Chi phí sản xuất, kinh doanh theo yếu tố FPT" })).toContainText("Nhân công");
  await expect(auto).toContainText("nhân công 25,0% tổng chi phí theo yếu tố");  // 100 of 400
});

test("the owner writes shares that may be issued", async ({ page }) => {
  await page.goto("/research/FPT");
  const box = page.getByRole("region", { name: "Thuyết minh TSCĐ (nhập tay)" });
  await box.getByRole("button", { name: "Ghi số cổ phiếu có thể phát hành thêm" }).click();
  const form = box.getByRole("form", { name: "Pha loãng cổ phiếu" });
  await form.getByLabel("Nguồn 1").fill("ESOP mẫu");
  await form.getByLabel("Số cổ phiếu").fill("5.000.000");
  await form.getByRole("button", { name: "Lưu" }).click();
  await expect(box.getByTestId("fan-dilution")).toContainText("ESOP mẫu: 5.000.000 cổ phiếu");
  await expect(box.getByTestId("fan-dilution-eps")).toBeVisible();
});

test("the owner writes a tax incentive and sees until when it runs", async ({ page }) => {
  await page.goto("/research/FPT");
  const box = page.getByRole("region", { name: "Thuyết minh TSCĐ (nhập tay)" });
  await box.getByRole("button", { name: "Thêm ưu đãi thuế" }).click();
  const form = box.getByRole("form", { name: "Ưu đãi thuế" });
  await form.getByLabel("Công ty con hoặc dự án").fill("Dự án mẫu");
  await form.getByLabel("Thuế suất ưu đãi (%)").fill("10");
  await form.getByLabel("Năm hết ưu đãi").fill("2099");
  await form.getByRole("button", { name: "Lưu ưu đãi" }).click();
  await expect(box.getByTestId("fan-incentive")).toContainText("thuế suất ưu đãi 10%");
  await expect(box.getByTestId("fan-incentive")).toContainText("Còn đến hết năm 2099");
});

test("the owner writes financial income by kind and sees the part hard to repeat", async ({ page }) => {
  await page.goto("/research/FPT");
  const box = page.getByRole("region", { name: "Thuyết minh TSCĐ (nhập tay)" });
  await box.getByRole("button", { name: "Thêm năm doanh thu tài chính" }).click();
  const form = box.getByRole("form", { name: "Doanh thu tài chính theo loại" });
  await form.getByLabel("Năm", { exact: true }).fill("2021");
  await form.getByLabel("Lãi cho vay (tỷ đồng)").fill("490,8");
  await form.getByLabel("trong đó: cho bên liên quan vay (tỷ đồng)").fill("469");
  await form.getByLabel("Lãi thanh lý, chuyển nhượng đầu tư (tỷ đồng)").fill("240");
  await form.getByRole("button", { name: "Lưu doanh thu tài chính" }).click();
  await expect(box.getByTestId("fan-fin")).toContainText("730,8");  // 490,8 + 240; related parties are part of lending
  await expect(box.getByTestId("fan-fin-summary")).toContainText("Năm 2021");
});

test("the owner writes a year's segments and sees each one's share of gross profit", async ({ page }) => {
  await page.goto("/research/FPT");
  const box = page.getByRole("region", { name: "Thuyết minh TSCĐ (nhập tay)" });
  await box.getByRole("button", { name: "Thêm kỳ theo mảng" }).click();
  const form = box.getByRole("form", { name: "Doanh thu theo mảng" });
  await form.getByLabel("Kỳ báo cáo").fill("2021");
  await form.getByLabel("Mảng 1").fill("Mảng mẫu A");
  await form.getByLabel("Doanh thu (tỷ)").fill("100");
  await form.getByLabel("Giá vốn (tỷ)").fill("70");
  await form.getByRole("button", { name: "Thêm mảng" }).click();
  await form.getByLabel("Mảng 2").fill("Mảng mẫu B");
  await form.getByLabel("Doanh thu (tỷ)").nth(1).fill("50");
  await form.getByLabel("Giá vốn (tỷ)").nth(1).fill("40");
  await form.getByRole("button", { name: "Lưu các mảng" }).click();
  const table = box.getByTestId("fan-segments");
  await expect(table).toContainText("Mảng mẫu A");
  await expect(table).toContainText("75,0%");  // A: 30 of the 40 gross profit
  await expect(table).toContainText("25,0%");
});

test("the owner writes a foreign-currency loan and sees the exchange scenario", async ({ page }) => {
  await page.goto("/research/FPT");
  const box = page.getByRole("region", { name: "Thuyết minh TSCĐ (nhập tay)" });
  await box.getByRole("button", { name: "Thêm khoản vay" }).click();
  const form = box.getByRole("form", { name: "Khoản vay" });
  await form.getByLabel("Bên cho vay").fill("Ngân hàng mẫu");
  await form.getByLabel("Loại tiền").selectOption("USD");
  await form.getByLabel("Kỳ hạn").selectOption("long");
  await form.getByLabel(/Dư nợ/).fill("1000");
  await form.getByLabel("Năm đáo hạn").fill("2027");
  await form.getByRole("button", { name: "Lưu khoản vay" }).click();
  await expect(box.getByTestId("fan-loan")).toContainText("Ngân hàng mẫu");
  await box.getByRole("button", { name: "Kỳ đã đọc, nợ đến hạn, kịch bản tỷ giá" }).click();
  await box.getByRole("form", { name: "Ghi chú nợ vay" }).getByLabel(/mất giá/).fill("5");
  await box.getByRole("form", { name: "Ghi chú nợ vay" }).getByRole("button", { name: "Lưu" }).click();
  await expect(box.getByTestId("fan-debt")).toContainText("mất giá 5% thì dư nợ ngoại tệ 1.000 tỷ tăng thêm khoảng 50 tỷ");
  await expect(box.getByTestId("fan-debt")).toContainText("2027 1.000 tỷ");
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
