# VNCONTENTGUARD PRO — COMPLETE SYSTEM CONTEXT
# Paste this file into any new chat so the AI knows exactly what the system is and does.
# Last updated: February 24, 2026 | Version: 7.0.0

## PROJECT IDENTITY
- **Name:** VnContentGuard Pro
- **Purpose:** AI-powered Vietnamese content moderation Chrome Extension + backend with unified structured analysis and self-learning feedback system
- **Repo:** https://github.com/NgocDungNguyen/VnContentGuard-Pro.git
- **Branch:** `V7-enhancement` (active dev), `v4-enhancement` (stable), `main` (production)
- **Workspace:** `C:\Users\LucyS\Tox`
- **Language:** Python 3.10 (backend) + JavaScript (Chrome extension)
- **Version:** 7.0.0

---

## TECH STACK

### Backend
- **Framework:** FastAPI + Uvicorn
- **AI Model (Primary):** Google Gemini 2.5 Flash (`gemini-2.5-flash`)
- **AI Model (Fallback):** Google Gemini 2.5 Flash Lite (`gemini-2.5-flash-lite`)
- **API Keys:** 30 Gemini keys via shared `APIKeyRotator` (env vars `GEMINI_API_KEY` through `GEMINI_API_KEY_30`)
- **External APIs:**
  - Google Fact Check Tools API (`GOOGLE_FACT_CHECK_API_KEY`)
  - Google Perspective API (`GOOGLE_PERSPECTIVE_API_KEY`) — auto-skipped for Vietnamese text (returns 400 for `vi`)
  - NewsData.io (`NEWSDATA_API_KEY`, 200 req/day)
  - GNews (`GNEWS_API_KEY`, 100 req/day)
- **Dependencies:** `fastapi`, `uvicorn`, `pydantic`, `google-genai`, `python-dotenv`, `beautifulsoup4`, `requests`, `gunicorn`
- **Config:** `.env` file (gitignored), `.render.yaml` for cloud deployment
- **Encoding fix:** `sys.stdout.reconfigure(encoding="utf-8")` at top of api.py for Windows CP1258 compatibility

### Frontend (Chrome Extension)
- **Manifest:** V3
- **Permissions:** `activeTab`, `tabs`, `scripting`, `storage`, `downloads`, `notifications`, `webNavigation`, `alarms`
- **UI Language:** Fully Vietnamese
- **Supported sites:** Facebook, VnExpress, Dân Trí, Tuổi Trẻ (+ any page via content scraping)
- **API endpoints tried (in order):**
  1. `http://127.0.0.1:8000/analyze/v3/stream` (SSE streaming, local) — fallback to regular
  2. `http://127.0.0.1:8000/analyze/v3` (local, 120s timeout)
  3. `https://vncontentguard-pro.onrender.com/analyze/v3` (cloud fallback, 30s timeout)

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

## FILE STRUCTURE

