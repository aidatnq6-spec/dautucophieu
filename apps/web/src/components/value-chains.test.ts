import { describe, expect, it } from "vitest";
import { missingLine, missingReason, move } from "./value-chains";

const reading = { direction: "flat" as const, change: "0", kind: "ratio" as const, from: "2026-08-01", date: "2026-09-01", value: "100", stale: true };

describe("what keeps a chain's factors unread", () => {
  it("says why for each reason", () => {
    expect(missingReason({ missing: { reason: "no_series", max_age_days: null }, reading: null })).toBe("chưa có nguồn số liệu");
    expect(missingReason({ missing: { reason: "stale", max_age_days: 75 }, reading })).toBe("số mới nhất 01/09/2026, quá 75 ngày");
    expect(missingReason({ missing: { reason: "one_point", max_age_days: 75 }, reading: { ...reading, direction: null, stale: false } }))
      .toBe("mới có một kỳ số liệu, chưa so được");
    expect(missingReason({ missing: { reason: "no_data", max_age_days: 75 }, reading: null })).toBe("chưa tải được số liệu");
    expect(missingReason({ missing: null, reading })).toBeNull();
  });
  it("lists the unread factors on the card, the heaviest first, and nothing when all are read", () => {
    const f = (label: string, weight: "major" | "minor" | "small", status: "unknown" | "good", missing: { reason: "no_series"; max_age_days: null } | null) =>
      ({ label, weight, status, missing, reading: null });
    expect(missingLine([f("Nhỏ", "small", "unknown", { reason: "no_series", max_age_days: null }), f("Đọc được", "major", "good", null),
      f("Chính", "major", "unknown", { reason: "no_series", max_age_days: null })]))
      .toBe("Thiếu: Chính (chưa có nguồn số liệu); Nhỏ (chưa có nguồn số liệu)");
    expect(missingLine([f("Đọc được", "major", "good", null)])).toBeNull();
  });
});

describe("a series read against the same days a year before", () => {
  it("says more or less water than a year before, over the week", () => {
    const r = { direction: "up" as const, change: "14.29", kind: "yoy" as const, from: "2026-11-14", date: "2026-11-20", value: "-5", stale: false };
    expect(move(r)).toBe("nhiều hơn cùng kỳ năm trước 14,3% (bình quân 7 ngày)");
    expect(move({ ...r, direction: "down", change: "-12.00" })).toBe("ít hơn cùng kỳ năm trước 12% (bình quân 7 ngày)");
    expect(move({ ...r, direction: "flat", change: "4.00" })).toBe("gần bằng cùng kỳ năm trước (+4%, bình quân 7 ngày)");
  });
});
