import { expect, it } from "vitest";
import { parseSeries, slugify, stackTop } from "./operating-figures";

it("a group's id comes from its Vietnamese name without accents", () => {
  expect(slugify("Sản lượng bán theo sản phẩm")).toBe("san-luong-ban-theo-san-pham");
  expect(slugify("Thị phần (%) — HRC/Thép XD")).toBe("thi-phan-hrc-thep-xd");
  expect(slugify("Đường Ống")).toBe("duong-ong");
});

it("lines are typed comma-separated, trimmed, empty ones dropped", () => {
  expect(parseSeries(" Thép XD, HRC ,, Ống thép ")).toEqual(["Thép XD", "HRC", "Ống thép"]);
});

it("the chart's top is the largest total of a stacked group or the largest value of a line group", () => {
  const rows: { values: Record<string, string>; total: string | null }[] = [{ values: { A: "10", B: "5" }, total: "15" }, { values: { A: "12" }, total: null }];
  expect(stackTop(rows, "stack")).toBe(15);
  expect(stackTop(rows, "line")).toBe(12);
  expect(stackTop([], "stack")).toBe(0);
});
