# 🛡️ VNCONTENTGUARD PRO — V6 UPGRADE PLAN
### Version: 6.0.0 | Planned Start: March 2026
### Tracking Document — Update status as each feature is completed
### Base: v5.0.0 (all 20 v5 features complete, deployed on Render, Chrome Store)

---

## 📋 OVERVIEW

| Feature ID | Name | Priority | Effort | Phase |
|------------|------|----------|--------|-------|
| 6.2 | Domain Whitelist + Blacklist (Manual Parental Block) | 🔴 P0 | 3 days | 1 |
| 6.3 | Explainable AI — Highlight Evidence | 🔴 P0 | 4 days | 1 |
| 6.6 | Incognito Mode Detection | 🟡 P1 | 2 days | 2 |
| 6.9 | User Correction + Model Re-Ranking | 🟡 P1 | 5 days | 2 |
| 6.12 | Scam URL Database Contribution | 🟡 P1 | 3 days | 2 |
| 6.13 | Bulk Analysis Mode | 🟢 P2 | 5 days | 3 |

---

## 📋 LEGEND

| Symbol | Status |
|--------|--------|
| ⬜ | Not started |
| 🔄 | In progress |
| ✅ | Completed |
| ❌ | Cancelled / Deferred |

---

## PHASE 1 — Core Parental Protection + AI Transparency (Week 1–2)

---

### 6.2 — Domain Whitelist + Blacklist (Manual Parental Block)

| Field | Detail |
|-------|--------|
| **What** | Two-way manual domain control panel for parents: **Blacklist** = domains permanently blocked (porn, gambling, betting, adult content) regardless of AI score. **Whitelist** = domains always trusted, never scanned. Both lists manually curated by parent with PIN protection. |
| **Why** | Parents need absolute, deterministic control that does NOT rely on AI scoring. A site like `xvideos.com` should be blocked 100% of the time — not dependent on whether Gemini happens to flag it on a given day. Current AI-based blocking is probabilistic and has false negatives on adult domains. |
| **User Story** | Parent opens extension → Settings → "Kiểm soát nội dung" → enters PIN → sees Blacklist + Whitelist tabs → types in `xvideos.com`, `sunwin.me`, `fb88.net` → clicks "Thêm vào danh sách đen" → from this moment, any attempt to open those domains is intercepted and redirected to `block.html` with "Trang này bị chặn bởi phụ huynh." |

#### Implementation — Backend (api.py)

No backend changes required for core block functionality. All blocking is local/client-side.

Optional: Add `/api/blacklist/community-porn` endpoint returning a curated seed list of ~500 known Vietnamese adult/gambling domains to pre-populate the blacklist on first install.

```python
# api.py addition
SEED_BLACKLIST = [
    "xvideos.com", "xnxx.com", "pornhub.com", "xhamster.com",
    "sunwin.me", "fb88.net", "w88.com", "bet365vn.com",
    "68gamebai.com", "789club.me", "rikvip.net",
    # ... expand to 500+ Vietnamese-focused list
]

@app.get("/api/blacklist/seed")
async def get_seed_blacklist():
    return {"domains": SEED_BLACKLIST, "version": "1.0", "count": len(SEED_BLACKLIST)}
```

#### Implementation — Extension

**New file: `extension/domain_control.js`**
```javascript
// DomainControl — manages whitelist and blacklist
// All operations require PIN verification if parentalControlEnabled

const DomainControl = {
  async getBlacklist() {
    const data = await chrome.storage.local.get('domainBlacklist');
    return data.domainBlacklist || [];
  },
  async getWhitelist() {
    const data = await chrome.storage.local.get('domainWhitelist');
    return data.domainWhitelist || [];
  },
  async addToBlacklist(domain) {
    const list = await this.getBlacklist();
    const clean = this.cleanDomain(domain);
    if (!list.includes(clean)) {
      list.push(clean);
      await chrome.storage.local.set({ domainBlacklist: list });
    }
    return list;
  },
  async removeFromBlacklist(domain) { ... },
  async addToWhitelist(domain) { ... },
  async removeFromWhitelist(domain) { ... },
  cleanDomain(input) {
    // Accepts full URLs or bare domains, strips protocol/path/www
    try { return new URL(input.startsWith('http') ? input : 'https://'+input).hostname.replace(/^www\./, ''); }
    catch { return input.toLowerCase().trim(); }
  },
  async isBlacklisted(url) {
    const domain = this.cleanDomain(url);
    const list = await this.getBlacklist();
    return list.some(d => domain === d || domain.endsWith('.'+d));
  },
  async isWhitelisted(url) { ... },
  async importFromText(text) {
    // Parse newline/comma separated list, bulk-add
    const domains = text.split(/[\n,]+/).map(d => d.trim()).filter(Boolean);
    for (const d of domains) await this.addToBlacklist(d);
    return domains.length;
  },
  async exportToText(listType) {
    const list = listType === 'black' ? await this.getBlacklist() : await this.getWhitelist();
    return list.join('\n');
  }
};
```

**`extension/background.js` changes:**
```javascript
// In chrome.tabs.onUpdated listener — BEFORE any other check:
const isBlocked = await DomainControl.isBlacklisted(tab.url);
if (isBlocked && parentalControlEnabled) {
  chrome.tabs.update(tabId, {
    url: chrome.runtime.getURL('block.html') + '?reason=blacklist&blockedUrl=' + encodeURIComponent(tab.url)
  });
  return;
}

// Also add to chrome.webNavigation.onBeforeNavigate for faster interception:
chrome.webNavigation.onBeforeNavigate.addListener(async (details) => {
  if (details.frameId !== 0) return; // main frame only
  const isBlocked = await DomainControl.isBlacklisted(details.url);
  const { parentalControlEnabled } = await chrome.storage.local.get('parentalControlEnabled');
  if (isBlocked && parentalControlEnabled) {
    chrome.tabs.update(details.tabId, { url: chrome.runtime.getURL('block.html') + '?reason=blacklist&blockedUrl=' + encodeURIComponent(details.url) });
  }
}, { url: [{ schemes: ['http', 'https'] }] });
```

**`extension/popup.js` + `popup.html` changes:**
- Add "🚫 Danh sách đen" and "✅ Danh sách trắng" tabs inside the "Kiểm soát phụ huynh" section
- Each tab shows:
  - Input box: "Nhập tên miền hoặc URL..." + "Thêm" button
  - Bulk import textarea + "Nhập hàng loạt" button
  - Domain list with 🗑 delete button per entry, domain count badge
  - "📥 Xuất danh sách" button → downloads `.txt` file
  - "📤 Nhập từ file" button → uploads `.txt` file
  - "⬇️ Tải danh sách mẫu độc hại" button → fetches seed list from `/api/blacklist/seed`