```
C:\Users\LucyS\Tox\
├── api.py                             # FastAPI server (~1066 lines) — MAIN ENTRY POINT
├── requirements.txt                   # Python dependencies
├── build.sh                           # Render deployment build script
├── .render.yaml                       # Render deployment config
├── .env                               # API keys (gitignored, 30 Gemini + 4 external)
├── .gitignore                         # venv/, __pycache__/, .env, etc.
├── README.md                          # Project documentation (Vietnamese)
├── SYSTEM_CONTEXT.md                  # This file — full system documentation
├── V4_UPGRADE_PLAN.md                 # Feature roadmap with status tracking
│
├── src/
│   ├── __init__.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── gemini_llm.py             # APIKeyRotator + GeminiAgent (352 lines)
│   │   ├── sentiment.py              # v2 keyword-based sentiment (fallback)
│   │   ├── sentiment_v4.py           # v4 PhoBERT sentiment analysis
│   │   ├── toxicity.py               # v2 regex toxicity (fallback, used in v3 pipeline)
│   │   ├── toxicity_v4.py            # v4 4-layer toxicity detection
│   │   ├── fact_checker_v4.py        # v4 multi-source fact checking
│   │   ├── source_analyzer_v4.py     # Domain credibility (SSL/WHOIS/reputation)
│   │   ├── news_aggregator_v4.py     # NewsData.io/GNews cross-reference
│   │   ├── risk_scorer_v4.py         # v4 evidence-based risk scoring
│   │   └── article_summarizer_v4.py  # Gemini article summarization + cache
│   └── utils/
│       ├── __init__.py
│       ├── cache_manager.py           # In-memory TTL cache (24h default)
│       ├── comment_filter.py          # Pre-filter comments into categories
│       ├── feedback_store.py          # User feedback storage + LEARNING ENGINE (v4.9)
│       └── blocklist.py               # Community blocklist manager (v4.9)
│
├── tests/
│   ├── test_sentiment_v4.py           # 19 tests
│   ├── test_toxicity_v4.py            # 26 tests
│   ├── test_fact_checking_v4.py       # 31 tests
│   └── test_risk_scorer_v4.py         # 20 tests
│
└── extension/
    ├── manifest.json                  # Chrome Manifest V3 (v4.9.0)
    ├── popup.html                     # UI layout (~220 lines, all Vietnamese)
    ├── popup.js                       # Logic + rendering (~1900 lines)
    ├── style.css                      # Styling (~800 lines)
    ├── background.js                  # Service worker (~650 lines)
    ├── offline_analyzer.js            # Offline regex analysis
    ├── warning.html                   # Content warning interstitial (v4.9)
    ├── block.html                     # Parental control block page (v4.9)
    ├── report.html                    # Weekly safety report page (v4.9)
    ├── report.js                      # Weekly report logic (v4.9)
    └── icons/
        └── icon.png                   # Extension icon
```

---

## API ENDPOINTS

### `GET /health`
Returns `{"status": "🟢 VnContentGuard Pro Server is Running"}`

### `GET /api/stats`
Returns system health, API key stats, cache stats, blocklist stats, version info.

### `POST /analyze/full_scan` (v2, legacy)
- Input: `{ url, article_text, comments[] }`
- Returns: `{ fake_check, sentiment, toxicity }`

### `POST /analyze/v3` (v4.9, PRIMARY — used by Chrome extension)
- Input: `{ url, article_text, comments[] }`
- Pipeline (in order):
  1. **Learning Context Load** → `feedback_store.get_learning_context(url)` — loads past user corrections for this domain
  2. **Article Summary** → `ArticleSummarizer.summarize()` (Gemini, cached per URL)
  3. **Sentiment v3** → `SentimentAnalyzerV4.analyze()` (PhoBERT or keyword fallback)
  4. **Toxicity v3** → `ToxicityAnalyzerV4.analyze()` (article body only, 4-layer)
  5. **Fact Check v3** → `FactCheckerV4.check()` (multi-source)
  6. **Risk Score v3** → `RiskScorerV4.score()` (weighted formula)
  7. **Comments Analysis** → `_analyze_comments_v31(learning_ctx)` (filter + regex + batch Gemini WITH learning context)
  8. **Blocklist Check** → `community_blocklist.is_blocked(url)` + report count
  9. **Domain Feedback** → `feedback_store.get_domain_feedback(url)` — accuracy stats
- Returns (extended v4.9):
```json
{
    "version": "4.9",
    "article_summary": { "summary": "...", "method": "gemini|fallback|cache", "cached": true },
    "sentiment_v4": { "overall": "Positive|Negative|Neutral", "confidence": 0.85, "intensity": "...", "method": "..." },
    "toxicity_v4": { "is_toxic": false, "overall_score": 0.1, "severity": "Low|Medium|High|Critical", "categories": {}, "detection_layers": [] },
    "fact_check_v4": { "score": 75, "verdict": "...", "evidence": [] },
    "risk_score_v4": { "risk_score": 35.0, "risk_level": "Low|Medium|High|Critical", "warnings": [], "recommendations": [] },
    "comments_analysis": { "total": 10, "toxic_count": 2, "toxic_percentage": 20.0, "toxic_comments": [], "filter_stats": {}, "api_calls_saved": 5 },
    "blocklist_info": { "is_blocked": false, "report_count": 0 },
    "domain_feedback": { "domain": "vnexpress.net", "total": 5, "positive": 4, "negative": 1, "accuracy": 80.0, "recent_corrections": [] },
    "learning_applied": true,
    "url": "...",
    "cache_stats": { "size": 10, "hits": 3, "misses": 7 }
}
```

