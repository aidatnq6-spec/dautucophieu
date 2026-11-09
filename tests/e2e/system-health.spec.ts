import { expect, test } from "@playwright/test";
import { signIn } from "./helpers";

// The fixture has no scheduler log and no backups, so the page must say so rather than show all clear.
test.beforeEach(async ({ context }) => signIn(context));

test("Cài đặt says what the unattended work has not done", async ({ page }) => {
  await page.goto("/settings");
  const box = page.getByRole("region", { name: "Tình trạng hệ thống" });
  await expect(box.getByRole("list", { name: "Sự cố" })).toContainText("Lịch sau phiên");
  await expect(box.getByRole("list", { name: "Sự cố" })).toContainText("Diễn tập khôi phục");
  await expect(box).not.toContainText("Mọi thứ đang chạy bình thường");
  await expect(box.getByRole("table", { name: "Độ mới của dữ liệu" })).toContainText("Thuyết minh ngân hàng");
});
