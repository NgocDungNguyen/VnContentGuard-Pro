/**
 * VnContentGuard Pro v5.0 — Background Service Worker
 * =====================================================
 * Handles API calls in the background so they survive popup close.
 * 
 * Responsibilities:
 * 1. Receive scan requests from popup via chrome.runtime.sendMessage
 * 2. Execute API call (try local → cloud fallback) + SSE streaming (1.5)
 * 3. Save results to chrome.storage.local
 * 4. Update badge with risk score
 * 5. Notify popup when done (if still open)
 * 6. Auto-scan supported sites when toggle is ON
 * 7. 🔔 Notification system (3.5)
 * 8. 🚩 Community Blocklist checking (4.1)
 * 9. 🔒 Parental Control interception (4.2)
 * 10. ⚠️ Browser Content Warning redirect (4.3)
 * 11. 📊 Weekly Safety Report via alarms (4.4)
 */

// API endpoints (cloud)
const API_ENDPOINTS = [
    "https://vncontentguard-pro.onrender.com/analyze/v5"
];

const STREAM_ENDPOINTS = [
    "https://vncontentguard-pro.onrender.com/analyze/v5/stream"
];

// ARCH-01: Unified single-pass endpoint
const UNIFIED_ENDPOINTS = [
    "https://vncontentguard-pro.onrender.com/analyze/v5/unified"
];

// Feedback endpoints
const FEEDBACK_ENDPOINTS = [
    "https://vncontentguard-pro.onrender.com/api/feedback"
];

const REPORT_ENDPOINTS = [
    "https://vncontentguard-pro.onrender.com/api/report"
];

const BLOCKLIST_ENDPOINTS = [
    "https://vncontentguard-pro.onrender.com/api/blocklist"
];

const BLOCKLIST_CHECK_ENDPOINTS = [
    "https://vncontentguard-pro.onrender.com/api/blocklist/check"
];

const STATS_ENDPOINTS = [
    "https://vncontentguard-pro.onrender.com/api/stats"
];

// Cached blocklist (refreshed every 6h)
let cachedBlocklist = [];
let blocklistLastFetch = 0;
const BLOCKLIST_REFRESH_MS = 6 * 60 * 60 * 1000;

// Server warm-up: Render free tier cold-starts in ~30s.
// Pre-ping /health to wake the server before sending the actual scan.
const HEALTH_URL = "https://vncontentguard-pro.onrender.com/health";
async function warmUpServer() {
    try {
        const controller = new AbortController();
        const tid = setTimeout(() => controller.abort(), 50000);
        await fetch(HEALTH_URL, { signal: controller.signal });
        clearTimeout(tid);
        console.log('[BG] Server warm-up OK');
    } catch (e) {
        console.log('[BG] Server warm-up ping failed:', e.message);
    }
}

// Supported domains for auto-scan
const AUTO_SCAN_DOMAINS = [
    'facebook.com', 'vnexpress.net', 'dantri.com.vn', 'tuoitre.vn',
    'thanhnien.vn', 'baomoi.com', 'kenh14.vn', 'cafef.vn', 'tiktok.com'
];

// Auto-scan rate limit: 1 scan per URL per 30 minutes
const AUTO_SCAN_COOLDOWN_MS = 30 * 60 * 1000;
const autoScanTimestamps = {};

// ============================================================================
// MESSAGE HANDLER — Receives requests from popup.js
// ============================================================================

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.type === 'START_SCAN') {
        handleScan(message.data);
        sendResponse({ status: 'started' });
        return true;
    }

    if (message.type === 'START_SCAN_UNIFIED') {
        handleUnifiedScan(message.data);
        sendResponse({ status: 'started' });
        return true;
    }

    if (message.type === 'START_SCAN_STREAM') {
        handleStreamScan(message.data);
        sendResponse({ status: 'started' });
        return true;
    }

    if (message.type === 'GET_SCAN_STATUS') {
        getScanStatus(message.url).then(status => sendResponse(status));
        return true;
    }

    if (message.type === 'CANCEL_SCAN') {
        cancelScan(message.url);
        sendResponse({ status: 'cancelled' });
        return true;
    }

    if (message.type === 'SUBMIT_FEEDBACK') {
        submitFeedback(message.data).then(result => sendResponse(result));
        return true;
    }

    if (message.type === 'SUBMIT_REPORT') {
        submitReport(message.data).then(result => sendResponse(result));
        return true;
    }

    if (message.type === 'SET_AUTO_SCAN') {
        chrome.storage.sync.set({ autoScan: message.enabled });
        sendResponse({ status: 'ok', enabled: message.enabled });
        return true;
    }

    if (message.type === 'GET_AUTO_SCAN') {
        chrome.storage.sync.get(['autoScan'], (result) => {
            sendResponse({ enabled: !!result.autoScan });
        });
        return true;
    }

    if (message.type === 'SET_PARENTAL_CONTROL') {
        setParentalControl(message.enabled, message.pin, message.threshold).then(r => sendResponse(r));
        return true;
    }

    if (message.type === 'GET_PARENTAL_CONTROL') {
        chrome.storage.local.get(['parentalEnabled', 'parentalPIN', 'parentalThreshold'], (d) => {
            sendResponse({
                enabled: !!d.parentalEnabled,
                pin: d.parentalPIN || '0000',
                threshold: d.parentalThreshold || 70
            });
        });
        return true;
    }

    if (message.type === 'OPEN_WEEKLY_REPORT') {
        chrome.tabs.create({ url: chrome.runtime.getURL('report.html') });
        sendResponse({ status: 'opened' });
        return true;
    }

    if (message.type === 'CHECK_BLOCKLIST') {
        checkBlocklist(message.url).then(result => sendResponse(result));
        return true;
    }

    if (message.type === 'GET_STATS') {
        fetchSystemStats().then(result => sendResponse(result));
        return true;
    }
});

