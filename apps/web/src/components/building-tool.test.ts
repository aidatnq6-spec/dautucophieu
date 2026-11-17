import { describe, expect, it } from "vitest";
import { gapText } from "./building-tool";

describe("gapText", () => {
  it("says how far a yield sits above or below the deposit rate, in points", () => {
    expect(gapText(0.092, 0.06)).toBe("cao hơn 3,2 điểm %");
    expect(gapText(0.045, 0.06)).toBe("thấp hơn 1,5 điểm %");
  });
});

describe("the hints from the 17/11/2026 recording", async () => {
  const { ARTICLE_HINTS, fillFromArticle } = await import("./building-tool");
  it("give each line the article's figure, or say it gave none", () => {
    expect(ARTICLE_HINTS.brokerPct).toBe("Bài: 8,3–10% (môi giới cá nhân, mạng xã hội); 8,3% là 1 tháng tiền thuê cho hợp đồng 12 tháng");
    expect(ARTICLE_HINTS.cleaning).toBe("Bài: 2.000.000 đ/lần, 1 lần/tuần ≈ 8.000.000 đ/tháng");
    expect(ARTICLE_HINTS.staff).toBe("Bài không nêu số");
  });
  it("fill only the single figures into empty boxes, never a range and never over a typed one", () => {
    const f = { otaPct: "", vatPct: "8", cleaning: "", brokerPct: "", pitPct: "" };
    const rows = [{ name: "", count: "", price: "", life: "" }];
    const out = fillFromArticle(f, rows);
    expect(out.f).toEqual({ otaPct: "15", vatPct: "8", cleaning: "8.000.000", brokerPct: "", pitPct: "" });
    expect(out.rows.map((r) => r.name)).toEqual(["Đèn chiếu sáng", "Thiết bị vệ sinh (bồn cầu, vòi)", "Bình nóng lạnh", "Điều hòa"]);
    expect(out.rows.every((r) => !r.count && !r.price && !r.life)).toBe(true);
    const typed = [{ name: "Thang máy", count: "1", price: "500.000.000", life: "20" }];
    expect(fillFromArticle(f, typed).rows[0]).toEqual(typed[0]);  // a list already typed is kept, the article's names added after it
    expect(fillFromArticle(f, typed).rows).toHaveLength(5);
  });
});

describe("broker commission as months of rent per contract", async () => {
  const { readPlan } = await import("./building-tool");
  const blank = { rooms: "", hiMonths: "", hiRent: "", hiOcc: "", loMonths: "", loRent: "", loOcc: "", peakRent: "", brokerPct: "", brokerMonths: "",
    contractMonths: "", otaPct: "", otaShare: "", vatPct: "", pitPct: "", otherPct: "", reservePct: "", cleaning: "", common: "", staff: "", internet: "",
    insurance: "", fixedOther: "", pcccCost: "", pcccYears: "", price: "", buyCosts: "", renovation: "", own: "", loanRate: "", termYears: "", holdYears: "", holdRate: "", leaseRent: "",
    deposit: "", setup: "", leaseMonths: "", badOcc: "", badRent: "", goodOcc: "", goodRent: "" };
  const room = { ...blank, rooms: "1", hiMonths: "12", hiRent: "7.000.000", hiOcc: "100" };
  it("one month of rent on a one-year lease of a 7m room is 583,333 đ a month", () => {
    const out = readPlan({ ...room, brokerMonths: "1", contractMonths: "12" }, [], "annuity");
    expect(out && "plan" in out && Math.round(out.plan.costs.commission)).toBe(583_333);
  });
  it("a six-month lease doubles it, and the months win over a typed share", () => {
    const out = readPlan({ ...room, brokerPct: "8,3", brokerMonths: "1", contractMonths: "6" }, [], "annuity");
    expect(out && "plan" in out && Math.round(out.plan.costs.commission)).toBe(1_166_667);
    const typed = readPlan({ ...room, brokerPct: "8,3" }, [], "annuity");
    expect(typed && "plan" in typed && Math.round(typed.plan.costs.commission)).toBe(581_000);
  });
});

