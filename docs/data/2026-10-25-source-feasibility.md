# Khảo sát khả thi nguồn dữ liệu — 25/10/2026

Ngày đánh giá theo Asia/Ho_Chi_Minh. Task 5: **partial** (đã đọc tài liệu công khai; chưa chạy audit dữ liệu thật). Gate A về nguồn: **chưa đạt**. Không có bằng chứng đủ 50 doanh nghiệp HOSE × 10 năm.

## Bằng chứng và giới hạn

Các thông tin bên dưới là tuyên bố trong tài liệu của nhà cung cấp, chưa phải kết quả đo endpoint bằng tài khoản được cấp quyền. Không đăng ký tài khoản, chấp thuận điều khoản, mua gói hoặc gửi dữ liệu cá nhân trong lượt khảo sát này.

| Nguồn | Quan sát từ tài liệu | Phần chưa xác minh |
| --- | --- | --- |
| [Vnstock Market](https://vnstocks.com/docs/vnstock/thi-truong-market) | Có `Market().equity(symbol).ohlcv(start=..., end=...)`; tài liệu mô tả giá cổ phiếu bằng nghìn đồng và đã điều chỉnh quyền. | Giá gốc độc lập, phương pháp/factor điều chỉnh, lịch phiên và lịch sử đủ theo từng doanh nghiệp. Không dùng giá điều chỉnh làm giá giao dịch thô. |
| [Vnstock Fundamental](https://vnstocks.com/docs/vnstock/co-ban-fundamental) | Có tài liệu truy xuất tài chính. | Chưa xác nhận 10 năm/40 quý, hợp nhất/thuyết minh, ngày công bố và mọi bản sửa qua mẫu thật. |
| [Vnstock Analytics](https://vnstocks.com/docs/vnstock/dinh-gia-analytics) | Có tài liệu định giá; trang [mục lục](https://vnstocks.com/docs/vnstock) mô tả P/E/P/B chỉ số. | Chưa có bằng chứng chuỗi P/E/P/B 10 năm của từng cổ phiếu, EPS TTM và số cổ phiếu đúng thời kỳ. Không suy độ phủ cổ phiếu từ ví dụ chỉ số. |
| [FiinQuant Pricing](https://fiinquant.vn/Pricing) | Bảng giá lịch sử nêu gói trải nghiệm 33 mã/1 năm; các gói khác có độ sâu lớn hơn. | Các bảng dữ liệu khác có độ sâu khác nhau. Chưa xác định gói đủ cả giá, tài chính, ratios, quyền, revisions; chưa xác minh giá thanh toán. |
| [FiinGroup Datafeed](https://dff.fiingroup.vn/ApiDataFeed?lang=vi-vn) | Lần đọc bằng công cụ web gặp HTTP 503. | Khả năng, điều khoản, phí và endpoint đều chưa kiểm tra. Đây là lỗi truy cập trong lượt này, không kết luận dịch vụ ngừng hoạt động. |

### Quyền dữ liệu và thời điểm hiệu lực

[Trang chủ Vnstock](https://vnstocks.com/) phân biệt quyền phần mềm với điều kiện dữ liệu từng nguồn. Cần xác định nguồn thực tế rồi kiểm tra quyền truy cập, lưu cục bộ, tính toán, gửi phần dẫn xuất cho AI và chia sẻ bản tin trong nhóm Telegram.

Trang [giấy phép Vnstock](https://vnstocks.com/policies/license) được truy xuất hiển thị `license-2026.11`, ngày công bố 31/10/2026 và hiệu lực 30/11/2026. Cả hai đều sau ngày đánh giá 25/10/2026. Vì bất nhất thời điểm này, **không coi phiên bản đó là điều khoản hiện hành hoặc bằng chứng được cấp quyền**. Cần bản có hiệu lực tại ngày sử dụng và quyền của tài khoản thực tế. Không lấy việc đọc được trang làm bằng chứng chấp thuận.

[Điều khoản FiinQuant](https://fiinquant.vn/Home/Privacy) đề cập tài khoản được cấp và việc chấp thuận điều khoản khi sử dụng. Chưa đối chiếu hợp đồng/gói của người dùng; không suy quyền tích hợp hay phân phối dữ liệu từ trang giá. Chưa có chi phí vận hành nào được xác nhận. Các số tiền rời trong hộp thanh toán không được dùng làm báo giá gói.

## Ma trận khả thi hiện tại

`documented` chỉ nghĩa là có mô tả; `unknown` là chưa có bằng chứng kiểm tra. Không trạng thái nào bên dưới tương đương `verified` trong audit.

| Yêu cầu | Vnstock | FiinQuant |
| --- | --- | --- |
| Giá lịch sử | documented, adjusted | documented, phụ thuộc gói |
| Giá gốc + adjustment factors | unknown | unknown |
| Tài chính 10 năm/40 quý mỗi mã | unknown | unknown |
| P/E/P/B cổ phiếu 10 năm đúng share basis | unknown | documented theo gói; chưa đo |
| Corporate actions đầy đủ | unknown | unknown |
| Thời điểm công bố + historical revisions | unknown | unknown |
| Identity xuyên chuyển sàn/mã | unknown | unknown |
| Quyền dùng cá nhân + lưu trữ + AI/Telegram | unknown | unknown |
| Chi phí và cập nhật lặp lại | unknown | unknown |

## Audit thật chưa chạy

Chưa có cấu hình nguồn được xác minh cho tiến trình này. Không đọc/in secrets để khảo sát. Không thêm adapter giả mang tên nguồn thật. `config/data-sources.example.json` giữ mọi nguồn disabled và mọi capability unknown; file này là mẫu khai báo, chưa có loader hay tác dụng kích hoạt runtime.

| Ca đại diện cần chọn từ danh sách ứng viên | Live result | Bằng chứng còn thiếu |
| --- | --- | --- |
| Ngân hàng | not_run | Quyền nguồn, request/response, kỳ tài chính, share basis |
| Phi tài chính | not_run | Như trên; raw/adjusted prices |
| Doanh nghiệp chu kỳ | not_run | Như trên; khoảng ratios không phù hợp |
| Bất động sản | not_run | Như trên; hợp nhất/thuyết minh |
| Doanh nghiệp chuyển sàn | not_run | Định danh xuyên sàn, sự kiện vốn và tính liên tục |

Đây là nhóm ca kiểm tra, chưa phải đề xuất hay phê duyệt danh sách nghiên cứu. Không ghi ticker hoặc kết quả giả vào live audit.

## Bước thực hiện tiếp

1. Xác nhận nguồn/gói thực tế và điều khoản có hiệu lực; lưu document ID, URI, ngày kiểm tra và phạm vi quyền. Giữ riêng quyền cá nhân, AI, Telegram và phân phối lại.
2. Chỉ triển khai adapter cho endpoint đã được phép; khóa phiên bản SDK sau kiểm tra tài liệu thực tế. Có test response giảm thông tin theo quyền nguồn.
3. Audit nhỏ các nhóm trên, đối chiếu tài liệu gốc và chạy cập nhật lặp lại; đo missing sessions, revisions, đơn vị, thời điểm, chi phí và quota. Dùng lịch thị trường thật, không dùng weekday fixture làm lịch HOSE.
4. Audit từng ứng viên trong toàn bộ 50 mã trước mở phân tích thật. Bản thiếu as-reported không đủ để xác nhận backtest.
5. Nếu cần trả phí, trình gói/phạm vi/chi phí cụ thể trước mua. Trong khi đó tiếp tục sổ cá nhân và fixture có nhãn theo kế hoạch; khóa khuyến nghị thật phụ thuộc nguồn chưa đạt.

## Kiểm chứng cục bộ trong lượt này

- Backend: 69 test PASS, gồm 25 test coverage.
- CLI `data-audit --fixtures`: xuất JSON và Markdown thành công; aggregate giữ `live_eligible=false`, số doanh nghiệp live đủ điều kiện bằng 0.
- Fixture sinh lịch ngày thường chỉ phục vụ kiểm tra logic. Không có test nào ở trên chứng minh độ phủ hoặc quyền dữ liệu thật.

## Cập nhật 25/10/2026 (chiều): Vnstock v5.0.1 so với yêu cầu

Đọc tài liệu [Market](https://vnstocks.com/docs/vnstock/thi-truong-market), [Fundamental](https://vnstocks.com/docs/vnstock/co-ban-fundamental) và [giấy phép](https://vnstocks.com/policies/license) (license-2026.11, công bố 24/10/2026, hiệu lực 30/11/2026, nên chưa áp dụng tại ngày đánh giá). Chưa cài thư viện và chưa gọi API.

| Yêu cầu thiết kế | Vnstock Community (miễn phí, có key) | Gói Mở rộng (trả phí) |
|---|---|---|
| Giá ngày ≥ 10 năm | **Không đạt**: giới hạn 2.920 ngày (khoảng 8 năm), tối đa 10.000 dòng | Tài liệu không nêu giới hạn khác cho ngày |
| Giá gốc tách khỏi giá điều chỉnh | **Không đạt**: chỉ có giá đã điều chỉnh quyền (nghìn đồng, làm tròn 2 số lẻ mặc định); `vci` và `kbs` điều chỉnh khác nhau | Như trên |
| BCTC 10 kỳ năm / 40 kỳ quý | **Không đạt**: 8 kỳ gần nhất mỗi lần gọi | Tất cả kỳ nguồn trả về |
| Ngày công bố, bản sửa (as-reported) | **Không có** trong tài liệu | Không có; chỉ có danh mục tài liệu `filing()` |
| Hợp nhất / riêng | Không có tham số | Phân biệt qua `filing(doc_type="financial_report")` |
| Cổ tức, sự kiện quyền | Không có phương thức | Chỉ qua `filing()` (nghị quyết…) |
| Chỉ số P/E, P/B | `ratio()` (sắp thay bằng `vnstock_quant`, dùng được đến 15/01/2027) | Như trên |
| Quyền dữ liệu | Giấy phép chỉ cho mục đích cá nhân/học tập/nghiên cứu; Vnstock **không chuyển giao quyền** với dữ liệu từ nguồn bên thứ ba (VCI, KBS…); người dùng tự xác định quyền lưu, hiển thị, chia sẻ theo điều khoản từng nguồn; không gói nào có quyền phân phối lại | Như trên |

**Kết luận:** Vnstock Community không đáp ứng yêu cầu 10 năm, giá gốc và dữ liệu đúng thời điểm công bố. Gói trả phí giải quyết độ sâu BCTC nhưng theo tài liệu vẫn thiếu giá gốc, ngày công bố và sự kiện quyền dạng có cấu trúc. Gate A về nguồn **vẫn chưa đạt**. Không viết adapter Vnstock cho đến khi chủ sở hữu chọn hướng, vì kế hoạch không cho tự hạ tiêu chí.

Các hướng để chủ sở hữu quyết định:

1. **Đánh giá FiinQuant / FiinGroup Datafeed** (trả phí): kiểm tra gói có giá gốc + hệ số điều chỉnh, 10 năm BCTC kèm ngày công bố, sự kiện quyền, quyền lưu cục bộ, và báo giá trước khi mua.
2. **Chạy chế độ hạn chế với Vnstock**: chỉ dữ liệu `latest_restated`, giá đã điều chỉnh, tối đa 8 năm. Ứng dụng phải gắn nhãn rõ và chặn mọi kết luận cần dữ liệu đúng thời điểm (backtest, "rẻ nhất 10 năm"). Đây là hạ tiêu chí so với thiết kế, nên cần chủ sở hữu duyệt rõ ràng.
3. **Tự thu thập từ nguồn công bố gốc** (BCTC trên HOSE và website doanh nghiệp) kết hợp nguồn giá: công sức lớn, cần kiểm tra điều khoản từng nguồn.
