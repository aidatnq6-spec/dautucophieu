import { expect, it } from "vitest";
import { bookPayload, removeRow, reservePayload, upsertRow, type AccountDraft, type BondDraft, type DepositDraft, type GoldDraft, type HoldingDraft } from "./deposit-book";

const depo = (d: Partial<DepositDraft> = {}): DepositDraft => ({ id: "a", bank: "Ngân hàng A", matures: "2027-03-05", principal: "50.000.000", rate: "",
  interest: "", payout: "end", locked: true, ...d });
const tk = (a: Partial<AccountDraft> = {}): AccountDraft => ({ id: "x", name: "Tài khoản", amount: "1.000.000", liquid: true, ...a });

it("turns typed rows into the API book, a blank rate or interest staying unknown rather than 0", () => {
  const r = bookPayload([tk()], [depo({ rate: "5,8", interest: "2.030.548" }), depo({ id: "b" })]);
  expect(r).toEqual({ ok: { accounts: [{ id: "x", name: "Tài khoản", amount: "1000000", liquid: true }],
    deposits: [{ id: "a", bank: "Ngân hàng A", matures: "2027-03-05", principal: "50000000", rate: "5.8", interest: "2030548", payout: "end", locked: true },
      { id: "b", bank: "Ngân hàng A", matures: "2027-03-05", principal: "50000000", rate: null, interest: null, payout: "end", locked: true }],
    bonds: [], gold: [], crypto: [] } });
});

it("names the row that cannot be saved", () => {
  expect(bookPayload([], [depo({ principal: "" })])).toEqual({ error: "Sổ 1: nhập tiền gốc (đồng, lớn hơn 0)." });
  expect(bookPayload([], [depo(), depo({ id: "b", matures: "" })])).toEqual({ error: "Sổ 2: chọn ngày đáo hạn." });
  expect(bookPayload([], [depo({ bank: " " })])).toEqual({ error: "Sổ 1: nhập tên ngân hàng." });
  expect(bookPayload([], [depo({ rate: "31" })])).toEqual({ error: "Sổ 1: lãi suất từ 0 đến 30%/năm, hoặc để trống." });
  expect(bookPayload([tk({ amount: "" })], [])).toEqual({ error: "Tài khoản 1: nhập số tiền (đồng)." });
  expect(bookPayload([tk({ name: "" })], [])).toEqual({ error: "Tài khoản 1: nhập tên." });
});

const bond = (b: Partial<BondDraft> = {}): BondDraft => ({ id: "f", name: "Quỹ trái phiếu", amount: "50.000.000", rate: "", fund: "", units: "", ...b });
const item = (h: Partial<HoldingDraft> = {}): HoldingDraft => ({ id: "g", name: "Vàng nhẫn", amount: "39.364.000", ...h });
const gold = (g: Partial<GoldDraft> = {}): GoldDraft => ({ ...item(), kind: "", chi: "", ...g });

it("adds bonds, gold and crypto, a blank bond rate staying unknown", () => {
  const r = bookPayload([], [], { bonds: [bond({ rate: "7,4" }), bond({ id: "f2" })], gold: [gold()], crypto: [item({ id: "c", name: "BTC", amount: "1.000" })] });
  expect(r).toEqual({ ok: { accounts: [], deposits: [], bonds: [{ id: "f", name: "Quỹ trái phiếu", amount: "50000000", rate: "7.4", fund: null, units: null },
    { id: "f2", name: "Quỹ trái phiếu", amount: "50000000", rate: null, fund: null, units: null }], gold: [{ id: "g", name: "Vàng nhẫn", amount: "39364000", kind: null, chi: null }],
    crypto: [{ id: "c", name: "BTC", amount: "1000" }] } });
});

it("names the bond, gold or crypto row that cannot be saved", () => {
  expect(bookPayload([], [], { bonds: [bond({ amount: "" })], gold: [], crypto: [] })).toEqual({ error: "Trái phiếu 1: nhập số tiền (đồng)." });
  expect(bookPayload([], [], { bonds: [bond({ rate: "40" })], gold: [], crypto: [] })).toEqual({ error: "Trái phiếu 1: lợi suất từ 0 đến 30%/năm, hoặc để trống." });
  expect(bookPayload([], [], { bonds: [], gold: [gold({ name: "" })], crypto: [] })).toEqual({ error: "Vàng 1: nhập tên." });
  expect(bookPayload([], [], { bonds: [], gold: [], crypto: [item(), item({ id: "d", amount: "x" })] })).toEqual({ error: "Tiền số 2: nhập số tiền (đồng)." });
});

