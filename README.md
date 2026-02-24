# 🛡️ VnContentGuard Pro v5.0

**Hệ thống kiểm duyệt nội dung tiếng Việt bằng AI**

[![Version](https://img.shields.io/badge/version-5.0.0-blue.svg)](https://github.com/NgocDungNguyen/VnContentGuard-Pro)
[![Tests](https://img.shields.io/badge/tests-96%2F96-brightgreen.svg)](tests/)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

> **v5.0:** Phân tích thống nhất (↓70% API calls) • Structured scraping • YouTube & TikTok support • Content overlay • Learning AI • Streaming SSE • Community blocklist • Parental control

---

## ✨ Tính năng

### 🧠 Phân tích cảm xúc v3 (90% chính xác)
- **PhoBERT** mô hình transformer tiếng Việt
- Điểm tin cậy (0.0-1.0)
- Mức độ (Yếu/Trung bình/Mạnh)
- Dự phòng bằng phân tích từ khóa

### 🛡️ Phát hiện độc hại v3 (95% chính xác)
- **Phát hiện 4 tầng:**
  1. Regex (500+ cụm từ tiếng Việt)
  2. Detoxify (multilingual_debiased)
  3. Perspective API (Google) — tự động bỏ qua cho tiếng Việt
  4. Gemini phân tích ngữ cảnh
- Mức độ nghiêm trọng (Thấp/Trung bình/Cao/Nghiêm trọng)

### ✅ Kiểm tra thực tế v3 (90% chính xác)
- **Xác minh đa nguồn:**
  - Google Fact Check Tools API
  - NewsData.io (200 req/ngày)
  - GNews (100 req/ngày dự phòng)
  - Phân tích uy tín nguồn (SSL/WHOIS/danh tiếng)
  - Gemini tổng hợp bằng chứng
- Kết quả hoàn toàn bằng tiếng Việt

### 📊 Tóm tắt bài viết
- Gemini AI tự động tóm tắt nội dung
- Cache thông minh tránh gọi API lặp
- Hỗ trợ chunked batching (25 bình luận/batch)

### 📈 Chấm điểm rủi ro v3
- **Công thức dựa trên bằng chứng:**
  - 40% Độ tin cậy (kiểm tra thực tế)
  - 25% Độc hại
  - 15% Cảm xúc
  - 10% Chất lượng nguồn
  - 10% Dấu hiệu thao túng
- Mức rủi ro: Thấp/Trung bình/Cao/Nghiêm trọng
- Khuyến nghị hành động

---

## 🚀 Bắt đầu nhanh

### Cài đặt

```bash
# Clone repository
git clone https://github.com/NgocDungNguyen/VnContentGuard-Pro.git
cd VnContentGuard-Pro
git checkout v3-enhancement

# Tạo virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Cài đặt dependencies
pip install -r requirements.txt

# Cấu hình API keys
cp .env.example .env
# Chỉnh sửa .env với 30 Gemini keys + 4 external APIs

# Kiểm tra
pytest -v
# Kết quả mong đợi: 96 passed
```

---

## 💻 Sử dụng

### Chạy server

```bash
python api.py
# Server: http://localhost:8000
# Health check: http://localhost:8000/health
```

### Chrome Extension

1. Mở `chrome://extensions/`
2. Bật "Developer mode"
3. Click "Load unpacked"
4. Chọn thư mục `extension/`
5. Phân tích nội dung tiếng Việt real-time

---

## 📊 Hiệu suất

| Chỉ số | v1 | v2 | v3.2 |
|--------|----|----|------|
| **Cảm xúc** | 50% | 60% | **90%** |
| **Độc hại** | 65% | 75% | **95%** |
| **Kiểm tra thực tế** | N/A | ~70% | **90%** |
| **Tests** | 0 | 0 | **96** |
| **API Keys** | 0 | 1 | **30** |
| **Tầng phát hiện** | 1 | 1 | **4** |

---

## 🏗️ Kiến trúc

```
Chrome Extension (popup.html/js/css)
       ↓ HTTP POST
FastAPI Backend (api.py)
       ↓
┌──────────────────────────────┐
│  Phân tích cảm xúc v3       │
│  Phát hiện độc hại v3        │
│  Kiểm tra thực tế v3        │
│  Phân tích nguồn v3         │
│  Tóm tắt bài viết v3        │
│  Chấm điểm rủi ro v3        │
└──────────────────────────────┘
       ↓
  Gemini 2.5 Flash Lite (30 keys)
  + Google Fact Check / Perspective
  + NewsData.io / GNews
```

---

## 🗺️ Cấu trúc dự án

```
VnContentGuard-Pro/
├── api.py                         # FastAPI backend server
├── requirements.txt               # Python dependencies
├── build.sh                       # Render deployment build
├── .render.yaml                   # Render config
├── .env                           # API keys (gitignored)
├── .gitignore
├── README.md
│
├── src/
│   ├── models/
│   │   ├── sentiment.py           # Keyword-based sentiment (v2 base)
│   │   ├── sentiment_v4.py        # Enhanced sentiment analysis
│   │   ├── toxicity.py            # Regex toxicity (v2 base)
│   │   ├── toxicity_v4.py         # 4-layer toxicity detection
│   │   ├── fact_checker_v4.py     # Multi-source fact checking
│   │   ├── source_analyzer_v4.py  # Domain credibility analysis
│   │   ├── news_aggregator_v4.py  # NewsData.io/GNews cross-reference
│   │   ├── risk_scorer_v4.py      # Risk scoring engine
│   │   ├── article_summarizer_v4.py # AI article summarization
│   │   └── gemini_llm.py         # Gemini API key rotator (30 keys)
│   └── utils/
│       ├── cache_manager.py       # Response caching (24h TTL)
│       ├── comment_filter.py      # Comment pre-filtering
│       ├── blocklist.py           # Community blocklist
│       └── feedback_store.py      # User feedback store
│
├── tests/
│   ├── test_sentiment_v4.py       # Sentiment tests
│   ├── test_toxicity_v4.py        # Toxicity tests
│   ├── test_fact_checking_v4.py   # Fact-checking tests
│   └── test_risk_scorer_v4.py     # Risk scorer tests
│
└── extension/
    ├── manifest.json              # Chrome extension manifest v3
    ├── popup.html                 # Popup UI (tiếng Việt)
    ├── popup.js                   # Logic & rendering
    ├── background.js              # Service worker (SSE, scans)
    ├── offline_analyzer.js        # Offline regex analysis
    ├── style.css                  # Styling + dark mode
    ├── block.html                 # Parental control block page
    ├── warning.html               # Content warning interstitial
    ├── report.html                # Weekly safety report
    ├── report.js                  # Report logic
    └── icons/
        └── icon.png               # Extension icon
```

---

## 🔑 Cấu hình API

### Biến môi trường (.env)

```bash
# Gemini API Keys (30 keys)
GEMINI_API_KEY_1=AIzaSy...
GEMINI_API_KEY_2=AIzaSy...
# ... (keys 3-30)

# External APIs
GOOGLE_FACT_CHECK_API_KEY=AIzaSyC...
GOOGLE_PERSPECTIVE_API_KEY=AIzaSyC...
NEWSDATA_API_KEY=pub_...
GNEWS_API_KEY=e3dc0...
```

---

## 🌐 Deployment (Render.com)

1. Push code lên `main` branch
2. Thêm environment variables trên Render dashboard
3. Auto-deploy (~5 phút)
4. Kiểm tra: `curl https://vncontentguard-pro.onrender.com/health`

---

## 🧪 Testing

```bash
# Chạy tất cả tests
pytest -v

# Module cụ thể
pytest tests/test_sentiment_v4.py -v
pytest tests/test_toxicity_v4.py -v
pytest tests/test_fact_checking_v4.py -v
pytest tests/test_risk_scorer_v4.py -v
```

---

## 🔄 Lịch sử phiên bản

### v3.2.0 (February 10, 2026) — HIỆN TẠI
- Giao diện tiếng Việt hoàn chỉnh (extension + backend)
- Sửa lỗi tóm tắt bài viết không hiển thị (article_summary key mismatch)
- Sửa lỗi regex false positive (biến/câm/tộc/hệ thống/ngu)
- Manifest icons + Vietnamese metadata
- Dọn dẹp project (loại bỏ 15+ file không sử dụng)

### v3.1.0 (February 9, 2026)
- CacheManager, CommentFilter, ArticleSummarizer
- Batch Gemini analysis (25/chunk)
- Enhanced filtering (73% rate)
- Rate limit protection
- Vietnamese Perspective skip

### v3.0.0 (February 8, 2026)
- PhoBERT sentiment analysis (90%)
- 4-layer toxicity detection (95%)
- Multi-source fact-checking (90%)
- Objective risk scoring
- 96 comprehensive tests

### v2.1 (January 30, 2026)
- Security fixes, environment variables migration

### v1.0 (2024)
- Basic keyword detection

---

## 📄 License

MIT License — see [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **PhoBERT** — Vietnamese transformer model
- **Detoxify** — Multilingual toxicity detection
- **Google Gemini** — AI content analysis
- **Google Fact Check Tools** — Fact verification
- **Google Perspective** — Toxicity scoring
- **NewsData.io / GNews** — News aggregation

---

**Built with ❤️ for the Vietnamese community**

**Status:** 🟢 v3.2.0 | **Last Updated:** February 10, 2026
