# V8 Protection Enhancements (SRS + Dev Plan)

## 1) Overview
Protection Enhancements improve safety and detection quality across web content by pre-screening URLs, detecting toxicity in real time, analyzing images, detecting phishing/scam patterns, and updating smart blocklists.

## 2) Scope
- In scope: URL pre-screening, real-time comment toxicity badges, image warning, phishing heuristics, blocklist auto-update.
- Out of scope: server-side scoring at scale, enterprise SIEM integration.

## 3) Functional Requirements

### 3.1 AI URL Pre‑Screening
- Before page load, classify URL and domain using lightweight AI / heuristics.
- Detect redirect chains and flag suspicious hops.

### 3.2 Real‑Time Comment Toxicity Filter
- Inject badges on social platforms (Facebook/YouTube/TikTok).
- Toggle on/off in settings.

### 3.3 Image Content Warning
- Use Vision API to classify thumbnails.
- Warn or blur NSFW/graphic images before display.

### 3.4 Phishing + Scam Detection
- Heuristics:
  - URL entropy and length anomalies
  - Punycode / look‑alike domains
  - Fake brand words
- Optional auto-block or warning.

### 3.5 Smart Blocklist Auto‑Update
- Periodically fetch from GitHub repo.
- Verify signature / checksum before applying.
- Merge with local blocklist without deleting custom entries.

## 4) Non‑Functional Requirements
- Minimal latency impact.
- Works in MV3 (background service worker + content scripts).
- Logs are local only unless explicitly exported.

## 5) Data Model
- urlPreScreenCache: { domain, score, lastChecked }
- imageWarnings: { url, label, ts }
- blocklistUpdates: { sourceUrl, checksum, appliedAt }

## 6) Integration Points
- background.js: pre-screen pipeline, auto-update scheduler.
- content.js: toxicity badges, image warning overlays.
- popup.html/js: toggles, thresholds, alerts.

## 7) Dev Plan (Step-by-step)
1. URL pre-screening classifier (rule + AI).
2. Redirect chain capture + decision logic.
3. Comment toxicity injection for FB/YT/TikTok.
4. Image detection pipeline + blur/warn UI.
5. Phishing heuristics module.
6. Blocklist auto-update scheduler.
7. QA: performance and false positives.

## 8) Success Criteria
- Suspicious URLs are flagged before load.
- Toxicity badges appear reliably in target platforms.
- NSFW image warnings are accurate and non-blocking.
- Blocklist updates apply without disrupting custom rules.
