# Thiết kế web app AI hỗ trợ đầu tư cổ phiếu Việt Nam

Ngày: 24/10/2026 · Múi giờ: Asia/Ho_Chi_Minh

Trạng thái: Đã được người dùng phê duyệt ngày 24/10/2026 để chuyển sang lập kế hoạch triển khai. Việc mua dịch vụ, đặt ngân sách AI và kích hoạt gửi bản tin thật vẫn theo các điều kiện cấu hình trong tài liệu.

## 1. Mục đích và cách đọc

Xây dựng bản thử nghiệm cá nhân giúp người thiếu thời gian và kiến thức đầu tư ra quyết định tích lũy cổ phiếu trong nhiều tháng đến nhiều năm. Ứng dụng kết nối hoàn cảnh tài chính, danh mục thực tế, phân tích vĩ mô, ngành, doanh nghiệp và định giá thành khuyến nghị có thể kiểm tra.

Các mục ghi **Đã chốt** phản ánh quyết định của người dùng. Các mục ghi **Đề xuất thiết kế** là lựa chọn của người soạn để tạo một đặc tả có thể lập kế hoạch; cần được xem xét khi duyệt tài liệu. Phê duyệt một phần trong trao đổi trước không phải phê duyệt toàn bộ tài liệu này.

Ghi nhận phê duyệt toàn tài liệu: người dùng đã yêu cầu “duyệt bản thiết kế này để chuyển sang lập kế hoạch triển khai”. Các đề xuất cụ thể trong tài liệu trở thành đường cơ sở của kế hoạch; giữ nguyên nhãn để truy vết nguồn quyết định. Những mục cố ý chưa ấn định, như nhà cung cấp dữ liệu, mô hình cụ thể và ngân sách AI, tiếp tục được giải quyết qua các điểm kiểm tra đã mô tả, không được tự coi là có quyền mua dịch vụ.

“Nhanh và chính xác” được chuyển thành tiêu chí: số liệu đúng theo nguồn và thời điểm; công thức nhất quán; căn cứ truy xuất được; tách sự kiện, giả định và nhận định; nêu rõ khi chưa đủ dữ liệu. Không có cam kết giao dịch luôn đúng hoặc bảo đảm lợi nhuận.

## 2. Phạm vi đã chốt

- Một người dùng cá nhân, chạy trên máy Windows; mở giao diện bằng trình duyệt.
- Nhập thủ công hồ sơ tài chính, giao dịch mua/bán, cổ tức và dòng tiền nộp/rút.
- Khảo sát 13 câu, mỗi câu 4 đáp án, phân loại 6 nhóm rủi ro.
- Xác định có phù hợp đầu tư cổ phiếu lúc này không, tỷ trọng vốn, ngành và doanh nghiệp nên xem xét, lý do và rủi ro.
- Phân tích theo triết lý doanh nghiệp chất lượng + tăng trưởng có căn cứ + biên an toàn; mô hình định giá phù hợp từng loại doanh nghiệp.
- Phạm vi nghiên cứu mục tiêu: 50 mã hiện niêm yết HOSE, tối thiểu 10 năm giá, tài chính và lịch sử P/E/P/B. Được nối lịch sử HNX/UPCoM của cùng doanh nghiệp trước khi chuyển sàn.
- Danh sách ban đầu và mọi lần thêm/loại/thay mã phải được người dùng duyệt. Giá và tài liệu của mã đã duyệt vẫn tự cập nhật.
- Chủ động rà soát sau mỗi phiên: giá, tỷ trọng, tổng hợp sự kiện, thay đổi đáng chú ý, cơ hội định giá và rủi ro.
- Lưu bản tin trong ứng dụng và gửi vào nhóm Telegram cấu hình bằng Bot Token, Group ID. Nội dung bao gồm tài sản, mã nắm giữ, tỷ trọng, lãi/lỗ, thị trường, cơ hội, cảnh báo.
- Chỉ khuyến nghị; người dùng tự đặt lệnh tại công ty chứng khoán.
- Next.js, TypeScript, Tailwind CSS, shadcn/ui, Lucide cho web; Firestore cho dữ liệu cá nhân; Python và kho cục bộ cho lịch sử/phân tích; Windows Task Scheduler cho tác vụ.
- OpenRouter làm cổng AI chính; tùy chọn mô hình theo nhóm tác vụ, có danh sách dự phòng được cho phép.
- Bố cục A làm trang tổng quan, bảng danh mục của B ngay dưới phần quyết định; C cho màn bản tin.

## 3. Ngoài phạm vi và các kết quả cần tránh

Không kết nối đặt lệnh, không tự giao dịch, không tích hợp tài khoản môi giới, không phục vụ nhiều khách hàng ở bản này. Không xây bảng giá thời gian thực, giao dịch phái sinh, margin hoặc chiến lược lướt sóng. Không huấn luyện/fine-tune mô hình ở bản đầu. Không mặc định đánh giá lại toàn bộ 50 doanh nghiệp bằng LLM sau mỗi phiên.

Cần tránh: lấp dữ liệu thiếu; gọi P/B thấp là chắc chắn rẻ; quy kết đạo đức lãnh đạo bằng suy luận thiếu bằng chứng; dùng dữ liệu tương lai trong định giá quá khứ; biến dữ liệu giả lập thành phân tích thật; sửa danh sách nghiên cứu hoặc ghi giao dịch khi người dùng chưa xác nhận; tính trùng cổ tức; gửi lặp bản tin; lộ khóa qua trình duyệt, Git hoặc nhật ký.

## 4. Hồ sơ tài chính và vốn có thể đầu tư

### 4.1 Dữ liệu đầu vào — đề xuất thiết kế

Thu nhập, chi tiêu thiết yếu, chi tiêu khác, độ ổn định thu nhập, người phụ thuộc; các khoản nợ và lịch trả; tiền/tài sản tài chính có thể phân bổ; quỹ dự phòng đã dành riêng; mục tiêu, số tiền và thời điểm sử dụng; khả năng trì hoãn mục tiêu; danh mục thực tế.

Lưu số tiền, đơn vị VND, ngày hiệu lực và ngày xác nhận. Mỗi khoản tài sản cần đánh dấu đã nằm trong sổ danh mục chưa để không cộng hai lần. Nhà ở/tài sản tiêu dùng và tài sản khó thanh khoản không mặc định thuộc mẫu số phân bổ.

**Đề xuất ranh giới khoản cần bảo vệ:** mặc định rà soát mọi khoản chi lớn và nghĩa vụ tài chính trong 12 tháng tới; người dùng nhập số tiền còn thiếu sau nguồn thu chắc chắn đã dành cho khoản đó và xác nhận tổng tiền phải tách. Chi thường xuyên đã được nguồn thu đáp ứng không bị trừ lại toàn bộ 12 tháng; mất thu nhập được xét qua quỹ dự phòng. Khoản quá 12 tháng vẫn phải tách nếu người dùng xác định cần bảo toàn vốn/không thể trì hoãn; khoản có ngày hoặc nguồn bù không chắc chắn phải xác nhận trước tính phân bổ. Không mặc định tiền dành cho mục tiêu sau 12 tháng đều được đầu tư cổ phiếu. Phần vốn dành cho từng mục tiêu chỉ được phép chịu rủi ro sau khi người dùng xác nhận thời gian và mức linh hoạt; ngoại lệ 90% tiếp tục phải xét khả năng kéo dài nhiều năm. Giao diện hiển thị danh sách khoản bị trừ, lý do, nguồn bù và tổng số để người dùng duyệt, không để AI tự quyết định mẫu số.

