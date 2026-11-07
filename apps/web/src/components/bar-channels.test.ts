import { expect, it } from "vitest";
import { fmtT, kindLabel, statusLine } from "./bar-channels";

it("names each channel as the chart does", () => {
  expect(kindLabel("basic", 3)).toBe("Kênh basic 0-2");
  expect(kindLabel("accel1", 3)).toBe("Kênh tăng tốc 1");
  expect(kindLabel("final", 3)).toBe("Kênh final");
  expect(kindLabel("final", 1)).toBe("Kênh basic 0-2 (cũng là final)");
});

it("a bar's time reads as a date, or as a date and hour for hourly bars keyed in Hà Nội wall-clock seconds", () => {
  expect(fmtT("2026-11-02")).toBe("02/11/2026");
  expect(fmtT(Date.UTC(2026, 10, 6, 14) / 1000)).toBe("06/11/2026 14:00");
});

it("the status line places the last finished bar against the final channel", () => {
  const status = { state: "below" as const, since: "2026-06-01", close: "21", lower: "26.69", upper: "35.30" };
  expect(statusLine(status, "2026-11-02", "tuần")).toBe("Nến tuần 02/11/2026 đóng cửa 21 — dưới cạnh dưới kênh final (26,69) từ 01/06/2026");
  expect(statusLine({ ...status, state: "inside", close: "30" }, "2026-11-02", "ngày")).toBe("Nến ngày 02/11/2026 đóng cửa 30 — trong kênh final (26,69 – 35,30) từ 01/06/2026");
  expect(statusLine({ ...status, state: "above", close: "40", since: Date.UTC(2026, 10, 6, 9) / 1000 }, Date.UTC(2026, 10, 6, 14) / 1000, "1 giờ"))
    .toBe("Nến 1 giờ 06/11/2026 14:00 đóng cửa 40 — trên cạnh trên kênh final (35,30) từ 06/11/2026 09:00");
});
