import { describe, expect, it } from "vitest";
import { cell } from "./receivable-signs";

describe("cell", () => {
  it("marks a sign on, off, or not read", () => {
    expect(cell(true)).toEqual({ text: "●", label: "có dấu hiệu" });
    expect(cell(false)).toEqual({ text: "", label: "không" });
    expect(cell(null)).toEqual({ text: "–", label: "chưa đủ số" });
  });
});
