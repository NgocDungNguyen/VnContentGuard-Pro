#  VnContentGuard Pro v5.0

**Hệ thống kiểm duyệt nội dung tiếng Việt bằng AI  Phiên bản đầy đủ tính năng**

[![Version](https://img.shields.io/badge/version-5.0.0-purple.svg)](https://github.com/NgocDungNguyen/VnContentGuard-Pro)
[![Tests](https://img.shields.io/badge/tests-96%2F96-brightgreen.svg)](tests/)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![Deploy](https://img.shields.io/badge/deploy-Render-46E3B7.svg)](https://vncontentguard-pro.onrender.com)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

> **v5.0:** Unified AI (70% API calls)  Structured scraping  YouTube & TikTok  Content overlay  SSE streaming  Community blocklist  Parental control

---

##  Tính năng chính (v5.0)

###  ARCH-01  Phân tích thống nhất (Unified Analysis)
Thay vì gọi AI 3-5 lần riêng lẻ, v5.0 dùng **1 lần gọi Gemini duy nhất** cho toàn bộ phân tích:
- Cảm xúc  Độc hại  Kiểm tra thực tế  Tóm tắt  Rủi ro  Bình luận
- Giảm 70-80% số lần gọi API  độ trễ từ 30-60s xuống còn 5-15s
- Endpoint: `POST /analyze/v5/unified`

###  Structured Scraping  Trích xuất thông minh
| Nền tảng | Trích xuất |
|----------|-----------|
| **Facebook** | Bài đăng, tác giả, bình luận, reaction/share |
| **Báo tiếng Việt** | Tiêu đề, tác giả, ngày đăng, nội dung, bình luận |
| **YouTube** | Tiêu đề, kênh, mô tả, bình luận + lượt thích |
| **TikTok** | Mô tả, tác giả, bình luận, like/share (K/M) |

###  Content Script Overlay (Feature 2.1)
- Floating badge điểm rủi ro trực tiếp trên trang web
- Tô đỏ bình luận độc hại với tooltip giải thích
- Kéo thả, thu gọn/mở rộng, dark mode tự động
- Tự động hiển thị sau mỗi lần quét

###  SSE Streaming (Feature 1.5)   Parental Control (Feature 4.2)
###  Community Blocklist (Feature 4.1)   Weekly Report (Feature 4.4)
###  Offline Mode (Feature 2.7)  500+ regex patterns tiếng Việt

---

##  Kiến trúc v5.0

```
Chrome Extension (Manifest V3)
 popup.js         UI, structured scraping, overlay controls
 background.js    Service worker, API calls, badge, notifications
 content.js       Floating overlay, comment highlights
 offline_analyzer.js  Offline fallback

FastAPI Backend (Render.com)
 POST /analyze/v5/unified    PRIMARY (ARCH-01)
 POST /analyze/v5/stream     SSE streaming fallback
 POST /analyze/v5            Regular fallback
 GET  /health  /api/stats  /api/blocklist

src/models/
 unified_analyzer.py      Single-pass Gemini (all 6 modules)
 sentiment_v5.py  toxicity_v5.py  fact_checker_v5.py
 source_analyzer_v5.py  risk_scorer_v5.py  article_summarizer_v5.py
 gemini_llm.py            APIKeyRotator (30 keys)
```

---

##  Bắt đầu nhanh

### Cài đặt

```bash
git clone https://github.com/NgocDungNguyen/VnContentGuard-Pro.git
cd VnContentGuard-Pro

python -m venv venv
venv\Scripts\activate         # Windows
# source venv/bin/activate    # Linux/Mac

pip install -r requirements.txt
cp .env.example .env          # Điền 30 Gemini keys + external API keys

python api.py
#  http://localhost:8000/docs
```

### Cài đặt Extension

1. `chrome://extensions/`  Bật **Developer mode**
2. **Load unpacked**  chọn thư mục `extension/`

---

##  Hiệu suất

| Chỉ số | v3 | v4 | **v5** |
|--------|----|----|--------|
| Cảm xúc | 90% | 90% | **90%** |
| Độc hại | 95% | 95% | **95%** |
| Số lần gọi AI | 5 | 4 | **1** (80%) |
| Độ trễ | 40s | 25s | **~8s** |
| Nền tảng | Báo/FB | Báo/FB | **FB/Báo/YT/TikTok** |
| Overlay on-page |  |  | **** |
| Offline mode |  |  | **** |

---

##  Biến môi trường

```bash
GEMINI_API_KEY_1=AIzaSy...   # đến GEMINI_API_KEY_30
GOOGLE_FACT_CHECK_API_KEY=AIzaSyC...
GOOGLE_PERSPECTIVE_API_KEY=AIzaSyC...
NEWSDATA_API_KEY=pub_...
```

---

##  Testing

```bash
pytest -v                          # 96 tests
pytest tests/test_toxicity_v5.py -v
```

---

##  Lịch sử phiên bản

### v5.0.0 (February 2026)  HIỆN TẠI
- ARCH-01 Unified single-pass Gemini (70-80% API calls)
- Structured scraping: Facebook, news, YouTube, TikTok
- Content Script Overlay  floating badge, comment highlights
- SSE Streaming, Community Blocklist, Parental Control
- Weekly Safety Report, Offline Mode (500+ regex)
- All 20 features 

### v4.0.0 (January 2026)
- Service worker (Manifest V3), scan history, auto-scan, dark mode

### v3.2.0 (February 2026)
- PhoBERT sentiment, 4-layer toxicity, multi-source fact-check, 96 tests

---

##  License

MIT License  see [LICENSE](LICENSE)

---

**Built with  for the Vietnamese community**  
**Status:**  Live at [vncontentguard-pro.onrender.com](https://vncontentguard-pro.onrender.com) | **Updated:** February 2026