**`extension/block.html` changes:**
- Detect `?reason=blacklist` param
- Show different message: "🚫 Trang này bị chặn bởi phụ huynh" vs current AI-detection block
- Show which blacklist category (manually added vs community seed list)
- "🔓 Mở khóa tạm thời (nhập PIN)" option

**`extension/style.css` additions:**
```css
/* Domain control tabs */
.domain-control-tabs { display: flex; gap: 4px; margin-bottom: 8px; }
.domain-tab-btn { flex: 1; padding: 6px; border-radius: 6px; font-size: 12px; border: 1px solid var(--border); cursor: pointer; }
.domain-tab-btn.active { background: var(--danger); color: white; border-color: var(--danger); }
.domain-list { max-height: 150px; overflow-y: auto; margin: 6px 0; }
.domain-item { display: flex; justify-content: space-between; align-items: center; padding: 4px 8px; background: var(--card-bg); border-radius: 4px; margin-bottom: 2px; font-size: 12px; }
.domain-item .remove-btn { background: none; border: none; color: var(--danger); cursor: pointer; font-size: 14px; }
/* Dark mode */
.dark-mode .domain-tab-btn.active { background: #c0392b; }
```

#### Data Schema
```javascript
// chrome.storage.local
{
  domainBlacklist: ["xvideos.com", "fb88.net", "sunwin.me", ...],
  domainWhitelist: ["hocmai.vn", "violet.vn", "khan.academy.vn", ...],
  blacklistSeedVersion: "1.0",  // tracks which seed version is installed
  blacklistAddedAt: { "xvideos.com": 1740000000000, ... }  // timestamps for audit
}
```

#### Edge Cases & Notes
- **Subdomain matching**: `xvideos.com` in blacklist blocks `www.xvideos.com`, `m.xvideos.com`, `en.xvideos.com` etc.
- **PIN gate**: All add/remove/import/export operations check `parentalControlEnabled` — if enabled, require PIN before modifying lists
- **Seed list import**: First install with parental control ON → prompt "Bạn có muốn tải 500+ miền độc hại/cờ bạc phổ biến?" → one-click import
- **cannot be bypassed by clearing popup** — blocking intercepts at `webNavigation` level, not just popup level
- **Whitelist priority**: If domain is in both lists (user error), whitelist wins (safe default)

| Field | Detail |
|-------|--------|
| **Files** | `extension/domain_control.js` (new), `extension/background.js`, `extension/popup.html`, `extension/popup.js`, `extension/block.html`, `extension/style.css`, `api.py` (optional seed endpoint) |
| **Effort** | 3 days |
| **Dependencies** | Existing parental control PIN system (v5.0), existing `block.html` |
| **Status** | ⬜ Not started |

---

### 6.3 — Explainable AI (Highlight Evidence)

| Field | Detail |
|-------|--------|
| **What** | After scanning, the system shows users EXACTLY which words/phrases triggered the toxicity, misleading, and emotional manipulation flags. In the popup: inline-highlighted text snippets. On the page via content.js overlay: actual DOM text nodes are color-highlighted with tooltip explanations. |
| **Why** | "Why is this flagged?" is the #1 user frustration with AI moderation. A score of "Rủi ro: 74/100" means nothing if users don't know what triggered it. Evidence display: (1) builds trust in the system, (2) educates users to recognize harmful patterns, (3) reduces false positive complaints, (4) makes the tool genuinely useful for teachers/journalists. |
| **User Story** | User scans a Facebook post with toxic comments. The popup shows comments with specific phrases highlighted in red: "**[đồ ngu]** → xúc phạm cá nhân" and "[chết đi cho rồi] → kêu gọi bạo lực". On the page itself, those comment boxes get a red left border and hovering shows: "⚠️ Từ ngữ độc hại phát hiện: 'đồ ngu' (xúc phạm), 'chết đi' (bạo lực)". |

#### Implementation — Backend (api.py + unified_analyzer.py)

**`src/models/unified_analyzer.py` prompt extension:**
```python
# Add to the existing unified prompt — request evidence in structured format:
PROMPT_EVIDENCE_SECTION = """
For EACH flagged comment, provide evidence in this exact format:
"evidence": {
  "toxic_spans": [
    {"text": "exact phrase from comment", "reason": "xúc phạm/bạo lực/phân biệt/quấy rối", "severity": "high|medium|low"},
    ...
  ],
  "misleading_claims": [
    {"text": "exact claim text", "reason": "thiếu bằng chứng/sai sự thật/phóng đại"},
    ...
  ],
  "emotional_manipulation": [
    {"text": "exact phrase", "technique": "tạo sợ hãi/kích động/thao túng cảm xúc"}
  ]
}

For the article body, provide:
"article_evidence": {
  "misleading_claims": [...],
  "emotional_manipulation": [...],
  "unverified_statistics": [{"text": "con số/thống kê", "issue": "không có nguồn"}]
}
"""
```

**`api.py` response structure extension:**
```python
# /analyze/v5/unified response now includes:
{
  "comments": [
    {
      "text": "original comment",
      "toxicity_score": 0.85,
      "evidence": {
        "toxic_spans": [
          {"text": "đồ ngu", "reason": "xúc phạm cá nhân", "severity": "high"},
          {"text": "chết đi", "reason": "kêu gọi bạo lực", "severity": "high"}
        ],
        "emotional_manipulation": []
      }
    }
  ],
  "article_evidence": {
    "misleading_claims": [...],
    "unverified_statistics": [...],
    "emotional_manipulation": [...]
  }
}
```

#### Implementation — Extension

**`extension/popup.js` — `renderComments()` function update:**
```javascript
function renderCommentWithEvidence(comment) {
  let displayText = comment.text;
  const spans = comment.evidence?.toxic_spans || [];
  
  // Highlight evidence spans in comment text
  spans.sort((a, b) => b.text.length - a.text.length); // longest first to avoid overlapping replacements
  for (const span of spans) {
    const colorClass = span.severity === 'high' ? 'evidence-high' : span.severity === 'medium' ? 'evidence-medium' : 'evidence-low';
    const escaped = span.text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    displayText = displayText.replace(
      new RegExp(escaped, 'gi'),
      `<mark class="evidence-mark ${colorClass}" title="${span.reason}">$&</mark>`
    );
  }
  
  // Build evidence badges below comment
  const evidenceTags = spans.map(s => 
    `<span class="evidence-tag severity-${s.severity}">⚠️ ${s.text}: ${s.reason}</span>`
  ).join('');
  
  return `
    <div class="comment-card ${comment.toxicity_score > 0.7 ? 'toxic' : ''}">
      <p class="comment-text">${displayText}</p>
      ${evidenceTags ? `<div class="evidence-tags">${evidenceTags}</div>` : ''}
    </div>
  `;
}
```

