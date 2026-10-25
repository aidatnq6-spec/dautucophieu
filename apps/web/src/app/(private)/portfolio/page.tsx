import { PortfolioView } from "../../../components/portfolio-view";

export default function PortfolioPage() {
  return (
    <>
      <div className="pagehead"><h1>Danh mục & sổ giao dịch</h1>
        <p className="muted">Bình quân gia quyền di động · Phí mua cộng vào giá vốn · Phí, thuế bán trừ vào tiền bán</p></div>
      <PortfolioView />
    </>
  );
}