describe("boxes that cannot be right are refused, not worked out", async () => {
  const { readPlan } = await import("./building-tool");
  const blank = { rooms: "", hiMonths: "", hiRent: "", hiOcc: "", loMonths: "", loRent: "", loOcc: "", peakRent: "", brokerPct: "", brokerMonths: "",
    contractMonths: "", otaPct: "", otaShare: "", vatPct: "", pitPct: "", otherPct: "", reservePct: "", cleaning: "", common: "", staff: "", internet: "",
    insurance: "", fixedOther: "", pcccCost: "", pcccYears: "", price: "", buyCosts: "", renovation: "", own: "", loanRate: "", termYears: "", holdYears: "", holdRate: "", leaseRent: "",
    deposit: "", setup: "", leaseMonths: "", badOcc: "", badRent: "", goodOcc: "", goodRent: "" };
  const room = { ...blank, rooms: "1", hiMonths: "12", hiRent: "7.000.000", hiOcc: "100" };
  it("a sum of money typed as the months of rent paid to the broker", () => {
    expect(readPlan({ ...room, brokerMonths: "7000000", contractMonths: "12" }, [], "annuity"))
      .toEqual({ error: "Hoa hồng môi giới nhập theo số tháng tiền thuê (ví dụ 1), không phải số tiền; số tháng phải nhỏ hơn thời hạn hợp đồng." });
  });
  it("shares of revenue that add up to all of it or more", () => {
    expect(readPlan({ ...room, brokerPct: "60", vatPct: "30", pitPct: "10" }, [], "annuity"))
      .toEqual({ error: "Các khoản tính theo % doanh thu cộng lại đã từ 100% trở lên: kiểm tra lại các ô % ở mục 2." });
  });
});

describe("breakevenText", async () => {
  const { breakevenText } = await import("./building-tool");
  it("names each model's breakeven occupancy, or that even full rooms do not reach it", () => {
    const p = { breakevenOccupancy: 0.412, buy: { breakevenOccupancy: 1.2 }, lease: { breakevenOccupancy: 0.584 } } as never;
    expect(breakevenText(p)).toBe("vận hành 41,2% · mua tòa (sau trả nợ) kín phòng cũng chưa hòa vốn · thuê lại (sau tiền thuê tòa) 58,4%");
  });
});

describe("the profit chart", async () => {
  const { chartLines, OCC_STEPS } = await import("./building-tool");
  const { buildingPlan } = await import("./building-calc");
  const input = { rooms: 10, seasons: [{ months: 12, rent: 10_000_000, occupancy: 80 }], peakRent: null, brokerPct: 0, otaPct: 0, otaShare: 0, vatPct: 0,
    pitPct: 0, otherPct: 0, reservePct: 0, fixed: { cleaning: 8_000_000, common: 0, staff: 0, internet: 0, insurance: 0, other: 0 }, equipment: [],
    pccc: { cost: 0, years: 0 }, lease: { rent: 50_000_000, deposit: 0, setup: 0, months: 12 } };
  it("draws each model from empty to full rooms with the range to fit them and zero", () => {
    const c = chartLines(input, buildingPlan(input));
    expect(OCC_STEPS[0]).toBe(0); expect(OCC_STEPS.at(-1)).toBe(100);
    expect(c.series.map((s) => s.id)).toEqual(["noi", "lease"]);   // no purchase entered: no line for it
    const noi = c.series[0];
    expect(noi.values[0]).toBe(-8_000_000);                        // empty: the fixed cost
    expect(noi.values.at(-1)).toBe(92_000_000);                    // full: 100m less 8m
    expect(c.series[1].breakeven).toBeCloseTo(0.58, 10);           // (8m + 50m) of 100m
    expect(c.lo).toBe(-58_000_000); expect(c.hi).toBe(92_000_000);
  });
});

describe("the bars comparing saved plans", async () => {
  const { compareBars } = await import("./building-tool");
  it("gives each plan its models' monthly results and a range that holds them and zero", () => {
    const plan = (noi: number, buy: number | null, lease: number | null) =>
      ({ noiMonth: noi, buy: buy === null ? null : { cashMonth: buy }, lease: lease === null ? null : { profitMonth: lease } }) as never;
    const out = compareBars([{ name: "Tòa A", plan: plan(55e6, 22e6, null) }, { name: "Tòa B", plan: plan(30e6, null, -5e6) }, { name: "Tòa C", plan: null }]);
    expect(out.groups.map((g) => [g.name, g.bars.map((b) => [b.id, b.value])])).toEqual([
      ["Tòa A", [["noi", 55e6], ["buy", 22e6]]], ["Tòa B", [["noi", 30e6], ["lease", -5e6]]], ["Tòa C", []]]);
    expect([out.lo, out.hi]).toEqual([-5e6, 55e6]);
  });
});