### 4.2 Mẫu số phân bổ — đã chốt

Tỷ trọng cổ phiếu tính trên vốn có thể đầu tư sau khi trừ quỹ dự phòng và nhu cầu chi tiêu sắp tới, bao gồm cổ phiếu hiện có theo giá thị trường.

**Đề xuất thiết kế:** giao diện hướng dẫn người dùng phân nhóm khoản tiền theo mục tiêu/ngày cần; không tự giả định mọi tiền gửi đều sẵn sàng đầu tư. Nghĩa vụ nợ đến hạn thuộc nhu cầu tiền tương ứng; không đồng thời trừ toàn bộ dư nợ và trừ lại lịch trả. Dư nợ còn lại được xét riêng trong sức chịu rủi ro.

Nếu vốn có thể đầu tư không dương: không tính tỷ trọng bằng phép chia; trả về chưa có vốn phù hợp để bổ sung cổ phiếu. Nếu khoản tiền dự phòng đang nằm trong cổ phiếu, cảnh báo thiếu dự phòng thanh khoản thay vì coi như đã bảo vệ được khoản đó.

Danh mục hiển thị riêng: tổng tài sản đã khai báo; vốn đầu tư theo dõi; cổ phiếu; tiền; khoản phải thu/chờ thanh toán. Giải thích mẫu số bên cạnh tỷ trọng.

## 5. Khảo sát rủi ro

### 5.1 Nội dung đã chấp nhận làm bản nháp

Một đáp án mỗi câu. A=1, B=2, C=3, D=4. Tổng 13–52. Nội dung dưới đây lưu đầy đủ để không phụ thuộc lịch sử hội thoại.

| Câu | Câu hỏi | A | B | C | D |
|---|---|---|---|---|---|
| 1 | Mục tiêu quan trọng nhất của khoản đầu tư? | Giữ an toàn vốn, lợi nhuận thứ yếu | Tăng đều, chấp nhận biến động nhỏ | Tăng dài hạn, chấp nhận giai đoạn giảm đáng kể | Tăng trưởng cao, chấp nhận biến động lớn và mất phần đáng kể vốn |
| 2 | Bao lâu nữa bắt đầu cần một phần đáng kể khoản tiền? | Dưới 1 năm | 1 đến dưới 3 năm | 3 đến dưới 5 năm | Từ 5 năm |
| 3 | Nếu đang giảm giá khi cần tiền, có thể trì hoãn bao lâu? | Không thể | Dưới 6 tháng | 6 tháng đến dưới 2 năm | Từ 2 năm |
| 4 | Thu nhập còn dư sau chi phí thiết yếu và trả nợ? | Không dư/thường thiếu | Dư thất thường | Dư phần lớn các tháng | Dư đều, vẫn dư nếu thu nhập giảm 20% |
| 5 | Độ ổn định thu nhập 12 tháng tới? | Gián đoạn/nguy cơ giảm đáng kể cao | Biến động khó đoán | Tương đối ổn định, khó thay thế | Ổn định, có nguồn khác/phương án thay thế khả thi |
| 6 | Quỹ dự phòng đủ chi thiết yếu và trả nợ bao lâu nếu mất thu nhập? | Dưới 3 tháng | 3 đến dưới 6 tháng | 6 đến dưới 12 tháng | Từ 12 tháng |
| 7 | Mất 30% khoản đầu tư, chưa phục hồi 2 năm, ảnh hưởng thế nào? | Thiếu sinh hoạt/trả nợ | Hoãn mục tiêu quan trọng | Giảm chi không thiết yếu/điều chỉnh mục tiêu phụ | Vẫn đáp ứng nghĩa vụ và mục tiêu quan trọng |
| 8 | Mức hiểu biết về cổ phiếu và rủi ro? | Chưa hiểu rõ lãi/lỗ | Biết giá tăng giảm, chưa rõ rủi ro doanh nghiệp/danh mục | Hiểu đa dạng hóa, rủi ro doanh nghiệp, biến động và mất vốn | Giải thích và đánh giá được ảnh hưởng đến danh mục |
| 9 | Trải nghiệm đầu tư biến động giá? | Chưa đầu tư | Có, chưa trải qua giảm trên 10% | Trải qua giảm trên 10%, chưa có kế hoạch rõ | Trải qua giảm trên 10%, đã đánh giá lại theo kế hoạch |
| 10 | Đầu tư 100 triệu, giảm bao nhiêu trong 1 năm khiến muốn giảm rủi ro dù chưa cần tiền? | Đến 5 triệu | Trên 5 đến 10 triệu | Trên 10 đến 20 triệu | Trên 20 triệu |
| 11 | Danh mục giảm 20% trong 3 tháng, chưa cần tiền, chưa có thông tin triển vọng xấu đi? | Muốn bán hết | Muốn bán bớt đáng kể | Có thể giữ sau khi kiểm tra căn cứ | Có thể giữ và xem xét mua thêm theo kế hoạch/giới hạn vốn |
| 12 | Cảm giác khi đầu tư dài hạn từ 5 năm nhưng có năm thua lỗ và biến động mạnh? | Ảnh hưởng rõ sinh hoạt/giấc ngủ | Lo nhiều, thường muốn giảm vốn | Khó chịu nhưng theo được kế hoạch | Chấp nhận nếu trong giới hạn và luận điểm còn phù hợp |
| 13 | Lựa chọn đánh đổi cho khoản tiền dài hạn? | Bảo toàn, tăng trưởng thấp | Rủi ro mất vốn nhỏ để tăng trưởng hơn | Rủi ro mất phần đáng kể vốn để tăng trưởng dài hạn cao | Rủi ro mất phần lớn vốn để theo đuổi tăng trưởng cao hơn nữa |

Lưu ý cho câu 6: không tính cổ phiếu/tài sản khó bán vào quỹ dự phòng. Câu 10 không phải giới hạn lỗ được bảo đảm. Câu 13 không mô tả lợi nhuận cam kết.

### 5.2 Điểm và tỷ trọng cơ sở

| Điểm | Nhóm | Cổ phiếu cơ sở |
|---|---|---:|
| 13–19 | Rất an toàn | 0% |
| 20–26 | Thận trọng | 10% |
| 27–33 | Thận trọng vừa phải | 25% |
| 34–40 | Cân bằng | 35% |
| 41–46 | Tăng trưởng | 50% |
| 47–52 | Tăng trưởng mạnh | 60% |

