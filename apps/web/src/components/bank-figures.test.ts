import { describe, expect, it } from "vitest";
import { fromInput, pageNote, quarterToEnter } from "./bank-figures";

describe("fromInput", () => {
  it("reads Vietnamese, thousands-only and decimal-point numbers without scaling them", () => {
    expect(fromInput("537.304,578")).toBe("537304.578");
    expect(fromInput("537304,578")).toBe("537304.578");
    expect(fromInput("447.734")).toBe("447734");
    expect(fromInput("537304.578")).toBe("537304.578");
    expect(fromInput("11,5")).toBe("11.5");
    expect(fromInput(" 7 808 ")).toBe("7808");
  });
});

describe("pageNote", () => {
  it("names the page and file a value came from, and says when it was read from a scanned image", () => {
    expect(pageNote(31, "mbb.pdf", false)).toBe("trang 31 trong mbb.pdf");
    expect(pageNote(31, "mbb.pdf", true)).toBe("trang 31 trong mbb.pdf · đọc từ ảnh (OCR), so lại từng chữ số");
  });
});

describe("quarterToEnter", () => {
  it("suggests the last quarter that has ended, or the one before it once that is saved", () => {
    expect(quarterToEnter(new Date(2026, 10, 10), [])).toBe("2026-Q3");
    expect(quarterToEnter(new Date(2026, 10, 10), ["2026-Q3"])).toBe("2026-Q2");
    expect(quarterToEnter(new Date(2026, 10, 10), ["2026-Q3", "2026-Q2"])).toBe("2026-Q1");
    expect(quarterToEnter(new Date(2027, 1, 3), [])).toBe("2026-Q4");
    expect(quarterToEnter(new Date(2026, 3, 1), ["2026-Q1", "2025-Q4", "2025-Q3", "2025-Q2", "2025-Q1", "2024-Q4", "2024-Q3", "2024-Q2"])).toBe("2026-Q1");
  });
});
