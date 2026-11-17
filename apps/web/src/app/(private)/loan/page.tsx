import { Suspense } from "react";
import { LoanTabs } from "../../../components/loan-tabs";

export default function LoanPage() {
  return (
    <>
      <div className="pagehead"><h1>Vay & bất động sản</h1>
        <p className="muted">Tính khoản vay, so mua một căn hộ để cho thuê với gửi tiết kiệm, và tính lợi nhuận vận hành một tòa nhà cho thuê.</p></div>
      <Suspense fallback={<p className="muted fx-loading" role="status">Đang tải…</p>}><LoanTabs /></Suspense>
    </>
  );
}
