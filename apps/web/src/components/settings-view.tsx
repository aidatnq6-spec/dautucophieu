"use client";
import { useCallback, useEffect, useState } from "react";
import { Save } from "lucide-react";
import { ApiError, api, requestId, type ApiFailure } from "../lib/api";
import { formatRatio, percentToRatio } from "../lib/format";
import { AiStatusSection } from "./ai-status";
import { FormErrors } from "./form-errors";
import { PortfolioSettingsSection } from "./portfolio-settings";

type Notify = { enabled: boolean; chat_id: string | null; members_may_view_personal_data: boolean; scheduled_enabled: boolean };
type NotifyView = { version: number; settings: Notify; bot_token_configured: boolean };
type Trading = { version: number; settings: { fee_rate: string } | null };
type Valuation = { version: number; settings: { required_return: string; long_term_growth: string; threshold: string } };
const VALUATION_FIELDS = [["required_return", "Lợi suất yêu cầu (%/năm)"], ["long_term_growth", "Tăng trưởng dài hạn (%/năm)"],
  ["threshold", "Ngưỡng Rẻ/Đắt (%)"]] as const;

export function SettingsView() {
  const [notify, setNotify] = useState<NotifyView | null>(null);
  const [trading, setTrading] = useState<Trading | null>(null);
  const [form, setForm] = useState<Notify | null>(null);
  const [fee, setFee] = useState("");
  const [valuation, setValuation] = useState<Valuation | null>(null);
  const [vForm, setVForm] = useState<Record<string, string>>({});
  const [failure, setFailure] = useState<ApiFailure | null>(null);
  const [saved, setSaved] = useState<string | null>(null);
  const load = useCallback(() => Promise.all([api<NotifyView>("notifications/settings"), api<Trading>("settings/trading"),
    api<Valuation>("settings/valuation")]).then(([n, t, v]) => {
    setNotify(n); setForm(n.settings); setTrading(t); setValuation(v);
    setVForm(Object.fromEntries(VALUATION_FIELDS.map(([k]) => [k, formatRatio(v.settings[k], 1).replace("%", "")])));
  }, (e) => { if (e instanceof ApiError) setFailure(e.failure); }), []);
  useEffect(() => { void load(); }, [load]);

  async function save(kind: "notify" | "trading" | "valuation") {
    setFailure(null);
    setSaved(null);
    try {
      if (kind === "notify" && notify && form) {
        await api("notifications/settings", { method: "PUT", body: { settings: { ...form, chat_id: form.chat_id || null }, expected_version: notify.version, request_id: requestId() } });
      } else if (kind === "trading" && trading) {
        const ratio = percentToRatio(fee);
        if (ratio === null) { setFailure({ status: 0, code: "invalid", message: "Phí phải là phần trăm hợp lệ, ví dụ 0,15", fields: [] }); return; }
        await api("settings/trading", { method: "PUT", body: { settings: { fee_rate: ratio }, expected_version: trading.version, request_id: requestId() } });
      } else if (kind === "valuation" && valuation) {
        const ratios = Object.fromEntries(VALUATION_FIELDS.map(([k]) => [k, percentToRatio(vForm[k] ?? "")]));
        if (Object.values(ratios).some((r) => r === null)) {
          setFailure({ status: 0, code: "invalid", message: "Các ô định giá phải là phần trăm hợp lệ, ví dụ 13 hoặc 5,5", fields: [] }); return;
        }
        await api("settings/valuation", { method: "PUT", body: { settings: ratios, expected_version: valuation.version, request_id: requestId() } });
      }
      setSaved("Đã lưu.");
      await load();
    } catch (e) { if (e instanceof ApiError) setFailure(e.failure); }
  }

  if (!notify || !form || !trading || !valuation) return <><FormErrors failure={failure} /><p className="muted fx-loading" role="status">Đang tải…</p></>;
  const set = (patch: Partial<Notify>) => setForm({ ...form, ...patch });
  return (
    <>
      <FormErrors failure={failure} />
      {saved && <p role="status" className="pill good">{saved}</p>}
      <section className="surface">
        <h2>Phí giao dịch</h2>
        <p className="caption">Theo biểu phí của công ty chứng khoán của bạn; dùng để đề xuất mua không vượt tiền khả dụng. Ứng dụng không tự đặt mức phí.</p>
        <p>Đang dùng: {trading.settings ? formatRatio(trading.settings.fee_rate, 3) : "chưa cấu hình"}</p>
        <div className="formgrid"><label className="field">Phí mua/bán (% giá trị lệnh)<input inputMode="decimal" value={fee} onChange={(e) => setFee(e.target.value)} placeholder="0,15" /></label></div>
        <div className="actions"><button className="btn primary" onClick={() => void save("trading")}><Save size={16} aria-hidden="true" />Lưu phí</button></div>
      </section>
      <section className="surface" aria-label="Định giá tham khảo">
        <h2>Định giá tham khảo</h2>
        <p className="caption">Dùng cho trang Định giá: lợi suất yêu cầu và tăng trưởng dài hạn cho P/B theo ROE và chiết khấu cổ tức; ngưỡng so với giá hợp lý để gọi Rẻ/Đắt.</p>
        <div className="formgrid">{VALUATION_FIELDS.map(([k, label]) => (
          <label key={k} className="field">{label}<input inputMode="decimal" value={vForm[k] ?? ""} onChange={(e) => setVForm({ ...vForm, [k]: e.target.value })} /></label>))}
        </div>
        <div className="actions"><button className="btn primary" onClick={() => void save("valuation")}><Save size={16} aria-hidden="true" />Lưu định giá</button></div>
      </section>
      <PortfolioSettingsSection />
      <section className="surface">
        <h2>Telegram</h2>
        <p>Bot Token: {notify.bot_token_configured ? "đã cấu hình phía máy chủ" : "chưa cấu hình (đặt TELEGRAM_BOT_TOKEN trong .env.local trên máy chủ)"}. Ứng dụng không nhận token qua giao diện.</p>
        <div className="formgrid"><label className="field">Group ID<input value={form.chat_id ?? ""} onChange={(e) => set({ chat_id: e.target.value.trim() })} placeholder="-100…" /></label></div>
        <label className="choice"><input type="checkbox" checked={form.members_may_view_personal_data} onChange={(e) => set({ members_may_view_personal_data: e.target.checked })} />
          Tôi xác nhận mọi thành viên trong nhóm được phép xem giá trị danh mục cá nhân của tôi</label>
        <label className="choice"><input type="checkbox" checked={form.enabled} onChange={(e) => set({ enabled: e.target.checked, scheduled_enabled: e.target.checked && form.scheduled_enabled })} />
          Cho phép gửi (chỉ khi tôi bấm “Gửi thử”)</label>
        <label className="choice"><input type="checkbox" checked={form.scheduled_enabled} disabled={!form.enabled} onChange={(e) => set({ scheduled_enabled: e.target.checked })} />
          Gửi tự động theo lịch sau phiên</label>
        <div className="actions"><button className="btn primary" onClick={() => void save("notify")}><Save size={16} aria-hidden="true" />Lưu Telegram</button></div>
      </section>
      <section className="surface">
        <h2>Lịch sau phiên</h2>
        <p>Chạy lúc 15:30, thử lại 17:30, 18:30 và 20:00 (giờ Việt Nam) chỉ khi giá của phiên chưa về đủ; 07:00 sáng và khi máy bật lại sẽ chạy bù phiên gần nhất chưa có bản tin.
          Bản tin lịch sử bổ sung không được gửi hàng loạt.</p>
        <p className="notice">Máy tắt hoặc ngủ thì không bảo đảm chạy đúng giờ. Đăng ký lịch bằng <code>scripts\windows\register-tasks.ps1 -Register</code> sau khi cấu hình xong.</p>
      </section>
      <AiStatusSection />
    </>
  );
}
