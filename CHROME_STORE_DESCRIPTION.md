# VnContentGuard Pro V7.0 — Chrome Web Store Listing

---

## Extension Name
**VnContentGuard Pro**

## Short Description (132 chars max)
Quét an toàn nội dung tiếng Việt bằng AI — phân tích thống nhất, overlay trực quan, hỗ trợ YouTube & TikTok.

---

## Full Description

🛡️ **VnContentGuard Pro V7.0** — Hệ thống kiểm duyệt nội dung tiếng Việt thế hệ mới, được hỗ trợ bởi Gemini AI.

### ✨ Tính năng nổi bật

**⚡ Phân tích thống nhất (ARCH-01)**
Thay vì gọi AI 3-5 lần riêng lẻ, V7.0 chỉ dùng 1 lần gọi Gemini duy nhất — giảm 70-80% lượng API call, độ trễ từ 30-60 giây xuống còn 5-15 giây.

**🔍 Overlay trực tiếp trên trang**
Huy hiệu rủi ro nổi xuất hiện ngay trên trang web sau mỗi lần quét. Kéo thả được, thu gọn/mở rộng, hỗ trợ dark mode tự động. Tô đỏ bình luận độc hại với tooltip giải thích.

**📱 Hỗ trợ đa nền tảng**
- 📘 **Facebook** — bài đăng, bình luận, tác giả, reaction/share
- 📰 **Báo tiếng Việt** — VnExpress, Dân Trí, Tuổi Trẻ, Thanh Niên và nhiều hơn
- ▶️ **YouTube** — tiêu đề, kênh, mô tả, bình luận + lượt thích
- 🎵 **TikTok** — mô tả, tác giả, bình luận, like/share (K/M)

**🤖 Phân tích AI đa lớp**
- Cảm xúc cộng đồng (tích cực / tiêu cực / trung lập)
- Phát hiện độc hại (500+ pattern regex + Gemini AI)
- Kiểm chứng thực tế (Google Fact Check + NewsData.io)
- Điểm rủi ro tổng hợp 0-100
- Tóm tắt bài viết bằng AI

**🔒 Kiểm soát & Bảo vệ**
- 👨‍👩‍👧 Kiểm soát phụ huynh với mã PIN, tự động chặn nội dung nguy hiểm
- 🚫 Blocklist cộng đồng — chặn trang web được báo cáo nhiều lần
- ⚠️ Cảnh báo trình duyệt khi truy cập trang có rủi ro cao
- 📊 Báo cáo an toàn hàng tuần với thống kê chi tiết

**💡 Thêm tính năng**
- 🌙 Dark mode tự động
- ⚡ SSE Streaming — xem kết quả từng module theo thời gian thực
- 📡 Chế độ offline — 500+ regex pattern khi không có Internet
- 🔄 Tự động quét — phân tích trang ngay khi tải xong
- 📁 Lịch sử quét & xuất báo cáo JSON
- 🧠 Học từ phản hồi người dùng

### 🔑 Yêu cầu
Extension kết nối đến API server được host sẵn tại `vncontentguard-pro.onrender.com` — không cần cấu hình gì thêm.

### 🛡️ Quyền riêng tư
- Chỉ đọc nội dung trang khi bạn chủ động bấm "Quét"
- Không lưu trữ dữ liệu cá nhân
- Không theo dõi lịch sử duyệt web

---

## Version History

**V7.0.0** (February 2026) — Phiên bản hiện tại
- ARCH-01: Unified single-pass Gemini analysis
- Structured scraping: Facebook, news, YouTube, TikTok
- Content Script Overlay: floating badge, comment highlights
- All 20 planned features complete

**v4.0.0** (January 2026)
- Service worker (Manifest V3), scan history, auto-scan, dark mode

**v3.2.0** (January 2026)
- PhoBERT sentiment, 4-layer toxicity, multi-source fact-check

---

## Store Category
**Productivity** / **Privacy & Security**

## Tags / Keywords
an toàn nội dung, kiểm duyệt AI, fake news, tiếng Việt, Gemini, độc hại, phân tích, VnExpress, YouTube, TikTok, Facebook, overlay, parental control, blocklist

## Screenshots Needed
1. Main popup with scan results (risk score visible)
2. Content overlay badge on a news article page
3. Toxic comment highlighting on Facebook
4. Dark mode view
5. YouTube/TikTok scan results
6. Weekly safety report page
