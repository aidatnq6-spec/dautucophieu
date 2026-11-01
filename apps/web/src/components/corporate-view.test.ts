import { expect, it } from "vitest";
import { describeSuggestion } from "./corporate-view";

const base = { id: "FPT-1", symbol: "FPT", title: "Trả cổ tức bằng tiền mặt - FPT", exright: "2026-06-10", record: "2026-06-11", payout: "2026-07-01",
  value_per_share: 700, ratio: 0.07, eligible: 1000, draft: null };

it("says what each suggestion is about and what is left to do", () => {
  expect(describeSuggestion({ ...base, kind: "cash", status: "to_record" }))
    .toBe("Cổ tức tiền 700 đ/cp · GDKHQ 10/06/2026 · bạn có 1.000 cp trước ngày này → ghi quyền vào sổ");
  expect(describeSuggestion({ ...base, kind: "cash", status: "to_receive" })).toBe("Cổ tức tiền 700 đ/cp · trả 01/07/2026 → ghi tiền đã nhận");
  expect(describeSuggestion({ ...base, kind: "cash", status: "waiting" })).toBe("Cổ tức tiền 700 đ/cp · đã ghi quyền, chờ trả 01/07/2026");
  expect(describeSuggestion({ ...base, kind: "stock", status: "to_record", ratio: 0.15 }))
    .toBe("Cổ phiếu thưởng 15% · GDKHQ 10/06/2026 · bạn có 1.000 cp trước ngày này → ghi quyền vào sổ");
  expect(describeSuggestion({ ...base, kind: "stock", status: "to_credit", ratio: 0.15 })).toBe("Cổ phiếu thưởng 15% · đã ghi quyền → ghi khi cổ phiếu về tài khoản");
  expect(describeSuggestion({ ...base, kind: "rights", status: "rights", ratio: 0.2 }))
    .toBe("Quyền mua 20% · GDKHQ 10/06/2026 · sổ chưa hỗ trợ quyền mua: nếu bạn thực hiện, ghi “Sự kiện chưa hỗ trợ”");
  expect(describeSuggestion({ ...base, kind: "cash", status: "upcoming" })).toBe("Cổ tức tiền 700 đ/cp · GDKHQ 10/06/2026 · sắp tới, bạn đang có 1.000 cp");
});