Tỷ trọng cơ sở đã chốt. Bộ câu hỏi và ngưỡng điểm là bản nháp đã chấp nhận về nội dung, chưa kiểm định tâm lý/hiệu quả đầu tư và không phải phương pháp TOPI. Khảo sát trộn mức sẵn lòng, năng lực tài chính, kiến thức và trải nghiệm; ứng dụng gọi kết quả là hồ sơ khảo sát tổng hợp, không coi tổng điểm là phép đo độc lập thuần túy về tâm lý rủi ro.

### 5.3 Kiểm tra bổ sung — đề xuất thiết kế

Giữ nhóm theo tổng điểm nhưng tách kết quả khả năng tài chính. Câu 4=A hoặc 7=A: chưa đề xuất tăng vốn, cần làm rõ thiếu hụt. Câu 6=A: rà soát dự phòng. Câu 2=A hoặc 3=A: tách khoản tiền cần sớm. Câu 10=A nhưng 11/13=D: hỏi xác nhận mâu thuẫn. Dữ liệu hồ sơ mâu thuẫn khảo sát: yêu cầu xác nhận trước đề xuất phân bổ.

Không ép người mới nhận nhóm cao bằng cách coi kiến thức nhiều là muốn chịu lỗ nhiều. Cho phép xem lại câu trả lời, giữ phiên bản khảo sát, thời điểm và quy tắc chấm. Đề xuất nhắc xác nhận hồ sơ khi có thay đổi tài chính và trước rà soát tháng; quá hạn hoặc chưa đủ hồ sơ thì vẫn báo cáo tài sản nhưng không phát hành khuyến nghị cá nhân hóa mới.

## 6. Phân bổ và ngoại lệ

Đã chốt: có thể nâng trên tỷ trọng cơ sở nếu khả năng tài chính và cơ hội phù hợp. Riêng nhóm Tăng trưởng mạnh được xem xét tối đa 90% vốn có thể đầu tư vào danh mục cổ phiếu đa dạng. Phần vốn bổ sung chưa cần dùng tối thiểu 1 năm, đồng thời có thể kéo dài nắm giữ nhiều năm nếu cần; đây không phải thời hạn thu hồi vốn.

Các mức trần thông thường 0/15/30/45/60/70% từng được người soạn đề xuất nhưng chưa được người dùng chốt rõ. **Đề xuất cho bản đầu:** chưa tự tăng trên cơ sở ở năm nhóm đầu; nhóm Tăng trưởng mạnh chỉ đưa đề xuất ngoại lệ khi người dùng xác nhận đánh giá bổ sung. Không mặc định 70% là ngưỡng đã được duyệt. Hạ tỷ trọng vẫn được đề xuất khi khả năng tài chính hoặc luận điểm không còn phù hợp.

### 6.1 Điều kiện ngoại lệ — đề xuất để kiểm chứng

Để tránh tạo ngưỡng mang vẻ chính xác khi chưa kiểm định, ứng dụng chưa tự động cấp quyền ngoại lệ chỉ bằng một điểm số. Hồ sơ đánh giá phải có: quỹ dự phòng mục tiêu được xác nhận và đã tách; dòng tiền/nhu cầu tiền được cập nhật; không dùng tiền vay; khả năng kéo dài nắm giữ được giải thích bằng mục tiêu và nguồn tiền thay thế; xác nhận các kịch bản giảm giá; các cơ hội đạt tiêu chí và danh mục đa dạng.

Đề xuất giới hạn thử nghiệm: tối thiểu 8 mã thuộc ít nhất 4 nhóm ngành; mỗi doanh nghiệp tối đa 15% vốn có thể đầu tư; một ngành tối đa 30%; cộng gộp các mã cùng nhóm kiểm soát khi đánh giá tập trung. Chỉ là ngưỡng chính sách ban đầu cần duyệt/kiểm chứng, không bảo đảm đa dạng hóa đủ. Không cho phép dùng chúng để vượt tỷ trọng 90%.

Trình bày các kịch bản phần cổ phiếu giảm 30%, 50%, 60%, ảnh hưởng lên toàn vốn và mục tiêu cá nhân; không gọi đó là mức lỗ tối đa. Đánh giá dựa trên cả dữ liệu và xác nhận người dùng, không chỉ ô “tôi chấp nhận”. Không xác nhận thì duy trì đề xuất ở mức cơ sở hoặc thấp hơn.

Giới hạn áp dụng cho khuyến nghị giao dịch mới. Nếu tỷ trọng vượt vì giá tăng, cảnh báo và đề xuất cách đưa về; không tự bán. Ngoại lệ được đánh giá lại ở kỳ tháng hoặc khi tài chính/sự kiện trọng yếu thay đổi. Việc có 90% cổ phiếu không có nghĩa phải giữ mức đó khi điều kiện mất hiệu lực.

## 7. Dữ liệu: hợp đồng chất lượng và điểm kiểm tra khả thi

### 7.1 Yêu cầu bắt buộc

50 mã hiện ở HOSE; ít nhất 10 năm lịch sử giá, tài chính và P/E/P/B. Chuỗi giá gồm giá gốc, dữ liệu điều chỉnh và phương pháp điều chỉnh. BCTC gồm báo cáo quý/năm, hợp nhất khi có, thuyết minh và các bản sửa. Dữ liệu phải có định danh doanh nghiệp xuyên chuyển sàn/mã.

**Đề xuất định nghĩa để triển khai:** 10 năm là khoảng lịch ít nhất 10 năm đến ngày dữ liệu gần nhất, không suy ra bằng số dòng. Yêu cầu tối thiểu 10 kỳ năm và 40 kỳ quý theo cấu trúc phù hợp của nguồn; dữ liệu tài chính đầu kỳ cần thêm nếu tính trung bình/TTM ở biên. Ngày ngừng giao dịch không sinh giá giả. Dữ liệu quý IV suy từ năm trừ 9 tháng phải gắn nhãn dẫn xuất.

P/E dùng giá và EPS TTM nhất quán; P/B dùng vốn chủ sở hữu thuộc cổ đông công ty mẹ và số cổ phiếu phù hợp, với phương pháp pha loãng/điều chỉnh được lưu phiên bản. Không dùng cổ phiếu lưu hành hiện tại cho mọi ngày quá khứ. EPS/vốn chủ sở hữu không dương hoặc không đủ dữ liệu: chỉ số không phù hợp, không xếp hạng “rẻ” bằng số âm. Các khoảng không hợp lệ được lưu rõ, không thay bằng 0.

Lưu song song chuỗi tính theo thông tin đã công bố tại thời điểm đó và chuỗi mới nhất đã hồi tố nếu nguồn cho phép. Khi không có lịch sử phiên bản/ngày công bố đủ tin cậy, không gắn nhãn chuỗi là “đã biết tại thời điểm đó” và không dùng nó để xác nhận hiệu quả kiểm thử lịch sử. Không dùng ngày tải thay cho ngày công bố mà không ghi nhận hạn chế.

