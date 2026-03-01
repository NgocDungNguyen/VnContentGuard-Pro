# VnContentGuard Pro — Complete Project Documentation
**Version:** 6.0.0 | **Last Updated:** March 1, 2026 | **Status:** Production

---

## Table of Contents
1. [Project Overview](#1-project-overview)
2. [Tech Stack](#2-tech-stack)
3. [System Architecture & Workflow](#3-system-architecture--workflow)
   - 3.1 [High-Level Architecture](#31-high-level-architecture)
   - 3.2 [User-Side Workflow](#32-user-side-workflow)
   - 3.3 [Backend Processing Workflow](#33-backend-processing-workflow)
   - 3.4 [Data Flow Diagram](#34-data-flow-diagram)
   - 3.5 [Extension ↔ Backend Communication](#35-extension--backend-communication)
4. [File Structure](#4-file-structure)
5. [API Reference](#5-api-reference)
6. [Key Components Deep Dive](#6-key-components-deep-dive)
7. [Version History & Feature Comparison](#7-version-history--feature-comparison)
8. [Known Limitations](#8-known-limitations)
9. [Development Setup](#9-development-setup)

---

## 1. Project Overview

| Field | Value |
|---|---|
| **Full Name** | VnContentGuard Pro |
| **Type** | AI-powered Chrome Extension + FastAPI Cloud Backend |
| **Purpose** | Real-time Vietnamese content safety analysis — detects toxic language, misinformation, scam indicators, and risky content on social media and news sites |
| **Target Users** | Vietnamese Internet users, parents, educators, journalists, researchers |
| **Language** | Vietnamese (UI) + Python 3.10 (backend) + JavaScript (extension) |
| **Repository** | https://github.com/NgocDungNguyen/VnContentGuard-Pro.git |
| **Production Branch** | `main` |
| **Cloud Deployment** | Render.com — https://vncontentguard-pro.onrender.com |
| **Current Version** | 6.0.0 |
| **Test Coverage** | 96 automated tests (pytest) |
| **License** | MIT |

### What it does
When a user visits a Vietnamese news article, Facebook post, YouTube video, or TikTok page, a single click on the extension icon causes the system to:
1. Scrape structured content from the page (article body, author, reactions, comments)
2. Send it to the FastAPI cloud backend
3. Run a unified Gemini AI analysis in a single API call (v6 ARCH-01)
4. Return a comprehensive risk report: toxicity score, sentiment, fact-check rating, article summary, identified scam indicators, explainable AI evidence, and per-comment toxicity

---

## 2. Tech Stack

### 2.1 Backend

| Layer | Technology | Role |
|---|---|---|
| **Web Framework** | FastAPI 0.112+ | REST API endpoints, SSE streaming, CORS middleware |
| **ASGI Server** | Uvicorn (standard) | Async server; Gunicorn for production multi-worker |
| **Primary AI Model** | Google Gemini 2.5 Flash (`gemini-2.5-flash`) | All natural language understanding tasks |
| **Fallback AI Model** | Google Gemini 2.5 Flash Lite (`gemini-2.5-flash-lite`) | Auto-fallback on quota (429) |
| **AI SDK** | `google-genai >= 0.2.0` | Google Gemini API client |
| **Data Validation** | Pydantic 2.8+ | Request/response schemas |
| **Web Scraping** | BeautifulSoup4 4.12+ | HTML parsing for article content |
| **HTTP Client** | Requests 2.32+ / aiohttp 3.9+ | External API calls |
| **Domain Analysis** | python-whois 0.9+, validators 0.22+ | WHOIS lookups, URL validation |
| **Environment** | python-dotenv 1.0+ | `.env` file management |
| **Deployment** | Render.com (PaaS), `.render.yaml` | Cloud hosting, auto-deploy from git |

#### External APIs Used

| API | Purpose | Free Tier Limit |
|---|---|---|
| Google Gemini API (×30 keys) | Core AI analysis — all 6 modules | 10 RPM, 20 RPD per key → 600 RPD shared |
| Google Fact Check Tools API | Cross-reference claims against verified fact-checks | 10,000 req/day |
| Google Perspective API | Toxicity scoring (auto-skipped for Vietnamese — returns 400 on `vi`) | 1 QPS |
| NewsData.io | Cross-reference article claims against recent news | 200 req/day |
| GNews API | Secondary news cross-reference | 100 req/day |

#### API Key Management (APIKeyRotator)
- 30 Gemini API keys loaded from env vars `GEMINI_API_KEY_1` through `GEMINI_API_KEY_30`
- Rotates key on every 429 (quota exceeded) response
- Tracks per-key request count; skips exhausted keys
- Auto-resets daily counter at UTC midnight
- Single shared instance across all modules (prevents key burn)

### 2.2 Frontend (Chrome Extension)

| Layer | Technology | Role |
|---|---|---|
| **Manifest Version** | Chrome Manifest V3 | Extension packaging standard |
| **UI Language** | Vietnamese | All labels, messages, and reports |
| **Service Worker** | `background.js` | Survives popup close; handles all API calls |
| **UI Layer** | `popup.html` + `popup.js` + `style.css` | Main 600×580px popup interface |
| **Page Injection** | `content.js` + `content.css` | Floating overlay badges injected into web pages |
| **Offline Engine** | `offline_analyzer.js` | 500+ Vietnamese regex patterns for offline mode |
| **Storage** | `chrome.storage.local` / `.sync` | Scan history, settings, blocklist cache |
| **Permissions** | `activeTab`, `tabs`, `scripting`, `storage`, `notifications`, `webNavigation`, `alarms` | Full feature set |

### 2.3 Infrastructure

| Component | Technology |
|---|---|
| **Source Control** | Git + GitHub |
| **CI/CD** | Render auto-deploy on push to `main` |
| **Build Script** | `build.sh` → `pip install -r requirements.txt` |
| **Start Command** | `uvicorn api:app --host 0.0.0.0 --port 8000` |
| **Local Dev** | `python api.py` → http://127.0.0.1:8000 |
| **Testing** | pytest (96 tests across 4 test files) |

---

## 3. System Architecture & Workflow

### 3.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER'S BROWSER                           │
│                                                                 │
│  ┌───────────────────────┐    ┌──────────────────────────────┐  │
│  │   POPUP UI            │    │   WEB PAGE CONTENT           │  │
│  │  (popup.html/.js)     │◄──►│  (Facebook / YouTube / etc.) │  │
│  └──────────┬────────────┘    └──────────────┬───────────────┘  │
│             │ chrome.runtime.sendMessage       │ DOM scraping     │
│             │                                 │                  │
│  ┌──────────▼─────────────────────────────────▼───────────────┐  │
│  │              SERVICE WORKER (background.js)                 │  │
│  │   API calls │ Scan history │ Auto-scan │ Notifications       │  │
│  │   Blocklist │ Parental ctrl │ Alarms   │ Badge updates        │  │
│  └──────────────────────────┬────────────────────────────────┘  │
│                             │                                    │
│  ┌──────────────────────────▼────────────────────────────────┐  │
│  │              content.js (Page Overlay)                    │  │
│  │   Floating risk badge │ Comment highlights │ Tooltips      │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────┬───────────────────────────────────┘
                              │ HTTPS POST/GET
                              │ (local first → cloud fallback)
┌─────────────────────────────▼───────────────────────────────────┐
│                   FASTAPI BACKEND (api.py)                       │
│                  https://vncontentguard-pro.onrender.com         │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  POST /analyze/v6/unified  (ARCH-01 — Primary)           │   │
│  │  POST /analyze/v6/stream   (SSE Streaming fallback)      │   │
│  │  POST /analyze/v6          (Regular fallback)            │   │
│  │  GET  /health  /api/stats  /api/blocklist                │   │
│  │  POST /api/feedback  /api/report                         │   │
│  └─────────────────┬────────────────────────────────────────┘   │
│                    │                                             │
│  ┌─────────────────▼────────────────────────────────────────┐   │
│  │              ANALYSIS PIPELINE                            │   │
│  │                                                           │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌────────────────┐  │   │
│  │  │ UnifiedAI    │  │ FactChecker  │  │ ScoreReranker  │  │   │
│  │  │ (1 Gemini    │  │ (Google FC + │  │ (User feedback │  │   │
│  │  │  call does   │  │  NewsData +  │  │  re-ranking)   │  │   │
│  │  │  everything) │  │  GNews)      │  │                │  │   │
│  │  └──────────────┘  └──────────────┘  └────────────────┘  │   │
│  │                                                           │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌────────────────┐  │   │
│  │  │ FeedbackStore│  │ Community    │  │ CacheManager   │  │   │
│  │  │ (Learning    │  │ Blocklist    │  │ (24h TTL       │  │   │
│  │  │  engine from │  │ (JSON, 5+    │  │  per URL)      │  │   │
│  │  │  corrections)│  │  reports)   │  │                │  │   │
│  │  └──────────────┘  └──────────────┘  └────────────────┘  │   │
│  └──────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
```

### 3.2 User-Side Workflow

```
USER ACTION                        WHAT THEY SEE
─────────────────────────────────────────────────────────────────

1. Navigate to page                 [Normal browsing — nothing yet]
   (Facebook/YouTube/VnExpress...)

2. Click extension icon             [Popup opens — shows current URL]
                   │
                   ▼
3. Click "🔍 Quét trang này"        [Offline analysis starts instantly]
                   │                [⚡ Chế độ nhanh results appear in ~0.5s]
                   │                [Progress bar: "0/6 mô-đun"]
                   ▼
4. Extension scrapes page          [No visible change — happens in background]
   (article, author, comments...)

5. Backend receives request        [Progress bar advances: 1/6 → 2/6 → ...]
   (SSE streaming events arrive)   [Each module card appears as it completes]
                   │
                   │  5-15 seconds
                   ▼
6. Full results displayed          [Complete analysis report shown:]
                                    ├─ 🎯 Điểm rủi ro: 42/100 (Medium)
                                    ├─ 📰 Tóm tắt AI (3-5 lines)
                                    ├─ 💬 Cảm xúc: Tiêu cực (82%)
                                    ├─ ☣️ Độc hại: Không (15%)
                                    ├─ ✅ Kiểm chứng: Có thể đúng (65/100)
                                    ├─ 🔍 Bằng chứng AI (highlighted spans)
                                    └─ 💬 Bình luận: 3/10 độc hại

7. Optional actions:
   ├─ 👍/👎 Feedback → AI learns      [Toast: "Cảm ơn phản hồi!"]
   ├─ 🚨 Báo cáo URL lừa đảo        [Scam report submitted]
   ├─ 📐 Hiệu chỉnh điểm           [Drag sliders → re-ranked result]
   ├─ 📥 Xuất báo cáo              [HTML report downloaded]
   ├─ 🌐 Open overlay on page      [Badge + comment highlights inject]
   └─ 📊 Bulk analysis (v6.13)     [Paste multiple URLs → batch results]

[BACKGROUND — happens without user action]
   ├─ Auto-scan on navigation      [Badge updates automatically]
   ├─ Blocklist check              [Warning page if flagged domain]
   ├─ Parental control             [Block page if risk > threshold]
   └─ Weekly report alarm          [Notification every Sunday]
```

### 3.3 Backend Processing Workflow

```
REQUEST ARRIVES: POST /analyze/v6/unified
{url, article{title, author, body}, comments[], metadata{reactions, shares}}

STEP 1 — PARALLEL PRE-PROCESSING (no Gemini, ~1-2 seconds)
───────────────────────────────────────────────────────────
┌─────────────────┐  ┌─────────────────┐  ┌──────────────────┐
│ Regex Toxicity  │  │ Keyword Sentiment│  │ Source Credibility│
│ 500+ Vi phrases │  │ Fast keyword scan│  │ Domain WHOIS/SSL  │
│ → score, flags  │  │ → polarity hint  │  │ → trust score    │
└─────────────────┘  └─────────────────┘  └──────────────────┘
┌─────────────────┐  ┌─────────────────┐  ┌──────────────────┐
│ Comment Filter  │  │ Google Fact Check│  │ NewsData.io      │
│ Obvious toxic   │  │ API cross-ref    │  │ GNews cross-ref  │
│ obvious clean   │  │ → claim matches  │  │ → related news   │
│ → needs_ai only │  │                  │  │                  │
└─────────────────┘  └─────────────────┘  └──────────────────┘
┌─────────────────┐  ┌─────────────────┐
│ Cache Check     │  │ Learning Context │
│ (24h TTL)       │  │ FeedbackStore    │
│ → hit or miss   │  │ → past corrections│
└─────────────────┘  └──────────────────┘

STEP 2 — SINGLE UNIFIED GEMINI CALL (1 API call, ~3-10 seconds)
────────────────────────────────────────────────────────────────
Prompt contains:
  ├─ Article text (max 2000 chars)
  ├─ All pre-computed results from Step 1
  ├─ Ambiguous comments only (pre-filtered)
  ├─ Metadata: author, reactions, shares, page_type
  └─ Learning context: past user corrections for this domain

Gemini returns single JSON with:
  ├─ article_summary (3-5 sentences)
  ├─ sentiment {overall, confidence, intensity}
  ├─ fact_check {score, verdict, evidence[]}
  ├─ article_toxicity {is_toxic, score, severity}
  ├─ comments[] {is_toxic, severity, sentiment, reason}
  ├─ scam_indicators {detected, signals[], confidence}
  ├─ evidence_spans[] {text, category, confidence}   ← v6.3
  └─ risk_assessment {score, level, warnings[]}

STEP 3 — POST-PROCESSING & SCORING (~0.5 seconds)
──────────────────────────────────────────────────
  ├─ RiskScorerV6: Weighted formula combining all signals
  ├─ ScoreReranker: Apply user correction adjustments (v6.9)
  ├─ Blocklist: Check domain against community reports
  ├─ Incognito flag: Check metadata for incognito pattern (v6.6)
  └─ Domain feedback stats: accuracy from FeedbackStore

STEP 4 — RESPONSE
──────────────────
  If SSE: yield each module event as it completes (1/6 → 6/6)
  If regular: return complete JSON
  Both: cache result for 24h by URL

FINAL RESPONSE (version: "6.0"):
{
  article_summary, sentiment_v6, toxicity_v6, fact_check_v6,
  risk_score_v6, comments_analysis, scam_analysis,
  evidence_spans,        ← v6.3 Explainable AI
  correction_history,    ← v6.9 Re-ranker
  incognito_flag,        ← v6.6
  blocklist_info, domain_feedback, learning_applied,
  url, version: "6.0", cache_stats
}
```

### 3.4 Data Flow Diagram

```
[WEBPAGE DOM]
     │
     │  popup.js: structuredScrape()
     ▼
{page_type, article{title,author,body}, comments[{text,author,reactions}],
 metadata{reactions,shares,domain}}
     │
     │  chrome.runtime.sendMessage({type:'START_SCAN', data})
     ▼
[background.js SERVICE WORKER]
     │
     │  Priority: local (127.0.0.1) → cloud (onrender.com)
     │  Method: SSE stream (primary) → regular POST (fallback)
     ▼
[FASTAPI /analyze/v6/unified]
     │
     ├──────────────────────────────────────────────────────┐
     │ asyncio.gather():                                     │
     │  regex_tox() ──────────────────────┐                 │
     │  keyword_sent() ───────────────────┤                 │
     │  source_cred() ────────────────────┤→ pre_results{}  │
     │  comment_filter() ─────────────────┤                 │
     │  factcheck_api() ──────────────────┘                 │
     │                                                       │
     │  feedback_store.get_learning_context(url)             │
     │                                                       │
     │  gemini_unified_call(article, pre_results,           │
     │                       ambiguous_comments,             │
     │                       learning_context)               │
     │  → ai_result{}                                        │
     │                                                       │
     │  score_reranker.apply(ai_result, url)  ← v6.9        │
     │  blocklist.is_blocked(url)                            │
     │  cache.set(url, final_result, ttl=86400)              │
     └──────────────────────────────────────────────────────┘
     │
     │  SSE: event:module → event:complete
     │  or   JSON response
     ▼
[background.js] → chrome.storage.local.set({scanResult})
     │
     ▼
[popup.js] → renderResults() → UI cards displayed
     │
     ├─► content.js ──→ injectOverlay() → badges on page DOM
     └─► chrome.action.setBadgeText(riskScore)
```

### 3.5 Extension ↔ Backend Communication

| Message Type | Direction | Payload | Purpose |
|---|---|---|---|
| `START_SCAN` | popup → background | `{url, pageData}` | Trigger regular scan |
| `START_SCAN_STREAM` | popup → background | `{url, pageData}` | Trigger SSE streaming scan |
| `GET_SCAN_STATUS` | popup → background | `{url}` | Poll for results |
| `CANCEL_SCAN` | popup → background | — | Cancel in-progress scan |
| `SUBMIT_FEEDBACK` | popup → background | `{url, rating, correction}` | Send user rating to backend |
| `SUBMIT_REPORT` | popup → background | `{url, reason}` | Community report submission |
| `SUBMIT_SCAM_REPORT` | popup → background | `{url, scamType}` | Scam URL report (v6.12) |
| `SUBMIT_CORRECTION` | popup → background | `{url, corrections{}}` | Score correction (v6.9) |
| `BULK_SCAN` | popup → background | `{urls[]}` | Batch analysis (v6.13) |
| `SET_AUTO_SCAN` | popup → background | `{enabled}` | Toggle auto-scan |
| `SET_PARENTAL_CONTROL` | popup → background | `{enabled, pin, threshold}` | Parental settings |
| `OPEN_WEEKLY_REPORT` | popup → background | — | Open report.html tab |
| `CHECK_BLOCKLIST` | popup → background | `{url}` | Domain blocklist check |

---

## 4. File Structure

```
C:\Users\LucyS\Tox\
│
├── api.py                          # FastAPI server (~2274 lines) — MAIN ENTRY POINT
├── requirements.txt                # Python dependencies (11 packages)
├── build.sh                        # Render deployment build script
├── .render.yaml                    # Render cloud deployment config
├── .env                            # API keys — 30 Gemini + 4 external (gitignored)
├── .gitignore
├── README.md                       # Vietnamese project documentation
├── SYSTEM_CONTEXT.md               # Full system context for AI chat continuity
├── V4_UPGRADE_PLAN.md              # Feature roadmap with status tracking
├── PROJECT_DOCUMENTATION.md        # ← This file
├── chrome_store_description_v6.txt # Chrome Web Store listing copy
│
├── src/
│   ├── __init__.py
│   ├── models/
│   │   ├── gemini_llm.py           # APIKeyRotator + GeminiAgent (30-key rotation)
│   │   ├── unified_analyzer.py     # ARCH-01: single-pass Gemini analysis (v6)
│   │   ├── sentiment_v6.py         # v6 sentiment: Gemini + PhoBERT + keyword fallback
│   │   ├── toxicity_v6.py          # v6 toxicity: 4-layer (regex→Gemini→Persp→Detoxify)
│   │   ├── fact_checker_v6.py      # v6 fact check: multi-source verification
│   │   ├── source_analyzer_v6.py   # Domain credibility: SSL/WHOIS/reputation
│   │   ├── risk_scorer_v6.py       # Weighted formula: fake(30%)+tox(25%)+sent(15%)+src(15%)+manip(15%)
│   │   ├── article_summarizer_v6.py# Gemini article summarization + URL cache
│   │   ├── reranker.py             # ScoreReranker: user correction re-ranking (v6.9)
│   │   ├── sentiment.py            # v2 keyword-based fallback
│   │   └── toxicity.py             # v2 regex-based fallback
│   └── utils/
│       ├── cache_manager.py        # In-memory TTL cache (default 24h)
│       ├── comment_filter.py       # Pre-classify: obvious_toxic/obvious_clean/needs_ai
│       ├── feedback_store.py       # User feedback storage + learning engine
│       └── blocklist.py            # Community blocklist (JSON, 5+ reports = block)
│
├── tests/
│   ├── test_sentiment_v3.py        # 19 sentiment tests
│   ├── test_toxicity_v3.py         # 26 toxicity tests
│   ├── test_fact_checking_v3.py    # 31 fact-check tests
│   └── test_risk_scorer_v3.py      # 20 risk scorer tests
│
└── extension/
    ├── manifest.json               # Chrome Manifest V3, version 6.0.0
    ├── popup.html                  # UI layout (~415 lines, fully Vietnamese)
    ├── popup.js                    # Logic + rendering (~3461 lines)
    ├── style.css                   # Styling (~1213 lines), light/dark mode CSS vars
    ├── background.js               # Service worker (~1409 lines)
    ├── content.js                  # Page overlay injection
    ├── content.css                 # Overlay styles
    ├── offline_analyzer.js         # Offline regex engine (500+ patterns)
    ├── domain_control.js           # Domain blacklist/whitelist module (v6.2)
    ├── warning.html                # Interstitial warning for blocklisted domains
    ├── block.html                  # Parental control block page
    ├── report.html                 # Weekly safety report page
    ├── report.js                   # Weekly report logic + visualization
    └── icons/
        └── icon.png
```

---

## 5. API Reference

### Core Scan Endpoints

#### `POST /analyze/v6/unified` — Primary (ARCH-01)
**Input:**
```json
{
  "url": "https://...",
  "page_type": "facebook_post | news_article | youtube_video | tiktok | generic",
  "article": { "title": "...", "author": "...", "published_date": "...", "body": "..." },
  "comments": [{ "text": "...", "author": "...", "reactions": 15, "is_reply": false }],
  "metadata": { "domain": "vnexpress.net", "reactions_total": 1200, "shares": 350 }
}
```
**Output:** Full analysis JSON (see §3.3 Final Response)
**Latency:** 5–15 seconds
**Gemini calls:** 1

---

#### `POST /analyze/v6/stream` — SSE Streaming
Same input as above. Returns `text/event-stream`.
Yields events in order:
```
event: module  data: {"module": "summary", "data": {...}}
event: module  data: {"module": "sentiment", "data": {...}}
event: module  data: {"module": "toxicity", "data": {...}}
event: module  data: {"module": "fact_check", "data": {...}}
event: module  data: {"module": "risk_score", "data": {...}}
event: module  data: {"module": "comments", "data": {...}}
event: complete  data: {"type": "complete", "data": {full_result}}
event: error   data: {"type": "error", "message": "..."}
```

---

#### `GET /health`
```json
{"status": "🟢 VnContentGuard Pro Server is Running"}
```

#### `GET /api/stats`
Returns: keys_total, keys_available, daily_requests, cache stats, uptime, version.

#### `POST /api/feedback`
Input: `{url, rating ("positive"|"negative"), correction?, modules?, scan_results?}`
Stores in `feedback_store.py`. Learning context injected into next Gemini call for this domain.

#### `POST /api/report`
Input: `{url, risk_score, reason}`
Auto-blocks domain after 5+ reports.

#### `GET /api/blocklist` / `GET /api/blocklist/check?url=`
Returns blocked domains list or single domain check.

---

## 6. Key Components Deep Dive

### 6.1 UnifiedAnalyzer (ARCH-01) — `src/models/unified_analyzer.py`
The core innovation introduced in v6.0. Replaces 3–5 sequential Gemini calls with one structured prompt that returns all 6 analysis modules simultaneously.

**Token savings:** ~10,200 tokens (v3) → ~3,300 tokens (v6) — **68% reduction**
**Latency improvement:** 15–60s → 5–15s — **60–75% faster**
**Quality improvement:** Cross-module awareness — AI sees comments when fact-checking, sees reactions when scoring risk

### 6.2 FeedbackStore + Learning Engine — `src/utils/feedback_store.py`
Stores user corrections (👍/👎 + text) per domain. On subsequent scans, `get_learning_context(url)` generates a prompt prefix like:

> *"USER FEEDBACK LEARNING: Domain vnexpress.net accuracy: 75% (12 feedback). Recent corrections: User said 'This is satire, not misinformation'..."*

This string is injected into the Gemini unified prompt, causing the AI to apply past corrections to new analyses of the same domain.

### 6.3 ScoreReranker — `src/models/reranker.py` (v6.9)
When a user drags the correction sliders in the popup, corrections are sent to `POST /api/correction`. The `ScoreReranker` applies a weighted adjustment formula to re-rank the AI's raw scores, storing the delta as a per-URL/per-domain correction factor for future scans.

### 6.4 CommunityBlocklist — `src/utils/blocklist.py`
Thread-safe JSON store. Any user can flag a URL. When a domain accumulates 5+ reports, it is auto-added to the blocklist. The extension refreshes this list every 6 hours. Flagged domains trigger `warning.html` interstitial before navigation completes.

### 6.5 CommentFilter — `src/utils/comment_filter.py`
Pre-categorizes comments before sending to AI:
- `obvious_toxic` — matches high-confidence Vietnamese toxic patterns → marked toxic, no AI call
- `obvious_clean` — short positive comments, greetings → marked clean, no AI call
- `spam` — repetitive, emoji-only, promotional → filtered out
- `needs_ai` — ambiguous text → sent to Gemini for analysis

This saves significant API calls on articles with large comment sections.

### 6.6 APIKeyRotator — `src/models/gemini_llm.py`
- 30 keys loaded from `.env`
- Single shared instance across ALL modules (`shared_key_rotator`)
- On 429: increments key pointer, retries with next key
- Tracks `exhausted_keys` set; skips them until daily reset
- Daily reset at UTC midnight via `_check_reset()` called on each increment

---

## 7. Version History & Feature Comparison

### Version Timeline

```
Feb 2026   v2.0  ──── Basic keyword analysis + regex toxicity
                │
Feb 13     v3.0  ──── 4-layer AI pipeline + 96 tests
                │
Feb 13     v4.0  ──── BUG-01 fix + dark mode + Gemini Flash
                │
Feb 15     v4.5  ──── Export report + API dashboard
                │
Feb 16     v5.0  ──── Auto-scan + comparison + offline mode + feedback
                │
Feb 19     v5.9  ──── SSE streaming + YouTube/TikTok + overlay + notifications
           (shipped as v4.9 internally)
                │
Feb 23     v6.0  ──── ARCH-01 unified AI + explainable AI + incognito
                │         + score correction + scam detection + bulk analysis
                ▼
Mar  1     v6.0  ──── Production (current, main branch)
```

---

### Feature Comparison Table

| Feature | v2.0 | v3.0 | v4.0 | v4.5 | v5.0 | v5.9/4.9 | v6.0 |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **ANALYSIS CORE** | | | | | | | |
| Basic toxicity (regex) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Keyword sentiment | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 4-layer toxicity (regex→Gemini→API→model) | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| AI-powered sentiment (Gemini/PhoBERT) | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Multi-source fact checking | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Evidence-based risk scoring (0–100) | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| AI article summarization (cached) | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Comment batch analysis | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Unified single-pass AI (ARCH-01)** | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| **Explainable AI evidence spans** | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | **✅ v6.3** |
| **Scam indicator detection** | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | **✅ v6.12** |
| AI model | keyword | Gemini 2.5 Flash-Lite | Gemini 2.5 Flash | Flash | Flash | Flash | Flash |
| API calls per scan | 0 | 3–5 | 3–5 | 3–5 | 3–5 | 3–5 | **1** |
| Latency | <1s | 15–60s | 15–60s | 15–60s | 15–60s | 10–40s | **5–15s** |
| **EXTENSION STABILITY** | | | | | | | |
| Results survive popup close | ❌ | ❌ | **✅ BUG-01** | ✅ | ✅ | ✅ | ✅ |
| Background service worker | ❌ | ❌ | **✅** | ✅ | ✅ | ✅ | ✅ |
| Badge with risk score | ❌ | ❌ | **✅** | ✅ | ✅ | ✅ | ✅ |
| **UI & UX** | | | | | | | |
| Dark mode | ❌ | ❌ | **✅** | ✅ | ✅ | ✅ | ✅ |
| Scan history (20 entries) | ❌ | ❌ | **✅** | ✅ | ✅ | ✅ | ✅ |
| Export report (HTML/PDF) | ❌ | ❌ | ❌ | **✅** | ✅ | ✅ | ✅ |
| API usage dashboard | ❌ | ❌ | ❌ | **✅** | ✅ | ✅ | ✅ |
| SSE streaming progress bar | ❌ | ❌ | ❌ | ❌ | ❌ | **✅** | ✅ |
| **Score correction UI (drag sliders)** | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | **✅ v6.9** |
| **Bulk analysis (paste multiple URLs)** | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | **✅ v6.13** |
| **PLATFORM SUPPORT** | | | | | | | |
| Facebook | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| VnExpress / Dân Trí / Tuổi Trẻ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| YouTube | ❌ | ❌ | ❌ | ❌ | ❌ | **✅** | ✅ |
| TikTok | ❌ | ❌ | ❌ | ❌ | ❌ | **✅** | ✅ |
| Any URL (manual mode) | ❌ | partial | ✅ | ✅ | ✅ | ✅ | ✅ |
| **SMART FEATURES** | | | | | | | |
| Auto-scan on navigation | ❌ | ❌ | ❌ | ❌ | **✅** | ✅ | ✅ |
| Comparison mode (side-by-side) | ❌ | ❌ | ❌ | ❌ | **✅** | ✅ | ✅ |
| Offline regex mode (⚡ instant) | ❌ | ❌ | ❌ | ❌ | **✅** | ✅ | ✅ |
| User feedback loop (👍/👎) | ❌ | ❌ | ❌ | ❌ | **✅** | ✅ | ✅ |
| AI learning from corrections | ❌ | ❌ | ❌ | ❌ | **✅** | ✅ | ✅ |
| Real-time Chrome notifications | ❌ | ❌ | ❌ | ❌ | ❌ | **✅** | ✅ |
| **Incognito mode detection** | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | **✅ v6.6** |
| **Domain blacklist/whitelist (custom)** | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | **✅ v6.2** |
| **Scam URL 1-click reporting** | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | **✅ v6.12** |
| **Re-Ranker (AI self-corrects from user)** | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | **✅ v6.9** |
| **SAFETY SYSTEMS** | | | | | | | |
| Content script overlay (page badges) | ❌ | ❌ | ❌ | ❌ | ❌ | **✅** | ✅ |
| Community blocklist (5+ reports = block) | ❌ | ❌ | ❌ | ❌ | ❌ | **✅** | ✅ |
| Interstitial warning page | ❌ | ❌ | ❌ | ❌ | ❌ | **✅** | ✅ |
| Parental control (PIN + threshold) | ❌ | ❌ | ❌ | ❌ | ❌ | **✅** | ✅ |
| Weekly safety report (alarm) | ❌ | ❌ | ❌ | ❌ | ❌ | **✅** | ✅ |

---

### What Changed Per Version (Narrative)

#### v2.0 — Foundation
The first usable version. Analysis was entirely regex-based and keyword-based — no AI calls. Fast but inaccurate, especially for sarcasm and nuanced Vietnamese text. No background worker; results disappeared when popup closed.

#### v3.0–3.2 — AI Integration
The AI backbone was added: Gemini for fact-check synthesis and comment analysis, PhoBERT for sentiment, 4-layer toxicity pipeline. Multi-source fact checking added (Google Fact Check API + NewsData.io + GNews). Risk scorer added with weighted formula. 96 automated tests written. But the critical bug (popup closing deletes results) remained.

#### v4.0 — Stability Fix
**BUG-01:** Scan moved entirely to background service worker — results now survive popup close. This was foundational — all later features depend on the service worker. Added scan history, dark mode, badge updates, and upgraded the AI model from Flash Lite to full Gemini 2.5 Flash.

#### v4.5 — Productivity
Export report feature (formatted HTML, printable to PDF). API usage dashboard showing key rotation health and cache hit rates.

#### v5.0 — Intelligence
Auto-scan on navigation (with 30-min rate limit). Comparison mode for two sources side-by-side. Offline regex mode for instant partial results while waiting for AI. User feedback loop storing corrections to `feedback_store.py` — the first version where the AI could learn from users.

#### v5.9 / v4.9 — Platform Expansion
YouTube and TikTok support (scrapes video metadata + comments). Content script overlay — floating badges injected directly into web pages. SSE streaming progress (each of 6 modules renders as it completes). Notification system, community blocklist, parental control, browser warning interstitial, and weekly safety report all added.

#### v6.0 — Architectural Overhaul (Current)
The biggest architectural change: **ARCH-01** replaced 3–5 sequential Gemini calls with a single unified call (68% fewer tokens, 60–75% faster). Added v6.3 explainable AI (text evidence spans), v6.6 incognito detection, v6.9 score correction with Re-Ranker model, v6.12 scam URL detection and reporting, v6.13 bulk analysis mode (multiple URLs at once), and v6.2 custom domain blacklist/whitelist. All version labels in UI and code unified to "v6".

---

## 8. Known Limitations

| # | Limitation | Impact | Workaround |
|---|---|---|---|
| 1 | **Perspective API** returns HTTP 400 for Vietnamese (`vi`) locale | Toxicity layer 3 always skipped for Vietnamese text | Regex (layer 1) + Gemini (layer 2) compensate |
| 2 | **Gemini free tier** — 15 RPM per key, 20 RPD per key | High traffic burns through 30 keys quickly | 30-key rotation gives ~600 RPD total |
| 3 | **Render cold start** — ~30s on first request after inactivity | First scan of the day is slow | Offline mode shows instant partial results |
| 4 | **Facebook DOM changes** — selectors for comments may break | Scraper returns empty comments | Manual copy-paste fallback in generic mode |
| 5 | **TikTok DOM** — frequently restructured | Selectors may break with TikTok updates | Need manual selector maintenance per update |
| 6 | **Parental control PIN** stored in plaintext in `chrome.storage.local` | Minor security concern | Acceptable for browser extension context; not a server secret |
| 7 | **Blocklist uses JSON file** — not a database | Not suitable for production scale (>10K reports) | Would need Redis/PostgreSQL migration for scale |
| 8 | **CORS set to `*`** | Open to any origin in development | Should be restricted to extension origin in production |

---

## 9. Development Setup

### Backend
```bash
# Clone and set up
git clone https://github.com/NgocDungNguyen/VnContentGuard-Pro.git
cd VnContentGuard-Pro
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux/Mac

pip install -r requirements.txt

# Configure API keys
cp .env.example .env
# Fill in: GEMINI_API_KEY_1 through _30, GOOGLE_FACT_CHECK_API_KEY,
#          GOOGLE_PERSPECTIVE_API_KEY, NEWSDATA_API_KEY, GNEWS_API_KEY

# Run locally
python api.py
# → http://127.0.0.1:8000
```

### Extension (Chrome)
1. Open `chrome://extensions`
2. Enable **Developer mode** (top-right toggle)
3. Click **Load unpacked** → select `C:\Users\LucyS\Tox\extension`
4. Extension icon appears in toolbar

### Tests
```bash
pytest -v
# Expected: 96 passed
```

### Deployment (Render)
Push to `main` branch → Render auto-deploys via `.render.yaml`
```bash
git add -A
git commit -m "feat: description of change"
git push origin main
```

### Key Files for Each Task

| Task | Files to Edit |
|---|---|
| Change AI prompts | `src/models/unified_analyzer.py`, `src/models/fact_checker_v6.py` |
| Add new API endpoint | `api.py` |
| Extend scraper (new site) | `extension/popup.js` — `structuredScrape()` function |
| Modify popup UI | `extension/popup.html`, `extension/popup.js`, `extension/style.css` |
| Change background behavior | `extension/background.js` |
| Adjust risk weighting | `src/models/risk_scorer_v6.py` |
| Modify learning/feedback | `src/utils/feedback_store.py` |
| Blocklist behavior | `src/utils/blocklist.py` |
| Add new Chrome pages | `extension/*.html` + update `manifest.json` |

---

*Document generated: March 1, 2026 | VnContentGuard Pro v6.0.0*
