import { Suspense } from "react";
import { SectorAnalysis } from "../../../components/sector-analysis";

export default function SectorsPage() {
  return (
    <>
      <div className="pagehead"><h1>Phân tích ngành</h1><p className="muted">Kết quả theo quý và định giá của cả ngành, và chuỗi giá trị của từng ngành với vĩ mô đang tốt hay xấu cho ngành.</p></div>
      <Suspense fallback={<p className="muted fx-loading" role="status">Đang tải…</p>}><SectorAnalysis /></Suspense>
    </>
  );
}
