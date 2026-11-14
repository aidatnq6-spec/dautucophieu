import { describe, expect, it } from "vitest";
import { weighted } from "./thesis-model";

describe("weighted", () => {
  it("weighs three scenarios by their probabilities, as typed", () => {
    expect(weighted([{ price: "44.106", prob: "25" }, { price: "58136", prob: "50" }, { price: "61362", prob: "25" }])).toBe(55435);
  });
  it("waits for all three and probabilities adding to 100", () => {
    expect(weighted([{ price: "1", prob: "30" }, { price: "1", prob: "50" }, { price: "1", prob: "25" }])).toBeNull();
    expect(weighted([{ price: "", prob: "25" }, { price: "1", prob: "50" }, { price: "1", prob: "25" }])).toBeNull();
  });
});
