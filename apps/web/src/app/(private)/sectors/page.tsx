import { redirect } from "next/navigation";
import { Suspense } from "react";
import { SectorsView } from "../../../components/sectors-view";

export default async function SectorsPage({ searchParams }: { searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  if ((await searchParams).tab === "chuoi-gia-tri") redirect("/value-chains");  // links from when Chuỗi giá trị was a tab here
  return (
    <>
      <div className="pagehead"><h1>Ngành theo quý</h1><p className="muted">Bản đồ nhiệt kết quả theo quý và định giá P/B của cả ngành, trên các mã trong danh sách theo dõi.</p></div>
      <Suspense fallback={<p className="muted fx-loading" role="status">Đang tải…</p>}><SectorsView /></Suspense>
    </>
  );
}