**`extension/content.js` — overlay highlight update:**
```javascript
// When receiving SHOW_OVERLAY with evidence data:
function highlightEvidenceOnPage(comments) {
  for (const comment of comments) {
    const spans = comment.evidence?.toxic_spans || [];
    if (!spans.length) continue;
    
    // Find this comment's DOM node (match by text content)
    const allTextNodes = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    let node;
    while (node = allTextNodes.nextNode()) {
      if (node.textContent.includes(comment.text.substring(0, 50))) {
        const parent = node.parentElement;
        parent.classList.add('vcg-comment-highlighted');
        
        // Add per-span highlights using innerHTML replacement
        let html = parent.innerHTML;
        for (const span of spans) {
          const escaped = span.text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
          html = html.replace(
            new RegExp(`(${escaped})`, 'gi'),
            `<span class="vcg-evidence-span vcg-evidence-${span.severity}" 
                   data-reason="${span.reason}"
                   onmouseenter="vcgShowEvidenceTooltip(this)" 
                   onmouseleave="vcgHideTooltip()">$1</span>`
          );
        }
        parent.innerHTML = html;
        break;
      }
    }
  }
}

// Global tooltip functions injected into page
function vcgShowEvidenceTooltip(el) {
  const tooltip = document.createElement('div');
  tooltip.className = 'vcg-evidence-tooltip';
  tooltip.textContent = '⚠️ ' + el.dataset.reason;
  document.body.appendChild(tooltip);
  const rect = el.getBoundingClientRect();
  tooltip.style.cssText = `position:fixed;top:${rect.top-30}px;left:${rect.left}px;z-index:2147483647;`;
}
```

**`extension/style.css` additions:**
```css
/* Evidence highlighting in popup */
.evidence-mark { border-radius: 2px; padding: 0 2px; cursor: help; }
.evidence-mark.evidence-high { background: rgba(231,76,60,0.3); border-bottom: 2px solid #e74c3c; }
.evidence-mark.evidence-medium { background: rgba(230,126,34,0.25); border-bottom: 2px solid #e67e22; }
.evidence-mark.evidence-low { background: rgba(241,196,15,0.25); border-bottom: 2px solid #f1c40f; }

.evidence-tags { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 6px; }
.evidence-tag { font-size: 10px; padding: 2px 6px; border-radius: 10px; }
.evidence-tag.severity-high { background: rgba(231,76,60,0.15); color: #c0392b; border: 1px solid rgba(231,76,60,0.3); }
.evidence-tag.severity-medium { background: rgba(230,126,34,0.15); color: #d35400; border: 1px solid rgba(230,126,34,0.3); }
.evidence-tag.severity-low { background: rgba(241,196,15,0.15); color: #b7950b; border: 1px solid rgba(241,196,15,0.3); }

/* On-page evidence spans (injected by content.js) */
.vcg-evidence-span { border-radius: 2px; padding: 1px 2px; cursor: help; transition: opacity 0.2s; }
.vcg-evidence-span.vcg-evidence-high { background: rgba(231,76,60,0.35); border-bottom: 2px solid #e74c3c; }
.vcg-evidence-span.vcg-evidence-medium { background: rgba(230,126,34,0.3); border-bottom: 2px solid #e67e22; }
.vcg-evidence-span.vcg-evidence-low { background: rgba(241,196,15,0.25); border-bottom: 2px solid #f1c40f; }
.vcg-evidence-tooltip { background: #2c3e50; color: white; padding: 4px 10px; border-radius: 6px; font-size: 12px; pointer-events: none; box-shadow: 0 2px 8px rgba(0,0,0,0.3); }

/* Dark mode overrides */
.dark-mode .evidence-mark.evidence-high { background: rgba(231,76,60,0.45); }
.dark-mode .evidence-tag.severity-high { background: rgba(231,76,60,0.25); color: #f1948a; }
```

**`extension/popup.html` additions:**
- Add evidence legend section in results:
  ```html
  <div class="evidence-legend" id="evidenceLegend" style="display:none">
    <span style="font-size:11px;color:var(--text-secondary)">Chú thích bằng chứng:</span>
    <span class="evidence-tag severity-high">🔴 Cao</span>
    <span class="evidence-tag severity-medium">🟠 TB</span>
    <span class="evidence-tag severity-low">🟡 Thấp</span>
  </div>
  ```

#### Fallback (when Gemini doesn't return evidence)
If `evidence` field is missing from API response, fall back to client-side regex matching against the 500+ pattern library in `offline_analyzer.js`. This ensures evidence always displays even when unified endpoint is unavailable.

| Field | Detail |
|-------|--------|
| **Files** | `src/models/unified_analyzer.py`, `api.py`, `extension/popup.js`, `extension/content.js`, `extension/content.css`, `extension/style.css`, `extension/popup.html` |
| **Effort** | 4 days |
| **Dependencies** | Unified analyzer v5 (done), content script overlay v5 (done) |
| **Status** | ⬜ Not started |

---

## PHASE 2 — Parental Safety + Learning System (Week 3–4)

---

### 6.6 — Incognito Mode Detection

| Field | Detail |
|-------|--------|
| **What** | When parental control is active and a new incognito window opens, the extension detects it and: (1) shows a full-screen overlay in that window warning that the session is being logged, (2) optionally blocks navigation entirely until PIN is entered, (3) logs the attempt to `incognitoLog` in storage so parents can see it later. |
| **Why** | Kids know that incognito bypasses most browser history. This is the primary loophole in v5 parental control. Closing this loophole significantly increases protection. Chrome extensions CAN run in incognito if `"incognito": "spanning"` or `"split"` is declared in manifest. |
| **Technical Constraint** | Chrome doesn't allow extensions to fully BLOCK incognito window creation. However, we CAN: detect incognito tabs, inject content scripts into them, intercept navigation, and show warnings/blocks. The `"incognito": "spanning"` manifest setting makes the extension run in incognito with the same background worker. |

#### Implementation

**`extension/manifest.json` change:**
```json
{
  "incognito": "spanning"
}
```
This makes `background.js` service worker handle both normal and incognito tabs.

