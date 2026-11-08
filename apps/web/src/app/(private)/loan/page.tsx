import { LoanTool } from "../../../components/loan-tool";

export default function LoanPage() {
  return (
    <>
      <div className="pagehead"><h1>Tính khoản vay</h1><p className="muted">Ước tính tiền phải trả mỗi tháng của một khoản vay.</p></div>
      <LoanTool />
    </>
  );
}
