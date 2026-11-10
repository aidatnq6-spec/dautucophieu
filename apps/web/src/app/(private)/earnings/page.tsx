import { EarningsView } from "../../../components/earnings-view";

export default function EarningsPage() {
  return (
    <>
      <div className="pagehead"><h1>Mùa báo cáo</h1><p className="muted">Kết quả quý mới nhất của danh sách theo dõi, theo ngành, lợi nhuận so với dòng tiền, và rà luận điểm mã đang nắm.</p></div>
      <EarningsView />
    </>
  );
}
