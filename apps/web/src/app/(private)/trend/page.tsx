import { TrendView } from "../../../components/trend-view";

export default function TrendPage() {
  return (
    <>
      <div className="pagehead"><h1>Xu hướng theo khung thời gian</h1><p className="muted">MACD và RSI theo tháng, tuần, ngày, 4 giờ và 1 giờ, lập sau 15:30 mỗi phiên.</p></div>
      <TrendView />
    </>
  );
}