it("takes the reserve in whole đồng, a blank one meaning the profile's figure", () => {
  expect(reservePayload("")).toEqual({ ok: null });
  expect(reservePayload(" 120.000.000 ")).toEqual({ ok: "120000000" });
  expect(reservePayload("12,5")).toEqual({ error: "Quỹ dự phòng: nhập số đồng, hoặc để trống để theo hồ sơ." });
  expect(reservePayload("abc")).toEqual({ error: "Quỹ dự phòng: nhập số đồng, hoặc để trống để theo hồ sơ." });
});

it("saves one row at a time: an edited row keeps its place, a new one goes last, a deleted one leaves the rest as they were", () => {
  const rows = [item({ id: "a" }), item({ id: "b", name: "Vàng miếng" })];
  expect(upsertRow(rows, item({ id: "b", amount: "1.000" }))).toEqual([item({ id: "a" }), item({ id: "b", amount: "1.000" })]);
  expect(upsertRow(rows, item({ id: "c" })).map((r) => r.id)).toEqual(["a", "b", "c"]);
  expect(removeRow(rows, "a")).toEqual([item({ id: "b", name: "Vàng miếng" })]);
  expect(removeRow(rows, "z")).toEqual(rows);
});

it("takes a fund code with its units, written the Vietnamese way, and refuses one without the other", () => {
  const ok = bookPayload([], [], { bonds: [bond({ fund: " vcbf-fif ", units: "1.837,42" })], gold: [], crypto: [] });
  expect(ok).toEqual({ ok: { accounts: [], deposits: [], bonds: [{ id: "f", name: "Quỹ trái phiếu", amount: "50000000", rate: null, fund: "VCBF-FIF",
    units: "1837.42" }], gold: [], crypto: [] } });
  const err = (b: Partial<BondDraft>) => bookPayload([], [], { bonds: [bond(b)], gold: [], crypto: [] });
  expect(err({ fund: "VFF" })).toEqual({ error: "Trái phiếu 1: nhập cả mã quỹ và số đơn vị, hoặc để trống cả hai." });
  expect(err({ units: "10" })).toEqual({ error: "Trái phiếu 1: nhập cả mã quỹ và số đơn vị, hoặc để trống cả hai." });
  expect(err({ fund: "VFF", units: "1,234" })).toEqual({ error: "Trái phiếu 1: số đơn vị lớn hơn 0, tối đa 2 chữ số thập phân." });
  expect(err({ fund: "V F F", units: "1" })).toEqual({ error: "Trái phiếu 1: mã quỹ như trên Fmarket, ví dụ VFF hoặc VCBF-FIF." });
});

it("takes a gold kind with its chi, and refuses one without the other", () => {
  const ok = bookPayload([], [], { bonds: [], gold: [gold({ kind: "Nhẫn tròn Phú Quý 999.9", chi: "2,5" })], crypto: [] });
  expect(ok).toEqual({ ok: { accounts: [], deposits: [], bonds: [], gold: [{ id: "g", name: "Vàng nhẫn", amount: "39364000",
    kind: "Nhẫn tròn Phú Quý 999.9", chi: "2.5" }], crypto: [] } });
  const err = (g: Partial<GoldDraft>) => bookPayload([], [], { bonds: [], gold: [gold(g)], crypto: [] });
  expect(err({ kind: "Vàng miếng SJC" })).toEqual({ error: "Vàng 1: chọn cả loại giá và số chỉ, hoặc để trống cả hai." });
  expect(err({ chi: "1" })).toEqual({ error: "Vàng 1: chọn cả loại giá và số chỉ, hoặc để trống cả hai." });
  expect(err({ kind: "Vàng miếng SJC", chi: "1,255" })).toEqual({ error: "Vàng 1: số chỉ lớn hơn 0, tối đa 2 chữ số thập phân." });
});
