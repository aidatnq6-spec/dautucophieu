import { describe, expect, it } from "vitest";
import { fromInput } from "./bank-figures";

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