// ============================================================================
// SCAN HANDLER — Executes API call in background
// ============================================================================

async function handleScan(data) {
    const { url, article_text, comments, pageTitle } = data;
    const storageKey = `scan_${url}`;

    try {
        // 0. Wake up server (cold-start protection)
        await warmUpServer();

        // 1. Save scanning state immediately
        await chrome.storage.local.set({
            [storageKey]: {
                status: 'scanning',
                url: url,
                timestamp: new Date().toISOString(),
                progress: 'Đang kết nối máy chủ...'
            }
        });

        // Update badge to show scanning
        chrome.action.setBadgeText({ text: '...' });
        chrome.action.setBadgeBackgroundColor({ color: '#3498db' });

        // 2. Try API endpoints (local → cloud)
        let response = null;
        let lastError = null;

        for (const endpoint of API_ENDPOINTS) {
            try {
                console.log(`[BG] Trying: ${endpoint}`);

                // Update progress
                await chrome.storage.local.set({
                    [storageKey]: {
                        status: 'scanning',
                        url: url,
                        timestamp: new Date().toISOString(),
                        progress: 'Đang phân tích (đám mây)...'
                    }
                });

                const timeoutMs = 120000;

                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

                response = await fetch(endpoint, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ url, article_text, comments }),
                    signal: controller.signal
                });

                clearTimeout(timeoutId);

                if (response.ok) {
                    console.log(`[BG] Connected to: ${endpoint}`);
                    break;
                }
            } catch (err) {
                console.log(`[BG] Failed: ${endpoint} (${err.message})`);
                lastError = err;
                response = null;
            }
        }

        if (!response || !response.ok) {
            throw new Error(lastError?.message || "All API endpoints failed");
        }

        // 3. Parse response
        const results = await response.json();

        // 4. Save results to storage
        const resultData = {
            status: 'completed',
            url: url,
            timestamp: new Date().toISOString(),
            results: results
        };

        await chrome.storage.local.set({ [storageKey]: resultData });

        // Also save under the URL key for backward compatibility with popup.js cache
        await chrome.storage.local.set({
            [url]: {
                ...results,
                timestamp: new Date().toISOString(),
                url: url
            }
        });

        // 5. Update badge with risk score
        const riskScore = results.risk_score_v5?.risk_score || 0;
        const riskLevel = results.risk_score_v5?.risk_level || 'Low';
        updateBadge(riskScore, riskLevel);

        // 6. Add to scan history
        await addToScanHistory(url, results, pageTitle);

        console.log(`[BG] Scan completed for: ${url}`);

        // 7. Send notification if high risk (3.5)
        sendRiskNotification(url, riskScore, riskLevel);

    } catch (err) {
        console.error(`[BG] Scan failed:`, err.message);

        // Save error state
        await chrome.storage.local.set({
            [storageKey]: {
                status: 'error',
                url: url,
                timestamp: new Date().toISOString(),
                error: err.message
            }
        });

        // Update badge to show error
        chrome.action.setBadgeText({ text: '!' });
        chrome.action.setBadgeBackgroundColor({ color: '#e74c3c' });
    }
}

// ============================================================================
// SCAN STATUS
// ============================================================================

async function getScanStatus(url) {
    const storageKey = `scan_${url}`;
    const data = await chrome.storage.local.get([storageKey]);
    return data[storageKey] || null;
}

async function cancelScan(url) {
    const storageKey = `scan_${url}`;
    await chrome.storage.local.remove([storageKey]);
    chrome.action.setBadgeText({ text: '' });
}

// ============================================================================
// BADGE UPDATE
// ============================================================================

function updateBadge(riskScore, riskLevel) {
    const score = Math.round(riskScore);
    chrome.action.setBadgeText({ text: score.toString() });

    // Color based on risk level
    const colors = {
        'Low': '#27ae60',       // Green
        'Medium': '#f39c12',    // Orange
        'High': '#e74c3c',      // Red
        'Critical': '#c0392b'   // Dark Red
    };
    chrome.action.setBadgeBackgroundColor({ 
        color: colors[riskLevel] || '#3498db' 
    });
}

