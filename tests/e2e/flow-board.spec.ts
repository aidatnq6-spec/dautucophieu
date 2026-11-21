import { expect, test } from "@playwright/test";
import { seedOwner, signIn } from "./helpers";

// Dòng tiền & kỹ thuật on Theo dõi and Hiệu suất theo kỳ on Chuỗi giá trị, on the fixture's stored closes.
test.beforeEach(async ({ context }) => signIn(context));

test("Theo dõi shows the flow board with its quick filters, held tickers marked", async ({ page }) => {
  await seedOwner(page);
  await page.goto("/watchlist");
  const box = page.getByRole("region", { name: "Dòng tiền và kỹ thuật" });
  await expect(box.getByRole("group", { name: "Lọc nhanh" })).toContainText("Vượt đỉnh 52 tuần");
  await expect(box.getByTestId("flow-FPT")).toContainText("đang nắm");
  await expect(box).toContainText("không phải khuyến nghị");
});

test("Chuỗi giá trị shows each chain's change over the periods", async ({ page }) => {
  await page.goto("/value-chains");
  const box = page.getByRole("region", { name: "Hiệu suất theo kỳ" });
  const table = box.getByRole("table", { name: "Hiệu suất chuỗi theo kỳ" });
  for (const head of ["1 tuần", "1 tháng", "3 tháng", "1 năm", "Từ đầu năm"]) await expect(table.getByRole("columnheader", { name: head, exact: true })).toBeVisible();
  await expect(table.getByRole("row").nth(1)).toContainText("mã");
});
