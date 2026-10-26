/** Vietnamese labels for codes returned by the analysis API. Unknown codes are shown as-is. */
export const ACTION_LABEL: Record<string, string> = {
  buy_tranche: "Mua từng phần", hold: "Giữ nguyên", reduce: "Cân nhắc giảm", wait: "Chờ", insufficient_basis: "Chưa đủ cơ sở",
};
export const REASON_TEXT: Record<string, string> = {
  setup_incomplete: "Chưa hoàn tất hồ sơ tài chính và khảo sát rủi ro",
  outside_research_universe: "Mã ngoài danh sách nghiên cứu đã duyệt: vẫn theo dõi, không đề xuất mua mới",
  removed_from_universe: "Mã đã bị loại khỏi danh sách: ngừng đề xuất mua",
  valuation_unavailable: "Chưa có định giá", assumptions_not_approved: "Giả định định giá chưa được duyệt",
  zone_policy_missing: "Chưa có biên an toàn/tỷ lệ giải ngân trong giả định đã duyệt", price_missing: "Chưa có giá đã xác minh",
  analysis_gaps: "Gói phân tích còn thiếu dữ liệu", profile_reconfirm_required: "Hồ sơ cần xác nhận lại",
  risk_needs_confirmation: "Khảo sát có mâu thuẫn cần xác nhận", capital_not_ready: "Chưa có vốn phù hợp để đầu tư",
  price_above_buy_zone: "Giá trên vùng mua", price_above_up_scenario: "Giá trên kịch bản thuận lợi",
  capacity_blocks_increase: "Khả năng tài chính chưa cho phép tăng vốn cổ phiếu", buying_power_unknown: "Chưa xác nhận được tiền có thể mua",
  no_allocation_headroom: "Đã đạt tỷ trọng mục tiêu", post_trade_policy_violation: "Danh mục sau đề xuất vi phạm chính sách",
  below_buy_zone: "Giá dưới vùng mua theo giả định đã duyệt",
};
export const SCOPE_LABEL: Record<string, string> = {
  research: "Trong danh sách nghiên cứu", held_outside_universe: "Ngoài danh sách nghiên cứu", removed_stop_buy: "Đã loại khỏi danh sách",
};
const FLAG_TEXT: Record<string, string> = {
  universe_incomplete: "Danh sách nghiên cứu chưa hoàn tất", ai_not_configured: "Chưa bật AI: phần nhận định dùng số liệu đã kiểm chứng",
  ai_unavailable: "AI tạm không dùng được: phần nhận định dùng số liệu đã kiểm chứng",
};
export const NOTE_TEXT = (note: string) => FLAG_TEXT[note] ? FLAG_TEXT[note]
  : note.startsWith("market_provenance:") ? `Nguồn giá: ${note.split(":")[1] === "vnstock_adjusted" ? "Vnstock, giá đã điều chỉnh" : note.split(":")[1]}`
  : note.startsWith("price_missing:") ? `Chưa có giá đã xác minh cho ${note.split(":")[1]}: giá trị danh mục chưa đầy đủ`
  : note.startsWith("price_not_for_session:") ? `Giá của ${note.split(":")[1]} chưa cập nhật cho phiên này: chờ lần chạy sau` : note;
export const label = (map: Record<string, string>, code: string) => map[code] ?? code;
