import { describe, expect, it } from "vitest";
import { fromInput, pageNote } from "./bank-figures";

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
