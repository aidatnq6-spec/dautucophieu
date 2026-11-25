import { expect, it } from "vitest";
import { bargainText, dealText, gapText, quarterInput, stateText, yearsLeftText } from "./fixed-asset-notes";

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
