import { describe, expect, it } from "vitest";
import { whenText } from "./us-calendar";

describe("whenText", () => {
  it("gives the Vietnam day and time and how far away it is", () => {
    expect(whenText({ on: "2026-12-10", at: "02:00" }, "2026-11-16")).toBe("10/12 · 02:00 (còn 24 ngày)");
    expect(whenText({ on: "2026-11-19", at: "02:00" }, "2026-11-18")).toBe("19/11 · 02:00 (ngày mai)");
    expect(whenText({ on: "2026-11-19", at: "02:00" }, "2026-11-19")).toBe("19/11 · 02:00 (hôm nay)");
  });
});
