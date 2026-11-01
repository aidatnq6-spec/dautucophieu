import { expect, it } from "vitest";
import { groupCount, horizonText } from "./hindsight-view";

it("shows a horizon's change against VN-Index, or why there is none", () => {
  expect(horizonText({ status: "ok", on: "2025-05-01", change: "0.2000", index: "-0.0500", diff: "0.2500", reason: null })).toBe("+20,0% (VN-Index −5,0%)");
  expect(horizonText({ status: "ok", on: "2025-05-01", change: "-0.1000", index: null, diff: null, reason: null })).toBe("−10,0% (VN-Index: thiếu số)");
  expect(horizonText({ status: "not_yet", on: "2026-12-01", change: null, index: null, diff: null, reason: null })).toBe("chưa tới (01/12/2026)");
  expect(horizonText({ status: "missing", on: "2025-05-01", change: null, index: null, diff: null, reason: "Giá đã lưu chỉ tới 11/03/2025" }))
    .toBe("thiếu giá: Giá đã lưu chỉ tới 11/03/2025");
});

it("counts every decision and says how many have six months behind them", () => {
  expect(groupCount({ count: 8, matured: 0 })).toBe("8 lần, 0 đủ 6 tháng");
  expect(groupCount({ count: 6, matured: 6 })).toBe("6 lần");
});