**`extension/background.js` additions:**
```javascript
// Detect new incognito tab
chrome.tabs.onCreated.addListener(async (tab) => {
  if (!tab.incognito) return;
  const { parentalControlEnabled } = await chrome.storage.local.get('parentalControlEnabled');
  if (!parentalControlEnabled) return;
  
  // Log the attempt
  const log = (await chrome.storage.local.get('incognitoLog')).incognitoLog || [];
  log.unshift({ timestamp: Date.now(), tabId: tab.id, url: tab.url || 'new tab' });
  if (log.length > 50) log.pop(); // keep last 50 entries
  await chrome.storage.local.set({ incognitoLog: log });
  
  // Update badge on action icon to warn parent
  chrome.action.setBadgeText({ text: '⚠' });
  chrome.action.setBadgeBackgroundColor({ color: '#e67e22' });
  
  // Send notification to parent
  chrome.notifications.create({
    type: 'basic',
    iconUrl: 'icons/icon48.png',
    title: '⚠️ VnContentGuard Pro',
    message: 'Phát hiện cửa sổ ẩn danh! Mở VnContentGuard để xem chi tiết.',
    priority: 2
  });
});

// Intercept ALL navigation in incognito tabs
chrome.webNavigation.onBeforeNavigate.addListener(async (details) => {
  if (details.frameId !== 0) return;
  
  const tab = await chrome.tabs.get(details.tabId);
  if (!tab.incognito) return;
  
  const { parentalControlEnabled, incognitoBlockMode } = await chrome.storage.local.get(['parentalControlEnabled', 'incognitoBlockMode']);
  if (!parentalControlEnabled) return;
  
  if (incognitoBlockMode === 'block_all') {
    // Redirect everything to warning page
    chrome.tabs.update(details.tabId, {
      url: chrome.runtime.getURL('block.html') + '?reason=incognito&blockedUrl=' + encodeURIComponent(details.url)
    });
  } else if (incognitoBlockMode === 'warn_only') {
    // Inject warning banner into the page via content script
    chrome.scripting.executeScript({
      target: { tabId: details.tabId },
      func: injectIncognitoWarning
    });
  }
}, { url: [{ schemes: ['http', 'https'] }] });

function injectIncognitoWarning() {
  if (document.getElementById('vcg-incognito-banner')) return;
  const banner = document.createElement('div');
  banner.id = 'vcg-incognito-banner';
  banner.style.cssText = 'position:fixed;top:0;left:0;right:0;z-index:2147483647;background:#e67e22;color:white;padding:10px 16px;font-family:sans-serif;font-size:14px;display:flex;justify-content:space-between;align-items:center;box-shadow:0 2px 8px rgba(0,0,0,0.3)';
  banner.innerHTML = `
    <span>⚠️ <strong>VnContentGuard Pro:</strong> Hoạt động ẩn danh đang được ghi lại bởi kiểm soát phụ huynh.</span>
    <button onclick="this.parentElement.remove()" style="background:rgba(255,255,255,0.3);border:none;color:white;padding:4px 10px;border-radius:4px;cursor:pointer">✕</button>
  `;
  document.body.insertBefore(banner, document.body.firstChild);
  document.body.style.marginTop = (document.body.style.marginTop || '0px').replace(/\d+/, n => parseInt(n) + 44);
}
```

**`extension/popup.js` + `popup.html` — Settings panel addition:**
```html
<!-- Inside parental control section -->
<div class="setting-row" id="incognitoControlRow">
  <label>🕵️ Chế độ ẩn danh</label>
  <select id="incognitoBlockMode">
    <option value="off">Không làm gì</option>
    <option value="warn_only">Hiện cảnh báo</option>
    <option value="block_all" selected>Chặn hoàn toàn</option>
  </select>
</div>
<div class="incognito-log-row" id="incognitoLogRow">
  <span id="incognitoLogCount">0 lần mở ẩn danh</span>
  <button id="viewIncognitoLog">📋 Xem nhật ký</button>
  <button id="clearIncognitoLog">🗑️ Xóa</button>
</div>
```

**`extension/block.html` — Add incognito branch:**
```javascript
if (reason === 'incognito') {
  titleEl.textContent = '🕵️ Chế độ ẩn danh bị hạn chế';
  msgEl.textContent = 'Kiểm soát phụ huynh đang hoạt động. Cửa sổ ẩn danh đã bị chặn. Hành động này đã được ghi lại.';
}
```

#### Privacy Note
The incognito log stores only: timestamps and attempted URLs. No page content is stored. Parents see entries like: `"2026-03-01 14:32 — Mở cửa sổ ẩn danh → https://..."`. Log is stored locally in `chrome.storage.local`, never sent to server.

| Field | Detail |
|-------|--------|
| **Files** | `extension/manifest.json`, `extension/background.js`, `extension/popup.html`, `extension/popup.js`, `extension/block.html`, `extension/style.css` |
| **Effort** | 2 days |
| **Dependencies** | Existing parental control PIN (v5.0), `chrome.webNavigation` permission (already in manifest) |
| **Status** | ⬜ Not started |

---

### 6.9 — User Correction + Model Re-Ranking

| Field | Detail |
|-------|--------|
| **What** | Two-part system: (1) **Improved feedback collection** — after each scan, users can correct wrong scores with a specific reason. (2) **Re-ranking layer** — backend aggregates corrections per domain/content-type and applies a learned adjustment (+/- up to 20 points) to future Gemini outputs for similar content. |
| **Why** | Gemini is trained on global data and misses Vietnamese cultural context — sarcasm, slang, regional dialects, tone-specific toxicity. Each user correction is a training signal. After 1000+ corrections, the system becomes measurably better at Vietnamese content than stock Gemini. This creates a long-term competitive moat. |

#### Implementation — Backend

