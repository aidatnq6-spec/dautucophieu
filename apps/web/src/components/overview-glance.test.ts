import { expect, it } from "vitest";
import { kpiNotes, scopeLine, type Glance } from "./overview-glance";

const kpis: Glance["kpis"] = { market_value: "6000000", unrealized_gain: "1000000", day_change: "100000", day_change_ratio: "0.0169", vnindex: "1252.4",
  vnindex_change_ratio: "0.0100", performance: null, room: null, over_budget: null, held_count: 2, unpriced: [], no_prior_close: [],
  price_dates: ["2027-01-14"] };
const g = (k: Partial<Glance["kpis"]> = {}, session: string | null = "2027-01-14"): Glance =>
  ({ session_date: session, kpis: { ...kpis, ...k }, attention: { events: [], over_limit: [], journal_reviews: [], latest_report: null } });

it("the scope line names the session, the price day, how many holdings and the unit", () => {
  expect(scopeLine(g())).toBe("Phiên 14/01/2027 · giá ngày 14/01/2027 · 2 mã đang giữ · đơn vị đồng");
  expect(scopeLine(g({ price_dates: ["2027-01-13", "2027-01-14"] }))).toContain("giá các ngày 13/01/2027, 14/01/2027");
  expect(scopeLine(g({ price_dates: [], held_count: 0 }, null))).toBe("Chưa có phiên VN-Index đã lưu · chưa nắm giữ mã nào · đơn vị đồng");
});

it("each number says how it is made", () => {
  const n = kpiNotes(g());
  expect(n.value).toBe("Số lượng × giá gần nhất");
  expect(n.gain).toBe("Giá trị theo giá gần nhất − giá vốn");
  expect(n.day).toBe("So với giá đóng cửa phiên trước");
  expect(n.vnindex).toBe("Điểm đóng cửa phiên gần nhất");
  expect(n.budget).toBe("Vốn cho cổ phiếu − giá vốn đang nắm");
});

it("a holding left out is named instead of silently dropped", () => {
  const n = kpiNotes(g({ unpriced: ["MBB"], no_prior_close: ["MBB", "VCB"] }));
  expect(n.value).toBe("Chưa tính MBB: chưa có giá");
  expect(n.gain).toBe("Chưa tính MBB: chưa có giá");
  expect(n.day).toBe("Chưa tính MBB, VCB: thiếu giá đóng cửa phiên trước");
});

it("an empty number gives its reason", () => {
  expect(kpiNotes(g({ day_change: null, held_count: 0 })).day).toBe("Chưa nắm giữ mã nào");
  expect(kpiNotes(g({ day_change: null, no_prior_close: ["FPT"] })).day).toBe("Chưa có hai phiên đóng cửa đã lưu cho mã đang giữ");
  expect(kpiNotes(g({ vnindex: null })).vnindex).toBe("Chưa có chuỗi VN-Index đã lưu");
});
