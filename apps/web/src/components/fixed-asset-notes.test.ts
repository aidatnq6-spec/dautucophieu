import { expect, it } from "vitest";
import { autoTable, mergeDraft, bargainText, coverText, dealText, dilutionText, finText, fxText, gapText, incentiveState, interestText, quarterInput, segmentCheckText, stateText, yearsLeftText } from "./fixed-asset-notes";

it("an AI draft merges only the picked lines into the parts of the notes, keeping what was there", () => {
  const draft = {
    projects: [{ name: "Dung Quất 2", cip_value: "8289.3", due: "Q4/2024", due_text: "quý 4 năm 2024", page: 2 }, { name: "B", cip_value: "1", due: "", due_text: "", page: 2 }],
    ranges: { buildings: { from: 5, to: 50, page: 3 } }, prepaid: { tools: { amount: "109", page: 4 } },
    deals: [{ name: "Greenland", date: "29/03/2021", share: "69.87", price: "2859.9", net_assets: "3896.1", note_goodwill: "103", page: 5 }],
    capitalised_interest: { amount: "412", page: 4 }, incentives: [{ entity: "Thép DQ", kind: "rate", rate: "10", until: "2026", page: 6 }] };
  const picked = new Set(["projects:0", "ranges:buildings", "prepaid:tools", "deals:0", "capitalised_interest", "incentives:0"]);
  const merged = mergeDraft(draft, picked, "2021", { projects: [{ name: "cũ", due: "Q1/2030" }], prepaid: { "2020": { total: "1" } }, deals: [], incentives: [],
    fin: { "2021": { deposit: "5" } } });
  expect(merged.projects).toEqual([{ name: "cũ", due: "Q1/2030" }, { name: "Dung Quất 2", due: "Q4/2024", read_period: "2021", cip_value: "8289.3", budget: null,
    source_url: null, note: "AI soạn nháp từ BCTC 2021, trang 2 (quý 4 năm 2024)" }]);
  expect(merged.ranges).toEqual({ buildings: { from: 5, to: 50 }, period: "2021" });
  expect(merged.prepaid).toEqual({ "2020": { total: "1" }, "2021": { tools: "109" } });
  expect(merged.deals).toEqual([{ name: "Greenland", date: "29/03/2021", share: "69.87", price: "2859.9", net_assets: "3896.1", years: "", note_goodwill: "103",
    nci_part: "", source_url: null, note: "AI soạn nháp từ BCTC 2021, trang 5" }]);
  expect(merged.fin_income_notes).toEqual({ "2021": { deposit: "5", capitalised_interest: "412" } });
  expect(merged.tax_incentives).toEqual([{ entity: "Thép DQ", kind: "rate", rate: "10", until: "2026", source_url: null, note: "AI soạn nháp từ BCTC 2021, trang 6" }]);
  expect(mergeDraft(draft, new Set(), "2021", { projects: [], prepaid: {}, deals: [], incentives: [], fin: {} }).ranges).toBe(undefined);  // nothing picked: kept
});

it("the automatic notes become a table with the lines as rows and the years as columns, empty lines left out", () => {
  const year = (y: string, loans: Record<string, string>) => ({ year: y, loans, loans_total: null, manual_current_portion: null, fin_income: {}, fin_expense: {},
    hard_to_repeat: "0", pbt: null, share: null, ppe: {}, costs: {}, inventory: {},
    labour_share: null, materials_share: null });
  const auto = { fetched_at: "2026-11-25T13:00:00+00:00", source: "vietcap:iq", years: [year("2021", { lt_due: "6200.6", bonds: "0" }), year("2020", { lt_due: "5000" })] };
  expect(autoTable(auto, "loans", ["st_loans_contract", "lt_due", "bonds"], { lt_due: "Vay dài hạn đến hạn trả", bonds: "Trái phiếu phát hành" })).toEqual({
    years: ["2021", "2020"], rows: [{ key: "lt_due", label: "Vay dài hạn đến hạn trả", values: ["6200.6", "5000"] }, { key: "bonds", label: "Trái phiếu phát hành", values: ["0", null] }] });
});

it("shares that may be issued give EPS before and after dilution", () => {
  expect(dilutionText({ quarter: "2026-Q1", shares: "100000000", extra: "20000000", share: "0.2000", npat_ttm: "100", eps: "1000", eps_diluted: "833" }))
    .toBe("LNST công ty mẹ 4 quý đến Q1/2026: 100 tỷ; 100.000.000 cổ phiếu: EPS 1.000 đ. Thêm 20.000.000 cổ phiếu (20,0%): EPS 833 đ");
  expect(dilutionText({ quarter: null, shares: null, extra: "1", share: null, npat_ttm: null, eps: null, eps_diluted: null }))
    .toBe("Chưa có LNST 4 quý và số cổ phiếu trong báo cáo đã lưu");
});

it("a tax incentive says whether it is still running", () => {
  expect(incentiveState({ state: "ending", until: "2026" })).toBe("Hết trong năm 2026: thuế suất thực tế có thể tăng từ năm sau");
  expect(incentiveState({ state: "active", until: "2030" })).toBe("Còn đến hết năm 2030");
  expect(incentiveState({ state: "ended", until: "2024" })).toBe("Đã hết từ năm 2025");
});

it("financial income hard to repeat is set against profit before tax", () => {
  expect(finText({ year: "2021", hard_to_repeat: "709", pbt: "-130.6", share: null, pbt_without: "-839.6" }))
    .toBe("Năm 2021: phần khó lặp lại hoặc chưa thu tiền 709 tỷ; doanh nghiệp lỗ trước thuế −130,6 tỷ, loại phần này thì lỗ −839,6 tỷ");
  expect(finText({ year: "2021", hard_to_repeat: "46", pbt: "37057", share: "0.0012", pbt_without: "37011" }))
    .toBe("Năm 2021: phần khó lặp lại hoặc chưa thu tiền 46 tỷ, bằng 0,1% LNTT 37.057 tỷ; LNTT loại phần này 37.011 tỷ");
  expect(finText({ year: "2021", hard_to_repeat: "0", pbt: null, share: null, pbt_without: null })).toBe("Năm 2021: chưa có LNTT năm này trong báo cáo đã lưu");
});

it("the interest really borne adds what was capitalised", () => {
  expect(interestText({ interest_expensed: "971.9", interest_total: "1021.9", capitalised_share: null }))
    .toBe("Lãi vay thực tế 1.021,9 tỷ = 971,9 tỷ ghi vào chi phí + phần vốn hóa; phần vốn hóa sẽ vào chi phí khi dự án hoàn thành");
  expect(interestText({ interest_expensed: "971.9", interest_total: null, capitalised_share: null })).toBe(null);
});

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
