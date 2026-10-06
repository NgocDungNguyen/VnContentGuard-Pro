# Phụ lục minh chứng: lịch sử phát triển mã nguồn (trích từ Git)

Nguồn: `git log` của kho mã VnContentGuard-Pro (nhánh main). Đây là dấu vết có thật theo thời gian, dùng làm minh chứng bổ sung. Bảng này KHÔNG thay thế sổ nhật ký viết tay.

| Ngày | Nội dung commit |
|---|---|
| 2026-02-13 | fix: major consistency/correctness improvements across all analysis modules |
| 2026-02-13 | style: auto-format all modified files |
| 2026-02-18 | feat(3.4): API Usage Dashboard + article_summarizer_v4 fix |
| 2026-02-18 | fix(3.4): usage counter now tracks real Gemini API calls |
| 2026-02-18 | fix(3.4): show 'used X/45k' instead of 'remaining' to make changes visible |
| 2026-02-18 | feat: longer article summaries (12-15 sentences, 1500+ chars, 4096 tokens) |
| 2026-02-18 | chore: remove v3 files  keep only v4 |
| 2026-02-18 | chore: final v4.9 extension audit  fix all version strings, create Chrome Web Store zip |
| 2026-02-18 | docs: add full Chrome Web Store description for v4.9 (Vietnamese + English) |
| 2026-02-19 | fix: remove unused downloads permission + localhost endpoints for Chrome Web Store approval |
| 2026-02-21 | fix: update render.yaml - use PORT env var, remove build-only scope |
| 2026-02-21 | fix: remove 4-layer false claim in popup.html for Chrome Web Store compliance |
| 2026-02-21 | fix: increase scan timeouts, add server warm-up & keep-alive to prevent Render cold-start failures |
| 2026-02-24 | feat: initial v5 setup - rename files and update versions |
| 2026-02-24 | feat: complete api.py v5 migration |
| 2026-02-24 | chore: update background.js endpoints to v5 |
| 2026-02-24 | chore: complete v4->v5 migration - rename all files, classes, variables |
| 2026-02-24 | feat(ARCH-01): unified structured scraping + single-pass Gemini analysis |
| 2026-02-24 | feat(2.1): content script overlay - floating risk badge + toxic comment highlights |
| 2026-02-24 | feat(2.2+2.3): YouTube and TikTok scraping support |
| 2026-02-24 | fix: storage key bugs + YouTube/TikTok auto-scrape upgrade |
| 2026-02-24 | fix: syntax error in structuredScrapePageContent generic else branch |
| 2026-02-24 | docs: update V5 setup status |
| 2026-02-24 | chore: merge v5-enhancement into main - all 20 v5 features complete |
| 2026-02-24 | fix: overlay CSS race + dark mode colors + shareEl bug + cleanup v4.9 refs |
| 2026-02-24 | chore: overlay fix + dark mode + shareEl + v4.9 cleanup (v5.0.1) |
| 2026-02-24 | fix: shorten manifest description to 126 chars (Chrome Store limit 132) |
| 2026-02-24 | fix: shorten manifest description for Chrome Store (126/132 chars) |
| 2026-02-25 | docs: V6 upgrade plan - 6 features (blacklist, explainable AI, incognito, reranker, scam report, bulk analysis) |
| 2026-02-25 | chore: complete v5->v6 migration - rename all files, classes, endpoints, variables |
| 2026-02-25 | chore: remove old zip files and temp scripts |
| 2026-02-25 | feat(v6): implement features 6.2 Domain Blacklist/Whitelist, 6.3 Explainable AI, 6.6 Incognito Detection |
| 2026-02-25 | style: apply Black formatter to api.py and unified_analyzer.py |
| 2026-02-25 | chore: merge v6-enhancement - v5->v6 migration + features 6.2 6.3 6.6 |
| 2026-02-25 | fix: limit AI summary to max 4 sentences in prompt + client-side 5-sentence safety cap |
| 2026-02-25 | fix: shorten AI summary (prompt + client cap) |
| 2026-02-25 | feat(v6): implement features 6.9 reranker + 6.12 scam report + 6.13 bulk analysis |
| 2026-02-25 | chore(ui): unify all version labels to v6 across extension files |
| 2026-02-25 | chore(ui): remove legacy Feature X.Y labels from section headers |
| 2026-02-25 | chore(ui): fix corrupted em-dash and remove legacy Feature labels in CSS |
| 2026-02-25 | docs: add Chrome Web Store description for v6.0 |
| 2026-02-28 | docs: fix Chrome store description - remove keyword stuffing per policy Yellow Argon |
| 2026-02-28 | a |
| 2026-03-01 | docs: add comprehensive project documentation (architecture, tech stack, version history) |
| 2026-03-06 | feat: branch v7-enhancement — rename all V6 identifiers, files, and references to V7 |
| 2026-03-06 | feat(v7): UI redesign — hamburger nav, result tabs, remove tech jargon, unify fonts |
| 2026-03-06 | feat(v7): clean tech terms, dropdown tooltips+desc, version footer, fix summary tab |
| 2026-03-06 | fix: V7 URL uppercase 404 + APIKeyRotator wrong method names |
| 2026-03-06 | feat: merge v7-enhancement — V7 rename, UI redesign, bug fixes |
| 2026-03-06 | fix: remaining V7 uppercase URL, v6.0 version strings in stats + export check |
| 2026-03-10 | fix: migrate unified_analyzer from google-generativeai to google-genai SDK |
| 2026-03-10 | fix: add Mixed/Very sentiment labels, fix evidence string rendering |
| 2026-03-10 | fix: switch to gemini-2.0-flash, increase max_output_tokens, add error diagnostics |
| 2026-03-10 | fix: switch to gemini-1.5-flash (free tier), fix 429 key rotation |
| 2026-03-10 | fix: switch to gemini-2.0-flash-lite (v1beta free tier) |
| 2026-03-10 | fix: revert to gemini-2.5-flash, disable thinking to fix token exhaustion |
| 2026-03-12 | fix: update extension version strings for v7 consistency |
| 2026-03-12 | fix: implement Google Fact Check + NewsData.io + GNews API calls |
| 2026-03-12 | feat: add clickable source citations to fact-check evidence |
| 2026-03-12 | ui: redesign fact-check evidence as source cards with header/rating/button |
| 2026-03-12 | chore: stage local edits to fact_checker_v7 and unified_analyzer |
| 2026-03-12 | fix: evidence shows only real direct URLs (no Google fallback), full dark mode support for evidence cards and toxic comment cards |
| 2026-03-12 | fix: restore block.html with clean UTF-8 encoding (was mojibake) |
| 2026-03-12 | feat: parental control PIN-gated auth flow with setup wizard, stats dashboard, secret triple-click access |
| 2026-03-13 | fix: parental control UI overhaul v7.2 — tabs, z-index 10000, dark mode, body-level overlay, dropdown close |
| 2026-03-13 | ui: enlarge and make parental PIN modal responsive |
| 2026-03-13 | docs: add V8 SRS plans for student, parental, and protection enhancements |
| 2026-03-13 | feat: add student Focus Mode with rules, overlay, and reports |
| 2026-03-13 | feat: add parent/student/general sections and parent tools UI |
| 2026-03-13 | feat: add pause/resume, session history, parent filters, and general impact/admin |
| 2026-03-13 | feat: add focus session detail, parent email flow, and community stats sync |
| 2026-03-13 | feat: add focus filters, schedule presets, and impact refresh |
