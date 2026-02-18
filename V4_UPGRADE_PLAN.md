# 🛡️ VNCONTENTGUARD PRO — V4 UPGRADE PLAN
### Version: 4.9 | Started: February 13, 2026
### Tracking Document — Update status as each feature is completed

---

## 🚨 CRITICAL BUG FIX (Priority 0 — Before anything else)

### BUG-01: UI Results Disappear When Switching Tabs / Clicking Away
| Field | Detail |
|-------|--------|
| **Severity** | 🔴 Critical — Users lose scan results mid-analysis |
| **Problem** | After clicking "Scan", if user switches to another tab or clicks outside the popup, the Chrome popup closes and all UI state (results, loading progress) is lost. User must re-scan from scratch. |
| **Root Cause** | Chrome extension popups are destroyed the moment they lose focus. The current code only saves results to `chrome.storage.local` AFTER the API response arrives. If the popup closes during the 15-60s analysis wait, nothing is saved. |
| **Solution** | **Multi-part fix:** |
| | 1. **Save scan state immediately** — When user clicks "Quét", save `{status: "scanning", url, timestamp}` to `chrome.storage.local` right away |
| | 2. **Move API call to background** — Use `chrome.runtime.sendMessage` to hand off the fetch to a **service worker** (`background.js`). The service worker survives popup close. |
| | 3. **Resume on popup reopen** — On `DOMContentLoaded`, check storage for `status: "scanning"` → show "⏳ Đang phân tích..." with the original URL. When background finishes, it writes results to storage and the popup picks them up. |
| | 4. **Badge update** — Service worker sets `chrome.action.setBadgeText` with risk score when done, so user sees results even without opening popup. |
| **Files to Change** | `manifest.json` (add `background.service_worker`), new `background.js`, `popup.js` (refactor scan flow) |
| **Effort** | 1-2 days |
| **Status** | ✅ Completed (v4.0) |

---

## 📋 FEATURE ROADMAP

### Legend
| Symbol | Status |
|--------|--------|
| ⬜ | Not started |
| 🔄 | In progress |
| ✅ | Completed |
| ❌ | Cancelled / Deferred |

---

## PHASE 1 — Polish & UX (Week 1-2)

### 1.1 — Scan History / Dashboard
| Field | Detail |
|-------|--------|
| **What** | Store last 10-20 scans in `chrome.storage.local` with timestamps. Add a "📜 Lịch sử" tab in popup showing past URLs + risk scores. Click any entry to re-view full results. |
| **Why** | Users lose results when popup closes. Having history means they can always go back. Huge UX win. |
| **Implementation** | |
| | 1. Create `scanHistory` array in `chrome.storage.local` — max 20 entries, FIFO |
| | 2. Each entry: `{url, title, riskScore, riskLevel, toxicPercent, timestamp, resultsKey}` |
| | 3. Add "📜 Lịch sử" toggle button in popup header |
| | 4. Build history list UI: cards with color-coded risk, relative timestamps ("2 giờ trước") |
| | 5. Click card → load full cached results from storage |
| | 6. "🗑️ Xoá lịch sử" button to clear all |
| **Files** | `popup.html`, `popup.js`, `style.css` |
| **Effort** | 1 day |
| **Cost** | $0 |
| **Status** | ✅ Completed (v4.0) — 20-entry FIFO history, color-coded risk cards, relative timestamps, click to open URL |

---

### 1.2 — Export Report (PDF/Text)
| Field | Detail |
|-------|--------|
| **What** | "📥 Xuất báo cáo" button → generates a clean, formatted HTML report of the scan results. Downloads as `.html` file (opens in browser, printable to PDF). |
| **Why** | Users need to share results with others — teachers, editors, parents, researchers. |
| **Implementation** | |
| | 1. Add "📥 Xuất báo cáo" button below results section |
| | 2. Build `generateReport(data)` function → creates standalone HTML string with: |
| |    - Header: VnContentGuard Pro logo, scan date, URL |
| |    - Risk score (color-coded) |
| |    - All module results (sentiment, toxicity, fact check, comments) |
| |    - Footer: disclaimer + version |
| | 3. Create Blob → `URL.createObjectURL` → trigger download as `VnCG-Report-{domain}-{date}.html` |
| | 4. Alternative: `window.print()` for quick PDF via browser print dialog |
| **Files** | `popup.html`, `popup.js` |
| **Effort** | 1 day |
| **Cost** | $0 |
| **Status** | ✅ Completed (v4.5) — HTML report with styled template, risk hero, tables, comment cards, PDF print button, chrome.downloads API |

---

### 1.3 — Auto-scan Toggle
| Field | Detail |
|-------|--------|
| **What** | Settings option: "Tự động quét khi mở trang" → uses `chrome.tabs.onUpdated` listener in service worker to trigger scan when navigating to supported sites. |
| **Why** | Power users don't want to click "Scan" every time. Set it and forget it. |
| **Implementation** | |
| | 1. Add toggle switch in popup: "⚡ Tự động quét" |
| | 2. Store preference in `chrome.storage.sync` (syncs across devices) |
| | 3. In `background.js`: listen for `chrome.tabs.onUpdated` with `status: "complete"` |
| | 4. Check if URL matches supported domains (Facebook, VnExpress, etc.) |
| | 5. Auto-execute scrape + send to API |
| | 6. Save results to storage, update badge |
| | 7. Rate-limit: max 1 auto-scan per URL per 30 minutes |
| **Dependencies** | Requires BUG-01 fix (background service worker) |
| **Files** | `popup.html`, `popup.js`, `background.js`, `manifest.json` |
| **Effort** | 1 day |
| **Cost** | $0 |
| **Status** | ✅ Completed (v5.0) — Auto-scan toggle in popup, background.js tabs.onUpdated listener, domain whitelist, 30-min rate limit |

