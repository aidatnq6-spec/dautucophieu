import { describe, expect, it } from "vitest";
import { positionWord } from "./chain-valuation";

describe("Định giá chuỗi so với 5 năm", () => {
  it("names the cheapest and the dearest fifth of the five years", () => {
    expect(positionWord("0.09")).toEqual({ text: "9% · rẻ", tone: "good" });
    expect(positionWord("0.5")).toEqual({ text: "50%", tone: "" });
    expect(positionWord("0.85")).toEqual({ text: "85% · đắt", tone: "bad" });
    expect(positionWord(null)).toEqual({ text: "—", tone: "" });
  });
});
