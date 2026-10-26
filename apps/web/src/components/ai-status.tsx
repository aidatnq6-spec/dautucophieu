"use client";
import { useEffect, useState } from "react";
import { ApiError, api } from "../lib/api";

type AiStatus = { key: { configured: boolean; hint: string | null };
  policy: { version: string; status: string; monthly_usd: string; models: string[] };
  spend: { month: string; used_usd: string; calls: number } };

const usd = (v: string) => Number(v).toLocaleString("vi-VN", { minimumFractionDigits: 4, maximumFractionDigits: 4 });

/** Read-only: what the server actually has (key presence, approved policy, this month's spend). Changes go through config/ai-policy.json. */
export function AiStatusSection() {
  const [s, setS] = useState<AiStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { api<AiStatus>("settings/ai").then(setS, (e) => setError(e instanceof ApiError ? e.failure.message : "Lỗi tải.")); }, []);
  return (
    <section className="surface" aria-label="AI">
      <h2>AI</h2>
      {error ? <p className="errors" role="alert">{error}</p> : !s ? <p className="muted fx-loading" role="status">Đang tải…</p> : <>
        <ul>
          <li>Key OpenRouter: {s.key.configured ? <strong>đã cấu hình ({s.key.hint})</strong> : <strong>chưa cấu hình</strong>}
            {!s.key.configured && <span className="muted"> (thêm OPENROUTER_API_KEY vào .env.local ở thư mục gốc rồi khởi động lại)</span>}</li>
          <li>Chính sách: <strong>{s.policy.status === "approved" ? "đã duyệt" : "chưa duyệt"}</strong> <span className="caption">({s.policy.version})</span></li>
          <li>Model được phép: {s.policy.models.length ? s.policy.models.join(", ") : "chưa có"}</li>
          <li>Đã dùng tháng {s.spend.month.slice(5)}/{s.spend.month.slice(0, 4)}: <strong>{usd(s.spend.used_usd)} / {Number(s.policy.monthly_usd).toLocaleString("vi-VN")} USD</strong>
            {" "}<span className="caption">({s.spend.calls} lượt gọi)</span></li>
        </ul>
        <p>Chỉ dùng cho tab Nhận định: AI đọc nội dung báo cáo vĩ mô, ngành công khai (ACBS, World Bank). Bản tin sau phiên dùng số liệu đã kiểm chứng, không gọi AI.</p>
        <p className="notice">Không gửi danh mục, mã đang nắm, danh sách theo dõi hay kết quả định giá cho AI. Đổi model hoặc ngân sách trong config/ai-policy.json.</p>
      </>}
    </section>
  );
}
