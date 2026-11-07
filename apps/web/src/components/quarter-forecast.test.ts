import { expect, it } from "vitest";
import { fromForm, toForm } from "./quarter-forecast";

it("percent fields are sent as decimals, amounts in tỷ as typed, blanks left out", () => {
  expect(fromForm({ revenue_yoy: "55", gross_margin: "18,5", fin_income: "900", tax_rate: "", interest: " " }))
    .toEqual({ revenue_yoy: "0.55", gross_margin: "0.185", fin_income: "900" });
});

it("saved assumptions come back as the owner typed them", () => {
  expect(toForm({ revenue_yoy: "0.55", gross_margin: "0.185", fin_income: "900" })).toEqual({ revenue_yoy: "55", gross_margin: "18,5", fin_income: "900" });
  expect(toForm(null)).toEqual({});
});