**New file: `src/models/reranker.py`**
```python
import json, os, statistics
from pathlib import Path
from collections import defaultdict

class ScoreReranker:
    """
    Lightweight domain+category re-ranker.
    
    For each (domain, category) pair, stores:
    - raw_scores_given: list of Gemini's scores
    - user_corrected_scores: list of user's corrections
    
    Adjustment = mean(user_corrections) - mean(gemini_scores)
    Capped at ±20 points, only applied when n >= MIN_SAMPLES (5)
    """
    
    MIN_SAMPLES = 5
    MAX_ADJUSTMENT = 20
    DATA_FILE = Path(os.getenv('RERANKER_DATA', '/opt/render/project/src/reranker_data.json'))
    
    def __init__(self):
        self.data = self._load()
    
    def _load(self):
        try:
            return json.loads(self.DATA_FILE.read_text())
        except:
            return {}
    
    def _save(self):
        self.DATA_FILE.write_text(json.dumps(self.data, ensure_ascii=False))
    
    def record_correction(self, domain: str, category: str, gemini_score: float, user_score: float):
        key = f"{domain}:{category}"
        if key not in self.data:
            self.data[key] = {"gemini": [], "user": []}
        self.data[key]["gemini"].append(gemini_score)
        self.data[key]["user"].append(user_score)
        # Keep only last 200 samples per key
        for k in ["gemini", "user"]:
            if len(self.data[key][k]) > 200:
                self.data[key][k] = self.data[key][k][-200:]
        self._save()
    
    def get_adjustment(self, domain: str, category: str) -> float:
        key = f"{domain}:{category}"
        entry = self.data.get(key, {})
        gemini = entry.get("gemini", [])
        user = entry.get("user", [])
        if len(gemini) < self.MIN_SAMPLES or len(user) < self.MIN_SAMPLES:
            return 0.0
        adjustment = statistics.mean(user) - statistics.mean(gemini)
        return max(-self.MAX_ADJUSTMENT, min(self.MAX_ADJUSTMENT, adjustment))
    
    def apply(self, domain: str, results: dict) -> dict:
        """Apply learned adjustments to a full scan result."""
        adjusted = dict(results)
        risk_adj = self.get_adjustment(domain, "risk_score")
        tox_adj = self.get_adjustment(domain, "toxicity")
        adjusted["risk_score"] = max(0, min(100, results.get("risk_score", 0) + risk_adj))
        adjusted["reranker_applied"] = abs(risk_adj) >= 1 or abs(tox_adj) >= 1
        adjusted["reranker_adjustments"] = {
            "risk_score": round(risk_adj, 1),
            "toxicity": round(tox_adj, 1),
            "samples": len(self.data.get(f"{domain}:risk_score", {}).get("gemini", []))
        }
        return adjusted
```

**`api.py` changes:**
```python
# Add new correction endpoint
class CorrectionRequest(BaseModel):
    url: str
    domain: str
    original_risk_score: float
    corrected_risk_score: float
    original_toxicity: float
    corrected_toxicity: float
    reason: str  # "too_high" | "too_low" | "wrong_category" | "cultural_context"
    category: str  # "news" | "social" | "video" | "other"
    examples: List[str] = []  # specific phrases AI got wrong

@app.post("/api/correction")
async def submit_correction(req: CorrectionRequest):
    reranker.record_correction(req.domain, "risk_score", req.original_risk_score, req.corrected_risk_score)
    reranker.record_correction(req.domain, "toxicity", req.original_toxicity, req.corrected_toxicity)
    # Also save raw correction to feedback store for future model training
    feedback_store.save({
        "type": "correction",
        "url_hash": hashlib.md5(req.url.encode()).hexdigest(),
        "domain": req.domain,
        "delta_risk": req.corrected_risk_score - req.original_risk_score,
        "reason": req.reason,
        "examples": req.examples,
        "timestamp": datetime.now().isoformat()
    })
    return {"status": "ok", "adjustment_preview": reranker.get_adjustment(req.domain, "risk_score")}

# Apply reranker to unified endpoint output:
# In /analyze/v5/unified, after combined_results:
combined_results = reranker.apply(domain, combined_results)
```

**`extension/popup.js` — Correction UI:**

After results render, show correction panel:
```javascript
function renderCorrectionPanel(data, url) {
  const domain = new URL(url).hostname;
  const panel = document.createElement('div');
  panel.className = 'correction-panel';
  panel.innerHTML = `
    <div class="correction-header">🤔 Kết quả AI không chính xác?</div>
    <div class="correction-body" id="correctionBody" style="display:none">
      <div class="correction-row">
        <label>Điểm rủi ro thực tế:</label>
        <input type="range" id="correctedRisk" min="0" max="100" value="${data.risk_score}" step="5">
        <span id="correctedRiskVal">${data.risk_score}</span>
      </div>
      <div class="correction-row">
        <label>Lý do sửa:</label>
        <select id="correctionReason">
          <option value="too_high">AI đánh giá quá cao</option>
          <option value="too_low">AI đánh giá quá thấp</option>
          <option value="cultural_context">Ngữ cảnh văn hóa VN</option>
          <option value="sarcasm">Đây là châm biếm/hài hước</option>
          <option value="wrong_category">Sai loại nội dung</option>
        </select>
      </div>
      <button id="submitCorrection" class="btn-primary btn-sm">✅ Gửi điều chỉnh</button>
    </div>
    <button id="toggleCorrection" class="btn-link">✏️ Sửa kết quả này</button>
  `;
  return panel;
}
```

**`extension/popup.html`** — Add correction panel placeholder after results section.

| Field | Detail |
|-------|--------|
| **Files** | `src/models/reranker.py` (new), `api.py`, `extension/popup.js`, `extension/popup.html`, `extension/style.css` |
| **Effort** | 5 days |
| **Dependencies** | Existing feedback store (v5.0), unified endpoint (v5.0) |
| **Status** | ⬜ Not started |

---

### 6.12 — Scam URL Database Contribution

| Field | Detail |
|-------|--------|
| **What** | When a URL gets risk score ≥ 75 AND user confirms it's a scam (or the AI detects scam-specific patterns), the system automatically submits the URL to: (1) **PhishTank** public API, (2) **Google Safe Browsing Submit** (via report form), (3) our own **community blocklist** on the backend. Users get a confirmation with tracking. |
| **Why** | Scam websites targeting Vietnamese users (fake bank login pages, lottery scams, fake government portals) are extremely common and under-reported. Our extension sees thousands of scans — we're uniquely positioned to become a Vietnamese-focused anti-scam database that feeds into global systems. This protects people who don't even use our extension. |

#### Scam Pattern Detection

**`src/models/unified_analyzer.py` extension:**
```python
SCAM_INDICATORS = {
    "financial_phishing": ["nhập thông tin thẻ", "xác minh tài khoản ngân hàng", "OTP", "mã bí mật", "nạp tiền để nhận thưởng"],
    "lottery_scam": ["trúng thưởng", "quà tặng", "iPhone miễn phí", "nhận tiền thưởng ngay"],
    "fake_government": ["thông báo từ công an", "bộ công an", "cục thuế", "yêu cầu đóng tiền phạt"],
    "investment_scam": ["lãi suất 30%", "đầu tư không rủi ro", "lợi nhuận đảm bảo", "chứng khoán siêu lợi nhuận"],
    "impersonation": ["zalo official", "facebook xác nhận", "google yêu cầu"],
}

# Compute scam_probability in unified analyzer alongside other scores
# Returns: {"is_scam": true, "scam_type": "financial_phishing", "confidence": 0.87, "evidence_phrases": [...]}
```