### `POST /analyze/v3/stream` (v4.9, SSE STREAMING)
- Input: same as `/analyze/v3`
- Returns: `text/event-stream` (Server-Sent Events)
- Yields 6 modules progressively as they complete:
  - `event: module` → `{"type": "module", "module": "summary|sentiment|toxicity|fact_check|risk_score|comments", "data": {...}}`
  - `event: complete` → `{"type": "complete", "data": {full_result}}`
  - `event: error` → `{"type": "error", "message": "..."}`

### `POST /api/feedback`
- Input: `{ url, rating, correction, modules, scan_results }`
- Stores feedback + scan snapshot for learning
- Invalidates learning cache for immediate effect

### `POST /api/report` (v4.9)
- Input: `{ url, risk_score, reason }`
- Community report submission; auto-blocks domains with 5+ reports
- Returns: `{ status: "reported|already_blocked", report_count, domain }`

### `GET /api/blocklist` (v4.9)
- Returns: `{ blocklist: [domains...], count: int }`

### `GET /api/blocklist/check?url=` (v4.9)
- Returns: `{ is_blocked: bool, report_count: int, domain: str }`

### `GET /api/feedback/domain?url=` (v4.9)
- Returns: per-domain accuracy stats and recent corrections

---

## KEY COMPONENTS

### 1. APIKeyRotator (`gemini_llm.py`)
- Manages 30 Gemini API keys loaded from env vars
- Auto-rotates on 429 (quota exceeded)
- Daily reset at UTC midnight
- Tracks per-key request counts and exhausted keys
- **SHARED** — single instance used by: GeminiAgent, ArticleSummarizer, FactCheckerV4, batch comment analysis

### 2. ArticleSummarizer (`article_summarizer_v4.py`)
- Generates Vietnamese summaries via Gemini
- Caches summaries per URL (24h TTL via CacheManager)
- Fallback: first 200 chars of article text

### 3. SentimentAnalyzerV4 (`sentiment_v4.py`)
- Gemini-based Vietnamese sentiment analysis
- Returns: overall sentiment, confidence, intensity
- Fallback: keyword-based analysis via `sentiment.py`

### 4. ToxicityAnalyzerV4 (`toxicity_v4.py`)
- 4-layer detection pipeline: Regex → Gemini → Perspective API → Detoxify
- Vietnamese-optimized regex patterns (500+ toxic phrases)
- Returns: toxic/safe, severity, categories, detection layers used

### 5. FactCheckerV4 (`fact_checker_v4.py`)
- Multi-source verification: Google Fact Check API, NewsData.io, GNews, Gemini analysis
- Cross-references claims across sources
- Returns: credibility score 0-100, verdict, evidence list

### 6. RiskScorerV4 (`risk_scorer_v4.py`)
- Weighted formula combining all modules
- Components: fake_news (30%), toxicity (25%), sentiment (15%), source (15%), manipulation (15%)
- Returns: risk_score 0-100, risk_level, breakdown, warnings, recommendations

### 7. FeedbackStore (`feedback_store.py`) — LEARNING ENGINE (v4.9)
- **Purpose:** Makes AI actually learn from user corrections over time
- **Storage:** JSON file (`feedback_data.json`), thread-safe with threading.Lock
- **Key methods:**
  - `add_feedback(url, rating, correction, modules, scan_results)` — stores feedback + compressed scan snapshot
  - `get_learning_context(url, max_examples=5)` — generates a learning prompt string injected into Gemini prompts
    - Includes: domain-specific accuracy, recent user corrections, overall accuracy rate
    - Example output: `"USER FEEDBACK LEARNING: Domain vnexpress.net accuracy: 75% (12 feedback). Recent corrections: User said 'This article is satire, not misinformation'..."`
  - `get_domain_feedback(url)` — returns `{domain, total, positive, negative, accuracy, recent_corrections}`
  - `invalidate_cache()` — clears learning cache when new feedback arrives
  - `_compress_snapshot(scan_results)` — extracts essential fields for compact storage
