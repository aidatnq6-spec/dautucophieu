import { expect, it } from "vitest";
import { horizonText } from "./hindsight-view";

it("shows a horizon's change against VN-Index, or why there is none", () => {
  expect(horizonText({ status: "ok", on: "2025-05-01", change: "0.2000", index: "-0.0500", diff: "0.2500" })).toBe("+20,0% (VN-Index −5,0%)");
  expect(horizonText({ status: "ok", on: "2025-05-01", change: "-0.1000", index: null, diff: null })).toBe("−10,0% (VN-Index: thiếu số)");
  expect(horizonText({ status: "not_yet", on: "2026-12-01", change: null, index: null, diff: null })).toBe("chưa tới (01/12/2026)");
  expect(horizonText({ status: "missing", on: "2025-05-01", change: null, index: null, diff: null })).toBe("thiếu giá");
});