---

### 1.4 — Dark Mode
| Field | Detail |
|-------|--------|
| **What** | 🌙/☀️ toggle in popup header. Dark theme for popup UI. Saves preference in `chrome.storage.sync`. |
| **Why** | Looks modern, reduces eye strain, easy to implement, good for Chrome Web Store ratings. |
| **Implementation** | |
| | 1. Add `🌙` button in popup header (top-right) |
| | 2. Create CSS variables: `--bg-primary`, `--text-primary`, `--card-bg`, etc. |
| | 3. `.dark-mode` class on `<body>` overrides CSS variables |
| | 4. Save preference in `chrome.storage.sync` |
| | 5. On `DOMContentLoaded`, apply saved theme before render (avoid flash) |
| **Files** | `popup.html`, `popup.js`, `style.css` |
| **Effort** | 3-4 hours |
| **Cost** | $0 |
| **Status** | ✅ Completed (v4.0) — CSS variables, dark-mode class, chrome.storage.sync preference, header toggle button |

---

### 1.5 — Better Loading UX (Streaming Results)
| Field | Detail |
|-------|--------|
| **What** | Show each analysis module result as it completes instead of waiting for the entire `/analyze/v3` to finish. Use FastAPI `StreamingResponse` with Server-Sent Events (SSE). |
| **Why** | Current wait is 15-60s with blank screen. Streaming keeps users engaged and shows progress. |
| **Implementation** | |
| | **Backend (`api.py`):** |
| | 1. New endpoint `POST /analyze/v3/stream` returning `text/event-stream` |
| | 2. Yield each module result as it completes: `data: {"module": "sentiment_v3", "result": {...}}` |
| | 3. Order: summary → sentiment → toxicity → fact_check → risk_score → comments |
| | 4. Keep existing `/analyze/v3` for backward compatibility |
| | **Frontend (`popup.js`):** |
| | 5. Use `EventSource` or `fetch` with `ReadableStream` reader |
| | 6. On each SSE message, render that module's card immediately |
| | 7. Show progress bar: "2/6 mô-đun hoàn tất" |
| | 8. Fallback to regular POST if SSE fails |
| **Files** | `api.py`, `popup.js`, `popup.html`, `style.css` |
| **Effort** | 2-3 days |
| **Cost** | $0 |
| **Status** | ✅ Completed (v4.9) — Backend SSE streaming endpoint, background.js stream handler, popup progress bar "X/6 mô-đun hoàn tất", fallback to regular POST |

---

## PHASE 2 — Platform Expansion (Week 3-4)

### 2.1 — Content Script Overlay
| Field | Detail |
|-------|--------|
| **What** | Inject scan results directly into the webpage: highlight toxic comments in red/orange borders, show a floating risk badge next to article titles. |
| **Why** | More immersive than the popup. Competitors (e.g., NewsGuard) do this. |
| **Implementation** | |
| | 1. Add `content_scripts` to `manifest.json` for supported domains |
| | 2. Create `content.js` — injects CSS + result badges into page DOM |
| | 3. After scan, send results from popup/background → content script via `chrome.tabs.sendMessage` |
| | 4. Toxic comments: add red/orange left-border + tooltip showing category |
| | 5. Article title: floating badge "🛡️ Rủi ro: 72/100" |
| | 6. Toggle overlay on/off from popup |
| **Files** | `manifest.json`, new `content.js`, new `content.css`, `popup.js` |
| **Effort** | 3-4 days |
| **Cost** | $0 |
| **Status** | ⬜ Not started |

---