- **How learning works:**
  1. User submits feedback (agree/disagree + correction text)
  2. Feedback + scan snapshot stored in `feedback_data.json`
  3. Next scan of same domain → `get_learning_context()` builds a prompt string from past corrections
  4. This string is injected into the Gemini prompt in `_try_batch_gemini()` as `learning_line`
  5. Gemini considers past user corrections when analyzing new content
  6. Over time, the system becomes more accurate for frequently-scanned domains

### 8. CommunityBlocklist (`blocklist.py`) — v4.9
- **Purpose:** Community-powered domain blocking
- **Storage:** JSON file (`blocklist_data.json`), thread-safe
- **Threshold:** 5 reports to auto-block a domain
- **Key methods:**
  - `add_report(url, risk_score, reason)` — adds report, auto-blocks at threshold
  - `get_blocklist()` — returns list of blocked domains
  - `is_blocked(url)` — checks if domain is blocked
  - `get_domain_report_count(url)` — report count for a domain
- **Max capacity:** 10,000 reports

### 9. Background Service Worker (`background.js`) — v4.9
- **Purpose:** Handles all API calls, survives popup close
- **Key features:**
  - Regular scan handler (POST to /analyze/v3)
  - SSE streaming scan handler (POST to /analyze/v3/stream with ReadableStream parsing)
  - Auto-scan on page navigation for supported domains (30-min cooldown)
  - Notification system: `chrome.notifications.create()` for risk >= 50
  - Community blocklist: refreshes every 6h, caches locally
  - Parental control: `webNavigation.onCompleted` intercepts, redirects to block.html
  - Content warning: redirects blocklisted URLs to warning.html
  - Weekly report: `chrome.alarms` every 7 days, compiles stats from scanHistory
  - Report submission to backend
  - Badge update with risk score color coding

### 10. Offline Analyzer (`offline_analyzer.js`)
- **Purpose:** Instant regex-based analysis while waiting for AI
- Shows immediate partial results, upgraded when AI finishes

---

## EXTENSION MESSAGE TYPES (popup ↔ background)

| Message Type | Direction | Purpose |
|---|---|---|
| `START_SCAN` | popup → bg | Regular scan request |
| `START_SCAN_STREAM` | popup → bg | SSE streaming scan request |
| `GET_SCAN_STATUS` | popup → bg | Poll for scan results |
| `CANCEL_SCAN` | popup → bg | Cancel in-progress scan |
| `SUBMIT_FEEDBACK` | popup → bg | Send user feedback to backend |
| `SUBMIT_REPORT` | popup → bg | Report page to community blocklist |
| `SET_AUTO_SCAN` | popup → bg | Toggle auto-scan on/off |
| `GET_AUTO_SCAN` | popup → bg | Get auto-scan state |
| `SET_PARENTAL_CONTROL` | popup → bg | Enable/disable parental control + PIN + threshold |
| `GET_PARENTAL_CONTROL` | popup → bg | Get parental control settings |
| `OPEN_WEEKLY_REPORT` | popup → bg | Open report.html in new tab |
| `CHECK_BLOCKLIST` | popup → bg | Check if current URL is blocklisted |

---

## FEATURE HISTORY

### v3.0–3.2 (Foundation)
- 4-layer toxicity detection
- Multi-source fact checking
- Weighted risk scoring
- Vietnamese regex patterns (500+ phrases)
- PhoBERT sentiment model integration
- Article summarization with caching
- Comment filtering + batch Gemini analysis
- 96 unit tests

### v4.0 (BUG-01 Fix + UX)
- Background service worker (popup survival)
- Scan history (20 entries, FIFO)
- Badge updates with risk score
- Dark mode toggle

