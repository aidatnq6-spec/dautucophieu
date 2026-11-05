import { expect, it } from "vitest";
import { bookPayload, type AccountDraft, type DepositDraft } from "./deposit-book";

const depo = (d: Partial<DepositDraft> = {}): DepositDraft => ({ id: "a", bank: "Ngân hàng A", matures: "2027-03-05", principal: "50.000.000", rate: "",
  interest: "", payout: "end", locked: true, ...d });
const tk = (a: Partial<AccountDraft> = {}): AccountDraft => ({ id: "x", name: "Tài khoản", amount: "1.000.000", liquid: true, ...a });

it("turns typed rows into the API book, a blank rate or interest staying unknown rather than 0", () => {
  const r = bookPayload([tk()], [depo({ rate: "5,8", interest: "2.030.548" }), depo({ id: "b" })]);
  expect(r).toEqual({ ok: { accounts: [{ id: "x", name: "Tài khoản", amount: "1000000", liquid: true }],
    deposits: [{ id: "a", bank: "Ngân hàng A", matures: "2027-03-05", principal: "50000000", rate: "5.8", interest: "2030548", payout: "end", locked: true },
      { id: "b", bank: "Ngân hàng A", matures: "2027-03-05", principal: "50000000", rate: null, interest: null, payout: "end", locked: true }] } });
});

it("names the row that cannot be saved", () => {
  expect(bookPayload([], [depo({ principal: "" })])).toEqual({ error: "Sổ 1: nhập tiền gốc (đồng, lớn hơn 0)." });
  expect(bookPayload([], [depo(), depo({ id: "b", matures: "" })])).toEqual({ error: "Sổ 2: chọn ngày đáo hạn." });
  expect(bookPayload([], [depo({ bank: " " })])).toEqual({ error: "Sổ 1: nhập tên ngân hàng." });
  expect(bookPayload([], [depo({ rate: "31" })])).toEqual({ error: "Sổ 1: lãi suất từ 0 đến 30%/năm, hoặc để trống." });
  expect(bookPayload([tk({ amount: "" })], [])).toEqual({ error: "Tài khoản 1: nhập số tiền (đồng)." });
  expect(bookPayload([tk({ name: "" })], [])).toEqual({ error: "Tài khoản 1: nhập tên." });
});