### 2.2 — YouTube Support
| Field | Detail |
|-------|--------|
| **What** | Add YouTube to `host_permissions`. Scrape video title + description + comments via DOM selectors. Analyze like a regular article. |
| **Why** | Massive Vietnamese audience on YouTube. Major feature gap currently. |
| **Implementation** | |
| | 1. Add `https://*.youtube.com/*` to `host_permissions` in manifest |
| | 2. Extend `scrapePageContent()` with YouTube-specific selectors: |
| |    - Title: `h1.ytd-watch-metadata` or `#title h1` |
| |    - Description: `#description-inner` or `ytd-text-inline-expander` |
| |    - Comments: `#content-text` inside `ytd-comment-renderer` |
| | 3. Handle YouTube SPA navigation (page doesn't fully reload) |
| | 4. Cap comments at 50 (same as current) |
| **Files** | `manifest.json`, `popup.js` (scraper section) |
| **Effort** | 2-3 days |
| **Cost** | $0 |
| **Status** | ⬜ Not started |

---

### 2.3 — TikTok Support
| Field | Detail |
|-------|--------|
| **What** | Scrape TikTok video captions + comments. TikTok's DOM is complex but doable. |
| **Why** | Biggest platform for Vietnamese youth. Critical for content safety mission. |
| **Implementation** | |
| | 1. Add `https://*.tiktok.com/*` to `host_permissions` |
| | 2. TikTok selectors (frequently change — need maintenance): |
| |    - Caption: `[data-e2e="browse-video-desc"]` or `.tiktok-1ejylhp-DivContainer` |
| |    - Comments: `[data-e2e="comment-level-1"]` |
| | 3. May need `content_scripts` injection since TikTok loads dynamically |
| | 4. Add retry logic for lazy-loaded comments |
| **Risk** | TikTok frequently changes their DOM structure. Selectors may break. |
| **Files** | `manifest.json`, `popup.js`, possibly `content.js` |
| **Effort** | 3-4 days |
| **Cost** | $0 |
| **Status** | ⬜ Not started |

---

### 2.5 — Comparison Mode
| Field | Detail |
|-------|--------|
| **What** | Scan 2 articles about the same topic → show side-by-side fact check results, comparing which source is more credible. |
| **Why** | Unique feature. Great for education and research. No competitor does this. |
| **Implementation** | |
| | 1. "📊 So sánh" button in popup → opens comparison panel |
| | 2. User pastes/selects 2 URLs (or picks from scan history) |
| | 3. Both scanned → results shown side-by-side: |
| |    - Risk score comparison bars |
| |    - Source credibility comparison |
| |    - Fact check verdict comparison |
| | 4. Highlight which source is more reliable with clear visual |
| **Dependencies** | Feature 1.1 (Scan History) for picking previous scans |
| **Files** | `popup.html`, `popup.js`, `style.css`, possibly `api.py` |
| **Effort** | 3-4 days |
| **Cost** | $0 |
| **Status** | ✅ Completed (v5.0) — Side-by-side comparison from scan history, renderComparison() with score bars |

---

### 2.7 — Offline Regex Mode
| Field | Detail |
|-------|--------|
| **What** | When backend is unreachable (Render cold start ~30s), do local regex-only toxicity + keyword sentiment scan entirely in the extension. Show partial results with "⚡ Chế độ nhanh" badge. |
| **Why** | Eliminates the cold-start pain point. Users get instant partial results while waiting for full AI analysis. |
| **Implementation** | |
| | 1. Port Vietnamese toxic regex patterns (from `toxicity.py`) to JS |
| | 2. Port keyword sentiment lists (from `sentiment.py`) to JS |
| | 3. On scan: immediately run local analysis → show partial results |
| | 4. Simultaneously send to backend → when response arrives, replace with full results |
| | 5. If backend fails entirely, keep showing local results with "⚡ Chế độ nhanh — Chỉ phân tích cơ bản" |
| | 6. Badge: yellow "⚡" indicator for offline mode |
| **Files** | `popup.js` (add regex engine), possibly new `offline_analyzer.js` |
| **Effort** | 2-3 days |
| **Cost** | $0 |
| **Status** | ✅ Completed (v5.0) — offline_analyzer.js with 30+ regex patterns + sentiment keywords, instant partial results with ⚡ badge |

---

## PHASE 3 — Intelligence & Feedback (Week 5-6)

### 3.3 — User Feedback Loop
| Field | Detail |
|-------|--------|
| **What** | After each scan: "Kết quả chính xác không? 👍/👎" buttons. Optionally: text input for correction. Store feedback on backend. |
| **Why** | Continuous improvement. Builds evaluation dataset. Shows professionalism and user respect. |
| **Implementation** | |
| | 1. Add 👍/👎 buttons below each result module |
| | 2. On click: send `POST /feedback` to backend with `{url, module, rating, correction?, timestamp}` |
| | 3. Backend stores in SQLite or JSON file |
| | 4. After 100+ feedbacks: export as evaluation dataset to tune Gemini prompts |
| | 5. Show "Cảm ơn phản hồi của bạn! 🙏" toast after submission |
| **Files** | `popup.html`, `popup.js`, `api.py`, new `src/utils/feedback_store.py` |
| **Effort** | 2 days |
| **Cost** | $0 |
| **Status** | ✅ Completed (v5.0) — feedback_store.py JSON storage, POST /api/feedback endpoint, 👍/👎 UI with correction textarea |

---

### 3.4 — API Rate Limit Dashboard
| Field | Detail |
|-------|--------|
| **What** | New endpoint `GET /api/stats` showing: API keys remaining, cache hit rate, daily usage, system health. Display in popup footer as "🔋 Hệ thống: 420/600 lượt". |
| **Why** | Transparency. Helps debug "no results" issues. Users understand why scans may fail during high usage. |
| **Implementation** | |
| | 1. New `GET /api/stats` endpoint in `api.py` returning: |
| |    ```json |
| |    { "keys_total": 30, "keys_available": 24, "keys_exhausted": 6, |
| |      "daily_requests": 420, "daily_limit": 600, |
| |      "cache_hits": 150, "cache_misses": 270, "cache_size": 45, |
| |      "uptime_seconds": 3600, "version": "3.2" } |
| |    ``` |
| | 2. Popup calls `/api/stats` on load → shows compact status bar |
| | 3. Color-coded: 🟢 >50% capacity, 🟡 20-50%, 🔴 <20% |
| **Files** | `api.py`, `popup.js`, `popup.html`, `style.css` |
| **Effort** | 1 day |
| **Cost** | $0 |
| **Status** | 🔄 Partial (v4.0→v4.9) — Backend `GET /api/stats` exists but popup UI never implemented. **v4.9.1**: Added daily usage counter, cache stats, uptime to backend. Added compact "🔋 Hệ thống" status bar in popup header with color-coded capacity + auto-refresh on popup open. |

### 3.5 — Notification System

| Field | Detail |
|-------|--------|
| **What** | Use `chrome.notifications` API to alert user when: a previously-safe page gets re-flagged, risk score changes significantly, or auto-scan detects high-risk content. |
| **Why** | Proactive protection vs reactive scanning. Users are warned without opening the extension. |
| **Implementation** | |
| | 1. Add `notifications` permission to manifest |
| | 2. In `background.js`: after auto-scan or re-scan, compare new risk score with cached |
| | 3. If risk changed by >20 points OR new toxic content found → trigger notification |
| | 4. Notification: "⚠️ VnContentGuard: {domain} — Rủi ro tăng từ 30 → 65/100" |
| | 5. Click notification → opens popup with details |
| | 6. Settings: enable/disable notifications per category |
| **Dependencies** | BUG-01 (service worker), Feature 1.3 (auto-scan) |
| **Files** | `manifest.json`, `background.js`, `popup.js` |
| **Effort** | 1-2 days |
| **Cost** | $0 |
| **Status** | ✅ Completed (v4.9) — chrome.notifications for risk>=50, notification history in storage, click opens URL |

---

## PHASE 4 — Advanced / Differentiation (Week 7-8+)

### 4.1 — Community Blocklist
| Field | Detail |
|-------|--------|
| **What** | Users can "🚩 Báo cáo" toxic pages/domains → reports aggregated on backend into a shared blocklist. New users get warned before loading flagged URLs. |
| **Why** | Community-powered protection. Network effect — more users = better protection for all. |
| **Implementation** | |
| | 1. "🚩 Báo cáo trang này" button in popup |
| | 2. `POST /report` endpoint: `{url, domain, risk_score, reason, timestamp}` |
| | 3. Backend stores reports in SQLite — count per domain |
| | 4. `GET /blocklist` endpoint: returns domains with 5+ reports |
| | 5. Extension checks blocklist periodically (every 6h) |
| | 6. If user navigates to blocklisted domain → show warning banner |
| | 7. Anti-abuse: rate-limit reports per IP, require minimum risk_score |
| **Files** | `api.py`, new `src/utils/blocklist.py`, `popup.js`, `background.js` |
| **Effort** | 3-4 days |
| **Cost** | $0 (SQLite, no extra infra) |
| **Status** | ✅ Completed (v4.9) — CommunityBlocklist class (JSON storage, 5+ report threshold), POST /api/report, GET /api/blocklist, report button in popup, background periodic refresh |

---

### 4.2 — Parental Control Mode
| Field | Detail |
|-------|--------|
| **What** | Special mode: auto-scan all pages, block page if risk > configurable threshold, require password/PIN to bypass. Lock settings behind PIN. |
| **Why** | Parents are a huge target market for content safety tools. Differentiator from competitors. |
| **Implementation** | |
| | 1. "👨‍👩‍👧 Chế độ phụ huynh" in settings, protected by 4-digit PIN |
| | 2. Store PIN hash in `chrome.storage.local` |
| | 3. In `background.js`: intercept all navigations via `chrome.webNavigation.onBeforeNavigate` |
| | 4. Auto-scan page → if risk > threshold → inject blocking overlay |
| | 5. Blocking page: "⚠️ Trang này có nội dung không phù hợp. Nhập mã PIN để tiếp tục." |
| | 6. Configurable: risk threshold slider (default: 60), blocked categories |
| | 7. Activity log for parents to review |
| **Permissions** | `webNavigation`, `declarativeContent` |
| **Files** | `manifest.json`, `background.js`, new `block.html`, `popup.js` |
| **Effort** | 4-5 days |
| **Cost** | $0 |
| **Status** | ✅ Completed (v4.9) — Parental toggle + PIN + risk threshold slider in popup, webNavigation intercept in background.js, block.html with PIN unlock |

---

### 4.3 — Browser-level Content Warning
| Field | Detail |
|-------|--------|
| **What** | Before page fully loads, show an interstitial warning if domain is in blocklist or was previously flagged high-risk. Similar to Chrome's built-in "This site may be harmful" page. |
| **Why** | Proactive vs reactive. Premium feel. Prevents exposure before content is seen. |
| **Implementation** | |
| | 1. Use `chrome.webNavigation.onBeforeNavigate` to intercept navigation |
| | 2. Check domain against: community blocklist + local scan history |
| | 3. If flagged → redirect to `warning.html` with original URL as parameter |
| | 4. Warning page: risk details, "Tiếp tục" (proceed) vs "Quay lại" (go back) |
| | 5. "Tiếp tục" navigates to original URL, marks as acknowledged |
| | 6. Whitelist option: "Luôn cho phép trang này" |
| **Dependencies** | Feature 4.1 (blocklist), Feature 1.1 (scan history) |
| **Files** | `manifest.json`, `background.js`, new `warning.html`, new `warning.js` |
| **Effort** | 2-3 days |
| **Cost** | $0 |
| **Status** | ✅ Completed (v4.9) — warning.html interstitial with domain info + risk + report count, proceed/go-back/whitelist buttons, webNavigation.onCompleted check in background.js |

---

### 4.4 — Weekly Safety Report
| Field | Detail |
|-------|--------|
| **What** | Every Sunday, auto-compile scan statistics: pages checked, threats found, top toxic domains, risk distribution. Show as popup notification or dedicated in-extension report page. |
| **Why** | Engagement driver. Makes users feel actively protected. Encourages continued use. |
| **Implementation** | |
| | 1. `background.js`: `chrome.alarms` API — set weekly alarm (Sunday 10:00 AM) |
| | 2. On alarm: compile stats from `scanHistory` in storage |
| | 3. Stats: total scans, avg risk score, top 5 risky domains, threats blocked |
| | 4. Generate report card → store in storage |
| | 5. Show `chrome.notifications`: "📊 Báo cáo tuần: Bạn đã quét 15 trang, phát hiện 3 mối đe dọa" |
| | 6. Click notification → opens report page `report.html` |
| **Dependencies** | Feature 1.1 (Scan History) |
| **Files** | `background.js`, new `report.html`, new `report.js` |
| **Effort** | 2 days |
| **Cost** | $0 |
| **Status** | ✅ Completed (v4.9) — chrome.alarms weekly alarm, report.html + report.js with stats visualization (risk distribution, top domains, feedback accuracy), notification button to open report |

---

### 4.5 — Gemini 2.5 Flash (Full) — Smart Model Upgrade
| Field | Detail |
|-------|--------|
| **What** | Upgrade default model from `gemini-2.5-flash-lite` to `gemini-2.5-flash` for better accuracy. Auto-fallback to `lite` when quota is exhausted. |
| **Why** | Full Flash model handles nuanced Vietnamese, sarcasm, and context much better. Lite model misses subtle toxicity. |
| **Implementation** | |
| | 1. Change `MODEL_NAME` in `gemini_llm.py` to `gemini-2.5-flash` |
| | 2. Add fallback constant: `MODEL_NAME_FALLBACK = "gemini-2.5-flash-lite"` |
| | 3. In `GeminiAgent._is_quota_error()`: if quota hit on flash → auto-switch to lite |
| | 4. Track which model was used in API response: `"model_used": "gemini-2.5-flash"` |
| | 5. Log model switches for visibility |
| | 6. Same rotation logic — just smarter model selection |
| **Risk** | Flash (full) may have lower RPM/RPD limits. Test with free tier first. |
| **Files** | `src/models/gemini_llm.py`, `api.py` (response field) |
| **Effort** | 2-3 hours |
| **Cost** | $0 (same free tier API) |
| **Status** | ✅ Completed (v4.0) — gemini-2.5-flash primary, flash-lite fallback, _try_fallback_model(), shared key rotator |

---

## 📊 IMPLEMENTATION PRIORITY & TIMELINE

```
WEEK 1 (Feb 13-19):
  ├── 🔴 BUG-01: Fix UI disappearing (service worker)     [CRITICAL]
  ├── 1.4: Dark Mode                                        [3-4 hrs]
  └── 4.5: Gemini Flash upgrade                             [2-3 hrs]

WEEK 2 (Feb 20-26):
  ├── 1.1: Scan History                                     [1 day]
  ├── 1.2: Export Report                                    [1 day]
  └── 3.4: API Stats Dashboard                              [1 day]

WEEK 3-4 (Feb 27 - Mar 12):
  ├── 🧠 ARCH-01: Structured Scraping + Unified Analysis   [10-12 days, MAJOR]
  ├── 2.7: Offline Regex Mode                               [2-3 days]
  └── 1.3: Auto-scan Toggle                                 [1 day]

WEEK 5 (Mar 13-19):
  ├── 1.5: Streaming Results                                [2-3 days]
  └── 3.3: User Feedback Loop                               [2 days]

WEEK 6 (Mar 20-26):
  ├── 2.1: Content Script Overlay                           [3-4 days]
  └── 3.5: Notification System                              [1-2 days]

WEEK 7 (Mar 27 - Apr 2):
  ├── 2.2: YouTube Support                                  [2-3 days]
  └── 2.3: TikTok Support                                   [3-4 days]

WEEK 8 (Apr 3-9):
  ├── 4.1: Community Blocklist                              [3-4 days]
  └── 4.3: Browser Content Warning                          [2-3 days]

WEEK 9 (Apr 10-16):
  ├── 2.5: Comparison Mode                                  [3-4 days]
  ├── 4.2: Parental Control Mode                            [4-5 days]
  └── 4.4: Weekly Safety Report                             [2 days]
```

---

## 💰 COST SUMMARY

| Item | Monthly Cost |
|------|-------------|
| All features (Tier 1-4) | **$0** — all free APIs & existing infra |
| Render upgrade (if needed for PhoBERT/SQLite) | **$7/mo** (optional) |
| YouTube Data API | **Free** (10K units/day) |
| Custom domain (optional) | **~$1/mo** |
| **Total budget needed** | **$0 - $7/mo** |

---

## 📁 NEW FILES FORECAST

After all V4 features, expected new files:
```
extension/
├── background.js          ← Service worker (BUG-01, 1.3, 3.5, 4.2, 4.4)
├── content.js             ← Page overlay (2.1)
├── content.css            ← Overlay styles (2.1)
├── offline_analyzer.js    ← Local regex engine (2.7)
├── warning.html           ← Interstitial warning (4.3)
├── warning.js             ← Warning page logic (4.3)
├── block.html             ← Parental block page (4.2)
├── report.html            ← Weekly report page (4.4)
└── report.js              ← Report logic (4.4)

src/utils/
├── feedback_store.py      ← User feedback storage (3.3)
└── blocklist.py           ← Community blocklist (4.1)
```

---

## 🔖 VERSION PLAN

| Version | Features Included | Target |
|---------|------------------|--------|
| **v4.0** | BUG-01 + 1.4 + 4.5 | Week 1 |
| **v4.1** | 1.1 + 1.2 + 3.4 | Week 2 |
| **v4.2** | 🧠 ARCH-01 (Structured Scraping + Unified Analysis) + 2.7 + 1.3 | Week 3-4 |
| **v4.3** | 1.5 + 3.3 | Week 5 |
| **v4.4** | 2.1 + 3.5 | Week 6 |
| **v4.5** | 2.2 + 2.3 | Week 7 |
| **v4.6** | 4.1 + 4.3 | Week 8 |
| **v4.7** | 2.5 + 4.2 + 4.4 | Week 9 |

---

## 📝 NOTES

- **Always test on Chrome Web Store** after each version push
- **Manifest version bumps** required for each Chrome Web Store upload
- **BUG-01 is the foundation** — Features 1.3, 3.5, 4.2, 4.3, 4.4 all depend on the service worker
- **Keep backward compatibility** with `/analyze/v3` endpoint (don't break existing extension versions)
- **Update `SYSTEM_CONTEXT.md`** after each major version for AI chat continuity

---

## 🧠 MAJOR ARCHITECTURE UPGRADE: Unified Structured Scraping + Single-Pass AI Analysis

### ARCH-01: Structured JSON Scraping + Unified Gemini Analysis

> **This is the most impactful optimization in V4.** It reduces Gemini API calls by 60-80%,
> improves analysis quality through full context awareness, and cuts response latency in half.

---

#### 🔍 PROBLEM ANALYSIS — What's Wrong with the Current Architecture

**Current Data Flow (v3.1):**
```
[Frontend]                              [Backend /analyze/v3]
scrapePageContent()                     Sequential Pipeline:
  → flat string: article_text           ├─ 1. Summary        → 1 Gemini call
  → flat array:  comments[]             ├─ 2. Sentiment      → 0 calls (keywords)
  → POST {url, article_text, comments}  ├─ 3. Toxicity       → 0 calls (regex)
                                        ├─ 4. Fact Check     → 1 Gemini + external APIs
                                        ├─ 5. Risk Score     → 0 calls (computed)
                                        └─ 6. Comments       → 1 Gemini per 25 comments
                                        ────────────────────
                                        Total: 3-5+ Gemini API calls per scan
                                        Latency: 15-60 seconds
```

**5 Core Problems:**

| # | Problem | Impact |
|---|---------|--------|
| 1 | **Flat text = lost context** — Scraper sends raw `innerText` with no structure. Post author, timestamps, reactions, share counts are lost. The AI can't distinguish a news article from a personal rant without this metadata. | Lower analysis accuracy |
| 2 | **Sequential module calls** — Summary, fact check, and comments each make their own separate Gemini call. Each call repeats the article context in its prompt, wasting tokens on redundant input. | 3-5x more API calls than needed |
| 3 | **No cross-module awareness** — When Gemini analyzes comments, it only sees a summary. When it does fact check, it doesn't know if comments are agreeing or disagreeing. Each module operates in isolation. | Misses important signals |
| 4 | **Separate article + comment analysis** — Article is analyzed first (sequential steps 1-5), THEN comments are analyzed separately. A comment saying "tin giả" (fake news) is a strong signal that could boost fact-check confidence — but the current system never connects them. | Wasted intelligence |
| 5 | **Comment text is noisy** — Raw `innerText` includes reaction buttons ("Thích", "Trả lời"), timestamps ("2 giờ trước"), and UI elements mixed into comment text. Backend wastes tokens on garbage. | Wasted tokens + false positives |

---

#### 💡 SOLUTION — Structured JSON Scraping + Single-Pass Unified Analysis

**New Architecture:**
```
[Frontend]                                    [Backend /analyze/v4]
structuredScrape()                            Parallel + Unified:
  → structured JSON with:                    ├─ PARALLEL (no Gemini):
     • page_type                              │  ├─ Regex toxicity (article)
     • article {title, author, date, body}    │  ├─ Keyword sentiment
     • comments [{author, text, reactions}]   │  ├─ Source credibility (domain)
     • metadata {domain, reactions, shares}   │  ├─ Comment pre-filter
                                              │  └─ External APIs (Fact Check, NewsData)
  → POST /analyze/v4 (single JSON)           │
                                              ├─ SINGLE Gemini call (unified):
                                              │  ├─ Article summary
                                              │  ├─ Fact check synthesis
                                              │  ├─ Article toxicity (contextual)
                                              │  ├─ Sentiment refinement
                                              │  └─ ALL comment classifications
                                              │
                                              └─ COMBINE results → response
                                              ────────────────────
                                              Total: 1 Gemini call (down from 3-5+)
                                              Latency: 5-15 seconds (down from 15-60)
```

---

#### 📐 PART A — Structured JSON Scraping (Frontend)

**Current scraper returns:**
```javascript
{ text: "flat string of everything...", comments: ["flat string 1", "flat string 2"] }
```

**New structured scraper returns:**
```javascript
{
  "page_type": "facebook_post",       // "facebook_post" | "news_article" | "youtube_video" | "tiktok" | "generic"
  "url": "https://facebook.com/...",
  "scraped_at": "2026-02-13T10:00:00Z",

  "article": {
    "title": "Phát hiện lừa đảo mới trên mạng xã hội",
    "author": "VnExpress",            // NEW — post/article author
    "published_date": "2026-02-12",   // NEW — when posted/published
    "body": "Nội dung bài viết...",   // Clean text, no UI elements
    "word_count": 450                 // NEW — helps AI calibrate response
  },

  "comments": [
    {
      "text": "Bài viết rất hay, cảm ơn admin!",     // Clean text only
      "author": "Nguyễn Văn A",                      // NEW — commenter name
      "timestamp": "2 giờ trước",                     // NEW — when commented
      "reactions": 15,                                // NEW — engagement signal
      "is_reply": false                               // NEW — reply vs top-level
    },
    {
      "text": "Toàn tin giả, đừng tin",
      "author": "Trần Thị B",
      "timestamp": "1 giờ trước",
      "reactions": 42,                                // High reactions = influential
      "is_reply": false
    }
  ],

  "metadata": {
    "domain": "facebook.com",
    "comment_count_visible": 23,       // How many we captured
    "comment_count_total": 156,        // How many exist on page (if detectable)
    "reactions_total": 1200,           // NEW — post-level engagement
    "shares": 350,                     // NEW — virality signal
    "page_language": "vi"              // NEW — detected language
  }
}
```

**Why structured data matters for AI quality:**
| New Field | AI Benefit |
|-----------|-----------|
| `author` | Known news outlets (VnExpress) vs anonymous accounts → credibility signal |
| `published_date` | AI can check if claims reference future events or outdated info |
| `comment.reactions` | Comment with 500 reactions saying "tin giả" is stronger signal than one with 2 |
| `comment.is_reply` | Reply chains show debate/disagreement patterns |
| `shares` | High shares + low credibility = viral misinformation risk |
| `page_type` | Facebook post vs VnExpress article → different analysis weights |
| `word_count` | Short post (< 50 words) = opinion. Long article (500+) = news. Different standards. |

**Scraper changes:**
- Facebook: Extract `author` from post header, `reactions` from reaction bar, comment authors from `h3`/`span` tags
- News sites: Extract `author` from byline, `published_date` from `time` elements, total comment count from section headers
- Clean text: Strip UI elements (Thích/Trả lời/Chia sẻ/emoji reactions) BEFORE sending to backend
- **Backward compatible**: New scraper output can be flattened to old format for `/analyze/v3`

---

#### 📐 PART B — Unified Single-Pass Gemini Analysis (Backend)

**The Key Insight:** Instead of calling Gemini 3-5 times (summary, fact check, comment batches), send ALL data in ONE prompt and get ONE comprehensive JSON response.

**New endpoint: `POST /analyze/v4`**

**Step 1 — Parallel Pre-Processing (no Gemini, instant):**
```python
# All these run in PARALLEL (asyncio.gather) — zero Gemini calls
regex_toxicity   = toxicity_v3_engine.analyze(article_body)        # Regex only
keyword_sentiment = sentiment_v3_engine.analyze(article_body)      # Keywords only
source_analysis  = source_analyzer.analyze(url)                    # Domain check
comment_filter   = comment_filter.filter_comments(comment_texts)   # Pre-classify
factcheck_api    = factcheck_api.check(article_body)               # Google Fact Check API
newsdata_cross   = newsdata_api.search(article_body)               # NewsData.io
```
**Time: < 2 seconds. API calls: 0 Gemini, 2 external (same as now).**

**Step 2 — Single Unified Gemini Prompt:**
```
Bạn là VnContentGuard Pro AI. Phân tích TOÀN BỘ nội dung sau trong MỘT lần.

═══ DỮ LIỆU TRANG ═══
Loại: facebook_post
URL: https://facebook.com/...
Tác giả: [author]
Ngày đăng: [date]
Lượt chia sẻ: [shares] | Lượt tương tác: [reactions]

─── BÀI VIẾT ───
[article body - max 2000 chars]

─── KẾT QUẢ PHÂN TÍCH SƠ BỘ (đã tính) ───
• Regex toxicity: score=0.2, patterns=[]
• Keyword sentiment: Negative (0.7)
• Domain credibility: vnexpress.net → 95/100 (Đáng tin cậy)
• Google Fact Check API: 2 kết quả liên quan [...]
• NewsData.io: 3 bài đăng tương tự [...]

─── BÌNH LUẬN CẦN PHÂN TÍCH (chỉ ambiguous, đã lọc obvious) ───
1. "Toàn tin giả đừng tin" (👍42, Trần Thị B)
2. "Hay quá cảm ơn" (👍3, Ngọc)
3. "Admin ơi bài này sai rồi" (👍28, Minh)
[... only ambiguous comments, max 30]

═══ TRẢ LỜI (JSON DUY NHẤT) ═══
{
  "summary": "Tóm tắt 2-3 câu",
  "sentiment": {"overall": "Negative", "confidence": 0.82, "intensity": "Strong"},
  "fact_check": {"score": 65, "verdict": "Có thể đúng", "confidence": "Trung bình",
                 "evidence": ["...", "..."]},
  "article_toxicity": {"is_toxic": false, "score": 0.15, "severity": "Low"},
  "comments": [
    {"index": 1, "is_toxic": false, "severity": "none", "sentiment": "negative",
     "reason": "Phản đối nội dung nhưng không xúc phạm"},
    {"index": 2, "is_toxic": false, "severity": "none", "sentiment": "positive",
     "reason": "Bình luận tích cực"},
    {"index": 3, "is_toxic": false, "severity": "none", "sentiment": "negative",
     "reason": "Góp ý nội dung"}
  ],
  "risk_assessment": {"score": 42, "level": "Medium",
                      "warnings": ["Nội dung gây tranh cãi cao"],
                      "recommendations": ["Kiểm tra thêm nguồn tin"]}
}
```

**Why ONE call is better than 5:**

| Metric | Current (v3.1) | Unified (v4) | Improvement |
|--------|---------------|-------------|-------------|
| Gemini API calls | 3-5+ per scan | **1** per scan | **↓ 70-80%** |
| Input tokens (total) | ~12,000 (redundant context per call) | ~5,000 (context sent once) | **↓ 58%** |
| Output tokens | ~3,000 (across multiple responses) | ~2,000 (single structured response) | **↓ 33%** |
| Latency | 15-60s (sequential calls + rate limit sleeps) | **5-15s** (pre-processing parallel + 1 call) | **↓ 60-75%** |
| Rate limit risk | High (each call might hit 429) | **Low** (only 1 call to fail/retry) | **↓ 80%** |
| Cross-module intelligence | None (each module isolated) | **Full** (AI sees everything together) | **↑ Qualitative** |

**Why cross-module context matters (examples):**
- Comment "tin giả rồi" with 200 reactions → AI boosts fact-check skepticism score
- Article has 5000 shares but source credibility = 30 → AI flags viral misinformation
- Multiple comments say "sai thông tin" → AI increases risk score even if article text looks clean
- Post author is verified news page → AI lowers risk score accordingly
- Short post (< 50 words) with strong emotional language → manipulation signal

---

#### 📐 PART C — Backward Compatibility & Fallback Strategy

| Concern | Solution |
|---------|----------|
| `/analyze/v3` still works? | Yes — keep v3 endpoint unchanged. New extension uses `/analyze/v4`. |
| What if unified call fails? | Fallback to current sequential pipeline (v3.1 logic). |
| What if response JSON is malformed? | Parse what we can, fill gaps with pre-computed results (regex, keywords). |
| Token limit exceeded? | If >30 comments ambiguous, chunk into 2 unified calls (still better than 5+ separate). |
| Structured scraper breaks on new site? | Fallback to flat text scraper (current behavior) + old endpoint. |

**Graceful degradation chain:**
```
v4 unified call → if fails → v3.1 sequential pipeline → if fails → regex-only offline mode
```

---

#### 📐 PART D — Token Budget Analysis

**Gemini 2.5 Flash limits:**
- Input: 1,048,576 tokens (massive — no concern)
- Output: 65,536 tokens (way more than we need)
- Free tier: 10 RPM, 20 RPD per key → 30 keys = 600 RPD

**Per-scan token estimate (unified):**
| Component | Input Tokens | Output Tokens |
|-----------|-------------|--------------|
| Prompt template + instructions | ~400 | — |
| Article body (2000 chars) | ~700 | — |
| Pre-computed results (regex, source, APIs) | ~300 | — |
| 30 ambiguous comments (avg 80 chars each) | ~800 | — |
| Metadata (author, reactions, shares) | ~100 | — |
| **Total input** | **~2,300** | — |
| Summary + sentiment + fact check | — | ~300 |
| Comment analysis (30 items) | — | ~600 |
| Risk assessment | — | ~100 |
| **Total output** | — | **~1,000** |
| **Grand total** | **~3,300 tokens per scan** | |

**vs Current v3.1:**
| Call | Input | Output |
|------|-------|--------|
| Summary call | ~1,000 | ~200 |
| Fact check synthesis | ~2,000 | ~400 |
| Comment batch (25 per) | ~2,500 | ~800 |
| Comment batch 2 (if >25) | ~2,500 | ~800 |
| **Total** | **~8,000** | **~2,200** |

**Savings: ~3,300 vs ~10,200 total tokens = 68% reduction.**

---

#### 📐 IMPLEMENTATION PLAN

| Step | Task | Effort | Files |
|------|------|--------|-------|
| A1 | Refactor `scrapePageContent()` → `structuredScrape()` with metadata extraction | 2 days | `popup.js` |
| A2 | Add Facebook-specific metadata extraction (author, reactions, shares, comment authors) | 1 day | `popup.js` |
| A3 | Add news-site metadata extraction (VnExpress/DanTri/TuoiTre: author, date, comment count) | 1 day | `popup.js` |
| A4 | Backward-compat: `structuredScrape()` returns both structured + flat format | 0.5 day | `popup.js` |
| B1 | New `POST /analyze/v4` endpoint with structured input model | 1 day | `api.py` |
| B2 | Parallel pre-processing (asyncio.gather for regex, keywords, source, external APIs) | 1 day | `api.py` |
| B3 | Build unified Gemini prompt template with all context | 1 day | `api.py` or new `src/models/unified_analyzer.py` |
| B4 | Parse unified response + combine with pre-computed results | 1 day | `api.py` |
| B5 | Fallback chain: unified → sequential v3.1 → regex-only | 0.5 day | `api.py` |
| C1 | Update popup.js to use `/analyze/v4` with structured data, fallback to v3 | 0.5 day | `popup.js` |
| C2 | Update result rendering for new response format (if any fields changed) | 0.5 day | `popup.js` |
| D1 | Testing + prompt tuning for quality | 1-2 days | — |
| **Total** | | **~10-12 days** | |

---

#### 📊 SUMMARY TABLE

| Metric | v3.1 Current | v4 Unified | Delta |
|--------|-------------|-----------|-------|
| Gemini calls per scan | 3-5+ | **1** | ↓ 70-80% |
| Total tokens per scan | ~10,200 | **~3,300** | ↓ 68% |
| Latency | 15-60s | **5-15s** | ↓ 60-75% |
| Daily scan capacity (600 RPD) | 120-200 scans | **~550 scans** | ↑ 175-350% |
| Context awareness | Isolated modules | **Full cross-module** | Qualitative ↑ |
| Scraper data richness | Flat text | **Structured with metadata** | Qualitative ↑ |
| Data sent to backend | `{url, text, comments[]}` | **Structured JSON with 15+ fields** | ↑ Much richer |
| Backward compatible | — | **Yes** (v3 endpoint kept) | ✅ |

---

#### 🎯 PRIORITY PLACEMENT

This is a **PHASE 2 feature** — should be implemented in **Week 3-4** after BUG-01 and basic UX features are done, because:
1. It's the single biggest performance + quality improvement in the entire V4 plan
2. Features 1.5 (Streaming), 2.2 (YouTube), 2.3 (TikTok) all benefit from structured scraping
3. It directly reduces API costs and increases daily scan capacity by ~3x
4. But it needs careful prompt engineering and testing — not a quick win
