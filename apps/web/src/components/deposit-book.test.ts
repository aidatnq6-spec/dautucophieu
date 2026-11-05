import { expect, it } from "vitest";
import { bookPayload, type AccountDraft, type BondDraft, type DepositDraft, type HoldingDraft } from "./deposit-book";

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

const bond = (b: Partial<BondDraft> = {}): BondDraft => ({ id: "f", name: "Quỹ trái phiếu", amount: "50.000.000", rate: "", ...b });
const item = (h: Partial<HoldingDraft> = {}): HoldingDraft => ({ id: "g", name: "Vàng nhẫn", amount: "39.364.000", ...h });

it("adds bonds, gold and crypto, a blank bond rate staying unknown", () => {
  const r = bookPayload([], [], { bonds: [bond({ rate: "7,4" }), bond({ id: "f2" })], gold: [item()], crypto: [item({ id: "c", name: "BTC", amount: "1.000" })] });
  expect(r).toEqual({ ok: { accounts: [], deposits: [], bonds: [{ id: "f", name: "Quỹ trái phiếu", amount: "50000000", rate: "7.4" },
    { id: "f2", name: "Quỹ trái phiếu", amount: "50000000", rate: null }], gold: [{ id: "g", name: "Vàng nhẫn", amount: "39364000" }],
    crypto: [{ id: "c", name: "BTC", amount: "1000" }] } });
});

it("names the bond, gold or crypto row that cannot be saved", () => {
  expect(bookPayload([], [], { bonds: [bond({ amount: "" })], gold: [], crypto: [] })).toEqual({ error: "Trái phiếu 1: nhập số tiền (đồng)." });
  expect(bookPayload([], [], { bonds: [bond({ rate: "40" })], gold: [], crypto: [] })).toEqual({ error: "Trái phiếu 1: lợi suất từ 0 đến 30%/năm, hoặc để trống." });
  expect(bookPayload([], [], { bonds: [], gold: [item({ name: "" })], crypto: [] })).toEqual({ error: "Vàng 1: nhập tên." });
  expect(bookPayload([], [], { bonds: [], gold: [], crypto: [item(), item({ id: "d", amount: "x" })] })).toEqual({ error: "Tiền số 2: nhập số tiền (đồng)." });
});
