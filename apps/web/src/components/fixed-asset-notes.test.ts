import { expect, it } from "vitest";
import { quarterInput, stateText, yearsLeftText } from "./fixed-asset-notes";

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
