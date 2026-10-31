"use client";
import { useEffect, useState } from "react";
import { Save } from "lucide-react";
import { ApiError, api, requestId } from "../lib/api";
import { formatDecimal, formatRatio } from "../lib/format";

type Damodaran = { erp: string; erp_cds: string | null; rating: string | null; published: string | null };
type Capm = { version: number; rf: { value: string; date: string } | null; beta: { value: string; date: string | null } | null; erp: string | null;
  erp_source: "owner" | "damodaran" | null; owner_erp: string | null; damodaran: Damodaran | null;
  required_return: string; ke: string | null; reason: string | null };

const day = (iso: string | null) => (iso ? iso.split("-").reverse().join("/") : "");
const pct = (v: string) => `${v.replace(".", ",")}%`;

/** Ke = Rf + β × ERP as a sentence with each input and its date, against the owner's required return. */
function Formula({ c, market }: { c: Capm; market: boolean }) {
  if (!c.ke) return <p className="muted">Chưa tính được: {c.reason}.</p>;
  return <p><strong>Chi phí vốn chủ theo CAPM: {formatRatio(c.ke, 2)}</strong>
    <span className="caption"> = Rf {pct(c.rf!.value)} (TPCP 10 năm, {day(c.rf!.date)}) + β {market ? "1 (thị trường)" : `${formatDecimal(c.beta!.value, 2)} (VNDirect, ${day(c.beta!.date)})`}
      {" × "}ERP {pct(c.erp!)} ({c.erp_source === "owner" ? "bạn nhập" : `Damodaran, ${day(c.damodaran?.published ?? null)}`}) · lợi suất yêu cầu đang đặt {formatRatio(c.required_return, 1)}</span></p>;
}

/** Cài đặt: the equity risk premium (the owner's, else Damodaran's for Vietnam), and the market cost of equity it gives (β = 1). A hint, never applied. */
export function CapmSettings() {
  const [view, setView] = useState<Capm | null>(null);
  const [erp, setErp] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  // Fill the box only while it is still empty, so a late reload never wipes what the owner is typing.
  useEffect(() => { api<Capm>("fairvalue/capm").then((v) => { setView(v); setErp((typed) => typed || (v.owner_erp ?? "").replace(".", ",")); },
    (e) => setMessage(e instanceof ApiError ? e.failure.message : "Lỗi tải.")); }, []);
  async function save(value: string | null) {
    if (!view) return;
    try {
      const v = await api<Capm>("fairvalue/capm", { method: "PUT", body: { erp: value, expected_version: view.version, request_id: requestId() } });
      setView(v); setMessage(null); if (value === null) setErp("");
    } catch (e) { setMessage(e instanceof ApiError ? e.failure.message : "Lỗi lưu."); }
  }
  return (
    <section className="surface" aria-label="Gợi ý CAPM">
      <h2>Gợi ý lợi suất yêu cầu (CAPM)</h2>
      <p className="caption">Ke = lợi suất trái phiếu Chính phủ 10 năm + beta × phần bù rủi ro vốn cổ phần (ERP). ERP mặc định lấy từ bảng quốc gia của
        Damodaran (NYU Stern) cho Việt Nam, tự đọc lại hằng tuần; bạn nhập số riêng thì phần mềm dùng số của bạn. Chỉ để tham khảo khi đặt Lợi suất yêu cầu ở
        mục trên; phần mềm không tự đổi. Trang từng mã tính theo beta của mã.</p>
      {view && <Formula c={view} market />}
      {view?.damodaran ? <p className="caption" data-testid="erp-damodaran">Damodaran cho Việt Nam: ERP {pct(view.damodaran.erp)}
        {view.damodaran.rating ? ` (theo xếp hạng Moody's ${view.damodaran.rating})` : ""}
        {view.damodaran.erp_cds ? `; theo CDS ${pct(view.damodaran.erp_cds)}` : ""}; bảng cập nhật ngày {day(view.damodaran.published)}.</p>
        : view && <p className="caption">Chưa tải được bảng Damodaran; lịch chạy sau giờ đóng cửa sẽ thử lại.</p>}
      <div className="formgrid"><label className="field">Phần bù rủi ro vốn cổ phần, ERP (%) — để trống là dùng số Damodaran
        <input inputMode="decimal" value={erp} placeholder={view?.damodaran ? view.damodaran.erp.replace(".", ",") : "7,8"} disabled={!view}
          onChange={(e) => setErp(e.target.value)} /></label></div>
      <div className="actions"><button className="btn primary" disabled={!view || !erp.trim()} onClick={() => void save(erp.trim())}>
        <Save size={16} aria-hidden="true" />Lưu ERP</button>
        {view?.erp_source === "owner" && <button className="btn" onClick={() => void save(null)}>Dùng số Damodaran</button>}</div>
      {message && <p className="errors" role="alert">{message}</p>}
    </section>
  );
}

/** Ticker page: the cost of equity on this ticker's beta. */
export function CapmTicker({ symbol }: { symbol: string }) {
  const [view, setView] = useState<Capm | null>(null);
  useEffect(() => { api<Capm>(`fairvalue/capm/${encodeURIComponent(symbol)}`).then(setView, () => setView(null)); }, [symbol]);
  if (!view) return null;
  return <div aria-label={`CAPM ${symbol}`} role="group"><Formula c={view} market={false} /></div>;
}
