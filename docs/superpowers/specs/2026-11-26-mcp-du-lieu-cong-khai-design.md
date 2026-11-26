# MCP dữ liệu công khai cho Claude

Chủ sở hữu duyệt ngày 26/11/2026: nối Claude (Claude Code và Claude Desktop) với ứng dụng qua một MCP server chạy trên máy, chỉ đọc dữ liệu thị trường công khai.

## Phạm vi

- Server chạy qua stdio: `python -m investment_agent.mcp_server`. Không mở cổng mạng, không dùng API nội bộ `127.0.0.1:8000`, không đọc `.env.local`.
- Chỉ đọc tệp trong `data/` (hoặc `INVESTMENT_DATA_DIR`). Không ghi, không gọi nguồn ngoài, không chạy việc nền.
- Không bao giờ chạm Firestore hay bất kỳ dữ liệu cá nhân nào: sổ giao dịch, danh mục, giá vốn, danh sách theo dõi, luận điểm, định giá và giả định định giá của chủ sở hữu, kế hoạch mua, tài sản, tiền gửi, nhật ký. Một test kiểm tra mã nguồn của server chỉ nhập `investment_agent.market` và thư viện chuẩn.
- Không có công cụ liệt kê những mã đang có dữ liệu doanh nghiệp hay sự kiện: danh sách đó phản ánh các mã ứng dụng theo dõi. Mỗi lần gọi trả đúng một mã được hỏi.

## Công cụ

| Nhóm | Công cụ | Nguồn |
|---|---|---|
| Giá và chỉ số | `thong_tin_ma`: có niêm yết HOSE không, ngành ICB, thuộc VN30/VN100 | `hose-listing.json`, `industries.json`, `index-groups.json` |
| | `gia_ngay`: giá ngày của một mã hoặc `VNINDEX` | `prices/` |
| | `lich_su_gia`: giá đóng cửa dài hạn từ 2013: giá ĐÃ điều chỉnh của VNDirect (adClose) khi `price-history/` có mã đó, cuối tháng hoặc từng phiên (tối đa 800); nếu chưa có thì giá chưa điều chỉnh của `index-history/`; kèm các đợt thưởng, cổ tức cổ phiếu, phát hành trong khoảng | `price-history/`, `index-history/`, `fundamentals/` |
| | `dinh_gia_chi_so`: P/E, P/B của VN-Index, VN30 | `index-valuation/` |
| | `dinh_gia_ma`: vốn hoá, P/E, P/B, số cổ phiếu VNDirect công bố cho một mã, kèm ngày và quý lợi nhuận | `valuation-check/` (chỉ các trường của VNDirect) |
| Báo cáo tài chính | `bao_cao_tai_chinh`: các dòng BCTC theo quý hoặc năm, kèm `ten_dong` (tên VNDirect của từng dòng, `config/statement-line-names.json`) và `pham_vi` | `statements/`, `statements-financial/` |
| Quỹ mở | `quy_mo`: danh sách quỹ và NAV; một quỹ: hồ sơ, lịch sử NAV, danh mục công bố. Không trả điểm quỹ do ứng dụng tự chấm (`fund-scores.json`) | `fund-nav.json`, `fund-nav-history.json`, `fund-holdings.json` (Fmarket) |
| | `chi_so_tai_chinh`: chỉ số theo quý | `financial-ratios/` |
| | `eps_co_tuc`: EPS, lợi nhuận, vốn chủ, cổ tức, phát hành, số cổ phiếu lưu hành | `fundamentals/` |
| Doanh nghiệp | `su_kien_doanh_nghiep`, `co_dong_ban_lanh_dao`, `giao_dich_noi_bo` | `events/`, `company/`, `insider/` |
| Vĩ mô và thế giới | `danh_sach_vi_mo`, `chi_bao_vi_mo`, `chi_so_chau_a`, `gia_vang`, `gia_vang_lich_su` (giá mua theo ngày), `omo` | `macro/`, `gold-price.json`, `gold-price-history.json`, `omo.json` |

