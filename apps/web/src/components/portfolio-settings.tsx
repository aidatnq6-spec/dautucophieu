"use client";
import { useEffect, useState } from "react";
import { Save } from "lucide-react";
import { ApiError, api, requestId } from "../lib/api";
import { formatRatio, percentToRatio } from "../lib/format";

type PortfolioSettings = { version: number; settings: { concentration_limit: string } };

/** Concentration threshold for the Danh mục page (display only; does not change allocation rules). */
export function PortfolioSettingsSection() {
  const [data, setData] = useState<PortfolioSettings | null>(null);
  const [value, setValue] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  useEffect(() => {
    api<PortfolioSettings>("settings/portfolio").then((d) => { setData(d); setValue(formatRatio(d.settings.concentration_limit, 1).replace("%", "").replace(/,0$/, "")); },
      (e) => setMessage(e instanceof ApiError ? e.failure.message : "Lỗi tải."));
  }, []);
  async function save() {
    if (!data) return;
    const ratio = percentToRatio(value);
    if (ratio === null) { setMessage("Nhập phần trăm, ví dụ 25."); return; }
    try {
      const saved = await api<PortfolioSettings>("settings/portfolio", { method: "PUT",
        body: { settings: { concentration_limit: ratio }, expected_version: data.version, request_id: requestId() } });
      setData(saved); setMessage("Đã lưu ngưỡng tập trung.");
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
        <input inputMode="decimal" value={value} onChange={(e) => setValue(e.target.value)} disabled={!data} /></label></div>
      <div className="actions"><button className="btn primary" onClick={() => void save()} disabled={!data}><Save size={16} aria-hidden="true" />Lưu ngưỡng</button></div>
      {message && <p className="caption" role="status">{message}</p>}
    </section>
  );
}
