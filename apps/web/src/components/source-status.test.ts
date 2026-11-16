import { describe, expect, it } from "vitest";
import { bySource } from "./source-status";

describe("bySource", () => {
  it("gathers failing items under their source with the longest run and earliest start", () => {
    const f = (key: string, source: string, label: string, fails: number, since: string) => ({ key, source, label, fails, since, error: "ConnectError", alerted: false });
    expect(bySource([f("a", "Cục Thống kê", "Bán lẻ", 3, "2026-11-16T00:36:00+00:00"), f("b", "Cục Thống kê", "FDI", 2, "2026-11-16T01:00:00+00:00"),
      f("c", "FRED", "SOFR", 1, "2026-11-16T02:00:00+00:00")]))
      .toEqual([{ source: "Cục Thống kê", labels: ["Bán lẻ", "FDI"], fails: 3, since: "2026-11-16T00:36:00+00:00", error: "ConnectError" },
        { source: "FRED", labels: ["SOFR"], fails: 1, since: "2026-11-16T02:00:00+00:00", error: "ConnectError" }]);
  });
});
