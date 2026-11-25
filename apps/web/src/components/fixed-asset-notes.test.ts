import { expect, it } from "vitest";
import { bargainText, coverText, dealText, fxText, gapText, quarterInput, segmentCheckText, stateText, yearsLeftText } from "./fixed-asset-notes";

it("the segments written are checked against the stored net revenue and cost of sales", () => {
  expect(segmentCheckText({ period: "2021", revenue: "149680", cogs: "108571", reported_revenue: "149680", reported_cogs: "108571", revenue_gap: "0", cogs_gap: "0" }))
    .toBe("Tổng các mảng khớp doanh thu thuần và giá vốn của báo cáo 2021");
  expect(segmentCheckText({ period: "2021", revenue: "150865", cogs: "108571", reported_revenue: "149680", reported_cogs: "108571", revenue_gap: "1185", cogs_gap: "0" }))
    .toBe("Tổng các mảng lệch báo cáo 2021: doanh thu +1.185 tỷ (có thể chưa trừ các khoản giảm trừ), giá vốn 0 tỷ");
  expect(segmentCheckText({ period: "Q2/2026", revenue: "1", cogs: "1", reported_revenue: null, reported_cogs: null, revenue_gap: null, cogs_gap: null }))
    .toBe("Chưa có số của kỳ này trong báo cáo đã lưu để đối chiếu");
});

it("the loans written are checked against the borrowings on the balance sheet", () => {
  expect(coverText({ period: "2021", total: "20858", reported: "57212.5", covered: "0.3646" }))
    .toBe("Các khoản bạn ghi: 20.858 tỷ, bằng 36,5% vay ngắn hạn + dài hạn trên bảng cân đối 2021 (57.212,5 tỷ)");
  expect(coverText({ period: null, total: "503", reported: null, covered: null })).toBe("Các khoản bạn ghi: 503 tỷ; ghi kỳ báo cáo đã đọc để đối chiếu với bảng cân đối");
});

it("the exchange scenario is the owner's own fall of the dong, not a forecast", () => {
  expect(fxText({ foreign: "7357", fx_shock: "5", fx_loss: "367.85", fx_to_pbt: "0.0099" }))
    .toBe("Kịch bản (không phải dự báo): đồng Việt Nam mất giá 5% thì dư nợ ngoại tệ 7.357 tỷ tăng thêm khoảng 367,9 tỷ, bằng 1,0% LNTT kỳ đã đọc");
  expect(fxText({ foreign: "0", fx_shock: "5", fx_loss: "0", fx_to_pbt: null })).toBe("Không có dư nợ ngoại tệ trong các khoản bạn ghi");
  expect(fxText({ foreign: "7357", fx_shock: null, fx_loss: null, fx_to_pbt: null })).toBe("Ghi mức mất giá giả định để xem kịch bản tỷ giá");
});

it("the notes' goodwill sits beside the formula's, with the gap", () => {
  expect(gapText({ computed: "-1715.537", note_goodwill: "-1670", gap: "-45.537" })).toBe("Công thức: −1.715,5 tỷ; thuyết minh: −1.670 tỷ (lệch −45,5 tỷ, dùng số thuyết minh)");
  expect(gapText({ computed: "400", note_goodwill: null, gap: null })).toBe(null);
});

it("a bargain gain says it brought no cash and what profit is without it", () => {
  expect(bargainText({ year: "2021", gain: "1670", pbt: "5086.2", share: "0.3283", pbt_without: "3416.2" }))
    .toBe("Năm 2021: lãi mua rẻ 1.670 tỷ (không có tiền đi kèm), bằng 32,8% LNTT 5.086,2 tỷ; LNTT loại lãi mua rẻ 3.416,2 tỷ");
  expect(bargainText({ year: "2021", gain: "1670", pbt: null, share: null, pbt_without: null }))
    .toBe("Năm 2021: lãi mua rẻ 1.670 tỷ (không có tiền đi kèm); chưa có LNTT năm này trong báo cáo đã lưu");
});

it("a quarter is written back as the owner types it", () => {
  expect(quarterInput("2027-Q3")).toBe("Q3/2027");
});

it("each project says where it stands against the reports already stored", () => {
  expect(stateText({ state: "upcoming", due: "2027-Q3", done_on: null, postpones: [] })).toBe("Đang làm, dự kiến xong Q3/2027");
  expect(stateText({ state: "waiting_report", due: "2026-Q1", done_on: null, postpones: [{}, {}] })).toBe("Chờ báo cáo Q1/2026 · đã lùi 2 lần");
  expect(stateText({ state: "due", due: "2025-Q3", done_on: null, postpones: [] })).toBe("Đến hạn: xác nhận đã hoàn thành hoặc lùi hạn");
  expect(stateText({ state: "done", due: "2025-Q3", done_on: "2026-08-01", postpones: [{}] })).toBe("Đã hoàn thành (xác nhận 01/08/2026) · đã lùi 1 lần");
});

it("the years left say they hold only at that year's pace", () => {
  expect(yearsLeftText({ year: "2021", years_left: "7.5" })).toBe("≈ 7,5 năm nếu giữ nhịp phân bổ năm 2021");
  expect(yearsLeftText({ year: "2022", years_left: null })).toBe("—");
});

it("a deal says what its goodwill does to profit", () => {
  expect(dealText({ kind: "goodwill", goodwill: "400", per_year: "40", ends: "2034-03-15", gain_year: null }))
    .toBe("Lợi thế thương mại 400 tỷ, phân bổ 40 tỷ/năm vào chi phí đến 15/03/2034");
  expect(dealText({ kind: "goodwill", goodwill: "350.5", per_year: null, ends: null, gain_year: null }))
    .toBe("Lợi thế thương mại 350,5 tỷ; ghi số năm phân bổ để thấy mức trừ vào lợi nhuận mỗi năm");
  expect(dealText({ kind: "bargain", goodwill: "-104", per_year: null, ends: null, gain_year: "2025" }))
    .toBe("Lãi mua rẻ 104 tỷ: lợi nhuận một lần năm 2025, loại ra khi so lợi nhuận các năm");
  expect(dealText({ kind: "none", goodwill: "0", per_year: null, ends: null, gain_year: null })).toBe("Giá mua bằng phần tài sản thuần: không có lợi thế thương mại");
});
