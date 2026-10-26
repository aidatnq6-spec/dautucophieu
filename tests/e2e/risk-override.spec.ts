import { expect, test } from "@playwright/test";
import { seedOwner, signIn } from "./helpers";

// seedOwner answers "C" to every question: 39 điểm, Cân bằng.
test.describe.configure({ mode: "serial" });
test.beforeEach(async ({ context }) => signIn(context));

test("a risk group chosen by hand shows its score range and equity share, and can be undone", async ({ page }) => {
  await seedOwner(page);
  await page.goto("/profile");
  const risk = page.getByRole("region", { name: "Khảo sát rủi ro" });
  await risk.getByLabel("Chọn nhóm thủ công").selectOption("strong_growth");
  await risk.getByRole("button", { name: "Áp dụng" }).click();
  await expect(risk.getByTestId("risk-effective")).toHaveText("Tăng trưởng mạnh · 47–52 điểm · cổ phiếu 60%");
  await expect(risk.getByText("Tự chọn", { exact: true })).toBeVisible();
  await expect(risk).toContainText("Kết quả khảo sát: Cân bằng · 39 điểm");

  await risk.getByRole("button", { name: "Dùng lại kết quả khảo sát" }).click();
  await expect(risk.getByTestId("risk-effective")).toHaveText("Cân bằng · 39 điểm · cổ phiếu 35%");
  await expect(risk.getByText("Tự chọn", { exact: true })).toBeHidden();
});
