import { expect, test } from "@playwright/test";
import { signIn } from "./helpers";

// The fixture backend has no OpenRouter key and no spend ledger; the approved policy is the repository's config/ai-policy.json.
test.beforeEach(async ({ context }) => signIn(context));

test("the AI section shows the real status, not a fixed sentence", async ({ page }) => {
  await page.goto("/settings");
  const ai = page.getByRole("region", { name: "AI", exact: true });  // a bare "AI" also matches any label containing "ai"
  await expect(ai).toContainText("Key OpenRouter: chưa cấu hình");
  await expect(ai).toContainText("Chính sách: đã duyệt");
  await expect(ai).toContainText("openai/gpt-6-luna");
  await expect(ai).toContainText("0,0000 / 2 USD");
  await expect(ai).toContainText("Chỉ dùng cho tab Nhận định");
  await expect(ai).toContainText("Không gửi danh mục");
  await expect(page.getByText("Chính sách AI mẫu chưa được duyệt")).toHaveCount(0);
});
