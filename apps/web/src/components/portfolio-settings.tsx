"use client";
import { useEffect, useState } from "react";
import { Save } from "lucide-react";
import { ApiError, api, requestId } from "../lib/api";
import { formatRatio, percentToRatio } from "../lib/format";

type PortfolioSettings = { version: number; settings: { concentration_limit: string; journal_review_threshold: string; drawdown_threshold: string } };

/** Concentration threshold for the Danh mục page (display only; does not change allocation rules). */
export function PortfolioSettingsSection() {
  const [data, setData] = useState<PortfolioSettings | null>(null);
  const [value, setValue] = useState("");
  const [review, setReview] = useState("");
  const [drawdown, setDrawdown] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  useEffect(() => {
    const percent = (r: string) => formatRatio(r, 1).replace("%", "").replace(/,0$/, "");
    api<PortfolioSettings>("settings/portfolio").then((d) => { setData(d); setValue(percent(d.settings.concentration_limit)); setReview(percent(d.settings.journal_review_threshold));
      setDrawdown(percent(d.settings.drawdown_threshold)); },
      (e) => setMessage(e instanceof ApiError ? e.failure.message : "Lỗi tải."));
  }, []);
  async function save() {
    if (!data) return;
    const ratio = percentToRatio(value);
    const reviewRatio = percentToRatio(review);
    const drawdownRatio = percentToRatio(drawdown);
    if (ratio === null || reviewRatio === null || drawdownRatio === null) { setMessage("Nhập phần trăm, ví dụ 25."); return; }
    try {
      const saved = await api<PortfolioSettings>("settings/portfolio", { method: "PUT",
        body: { settings: { concentration_limit: ratio, journal_review_threshold: reviewRatio, drawdown_threshold: drawdownRatio }, expected_version: data.version, request_id: requestId() } });
      setData(saved); setMessage("Đã lưu các ngưỡng.");
    } catch (e) {
      setMessage(e instanceof ApiError ? e.failure.message : "Lỗi lưu.");
    }
  }
  return (
    <section className="surface" aria-label="Rủi ro tập trung">
      <h2>Rủi ro tập trung</h2>
      <p className="caption">Dùng cho khối «Phân bổ và rủi ro tập trung» ở trang Danh mục & Giao dịch: một mã hoặc một ngành vượt ngưỡng (tính trên vốn có thể đầu tư)
        thì được đánh dấu. Chỉ để hiển thị, không đổi chính sách phân bổ.</p>
      <div className="formgrid"><label className="field">Ngưỡng tập trung một mã hoặc một ngành (%)
        <input inputMode="decimal" value={value} onChange={(e) => setValue(e.target.value)} disabled={!data} /></label>
        <label className="field">Nhật ký: nhắc xem lại khi giá đi thêm (%)
        <input inputMode="decimal" value={review} onChange={(e) => setReview(e.target.value)} disabled={!data} /></label>
        <label className="field">Kế hoạch sụt giảm: nhắc khi giá thấp hơn giá vốn (%)
        <input inputMode="decimal" value={drawdown} onChange={(e) => setDrawdown(e.target.value)} disabled={!data} /></label></div>
      <p className="caption">Mỗi lần giá đi thêm mức này so với giá lúc ghi nhật ký (lên hoặc xuống), ứng dụng gửi Telegram một lần kèm lý do đã ghi;
        theo «Gửi tự động theo lịch».</p>
      <div className="actions"><button className="btn primary" onClick={() => void save()} disabled={!data}><Save size={16} aria-hidden="true" />Lưu ngưỡng</button></div>
      {message && <p className="caption" role="status">{message}</p>}
    </section>
  );
}
