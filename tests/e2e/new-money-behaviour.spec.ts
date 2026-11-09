import path from "node:path";
import { expect, test } from "@playwright/test";
import { call, seedOwner, signIn } from "./helpers";

test.beforeEach(async ({ context }) => signIn(context));

test("new money is placed from the bottom of the tower, every đồng of it", async ({ page }) => {
  await seedOwner(page);
  const now = await (await call(page, "GET", "equity-budget")).json();
  if (now.budget.status === "no_total") {
    await call(page, "PUT", "equity-budget", { layers: { deposit: "300000000", bond: "0", gold: "100000000", crypto: "0" }, reserve: "100000000", expected_version: now.version, request_id: `nm-${Date.now()}` });
  }
  await page.goto("/profile");
  const box = page.getByRole("region", { name: "Tiền mới tháng này đi đâu" });
  await box.getByLabel("Số tiền mới (đ)").fill("100000000");
  await expect(box.getByLabel("Số tiền mới (đ)")).toHaveValue("100.000.000");
  await box.getByRole("button", { name: "Chia theo Tháp tài sản" }).click();
  await expect(box.getByTestId("nm-total")).toHaveText("100.000.000 đ");
});

test("the behaviour of a TCBS file is shown and nothing is saved", async ({ page }) => {
  await seedOwner(page);
  await page.goto("/portfolio");
  const before = await (await call(page, "GET", "ledger")).json();
  const box = page.getByRole("group", { name: "Soi hành vi giao dịch" });
  await box.locator("summary").click();
  await box.getByLabel("Chọn các file sao kê TCBS").setInputFiles(path.join(__dirname, "fixtures", "tcbs-mau.xlsx"));
  await expect(box.getByRole("table", { name: "Hành vi giao dịch theo năm" })).toBeVisible();
  expect((await (await call(page, "GET", "ledger")).json()).version).toBe(before.version);
});