**`api.py` — Scam reporting endpoint:**
```python
import httpx, hashlib

class ScamReportRequest(BaseModel):
    url: str
    scam_type: str
    ai_confidence: float
    user_confirmed: bool
    evidence_phrases: List[str] = []

@app.post("/api/report/scam")
async def report_scam(req: ScamReportRequest, background_tasks: BackgroundTasks):
    url_hash = hashlib.sha256(req.url.encode()).hexdigest()
    
    # 1. Save to community blocklist
    blocklist.add_domain(req.url, reason=f"scam:{req.scam_type}", confidence=req.ai_confidence, user_confirmed=req.user_confirmed)
    
    # 2. Submit to PhishTank (background task, fire-and-forget)
    background_tasks.add_task(submit_to_phishtank, req.url)
    
    # 3. Log to scam database for analysis
    background_tasks.add_task(log_scam_report, {
        "url_hash": url_hash,
        "scam_type": req.scam_type,
        "confidence": req.ai_confidence,
        "user_confirmed": req.user_confirmed,
        "timestamp": datetime.now().isoformat()
    })
    
    return {
        "status": "reported",
        "tracking_id": url_hash[:12].upper(),
        "submitted_to": ["community_blocklist", "phishtank"],
        "message": "Đã báo cáo lừa đảo. Mã theo dõi: " + url_hash[:12].upper()
    }

async def submit_to_phishtank(url: str):
    """Submit to PhishTank API — requires free PhishTank account API key"""
    phishtank_key = os.getenv('PHISHTANK_API_KEY', '')
    if not phishtank_key:
        return
    async with httpx.AsyncClient() as client:
        try:
            await client.post('https://www.phishtank.com/api/', data={
                'url': url, 'app_key': phishtank_key, 'format': 'json'
            }, timeout=10)
        except:
            pass  # non-critical, best-effort

async def submit_to_google_safebrowsing(url: str):
    """Submit via Google's reportpage form"""
    async with httpx.AsyncClient() as client:
        try:
            await client.get(
                f'https://safebrowsing.google.com/safebrowsing/report_phish/?url={url}',
                timeout=10
            )
        except:
            pass
```

**`extension/background.js` — Auto-submit trigger:**
```javascript
async function checkAndReportScam(scanResults, url) {
  const scam = scanResults.scam_detection;
  if (!scam) return;
  
  if (scam.is_scam && scam.confidence >= 0.85) {
    // High-confidence auto-report (no user confirmation needed)
    await fetch(`${BASE_URL}/api/report/scam`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        url,
        scam_type: scam.scam_type,
        ai_confidence: scam.confidence,
        user_confirmed: false,
        evidence_phrases: scam.evidence_phrases
      })
    });
  } else if (scam.is_scam && scam.confidence >= 0.65) {
    // Medium confidence — ask user to confirm in popup
    chrome.runtime.sendMessage({ type: 'PROMPT_SCAM_CONFIRM', scam, url });
  }
}
```

**`extension/popup.js` — Scam confirmation UI:**

If `PROMPT_SCAM_CONFIRM` is received, show a banner at top of results:
```javascript
function renderScamPrompt(scam, url) {
  return `
    <div class="scam-prompt-card">
      <div class="scam-prompt-icon">🚨</div>
      <div class="scam-prompt-text">
        <strong>AI phát hiện dấu hiệu lừa đảo</strong> (${Math.round(scam.confidence*100)}% tin cậy)
        <br>Loại: ${SCAM_TYPE_LABELS[scam.scam_type]}
      </div>
      <div class="scam-prompt-actions">
        <button id="confirmScam" class="btn-danger btn-sm">✅ Đúng, báo cáo ngay</button>
        <button id="denyScam" class="btn-ghost btn-sm">✗ Không phải</button>
      </div>
      <div class="scam-evidence">
        Bằng chứng: ${scam.evidence_phrases.map(p => `<code>${p}</code>`).join(', ')}
      </div>
    </div>
  `;
}
```

**Post-submission UX:**
```
✅ Đã báo cáo thành công!
Mã theo dõi: A3F2B8D1C9E4
Đã gửi đến: Danh sách cộng đồng, PhishTank
Cảm ơn bạn đã bảo vệ cộng đồng! 🛡️
```

| Field | Detail |
|-------|--------|
| **New env vars** | `PHISHTANK_API_KEY` (optional, free account at phishtank.org) |
| **Files** | `api.py`, `src/models/unified_analyzer.py`, `extension/background.js`, `extension/popup.js`, `extension/style.css` |
| **Effort** | 3 days |
| **Dependencies** | Unified analyzer (v5.0), community blocklist (v5.0) |
| **Status** | ⬜ Not started |

---

## PHASE 3 — Power User Tools (Week 5–6)

---

### 6.13 — Bulk Analysis Mode

| Field | Detail |
|-------|--------|
| **What** | A dedicated "Phân tích hàng loạt" tab in the popup where users can analyze 10–100 URLs at once. Input: paste URL list or upload CSV. Output: table with risk score per URL, downloadable as CSV/Excel. |
| **Why** | Journalists fact-checking a list of shared links, teachers reviewing student-submitted articles, researchers studying misinformation trends, NGOs monitoring propaganda campaigns — none of these use cases fit the "one URL at a time" popup model. This opens a B2B / power-user market segment. |

#### Implementation — Backend

**New endpoint `api.py`:**
```python
class BulkScanRequest(BaseModel):
    urls: List[str]  # max 100
    scan_depth: str = "quick"  # "quick" (regex only, no Gemini) | "full" (unified AI)
    include_summary: bool = False

class BulkScanResult(BaseModel):
    url: str
    domain: str
    risk_score: int
    risk_level: str
    toxicity_score: float
    sentiment: str
    fact_check_status: str
    title: str
    error: Optional[str] = None
    scan_time_ms: int

@app.post("/analyze/v6/bulk")
async def bulk_analyze(req: BulkScanRequest, background_tasks: BackgroundTasks):
    if len(req.urls) > 100:
        raise HTTPException(400, "Tối đa 100 URL mỗi lần")
    
    results = []
    
    if req.scan_depth == "quick":
        # Quick mode: fetch page title + run offline regex (no Gemini, very fast)
        async with httpx.AsyncClient() as client:
            tasks = [quick_analyze_url(client, url) for url in req.urls]
            results = await asyncio.gather(*tasks, return_exceptions=True)
    else:
        # Full mode: queue through unified analyzer with rate limiting
        # Process 3 at a time to avoid Gemini rate limits
        for i in range(0, len(req.urls), 3):
            batch = req.urls[i:i+3]
            batch_tasks = [full_analyze_url(url) for url in batch]
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            results.extend(batch_results)
            if i + 3 < len(req.urls):
                await asyncio.sleep(1)  # rate limit pause
    
    # Filter exceptions (failed URLs)
    clean_results = []
    for url, result in zip(req.urls, results):
        if isinstance(result, Exception):
            clean_results.append(BulkScanResult(url=url, domain=urlparse(url).netloc, risk_score=0, risk_level="error", toxicity_score=0, sentiment="unknown", fact_check_status="error", title="", error=str(result), scan_time_ms=0))
        else:
            clean_results.append(result)
    
    return {
        "total": len(clean_results),
        "high_risk_count": sum(1 for r in clean_results if r.risk_score >= 70),
        "results": [r.dict() for r in clean_results],
        "scan_depth": req.scan_depth,
        "timestamp": datetime.now().isoformat()
    }
```

