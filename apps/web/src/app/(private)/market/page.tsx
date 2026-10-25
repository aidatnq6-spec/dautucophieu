import { MarketView } from "../../../components/market-view";

export default function MarketPage() {
  return (
    <>
      <div className="pagehead"><h1>Thị trường và các ngành đang diễn biến ra sao?</h1><p className="muted">VN-Index, độ rộng thị trường và diễn biến theo ngành của các mã đang theo dõi.</p></div>
      <MarketView />
    </>
  );
}
