/**
 * VnContentGuard Pro v5.0 — Content Script Overlay (2.1)
 * Injects floating risk badge + highlights toxic comments directly on the page.
 * Activated by SHOW_OVERLAY message from background.js.
 * Toggle on/off via TOGGLE_OVERLAY message from popup.js.
 */

(() => {
    'use strict';

    // ─── State ───────────────────────────────────────────────────────────────
    let overlayEnabled = true;       // global toggle
    let currentResults = null;       // last scan results
    let badgeEl = null;              // floating badge element
    let highlightedEls = [];         // comment elements we highlighted
    let highlightMap = new Map();    // elem → tooltip element
    let styleEl = null;              // injected <link> for content.css

    // ─── Entry Point: Message Listener ──────────────────────────────────────
    chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
        if (message.type === 'SHOW_OVERLAY') {
            currentResults = message.data;
            chrome.storage.local.get(['overlayEnabled'], (s) => {
                overlayEnabled = s.overlayEnabled !== false;
                if (overlayEnabled) renderOverlay(currentResults);
            });
            sendResponse({ ok: true });
            return true;
        }

        if (message.type === 'TOGGLE_OVERLAY') {
            overlayEnabled = message.enabled;
            chrome.storage.local.set({ overlayEnabled });
            if (overlayEnabled && currentResults) {
                renderOverlay(currentResults);
            } else {
                removeOverlay();
            }
            sendResponse({ ok: true });
            return true;
        }

        if (message.type === 'GET_OVERLAY_STATE') {
            sendResponse({ enabled: overlayEnabled, hasResults: !!currentResults });
            return true;
        }
    });

    // ─── Main Render ─────────────────────────────────────────────────────────
    function renderOverlay(results) {
        removeOverlay(); // clean up any previous overlay first

        const risk = results?.risk_score_v5 || results?.risk_assessment || {};
        const riskScore = risk.risk_score ?? risk.score ?? 0;
        const riskLevel = risk.risk_level || risk.level || classifyRisk(riskScore);
        const riskCategory = risk.risk_category || risk.category || '';
        const analysisMode = results?.analysis_mode || '';

        // Inject CSS first; wait for it to load before adding the badge
        // so the visibility transition fires correctly.
        injectStyles(() => {
            // 1. Floating risk badge
            renderRiskBadge(riskScore, riskLevel, riskCategory, analysisMode, results);

            // 2. Highlight toxic comments in page
            if (results?.comments_analysis?.length) {
                highlightComments(results.comments_analysis);
            }
        });
    }

    // ─── Risk Badge ──────────────────────────────────────────────────────────
    function renderRiskBadge(score, level, category, mode, results) {
        const badge = document.createElement('div');
        badge.id = 'vcg-risk-badge';
        badge.className = `vcg-badge vcg-risk-${getRiskClass(score)}`;
        badge.setAttribute('role', 'complementary');
        badge.setAttribute('aria-label', `VnContentGuard: Rủi ro ${score}/100`);

        const modeTag = mode === 'unified' ? '⚡' : mode === 'stream' ? '〜' : '';
        const categoryText = category ? `<div class="vcg-badge-category">${escapeHtml(category)}</div>` : '';

        badge.innerHTML = `
            <div class="vcg-badge-header">
                <span class="vcg-badge-logo">🛡️</span>
                <span class="vcg-badge-title">VnContentGuard ${modeTag}</span>
                <button class="vcg-badge-close" title="Đóng overlay" aria-label="Đóng">✕</button>
            </div>
            <div class="vcg-badge-score">${score}<span class="vcg-badge-max">/100</span></div>
            <div class="vcg-badge-level">${escapeHtml(levelLabel(level))}</div>
            ${categoryText}
            <div class="vcg-badge-details">
                ${buildBadgeDetails(results)}
            </div>
            <div class="vcg-badge-footer">
                <button class="vcg-badge-jump" title="Xem bình luận độc hại">💬 Xem BL độc hại</button>
            </div>
        `;

        // Close handler
        badge.querySelector('.vcg-badge-close').addEventListener('click', (e) => {
            e.stopPropagation();
            badge.classList.add('vcg-badge-minimized');
            badge.innerHTML = `
                <div class="vcg-badge-mini" title="VnContentGuard: Rủi ro ${score}/100 — Click để mở lại">
                    🛡️ <strong>${score}</strong>
                    <button class="vcg-badge-restore" aria-label="Mở lại">▲</button>
                </div>`;
            badge.querySelector('.vcg-badge-restore').addEventListener('click', () => {
                renderRiskBadge(score, level, category, mode, results);
            });
        });

        // Jump to first toxic comment
        badge.querySelector('.vcg-badge-jump')?.addEventListener('click', () => {
            const first = document.querySelector('.vcg-comment-toxic');
            if (first) {
                first.scrollIntoView({ behavior: 'smooth', block: 'center' });
                first.classList.add('vcg-pulse');
                setTimeout(() => first.classList.remove('vcg-pulse'), 1200);
            }
        });

        // Draggable
        makeDraggable(badge);

        document.body.appendChild(badge);
        badgeEl = badge;

        // Animate in — one rAF is enough; CSS is guaranteed loaded by this point
        // (renderOverlay waits for injectStyles' onReady callback before calling us)
        requestAnimationFrame(() => badge.classList.add('vcg-badge-visible'));
    }

    function buildBadgeDetails(results) {
        const lines = [];
        const sentiment = results?.sentiment_v5 || {};
        const factCheck = results?.fact_check_v5 || results?.fact_check || {};
        const comments = results?.comments_analysis || [];
        const toxicCount = comments.filter(c => c.is_toxic || c.toxicity_score > 0.5).length;

        if (sentiment.label) {
            const emj = { 'tích cực': '😊', 'tiêu cực': '😠', 'trung lập': '😐' };
            const lbl = sentiment.label.toLowerCase();
            lines.push(`${emj[lbl] || '📊'} Cảm xúc: ${escapeHtml(sentiment.label)}`);
        }
        if (factCheck.overall_verdict || factCheck.verdict) {
            const v = factCheck.overall_verdict || factCheck.verdict;
            const emj = v.includes('sai') ? '❌' : v.includes('đún') || v.includes('chín') ? '✅' : '⚠️';
            lines.push(`${emj} Kiểm chứng: ${escapeHtml(v)}`);
        }
        if (comments.length) {
            const pct = Math.round((toxicCount / comments.length) * 100);
            lines.push(`💬 Bình luận: ${toxicCount}/${comments.length} độc hại (${pct}%)`);
        }
        return lines.map(l => `<div class="vcg-detail-row">${l}</div>`).join('');
    }

    // ─── Comment Highlighting ────────────────────────────────────────────────
    function highlightComments(commentsAnalysis) {
        // Build lookup: normalized text → analysis result
        const analyzed = new Map();
        commentsAnalysis.forEach(c => {
            if (c.is_toxic || c.toxicity_score > 0.5) {
                analyzed.set(normalizeText(c.text || c.comment || ''), c);
            }
        });
        if (analyzed.size === 0) return;

        // Common comment container selectors per platform
        const selectors = [
            // Facebook
            '[data-testid="UFI2Comment/body"]',
            '[data-commentid]',
            '.userContentWrapper',
            // News sites
            '.comment-content', '.comment-body', '.comment-text',
            '.user-comment', '[class*="comment"] p',
            '[class*="CommentContent"]',
            // Generic
            '[class*="comment"]',
        ];

        const candidateEls = [];
        selectors.forEach(sel => {
            try {
                document.querySelectorAll(sel).forEach(el => candidateEls.push(el));
            } catch (_) {}
        });

        // Deduplicate by DOM element
        const seen = new Set();
        candidateEls.forEach(el => {
            if (seen.has(el)) return;
            seen.add(el);

            const rawText = el.innerText || el.textContent || '';
            const norm = normalizeText(rawText);

            // Check if any analyzed toxic comment is a substring match
            let matchedResult = null;
            analyzed.forEach((result, analyzedNorm) => {
                if (!matchedResult && analyzedNorm.length > 10) {
                    if (norm.includes(analyzedNorm) || analyzedNorm.includes(norm.substring(0, 50))) {
                        matchedResult = result;
                    }
                }
            });
            if (!matchedResult) return;

            // Apply highlight
            el.classList.add('vcg-comment-toxic');
            el.setAttribute('data-vcg-toxic', '1');
            highlightedEls.push(el);

            // Build tooltip
            const tooltip = buildCommentTooltip(matchedResult);
            el.parentElement?.style && (el.parentElement.style.position = 'relative');
            el.appendChild(tooltip);
            highlightMap.set(el, tooltip);

            // Hover events
            el.addEventListener('mouseenter', () => tooltip.style.display = 'block');
            el.addEventListener('mouseleave', () => tooltip.style.display = 'none');
        });
    }

    function buildCommentTooltip(result) {
        const tooltip = document.createElement('div');
        tooltip.className = 'vcg-comment-tooltip';

        const level = result.toxicity_level || result.level || 'Độc hại';
        const explanation = result.explanation || result.reason || '';
        const score = result.toxicity_score != null
            ? Math.round(result.toxicity_score * 100)
            : null;

        tooltip.innerHTML = `
            <div class="vcg-tooltip-header">⚠️ ${escapeHtml(level)}${score !== null ? ` (${score}%)` : ''}</div>
            ${explanation ? `<div class="vcg-tooltip-body">${escapeHtml(explanation.substring(0, 120))}</div>` : ''}
            <div class="vcg-tooltip-footer">VnContentGuard Pro</div>
        `;
        return tooltip;
    }

    // ─── Cleanup ─────────────────────────────────────────────────────────────
    function removeOverlay() {
        // Remove badge
        document.getElementById('vcg-risk-badge')?.remove();
        badgeEl = null;

        // Remove comment highlights
        highlightedEls.forEach(el => {
            el.classList.remove('vcg-comment-toxic', 'vcg-pulse');
            el.removeAttribute('data-vcg-toxic');
            const tooltip = highlightMap.get(el);
            if (tooltip?.parentNode) tooltip.remove();
        });
        highlightedEls = [];
        highlightMap.clear();
    }

    // ─── Draggable Badge ─────────────────────────────────────────────────────
    function makeDraggable(el) {
        let startX, startY, startLeft, startTop, dragging = false;

        el.addEventListener('mousedown', (e) => {
            if (e.target.closest('button')) return;
            dragging = true;
            startX = e.clientX;
            startY = e.clientY;
            startLeft = el.offsetLeft;
            startTop = el.offsetTop;
            el.style.cursor = 'grabbing';
            e.preventDefault();
        });

        document.addEventListener('mousemove', (e) => {
            if (!dragging) return;
            const dx = e.clientX - startX;
            const dy = e.clientY - startY;
            el.style.right = 'auto';
            el.style.left = `${Math.max(0, startLeft + dx)}px`;
            el.style.top = `${Math.max(0, startTop + dy)}px`;
        });

        document.addEventListener('mouseup', () => {
            if (dragging) { dragging = false; el.style.cursor = 'default'; }
        });
    }

    // ─── Style Injection ─────────────────────────────────────────────────────
    // Accepts an optional callback fired once the CSS is ready to use.
    function injectStyles(onReady) {
        const existing = document.getElementById('vcg-overlay-styles');
        if (existing) {
            // CSS already injected — fire callback immediately
            onReady?.();
            return;
        }
        const link = document.createElement('link');
        link.id = 'vcg-overlay-styles';
        link.rel = 'stylesheet';
        link.href = chrome.runtime.getURL('content.css');
        // Wait for CSS to load before signalling readiness
        link.onload  = () => onReady?.();
        link.onerror = () => onReady?.(); // still render even if CSS fails
        (document.head || document.documentElement).appendChild(link);
        styleEl = link;
    }

    // ─── Helpers ─────────────────────────────────────────────────────────────
    function getRiskClass(score) {
        if (score >= 70) return 'high';
        if (score >= 40) return 'medium';
        return 'low';
    }

    function classifyRisk(score) {
        if (score >= 70) return 'Cao';
        if (score >= 40) return 'Trung bình';
        return 'Thấp';
    }

    function levelLabel(level) {
        const map = {
            'high': 'Rủi ro cao', 'medium': 'Rủi ro trung bình', 'low': 'Rủi ro thấp',
            'Cao': 'Rủi ro cao', 'Trung bình': 'Rủi ro trung bình', 'Thấp': 'Rủi ro thấp',
        };
        return map[level] || level || '';
    }

    function normalizeText(str) {
        return str.toLowerCase().replace(/\s+/g, ' ').trim().substring(0, 200);
    }

    function escapeHtml(str) {
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    // ─── Auto-restore if storage has results ─────────────────────────────────
    // background.js saves completed scans under both 'scan_${url}' (envelope)
    // and '[url]' (raw results spread). We use the envelope key here since it
    // has a reliable status field so we only restore truly completed scans.
    const scanKey = `scan_${location.href}`;
    chrome.storage.local.get([scanKey, 'overlayEnabled'], (s) => {
        overlayEnabled = s.overlayEnabled !== false;
        if (!overlayEnabled) return;
        const scanData = s[scanKey];
        if (scanData?.status === 'completed' && scanData?.results) {
            currentResults = scanData.results;
            // Delay to let page fully settle after navigation
            setTimeout(() => renderOverlay(currentResults), 1500);
        }
    });

})();