**`extension/popup.html` — New bulk tab:**
```html
<!-- Add to header tabs -->
<button class="tab-btn" data-tab="bulk" id="tabBulk">📋 Hàng loạt</button>

<!-- Bulk analysis panel -->
<div id="bulkPanel" class="tab-panel" style="display:none">
  <div class="bulk-header">
    <h3>📋 Phân tích hàng loạt</h3>
    <p class="hint">Tối đa 100 URL mỗi lần</p>
  </div>
  
  <!-- Input area -->
  <textarea id="bulkUrlInput" placeholder="Dán danh sách URL vào đây (mỗi dòng 1 URL)&#10;https://example.com&#10;https://example2.com"></textarea>
  
  <!-- OR upload CSV -->
  <div class="bulk-upload">
    <label for="bulkFile">📤 Hoặc tải file CSV/TXT lên</label>
    <input type="file" id="bulkFile" accept=".csv,.txt">
  </div>
  
  <!-- Scan depth toggle -->
  <div class="bulk-options">
    <label><input type="radio" name="scanDepth" value="quick" checked> ⚡ Nhanh (không dùng AI, ~1s/URL)</label>
    <label><input type="radio" name="scanDepth" value="full"> 🤖 Đầy đủ AI (Gemini, ~10s/URL)</label>
  </div>
  
  <!-- Progress -->
  <div id="bulkProgress" style="display:none">
    <div class="progress-bar"><div class="progress-fill" id="bulkProgressFill"></div></div>
    <span id="bulkProgressText">Đang phân tích 0/0...</span>
  </div>
  
  <!-- Action buttons -->
  <div class="bulk-actions">
    <button id="startBulkScan" class="btn-primary">🔍 Bắt đầu phân tích</button>
    <button id="exportBulkCSV" class="btn-secondary" style="display:none">📥 Tải CSV</button>
    <button id="exportBulkJSON" class="btn-secondary" style="display:none">📥 Tải JSON</button>
  </div>
  
  <!-- Results table -->
  <div id="bulkResults" style="display:none">
    <div class="bulk-summary" id="bulkSummary"></div>
    <table class="bulk-table" id="bulkTable">
      <thead>
        <tr>
          <th>URL</th>
          <th>Rủi ro</th>
          <th>Độc hại</th>
          <th>Cảm xúc</th>
          <th>Tin giả</th>
        </tr>
      </thead>
      <tbody id="bulkTableBody"></tbody>
    </table>
  </div>
</div>
```

**`extension/popup.js` — Bulk scan logic:**
```javascript
async function startBulkScan() {
  const raw = document.getElementById('bulkUrlInput').value;
  const urls = raw.split('\n').map(u => u.trim()).filter(u => u.startsWith('http'));
  
  if (!urls.length) { showToast('Vui lòng nhập ít nhất 1 URL'); return; }
  if (urls.length > 100) { showToast('Tối đa 100 URL'); return; }
  
  const depth = document.querySelector('input[name="scanDepth"]:checked').value;
  
  document.getElementById('bulkProgress').style.display = 'block';
  document.getElementById('startBulkScan').disabled = true;
  
  const updateProgress = (done, total) => {
    document.getElementById('bulkProgressFill').style.width = `${(done/total)*100}%`;
    document.getElementById('bulkProgressText').textContent = `Đang phân tích ${done}/${total}...`;
  };
  
  updateProgress(0, urls.length);
  
  try {
    const response = await fetch(`${API_BASE}/analyze/v6/bulk`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ urls, scan_depth: depth }),
      signal: AbortSignal.timeout(300000) // 5 min timeout for 100 URLs
    });
    
    const data = await response.json();
    updateProgress(urls.length, urls.length);
    renderBulkResults(data);
    
    // Save to history
    await chrome.storage.local.set({
      lastBulkScan: { results: data, timestamp: Date.now() }
    });
    
  } catch (err) {
    showToast('Lỗi phân tích hàng loạt: ' + err.message);
  } finally {
    document.getElementById('startBulkScan').disabled = false;
  }
}

function renderBulkResults(data) {
  const tbody = document.getElementById('bulkTableBody');
  const highRisk = data.results.filter(r => r.risk_score >= 70);
  
  document.getElementById('bulkSummary').innerHTML = `
    <div class="bulk-stat">Tổng: <strong>${data.total}</strong></div>
    <div class="bulk-stat danger">Rủi ro cao: <strong>${data.high_risk_count}</strong></div>
    <div class="bulk-stat success">An toàn: <strong>${data.total - data.high_risk_count}</strong></div>
  `;
  
  tbody.innerHTML = data.results.map(r => `
    <tr class="${r.risk_score >= 70 ? 'row-danger' : r.risk_score >= 40 ? 'row-warning' : 'row-safe'}">
      <td class="url-cell"><a href="${r.url}" target="_blank" title="${r.url}">${truncate(r.url, 40)}</a></td>
      <td><span class="risk-badge risk-${r.risk_level}">${r.risk_score}</span></td>
      <td>${(r.toxicity_score * 100).toFixed(0)}%</td>
      <td>${SENTIMENT_LABELS[r.sentiment] || r.sentiment}</td>
      <td>${FACTCHECK_LABELS[r.fact_check_status] || r.fact_check_status}</td>
    </tr>
  `).join('');
  
  document.getElementById('bulkResults').style.display = 'block';
  document.getElementById('exportBulkCSV').style.display = 'inline-block';
  document.getElementById('exportBulkJSON').style.display = 'inline-block';
}

function exportBulkToCSV(data) {
  const headers = ['URL', 'Domain', 'Rủi ro', 'Mức độ', 'Độc hại %', 'Cảm xúc', 'Kiểm chứng', 'Tiêu đề', 'Thời gian quét'];
  const rows = data.results.map(r => [
    r.url, r.domain, r.risk_score, r.risk_level,
    (r.toxicity_score * 100).toFixed(1),
    r.sentiment, r.fact_check_status, r.title, new Date().toISOString()
  ]);
  const csv = [headers, ...rows].map(row => row.map(v => `"${String(v).replace(/"/g, '""')}"`).join(',')).join('\r\n');
  const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8' }); // BOM for Excel Vietnamese support
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `VnCG-Bulk-${Date.now()}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}
```

