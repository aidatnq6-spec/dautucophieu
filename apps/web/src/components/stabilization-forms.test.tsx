import { render, screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import { ProfileForm } from "./profile-form";
import { TransactionForm } from "./transaction-form";

it("describes goal amount as the total before dedicated funding", () => {
  render(<ProfileForm version={0} onSaved={vi.fn()} />);
  expect(screen.getByText(/tổng số tiền cần cho mục tiêu trước khi trừ nguồn bù/i)).toBeTruthy();
});

it("offers opening balances and cash-dividend events", () => {
  render(<TransactionForm ledgerVersion={0} events={[]} editing={null} onSaved={vi.fn()} />);
  const options = screen.getAllByRole("option").map((node) => node.getAttribute("value"));
  expect(options).toEqual(expect.arrayContaining(["opening_balance", "cash_dividend_entitlement", "cash_dividend_payment"]));
});