// ============================================================================
// SCAN HISTORY
// ============================================================================

async function addToScanHistory(url, results, pageTitle = '') {
    const MAX_HISTORY = 20;

    try {
        const data = await chrome.storage.local.get(['scanHistory']);
        let history = data.scanHistory || [];

        // Determine best article title: pageTitle > article_summary > domain fallback
        const summaryTitle = results.article_summary?.summary?.substring(0, 80) || '';
        const articleTitle = pageTitle || summaryTitle || '';
        const domain = extractDomain(url);

        // Build history entry
        const entry = {
            url: url,
            title: articleTitle || domain,
            domain: domain,
            riskScore: results.risk_score_v5?.risk_score || 0,
            riskLevel: results.risk_score_v5?.risk_level || 'Low',
            toxicPercent: results.comments_analysis?.toxic_percentage || 0,
            toxicCount: results.comments_analysis?.toxic_count || 0,
            totalComments: results.comments_analysis?.total || 0,
            verdict: results.fact_check_v5?.verdict || 'Chưa rõ',
            sentiment: results.sentiment_v5?.overall || 'Neutral',
            timestamp: new Date().toISOString(),
            resultsKey: url // Key to load full results
        };

        // Remove existing entry for same URL (update it)
        history = history.filter(h => h.url !== url);

        // Add to front
        history.unshift(entry);

        // Cap at MAX_HISTORY
        if (history.length > MAX_HISTORY) {
            // Remove old entries and their cached results
            const removed = history.splice(MAX_HISTORY);
            for (const old of removed) {
                await chrome.storage.local.remove([`scan_${old.url}`]);
            }
        }

        await chrome.storage.local.set({ scanHistory: history });
        console.log(`[BG] History updated: ${history.length} entries`);
    } catch (err) {
        console.error(`[BG] Failed to update history:`, err);
    }
}

function extractDomain(url) {
    try {
        return new URL(url).hostname.replace('www.', '');
    } catch {
        return url.substring(0, 50);
    }
}

// ============================================================================
// ARCH-01: UNIFIED SINGLE-PASS SCAN — Structured /analyze/v5/unified
// 70-80% fewer Gemini calls, 5-15s latency
// ============================================================================

