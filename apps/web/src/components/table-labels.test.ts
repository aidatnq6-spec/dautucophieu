import { describe, expect, it } from "vitest";
import { labelTable } from "./table-labels";

function table(html: string): HTMLTableElement {
  const div = document.createElement("div");
  div.innerHTML = `<table>${html}</table>`;
  return div.querySelector("table")!;
}
const labels = (t: HTMLTableElement) => [...t.querySelectorAll("tbody tr")].map((r) => [...r.children].map((c) => c.getAttribute("data-label")));

describe("labelTable", () => {
  it("gives each cell its column's heading, keeping a label already set", () => {
    const t = table(`<thead><tr><th>Mã</th><th>Giá</th><th>Thay đổi</th></tr></thead>
      <tbody><tr><td>FPT</td><td data-label="Giá đóng cửa">100</td><td>+1%</td></tr></tbody>`);
    labelTable(t);
    expect(labels(t)).toEqual([["Mã", "Giá đóng cửa", "Thay đổi"]]);
  });
  it("follows spans and joins a group heading with the column's own", () => {
    const t = table(`<thead><tr><th rowspan="2">Mã</th><th colspan="2">Định giá</th></tr><tr><th>P/E</th><th>P/B</th></tr></thead>
      <tbody><tr><th scope="row">FPT</th><td>20</td><td>5</td></tr><tr><td colspan="2">ghi chú</td><td>x</td></tr></tbody>`);
    labelTable(t);
    expect(labels(t)).toEqual([["Mã", "Định giá · P/E", "Định giá · P/B"], ["Mã", "Định giá · P/B"]]);
  });
  it("marks a table without headings as left alone", () => {
    const t = table(`<tbody><tr><td>a</td><td>b</td></tr></tbody>`);
    labelTable(t);
    expect(t.hasAttribute("data-cards")).toBe(false);
    const h = table(`<thead><tr><th>A</th></tr></thead><tbody><tr><td>1</td></tr></tbody>`);
    labelTable(h);
    expect(h.getAttribute("data-cards")).toBe("1");
  });
});
