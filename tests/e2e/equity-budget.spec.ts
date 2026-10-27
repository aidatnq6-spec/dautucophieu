import { expect, test, type Locator } from "@playwright/test";
import { seedOwner, signIn } from "./helpers";

// seedOwner: risk answers "C" (Cân bằng, 35%), FPT bought at 50.000; stocks and the ledger's cash come from the ledger.
test.describe.configure({ mode: "serial" });
test.beforeEach(async ({ context }) => signIn(context));

const group = (n: bigint) => n.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ".");
const amount = async (box: Locator, id: string) => BigInt((await box.getByTestId(id).innerText()).replace(/\D/g, "") || "0");

async function fill(box: Locator, label: string, digits: string) {
  const input = box.getByLabel(label);
  await input.fill("");
  if (digits) await input.pressSequentially(digits);
}

async function enterLayers(box: Locator, { deposit = "0", bond = "0", gold = "0", crypto = "0", reserve = "" } = {}) {
  await fill(box, "Tiền gửi (đ)", deposit);
  await fill(box, "Trái phiếu (đ)", bond);
  await fill(box, "Vàng (đ)", gold);
  await fill(box, "Tiền số (đ)", crypto);
  await fill(box, "Quỹ dự phòng và khoản chi 12 tháng (đ)", reserve);
  await box.getByRole("button", { name: "Tính tháp tài sản" }).click();
}

test("layers add up to the total, build the pyramid and give the money for stocks", async ({ page }) => {
  await seedOwner(page);
  await page.goto("/portfolio");
  await expect(page.getByText("Chưa nhập tổng tài sản tài chính")).toBeVisible();
  await page.goto("/profile");
  const box = page.getByRole("region", { name: "Tháp tài sản" });
  await enterLayers(box, { deposit: "300000000", gold: "100000000" });
  await expect(box.getByLabel("Tiền gửi (đ)")).toHaveValue("300.000.000");
  const pyramid = box.getByRole("list", { name: "Các lớp tài sản, từ dưới lên" });
  for (const label of ["Dự phòng", "Tiền mặt", "Tiền gửi", "Trái phiếu", "Vàng", "Cổ phiếu", "Tiền số"]) await expect(pyramid).toContainText(label);
  await expect(pyramid.getByTestId("layer-cash")).toContainText("tính chung mục tiêu với tiền gửi");
  await expect(pyramid.getByTestId("layer-deposit")).not.toContainText("tiền mặt trong tài khoản");
  await expect(pyramid.getByTestId("layer-deposit")).toContainText("300.000.000 đ");
  await expect(pyramid.getByTestId("layer-gold")).toContainText("mục tiêu 10–15%");
  await expect(box).toContainText("Cân bằng");
  // Other specs may confirm a profile with a reserve or add FPT buys: expect (shown total − shown deduction) × 35%.
  const budget = (await amount(box, "equity-total") - await amount(box, "equity-deductions")) * BigInt(35) / BigInt(100);
  await expect(box.getByTestId("equity-budget")).toHaveText(`${group(budget)} đ`);

  await page.goto("/portfolio");
  await expect(page.getByText(`Tỷ trọng trên vốn dành cho cổ phiếu (${group(budget)} đ)`, { exact: false })).toBeVisible();
  await expect(page.getByText("Chưa nhập tổng tài sản tài chính")).toBeHidden();
});

test("a lower layer short while a higher one is over says to build from the bottom", async ({ page }) => {
  await seedOwner(page);
  await page.goto("/profile");
  const box = page.getByRole("region", { name: "Tháp tài sản" });
  await enterLayers(box, { deposit: "0", gold: "0", crypto: "100000000" });  // crypto far above 5%, gold below 10%
  await expect(box.getByTestId("layer-gold")).toContainText("thiếu");
  await expect(box.getByTestId("layer-crypto")).toContainText("vượt");
  await expect(box.locator(".notice").filter({ hasText: /^Vàng đang thiếu/ })).toContainText(/Vàng đang thiếu .* Tiền số đã\s+vượt mục tiêu/);
});

test("the reserve can be entered by hand, and cleared to use the profile again", async ({ page }) => {
  await seedOwner(page);
  await page.goto("/profile");
  const box = page.getByRole("region", { name: "Tháp tài sản" });
  await enterLayers(box, { deposit: "100000000000", reserve: "500000000" });
  await expect(box.getByLabel("Quỹ dự phòng và khoản chi 12 tháng (đ)")).toHaveValue("500.000.000");
  await expect(box.getByTestId("equity-deductions")).toHaveText("−500.000.000 đ");
  await expect(box).toContainText("(nhập tay)");
  await enterLayers(box, { deposit: "100000000000" });
  await expect(box).toContainText("(theo hồ sơ)");
  await expect(box).not.toContainText("(nhập tay)");
});

test("no horizontal scroll on the profile page at 375px", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 900 });
  await page.goto("/profile");
  await expect(page.getByRole("region", { name: "Tháp tài sản" })).toBeVisible();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(0);
});