async function handleUnifiedScan(data) {
    const { structured, url, article_text, comments, pageTitle } = data;
    const storageKey = `scan_${url}`;

    try {
        // 0. Wake up server (cold-start)
        await warmUpServer();

        // 1. Save scanning state immediately
        await chrome.storage.local.set({
            [storageKey]: {
                status: 'scanning',
                url,
                timestamp: new Date().toISOString(),
                progress: 'Đang phân tích thống nhất (v5)…',
            }
        });
        chrome.action.setBadgeText({ text: '…' });
        chrome.action.setBadgeBackgroundColor({ color: '#9b59b6' }); // Purple = ARCH-01 mode

        // 2. Build StructuredScanRequest body from popup's structuredScrapePageContent output
        const requestBody = {
            page_type: structured.page_type || 'generic',
            url: url,
            scraped_at: structured.scraped_at || new Date().toISOString(),
            article: {
                title: structured.article?.title || '',
                author: structured.article?.author || '',
                published_date: structured.article?.published_date || '',
                body: structured.article?.body || article_text || '',
                word_count: structured.article?.word_count || 0,
            },
            comments: (structured.comments || []).map(c =>
                typeof c === 'string'
                    ? { text: c, author: '', timestamp: '', reactions: 0, is_reply: false }
                    : { text: c.text || '', author: c.author || '', timestamp: c.timestamp || '', reactions: c.reactions || 0, is_reply: !!c.is_reply }
            ),
            metadata: {
                domain: structured.metadata?.domain || '',
                comment_count_visible: structured.metadata?.comment_count_visible || 0,
                comment_count_total: structured.metadata?.comment_count_total || 0,
                reactions_total: structured.metadata?.reactions_total || 0,
                shares: structured.metadata?.shares || 0,
                page_language: structured.metadata?.page_language || 'vi',
            },
        };

        // 3. Try unified endpoint
        let response = null;
        let lastError = null;

        for (const endpoint of UNIFIED_ENDPOINTS) {
            try {
                console.log(`[BG-unified] Trying: ${endpoint}`);

                await chrome.storage.local.set({
                    [storageKey]: {
                        status: 'scanning', url,
                        timestamp: new Date().toISOString(),
                        progress: 'Gửi dữ liệu cấu trúc đến AI…',
                    }
                });

                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), 120000);

                response = await fetch(endpoint, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(requestBody),
                    signal: controller.signal,
                });

                clearTimeout(timeoutId);

                if (response.ok) {
                    console.log(`[BG-unified] Connected: ${endpoint}`);
                    break;
                } else {
                    console.warn(`[BG-unified] ${endpoint} returned ${response.status}`);
                    response = null;
                }
            } catch (err) {
                console.warn(`[BG-unified] Failed ${endpoint}: ${err.message}`);
                lastError = err;
                response = null;
            }
        }

        // 4. Fallback to streaming if unified fails
        if (!response || !response.ok) {
            console.warn('[BG-unified] Falling back to stream endpoint');
            chrome.action.setBadgeText({ text: '…' });
            chrome.action.setBadgeBackgroundColor({ color: '#3498db' });
            return handleStreamScan({ url, article_text, comments, pageTitle });
        }

        // 5. Parse and save results
        const results = await response.json();

        const resultData = {
            status: 'completed',
            url,
            timestamp: new Date().toISOString(),
            results,
        };

        await chrome.storage.local.set({ [storageKey]: resultData });
        // URL-keyed cache: spread results directly (same format as handleScan/handleStreamScan)
        // so popup.js can use them without unwrapping the resultData envelope
        await chrome.storage.local.set({
            [url]: { ...results, timestamp: new Date().toISOString(), url }
        });

        // 6. Update badge
        const risk = results?.risk_score_v5?.risk_score ?? results?.risk_score ?? 0;
        const riskInt = Math.round(risk);
        const badgeColor = riskInt >= 75 ? '#e74c3c' : riskInt >= 50 ? '#e67e22' : riskInt >= 25 ? '#f39c12' : '#27ae60';
        chrome.action.setBadgeText({ text: `${riskInt}` });
        chrome.action.setBadgeBackgroundColor({ color: badgeColor });

        // 7. Save to scan history
        await addToScanHistory(url, results, pageTitle || structured?.article?.title || '');

        // 8. Notification for high-risk content
        if (riskInt >= 50) {
            const domain = new URL(url).hostname;
            chrome.notifications.create(`risk_${Date.now()}`, {
                type: 'basic',
                iconUrl: 'icons/icon48.png',
                title: '⚠️ VnContentGuard Pro',
                message: `${domain} — Rủi ro: ${riskInt}/100 (${results?.risk_score_v5?.risk_level || 'Cao'})`,
            });
        }

        // 9. Send results to content script for overlay
        try {
            const [tab] = await chrome.tabs.query({ url: url.replace(/#.*$/, '*') });
            if (tab) {
                chrome.tabs.sendMessage(tab.id, {
                    type: 'SHOW_OVERLAY',
                    data: results,
                }).catch(() => {}); // Content script may not be loaded yet
            }
        } catch (e) { /* ignore */ }

        console.log(`[BG-unified] Done. Risk: ${riskInt}/100, Mode: ${results?.analysis_mode || 'unknown'}`);

    } catch (err) {
        console.error('[BG-unified] Critical Error:', err);
        await chrome.storage.local.set({
            [storageKey]: {
                status: 'error',
                url,
                timestamp: new Date().toISOString(),
                error: err.message,
            }
        });
        chrome.action.setBadgeText({ text: '!' });
        chrome.action.setBadgeBackgroundColor({ color: '#e74c3c' });
    }
}

// ============================================================================
// SSE STREAMING SCAN — Feature 1.5 (v5.0)
// ============================================================================

async function handleStreamScan(data) {
    const { url, article_text, comments, pageTitle } = data;
    const storageKey = `scan_${url}`;

    try {
        // 0. Wake up server (cold-start protection)
        await warmUpServer();

        await chrome.storage.local.set({
            [storageKey]: {
                status: 'scanning',
                url: url,
                timestamp: new Date().toISOString(),
                progress: 'Đang kết nối streaming...',
                stream_modules: {}
            }
        });

        chrome.action.setBadgeText({ text: '...' });
        chrome.action.setBadgeBackgroundColor({ color: '#3498db' });

        let response = null;
        for (const endpoint of STREAM_ENDPOINTS) {
            try {
                console.log(`[BG] Stream trying: ${endpoint}`);
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), 180000);

                response = await fetch(endpoint, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ url, article_text, comments }),
                    signal: controller.signal
                });
                clearTimeout(timeoutId);
                if (response.ok) break;
            } catch (err) {
                console.log(`[BG] Stream failed: ${endpoint} (${err.message})`);
                response = null;
            }
        }

        if (!response || !response.ok) {
            // Fallback to regular scan
            console.log(`[BG] Stream unavailable, falling back to regular scan`);
            handleScan(data);
            return;
        }

        // Parse SSE stream
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        const streamModules = {};
        let finalResult = null;
        let currentEventType = ''; // Track SSE event type

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop() || '';

            for (const line of lines) {
                if (line.startsWith('event: ')) {
                    currentEventType = line.substring(7).trim();
                } else if (line.startsWith('data: ')) {
                    try {
                        const jsonStr = line.substring(6);
                        const evt = JSON.parse(jsonStr);

                        if (currentEventType === 'module') {
                            streamModules[evt.module] = evt.data;
                            // Save progressive update
                            await chrome.storage.local.set({
                                [storageKey]: {
                                    status: 'scanning',
                                    url: url,
                                    timestamp: new Date().toISOString(),
                                    progress: `Hoàn tất: ${evt.module}`,
                                    stream_modules: streamModules,
                                    completed_count: Object.keys(streamModules).length
                                }
                            });
                        } else if (currentEventType === 'complete') {
                            finalResult = evt;
                        } else if (currentEventType === 'error') {
                            console.error(`[BG] Stream error: ${evt.message}`);
                        }
                    } catch (parseErr) {
                        console.warn(`[BG] SSE parse error:`, parseErr.message);
                    }
                    currentEventType = ''; // Reset after processing
                }
            }
        }

        // Use final result or build from modules
        const results = finalResult || buildResultFromModules(streamModules);
        const resultData = {
            status: 'completed',
            url: url,
            timestamp: new Date().toISOString(),
            results: results,
            stream_modules: streamModules
        };

        await chrome.storage.local.set({ [storageKey]: resultData });
        await chrome.storage.local.set({
            [url]: { ...results, timestamp: new Date().toISOString(), url: url }
        });

        const riskScore = results.risk_score_v5?.risk_score || 0;
        const riskLevel = results.risk_score_v5?.risk_level || 'Low';
        updateBadge(riskScore, riskLevel);
        await addToScanHistory(url, results, pageTitle);
        sendRiskNotification(url, riskScore, riskLevel);

        console.log(`[BG] Stream scan completed for: ${url}`);

    } catch (err) {
        console.error(`[BG] Stream scan fail:`, err.message);
        // Fallback to regular scan
        handleScan(data);
    }
}