### 7.2 Nguồn và ngân sách

Ưu tiên kiểm tra Vnstock và FiinQuant cho thử nghiệm cá nhân, đối chiếu tài liệu doanh nghiệp/sở giao dịch; Cục Thống kê và NHNN cho vĩ mô. FiinGroup API Datafeed/WiFeed là phương án mua nếu nguồn thử nghiệm không đáp ứng. Chưa chốt nhà cung cấp, quyền khai thác cụ thể, tổng phí hay khả năng đủ 50 mã × 10 năm.

Người dùng ban đầu mong miễn phí và sau đó chọn thử nghiệm cá nhân. Không coi ngân sách dữ liệu 0 đồng là đã chứng minh khả thi cho phạm vi cuối cùng. Không dùng giả định mua gói cá nhân sẽ được quyền phân phối lại khi phát triển thương mại.

**Điểm kiểm tra bắt buộc trước khuyến nghị thật:** kiểm tra độ phủ trên ứng viên đại diện các ngành, ngày công bố, sự kiện vốn, hạn mức, quyền sử dụng và chạy cập nhật lặp lại. Có báo cáo thiếu dữ liệu và chi phí. Nếu không đủ: trình phương án nguồn trả phí hoặc chờ bổ sung để người dùng quyết định; vẫn có thể xây giao diện và sổ danh mục với dữ liệu giả lập gắn nhãn, không tự giảm yêu cầu hoặc đưa số giả vào báo cáo thật.

### 7.3 Kiểm soát chất lượng

Kiểm tra đơn vị đồng/nghìn đồng, kỳ báo cáo, báo cáo riêng/hợp nhất, giá ngoài phạm vi, trùng kỳ, cân đối kế toán, số cổ phiếu, thay đổi bất thường và sửa dữ liệu. Lưu nguồn, tài liệu gốc/tham chiếu, kỳ số liệu, ngày công bố, ngày tải, phiên bản và dấu kiểm tra.

Không thay dữ liệu đã xác minh bằng kết quả trống. Dữ liệu mới cách ly khi bất thường; lần phân tích trước được giữ lại và đánh dấu cũ. Giá danh mục dùng giá mới nhất đã xác nhận, hiển thị từng ngày giá. Không có giá hiện tại thì báo định giá danh mục chưa đầy đủ, không ghi giá bằng 0. Tài chính cũ xét theo lịch báo cáo và lịch sử công bố, không áp một số ngày chung cho mọi loại dữ liệu.

## 8. Danh sách nghiên cứu và danh mục sở hữu

Danh sách nghiên cứu 50 mã khác danh mục thực nắm giữ. Phải cho phép ghi nhận mọi khoản đang sở hữu kể cả ngoài danh sách; vẫn hạch toán, tính tỷ trọng theo giá có thể xác minh, nhưng không tự tạo phân tích mua mới cho mã ngoài phạm vi.

Tiêu chí sơ bộ đã đề xuất, chưa chốt: khớp lệnh bình quân 6 tháng từ 5 tỷ/phiên, giao dịch ít nhất 90% phiên, vốn hóa từ 2.000 tỷ, đa dạng ngành, công bố có thể kiểm chứng; không dùng P/E/P/B thấp làm điều kiện đầu vào. Ngưỡng, chuẩn ngành và ngày hiệu lực sẽ là cấu hình, cần hiện trong đề xuất duyệt.

Đề xuất không ép hạn ngạch ngành; xếp ứng viên qua điều kiện dữ liệu trước, sau đó thanh khoản và đại diện ngành. Nếu không đủ 50 thì báo rõ, chưa kích hoạt danh sách chính thức đủ 50.

Luồng: tạo đề xuất có phiên bản → hiển thị mã thêm/loại, lý do và ảnh hưởng ngành → người dùng duyệt hoặc từ chối → áp dụng. Mã bị loại vẫn giữ dữ liệu và giao dịch; thay đổi trạng thái niêm yết không xóa quyền sở hữu. Khi rủi ro trọng yếu, ngừng khuyến nghị mua và cảnh báo, không tự thay mã.

## 9. Phân tích và định giá

Thứ tự: kiểm tra hồ sơ/vốn → bối cảnh vĩ mô → triển vọng ngành → chất lượng và quản trị doanh nghiệp → định giá → phù hợp danh mục. Vĩ mô dùng để xây kịch bản và tiến độ giải ngân, không làm tín hiệu tất tay.

| Nhóm | Mô hình chính đề xuất | Đối chiếu |
|---|---|---|
| Phi tài chính, dòng tiền dự báo được | DCF | P/E, EV/EBITDA của nhóm tương đồng |
| Ngân hàng | Thu nhập thặng dư | P/B gắn ROE/chất lượng tài sản; P/E |
| Cổ tức ổn định, phản ánh khả năng phân phối | Chiết khấu cổ tức | DCF/P/E |
| Bất động sản, khu công nghiệp | NAV điều chỉnh theo dự án/nghĩa vụ | Dòng tiền dự án, doanh nghiệp tương đồng |
| Doanh nghiệp chu kỳ | Dòng tiền/lợi nhuận chuẩn hóa chu kỳ | Bội số trên chỉ tiêu chuẩn hóa |

Mỗi mã có kịch bản bất lợi/cơ sở/thuận lợi; tăng trưởng, biên, tái đầu tư, chiết khấu, tăng trưởng dài hạn, pha loãng và nguồn giả định được lưu. Biên an toàn hiển thị bằng công thức rõ; không cố định một tỷ lệ cho mọi doanh nghiệp khi chưa kiểm chứng. Lịch sử P/E/P/B là đối chiếu, không tự động quyết định giá trị hợp lý. Không lấy trung bình cơ học khi mô hình chênh lớn.

Đề xuất bản đầu: giả định mô hình được người dùng duyệt trước khi kích hoạt vùng mua; AI có thể đề xuất thay đổi nhưng không âm thầm sửa. Khi không đủ dữ liệu dự án cho NAV hoặc đầu vào quan trọng cho DCF: hiển thị hạn chế và chưa có vùng mua đã xác nhận, thay vì dùng mô hình không phù hợp để ép ra con số.

Quản trị: lưu bằng chứng về kiểm toán, công bố, giao dịch bên liên quan, nội bộ, xử phạt và thay đổi lãnh đạo. Phân biệt quyết định chính thức, thông tin đang xác minh, phản hồi doanh nghiệp và đánh giá AI. Không tìm thấy vi phạm không được diễn đạt thành xác nhận chính trực.

Khuyến nghị có: hành động mua từng phần/giữ/giảm/chờ/chưa đủ cơ sở; vùng giá; vốn và số lượng ước tính phù hợp quy tắc giao dịch đang có hiệu lực; tỷ trọng trước/sau; căn cứ; nguồn; rủi ro; điều kiện vô hiệu/đánh giá lại; ngày giá và thời điểm phân tích. Tiền khả dụng, phí, thuế và thanh toán được kiểm tra trước đề xuất mua. Khuyến nghị không tự biến thành giao dịch.

