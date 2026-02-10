# VNCONTENTGUARD PRO — COMPLETE SYSTEM CONTEXT
# Paste this file into any new chat so the AI knows exactly what the system is and does.
# Last updated: February 10, 2026 | Version: 3.2.0

## PROJECT IDENTITY
- **Name:** VnContentGuard Pro
- **Purpose:** AI-powered Vietnamese content moderation Chrome Extension + backend
- **Repo:** https://github.com/NgocDungNguyen/VnContentGuard-Pro.git
- **Branch:** `v3-enhancement` (active dev), `main` (production)
- **Workspace:** `C:\Users\LucyS\Tox`
- **Language:** Python 3.10 (backend) + JavaScript (Chrome extension)

---

## TECH STACK

### Backend
- **Framework:** FastAPI + Uvicorn
- **AI Model:** Google Gemini 2.5 Flash Lite (`gemini-2.5-flash-lite`)
- **API Keys:** 30 Gemini keys via shared `APIKeyRotator` (env vars `GEMINI_API_KEY` through `GEMINI_API_KEY_30`)
- **External APIs:**
  - Google Fact Check Tools API (`GOOGLE_FACT_CHECK_API_KEY`)
  - Google Perspective API (`GOOGLE_PERSPECTIVE_API_KEY`) — auto-skipped for Vietnamese text (returns 400 for `vi`)
  - NewsData.io (`NEWSDATA_API_KEY`, 200 req/day)
  - GNews (`GNEWS_API_KEY`, 100 req/day)
- **Dependencies:** `fastapi`, `uvicorn`, `pydantic`, `google-genai`, `python-dotenv`, `beautifulsoup4`, `requests`, `gunicorn`
- **Config:** `.env` file (gitignored), `.render.yaml` for cloud deployment

### Frontend (Chrome Extension)
- **Manifest:** V3
- **Files:** `extension/manifest.json`, `popup.html`, `popup.js`, `style.css`, `icons/icon.png`
- **UI Language:** Fully Vietnamese
- **Permissions:** `activeTab`, `scripting`, `storage`
- **Supported sites:** Facebook, VnExpress, Dân Trí, Tuổi Trẻ (+ any page via content scraping)
- **API endpoints tried (in order):**
  1. `http://127.0.0.1:8000/analyze/v3` (local, 120s timeout)
  2. `https://vncontentguard-pro.onrender.com/analyze/v3` (cloud fallback, 30s timeout)

### Deployment
- **Cloud:** Render.com (PaaS)
- **Build:** `bash build.sh` → `pip install -r requirements.txt`
- **Start:** `uvicorn api:app --host 0.0.0.0 --port 8000`
- **Local:** `python api.py` → starts on `http://127.0.0.1:8000`

### Testing
- **Framework:** pytest
- **Tests:** 96 total (19 sentiment + 26 toxicity + 31 fact-checking + 20 risk-scorer)
- **Location:** `tests/` directory
- **Run:** `pytest -v`

---

## FILE STRUCTURE (30 files total, cleaned v3.2)

```
C:\Users\LucyS\Tox\
├── api.py                             # FastAPI server (768 lines) — MAIN ENTRY POINT
├── requirements.txt                   # Python dependencies (8 packages)
├── build.sh                           # Render deployment build script
├── .render.yaml                       # Render deployment config
├── .env                               # API keys (gitignored, 30 Gemini + 4 external)
├── .gitignore                         # venv/, __pycache__/, .env, etc.
├── README.md                          # Project documentation (Vietnamese)
│
├── src/
│   ├── __init__.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── gemini_llm.py             # APIKeyRotator + GeminiAgent (352 lines)
│   │   ├── sentiment.py              # v2 keyword-based sentiment (fallback)
│   │   ├── sentiment_v3.py           # v3 PhoBERT sentiment analysis
│   │   ├── toxicity.py               # v2 regex toxicity (fallback, used in v3 pipeline)
│   │   ├── toxicity_v3.py            # v3 4-layer toxicity detection
│   │   ├── fact_checker_v3.py        # v3 multi-source fact checking
│   │   ├── source_analyzer_v3.py     # Domain credibility (SSL/WHOIS/reputation)
│   │   ├── news_aggregator_v3.py     # NewsData.io/GNews cross-reference
│   │   ├── risk_scorer_v3.py         # v3 evidence-based risk scoring
│   │   └── article_summarizer_v3.py  # Gemini article summarization + cache
│   └── utils/
│       ├── __init__.py
│       ├── cache_manager.py           # In-memory TTL cache (24h default)
│       └── comment_filter.py          # Pre-filter comments into categories
│
├── tests/
│   ├── test_sentiment_v3.py           # 19 tests
│   ├── test_toxicity_v3.py            # 26 tests
│   ├── test_fact_checking_v3.py       # 31 tests
│   └── test_risk_scorer_v3.py         # 20 tests
│
└── extension/
    ├── manifest.json                  # Chrome Manifest V3
    ├── popup.html                     # UI layout (115 lines, all Vietnamese)
    ├── popup.js                       # Logic + rendering (1112 lines)
    ├── style.css                      # Styling (414 lines)
    └── icons/
        └── icon.png                   # Extension icon
```