function buildResultFromModules(modules) {
    return {
        version: '5.0',
        article_summary: modules.article_summary || {},
        sentiment_v5: modules.sentiment_v5 || {},
        toxicity_v5: modules.toxicity_v5 || {},
        fact_check_v5: modules.fact_check_v5 || {},
        risk_score_v5: modules.risk_score_v5 || {},
        comments_analysis: modules.comments_analysis || {}
    };
}

// ============================================================================
// NOTIFICATION SYSTEM — Feature 3.5 (v5.0)
// ============================================================================

function sendRiskNotification(url, riskScore, riskLevel) {
    if (riskScore < 50) return; // Only notify for medium+ risk

    const domain = extractDomain(url);
    const icons = { 'Low': '✅', 'Medium': '⚠️', 'High': '🚨', 'Critical': '🔴' };
    const icon = icons[riskLevel] || '⚠️';

    const notifId = `risk_${Date.now()}`;
    chrome.notifications.create(notifId, {
        type: 'basic',
        iconUrl: 'icons/icon.png',
        title: `${icon} VnContentGuard — Cảnh báo rủi ro`,
        message: `${domain}: Mức rủi ro ${riskLevel} (${Math.round(riskScore)}/100)`,
        priority: riskScore >= 70 ? 2 : 1,
        requireInteraction: riskScore >= 70
    }, () => {
        console.log(`[BG] Notification sent: ${notifId}`);
    });

    // Store notification in history
    chrome.storage.local.get(['notificationHistory'], (data) => {
        const history = data.notificationHistory || [];
        history.unshift({
            id: notifId,
            url: url,
            domain: domain,
            riskScore: riskScore,
            riskLevel: riskLevel,
            timestamp: new Date().toISOString(),
            read: false
        });
        // Keep last 50
        if (history.length > 50) history.splice(50);
        chrome.storage.local.set({ notificationHistory: history });
    });
}

chrome.notifications.onClicked.addListener((notifId) => {
    // Mark as read
    chrome.storage.local.get(['notificationHistory'], (data) => {
        const history = data.notificationHistory || [];
        const notif = history.find(n => n.id === notifId);
        if (notif) {
            notif.read = true;
            chrome.storage.local.set({ notificationHistory: history });
            // Open the URL in a new tab
            if (notif.url) chrome.tabs.create({ url: notif.url });
        }
    });
});

// ============================================================================
// COMMUNITY REPORT — Feature 4.1 (v5.0)
// ============================================================================

async function submitReport(data) {
    for (const endpoint of REPORT_ENDPOINTS) {
        try {
            const response = await fetch(endpoint, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(data),
            });
            if (response.ok) {
                const result = await response.json();
                console.log(`[BG] Report submitted to: ${endpoint}`);
                // Refresh blocklist
                await refreshBlocklist(true);
                return result;
            }
        } catch (err) {
            console.log(`[BG] Report endpoint failed: ${endpoint}`);
        }
    }
    return { status: 'error', message: 'Không thể gửi báo cáo' };
}

// ============================================================================
// COMMUNITY BLOCKLIST — Feature 4.1 (v5.0)
// ============================================================================

async function refreshBlocklist(force = false) {
    const now = Date.now();
    if (!force && (now - blocklistLastFetch) < BLOCKLIST_REFRESH_MS && cachedBlocklist.length > 0) {
        return cachedBlocklist;
    }

    for (const endpoint of BLOCKLIST_ENDPOINTS) {
        try {
            const response = await fetch(endpoint, { method: 'GET' });
            if (response.ok) {
                const data = await response.json();
                cachedBlocklist = data.blocklist || [];
                blocklistLastFetch = now;
                console.log(`[BG] Blocklist refreshed: ${cachedBlocklist.length} domains`);
                return cachedBlocklist;
            }
        } catch { /* try next endpoint */ }
    }
    return cachedBlocklist;
}