## 10. Sổ giao dịch và hiệu quả đầu tư

### 10.1 Quy tắc đã chốt

Bình quân gia quyền di động. Mua: tổng giá vốn còn lại mới = giá vốn cũ + tiền mua + phí mua; chia số cổ phiếu mới. Bán: giá vốn xuất = số bán × giá vốn bình quân trước bán; lãi đã thực hiện = tiền bán − phí − thuế bán − giá vốn xuất. Bán không tự đổi giá vốn đơn vị của phần còn lại.

Cổ tức tiền mặt ghi thu nhập riêng, giữ nguyên giá vốn. Cổ tức cổ phiếu/thưởng cổ phiếu tăng số lượng, giữ nguyên tổng giá vốn và phân bổ lại đơn giá tại sự kiện thích hợp; tách quyền chờ nhận với cổ phiếu có thể giao dịch. Không ghi cổ phiếu thưởng là lợi nhuận tiền mặt.

### 10.2 Đề xuất triển khai

Một danh mục cá nhân gộp ở bản đầu. Nhập lịch sử theo thứ tự thời gian và thứ tự giao dịch trong ngày; nếu chỉ có vị thế hiện tại thì dùng bút toán số dư đầu kỳ gồm số lượng, tổng giá vốn, tiền và ngày bắt đầu, ghi rõ lãi đã thực hiện trước đó chưa biết. Không bịa lịch sử mua để lấp khoảng trống.

Mỗi bản ghi có ID, loại, ngày giao dịch, thời điểm/thứ tự, ngày thanh toán nếu có, mã, số lượng, giá, phí, thuế thực tế, số tiền, trạng thái và ghi chú. Dùng số nguyên VND và Decimal cho giá vốn/số lượng/tỷ lệ; lưu quy tắc làm tròn. Không gắn cứng thuế/phí dựa trên trí nhớ; người dùng nhập giá trị thực tế, bảng gợi ý sau này phải có ngày hiệu lực.

Phân biệt tiền kế toán, tiền chờ thanh toán và tiền có thể mua; lịch T+ và quy tắc lô phải được xác minh từ nguồn chính thức trước triển khai. Trong khi chưa có bộ quy tắc được xác minh, người dùng xác nhận tiền/số lượng khả dụng và khuyến nghị không giả định toàn bộ tiền bán dùng được ngay.

Quyền dự kiến và cổ tức thực nhận là hai trạng thái của cùng sự kiện, không hai lần thu nhập. Tại ngày không hưởng quyền theo quy tắc đã cấu hình, ghi khoản quyền/phải thu để không biến điều chỉnh giá thành khoản lỗ giả; khi thanh toán chuyển sang tiền/cổ phiếu thực, không ghi lợi nhuận lần hai. Chênh lệch cổ tức dự kiến/thực nhận được điều chỉnh và truy vết. Quyền mua, tách/gộp, chuyển mã được ghi như sự kiện riêng; trường hợp chưa hỗ trợ phải cảnh báo và chặn kết quả bị ảnh hưởng, không tự tính sai.

Sửa/xóa giao dịch bằng phiên bản thay thế/hủy có thể khôi phục; tính lại toàn bộ chuỗi sau ngày bị ảnh hưởng và lưu dấu vết. Chặn số lượng âm, bán vượt số lượng khả dụng, nhập trùng và ngày/thứ tự thiếu gây mơ hồ.

Lãi chưa thực hiện = giá trị thị trường của cổ phiếu có trong phép tính − giá vốn còn lại tương ứng. Tổng lãi đầu tư tuyệt đối = lãi đã thực hiện + lãi chưa thực hiện + thu nhập cổ tức ròng, tính nhất quán cả quyền/phải thu. Đối chiếu với tài sản cuối − tài sản đầu − nộp ròng. Không gọi chênh lệch tài sản do nộp tiền là lợi nhuận. Đề xuất hoãn TWR/XIRR đến khi dòng tiền và thời điểm đủ dữ liệu; hiển thị rõ hiệu quả tính từ ngày bắt đầu theo dõi.

## 11. Lịch tự động và bản tin

Sau mỗi phiên là yêu cầu đã chốt. **Giờ đề xuất:** bắt đầu 17:30 giờ Việt Nam vào ngày có phiên theo lịch thị trường, thử lại 18:30 và 20:00 nếu dữ liệu thiếu; không mặc định thứ Hai–thứ Sáu đều có phiên. Nếu nguồn cập nhật muộn, tạo bản tin trạng thái thiếu dữ liệu, không gọi giá cũ là giá phiên mới. Nếu máy tắt, chạy bù khi máy hoạt động trở lại, ghi rõ thời điểm và phiên được xử lý.

Rà soát tuần/tháng là lịch từng được đề xuất, chưa chốt rõ. Đề xuất giữ tổng hợp tuần vào phiên cuối tuần; rà soát đầy đủ tháng vào phiên cuối tháng, gồm xác nhận hồ sơ, phân bổ, ngành và luận điểm. Sự kiện trọng yếu phát hiện trong tác vụ ngày được đưa lên đầu bản tin. Bản đầu không cam kết giám sát tin tức liên tục trong phiên.

Luồng: lấy dữ liệu → xác minh chất lượng → chốt snapshot → tính danh mục/chỉ số/định giá liên quan → AI tổng hợp → kiểm tra kết quả → lưu → gửi Telegram. Chỉ phân tích lại doanh nghiệp có thay đổi hoặc đến kỳ rà soát, không gọi AI cho mọi mã mỗi ngày nếu không cần.

Nội dung gồm tổng vốn đầu tư theo dõi, tiền, cổ phiếu, từng mã/số lượng/giá vốn/giá/tỷ trọng/lãi lỗ; thay đổi so bản trước; sự kiện và nguồn; cơ hội; rủi ro; hành động đề xuất hoặc giữ nguyên/chưa đủ cơ sở. Phân biệt biến động giá trong phiên với hiệu quả sau dòng tiền. “Giá trị tài sản” trong bản tin mặc định là phạm vi danh mục đầu tư; không gửi thu nhập, nợ và quỹ dự phòng chi tiết vào nhóm nếu chưa được cấu hình riêng.

Telegram gửi dữ liệu tài chính cá nhân theo yêu cầu đã chốt; mọi thành viên nhóm cấu hình có thể đọc. Chia tin khi vượt giới hạn; gắn mã bản tin, số phần và ngày phiên. Thử gửi là hành động rõ ràng của người dùng. Gửi tự động bật sau khi xác nhận đích và nội dung mẫu.

Lưu trạng thái theo bản tin/đích/phần; chỉ retry lỗi có thể thử lại. Timeout không rõ đã gửi hay chưa cần trạng thái chưa xác định; không hứa exactly-once vì có thể Telegram đã nhận trước khi mất kết nối. Sửa bản tin không tự phát tán nhiều lần; gửi bản đính chính có phiên bản khi được cấu hình. Không thể gửi Telegram vẫn giữ bản tin trong ứng dụng. Không có LLM thì lưu số liệu kiểm chứng và trạng thái thiếu nhận định, không lấy nhận định cũ gắn ngày mới.