---

## API ENDPOINTS

### `GET /health`
Returns `{"status": "🟢 VnContentGuard Pro Server is Running"}`

### `POST /analyze/full_scan` (v2, legacy)
- Input: `{ url, article_text, comments[] }`
- Uses: `GeminiAgent.check_fake_news()`, `SentimentAnalyzer`, `ToxicityAnalyzer`
- Returns: `{ fake_check, sentiment, toxicity }`

### `POST /analyze/v3` (v3.1, PRIMARY — used by Chrome extension)
- Input: `{ url, article_text, comments[] }`
- Pipeline (in order):
  1. **Article Summary** → `ArticleSummarizer.summarize()` (Gemini, cached per URL)
  2. **Sentiment v3** → `SentimentAnalyzerV3.analyze()` (PhoBERT or keyword fallback)
  3. **Toxicity v3** → `ToxicityAnalyzerV3.analyze()` (article body only, 4-layer)
  4. **Fact Check v3** → `FactCheckerV3.check()` (multi-source)
  5. **Risk Score v3** → `RiskScorerV3.score()` (weighted formula)
  6. **Comments Analysis** → `_analyze_comments_v31()` (filter + regex + batch Gemini)
- Returns:
```json
{
    "version": "3.1",
    "article_summary": { "summary": "...", "method": "gemini|fallback|cache", "cached": bool },
    "sentiment_v3": { "overall": "Positive|Negative|Neutral", "confidence": 0.0-1.0, "intensity": "Weak|Moderate|Strong", "method": "..." },
    "toxicity_v3": { "is_toxic": bool, "overall_score": 0.0-1.0, "severity": "Low|Medium|High|Critical", "categories": {}, "detection_layers": [] },
    "fact_check_v3": { "score": 0-100, "verdict": "Đã xác minh đúng|Có thể đúng|Chưa rõ|Có thể sai|Sai", "confidence": "Cao|Trung bình|Thấp", "evidence": [] },
    "risk_score_v3": { "risk_score": 0.0-100.0, "risk_level": "Low|Medium|High|Critical", "confidence": float, "risk_breakdown": {}, "warnings": [], "recommendations": [] },
    "comments_analysis": { "total": int, "toxic_count": int, "toxic_percentage": float, "toxic_comments": [], "details": [], "filter_stats": {}, "api_calls_saved": int },
    "url": "...",
    "cache_stats": { "size": int, "hits": int, "misses": int }
}
```

---

## COMPONENT DETAILS

### 1. APIKeyRotator (`gemini_llm.py`)
- Manages 30 Gemini API keys loaded from env vars
- Auto-rotates on 429 (quota exceeded)
- Daily reset at UTC midnight
- Tracks per-key request counts and exhausted keys
- **SHARED** — single instance used by: GeminiAgent, ArticleSummarizer, FactCheckerV3, batch comment analysis

### 2. ArticleSummarizer (`article_summarizer_v3.py`)
- Generates Vietnamese summaries via Gemini
- Caches summaries per URL (24h TTL via CacheManager)
- Fallback: first 200 chars of article text
- Returns `{"summary": str, "method": "gemini|fallback|cache", "cached": bool}`

### 3. SentimentAnalyzerV3 (`sentiment_v3.py`)
- **PhoBERT mode** (`use_phobert=True`): HuggingFace transformer model `wonrax/phobert-base-vietnamese-sentiment`
- **Fallback mode** (`use_phobert=False`): Uses `SentimentAnalyzer` (keyword-based from `sentiment.py`)
- Currently runs in **fallback mode** for faster startup
- Returns: `overall`, `confidence`, `intensity`, `dominant_emotion`, `emotions`
- popup.js maps English labels to Vietnamese: `sentLabelVi = {Positive:'Tích cực', Negative:'Tiêu cực', Neutral:'Trung lập'}`

