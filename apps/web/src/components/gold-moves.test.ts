import { describe, expect, it } from "vitest";
import { passThroughText } from "./gold-moves";

const empty = { days: null, from: null, to: null, sjc_from: null, sjc_to: null, world_from: null, world_to: null, sjc_change: null, world_change: null };

describe("the 30-day pass-through line", () => {
  it("compares both moves over their dates", () => {
    expect(passThroughText({ ...empty, missing: null, since: "2026-12-14", ready_on: null, days: 32, from: "2026-12-14", to: "2027-01-15",
      sjc_change: "-0.0667", world_change: "-0.1000" }))
      .toBe("Từ 14/12/2026 đến 15/01/2027 (32 ngày): vàng miếng SJC −6,6%, giá thế giới quy ra đồng −10,0%.");
  });
  it("says when thirty days of both will be there", () => {
    expect(passThroughText({ ...empty, missing: "not_enough_history", since: "2026-11-16", ready_on: "2026-12-16" }))
      .toBe("Chưa đủ 30 ngày số liệu: giá SJC và giá thế giới cùng có từ 16/11/2026, nên có số từ khoảng 16/12/2026.");
  });
  it("says when there is no day with both", () => {
    expect(passThroughText({ ...empty, missing: "no_data", since: null, ready_on: null }))
      .toBe("Chưa có ngày nào có cả giá SJC và giá thế giới quy ra đồng.");
  });
});