## 12. Giao diện và luồng sử dụng

Bố cục đã chọn: A quyết định trước; bảng B ngay bên dưới; C cho bản tin. Bản mẫu dùng dữ liệu giả lập, không phải mã sản phẩm và chưa được kiểm chứng đầy đủ trên trình duyệt bằng công cụ tự động.

Các màn đề xuất:

1. Thiết lập ban đầu: tài khoản cá nhân → cấu hình khóa phía máy chủ → hồ sơ → 13 câu → nhập số dư/giao dịch → xem chất lượng dữ liệu → duyệt danh sách nghiên cứu → cấu hình bản tin.
2. Tổng quan: kết luận, điều cần làm/lý do/rủi ro; vốn và tỷ trọng; bảng danh mục; cơ hội/cảnh báo; biểu đồ với chú thích dòng tiền; mở bằng chứng.
3. Hồ sơ & rủi ro: mục tiêu và tài chính, phiên bản khảo sát, cơ sở/giới hạn phân bổ, đánh giá ngoại lệ.
4. Danh mục & giao dịch: mua/bán/cổ tức/nộp/rút, quyền chờ nhận, sửa và đối chiếu sổ.
5. Nghiên cứu: vĩ mô, ngành, 50 mã, đề xuất thay đổi danh sách chờ duyệt, chi tiết doanh nghiệp/định giá/nguồn/giả định.
6. Bản tin: xem theo phiên, trạng thái dữ liệu và Telegram, bản đính chính.
7. Cài đặt: OpenRouter và mô hình theo tác vụ, giới hạn sử dụng, Telegram, lịch, nguồn dữ liệu, sao lưu và nhật ký lỗi.

Thông tin tài chính thiếu thì chỉ hiển thị phân tích chung; chưa có 50 mã thì hiển thị trạng thái thiết lập, không tạo cảm giác danh sách đã duyệt. Nhãn mua/giảm phải có chữ, không chỉ màu. Bảng hỗ trợ cuộn màn hình nhỏ, bàn phím, focus rõ; mặc định ưu tiên desktop Windows và hỗ trợ xem điện thoại khi có đường truy cập phù hợp. Không tự mở dịch vụ ra Internet.

## 13. Kiến trúc kỹ thuật

### 13.1 Thành phần

- Next.js/TypeScript/Tailwind/shadcn/Lucide chạy Node.js trên Windows, phục vụ trình duyệt qua localhost.
- Firestore lưu dữ liệu cá nhân có cấu trúc: hồ sơ, khảo sát, giao dịch gốc, phê duyệt danh sách, khuyến nghị, bản tin, cấu hình không chứa bí mật.
- Python xử lý nguồn, công thức, định giá, quy tắc, gọi OpenRouter và Telegram.
- SQLite giữ catalog thị trường, metadata nguồn, bản ghi tác vụ và kết quả phân tích cục bộ; Parquet giữ chuỗi bảng lịch sử; tài liệu gốc lưu thư mục có manifest khi quyền nguồn cho phép.
- Task Scheduler chạy Python độc lập với trình duyệt/Next.js. Máy tắt hoặc ngủ thì tác vụ không chạy cho đến khi được khởi động/chạy bù.

### 13.2 Giao tiếp và nguồn sự thật — đề xuất thiết kế

Trình duyệt → Next.js phía máy chủ → dịch vụ Python FastAPI chỉ bind loopback, có token nội bộ. Tác vụ dài trả job ID, giao diện đọc tiến độ, không giữ một HTTP request suốt quá trình. Task Scheduler gọi cùng lớp nghiệp vụ Python; worker định kỳ không phụ thuộc Next.js đang mở.

Firestore là nguồn sự thật cho giao dịch/hồ sơ/phê duyệt; Python là chủ thể ghi nghiệp vụ để kiểm tra và tạo phiên bản. Trình duyệt không ghi thẳng các tổng tính toán. SQLite có snapshot cá nhân tối thiểu, quyền truy cập cục bộ và phiên bản để tính toán; không tạo hai sổ giao dịch độc lập. Mất Firestore: có thể đọc bản cache với nhãn cũ, chưa ghi giao dịch mới vào hàng đợi offline ở bản đầu. Không tạo khuyến nghị cá nhân hóa mới hoặc gửi bản tin cá nhân tự động nếu không xác minh được phiên bản hồ sơ/danh mục hiện tại.

Vì Firestore và kho cục bộ không có giao dịch nguyên tử chung, dùng job ID, snapshot/version và bước publish: chỉ công bố báo cáo hoàn chỉnh sau khi các đầu vào và kết quả đã lưu; retry không ghi lại nghiệp vụ. Khóa theo tác vụ, một worker ghi SQLite, transaction ngắn; không giữ khóa trong lúc chờ AI.

### 13.3 AI và bí mật

OpenRouter dùng key tạo trong tài khoản người dùng với credit của họ. Danh sách model đọc qua API, lọc khả năng theo tác vụ và lưu model ID cụ thể. Có mô hình bản tin, mô hình chuyên sâu, mô hình tương tác mặc định và fallback được duyệt; không dùng auto-routing không kiểm soát. Mô hình thiếu công cụ/structured output hoặc không đáp ứng chính sách dữ liệu thì không được dùng cho tác vụ đòi hỏi chúng.

Python cấp công cụ đọc dữ liệu/tính toán với phạm vi hữu hạn. Nội dung tài liệu, tin tức và phản hồi công cụ là dữ liệu không đáng tin để điều khiển hành động: không cho chúng thay hướng dẫn, lấy khóa, thực thi mã hoặc gửi tin. AI không được ghi sổ giao dịch, duyệt danh sách hay đặt lệnh. Kiểm tra schema, mã cổ phiếu, số liệu, nguồn và giới hạn trước publish; nếu lỗi thì thử sửa có giới hạn, sau đó trả chưa đủ cơ sở.

Nguồn bên ngoài và OpenRouter không mặc định được nhận toàn bộ hồ sơ. Chỉ gửi số liệu cần thiết, định danh tối thiểu, tắt logging nội dung tùy chọn và chọn provider theo chính sách dữ liệu; fallback không hạ yêu cầu riêng tư. Bản tin lưu model/provider thực tế, token, chi phí nếu có, prompt/schema version và input snapshot. Mô hình chưa được chọn cụ thể: cần chạy bộ đánh giá cùng dữ liệu thực trước đặt mặc định.

