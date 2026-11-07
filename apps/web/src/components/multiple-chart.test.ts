import { expect, it } from "vitest";
import { calcNote, periodText, yearLabels } from "./multiple-chart";

it("a point names the figures behind it: four quarters, a quarter's equity or a year", () => {
  expect(periodText("2026-Q3", "4 quý")).toBe("4 quý đến Q3/2026");
  expect(periodText("2026-Q3", "quý")).toBe("vốn chủ cuối Q3/2026");
  expect(periodText("2025", "năm")).toBe("số liệu năm 2025");
  expect(periodText("2025", undefined)).toBe("số liệu năm 2025");
});

it("each year is labelled at its first month; a label crowded by the next one is dropped, and one at the left edge is kept", () => {
  const months = ["2017-12", "2018-01", "2018-02", "2018-03", "2018-04", "2018-05", "2019-01", "2019-02"];
  const x = (i: number) => 36 + i * 6;  // dense: 6 px a month, as the index charts from 12/2017
  expect(yearLabels(months, x, 36, 1)).toEqual([{ i: 1, year: "2018", anchor: "start" }, { i: 6, year: "2019", anchor: "middle" }]);
  expect(yearLabels(months, (i) => 36 + i * 100, 36, 1)).toEqual([{ i: 0, year: "2017", anchor: "start" }, { i: 1, year: "2018", anchor: "middle" },
    { i: 6, year: "2019", anchor: "middle" }]);
  expect(yearLabels(months, (i) => 36 + i * 100, 36, 2).map((l) => l.year)).toEqual(["2018"]);  // every other year on a phone
});

it("the worked-out part of an index chart is named with its limits and how far it is from VNDirect where both exist", () => {
  const calc = { from: "2013-01", to: "2017-11", check: { tickers: 380, pe: { months: 107, mean_abs: "0.0612" }, pb: { months: 107, mean_abs: "0.0435" } } };
  expect(calcNote(calc)).toBe("Nét đứt 01/2013–11/2017: tự tính từ 380 mã còn niêm yết trên HOSE hôm nay; thiếu các mã đã hủy niêm yết nên quá khứ bị lệch. "
    + "Cùng cách tính so với VNDirect ở 107 tháng trùng nhau: P/E lệch trung bình 6,1%, P/B 4,4%.");
});

it("the estimated VN30 basket is named as such", () => {
  const calc = { from: "2013-01", to: "2017-11", check: { tickers: 408, basket: "top30", pe: { months: 107, mean_abs: "0.0700" }, pb: { months: 107, mean_abs: "0.0500" } } };
  expect(calcNote(calc)).toContain("rổ ước tính: 30 mã vốn hoá lớn nhất mỗi kỳ trong 408 mã còn niêm yết trên HOSE hôm nay");
  expect(calcNote(calc)).toContain("luật thật còn xét free-float và thanh khoản");
});
