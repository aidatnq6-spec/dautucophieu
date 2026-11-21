import { HistoryStatsView } from "../../../components/history-stats";

export default function HistoryPage() {
  return (
    <>
      <div className="pagehead"><h1>Thống kê lịch sử</h1><p className="muted">Trong quá khứ, khi thị trường ở trạng thái như hôm nay, VN-Index sau đó thường ra sao,
        và mỗi con số dựa trên bao nhiêu bằng chứng.</p></div>
      <HistoryStatsView />
    </>
  );
}