### 4. ToxicityAnalyzerV3 (`toxicity_v3.py`)
- **4-layer detection pipeline:**
  1. **Regex** (`toxicity.py` ToxicityAnalyzer): 500+ Vietnamese toxic patterns, standalone word boundaries to avoid false positives (e.g., "biến" won't match "biến mất")
  2. **Detoxify** (`use_detoxify` flag): `multilingual_debiased` model — currently **disabled** for faster startup
  3. **Perspective API**: Google's toxicity scoring — **auto-skipped for Vietnamese** (API returns 400 for `vi` language)
  4. **Gemini**: Contextual analysis — not used for individual article analysis, only batch comments
- Returns: `is_toxic`, `overall_score`, `severity`, `categories`, `detection_layers`
- popup.js maps severity: `severityVi = {Low:'Thấp', Medium:'Trung bình', High:'Cao', Critical:'Nghiêm trọng', None:'Không'}`

### 5. FactCheckerV3 (`fact_checker_v3.py`)
- Multi-source verification:
  1. **SourceAnalyzer** (`source_analyzer_v3.py`): Domain age, SSL, WHOIS, reputation DB
  2. **Google Fact Check Tools API**: Official fact-check database
  3. **NewsData.io** (via `news_aggregator_v3.py`): Cross-reference with news sources
  4. **Gemini synthesis**: AI-powered evidence combination
- Verdicts returned in Vietnamese: "Đã xác minh đúng", "Có thể đúng", "Chưa rõ", "Có thể sai", "Sai"
- Confidence in Vietnamese: "Cao", "Trung bình", "Thấp"

### 6. SourceAnalyzer (`source_analyzer_v3.py`)
- Checks: domain reputation (trusted list like vnexpress.net), SSL certificate, domain age, suspicious patterns
- Verdicts in Vietnamese: "Đáng tin cậy", "Tương đối đáng tin", "Đáng ngờ", "Không đáng tin"
- Risk factors in Vietnamese: "Tên miền rất mới", "Không có chứng chỉ SSL hợp lệ", etc.

### 7. RiskScorerV3 (`risk_scorer_v3.py`)
- **Weighted formula:**
  - 40% Credibility (fact check score)
  - 25% Toxicity
  - 15% Sentiment negativity
  - 10% Source quality
  - 10% Manipulation patterns (caps lock, excessive punctuation, emotional language)
- Risk levels: Low (0-25), Medium (25-50), High (50-75), Critical (75-100)
- Evidence module names in Vietnamese: "Phân tích cảm xúc v3", "Phát hiện độc hại v3", "Kiểm tra thực tế v3", "Phân tích nguồn v3", "Phát hiện thao túng"
- Recommendations in Vietnamese based on risk level

### 8. CommentFilter (`comment_filter.py`)
- Pre-classifies comments into 4 categories (no API calls):
  - `obvious_toxic`: Matches known toxic regex patterns
  - `obvious_clean`: Matches positive patterns (cảm ơn, hay quá, etc.)
  - `spam`: Empty, too short, URL-only, repeated chars
  - `ambiguous`: Needs AI analysis
- Achieves ~73% filtering rate (only ~27% go to Gemini)
- Known false-positive fixes: standalone "biến" (not "biến mất"), "câm" (not "bị câm"), "tộc" (not "dân tộc")

### 9. CacheManager (`cache_manager.py`)
- In-memory dict-based cache with TTL (default 24h)
- Used by: ArticleSummarizer (per-URL summaries), batch comment analysis (per-URL+comments hash)
- Methods: `get()`, `set()`, `clear()`, `get_stats()`

### 10. Batch Comment Analysis (`_analyze_comments_v31()` in `api.py`)
- Pipeline:
  1. CommentFilter pre-classifies (saves 70%+ API calls)
  2. Regex-only check on ambiguous comments (catches more toxic without API)
  3. Remaining truly ambiguous → batch Gemini call (25 comments/chunk, 1 API call per chunk)
  4. Rate limit: 7s sleep between chunks
  5. Circuit breaker: if all keys exhausted, falls back to regex-only
  6. Results cached per URL+comments hash
- Gemini prompt includes article context for context-aware analysis
- Fallback: `_fallback_results()` uses regex-only (no Perspective/Gemini calls)

---

## CHROME EXTENSION WORKFLOW

### User Flow:
1. User navigates to a page (Facebook, VnExpress, etc.)
2. Clicks extension icon → popup.html opens
3. Clicks "QUÉT TRANG NÀY" → `chrome.scripting.executeScript` scrapes page
4. Confirmation dialog shows: URL, text preview, comment count
5. User clicks "Quét" → POST to `/analyze/v3`
6. Results rendered in popup with color-coded risk, Vietnamese labels
7. Results cached in `chrome.storage.local` per URL
8. Warning modal shown if risk_score ≥ 60 or toxic_percentage ≥ 40%

### Content Scraping (`scrapePageContent()` in popup.js):
- **Facebook:** `div[role="article"]` for posts, multiple strategies for comments (data-testid, aria-label, list items)
- **VnExpress/Dân Trí/Tuổi Trẻ:** `article`, `.article-content`, `.detail-content` selectors
- **Generic:** `article`, `main`, `[role="main"]` fallback
- Comments capped at 50 per scan

### Result Rendering (`renderResults()` in popup.js):
- Article summary card (if available)
- Risk score (gradient card with score/100)
- Sentiment (with Vietnamese label mapping)
- Toxicity (4-layer details, Vietnamese severity)
- Fact check (verdict, evidence list with Vietnamese labels)
- Comments analysis (toxic count, filter stats showing "Phát hiện nhanh / Gửi AI phân tích sâu")
- Warnings card (if any)
- Recommendations card (if any)

### Label Mappings in popup.js:
```javascript
sentLabelVi = { Positive:'Tích cực', Negative:'Tiêu cực', Neutral:'Trung lập' }
severityVi  = { Low:'Thấp', Medium:'Trung bình', High:'Cao', Critical:'Nghiêm trọng', None:'Không' }
verdictVi   = { // Only for v2 legacy, v3 returns Vietnamese directly }
detection layer map = { regex:'Regex', gemini:'Gemini AI', perspective:'Perspective API', detoxify:'Detoxify' }
```

---

## API KEY MANAGEMENT

### Gemini Keys (30 total):
- Env vars: `GEMINI_API_KEY`, `GEMINI_API_KEY_2` through `GEMINI_API_KEY_30`
- Rate limits: 10 RPM (requests per minute), 20 RPD (requests per day) per key
- Total capacity: ~600 requests/day
- Rotation: automatic on 429, daily reset at UTC midnight
- **Single shared `APIKeyRotator` instance** used by all components (prevents key burning)

### External API Keys:
- `GOOGLE_FACT_CHECK_API_KEY` — unlimited
- `GOOGLE_PERSPECTIVE_API_KEY` — 86,400 req/day (but skipped for Vietnamese)
- `NEWSDATA_API_KEY` — 200 req/day
- `GNEWS_API_KEY` — 100 req/day

---

## IMPORTANT DESIGN DECISIONS / KNOWN BEHAVIORS

1. **PhoBERT disabled by default** — `SentimentAnalyzerV3(use_phobert=False)` for faster startup. Uses keyword fallback.
2. **Detoxify disabled by default** — `ToxicityAnalyzerV3(use_detoxify=False)` for faster startup. Relies on regex + Perspective + Gemini layers.
3. **Perspective API skipped for Vietnamese** — returns 400 for `vi` language. Only used if text is English-only.
4. **Comments capped at 50** — `req.comments[:50]` in v3 endpoint.
5. **Batch Gemini uses 25 comments/chunk** — with 7s sleep between chunks for rate limiting.
6. **Circuit breaker** — if all 30 keys exhausted, batch analysis falls back to regex-only.
7. **Cache** — article summaries and batch results cached 24h. User can clear via "Xóa kết quả đã lưu" button.
8. **Auto port kill** — `kill_port(8000)` runs before server start on Windows.
9. **All user-facing strings are Vietnamese** — backend returns Vietnamese for fact check verdicts, confidence, source verdicts, risk evidence. Frontend maps remaining English values (sentiment labels, severity) to Vietnamese.
10. **v2 endpoint still exists** — `/analyze/full_scan` kept for backward compatibility but not used by extension.

---

## GIT STATUS

- **Branch:** `v3-enhancement`
- **Latest commit:** `69f90cc` — "v3.2: Clean up project - remove 20 unused files, update README"
- **Remote:** `origin/v3-enhancement` — up to date
- **Commit chain:** `9c9bc41` → `19f2b9a` → `c6ffa79` → `14955a2` → `3e9da69` → `69f90cc`

---

## HOW TO RUN

### Local Development:
```bash
cd C:\Users\LucyS\Tox
venv\Scripts\activate
python api.py
# Server starts on http://127.0.0.1:8000
# Takes ~10-15 seconds to initialize (loads all engines)
```

### Run Tests:
```bash
pytest -v                              # All 96 tests
pytest tests/test_sentiment_v3.py -v   # 19 tests
pytest tests/test_toxicity_v3.py -v    # 26 tests
```

### Load Extension:
1. Chrome → `chrome://extensions/` → Developer mode ON
2. "Load unpacked" → select `C:\Users\LucyS\Tox\extension\`

### Deploy:
```bash
git checkout main
git merge v3-enhancement
git push origin main
# Render auto-deploys from main branch
```