## Giá dài hạn đã điều chỉnh (26/11/2026)

- `price-history-sync` lưu `adClose` từng phiên từ 02/01/2013 của mọi mã trong danh sách HOSE (không chỉ mã theo dõi), mỗi mã một lần gọi, tải lại cả chuỗi vì VNDirect tính lại giá điều chỉnh sau mỗi đợt thưởng.
- Lịch 20:00: 60 mã mỗi tối, mã chưa có trước rồi mã cũ hơn 7 ngày; cả danh sách được làm mới trong khoảng một tuần. Trả về rỗng thì giữ dữ liệu cũ.

## Quy tắc trả lời

- Số giữ nguyên chuỗi như trong kho, kèm nguồn và thời điểm lấy. Không nội suy, không tính thêm.
- Tệp không lưu thời điểm lấy (P/E và P/B chỉ số, lịch sử giá vàng, OMO) thì trả `tep_cap_nhat_luc`: giờ ghi tệp gần nhất (UTC), là lúc ứng dụng ghi chứ không phải lúc nguồn công bố.
- Phạm vi (26/11/2026): `npat` của dữ liệu cơ bản là LNST công ty mẹ; `equity` ở mọi nơi gồm lợi ích cổ đông không kiểm soát, nên `eps_co_tuc` trả thêm `loi_ich_thieu_so` cùng kỳ và `chu_thich`.
- Thiếu thì trả `{"thieu": true, "ly_do": "…"}`, ví dụ "chưa có tệp" hoặc "mã không hợp lệ".
- Mã chứng khoán chỉ gồm chữ in hoa và số, 3–10 ký tự. Tên chỉ báo vĩ mô phải nằm trong danh sách đang có.

## Đăng ký

- Plugin `dautucophieu` (`plugins/dautucophieu/`, marketplace cục bộ ở `.claude-plugin/marketplace.json`) mang MCP server và là nơi đăng ký duy nhất; cài ở phạm vi User nên dùng được ở mọi thư mục, cả Claude Code lẫn tab Code của Claude Desktop.
- Cài: `claude plugin marketplace add D:/GitHub/dautucophieu` rồi `claude plugin install dautucophieu@dautucophieu --scope user`.
- Server không nhận biến môi trường nào, nên không có khóa hay token của ứng dụng.
- Không dùng connector từ xa của claude.ai, vì phải đưa ứng dụng ra internet.

## Lệnh tắt (chủ sở hữu duyệt 26/11/2026)

| Lệnh | Việc |
|---|---|
| `/dautu-ma <MÃ>` | Hồ sơ, giá 20 phiên, BCTC 4 quý và 3 năm, chỉ số, EPS, cổ tức, sự kiện, cổ đông, giao dịch nội bộ, mục thiếu, nguồn |
| `/dautu-sosanh <MÃ1> <MÃ2> …` | 2–4 mã cạnh nhau: ngành, giá, KQKD 3 năm, EPS, cổ tức, chỉ số chung; không xếp hạng nên mua mã nào |
| `/dautu-quy <QUỸ1> <QUỸ2> …` | 2–4 quỹ mở cạnh nhau: NAV, phí, lợi nhuận Fmarket công bố, NAV đầu–cuối trong kho, danh mục công bố và cổ phiếu cùng nắm; không xếp hạng, không dùng điểm quỹ của ứng dụng |
| `/dautu-thitruong` | VN-Index, P/E và P/B của VN-Index và VN30, châu Á, vàng, OMO |
| `/dautu-vimo [chủ đề]` | Chỉ báo vĩ mô theo chủ đề hoặc bộ mặc định, kèm trạng thái cập nhật |

Lệnh nào cũng: không đoán hay nội suy số, chỉ tính thay đổi từ hai số trong kho và ghi rõ hai kỳ dùng để tính, không khuyến nghị mua bán, không nhắc danh mục hay giá vốn.