**`extension/style.css` additions:**
```css
/* Bulk analysis tab */
#bulkUrlInput { width: 100%; height: 100px; resize: vertical; padding: 8px; font-size: 12px; border: 1px solid var(--border); border-radius: 6px; background: var(--input-bg); color: var(--text-primary); font-family: monospace; }
.bulk-table { width: 100%; border-collapse: collapse; font-size: 11px; margin-top: 8px; }
.bulk-table th { background: var(--card-bg); padding: 6px 4px; text-align: left; font-weight: 600; border-bottom: 2px solid var(--border); }
.bulk-table td { padding: 5px 4px; border-bottom: 1px solid var(--border); vertical-align: middle; }
.url-cell a { color: var(--text-primary); text-decoration: none; font-family: monospace; font-size: 10px; }
.url-cell a:hover { text-decoration: underline; color: var(--primary); }
.row-danger { background: rgba(231,76,60,0.06); }
.row-warning { background: rgba(230,126,34,0.06); }
.row-safe { background: rgba(39,174,96,0.04); }
.bulk-stat { display: inline-block; padding: 4px 10px; background: var(--card-bg); border-radius: 6px; font-size: 12px; margin-right: 6px; }
.bulk-stat.danger { color: #e74c3c; }
.bulk-stat.success { color: #27ae60; }
.bulk-options { display: flex; flex-direction: column; gap: 4px; margin: 8px 0; font-size: 12px; }
.bulk-upload { font-size: 12px; margin: 6px 0; color: var(--text-secondary); }
/* Dark mode */
.dark-mode #bulkUrlInput { background: #2a2a3e; border-color: #444; }
.dark-mode .bulk-table th { background: #2a2a3e; }
.dark-mode .row-danger { background: rgba(231,76,60,0.12); }
```

#### File Upload Support (CSV parsing)
```javascript
document.getElementById('bulkFile').addEventListener('change', (e) => {
  const file = e.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = (ev) => {
    const text = ev.target.result;
    // Extract URLs from CSV (first column) or plain TXT (one per line)
    const urls = text.split(/[\r\n]+/)
      .map(line => line.split(',')[0].trim().replace(/^["']|["']$/g, ''))
      .filter(u => u.startsWith('http'));
    document.getElementById('bulkUrlInput').value = urls.join('\n');
    showToast(`Đã tải ${urls.length} URL từ file`);
  };
  reader.readAsText(file, 'UTF-8');
});
```

| Field | Detail |
|-------|--------|
| **Files** | `api.py`, `extension/popup.html`, `extension/popup.js`, `extension/style.css` |
| **Effort** | 5 days |
| **Dependencies** | Unified analyzer (v5.0), existing CSV export logic (v5.0 partial) |
| **New dependency** | `httpx` (already installed), `asyncio` (stdlib) |
| **Status** | ⬜ Not started |

---

## 📊 TOTAL EFFORT SUMMARY

| Phase | Features | Total Days | Target Completion |
|-------|----------|------------|-------------------|
| Phase 1 | 6.2 + 6.3 | ~7 days | Week 1–2 of March |
| Phase 2 | 6.6 + 6.9 + 6.12 | ~10 days | Week 3–4 of March |
| Phase 3 | 6.13 | ~5 days | Week 5 of March |
| **TOTAL** | **6 features** | **~22 dev days** | **End of March 2026** |

---

## 📁 FILES CHANGED — FULL LIST

### New Files
| File | Purpose |
|------|---------|
| `extension/domain_control.js` | Domain whitelist/blacklist manager (6.2) |
| `src/models/reranker.py` | Score re-ranking based on user corrections (6.9) |

### Modified Files
| File | Changes |
|------|---------|
| `api.py` | + seed blacklist endpoint (6.2), + `/api/correction` (6.9), + `/api/report/scam` (6.12), + `/analyze/v6/bulk` (6.13), + reranker integration (6.9) |
| `src/models/unified_analyzer.py` | + evidence spans in prompt/response (6.3), + scam detection (6.12) |
| `extension/manifest.json` | + `"incognito": "spanning"` (6.6), + `domain_control.js` in content_scripts (6.2) |
| `extension/background.js` | + webNavigation blacklist intercept (6.2), + incognito detection (6.6), + auto scam report (6.12) |
| `extension/popup.html` | + domain control UI (6.2), + evidence legend (6.3), + incognito log UI (6.6), + correction panel (6.9), + scam prompt (6.12), + bulk tab (6.13) |
| `extension/popup.js` | + domain control functions (6.2), + evidence rendering (6.3), + incognito log display (6.6), + correction UI/submit (6.9), + scam confirm prompt (6.12), + bulk scan engine + export (6.13) |
| `extension/content.js` | + per-span DOM highlights (6.3) |
| `extension/content.css` | + evidence span styles on-page (6.3) |
| `extension/style.css` | + domain list UI (6.2), + evidence marks + tags (6.3), + incognito log (6.6), + correction panel (6.9), + scam prompt (6.12), + bulk table + options (6.13) |
| `extension/block.html` | + blacklist reason branch (6.2), + incognito reason branch (6.6) |

### New Environment Variables
| Variable | Feature | Required |
|----------|---------|---------|
| `PHISHTANK_API_KEY` | 6.12 scam reporting | Optional (free account) |
| `RERANKER_DATA` | 6.9 data file path | Optional (has default) |

---

## 🔁 DEVELOPMENT ORDER (Recommended)

```
1. 6.2 Domain Blacklist/Whitelist  →  highest user demand from parents
2. 6.6 Incognito Detection          →  closes the main bypass loophole
3. 6.3 Explainable AI               →  backend + frontend, independent
4. 6.12 Scam Reporting              →  builds on unified analyzer
5. 6.9 User Correction              →  requires multiple scan cycles for data
6. 6.13 Bulk Analysis               →  most complex, save for last
```

---

## 🚀 VERSION TARGET

**v6.0.0** — All 6 features above  
**Manifest version** bump from `5.0.0` → `6.0.0`  
**Chrome Store** re-submission after v6.0.0 is stable  
**Backend** deploy to Render from `v6-enhancement` branch  
