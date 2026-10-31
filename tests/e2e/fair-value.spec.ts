import { expect, test } from "@playwright/test";
import { signIn } from "./helpers";

// Synthetic fixture data only: FPT has statements (P/E 12 every year, cash dividends), VCB has none.
test.beforeEach(async ({ context }) => signIn(context));

async function openPage(page: import("@playwright/test").Page) {
  await page.goto("/fair-value");
  await expect(page.getByText("Đang tải…")).toHaveCount(0);
}

test("each watched ticker gets a fair-value range and a verdict, with the methods behind it", async ({ page }) => {
  await openPage(page);
  const table = page.getByRole("table", { name: "Định giá tham khảo" });
  const fpt = table.getByRole("row", { name: /FPT/ });
  await expect(fpt).toContainText("Đắt");
  await expect(table.getByRole("row", { name: /VCB/ })).toContainText("Chưa có báo cáo tài chính");
  await fpt.getByRole("button", { name: "Chi tiết FPT" }).click();
  const detail = page.getByRole("region", { name: "Phương án định giá FPT" });
  await expect(detail).toContainText("P/E lịch sử");
  await expect(detail).toContainText("12.000");
  await expect(detail).toContainText("Cần ít nhất 3 mã cùng ngành có số liệu");
  await expect(page.getByText(/không phải khuyến nghị/)).toBeVisible();
  await expect(page.getByText(/Lợi suất yêu cầu 13,0%/)).toBeVisible();
});

test("the detail of a ticker charts its monthly P/E and P/B against their own history", async ({ page }) => {
  await openPage(page);
  await page.getByRole("button", { name: "Chi tiết FPT" }).click();
  const pe = page.getByRole("figure", { name: "P/E lịch sử FPT" });
  await expect(pe).toBeVisible();
  await expect(pe).toContainText("Trung vị");
  await expect(pe).toContainText("Hiện tại");
  await expect(page.getByRole("figure", { name: "P/B lịch sử FPT" })).toBeVisible();
  await pe.getByText("Bảng số liệu").click();
  await expect(pe.getByRole("table")).toContainText("12/2025");
});

test("no horizontal scroll with the P/E chart open at 375px", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 900 });
  await openPage(page);
  await page.getByRole("button", { name: "Chi tiết FPT" }).click();
  await expect(page.getByRole("figure", { name: "P/E lịch sử FPT" })).toBeVisible();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(0);
});

test("no horizontal scroll on the valuation page at 375px", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 900 });
  await openPage(page);
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(0);
  const scrollers = await page.evaluate(() => [...document.querySelectorAll("main *")]
    .filter((el) => el.scrollWidth > el.clientWidth + 1 && ["auto", "scroll"].includes(getComputedStyle(el).overflowX)).length);
  expect(scrollers).toBe(0);
});

test("VNINDEX and VN30 are valued from their P/E and P/B against a five-year median", async ({ page }) => {
  await openPage(page);
  const table = page.getByRole("table", { name: "Định giá chỉ số" });
  const vn30 = table.getByRole("row", { name: /VN30/ });
  await expect(vn30).toContainText("1.800,00");
  await expect(vn30).toContainText("2.025,00");
  await expect(vn30).toContainText("−11,1%");
  await expect(vn30).toContainText("Hợp lý");
  await expect(vn30).toContainText("trung vị 5 năm 15,00");
  await expect(table.getByRole("row", { name: /VN-Index/ })).toContainText("Chưa có số liệu");
  await expect(page.getByText(/lợi nhuận bốn quý gần nhất/)).toBeVisible();
});

test("the detail of an index charts its monthly P/E and P/B over five years", async ({ page }) => {
  await openPage(page);
  await page.getByRole("button", { name: "Chi tiết VN30" }).click();
  const pe = page.getByRole("figure", { name: "P/E lịch sử VN30" });
  await expect(pe).toBeVisible();
  await expect(pe).toContainText("Hiện tại 12,0x");
  await expect(pe).toContainText("Trung vị 15,0x");
  await expect(page.getByRole("figure", { name: "P/B lịch sử VN30" })).toBeVisible();
  await expect(page.getByText(/như bảng phía trên/)).toBeVisible();
  await pe.getByText("Bảng số liệu").click();
  await expect(pe.getByRole("table")).not.toContainText("Năm tài chính");
});

test("each ticker shows its F-Score, a new-quarter mark, and the criteria and warning signs behind it", async ({ page }) => {
  await openPage(page);
  const table = page.getByRole("table", { name: "Định giá tham khảo" });
  const fpt = table.getByRole("row", { name: /FPT/ }).first();
  await expect(fpt).toContainText("9/9");
  await expect(fpt).toContainText("mạnh");
  await expect(fpt).toContainText("Quý mới");
  const vcb = table.getByRole("row", { name: /VCB/ });
  await expect(vcb).toContainText("3/3");  // a bank: health score from sector ratios
  await expect(vcb).toContainText("sức khỏe ngành");
  await fpt.getByRole("button", { name: "Chi tiết FPT" }).click();
  const q = page.getByRole("region", { name: "Chất lượng báo cáo FPT" });
  await expect(q).toContainText("F-Score năm 2025: 9/9 tiêu chí đánh giá được");
  await expect(q).toContainText("ROA 9,0% (lợi nhuận 9 tỷ / tài sản đầu kỳ 100 tỷ)");
  await expect(q).toContainText("Lãi nhưng dòng tiền kinh doanh âm");
  await expect(q).toContainText("không kết luận gian lận");
});

test("a bank is scored on sector ratios, latest quarter against the same quarter a year before", async ({ page }) => {
  await openPage(page);
  await page.getByRole("button", { name: "Chi tiết VCB" }).click();
  const q = page.getByRole("region", { name: "Chất lượng báo cáo VCB" });
  await expect(q).toContainText("Điểm sức khỏe ngân hàng Q3/2026 so với Q3/2025: 3/3 tiêu chí đánh giá được");
  await expect(q).toContainText("Nợ xấu 0,71% so với 1,03% cùng kỳ");
  await expect(q).toContainText("không xếp mạnh/yếu");
});
