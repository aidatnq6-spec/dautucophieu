import { expect, it } from "vitest";
import { coverageNote, headline } from "./price-milestones";

const base = { symbol: "HPG", reason: null, threshold: "0.1500", date: "2026-11-06", close: "21200", peak: { date: "2025-09-12", price: "26780" },
  drawdown: "-0.2084", trend: "down" as const, corrections: [{ peak: "2025-09-12", trough: "2025-04-11", depth: "-0.25" }], floor: null, rows: [],
  weeks: 900, from: "2007-11-16", since: "2019-04-05", omitted_troughs: 12 };

it("the headline gives today's close, the fall from the peak and when the peak was", () => {
  expect(headline(base)).toBe("HPG · giá 21.200, −20,8% từ đỉnh 26.780 (09/2025)");
  expect(headline({ ...base, close: "26780", drawdown: "0.0000" })).toBe("HPG · giá 26.780, đang ở đỉnh 26.780 (09/2025)");
});

it("the note says from when turning points are listed and how many older troughs are left out", () => {
  expect(coverageNote(base)).toBe("Liệt kê từ 04/2019 (tuần đầu có P/B); 12 đáy cũ hơn thấp hơn giá hôm nay không liệt kê vì P/B, P/E theo số liệu hôm nay không còn ý nghĩa. 1 đợt chỉnh đã hoàn tất trong khoảng này.");
  expect(coverageNote({ ...base, since: null, omitted_troughs: 0, corrections: [] })).toBe("Chưa có chuỗi P/B: liệt kê trên toàn bộ lịch sử giá. 0 đợt chỉnh đã hoàn tất trong khoảng này.");
});
