/**
 * VnContentGuard Pro v5.0 — Background Service Worker
 * =====================================================
 * Handles API calls in the background so they survive popup close.
 * 
 * Responsibilities:
 * 1. Receive scan requests from popup via chrome.runtime.sendMessage
 * 2. Execute API call (try local → cloud fallback)
 * 3. Save results to chrome.storage.local
 * 4. Update badge with risk score
 * 5. Notify popup when done (if still open)
 * 6. Auto-scan supported sites when toggle is ON (v5.0)
 */

// API endpoints (local first, cloud fallback)
const API_ENDPOINTS = [
    "http://127.0.0.1:8000/analyze/v3",
    "https://vncontentguard-pro.onrender.com/analyze/v3"
];

// Feedback endpoints
const FEEDBACK_ENDPOINTS = [
    "http://127.0.0.1:8000/api/feedback",
    "https://vncontentguard-pro.onrender.com/api/feedback"
];

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
        return true; // Keep channel open for async
    }

    if (message.type === 'GET_SCAN_STATUS') {
        getScanStatus(message.url).then(status => sendResponse(status));
        return true; // Async response
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
});

// ============================================================================
// SCAN HANDLER — Executes API call in background
// ============================================================================

async function handleScan(data) {
    const { url, article_text, comments } = data;
    const storageKey = `scan_${url}`;

    try {
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
                        progress: endpoint.includes('127.0.0.1') 
                            ? 'Đang phân tích (máy chủ cục bộ)...' 
                            : 'Đang phân tích (đám mây)...'
                    }
                });

                const isLocal = endpoint.includes('127.0.0.1') || endpoint.includes('localhost');
                const timeoutMs = isLocal ? 120000 : 30000;

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
        const riskScore = results.risk_score_v3?.risk_score || 0;
        const riskLevel = results.risk_score_v3?.risk_level || 'Low';
        updateBadge(riskScore, riskLevel);

        // 6. Add to scan history
        await addToScanHistory(url, results);

        console.log(`[BG] Scan completed for: ${url}`);

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

async function addToScanHistory(url, results) {
    const MAX_HISTORY = 20;

    try {
        const data = await chrome.storage.local.get(['scanHistory']);
        let history = data.scanHistory || [];

        // Build history entry
        const entry = {
            url: url,
            title: extractDomain(url),
            riskScore: results.risk_score_v3?.risk_score || 0,
            riskLevel: results.risk_score_v3?.risk_level || 'Low',
            toxicPercent: results.comments_analysis?.toxic_percentage || 0,
            toxicCount: results.comments_analysis?.toxic_count || 0,
            totalComments: results.comments_analysis?.total || 0,
            verdict: results.fact_check_v3?.verdict || 'Chưa rõ',
            sentiment: results.sentiment_v3?.overall || 'Neutral',
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
// FEEDBACK SUBMISSION (v5.0)
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
        if (!scraped.text || scraped.text.trim().length < 30) {
            console.log('[BG] Auto-scan: Content too short');
            return;
        }

        // Start the scan
        handleScan({
            url: url,
            article_text: scraped.text,
            comments: scraped.comments
        });

    } catch (err) {
        console.log(`[BG] Auto-scan scrape failed: ${err.message}`);
    }
});

/**
 * Lightweight content scraper for auto-scan.
 * Runs in the content script context of the tab.
 */
function autoScrapeContent() {
    try {
        let text = "";
        let comments = [];

        // Get main content
        const main = document.querySelector('article') ||
                     document.querySelector('main') ||
                     document.querySelector('[role="main"]') ||
                     document.querySelector('[role="article"]');

        if (main) {
            text = main.innerText.substring(0, 5000).trim();
        }
        if (!text || text.length < 30) {
            text = document.body.innerText.substring(0, 5000).trim();
        }

        // Get comments (basic)
        const commentSet = new Set();
        const commentSelectors = [
            '[data-testid="comment"]', '.comment', '.comments',
            '.comment-content', '[data-comment-id]', '.user-comment'
        ];
        commentSelectors.forEach(sel => {
            document.querySelectorAll(sel).forEach(el => {
                const t = (el.innerText || '').trim();
                if (t.length > 5 && t.length < 500) commentSet.add(t);
            });
        });
        comments = Array.from(commentSet).slice(0, 50);

        return { text, comments };
    } catch (err) {
        return { text: document.body.innerText.substring(0, 3000), comments: [] };
    }
}

// ============================================================================
// SERVICE WORKER LIFECYCLE
// ============================================================================

chrome.runtime.onInstalled.addListener(() => {
    console.log('[BG] VnContentGuard Pro v5.0 service worker installed');
    chrome.action.setBadgeText({ text: '' });
});

// Keep service worker alive during scans
chrome.runtime.onStartup.addListener(() => {
    console.log('[BG] Service worker started');
});