### v4.5
- Export report (HTML with print-to-PDF)
- API stats dashboard
- Gemini 2.5 Flash upgrade (with Lite fallback)

### V7.0 Features (implemented, version = "7.0" internally)
- 1.3: Auto-scan toggle (supported domains, 30-min cooldown)
- 2.5: Comparison mode (side-by-side of 2 scanned pages)
- 2.7: Offline regex mode (instant partial results)
- 3.3: User feedback loop (agree/disagree + correction)

### v4.9 Features (current release)
- **1.5: SSE Streaming** — Server-Sent Events for progressive module rendering (6 modules yielded individually)
- **3.5: Notification System** — chrome.notifications for risk >= 50, notification history, click-to-open
- **4.1: Community Blocklist** — Report pages, shared blocklist (5+ reports = blocked), periodic refresh
- **4.2: Parental Control** — Auto-block high-risk pages, PIN protection (4-6 digits), configurable risk threshold slider
- **4.3: Browser Content Warning** — Interstitial warning.html for blocklisted/flagged domains, proceed/go-back/whitelist options
- **4.4: Weekly Safety Report** — chrome.alarms weekly, report.html with risk distribution, top domains, feedback accuracy
- **LEARNING SYSTEM** — FeedbackStore generates learning context from past corrections, injected into Gemini prompts. System improves accuracy over time per domain.

---

## IMPORTANT PATTERNS & CONVENTIONS

### Error Handling
- All Gemini calls wrapped in try/except with quota detection
- Fallback chain: Primary model → Fallback model → Error response
- API: returns `{"error": "..."}` with HTTP 500 on failure

### Caching
- `CacheManager` — in-memory TTL cache (24h default)
- Article summaries cached by URL
- Browser: results cached in `chrome.storage.local` per URL

### Vietnamese Text
- All UI strings in Vietnamese
- Regex patterns optimized for Vietnamese diacritics/tone marks
- Vietnamese sentiment labels: Tích cực/Tiêu cực/Trung lập
- Vietnamese risk labels: Thấp/Trung bình/Cao/Nguy hiểm

### Comments Analysis Pipeline
1. `comment_filter.py` pre-categorizes: obvious_toxic, obvious_clean, spam, needs_ai
2. Only `needs_ai` comments sent to Gemini (saves API calls)
3. Batch processing: 10 comments per Gemini call
4. Learning context injected into prompt for improved accuracy

### Security
- API keys in `.env` (gitignored)
- CORS configured for `*` (development), should restrict in production
- Parental control PIN stored in `chrome.storage.local` (plaintext — acceptable for browser extension)
- Blocklist reports rate-limited by design (one report per domain per session)

---

## KNOWN ISSUES & LIMITATIONS
1. Perspective API returns 400 for Vietnamese (`vi`) — auto-skipped
2. Free Gemini tier has 15 RPM per key — managed by 30-key rotation
3. Cloud deployment (Render) has cold start delay (~30s)
4. Facebook comment scraping depends on DOM structure — may break with FB updates
5. Parental control PIN is stored in plaintext (acceptable for browser extension context)
6. Blocklist uses JSON file — should migrate to database for production scale

---

## HOW TO CONTINUE DEVELOPMENT

### Start the backend locally:
```bash
cd C:\Users\LucyS\Tox
python api.py
# Server starts at http://127.0.0.1:8000
```

### Load the extension:
1. Open `chrome://extensions`
2. Enable "Developer mode"
3. Click "Load unpacked" → select `C:\Users\LucyS\Tox\extension`

### Run tests:
```bash
pytest -v
```

### Key files to edit:
- **Backend logic:** `api.py` (endpoints), `src/models/` (AI modules), `src/utils/` (utilities)
- **Extension UI:** `extension/popup.html` + `popup.js` + `style.css`
- **Extension background:** `extension/background.js` (service worker)
- **New pages:** `extension/warning.html`, `block.html`, `report.html`

### Git workflow:
```bash
git add -A
git commit -m "v4.9: [description]"
git push origin v4-enhancement
```
