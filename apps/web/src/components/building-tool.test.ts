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
    insurance: "", fixedOther: "", pcccCost: "", pcccYears: "", price: "", buyCosts: "", renovation: "", own: "", loanRate: "", termYears: "", leaseRent: "",
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
