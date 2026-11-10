import { describe, expect, it } from "vitest";
import { updatedLabel } from "./macro-view";

describe("updatedLabel", () => {
  it("writes the day as dd/mm/yyyy and how long ago it was", () => {
    expect(updatedLabel("2026-11-10", "2026-11-10")).toEqual({ day: "10/11/2026", ago: "hôm nay" });
    expect(updatedLabel("2026-11-09", "2026-11-10")).toEqual({ day: "09/11/2026", ago: "hôm qua" });
    expect(updatedLabel("2026-11-03", "2026-11-10")).toEqual({ day: "03/11/2026", ago: "7 ngày trước" });
    expect(updatedLabel("2026-08-31", "2026-11-10")).toEqual({ day: "31/08/2026", ago: "71 ngày trước" });
  });
  it("says nothing when there is no figure", () => {
    expect(updatedLabel(null, "2026-11-10")).toBeNull();
  });
});
