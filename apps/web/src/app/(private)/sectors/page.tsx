import { Suspense } from "react";
import { SectorsView } from "../../../components/sectors-view";

export default function SectorsPage() {
  return (
    <>
      <div className="pagehead"><h1>Toàn ngành</h1><p className="muted">Bản đồ nhiệt kết quả theo quý và định giá P/B của cả ngành, trên các mã trong danh sách theo dõi.</p></div>
      <Suspense fallback={<p className="muted fx-loading" role="status">Đang tải…</p>}><SectorsView /></Suspense>
    </>
  );
}