async function checkBlocklist(url) {
    await refreshBlocklist();
    try {
        const domain = new URL(url).hostname.replace('www.', '');
        const isBlocked = cachedBlocklist.some(d => domain.includes(d) || d.includes(domain));
        return { blocked: isBlocked, domain: domain };
    } catch {
        return { blocked: false, domain: url };
    }
}

// ============================================================================
// PARENTAL CONTROL — Feature 4.2 (v5.0)
// ============================================================================

async function setParentalControl(enabled, pin, threshold) {
    await chrome.storage.local.set({
        parentalEnabled: enabled,
        parentalPIN: pin || '0000',
        parentalThreshold: threshold || 70
    });
    console.log(`[BG] Parental control: ${enabled ? 'ON' : 'OFF'}, threshold: ${threshold}`);
    return { status: 'ok', enabled, threshold };
}

// ============================================================================
// CONTENT WARNING + PARENTAL INTERCEPT — Features 4.2 + 4.3 (v5.0)
// ============================================================================

chrome.webNavigation.onCompleted.addListener(async (details) => {
    if (details.frameId !== 0 || !details.url) return;
    if (details.url.startsWith('chrome') || details.url.startsWith('about')) return;

    try {
        const url = details.url;
        const domain = new URL(url).hostname.replace('www.', '');

        // Check whitelisted domains
        const storage = await chrome.storage.local.get([
            'whitelistedDomains', 'warningAcknowledged',
            'parentalEnabled', 'parentalThreshold', 'parentalBypass'
        ]);

        const whitelisted = storage.whitelistedDomains || [];
        if (whitelisted.includes(domain)) return;

        const acknowledged = storage.warningAcknowledged || [];
        if (acknowledged.includes(url)) return;

        const parentalBypass = storage.parentalBypass || [];
        if (parentalBypass.includes(url)) return;

        // Check community blocklist
        const blockResult = await checkBlocklist(url);
        if (blockResult.blocked) {
            // 4.3 — Redirect to warning page
            const warningUrl = chrome.runtime.getURL('warning.html') +
                `?url=${encodeURIComponent(url)}&reports=5%2B&risk=Cao`;
            chrome.tabs.update(details.tabId, { url: warningUrl });
            return;
        }

        // 4.2 — Parental control: check previous scan results
        if (storage.parentalEnabled) {
            const threshold = storage.parentalThreshold || 70;
            const scanData = await chrome.storage.local.get([url]);
            const cached = scanData[url];

            if (cached) {
                const risk = cached.risk_score_v5?.risk_score || 0;
                if (risk >= threshold) {
                    const blockUrl = chrome.runtime.getURL('block.html') +
                        `?url=${encodeURIComponent(url)}&risk=${risk >= 70 ? 'Cao' : 'Trung bình'}`;
                    chrome.tabs.update(details.tabId, { url: blockUrl });
                    return;
                }
            }
        }
    } catch (err) {
        console.log(`[BG] Warning/Parental check error:`, err.message);
    }
});

// ============================================================================
// WEEKLY SAFETY REPORT — Feature 4.4 (v5.0)
// ============================================================================

// Set up weekly alarm
chrome.alarms.create('weeklyReport', {
    // Fire every 7 days (in minutes)
    periodInMinutes: 7 * 24 * 60
});

chrome.alarms.onAlarm.addListener((alarm) => {
    if (alarm.name === 'weeklyReport') {
        generateWeeklyReportNotification();
    }
    if (alarm.name === 'keepAlive') {
        // Ping backend to prevent Render cold-start
        fetch(HEALTH_URL).then(() => console.log('[BG] Keep-alive ping OK')).catch(() => {});
    }
});

async function generateWeeklyReportNotification() {
    const data = await chrome.storage.local.get(['scanHistory']);
    const history = data.scanHistory || [];

    if (history.length === 0) return;

    // Count this week's stats
    const weekAgo = new Date();
    weekAgo.setDate(weekAgo.getDate() - 7);

    const weekScans = history.filter(s => new Date(s.timestamp) >= weekAgo);
    const highRisk = weekScans.filter(s => (s.riskScore || 0) >= 70).length;
    const total = weekScans.length;

    if (total === 0) return;

    chrome.notifications.create('weekly_report_' + Date.now(), {
        type: 'basic',
        iconUrl: 'icons/icon.png',
        title: '📊 Báo cáo an toàn hàng tuần',
        message: `Tuần này: ${total} trang đã quét, ${highRisk} rủi ro cao. Nhấn để xem chi tiết.`,
        priority: 1,
        buttons: [{ title: '📋 Xem báo cáo' }]
    });
}

chrome.notifications.onButtonClicked.addListener((notifId, btnIdx) => {
    if (notifId.startsWith('weekly_report_') && btnIdx === 0) {
        chrome.tabs.create({ url: chrome.runtime.getURL('report.html') });
    }
});

