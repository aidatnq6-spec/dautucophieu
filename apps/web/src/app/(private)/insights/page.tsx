import { InsightsView } from "../../../components/insights-view";

export default function InsightsPage() {
  return (
    <>
      <div className="pagehead"><h1>Nhận định từ báo cáo</h1><p className="muted">Vĩ mô thuận lợi hay bất lợi, ngành nào hưởng lợi hay bất lợi, theo báo cáo của các tổ chức.</p></div>
      <InsightsView />
    </>
  );
}