**Đề xuất chính sách gửi AI để người dùng duyệt:** được gửi tài liệu thị trường công khai có quyền sử dụng, mã cổ phiếu, tỷ trọng danh mục, tỷ lệ tài chính đã tính, nhóm rủi ro, khoảng thời gian và các cờ giới hạn. Không gửi tên, email, tài khoản, số tiền tài sản/thu nhập/nợ tuyệt đối, giá vốn cá nhân, toàn bộ lịch sử giao dịch hoặc tài liệu tài chính riêng. Python tính số tiền/số lượng đề xuất và chèn vào bản tin sau khi AI trả nhận định theo tỷ lệ; số cá nhân được gửi Telegram theo ủy quyền riêng đã chốt. Không gửi bí mật hoặc nội dung không cần thiết trong log lỗi.

Đề xuất yêu cầu tuyến AI không dùng đầu vào/đầu ra để huấn luyện và có chính sách zero-data-retention được nhà cung cấp công bố cho endpoint được chọn; tắt lưu nội dung prompt/output tùy chọn ở OpenRouter. Metadata vận hành/thanh toán tối thiểu có thể vẫn được giữ theo điều khoản dịch vụ, không mô tả là “không bên nào lưu gì”. Chỉ dùng endpoint đã kiểm tra đủ điều kiện; nếu mô hình mong muốn không có tuyến phù hợp thì báo không khả dụng theo chính sách, không tự chuyển sang tuyến lưu nội dung. Cần kiểm tra quyền tính năng theo gói OpenRouter tại thời điểm cấu hình. Nếu không đáp ứng được, tác vụ AI dừng, phép tính cục bộ và báo cáo số liệu vẫn hoạt động; thay đổi chính sách cần người dùng duyệt rõ.

Key OpenRouter, Bot Token, thông tin xác thực Firebase và token nội bộ nằm phía máy chủ/cục bộ; không dùng biến NEXT_PUBLIC cho bí mật, không lưu Firestore phía client, không log URL Telegram chứa token. Dùng .env cục bộ được Git bỏ qua và cơ chế bảo vệ bí mật Windows khi khả thi; chỉ hiển thị trạng thái/đuôi key. Cấu hình thử nghiệm không yêu cầu người dùng dán key vào hội thoại.

### 13.4 Truy cập, sao lưu và vận hành — đề xuất thiết kế

Firebase Authentication bằng tài khoản Google duy nhất có UID được cho phép. Next.js xác minh phiên cho mọi API cá nhân; backend dùng Admin SDK phải tự kiểm tra quyền, không dựa vào Firestore Rules vì Admin bỏ qua Rules. Client Firestore mặc định không được đọc/ghi dữ liệu ngoài phạm vi. Các endpoint thay đổi có kiểm tra origin/CSRF phù hợp; dịch vụ chỉ lắng nghe loopback. Đăng nhập cần Internet ở thiết lập đầu và khi làm mới phiên.

Tạo launcher Windows và lệnh kiểm tra môi trường; không bắt buộc Docker. Sao lưu có phiên bản SQLite, Parquet/manifest, tài liệu và xuất dữ liệu cá nhân bằng định dạng đọc lại được; không kèm key. Đề xuất chạy sau tác vụ thành công, giữ 7 bản ngày và 4 bản tuần; người dùng chọn nơi sao lưu, chưa tự đồng bộ lên dịch vụ khác. Phải thử khôi phục trước khi dùng sổ giao dịch thật.

Nhật ký có job ID, giai đoạn, thời gian, số bản ghi, lỗi và số lần thử; che nội dung nhạy cảm. Phân biệt lỗi nguồn, dữ liệu, Firebase, AI, Telegram. Có nút chạy lại từng giai đoạn an toàn, không xóa lịch sử khi lỗi.

## 14. Chi phí, hiệu năng và lộ trình kiểm chứng

Không chốt chi phí vận hành bằng 0. Hosting có thể dùng máy hiện có; điện/mạng không nằm trong dự toán. Firestore có quota nhưng cần đo thực tế. OpenRouter tính theo mô hình và phí credit hiện hành; 10 USD/tháng mới là đề xuất chưa được người dùng duyệt. **Đề xuất mặc định an toàn:** tắt gọi AI tính phí cho đến khi người dùng đặt ngân sách và xác nhận key; có giới hạn số request/token/job và ước tính trước khi chạy. Theo dõi chi phí thực tế khi có; không hứa chặn tuyệt đối ngân sách ở nhà cung cấp chỉ bằng bộ đếm cục bộ.

Dữ liệu dùng cache, cập nhật gia tăng và chỉ phân tích lại mã thay đổi. Có tiến độ tải lịch sử và phục hồi sau gián đoạn. Không đặt SLA chính xác trước khi thử máy Windows, nguồn dữ liệu và mô hình; đo thời gian giai đoạn để đặt mục tiêu sau.

Thứ tự kiểm chứng đề xuất: (1) khảo sát nguồn và chất lượng 10 năm; (2) sổ danh mục và công thức; (3) mẫu mô hình định giá theo nhóm; (4) AI dựa trên đầu vào đã kiểm chứng; (5) chu trình sau phiên và Telegram; (6) kiểm tra toàn bộ luồng trên Windows. Đây là thứ tự đánh giá thiết kế, chưa phải kế hoạch triển khai hay cho phép viết mã sản phẩm.

## 15. Điều kiện nghiệm thu bản thử nghiệm

- Hồ sơ và 13 câu tính đúng mọi biên điểm; hạn chế tài chính không bị tổng điểm cao vô hiệu.
- Bảng tỷ trọng đúng 0/10/25/35/50/60%; ngoại lệ không vượt 90% và không kích hoạt khi thiếu đánh giá.
- Sổ mua/bán, phí, thuế, cổ tức tiền/cổ phiếu, thứ tự trong ngày, số dư đầu và sửa lùi ngày tính lại đúng; đối chiếu được tài sản với dòng tiền, không lãi giả do nộp tiền/quyền cổ tức.
- Có báo cáo chứng minh nguồn, độ phủ và các khoảng không hợp lệ của 50 mã × 10 năm trước phân tích thật toàn phạm vi; thiếu phải chặn kết luận phụ thuộc.
- Chuyển sàn/sự kiện vốn không gây trùng mã, nhảy giá giả hoặc dùng số cổ phiếu sai kỳ; dữ liệu đã công bố đúng thời điểm được tách với dữ liệu hồi tố.
- Khuyến nghị có nguồn, giả định, mô hình, giới hạn vốn; không có giao dịch thật hay thay đổi danh sách khi chưa duyệt.
- Ngày nghỉ không báo thiếu phiên; lỗi mạng/máy tắt có trạng thái và chạy bù; tác vụ lặp không ghi trùng nghiệp vụ.
- Bản tin được lưu và gửi đúng nhóm đã xác nhận, có dữ liệu cá nhân theo cấu hình; lỗi/timeout có trạng thái, chia tin không mất phần.
- Đổi model hoặc fallback không đổi quy tắc tài chính, không hạ chính sách dữ liệu; từ chối phản hồi sai schema/thiếu bằng chứng.
- Khóa không xuất hiện trong bundle trình duyệt, Firestore client, Git hoặc log; tài khoản ngoài allowlist không truy cập dữ liệu.
- Khôi phục được bản sao lưu và chạy luồng từ nhập hồ sơ đến bản tin trên Windows.