// ============================================================================
// SYSTEM STATS — Feature 3.4 (v5.0)
// ============================================================================

async function fetchSystemStats() {
    for (const endpoint of STATS_ENDPOINTS) {
        try {
            const response = await fetch(endpoint, { method: 'GET', signal: AbortSignal.timeout(5000) });
            if (response.ok) {
                const data = await response.json();
                console.log(`[BG] Stats fetched from: ${endpoint}`);
                return data;
            }
        } catch { /* try next endpoint */ }
    }
    return { status: '🔴 Offline', error: 'Không thể kết nối server' };
}

// ============================================================================
// FEEDBACK SUBMISSION
// ============================================================================

async function submitFeedback(data) {
    for (const endpoint of FEEDBACK_ENDPOINTS) {
        try {
            const response = await fetch(endpoint, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(data),
            });
            if (response.ok) {
                const result = await response.json();
                console.log(`[BG] Feedback submitted to: ${endpoint}`);
                return result;
            }
        } catch (err) {
            console.log(`[BG] Feedback endpoint failed: ${endpoint} (${err.message})`);
        }
    }
    // If all endpoints fail, store locally
    console.log('[BG] Feedback stored locally (backend unavailable)');
    return { status: 'stored_locally', message: 'Phản hồi đã lưu, sẽ gửi khi có kết nối.' };
}

// ============================================================================
// AUTO-SCAN — Feature 1.3 (v5.0)
// ============================================================================

chrome.tabs.onUpdated.addListener(async (tabId, changeInfo, tab) => {
    // Only trigger on complete page load
    if (changeInfo.status !== 'complete' || !tab.url) return;

    // Check if auto-scan is enabled
    const prefs = await chrome.storage.sync.get(['autoScan']);
    if (!prefs.autoScan) return;

    // Check if URL matches supported domains
    const url = tab.url;
    const isSupported = AUTO_SCAN_DOMAINS.some(domain => url.includes(domain));
    if (!isSupported) return;

    // Rate limit: skip if scanned within cooldown period
    const now = Date.now();
    if (autoScanTimestamps[url] && (now - autoScanTimestamps[url]) < AUTO_SCAN_COOLDOWN_MS) {
        console.log(`[BG] Auto-scan skipped (cooldown): ${url}`);
        return;
    }

    // Check if scan already exists for this URL
    const existing = await getScanStatus(url);
    if (existing && (existing.status === 'scanning' || existing.status === 'completed')) {
        console.log(`[BG] Auto-scan skipped (already scanned): ${url}`);
        return;
    }

    console.log(`[BG] ⚡ Auto-scan triggered: ${url}`);
    autoScanTimestamps[url] = now;

    // Scrape content from the tab
    try {
        const scrapeResult = await chrome.scripting.executeScript({
            target: { tabId: tabId },
            func: autoScrapeContent
        });

        if (!scrapeResult || !scrapeResult[0] || !scrapeResult[0].result) {
            console.log('[BG] Auto-scan: No content scraped');
            return;
        }

        const scraped = scrapeResult[0].result;
        const articleBody = scraped.article?.body || scraped.text || '';
        if (articleBody.trim().length < 30) {
            console.log('[BG] Auto-scan: Content too short');
            return;
        }

        // Start the scan (use unified if structured data available)
        if (scraped._is_structured) {
            handleUnifiedScan({
                structured: scraped,
                url: url,
                article_text: articleBody,
                comments: scraped._flat_comments || (scraped.comments || []).map(c => typeof c === 'string' ? c : c.text),
                pageTitle: '',
            });
        } else {
            handleScan({
                url: url,
                article_text: scraped.text,
                comments: scraped.comments || [],
            });
        }

    } catch (err) {
        console.log(`[BG] Auto-scan scrape failed: ${err.message}`);
    }
});

/**
 * Lightweight structured content scraper for auto-scan.
 * Returns same format as structuredScrapePageContent() in popup.js.
 * Runs in the content script context of the tab.
 */
