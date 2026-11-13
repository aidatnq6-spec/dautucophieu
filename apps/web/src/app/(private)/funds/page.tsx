import { FundsView } from "../../../components/funds-view";

export default function FundsPage() {
  return (
    <>
      <div className="pagehead"><h1>Quỹ mở</h1><p className="muted">Các quỹ mở theo nhóm cổ phiếu, cân bằng, trái phiếu, so với VN-Index và lãi gửi 12 tháng; cùng cơ cấu quỹ bạn đang giữ.</p></div>
      <FundsView />
    </>
  );
}
