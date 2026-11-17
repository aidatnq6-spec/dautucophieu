import { BuildingTool } from "../../../components/building-tool";

export default function BuildingPage() {
  return (
    <>
      <div className="pagehead"><h1>Lợi nhuận tòa nhà cho thuê</h1>
        <p className="muted">Tính doanh thu theo mùa, chi phí nổi và chi phí chìm, rồi lợi nhuận khi mua tòa hoặc thuê lại nguyên tòa để vận hành.</p></div>
      <BuildingTool />
    </>
  );
}
