import { expect, it } from "vitest";
import { applyProposal, parseSeries, slugify, stackTop } from "./operating-figures";

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

it("a PDF proposal fills each line with its first candidate and the link with the pages as the source", () => {
  const proposal = { url: "https://hoaphat.com.vn/bt.pdf", values: { "Thép XD": [{ value: "412300", page: 1, text: "…" }, { value: "18", page: 1, text: "…" }],
    HRC: [{ value: "512000", page: 2, text: "…" }] }, missing: ["Tôn mạ"], warnings: [] };
  expect(applyProposal(proposal)).toEqual({ values: { "Thép XD": "412300", HRC: "512000" }, source: "https://hoaphat.com.vn/bt.pdf (trang 1, 2)" });
});