Kiểm thử phải tập trung vào các bất biến tiền/số lượng, thời điểm dữ liệu, phân quyền và luồng thực; không coi việc mô hình viết văn bản trôi chảy là đạt chất lượng đầu tư. Kiểm thử hồi cứu nếu làm cần xử lý thiên lệch sống sót, dữ liệu tương lai và chi phí giao dịch; không dùng 50 mã chọn hôm nay để tuyên bố hiệu quả lịch sử toàn thị trường.

## 16. Các lựa chọn còn lại và quyền quyết định

### Đã được giao người xây dựng quyết định

Phiên bản dependency được hỗ trợ tại thời điểm triển khai, cấu trúc thư mục, schema/API chi tiết, thuật toán retry, kiểm thử, chia batch và tối ưu index. Không thay đổi công nghệ/nguồn trả phí/phạm vi đầu tư mà không trình rõ.

### Đề xuất của người soạn cần xem khi duyệt

- Chỉ định lượng nâng tỷ trọng đến 90% cho nhóm Tăng trưởng mạnh; năm nhóm khác giữ mức cơ sở làm giới hạn mua mới ở bản đầu cho đến khi có chính sách riêng.
- Ngoại lệ: đề xuất 8 mã/4 ngành, 15% mỗi doanh nghiệp, 30% mỗi ngành; chưa được kiểm chứng.
- Một danh mục cá nhân gộp; hỗ trợ số dư đầu kỳ; quyền/phải thu tách khỏi tiền khả dụng.
- Giả định định giá cần duyệt trước khi kích hoạt vùng mua.
- Lịch 17:30, thử lại 18:30/20:00; bổ sung tổng hợp tuần và rà soát tháng.
- Đăng nhập Google một tài khoản; Python FastAPI loopback; không ghi giao dịch offline khi mất Firestore.
- Tắt AI tính phí đến khi đặt ngân sách; chưa chốt 10 USD hay mô hình cụ thể.
- Điểm kiểm tra nguồn dữ liệu là điều kiện trước phân tích thật, không cam kết miễn phí.
- Rà soát chi lớn/nghĩa vụ 12 tháng, bảo vệ thêm các mục tiêu xa hơn không thể trì hoãn; người dùng xác nhận cụ thể khoản trừ và nguồn tiền bù trước tính vốn.
- AI chỉ nhận tỷ lệ, nhóm, thời gian và dữ liệu công khai; tiền/số lượng cá nhân được tính cục bộ. Tuyến AI không huấn luyện trên nội dung và đáp ứng chính sách zero-data-retention đã xác minh.

Không yêu cầu xác nhận từng chi tiết nhỏ riêng lẻ. Người dùng có thể duyệt toàn tài liệu kèm sửa các điểm trên; mọi đề xuất sẽ được ghi thành chính sách khi duyệt. Nếu dữ liệu không đáp ứng, cần quyết định mới về nguồn/chi phí, không coi duyệt thiết kế là đồng ý mua dịch vụ.

## 17. Nguồn tham khảo và hiện trạng

Các nguồn đã tham khảo trong quá trình khám phá; khả năng, giá và quyền sử dụng phải kiểm tra lại khi tích hợp:

- TOPI: https://topi.vn/topi-academy-unit-42-cach-thiet-lap-ho-so-rui-ro.html — tham khảo cấu trúc 13 câu/6 nhóm; không có công thức gốc được xác minh.
- FiinGroup API: https://dff.fiingroup.vn/ApiDataFeed?lang=vi-vn
- FiinQuant: https://fiinquant.vn/Pricing
- WiFeed: https://www.wigroup.vn/san-pham/wifeed
- Vnstock: https://vnstocks.com/ và https://vnstocks.com/policies/license
- Cục Thống kê: https://www.nso.gov.vn/px-web-2/
- NHNN: https://www.sbv.gov.vn/
- CFA về chất lượng báo cáo: https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/evaluating-quality-financial-reports
- Damodaran về doanh nghiệp tài chính: https://pages.stern.nyu.edu/~adamodar/pdfiles/papers/finfirm09.pdf
- Investor.gov: https://www.investor.gov/introduction-investing/getting-started/asset-allocation
- VNDIRECT: https://support.vndirect.com.vn/hc/vi/articles/12022173069977-FAQs-Sao-k%C3%AA-l%C3%A3i-l%E1%BB%97-%C4%91%C3%A3-th%E1%BB%B1c-hi%E1%BB%87n
- Next.js: https://nextjs.org/docs/app/guides/self-hosting
- Firestore: https://firebase.google.com/docs/firestore/pricing
- OpenRouter: https://openrouter.ai/pricing và https://openrouter.ai/docs/guides/routing/provider-selection và https://openrouter.ai/docs/guides/privacy/data-collection
- Telegram: https://core.telegram.org/bots/api

Hiện trạng: kho chưa có ứng dụng sản phẩm; chỉ có phác thảo HTML trong .superpowers/ được Git bỏ qua. Mẫu đã chọn: portfolio-approved-v2.html; dữ liệu giả lập, chưa kết nối dịch vụ thật. Phê duyệt tài liệu xong mới lập kế hoạch thực hiện theo skill writing-plans.

## 18. Kết quả rà soát tính đầy đủ

Đã thực hiện một lượt rà soát độc lập theo góc nhìn kỹ sư cần lập kế hoạch mà không hỏi lại người soạn. Rà soát nêu hai điểm quan trọng: phạm vi dữ liệu cá nhân gửi AI/chính sách provider chưa đủ cụ thể; ranh giới “chi tiêu sắp tới” chưa đủ rõ để tính vốn.

Đã bổ sung lựa chọn cụ thể tại mục 4.1 và 13.3, đánh dấu là đề xuất để người dùng xem xét thay vì coi đó là ý kiến đã được chốt trước. Người dùng có thể duyệt chúng cùng tài liệu hoặc yêu cầu thay đổi; chưa gửi dữ liệu hay cấu hình dịch vụ thật.

Các kiểm tra nội bộ bổ sung: rà lại toàn bộ điểm khảo sát và bảng tỷ trọng; phân biệt danh sách nghiên cứu với sở hữu thực tế; ghi rõ trần thông thường chưa duyệt; làm rõ nguồn sự thật giữa Firestore và SQLite, cổ tức/phải thu, sự kiện vốn, chạy bù và lỗi gửi chưa xác định; giữ gate dữ liệu 50 mã × 10 năm. Không chuyển vấn đề nguồn dữ liệu chưa kiểm chứng thành cam kết miễn phí hoặc cam kết đủ lịch sử.

Kết luận: đủ cấu trúc để lập kế hoạch sau khi người dùng duyệt các đề xuất ghi rõ. Tính khả thi về nguồn dữ liệu, chi phí và chất lượng mô hình vẫn cần được kiểm chứng trong công việc tiếp theo; rà soát tài liệu không thay thế kiểm tra API hay kiểm định chính sách đầu tư.
