import { expect, it } from "vitest";
import { kindLabel, statusLine } from "./weekly-channels";

it("names each channel as the chart does", () => {
  expect(kindLabel("basic", 3)).toBe("Kênh basic 0-2");
  expect(kindLabel("accel1", 3)).toBe("Kênh tăng tốc 1");
  expect(kindLabel("final", 3)).toBe("Kênh final");
  expect(kindLabel("final", 1)).toBe("Kênh basic 0-2 (cũng là final)");
});

it("the status line places the last finished week against the final channel", () => {
  const status = { state: "below" as const, since: "2026-06-01", close: "21", lower: "26.69", upper: "35.30" };
  expect(statusLine(status, "2026-11-02")).toBe("Tuần 02/11/2026 đóng cửa 21 — dưới cạnh dưới kênh final (26,69) từ tuần 01/06/2026");
  expect(statusLine({ ...status, state: "inside", close: "30" }, "2026-11-02")).toBe("Tuần 02/11/2026 đóng cửa 30 — trong kênh final (26,69 – 35,30) từ tuần 01/06/2026");
  expect(statusLine({ ...status, state: "above", close: "40" }, "2026-11-02")).toBe("Tuần 02/11/2026 đóng cửa 40 — trên cạnh trên kênh final (35,30) từ tuần 01/06/2026");
});