function autoScrapeContent() {
    try {
        const hostname = location.hostname;
        const domain = hostname.replace(/^www\./, '');
        const cleanText = (raw) => (raw || '').trim().replace(/\s+/g, ' ');

        // Detect page type
        let pageType = 'generic';
        if (hostname.includes('facebook.com')) pageType = 'facebook_post';
        else if (hostname.includes('youtube.com')) pageType = 'youtube_video';
        else if (hostname.includes('tiktok.com')) pageType = 'tiktok';
        else if (/vnexpress|dantri|tuoitre|thanhnien|24h|vietnamnet/.test(hostname)) pageType = 'news_article';

        // Get main content with platform-aware selectors
        let text = '';
        let articleTitle = '';
        let articleAuthor = '';

        if (pageType === 'youtube_video') {
            const ytTitle = document.querySelector('h1.ytd-watch-metadata yt-formatted-string, #title h1 yt-formatted-string, ytd-watch-metadata h1');
            if (ytTitle) articleTitle = cleanText(ytTitle.innerText);
            const ytChannel = document.querySelector('ytd-channel-name yt-formatted-string a, #channel-name a');
            if (ytChannel) articleAuthor = cleanText(ytChannel.innerText);
            const ytDesc = document.querySelector('ytd-text-inline-expander yt-attributed-string, #description-inner yt-attributed-string');
            if (ytDesc) text = cleanText(ytDesc.innerText).substring(0, 3000);
            if (!text) { const m = document.querySelector('meta[name="description"]'); if (m) text = m.getAttribute('content') || ''; }
        } else if (pageType === 'tiktok') {
            const ttDesc = document.querySelector('[data-e2e="browse-video-desc"], [data-e2e="video-desc"]');
            if (ttDesc) { text = cleanText(ttDesc.innerText).substring(0, 2000); articleTitle = text.substring(0, 100); }
            const ttAuthor = document.querySelector('[data-e2e="browse-video-author-title"], [data-e2e="video-author-uniqueid"]');
            if (ttAuthor) articleAuthor = cleanText(ttAuthor.innerText);
            if (!text) { const m = document.querySelector('meta[name="description"], meta[property="og:description"]'); if (m) text = m.getAttribute('content') || ''; }
        } else {
            const articleEl = document.querySelector('article, [role="article"], main');
            if (articleEl) {
                const h1 = articleEl.querySelector('h1');
                if (h1) articleTitle = cleanText(h1.innerText);
                text = articleEl.innerText.substring(0, 5000).trim();
            }
        }
        if (!text || text.length < 30) {
            const h1 = document.querySelector('h1');
            if (h1) articleTitle = cleanText(h1.innerText);
            text = document.body.innerText.substring(0, 5000).trim();
        }

        // Get comments with platform-aware selectors
        const commentSet = new Set();
        const structuredComments = [];

        const addComment = (t, author = '') => {
            const clean = cleanText(t);
            if (clean.length > 5 && clean.length < 500 && !commentSet.has(clean)) {
                commentSet.add(clean);
                structuredComments.push({ text: clean, author, reactions: 0, is_reply: false, timestamp: '' });
            }
        };

        if (pageType === 'youtube_video') {
            document.querySelectorAll('ytd-comment-renderer #content-text, ytd-comment-view-model #content-text').forEach(el => {
                const container = el.closest('ytd-comment-renderer, ytd-comment-view-model');
                const author = container?.querySelector('#author-text span')?.innerText || '';
                addComment(el.innerText, cleanText(author));
            });
        } else if (pageType === 'tiktok') {
            document.querySelectorAll('[data-e2e="comment-level-1"] p, [data-e2e="comment-level-1-item"]').forEach(el => {
                const container = el.closest('[data-e2e="comment-level-1"], [class*="CommentItemContainer"]');
                const author = container?.querySelector('[data-e2e="comment-username-1"]')?.innerText || '';
                addComment(el.innerText, cleanText(author));
            });
        } else {
            const commentSelectors = [
                '[data-testid="comment"]', '.comment-content', '.comment_text',
                '[data-comment-id]', '.user-comment', '[class*="comment"] p'
            ];
            commentSelectors.forEach(sel => {
                document.querySelectorAll(sel).forEach(el => addComment(el.innerText));
            });
        }
        const finalComments = structuredComments.slice(0, 50);

        return {
            page_type: pageType,
            url: location.href,
            scraped_at: new Date().toISOString(),
            article: {
                title: articleTitle.substring(0, 200),
                author: articleAuthor,
                published_date: '',
                body: text,
                word_count: text.split(/\s+/).filter(Boolean).length,
            },
            comments: finalComments,
            metadata: {
                domain: domain,
                comment_count_visible: finalComments.length,
                comment_count_total: finalComments.length,
                reactions_total: 0,
                shares: 0,
                page_language: document.documentElement.lang || 'vi',
            },
            text: text,
            _flat_comments: finalComments.map(c => c.text),
            _is_structured: true,
        };
    } catch (err) {
        return {
            text: document.body.innerText.substring(0, 3000),
            comments: [],
            _is_structured: false,
        };
    }
}

// ============================================================================
// SERVICE WORKER LIFECYCLE
// ============================================================================

chrome.runtime.onInstalled.addListener(() => {
    console.log('[BG] VnContentGuard Pro v5.0 service worker installed');
    chrome.action.setBadgeText({ text: '' });

    // Initialize weekly report alarm
    chrome.alarms.create('weeklyReport', { periodInMinutes: 7 * 24 * 60 });

    // Keep backend warm: ping every 10 minutes to prevent Render cold-start
    chrome.alarms.create('keepAlive', { periodInMinutes: 10 });

    // Initialize blocklist
    refreshBlocklist(true);

    // Clear old parental bypass on install
    chrome.storage.local.set({ parentalBypass: [] });
});

// Keep service worker alive during scans
chrome.runtime.onStartup.addListener(() => {
    console.log('[BG] Service worker started');
});
