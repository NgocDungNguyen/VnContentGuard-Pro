# Phụ lục 6: Dàn ý báo cáo kết quả thực hiện dự án (dự án kỹ thuật)

Đây là dàn ý và bảng dữ kiện lấy từ kho mã, không phải bản báo cáo. Theo Phụ lục 8 (mục 4, 5, 9), bản đầu tiên của báo cáo phải do học sinh tự viết. Nhóm viết phần chữ; AI chỉ được dùng sau đó để sửa ngữ pháp, cú pháp ở mức nhỏ và phải ghi nhận.

## Quy cách (bắt buộc)
- Tối đa 15 trang gồm bìa, phụ lục, tài liệu tham khảo. A4, lề trái 3 cm, các lề còn lại 2 cm.
- Times New Roman cỡ 13, cách dòng đơn, cách đoạn 3pt.
- Không ghi tên học sinh, giáo viên, trường, phường/xã. Không dùng logo trường. Không để tên máy/tên người dùng trong ảnh chụp màn hình.

## Cấu trúc theo Phụ lục 6 và tiêu chí Phụ lục 9

### Bìa
Tên dự án, lĩnh vực (Phần mềm hệ thống), loại dự án (kỹ thuật). Không có tên người, tên trường.

### 1. Vấn đề nghiên cứu (10 điểm)
Cần trả lời: Thực tế nào đòi hỏi dự án? Vấn đề cụ thể là gì? Giải pháp phải đạt tiêu chí nào (đo được)? Có ràng buộc, giới hạn nào?
Nhóm tự tìm số liệu thực tế (ví dụ khảo sát phụ huynh/học sinh, số liệu về nội dung độc hại tiếng Việt) và trích nguồn đã đọc trực tiếp. Không dùng AI sinh danh mục tài liệu tham khảo.
Gợi ý tiêu chí đo được: độ chính xác phát hiện, thời gian phản hồi, tỷ lệ báo nhầm, mức hoạt động khi mất mạng.

### 2. Thiết kế và phương pháp (15 điểm)
Cần trả lời: Đã xem xét những phương án nào (ví dụ chỉ dùng từ khóa/regex, dùng mô hình học máy riêng, dùng LLM)? Vì sao chọn phương án hiện tại? Nguyên mẫu gồm những thành phần nào?
Dữ kiện có trong kho mã (cần tự kiểm chứng lại trước khi viết):
- Tiện ích Chrome (Manifest V3, thư mục `extension/`: popup, background, content, chế độ ngoại tuyến `offline_analyzer.js`).
- Máy chủ FastAPI (`api.py`), các mô-đun phân tích trong `src/models/` (cảm xúc, độc hại, kiểm chứng thông tin, tóm tắt, chấm rủi ro, gộp một lượt gọi LLM trong `unified_analyzer.py`).
- Danh sách chặn cộng đồng, bộ lọc bình luận, kho phản hồi, chế độ phụ huynh/học sinh (`src/utils/`).
- Sơ đồ khối nên tự vẽ.

### 3. Thực hiện, chế tạo và kiểm tra (20 điểm)
Cần trả lời: Chế tạo thế nào? Kiểm tra trong những điều kiện nào (nền tảng khác nhau, mạng yếu/mất mạng, nhiều loại nội dung)? Số liệu cụ thể?
Số liệu phải do nhóm đo và có trong nhật ký. Hai điểm cần xác minh trước khi ghi vào báo cáo:
- README ghi "96 tests" nhưng thư mục `tests/` hiện có 4 tệp kiểm thử bản v7. Chạy `pytest` và ghi con số thật.
- Các con số "độ chính xác 90%/95%" và "độ trễ ~8s" trong README chưa thấy phương pháp đo. Chỉ dùng nếu nhóm có bộ dữ liệu mẫu và bảng kết quả gốc; nếu không, đo lại.

### 4. Kết luận, giới hạn, tác động
Nhóm tự viết kết luận từ số liệu của mình (Phụ lục 8 mục 10 cấm dùng AI sinh kết luận). Nêu giới hạn thật (phụ thuộc API Gemini, hạn mức khóa API, tiếng Việt lóng, báo nhầm). Tác động: trẻ em, phụ huynh, nhà trường.

### 5. Tài liệu tham khảo
Chỉ liệt kê tài liệu nhóm đã đọc. Có thể dùng AI để chỉnh định dạng danh mục (Phụ lục 8 mục 14), nhưng nhóm phải kiểm tra từng nguồn.

## Các điểm cần lưu ý về liêm chính
- Quyền riêng tư: dự án thu thập nội dung từ Facebook, YouTube, TikTok. Báo cáo cần nói rõ dữ liệu nào được gửi đi đâu (máy chủ, Gemini API), có lưu không, người dùng có đồng ý không.
- Khóa API: tuyệt đối không đưa khóa thật (`GEMINI_API_KEY_*`) vào báo cáo, ảnh chụp, hoặc kho mã.
- Thời gian nghiên cứu: README ghi một số phiên bản "tháng 1/2026". Quy chế yêu cầu không quá 12 tháng tính đến 31/01/2027 (tức bắt đầu từ 01/02/2026 trở đi). Cần xác nhận ngày bắt đầu thật.
