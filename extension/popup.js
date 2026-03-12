/**
 * VnContentGuard Pro V7.0 — Popup Script
 * ========================================
 * - Delegates API calls to background.js (survives popup close)
 * - Resumes scan state on popup reopen
 * - Scan history + comparison mode
 * - Dark mode support
 * - Export report (PDF/HTML)
 * - Auto-scan for supported sites
 * - Offline regex mode with instant partial results
 * - SSE Streaming results (V7)
 * - Community report & blocklist (V7)
 * - Parental control + Domain Blacklist/Whitelist (V7)
 * - Weekly safety report (V7)
 * - Unified single-pass AI analysis (V7 ARCH-01)
 * - Explainable AI — evidence spans (V7.3)
 * - Incognito detection (V7.6)
 * - Score Correction + Re-Ranker (V7.9)
 * - Scam URL reporting (V7.12)
 * - Bulk analysis mode (V7.13)
 */

let currentResultsData = null;
let currentTabUrl = null;
let scanPollInterval = null;

document.addEventListener('DOMContentLoaded', async () => {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    
    if (tab) {
        currentTabUrl = tab.url;
        
        // Reset UI to clean state
        document.getElementById('results').classList.add('hidden');
        document.getElementById('confirmation').classList.add('hidden');
        document.getElementById('warningModal').classList.add('hidden');
        document.getElementById('errorBox').classList.add('hidden');
        document.getElementById('streamProgress').classList.add('hidden');
        document.getElementById('scanBtn').disabled = false;
        document.getElementById('scanBtn').textContent = '🚀 QUÉT TRANG NÀY';
        document.getElementById('status').textContent = 'Sẵn sàng quét';

        // Check blocklist for current URL (V7)
        checkBlocklistStatus(tab.url);

        // Fetch and display system stats (V7)
        loadUsageDashboard();

        // Apply saved dark mode preference
        chrome.storage.sync.get(['darkMode'], (result) => {
            if (result.darkMode) {
                document.body.classList.add('dark-mode');
                const dmBtn = document.getElementById('darkModeBtn');
                if (dmBtn) dmBtn.textContent = '☀️';
            }
        });

        // CHECK 1: Is a scan currently in progress? (Resume after popup close/reopen)
        const scanStatus = await chrome.runtime.sendMessage({ type: 'GET_SCAN_STATUS', url: tab.url });
        
        if (scanStatus && scanStatus.status === 'scanning') {
            // Scan is in progress — show loading state and poll for completion
            showScanInProgress(scanStatus);
            startPollingForResults(tab.url);
        } else if (scanStatus && scanStatus.status === 'completed' && scanStatus.results) {
            // Scan just completed — show results
            console.log("📂 Loading completed scan results for:", tab.url);
            currentResultsData = scanStatus.results;
            renderResults(scanStatus.results);
        } else if (scanStatus && scanStatus.status === 'error') {
            // Scan failed — show error
            showError(scanStatus.error || 'Phân tích thất bại');
        } else {
            // CHECK 2: Any cached results for this URL?
            chrome.storage.local.get([tab.url], (result) => {
                if (result[tab.url]) {
                    console.log("📂 Loading cached results for:", tab.url);
                    currentResultsData = result[tab.url];
                    renderResults(result[tab.url]);
                }
            });
        }
    }

    // Dark mode toggle
    const darkModeBtn = document.getElementById('darkModeBtn');
    if (darkModeBtn) {
        darkModeBtn.addEventListener('click', () => {
            const isDark = document.body.classList.toggle('dark-mode');
            darkModeBtn.textContent = isDark ? '☀️' : '🌙';
            chrome.storage.sync.set({ darkMode: isDark });
        });
    }

    // ── Hamburger dropdown menu toggle ──────────────────────────────────────────
    const menuToggleBtn = document.getElementById('menuToggleBtn');
    const headerDropdown = document.getElementById('headerDropdown');
    if (menuToggleBtn && headerDropdown) {
        menuToggleBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            headerDropdown.classList.toggle('hidden');
        });
        document.addEventListener('click', (e) => {
            if (!headerDropdown.contains(e.target) && e.target !== menuToggleBtn) {
                headerDropdown.classList.add('hidden');
            }
        });
    }

    // ── Results tab switching ────────────────────────────────────────────────────
    document.querySelectorAll('.result-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            document.querySelectorAll('.result-tab').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            const target = tab.dataset.tab;
            const analysisPane = document.getElementById('tab-analysis');
            const summaryPane  = document.getElementById('tab-summary');
            if (analysisPane) analysisPane.classList.toggle('hidden', target !== 'analysis');
            if (summaryPane)  summaryPane.classList.toggle('hidden', target !== 'summary');
        });
    });

    // Clear cache button handler
    if (document.getElementById('clearCache')) {
        document.getElementById('clearCache').addEventListener('click', async () => {
            if (currentTabUrl) {
                chrome.storage.local.remove([currentTabUrl, `scan_${currentTabUrl}`], () => {
                    console.log("🗑️ Cleared cache for:", currentTabUrl);
                    currentResultsData = null;
                    document.getElementById('results').classList.add('hidden');
                    document.getElementById('confirmation').classList.add('hidden');
                    document.getElementById('warningModal').classList.add('hidden');
                    document.getElementById('scanBtn').disabled = false;
                    document.getElementById('scanBtn').textContent = '🚀 QUÉT TRANG NÀY';
                    document.getElementById('status').textContent = 'Đã xóa kết quả đã lưu — Sẵn sàng quét';
                    chrome.action.setBadgeText({ text: '' });
                });
            }
        });
    }

    // History button handler
    const historyBtn = document.getElementById('historyBtn');
    if (historyBtn) {
        historyBtn.addEventListener('click', toggleHistory);
    }

    // Export report button handler
    const exportBtn = document.getElementById('exportBtn');
    if (exportBtn) {
        exportBtn.addEventListener('click', () => {
            if (currentResultsData) {
                exportReport(currentResultsData, currentTabUrl);
            }
        });
    }

    // V7.0 — Auto-scan toggle handler
    const autoScanBtn = document.getElementById('autoScanBtn');
    if (autoScanBtn) {
        // Load current auto-scan state
        chrome.runtime.sendMessage({ type: 'GET_AUTO_SCAN' }, (response) => {
            if (response && response.enabled) {
                autoScanBtn.classList.add('active');
                autoScanBtn.title = 'Tự động quét: BẬT';
            }
        });

        autoScanBtn.addEventListener('click', async () => {
            const isActive = autoScanBtn.classList.toggle('active');
            autoScanBtn.title = isActive ? 'Tự động quét: BẬT' : 'Tự động quét: TẮT';
            chrome.runtime.sendMessage({ type: 'SET_AUTO_SCAN', enabled: isActive });
            
            // Show brief status
            const statusEl = document.getElementById('status');
            statusEl.textContent = isActive ? '⚡ Tự động quét: BẬT' : 'Tự động quét: TẮT';
            setTimeout(() => { statusEl.textContent = 'Sẵn sàng quét'; }, 2000);
        });
    }

    // V7.0 — Comparison mode button handler
    const compareBtn = document.getElementById('compareBtn');
    if (compareBtn) {
        compareBtn.addEventListener('click', toggleComparePanel);
    }

    // V7.0 — Compare Go button
    const compareGoBtn = document.getElementById('compareGoBtn');
    if (compareGoBtn) {
        compareGoBtn.addEventListener('click', runComparison);
    }

    // V7.0 — Feedback button handlers
    const feedbackUp = document.getElementById('feedbackUp');
    const feedbackDown = document.getElementById('feedbackDown');
    if (feedbackUp) {
        feedbackUp.addEventListener('click', () => handleFeedback('positive'));
    }
    if (feedbackDown) {
        feedbackDown.addEventListener('click', () => handleFeedback('negative'));
    }

    const feedbackSubmit = document.getElementById('feedbackSubmit');
    if (feedbackSubmit) {
        feedbackSubmit.addEventListener('click', submitFeedbackWithCorrection);
    }

    // V7 — Report page button handler
    const reportPageBtn = document.getElementById('reportPageBtn');
    if (reportPageBtn) {
        reportPageBtn.addEventListener('click', toggleReportPanel);
    }

    const reportSubmitBtn = document.getElementById('reportSubmitBtn');
    if (reportSubmitBtn) {
        reportSubmitBtn.addEventListener('click', submitPageReport);
    }

    // V7 — Weekly report button handler
    const weeklyReportBtn = document.getElementById('weeklyReportBtn');
    if (weeklyReportBtn) {
        weeklyReportBtn.addEventListener('click', () => {
            chrome.runtime.sendMessage({ type: 'OPEN_WEEKLY_REPORT' });
        });
    }

    // V7 — Parental control button handler
    const parentalBtn = document.getElementById('parentalBtn');
    if (parentalBtn) {
        parentalBtn.addEventListener('click', toggleParentalPanel);
    }

    const parentalSaveBtn = document.getElementById('parentalSaveBtn');
    if (parentalSaveBtn) {
        parentalSaveBtn.addEventListener('click', saveParentalSettings);
    }

    const parentalThreshold = document.getElementById('parentalThreshold');
    if (parentalThreshold) {
        parentalThreshold.addEventListener('input', (e) => {
            document.getElementById('parentalThresholdVal').textContent = e.target.value;
        });
    }

    // ── feature 7.2 — Domain Blacklist / Whitelist UI ──────────────────────

    // Tab switching
    document.getElementById('blacklistTabBtn')?.addEventListener('click', () => switchDomainTab('blacklist'));
    document.getElementById('whitelistTabBtn')?.addEventListener('click', () => switchDomainTab('whitelist'));

    // Add buttons
    document.getElementById('blacklistAddBtn')?.addEventListener('click', () => addDomainToList('blacklist'));
    document.getElementById('whitelistAddBtn')?.addEventListener('click', () => addDomainToList('whitelist'));

    // Enter key in inputs
    document.getElementById('blacklistInput')?.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') addDomainToList('blacklist');
    });
    document.getElementById('whitelistInput')?.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') addDomainToList('whitelist');
    });

    // Import / Export
    document.getElementById('blacklistImportBtn')?.addEventListener('click', () => importDomainList('blacklist'));
    document.getElementById('blacklistExportBtn')?.addEventListener('click', () => exportDomainList('blacklist'));
    document.getElementById('whitelistImportBtn')?.addEventListener('click', () => importDomainList('whitelist'));
    document.getElementById('whitelistExportBtn')?.addEventListener('click', () => exportDomainList('whitelist'));

    // Load seed blacklist
    document.getElementById('loadSeedBlacklistBtn')?.addEventListener('click', async () => {
        const btn = document.getElementById('loadSeedBlacklistBtn');
        if (btn) { btn.disabled = true; btn.textContent = '⏳...'; }
        const r = await chrome.runtime.sendMessage({ type: 'LOAD_SEED_BLACKLIST' });
        if (btn) { btn.disabled = false; btn.textContent = '🌐 Tải mặc định'; }
        if (r?.ok) {
            showStatusMessage(`✅ Tải ${r.total} tên miền thành công!`);
            await loadDomainLists();
        } else {
            showStatusMessage('❌ ' + (r?.error || 'Lỗi không xác định'));
        }
    });

    // ── feature 7.6 — Incognito Log UI ────────────────────────────────────

    document.getElementById('incognitoLogBtn')?.addEventListener('click', () => {
        const panel = document.getElementById('incognitoLogPanel');
        if (panel) { panel.classList.toggle('hidden'); renderIncognitoLog(); }
    });
    document.getElementById('incognitoLogClearBtn')?.addEventListener('click', async () => {
        await chrome.runtime.sendMessage({ type: 'CLEAR_INCOGNITO_LOG' });
        document.getElementById('incognitoLogCount').textContent = '0';
        document.getElementById('incognitoLogList').innerHTML = '<div style="color:var(--text-secondary);text-align:center;padding:8px;">Nhật ký trống.</div>';
    });

    // ── feature 7.13 — Bulk Analysis ──────────────────────────────────────
    document.getElementById('bulkBtn')?.addEventListener('click', toggleBulkPanel);
    document.getElementById('bulkScanBtn')?.addEventListener('click', runBulkScan);
    document.getElementById('bulkExportBtn')?.addEventListener('click', exportBulkCsv);

    // ── feature 7.9 — Score Correction sliders ────────────────────────────
    document.getElementById('corrRiskSlider')?.addEventListener('input', (e) => {
        document.getElementById('corrRiskVal').textContent = e.target.value;
    });
    document.getElementById('corrToxSlider')?.addEventListener('input', (e) => {
        document.getElementById('corrToxVal').textContent = e.target.value;
    });
    document.getElementById('corrSubmitBtn')?.addEventListener('click', submitCorrection);

    // ── feature 7.12 — Scam prompt handlers ──────────────────────────────
    document.getElementById('scamConfirmBtn')?.addEventListener('click', confirmScamReport);
    document.getElementById('scamDenyBtn')?.addEventListener('click', () => {
        document.getElementById('scamPromptCard')?.classList.add('hidden');
        _pendingScam = null;
    });
});

// ============================================================================
// SCAN IN PROGRESS — Resume state after popup reopen
// ============================================================================

function showScanInProgress(scanStatus) {
    document.getElementById('results').classList.add('hidden');
    document.getElementById('confirmation').classList.add('hidden');
    document.getElementById('errorBox').classList.add('hidden');
    document.getElementById('scanBtn').disabled = true;
    document.getElementById('scanBtn').textContent = '⏳ Đang phân tích...';
    document.getElementById('status').textContent = scanStatus.progress || 'Đang phân tích... (có thể mất 1-2 phút)';
}

function startPollingForResults(url) {
    // Poll every 2 seconds to check if background scan completed
    if (scanPollInterval) clearInterval(scanPollInterval);
    
    scanPollInterval = setInterval(async () => {
        const status = await chrome.runtime.sendMessage({ type: 'GET_SCAN_STATUS', url: url });
        
        if (!status || status.status === 'completed') {
            clearInterval(scanPollInterval);
            scanPollInterval = null;

            if (status && status.results) {
                currentResultsData = status.results;
                
                // Save to URL cache too
                chrome.storage.local.set({
                    [url]: { ...status.results, timestamp: new Date().toISOString(), url: url }
                });

                document.getElementById('scanBtn').disabled = false;
                document.getElementById('scanBtn').textContent = '🚀 QUÉT TRANG NÀY';
                document.getElementById('status').textContent = 'Phân tích hoàn tất';
                renderResults(status.results, url);
                // Refresh usage dashboard after scan
                loadUsageDashboard();
            } else {
                // Check URL cache
                chrome.storage.local.get([url], (result) => {
                    if (result[url]) {
                        currentResultsData = result[url];
                        document.getElementById('scanBtn').disabled = false;
                        document.getElementById('scanBtn').textContent = '🚀 QUÉT TRANG NÀY';
                        renderResults(result[url], url);
                        loadUsageDashboard();
                    }
                });
            }
        } else if (status.status === 'error') {
            clearInterval(scanPollInterval);
            scanPollInterval = null;
            document.getElementById('scanBtn').disabled = false;
            document.getElementById('scanBtn').textContent = '🚀 QUÉT TRANG NÀY';
            showError(status.error || 'Phân tích thất bại');
        } else if (status.status === 'scanning') {
            document.getElementById('status').textContent = status.progress || 'Đang phân tích...';

            // Update streaming progress bar if available (V7)
            if (status.stream_modules && Object.keys(status.stream_modules).length > 0) {
                const count = Object.keys(status.stream_modules).length;
                updateStreamProgress(count, status.stream_modules);
            }
        }
    }, 2000);
}

// ============================================================================
// SCAN BUTTON HANDLER WITH CONFIRMATION
// ============================================================================

let scannedDataCache = null;

document.getElementById('scanBtn').addEventListener('click', async () => {
    const btn = document.getElementById('scanBtn');
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

    if (!tab) return;

    btn.disabled = true;
    btn.textContent = '⏳ Đang thu thập...';

    try {
        console.log(`📍 Scanning: ${tab.url}`);

        // Scrape content — use structured scraper (ARCH-01)
        const scrapeResult = await chrome.scripting.executeScript({
            target: { tabId: tab.id },
            func: structuredScrapePageContent
        });

        if (!scrapeResult || !scrapeResult[0] || !scrapeResult[0].result) {
            throw new Error("Không thể thu thập nội dung");
        }

        const scrapedData = scrapeResult[0].result;
        
        // Support both structured (_is_structured) and legacy flat format
        const textLength = scrapedData._is_structured
            ? (scrapedData.article?.body?.length || 0)
            : (scrapedData.text?.length || 0);
        const commentsCount = scrapedData._is_structured
            ? (scrapedData.comments?.length || 0)
            : (scrapedData.comments?.length || 0);

        console.log(`📊 Scraped Data (${scrapedData._is_structured ? 'structured' : 'flat'}):`, {
            textLength, commentsCount,
            pageType: scrapedData.page_type || 'unknown'
        });
        
        if (textLength < 20 && !(scrapedData.text?.length > 20)) {
            throw new Error("Không tìm thấy nội dung — trang có thể đang tải hoặc trống");
        }

        console.log(`✂️ Scraped: text=${textLength} chars, ${commentsCount} comments`);

        // Store for confirmation
        scannedDataCache = scrapedData;
        currentTabUrl = tab.url;

        // Show confirmation
        showConfirmation(tab.url, scrapedData);

    } catch (err) {
        console.error("Error:", err.message);
        showError(err.message);
    } finally {
        btn.disabled = false;
        btn.textContent = '🚀 QUÉT TRANG NÀY';
    }
});

// ============================================================================
// CONFIRMATION HANDLER
// ============================================================================

function showConfirmation(url, data) {
    document.getElementById('results').classList.add('hidden');
    document.getElementById('errorBox').classList.add('hidden');
    document.getElementById('confirmation').classList.remove('hidden');

    // Show URL
    document.getElementById('confirmUrl').textContent = url;

    // Support structured and flat data
    const previewText = data._is_structured
        ? (data.article?.title || data.article?.body || data.text || '')
        : (data.text || '');
    const commentCount = data._is_structured
        ? (data.comments?.length || 0)
        : (data.comments?.length || 0);

    // Show preview
    const preview = previewText.substring(0, 200).replace(/\n\n/g, ' ').trim();
    document.getElementById('confirmPreview').textContent = preview + (previewText.length > 200 ? '...' : '');

    // Show comment count + page type badge
    const pageType = data.page_type || '';
    const pageLabel = pageType === 'facebook_post' ? ' (Facebook)' :
                      pageType === 'news_article' ? ' (Báo)' :
                      pageType === 'youtube_video' ? ' (YouTube)' :
                      pageType === 'tiktok' ? ' (TikTok)' : '';
    document.getElementById('confirmComments').textContent = `${commentCount}${pageLabel}`;
}

document.getElementById('confirmYes').addEventListener('click', async () => {
    if (!scannedDataCache || !currentTabUrl) return;

    const btn = document.getElementById('confirmYes');
    btn.disabled = true;
    btn.textContent = '⏳ Đang gửi...';

    try {
        // Delegate to background service worker
        // ARCH-01: Use unified endpoint when structured data is available
        const [activeTab] = await chrome.tabs.query({ active: true, currentWindow: true });
        const pageTitle = activeTab?.title || '';

        let response;

        if (scannedDataCache._is_structured) {
            // ARCH-01: Send structured data to /analyze/V7/unified (1 Gemini call)
            response = await chrome.runtime.sendMessage({
                type: 'START_SCAN_UNIFIED',
                data: {
                    structured: scannedDataCache,
                    url: currentTabUrl,
                    // Also include flat format for fallback
                    article_text: scannedDataCache.text || scannedDataCache.article?.body || '',
                    comments: scannedDataCache._flat_comments || scannedDataCache.comments?.map(c => c.text) || [],
                    pageTitle: pageTitle,
                }
            });
        } else {
            // Legacy flat format → streaming endpoint
            response = await chrome.runtime.sendMessage({
                type: 'START_SCAN_STREAM',
                data: {
                    url: currentTabUrl,
                    article_text: scannedDataCache.text,
                    comments: scannedDataCache.comments,
                    pageTitle: pageTitle
                }
            });
        }

        if (response && response.status === 'started') {
            console.log("✅ Scan delegated to background service worker");

            // Hide confirmation, show streaming progress — NO partial results until AI finishes
            document.getElementById('confirmation').classList.add('hidden');
            document.getElementById('results').classList.add('hidden');
            document.getElementById('scanBtn').disabled = true;
            document.getElementById('scanBtn').textContent = '⏳ Đang phân tích...';
            document.getElementById('status').textContent = 'Đang kết nối máy chủ... (có thể đóng popup)';
            // Show streaming progress bar
            document.getElementById('streamProgress').classList.remove('hidden');
            updateStreamProgress(0, {});

            // Start polling for results
            startPollingForResults(currentTabUrl);
        } else {
            throw new Error("Failed to start background scan");
        }

    } catch (err) {
        console.error("Error:", err.message);
        showError(err.message);
    } finally {
        btn.disabled = false;
        btn.textContent = '✅ Quét';
    }
});

document.getElementById('confirmNo').addEventListener('click', () => {
    scannedDataCache = null;
    document.getElementById('confirmation').classList.add('hidden');
});

// ============================================================================
// ERROR HANDLING
// ============================================================================

function showError(msg) {
    const errorBox = document.getElementById('errorBox');
    const errorMessage = document.getElementById('errorMessage');

    if (msg.includes('Failed to fetch') || msg.includes('NetworkError')) {
        errorMessage.textContent = 'Không thể kết nối máy chủ. Vui lòng thử lại sau.';
    } else {
        errorMessage.textContent = msg;
    }

    document.getElementById('results').classList.add('hidden');
    errorBox.classList.remove('hidden');
}

document.getElementById('retryBtn').addEventListener('click', () => {
    document.getElementById('scanBtn').click();
});

// ============================================================================
// CONTENT SCRAPER - Advanced Element Detection with Dynamic Content Handling
// ============================================================================

function scrapePageContent() {
    let text = "";
    let comments = [];
    const hostname = location.hostname;

    try {
        // Facebook - Comprehensive element detection
        if (hostname.includes('facebook.com')) {
            let postContainer = null;
            let postContent = "";

            // ===== STRATEGY 1: Find main post container =====
            const articleElements = document.querySelectorAll('div[role="article"]');
            
            if (articleElements.length > 0) {
                // Filter articles - exclude sidebars, ads, suggestions
                const validArticles = Array.from(articleElements).filter(el => {
                    const style = window.getComputedStyle(el);
                    const isHidden = style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0';
                    const isSmall = el.offsetWidth < 200 || el.offsetHeight < 100;
                    const isAd = el.innerText.toLowerCase().includes('sponsored') || 
                                 el.innerText.toLowerCase().includes('ad') ||
                                 el.innerText.toLowerCase().includes('quảng cáo');
                    return !isHidden && !isSmall && !isAd && el.innerText.length > 50;
                });

                if (validArticles.length === 1) {
                    postContainer = validArticles[0];
                } else if (validArticles.length > 1) {
                    postContainer = validArticles.reduce((max, el) => 
                        el.innerText.length > max.innerText.length ? el : max
                    );
                }
            }

            // ===== STRATEGY 2: Direct post content extraction =====
            if (postContainer) {
                const header = postContainer.querySelector('[data-testid="post_header"]') ||
                               postContainer.querySelector('div[class*="post_header"]');
                if (header && header.innerText.trim()) {
                    postContent += "TITLE: " + header.innerText.trim() + "\n\n";
                }

                const postMessage = postContainer.querySelector('[data-testid="post_message"]') ||
                                   postContainer.querySelector('div[data-testid="story"]');
                if (postMessage && postMessage.innerText.trim()) {
                    postContent += "CONTENT: " + postMessage.innerText.trim() + "\n\n";
                }

                // Extract all text content from post (excluding UI elements)
                if (!postContent || postContent.length < 30) {
                    let allText = "";
                    const walker = document.createTreeWalker(
                        postContainer,
                        NodeFilter.SHOW_TEXT,
                        null,
                        false
                    );

                    let node;
                    while (node = walker.nextNode()) {
                        const text = node.textContent.trim();
                        if (text.length > 3 && 
                            !text.match(/^(Like|Love|Haha|Wow|Sad|Angry|Reply|Share|Comment|More|Hide|Delete|Edit|...|View more|Show more|Thích|Yêu|Buồn|Tức giận|Trả lời|Chia sẻ|Bình luận|Xem thêm|Ẩn|Xóa|Chỉnh sửa)$/i) &&
                            !text.match(/^[👍❤️😂😮😢😠🔥\s]*$/) &&
                            !text.match(/^\d+\s*(giờ|phút|ngày|tuần|tháng)$/) &&
                            !text.match(/^(ago|yesterday|today|h|m|d|w|mo)$/i)) {
                            allText += text + " ";
                        }
                    }
                    if (allText.trim().length > 30) {
                        postContent = allText.trim();
                    }
                }

                text = postContent.substring(0, 5000).trim();
            }

            // ===== STRATEGY 3: Fallback to main content area =====
            if (!text || text.length < 30) {
                const main = document.querySelector('main') || 
                            document.querySelector('[role="main"]') ||
                            document.querySelector('[role="region"]');
                if (main) {
                    const centerCol = main.querySelector('[style*="max-width"]') || 
                                     main.querySelector('div > div > div:nth-child(2)') ||
                                     main;
                    
                    if (centerCol) {
                        const content = centerCol.innerText.substring(0, 5000).trim();
                        if (content.length > 30) {
                            text = content;
                        }
                    }
                }
            }

            // ===== EXTRACT COMMENTS - Smart Detection =====
            const commentSet = new Set();

            // Strategy 1: Official Facebook comment elements with data-testid
            const commentElements1 = document.querySelectorAll('[data-testid="comment"]');
            commentElements1.forEach(el => {
                const commentText = el.innerText || el.textContent;
                if (commentText && commentText.length > 5 && commentText.length < 1000) {
                    commentSet.add(commentText.trim());
                }
            });

            // Strategy 2: Comment text containers
            const commentElements2 = document.querySelectorAll('[data-testid="comment_text"]');
            commentElements2.forEach(el => {
                const commentText = el.innerText || el.textContent;
                if (commentText && commentText.length > 5 && commentText.length < 1000) {
                    commentSet.add(commentText.trim());
                }
            });

            // Strategy 3: Look for comment bodies by structural analysis
            // Facebook comments are usually in xattr-like divs with specific structure
            const commentBodies = document.querySelectorAll('div[class*="comment"][class*="body"], div[class*="x1ey2e3e"]');
            commentBodies.forEach(el => {
                const txt = el.innerText;
                if (txt && txt.length > 5 && txt.length < 1000) {
                    const trimmed = txt.trim();
                    if (!trimmed.match(/^(Like|Love|Haha|Wow|Sad|Angry|Reply|Share|Comment|More|More|👍|❤️|😂|😮|😢|😠|🔥|Thích|Yêu|Buồn|Tức giận|Trả lời|Chia sẻ|Bình luận)$/i)) {
                        commentSet.add(trimmed);
                    }
                }
            });

            // Strategy 4: Paragraph elements within comment containers (more careful filtering)
            const allArticleElements = document.querySelectorAll('div[role="article"]');
            let postOffset = 0;
            if (postContainer) {
                postOffset = Array.from(allArticleElements).indexOf(postContainer);
            }
            
            Array.from(allArticleElements).forEach((el, idx) => {
                // Skip the main post container itself
                if (el === postContainer || idx <= postOffset) return;
                
                const txt = el.innerText;
                if (txt && txt.length > 5 && txt.length < 500) {
                    const trimmed = txt.trim();
                    // Stricter filtering for UI elements
                    if (!trimmed.match(/^(Like|Love|Haha|Wow|Sad|Angry|Reply|Share|Comment|More|Delete|Edit|...|View more|More|Thích|Yêu|Buồn|Tức giận|Trả lời|Chia sẻ|Bình luận|Xem thêm|Ẩn|Xóa|Chỉnh sửa|👍|❤️|😂|😮|😢|😠|🔥)$/i) &&
                        !trimmed.match(/^\d+\s*(minute|hour|day|week|month|giờ|phút|ngày|tuần|tháng).*ago$/i) &&
                        !trimmed.match(/^[👍❤️😂😮😢😠🔥\s]{1,5}$/) &&
                        !commentSet.has(trimmed)) {
                        commentSet.add(trimmed);
                    }
                }
            });

            comments = Array.from(commentSet).slice(0, 100);
        }
        // VnExpress, DanTri, TuoiTre - News sites with DYNAMIC COMMENTS
        else if (hostname.includes('vnexpress') || hostname.includes('dantri') || hostname.includes('tuoitre')) {
            // ===== EXTRACT ARTICLE CONTENT =====
            const articleSelectors = [
                'article',
                'div.article-content',
                'div.article-body',
                'div[data-type="article_content"]',
                'div.main-content',
                'div.detail-content',
                'main'
            ];

            let articleElement = null;
            for (let selector of articleSelectors) {
                articleElement = document.querySelector(selector);
                if (articleElement && articleElement.innerText.length > 100) {
                    break;
                }
            }

            if (articleElement) {
                const title = articleElement.querySelector('h1, .article-title, [data-type="title"]');
                if (title && title.innerText.trim()) {
                    text += "TITLE: " + title.innerText.trim() + "\n\n";
                }

                const paragraphs = articleElement.querySelectorAll('p');
                let contentText = "";
                paragraphs.forEach(p => {
                    const pText = p.innerText.trim();
                    if (pText.length > 10) {
                        contentText += pText + " ";
                    }
                });
                if (contentText.length > 50) {
                    text += "CONTENT: " + contentText.substring(0, 3000) + "\n\n";
                }
            }

            if (text.length < 50) {
                const paragraphs = document.querySelectorAll('p');
                text = Array.from(paragraphs)
                    .map(p => p.innerText.trim())
                    .filter(t => t.length > 10)
                    .join('\n')
                    .substring(0, 5000);
            }

            // ===== EXTRACT COMMENTS - Site-specific selectors =====
            const commentSet = new Set();

            // Helper: clean comment text, remove UI noise
            const cleanComment = (raw) => {
                if (!raw) return '';
                return raw
                    .replace(/\n+/g, ' ')
                    .replace(/\s{2,}/g, ' ')
                    .replace(/^(Thích|Like|Reply|Trả lời|Chia sẻ|Share|Xem thêm|Tặng sao|Xem tất cả.*trả lời)\s*/gi, '')
                    .replace(/(Thích|Like|Reply|Trả lời|Chia sẻ|Share|Tặng sao)\s*$/gi, '')
                    .trim();
            };
            const isValidComment = (txt) => {
                if (!txt || txt.length < 8 || txt.length > 2000) return false;
                if (txt.match(/^(Like|Reply|Share|Delete|Edit|Thích|Trả lời|Chia sẻ|Xóa|Chỉnh sửa|Xem thêm|Tặng sao|Xem tất cả.*trả lời|Vui|Buồn|Ngạc nhiên|Phẫn nộ)$/i)) return false;
                if (txt.match(/^\d+\s*(giờ|phút|ngày|tuần|tháng|hour|minute|day|week|h trước|giờ trước|phút trước)$/i)) return false;
                if (txt.match(/^[👍❤️😂😮😢😠🔥\s]+$/)) return false;
                if (txt.match(/^\d+h?\s*trước$/i)) return false;
                return true;
            };

            // ===== VNEXPRESS =====
            if (hostname.includes('vnexpress')) {
                // Primary: p.full_content inside div.content-comment (exact VnExpress structure)
                document.querySelectorAll('div.content-comment p.full_content').forEach(el => {
                    const txt = cleanComment(el.innerText || el.textContent);
                    if (isValidComment(txt) && !commentSet.has(txt)) commentSet.add(txt);
                });

                // Also try: comment_item containers
                if (commentSet.size === 0) {
                    document.querySelectorAll('.comment_item').forEach(item => {
                        const contentEl = item.querySelector('.content-comment') || item.querySelector('p.full_content');
                        if (contentEl) {
                            const txt = cleanComment(contentEl.innerText || contentEl.textContent);
                            if (isValidComment(txt) && !commentSet.has(txt)) commentSet.add(txt);
                        }
                    });
                }

                // Fallback: comment box containers
                if (commentSet.size === 0) {
                    const commentBox = document.getElementById('box_comment_app_inner') ||
                                      document.getElementById('box_comment_vne') ||
                                      document.querySelector('[data-component-type="comment_library"]') ||
                                      document.querySelector('[data-component-function="showComment"]');
                    if (commentBox) {
                        commentBox.querySelectorAll('[data-comment-id], [class*="comment"]').forEach(item => {
                            const txt = cleanComment(item.innerText || item.textContent);
                            if (isValidComment(txt) && !commentSet.has(txt)) commentSet.add(txt);
                        });
                    }
                }
            }

            // ===== DANTRI =====
            else if (hostname.includes('dantri')) {
                // Primary: div.comment-text inside div.comment-item (exact DanTri structure)
                document.querySelectorAll('div.comment-item div.comment-text').forEach(el => {
                    const txt = cleanComment(el.innerText || el.textContent);
                    if (isValidComment(txt) && !commentSet.has(txt)) commentSet.add(txt);
                });

                // Also try: comment-content containers
                if (commentSet.size === 0) {
                    document.querySelectorAll('div.comment-item div.comment-content').forEach(item => {
                        const textEl = item.querySelector('.comment-text');
                        if (textEl) {
                            const txt = cleanComment(textEl.innerText || textEl.textContent);
                            if (isValidComment(txt) && !commentSet.has(txt)) commentSet.add(txt);
                        } else {
                            // Get text directly, skip author/time
                            const authorEl = item.querySelector('.comment-author');
                            const timeEl = item.querySelector('.comment-time');
                            let raw = item.innerText || '';
                            if (authorEl) raw = raw.replace(authorEl.innerText, '');
                            if (timeEl) raw = raw.replace(timeEl.innerText, '');
                            const txt = cleanComment(raw);
                            if (isValidComment(txt) && !commentSet.has(txt)) commentSet.add(txt);
                        }
                    });
                }

                // Fallback: broader comment selectors
                if (commentSet.size === 0) {
                    document.querySelectorAll('.comment-content, [class*="cmt_content"]').forEach(el => {
                        const txt = cleanComment(el.innerText || el.textContent);
                        if (isValidComment(txt) && !commentSet.has(txt)) commentSet.add(txt);
                    });
                }
            }

            // ===== TUOITRE =====
            else if (hostname.includes('tuoitre')) {
                // Primary: span.contentcomment inside div.maincmt (exact TuoiTre structure)
                document.querySelectorAll('div.maincmt span.contentcomment').forEach(el => {
                    // TuoiTre uses span.remain for truncated content, combine with visible text
                    const visibleText = el.querySelector('.remain')
                        ? (el.textContent || '').replace(/\+$/, '').trim()
                        : (el.innerText || el.textContent || '').trim();
                    const txt = cleanComment(visibleText);
                    if (isValidComment(txt) && !commentSet.has(txt)) commentSet.add(txt);
                });

                // Also try: direct maincmt containers
                if (commentSet.size === 0) {
                    document.querySelectorAll('div.maincmt').forEach(item => {
                        const contentEl = item.querySelector('span.contentcomment') || item.querySelector('.minimize');
                        if (contentEl) {
                            const txt = cleanComment(contentEl.innerText || contentEl.textContent);
                            if (isValidComment(txt) && !commentSet.has(txt)) commentSet.add(txt);
                        }
                    });
                }

                // Fallback: broader selectors for tuoitre
                if (commentSet.size === 0) {
                    document.querySelectorAll('[class*="cmt"], [class*="comment"]').forEach(el => {
                        const txt = cleanComment(el.innerText || el.textContent);
                        if (isValidComment(txt) && !commentSet.has(txt)) commentSet.add(txt);
                    });
                }
            }

            // ===== GENERIC FALLBACK for other news sites =====
            if (commentSet.size === 0) {
                const genericSelectors = [
                    '.comment-content', '.comment-text', '.comment-item',
                    '.comments', '[data-component="comment"]', '.user-comment',
                    '[class*="cmt_content"]', '[class*="comment-body"]',
                    '[data-comment-id]'
                ];
                genericSelectors.forEach(selector => {
                    document.querySelectorAll(selector).forEach(el => {
                        const txt = cleanComment(el.innerText || el.textContent);
                        if (isValidComment(txt) && !commentSet.has(txt)) commentSet.add(txt);
                    });
                });
            }

            comments = Array.from(commentSet).slice(0, 100);
        }
        // Generic/Other sites
        else {
            const main = document.querySelector('main') || 
                        document.querySelector('article') || 
                        document.querySelector('[role="main"]') ||
                        document.querySelector('[role="article"]');
            
            if (main) {
                const title = main.querySelector('h1, h2, [role="heading"]');
                if (title && title.innerText.trim()) {
                    text += "TITLE: " + title.innerText.trim() + "\n\n";
                }

                const content = main.innerText.substring(0, 5000).trim();
                if (content.length > 50) {
                    text += "CONTENT: " + content + "\n";
                }
            }

            if (text.length < 50) {
                text = document.body.innerText.substring(0, 5000).trim();
            }

            const commentSelectors = ['.comment', '.comments', '.reply', '.discussion', '[data-comment]'];
            const commentSet = new Set();
            
            commentSelectors.forEach(selector => {
                document.querySelectorAll(selector).forEach(el => {
                    const commentText = el.innerText;
                    if (commentText && commentText.length > 10 && commentText.length < 500) {
                        const trimmed = commentText.trim();
                        if (!trimmed.match(/^(Like|Reply|Share|Edit|Delete)$/i) && !commentSet.has(trimmed)) {
                            commentSet.add(trimmed);
                        }
                    }
                });
            });

            comments = Array.from(commentSet).slice(0, 100);
        }

        // ===== FINAL CLEANUP =====
        comments = [...new Set(comments)]
            .filter(c => c && c.length > 0)
            .slice(0, 50);

        text = text.trim().substring(0, 10000);

        if (!text || text.length < 20) {
            text = document.body.innerText.substring(0, 5000).trim();
        }

        return { text, comments };
    } catch (err) {
        console.error("Scraper error:", err);
        return { text: document.body.innerText.substring(0, 5000), comments: [] };
    }
}

// ============================================================================
// ARCH-01: Structured Scraper — returns rich JSON for unified analysis
// Self-contained: runs inside chrome.scripting.executeScript
// ============================================================================

function structuredScrapePageContent() {
    const hostname = location.hostname;
    const domain = hostname.replace(/^www\./, '');

    // ── Helpers ────────────────────────────────────────────────────────────
    const cleanText = (raw) => {
        if (!raw) return '';
        return raw.trim()
            .replace(/\s+/g, ' ')
            .replace(/(\n\s*)+/g, '\n');
    };

    const detectPageType = () => {
        if (hostname.includes('facebook.com')) return 'facebook_post';
        if (hostname.includes('youtube.com')) return 'youtube_video';
        if (hostname.includes('tiktok.com')) return 'tiktok';
        if (/vnexpress|dantri|tuoitre|thanhnien|24h|vietnamnet|vov|vtc|zingnews|kenh14/.test(hostname)) return 'news_article';
        return 'generic';
    };

    const pageType = detectPageType();

    // ── Article extraction ─────────────────────────────────────────────────
    let articleTitle = '';
    let articleAuthor = '';
    let articleDate = '';
    let articleBody = '';

    try {
        if (pageType === 'facebook_post') {
            // Title: first meaningful line of post
            const postEl = document.querySelector('[data-testid="post_message"]') ||
                           document.querySelector('[data-ad-comet-preview="message"]') ||
                           document.querySelector('div[dir="auto"]');
            if (postEl) articleBody = cleanText(postEl.innerText).substring(0, 3000);

            // Author: page/profile name
            const authorEl = document.querySelector('a[href*="profile"] strong') ||
                             document.querySelector('h3[class*="actor"] a') ||
                             document.querySelector('[data-testid="actor-name"]') ||
                             document.querySelector('strong[class*="x1q0g3bu"]');
            if (authorEl) articleAuthor = cleanText(authorEl.innerText);

            // Date: aria-label on time element
            const timeEl = document.querySelector('abbr[data-utime], time[datetime], a[role="link"] > span > span[aria-hidden]');
            if (timeEl) articleDate = timeEl.getAttribute('datetime') || timeEl.getAttribute('data-utime') || timeEl.innerText;

            articleTitle = articleAuthor ? `${articleAuthor}: ${articleBody.substring(0, 80)}` : articleBody.substring(0, 80);

        } else if (pageType === 'news_article') {
            // Title
            const titleEl = document.querySelector('h1.title-detail, h1.article-title, h1[class*="title"], h1');
            if (titleEl) articleTitle = cleanText(titleEl.innerText);

            // Author byline
            const authorEl = document.querySelector(
                '.author-name, .byline, .article-author, [class*="author"], [rel="author"], .reporter-name, .txt_author, .article_author'
            );
            if (authorEl) articleAuthor = cleanText(authorEl.innerText).substring(0, 100);

            // Date
            const dateEl = document.querySelector('time[datetime], time[pubdate], .PublishDate, .datePublished, .article-date, [class*="date"], meta[property="article:published_time"]');
            if (dateEl) articleDate = dateEl.getAttribute('datetime') || dateEl.getAttribute('content') || cleanText(dateEl.innerText);

            // Body: try article selectors then fall back to paragraphs
            const bodyEl = document.querySelector(
                'article, .article-body, .content-detail, [class*="article-content"], [class*="news-content"], .fck_detail, .detail-content, main'
            );
            if (bodyEl) {
                articleBody = Array.from(bodyEl.querySelectorAll('p'))
                    .map(p => cleanText(p.innerText))
                    .filter(t => t.length > 20)
                    .join('\n').substring(0, 3000);
            }
            if (!articleBody) {
                articleBody = cleanText(document.body.innerText).substring(0, 3000);
            }

        } else if (pageType === 'youtube_video') {
            // ── YouTube Watch Page ──────────────────────────────────────
            // Title
            const titleEl = document.querySelector(
                'h1.ytd-watch-metadata yt-formatted-string, #title h1 yt-formatted-string, ytd-watch-metadata h1'
            );
            if (titleEl) articleTitle = cleanText(titleEl.innerText);

            // Channel name
            const channelEl = document.querySelector(
                'ytd-channel-name yt-formatted-string a, #channel-name a, #upload-info #channel-name a'
            );
            if (channelEl) articleAuthor = cleanText(channelEl.innerText);

            // Upload date
            const dateEl = document.querySelector(
                'ytd-video-primary-info-renderer #info yt-formatted-string.bold, ytd-watch-info-text #info yt-formatted-string'
            );
            if (dateEl) articleDate = cleanText(dateEl.innerText);

            // Description
            const descEl = document.querySelector(
                'ytd-text-inline-expander yt-attributed-string, ytd-expander #content yt-formatted-string, #description-inner yt-attributed-string'
            );
            if (descEl) articleBody = cleanText(descEl.innerText).substring(0, 3000);
            if (!articleBody) {
                // Fallback via meta tag
                const metaEl = document.querySelector('meta[name="description"]');
                if (metaEl) articleBody = metaEl.getAttribute('content') || '';
            }

        } else if (pageType === 'tiktok') {
            // ── TikTok Video Page ──────────────────────────────────────
            // Video description / title
            const descEl = document.querySelector(
                '[data-e2e="browse-video-desc"], [data-e2e="video-desc"], [class*="video-meta-title"]'
            );
            if (descEl) {
                articleBody = cleanText(descEl.innerText).substring(0, 2000);
                articleTitle = articleBody.substring(0, 100);
            }

            // Channel / author
            const authorEl = document.querySelector(
                '[data-e2e="browse-video-author-title"], [data-e2e="video-author-uniqueid"], h3[class*="AuthorTitle"]'
            );
            if (authorEl) articleAuthor = cleanText(authorEl.innerText);

            // Timestamp
            const timeEl = document.querySelector(
                '[data-e2e="browser-nickname-create-time"], span[class*="create-time"]'
            );
            if (timeEl) articleDate = cleanText(timeEl.innerText);

            // Meta description fallback
            if (!articleBody) {
                const metaEl = document.querySelector('meta[name="description"], meta[property="og:description"]');
                if (metaEl) articleBody = metaEl.getAttribute('content') || '';
            }

        } else {

            const metaDesc = document.querySelector('meta[name="description"], meta[property="og:description"]');
            if (metaDesc) articleBody = metaDesc.getAttribute('content') || '';
            if (!articleBody) articleBody = cleanText(document.body.innerText).substring(0, 3000);
        }
    } catch (e) {
        articleBody = cleanText(document.body.innerText).substring(0, 3000);
    }

    // ── Reactions & shares (Facebook) ──────────────────────────────────────
    let reactionsTotal = 0;
    let shares = 0;

    try {
        if (pageType === 'facebook_post') {
            // Reactions
            const reactionEl = document.querySelector('[aria-label*="reaction"], [data-testid="ufi_reaction_count"] > span');
            if (reactionEl) {
                const num = reactionEl.getAttribute('aria-label') || reactionEl.innerText;
                const match = num.match(/[\d,]+/);
                if (match) reactionsTotal = parseInt(match[0].replace(/,/g, ''), 10);
            }

            // Shares
            const shareEls = document.querySelectorAll('div[role="button"]');
            shareEls.forEach(el => {
                const txt = el.innerText || '';
                if (/^\d[\d,\.Kk]* (share|lượt chia sẻ)/i.test(txt)) {
                    const m = txt.match(/[\d,\.]+/);
                    if (m) shares = parseFloat(m[0].replace(/,/g, ''));
                }
            });
        } else if (pageType === 'youtube_video') {
            // Like count
            const likeEl = document.querySelector(
                'ytd-toggle-button-renderer[is-icon-button] #text, yt-formatted-string#text.ytd-toggle-button-renderer'
            );
            if (likeEl) {
                const m = likeEl.innerText.replace(/[,. ]/g, '').match(/\d+/);
                if (m) reactionsTotal = parseInt(m[0], 10);
            }

            // View count → use as shares proxy (for metadata richness)
            const viewEl = document.querySelector(
                'ytd-watch-info-text span.bold, .view-count, ytd-video-view-count-renderer'
            );
            if (viewEl) {
                const m = viewEl.innerText.replace(/[,. lượt xem views]/gi, '').match(/\d+/);
                if (m) shares = parseInt(m[0], 10);
            }

        } else if (pageType === 'tiktok') {
            // Likes
            const likeEl = document.querySelector(
                '[data-e2e="browse-like-count"], [data-e2e="like-count"], [class*="like-count"]'
            );
            if (likeEl) {
                const raw = (likeEl.innerText || '').trim();
                if (/k/i.test(raw)) reactionsTotal = Math.round(parseFloat(raw) * 1000);
                else if (/m/i.test(raw)) reactionsTotal = Math.round(parseFloat(raw) * 1_000_000);
                else { const m = raw.match(/[\d,.]+/); if (m) reactionsTotal = parseInt(m[0].replace(/,/g, ''), 10); }
            }

            // Shares
            const shareEl = document.querySelector(
                '[data-e2e="browse-share-count"], [data-e2e="share-count"], [class*="share-count"]'
            );
            if (shareEl) {
                const raw = (shareEl.innerText || '').trim();
                if (/k/i.test(raw)) shares = Math.round(parseFloat(raw) * 1000);
                else if (/m/i.test(raw)) shares = Math.round(parseFloat(raw) * 1_000_000);
                else { const m = raw.match(/[\d,.]+/); if (m) shares = parseInt(m[0].replace(/,/g, ''), 10); }
            }

        } else if (pageType === 'news_article') {
            const newsShareEl = document.querySelector(
                '[class*="share-count"], [class*="shareCount"], .share-count, .txt_share'
            );
            if (newsShareEl) {
                const m = newsShareEl.innerText.match(/[\d,]+/);
                if (m) shares = parseInt(m[0].replace(/,/g, ''), 10);
            }
        }
    } catch (e) { /* ignore */ }

    // ── Comments extraction (structured) ──────────────────────────────────
    const structuredComments = [];
    const seenTexts = new Set();

    try {
        if (pageType === 'facebook_post') {
            // Comment containers: each [data-testid="comment"] or ul[class*="comment"]
            const commentContainers = document.querySelectorAll(
                '[aria-label*="Comment"], [data-testid="comment"], div[class*="Comment"]'
            );

            commentContainers.forEach((container) => {
                // Author
                const authorEl = container.querySelector('a[href*="profile"] strong, a[href*="/"] > span[class*="x1q0g3bu"]');
                const author = authorEl ? cleanText(authorEl.innerText) : '';

                // Text
                const textEl = container.querySelector('[data-testid="comment_text"] > span, div[dir="auto"] > span');
                const text = textEl ? cleanText(textEl.innerText) : cleanText(container.innerText);
                if (!text || text.length < 3 || text.length > 500) return;
                if (seenTexts.has(text)) return;
                seenTexts.add(text);

                // Reactions on comment
                let reactions = 0;
                const reactionEl = container.querySelector('[aria-label*="reaction"], span[class*="reaction"]');
                if (reactionEl) {
                    const m = (reactionEl.getAttribute('aria-label') || reactionEl.innerText).match(/[\d,]+/);
                    if (m) reactions = parseInt(m[0].replace(/,/g, ''), 10);
                }

                // Is reply? (nested inside another comment)
                const isReply = container.closest('[data-testid="comment"]') !== container;

                structuredComments.push({ text, author, reactions, is_reply: isReply, timestamp: '' });
            });

            // Fallback: grab texts from [data-testid="comment_text"]
            if (structuredComments.length === 0) {
                document.querySelectorAll('[data-testid="comment_text"] span, [data-ad-comet-preview="comment_body"] span').forEach(el => {
                    const text = cleanText(el.innerText);
                    if (!text || text.length < 3 || text.length > 500) return;
                    if (seenTexts.has(text)) return;
                    seenTexts.add(text);
                    structuredComments.push({ text, author: '', reactions: 0, is_reply: false, timestamp: '' });
                });
            }

        } else if (pageType === 'news_article') {
            // VnExpress, DanTri, TuoiTre comment schemas
            const selectors = [
                '.comment-item .content-comment p',
                '.comment-item .comment_body',
                '.comment_pos .comment_text',
                '.comment-content .txt-content',
                '.cmt-item .nd_body',
                '[class*="comment"] p',
                'li.comment span.comment-text',
            ];

            for (const sel of selectors) {
                const els = document.querySelectorAll(sel);
                if (els.length > 0) {
                    els.forEach(el => {
                        const text = cleanText(el.innerText);
                        if (!text || text.length < 3 || text.length > 500) return;
                        if (seenTexts.has(text)) return;
                        seenTexts.add(text);

                        // Try to get author from parent
                        const container = el.closest('li, div[class*="comment"]');
                        const authorEl = container ? container.querySelector('[class*="author"], [class*="user"], .fullname, b') : null;
                        const author = authorEl ? cleanText(authorEl.innerText) : '';

                        // Likes on comment
                        let reactions = 0;
                        if (container) {
                            const likeEl = container.querySelector('[class*="like"], [class*="vote"]');
                            if (likeEl) {
                                const m = likeEl.innerText.match(/\d+/);
                                if (m) reactions = parseInt(m[0], 10);
                            }
                        }
                        structuredComments.push({ text, author, reactions, is_reply: false, timestamp: '' });
                    });
                    break; // Found a working selector
                }
            }
        } else if (pageType === 'youtube_video') {
            // ── YouTube Comments ──────────────────────────────────────
            // Selectors work once comments section scrolled into view
            const commentEls = document.querySelectorAll(
                'ytd-comment-renderer #content-text, ytd-comment-view-model #content-text'
            );
            commentEls.forEach(el => {
                const text = cleanText(el.innerText);
                if (!text || text.length < 3 || text.length > 500) return;
                if (seenTexts.has(text)) return;
                seenTexts.add(text);

                // Author
                const container = el.closest('ytd-comment-renderer, ytd-comment-view-model');
                const authorEl = container?.querySelector('#author-text span, #author-text a');
                const author = authorEl ? cleanText(authorEl.innerText) : '';

                // Likes
                let reactions = 0;
                const likeEl = container?.querySelector('#vote-count-middle, span.ytd-comment-action-buttons-renderer');
                if (likeEl) {
                    const m = likeEl.innerText.match(/[\d,]+/);
                    if (m) reactions = parseInt(m[0].replace(/,/g, ''), 10);
                }

                // Is reply
                const isReply = !!el.closest('ytd-comment-replies-renderer');

                structuredComments.push({ text, author, reactions, is_reply: isReply, timestamp: '' });
            });

        } else if (pageType === 'tiktok') {
            // ── TikTok Comments ──────────────────────────────────────
            const commentEls = document.querySelectorAll(
                '[data-e2e="comment-level-1"] p, [class*="CommentItemContainer"] p[class*="comment-text"], [data-e2e="comment-level-1-item"]'
            );
            commentEls.forEach(el => {
                const text = cleanText(el.innerText);
                if (!text || text.length < 3 || text.length > 500) return;
                if (seenTexts.has(text)) return;
                seenTexts.add(text);

                // Container
                const container = el.closest('[data-e2e="comment-level-1"], [class*="CommentItemContainer"]');
                const authorEl = container?.querySelector('[data-e2e="comment-username-1"], [class*="user-name"]');
                const author = authorEl ? cleanText(authorEl.innerText) : '';

                let reactions = 0;
                const likeEl = container?.querySelector('[data-e2e="comment-like-count"], [class*="like-count"]');
                if (likeEl) {
                    const m = likeEl.innerText.match(/[\d,.KkMm]+/);
                    if (m) {
                        const raw = m[0].replace(/,/g, '');
                        if (/k/i.test(raw)) reactions = Math.round(parseFloat(raw) * 1000);
                        else if (/m/i.test(raw)) reactions = Math.round(parseFloat(raw) * 1_000_000);
                        else reactions = parseInt(raw, 10) || 0;
                    }
                }

                // Replies are nested differently in TikTok
                const isReply = el.closest('[data-e2e="comment-level-2"]') !== null;
                structuredComments.push({ text, author, reactions, is_reply: isReply, timestamp: '' });
            });

        } else {
            // Generic: any paragraph-in-comment pattern
            document.querySelectorAll('[class*="comment"] p, [id*="comment"] p').forEach(el => {
                const text = cleanText(el.innerText);
                if (!text || text.length < 3 || text.length > 500) return;
                if (seenTexts.has(text)) return;
                seenTexts.add(text);
                structuredComments.push({ text, author: '', reactions: 0, is_reply: false, timestamp: '' });
            });
        }
    } catch (e) { /* ignore comment errors */ }

    // Cap at 50 comments
    const finalComments = structuredComments.slice(0, 50);

    // ── Word count ──────────────────────────────────────────────────────────
    const wordCount = articleBody ? articleBody.split(/\s+/).filter(Boolean).length : 0;

    // ── Flat backward-compatible fallback ───────────────────────────────────
    // Old /analyze/V7 still works with this
    const flatText = [articleTitle, articleBody].filter(Boolean).join('\n').trim() || cleanText(document.body.innerText).substring(0, 5000);
    const flatComments = finalComments.map(c => c.text);

    // ── Total comment count on page ─────────────────────────────────────────
    let commentCountTotal = finalComments.length;
    try {
        if (pageType === 'youtube_video') {
            // YouTube shows comment count in #count .count-text
            const ytCountEl = document.querySelector('#count .count-text yt-formatted-string, ytd-comments-header-renderer h2 yt-formatted-string');
            if (ytCountEl) {
                const m = ytCountEl.innerText.replace(/[,. ]/g, '').match(/\d+/);
                if (m) commentCountTotal = parseInt(m[0], 10);
            }
        } else if (pageType === 'tiktok') {
            const ttCountEl = document.querySelector('[data-e2e="browse-comment-count"], [class*="comment-count"]');
            if (ttCountEl) {
                const raw = (ttCountEl.innerText || '').trim();
                if (/k/i.test(raw)) commentCountTotal = Math.round(parseFloat(raw) * 1000);
                else if (/m/i.test(raw)) commentCountTotal = Math.round(parseFloat(raw) * 1_000_000);
                else { const m = raw.match(/[\d,.]+/); if (m) commentCountTotal = parseInt(m[0].replace(/,/g, ''), 10); }
            }
        } else {
            const countEl = document.querySelector('[class*="comment-count"], [class*="comment-total"], .txt_comment_list_title');
            if (countEl) {
                const m = countEl.innerText.match(/\d+/);
                if (m) commentCountTotal = parseInt(m[0], 10);
            }
        }
    } catch (e) { /* ignore */ }

    return {
        // ── ARCH-01 structured data ──
        page_type: pageType,
        url: location.href,
        scraped_at: new Date().toISOString(),
        article: {
            title: articleTitle.substring(0, 200),
            author: articleAuthor.substring(0, 100),
            published_date: articleDate.substring(0, 50),
            body: articleBody,
            word_count: wordCount,
        },
        comments: finalComments,
        metadata: {
            domain: domain,
            comment_count_visible: finalComments.length,
            comment_count_total: commentCountTotal,
            reactions_total: reactionsTotal,
            shares: shares,
            page_language: document.documentElement.lang || 'vi',
        },
        // ── Backward-compatible flat format ──
        text: flatText,
        _flat_comments: flatComments,
        _is_structured: true,
    };
}



function renderResults(data, urlInfo) {
    // All responses from V7 endpoint include sentiment_v7 or version="7.0"
    const isV7 = !!(data.sentiment_v7 || data.version === "7.0");

    // ===== RESET ALL UI STATES FIRST =====
    document.getElementById('confirmation').classList.add('hidden');
    document.getElementById('errorBox').classList.add('hidden');
    document.getElementById('warningModal').classList.add('hidden');
    
    // Show results container
    document.getElementById('results').classList.remove('hidden');

    // Reset to analysis tab on every new render
    document.querySelectorAll('.result-tab').forEach(t => t.classList.remove('active'));
    const analysisTab = document.querySelector('.result-tab[data-tab="analysis"]');
    if (analysisTab) analysisTab.classList.add('active');
    document.getElementById('tab-analysis')?.classList.remove('hidden');
    document.getElementById('tab-summary')?.classList.add('hidden');

    if (isV7) {
        renderV7Results(data, urlInfo);
    } else {
        renderV2Results(data, urlInfo);
    }
}

function renderV7Results(data, urlInfo) {
    const sentiment = data.sentiment_v7 || { overall: "Neutral", confidence: 0, intensity: "Weak" };
    const toxicity = data.toxicity_v7 || { is_toxic: false, overall_score: 0, severity: "Low" };
    const factCheck = data.fact_check_v7 || { score: 50, verdict: "Unknown" };
    const riskScore = data.risk_score_v7 || { risk_score: 0, risk_level: "Low" };
    const comments = data.comments_analysis || { total: 0, toxic_count: 0, toxic_comments: [], details: [] };
    const articleSummary = data.article_summary || null;
    const isOffline = data.offline_mode === true;

    console.log("📊 Rendering V7 results:", { sentiment, toxicity, factCheck, riskScore, articleSummary, isOffline });

    // Hide streaming progress bar
    const streamEl = document.getElementById('streamProgress');
    if (streamEl) streamEl.classList.add('hidden');

    // Show learning indicator if AI used feedback (V7.0)
    const learningIndicator = document.getElementById('learningIndicator');
    if (learningIndicator && data.learning_applied) {
        learningIndicator.classList.remove('hidden');
        const learningCount = document.getElementById('learningCount');
        if (learningCount) learningCount.textContent = data.domain_feedback?.total || '?';
    } else if (learningIndicator) {
        learningIndicator.classList.add('hidden');
    }

    // Show blocklist warning if applicable (V7)
    const blockWarning = document.getElementById('blocklistWarning');
    if (blockWarning && data.blocklist_info && data.blocklist_info.is_blocked) {
        blockWarning.classList.remove('hidden');
        const detail = document.getElementById('blocklistDetail');
        if (detail) detail.textContent = `${data.blocklist_info.report_count || 5}+ lượt báo cáo từ cộng đồng`;
    } else if (blockWarning) {
        blockWarning.classList.add('hidden');
    }

    // feature 7.12 — Show scam prompt if AI detected scam indicators
    renderScamPrompt(data.scam_detection, urlInfo || currentTabUrl);

    // ===== 0. ARTICLE SUMMARY (V7 — AI-generated, cached) =====
    const summaryCard = document.getElementById('summaryCard');
    const summaryRaw = articleSummary?.summary || articleSummary?.text || '';
    const summaryContent = truncateSummary(summaryRaw, 5);
    if (summaryContent) {
        summaryCard.style.display = 'block';
        document.getElementById('summaryText').textContent = summaryContent;

        let methodLabel = 'Gemini AI';
        if (isOffline) methodLabel = '⚡ Chế độ nhanh';
        else if (articleSummary.method === 'cached') methodLabel = 'Đã lưu';
        else if (articleSummary.method === 'fallback') methodLabel = 'Trích xuất';

        let metaHTML = `<span class="summary-badge${isOffline ? ' offline' : ''}">${methodLabel}</span>`;
        if (articleSummary.cached) {
            metaHTML += ' <span class="summary-badge cached">⚡ Đã lưu</span>';
        }
        if (isOffline) {
            metaHTML += ' <span class="summary-badge" style="background: #e67e22;">Đang chờ AI...</span>';
        }
        document.getElementById('summaryMeta').innerHTML = metaHTML;
        document.getElementById('noSummaryMsg')?.style.setProperty('display', 'none');
    } else {
        summaryCard.style.display = 'none';
        const noSummaryEl = document.getElementById('noSummaryMsg');
        if (noSummaryEl) noSummaryEl.style.display = 'block';
    }

    // ===== 1. RISK SCORE (Overall) =====
    const riskValue = riskScore.risk_score || 0;
    const riskLevel = riskScore.risk_level || "Low";
    
    // Color based on risk level
    let riskColor = '#27ae60';  // Green for Low
    if (riskLevel === 'Medium') riskColor = '#f39c12';  // Orange
    else if (riskLevel === 'High') riskColor = '#e74c3c';  // Red
    else if (riskLevel === 'Critical') riskColor = '#c0392b';  // Dark Red

    // Vietnamese risk level labels
    const riskLevelVi = {
        'Low': 'Thấp', 'Medium': 'Trung bình', 'High': 'Cao', 'Critical': 'Nguy hiểm'
    };

    document.getElementById('riskScore').innerHTML = `<span style="color: ${riskColor}">${riskValue.toFixed(1)}/100</span>`;
    document.getElementById('riskLevel').innerHTML = `<strong style="color: white;">Rủi ro ${riskLevelVi[riskLevel] || riskLevel}</strong>`;
    
    // Risk Breakdown
    if (riskScore.breakdown) {
        const breakdown = riskScore.breakdown;
        let breakdownHTML = '<div style="margin-top: 10px; padding: 8px; background: rgba(255,255,255,0.1); border-radius: 4px;">';
        breakdownHTML += '<strong>Chi tiết rủi ro:</strong><br/>';
        breakdownHTML += `Tin giả: ${(breakdown.fake_news_component || 0).toFixed(1)} | `;
        breakdownHTML += `Độc hại: ${(breakdown.toxicity_component || 0).toFixed(1)} | `;
        breakdownHTML += `Cảm xúc: ${(breakdown.sentiment_component || 0).toFixed(1)}<br/>`;
        breakdownHTML += `Nguồn: ${(breakdown.source_component || 0).toFixed(1)} | `;
        breakdownHTML += `Thao túng: ${(breakdown.manipulation_component || 0).toFixed(1)}`;
        breakdownHTML += '</div>';
        document.getElementById('riskBreakdown').innerHTML = breakdownHTML;
    }

    // ===== 2. SENTIMENT V7 (PhoBERT) =====
    const sentLabel = sentiment.overall || "Neutral";
    const sentConf = sentiment.confidence || 0;
    const sentIntensity = sentiment.intensity || "Weak";
    const sentMethod = sentiment.method || "unknown";

    // Vietnamese sentiment labels
    const sentLabelVi = {
        'Positive': 'Tích cực', 'Negative': 'Tiêu cực', 'Neutral': 'Trung lập',
        'Mixed': 'Hỗn hợp', 'Very Positive': 'Rất tích cực', 'Very Negative': 'Rất tiêu cực'
    };
    const sentIntensityVi = {
        'Weak': 'Yếu', 'Moderate': 'Vừa', 'Strong': 'Mạnh', 'Very Strong': 'Rất mạnh'
    };

    let sentColor = '#3498db';  // Blue for Neutral
    if (sentLabel === 'Positive' || sentLabel === 'Very Positive') sentColor = '#27ae60';  // Green
    else if (sentLabel === 'Negative' || sentLabel === 'Very Negative') sentColor = '#e74c3c';  // Red
    else if (sentLabel === 'Mixed') sentColor = '#f39c12';  // Orange

    document.getElementById('sentimentStatus').innerHTML = 
        `<strong style="color: ${sentColor};">${sentLabelVi[sentLabel] || sentLabel}</strong> (độ tin cậy ${(sentConf * 100).toFixed(0)}%)`;
    
    document.getElementById('sentimentDetails').innerHTML = `
        <div style="font-size: 12px; color: var(--text-secondary);">
            <strong>Cường độ:</strong> ${sentIntensityVi[sentIntensity] || sentIntensity}<br/>
            <div style="margin-top: 4px; background: var(--border-color); border-radius: 3px; overflow: hidden;">
                <div style="width: ${sentConf * 100}%; background: ${sentColor}; height: 8px;"></div>
            </div>
        </div>
    `;

    // ===== 3. TOXICITY V7 (4-Layer) =====
    const isToxic = toxicity.is_toxic || false;
    const toxScore = toxicity.overall_score || 0;
    const toxSeverity = toxicity.severity || "Low";
    const toxCategories = toxicity.categories || {};
    const toxLayers = toxicity.detection_layers || [];

    // Vietnamese severity labels
    const severityVi = {
        'None': 'Không', 'Low': 'Thấp', 'Medium': 'Trung bình', 'High': 'Cao', 'Critical': 'Nguy hiểm'
    };

    let toxColor = '#27ae60';  // Green for Low
    if (toxSeverity === 'Medium') toxColor = '#f39c12';
    else if (toxSeverity === 'High') toxColor = '#e74c3c';
    else if (toxSeverity === 'Critical') toxColor = '#c0392b';

    document.getElementById('toxicStatus').innerHTML = 
        `<strong style="color: ${toxColor};">${isToxic ? '⚠️ ĐỘC HẠI' : '✅ AN TOÀN'}</strong> - Mức độ: ${severityVi[toxSeverity] || toxSeverity} (${(toxScore * 100).toFixed(0)}%)`;
    
    let toxDetailsHTML = `
        <div style="font-size: 12px; color: var(--text-secondary); margin-top: 8px;">
            <strong>Mức độ:</strong> ${(toxScore * 100).toFixed(0)}%<br/>
    `;
    
    if (Object.keys(toxCategories).length > 0) {
        toxDetailsHTML += '<strong>Danh mục:</strong><br/>';
        for (const [cat, score] of Object.entries(toxCategories)) {
            if (score > 0.3) {
                toxDetailsHTML += `- ${cat}: ${(score * 100).toFixed(0)}%<br/>`;
            }
        }
    }
    toxDetailsHTML += '</div>';
    document.getElementById('toxicDetails').innerHTML = toxDetailsHTML;

    // ===== 4. FACT CHECK V7 (Multi-Source) =====
    const credScore = factCheck.score || 50;
    const verdict = factCheck.verdict || "Unknown";
    const evidence = factCheck.evidence || [];
    const verificationMethods = factCheck.verification_methods || [];

    // Vietnamese verdict labels
    const verdictVi = {
        'Verified True': 'Đã xác minh đúng', 'Likely True': 'Có thể đúng',
        'Unclear': 'Chưa rõ', 'Likely False': 'Có thể sai', 'False': 'Sai',
        'Unknown': 'Không xác định', 'Quota Limit': '⏳ Đang kiểm tra lại sau'
    };
    const verdictDisplay = verdictVi[verdict] || verdict;

    let credColor = '#27ae60';  // Green for high credibility
    if (credScore < 70) credColor = '#f39c12';  // Orange
    if (credScore < 40) credColor = '#e74c3c';  // Red

    document.getElementById('fakeStatus').innerHTML = 
        `<strong style="color: ${credColor};">${verdictDisplay}</strong><br/>Độ tin cậy: ${credScore}/100`;
    
    document.getElementById('fakeSummary').textContent = 
        `Đã kiểm tra ${verificationMethods.length} nguồn. Tìm thấy ${evidence.length} bằng chứng.`;
    
    // Show evidence with prominent source citation cards
    if (evidence.length > 0) {
        // Rating pill: background + text color pairs
        const ratingStyle = {
            'True':         { bg: '#d4edda', color: '#155724', label: '✔ Đúng' },
            'Accurate':     { bg: '#d4edda', color: '#155724', label: '✔ Chính xác' },
            'Mostly True':  { bg: '#d4edda', color: '#155724', label: '✔ Gần đúng' },
            'False':        { bg: '#f8d7da', color: '#721c24', label: '✘ Sai' },
            'Incorrect':    { bg: '#f8d7da', color: '#721c24', label: '✘ Không đúng' },
            'Mostly False': { bg: '#fde8d8', color: '#7d3200', label: '✘ Phần lớn sai' },
            'Misleading':   { bg: '#fff3cd', color: '#856404', label: '⚠ Gây hiểu nhầm' },
            'Sai lệch':     { bg: '#fff3cd', color: '#856404', label: '⚠ Sai lệch' },
            'Mixture':      { bg: '#fff3cd', color: '#856404', label: '~ Hỗn hợp' },
            'Unverified':   { bg: '#e2e3e5', color: '#383d41', label: '? Chưa xác minh' },
        };

        // Config per source type
        const typeConfig = {
            factcheck: { icon: '🔍', accentColor: '#1a73e8', label: 'Google Fact Check', bgColor: '#e8f0fe' },
            news:      { icon: '📰', accentColor: '#0f9d58', label: 'Báo chí',            bgColor: '#e6f4ea' },
            ai:        { icon: '🤖', accentColor: '#7b1fa2', label: 'AI Analysis',        bgColor: '#f3e5f5' },
        };

        let evidenceHTML = `
<div style="margin-top:10px;">
  <div style="display:flex; align-items:center; gap:6px; margin-bottom:8px;">
    <span style="font-size:13px;">🔎</span>
    <span style="font-size:12px; font-weight:700; color:#1a1a1a; letter-spacing:0.2px;">Nguồn kiểm chứng</span>
    <span style="font-size:10px; background:#e0e0e0; color:#555; border-radius:10px; padding:1px 7px; font-weight:600;">${evidence.length} nguồn</span>
  </div>`;

        evidence.slice(0, 5).forEach(ev => {
            const isStr = typeof ev === 'string';
            const text = isStr ? ev : (ev.text || ev.claim || ev.analysis || ev.description || '');
            const source = isStr ? null : (ev.source || ev.publisher || null);
            const url = isStr ? '' : (ev.url || '');
            const rating = isStr ? '' : (ev.rating || '');
            const itemType = isStr ? 'ai' : (ev.type || (url ? 'news' : 'ai'));

            const cfg = typeConfig[itemType] || typeConfig.ai;
            const searchQuery = encodeURIComponent((text || '').substring(0, 80));
            const linkUrl = url || `https://www.google.com/search?q=${searchQuery}`;
            const hasRealUrl = !!url;

            // Source name: prefer real source field, fall back to type label
            const sourceName = source || cfg.label;

            // Rating pill
            let ratingPill = '';
            if (rating) {
                const rs = ratingStyle[rating] || { bg: '#e2e3e5', color: '#383d41', label: rating };
                ratingPill = `<span style="display:inline-block; font-size:9px; font-weight:700; background:${rs.bg}; color:${rs.color}; border-radius:10px; padding:2px 7px; margin-left:6px; vertical-align:middle; white-space:nowrap;">${rs.label}</span>`;
            }

            evidenceHTML += `
<div style="margin-bottom:7px; border-radius:8px; overflow:hidden; border:1px solid ${cfg.accentColor}33; box-shadow:0 1px 3px rgba(0,0,0,0.07);">
  <!-- Source header -->
  <div style="background:${cfg.bgColor}; padding:5px 8px; display:flex; align-items:center; gap:5px; border-bottom:1px solid ${cfg.accentColor}22;">
    <span style="font-size:12px;">${cfg.icon}</span>
    <span style="font-size:10px; font-weight:700; color:${cfg.accentColor}; flex:1; text-overflow:ellipsis; overflow:hidden; white-space:nowrap;" title="${sourceName}">${sourceName}</span>
    ${ratingPill}
  </div>
  <!-- Evidence text -->
  <div style="background:#fff; padding:6px 8px;">
    <p style="margin:0 0 5px 0; font-size:10px; color:#222; line-height:1.45;">${(text || 'Không có nội dung chi tiết.').substring(0, 160)}</p>
    <a href="${linkUrl}" target="_blank"
       style="display:inline-flex; align-items:center; gap:3px; font-size:9px; font-weight:700; color:#fff; background:${cfg.accentColor}; border-radius:4px; padding:3px 8px; text-decoration:none; letter-spacing:0.2px;">
      ${hasRealUrl ? '🔗 Xem nguồn gốc' : '🔍 Tìm kiếm Google'} <span style="font-size:9px;">→</span>
    </a>
  </div>
</div>`;
        });

        if (evidence.length > 5) {
            evidenceHTML += `<div style="font-size:10px; color:#888; text-align:center; padding:3px 0;">… và ${evidence.length - 5} nguồn khác</div>`;
        }

        evidenceHTML += '</div>';
        document.getElementById('fakeEvidence').innerHTML = evidenceHTML;
    }

    // ===== 5. COMMENTS ANALYSIS V7 (Enhanced) =====
    const totalComments = comments.total || 0;
    const toxicCount = comments.toxic_count || 0;
    const toxicComments = comments.toxic_comments || [];
    const commentDetails = comments.details || [];
    const filterStats = comments.filter_stats || {};
    const apiCallsSaved = comments.api_calls_saved || 0;

    document.getElementById('commentsStatus').innerHTML = 
        `Đã quét: ${totalComments} bình luận | Độc hại: <strong style="color: ${toxicCount > 0 ? '#e74c3c' : '#27ae60'};">${toxicCount}</strong>` +
        (totalComments > 0 ? ` (${comments.toxic_percentage || 0}%)` : '');

    // Always hide the API savings bar (technical info, not user-friendly)
    const savingsBar = document.getElementById('commentsApiSavings');
    if (savingsBar) savingsBar.style.display = 'none';
    
    if (toxicCount > 0) {
        let commentsHTML = '<div style="margin-top: 8px;">';
        toxicComments.forEach((tc, idx) => {
            if (idx < 8) {
                const sevColor = tc.severity === 'Critical' ? '#c0392b' : tc.severity === 'High' ? '#e74c3c' : '#f39c12';
                const sevLabel = severityVi[tc.severity] || tc.severity;
                commentsHTML += `
                    <div style="margin: 6px 0; padding: 8px; background: #fff3cd; border-left: 3px solid ${sevColor}; border-radius: 3px;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span style="font-size: 12px; color: ${sevColor}; font-weight: bold;">${sevLabel} - ${(tc.score * 100).toFixed(0)}%</span>
                        </div>
                        <div style="font-size: 12px; margin-top: 3px;">${highlightEvidenceInText(tc.comment || '', tc.evidence_spans || [])}</div>
                        ${tc.reason ? `<div style="font-size: 12px; color: var(--text-secondary); font-style: italic; margin-top: 3px;">💡 ${tc.reason}</div>` : ''}
                        ${renderEvidenceTags(tc.evidence_spans || [])}
                    </div>
                `;
            }
        });
        if (toxicCount > 8) {
            commentsHTML += `<div style="text-align: center; font-size: 10px; color: #999; margin-top: 4px;">... và ${toxicCount - 8} bình luận độc hại khác</div>`;
        }
        commentsHTML += '</div>';
        document.getElementById('commentsDetails').innerHTML = commentsHTML;
    } else {
        document.getElementById('commentsDetails').innerHTML = '<div style="text-align: center; color: #27ae60; font-weight: bold; margin-top: 8px;">✅ Không phát hiện bình luận độc hại!</div>';
    }

    // ===== 6. WARNINGS (if any) =====
    if (riskScore.warnings && riskScore.warnings.length > 0) {
        document.getElementById('warningsCard').style.display = 'block';
        let warningsHTML = '<ul style="margin: 0; padding-left: 20px; font-size: 12px;">';
        riskScore.warnings.forEach(w => {
            warningsHTML += `<li>${w}</li>`;
        });
        warningsHTML += '</ul>';
        document.getElementById('warningsList').innerHTML = warningsHTML;
    } else {
        document.getElementById('warningsCard').style.display = 'none';
    }

    // ===== 7. RECOMMENDATIONS (if any) =====
    if (riskScore.recommendations && riskScore.recommendations.length > 0) {
        document.getElementById('recommendationsCard').style.display = 'block';
        let recsHTML = '<ul style="margin: 0; padding-left: 20px; font-size: 12px;">';
        riskScore.recommendations.forEach(r => {
            recsHTML += `<li>${r}</li>`;
        });
        recsHTML += '</ul>';
        document.getElementById('recommendationsList').innerHTML = recsHTML;
    } else {
        document.getElementById('recommendationsCard').style.display = 'none';
    }

    console.log("✅ V7 results rendered");

    // ===== 2.1 — OVERLAY CONTROLS (Content Script) =====
    renderOverlayControls(data, urlInfo);

    // ===== V7.0 — SHOW FEEDBACK SECTION (after results) =====
    const feedbackSection = document.getElementById('feedbackSection');
    if (feedbackSection && !isOffline) {
        feedbackSection.classList.remove('hidden');
        // Reset feedback state
        document.getElementById('feedbackExtra').classList.add('hidden');
        document.getElementById('feedbackThanks').classList.add('hidden');
        document.getElementById('feedbackUp').disabled = false;
        document.getElementById('feedbackDown').disabled = false;
    }

    // feature 7.9 — Correction panel (pre-filled with current scores)
    renderCorrectionPanel(data, urlInfo || currentTabUrl);

    // ===== SHOW WARNING MODAL if high risk (after delay) =====
    if (riskValue >= 50) {  // Medium-High or higher (0-100 scale)
        setTimeout(() => {
            showWarningModalV7(riskScore, sentiment, toxicity, factCheck);
        }, 12000);
    }
}

/**
 * V7 Content Script Overlay — Toggle controls card injected into popup results.
 * Shows/hides the floating risk badge on the active page via content.js.
 */
async function renderOverlayControls(data, urlInfo) {
    // Find or create the overlay card
    let card = document.getElementById('overlayControlCard');
    const isNew = !card;
    if (!card) {
        card = document.createElement('div');
        card.id = 'overlayControlCard';
        card.style.cssText = 'margin-top: 10px;';
        // Inject after results container (append to #results)
        const resultsEl = document.getElementById('results');
        if (resultsEl) resultsEl.appendChild(card);
        else return;
    }

    // Read stored toggle state
    const stored = await chrome.storage.local.get(['overlayEnabled']);
    let enabled = stored.overlayEnabled !== false;

    const renderCard = () => {
        const modeTag = data.analysis_mode === 'unified' ? ' ⚡ Unified' : data.was_fallback ? ' (fallback)' : '';
        const pageType = data.page_metadata?.page_type || '';
        const pageTypeLabel = { facebook_post: '📘 Facebook', news_article: '📰 Báo', youtube_video: '▶ YouTube', tiktok: '🎵 TikTok', generic: '🌐 Web' }[pageType] || '';

        card.innerHTML = `
            <div class="card overlay-ctrl-card">
                <div class="overlay-ctrl-header">
                    <div class="overlay-ctrl-title">
                        🔍 Overlay trang${modeTag ? `<span class="overlay-mode-tag"> ${modeTag}</span>` : ''}
                    </div>
                    ${pageTypeLabel ? `<span class="overlay-page-badge">${pageTypeLabel}</span>` : ''}
                </div>
                <div class="overlay-ctrl-btns">
                    <button id="overlayToggleBtn" class="${enabled ? 'btn-primary' : 'btn-secondary'}" style="flex:1; padding: 7px; margin: 0; font-size: 11px;">
                        ${enabled ? '👁 Ẩn Overlay' : '👁 Hiện Overlay'}
                    </button>
                    <button id="overlayJumpBtn" class="btn-secondary" style="flex:1; padding: 7px; font-size: 11px;" title="Cuộn đến bình luận độc hại đầu tiên">
                        💬 BL độc hại
                    </button>
                </div>
                ${data.page_metadata ? `
                <div class="overlay-ctrl-meta">
                    ${data.page_metadata.comment_count_total ? `<span>💬 ${data.page_metadata.comment_count_total} BL</span>` : ''}
                    ${data.page_metadata.reactions_total ? `<span>❤ ${data.page_metadata.reactions_total} react</span>` : ''}
                    ${data.page_metadata.shares ? `<span>↗ ${data.page_metadata.shares} share</span>` : ''}
                    ${data.page_metadata.page_language ? `<span>🌐 ${data.page_metadata.page_language}</span>` : ''}
                </div>` : ''}
            </div>
        `;

        // Toggle handler
        card.querySelector('#overlayToggleBtn').addEventListener('click', async () => {
            enabled = !enabled;
            await chrome.storage.local.set({ overlayEnabled: enabled });

            try {
                const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
                if (tab?.id) {
                    chrome.tabs.sendMessage(tab.id, {
                        type: 'TOGGLE_OVERLAY',
                        enabled,
                    }).catch(() => {
                        // Content script not loaded — inject then show overlay
                        if (chrome.scripting && enabled) {
                            chrome.scripting.executeScript({ target: { tabId: tab.id }, files: ['content.js'] })
                                .then(() => setTimeout(() => {
                                    chrome.tabs.sendMessage(tab.id, { type: 'SHOW_OVERLAY', data }).catch(() => {});
                                }, 600))
                                .catch(() => {});
                        }
                    });
                }
            } catch (_) {}

            renderCard(); // Re-render with updated button state
        });

        // Jump to first toxic comment (also re-shows overlay if dismissed)
        card.querySelector('#overlayJumpBtn').addEventListener('click', async () => {
            try {
                const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
                if (tab?.id) {
                    chrome.tabs.sendMessage(tab.id, { type: 'SHOW_OVERLAY', data }).catch(() => {});
                }
            } catch (_) {}
            window.close(); // Close popup so user can see the page
        });
    };

    renderCard();

    // Auto-send SHOW_OVERLAY to content script as soon as results appear
    if (isNew && enabled) {
        try {
            const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
            if (tab?.id) {
                chrome.tabs.sendMessage(tab.id, {
                    type: 'SHOW_OVERLAY',
                    data,
                }).catch(() => {
                    // Content script not loaded on this page — inject it then retry
                    if (chrome.scripting) {
                        chrome.scripting.executeScript({ target: { tabId: tab.id }, files: ['content.js'] })
                            .then(() => setTimeout(() => {
                                chrome.tabs.sendMessage(tab.id, { type: 'SHOW_OVERLAY', data }).catch(() => {});
                            }, 600))
                            .catch(() => {});
                    }
                });
            }
        } catch (_) {}
    }
}

function renderV2Results(data, urlInfo) {
    const sentiment = data.sentiment || { label: "Neutral", score: 0 };
    const toxicity = data.toxicity || { total: 0, toxic_count: 0, results: [] };

    // Clear previous-version elements
    document.getElementById('riskScore').textContent = 'Chế độ v2';
    document.getElementById('riskLevel').textContent = 'Đang dùng API v2';
    document.getElementById('riskBreakdown').innerHTML = '';
    document.getElementById('sentimentDetails').innerHTML = '';
    document.getElementById('fakeEvidence').innerHTML = '';
    document.getElementById('warningsCard').style.display = 'none';
    document.getElementById('recommendationsCard').style.display = 'none';

    // Sentiment
    const sentLabelVi2 = {'Positive':'Tích cực','Negative':'Tiêu cực','Neutral':'Trung lập','Mixed':'Hỗn hợp','Very Negative':'Rất tiêu cực','Very Positive':'Rất tích cực'};
    document.getElementById('sentimentStatus').innerHTML = 
        `<strong>${sentLabelVi2[sentiment.label] || sentiment.label}</strong> (độ tin cậy ${(sentiment.score * 100).toFixed(0)}%)`;

    // Fact check
    const riskScore = parseInt(fake.risk_score) || 0;
    let riskClass = riskScore <= 3 ? 'risk-low' : 'risk-high';
    let verdict = fake.verdict || "Unknown";
    const verdictVi2 = {'Verified True':'Đã xác minh đúng','Likely True':'Có thể đúng','Unclear':'Chưa rõ','Likely False':'Có thể sai','False':'Sai','Unknown':'Không xác định','Quota Limit':'⏳ Đang kiểm tra lại sau'};
    verdict = verdictVi2[verdict] || verdict;
    
    document.getElementById('fakeStatus').innerHTML = 
        `<strong class="${riskClass}">${verdict}</strong><br/>Rủi ro: ${riskScore}/10`;
    document.getElementById('fakeSummary').textContent = fake.summary || "Không có tóm tắt";

    // Toxicity - Summary
    document.getElementById('toxicStatus').textContent = 
        `Đã quét: ${toxicity.total} bình luận | Phát hiện: ${toxicity.toxic_count} độc hại`;

    const toxicDetails = document.getElementById('toxicDetails');
    document.getElementById('toxicFindings').innerHTML = '';

    if (toxicity.toxic_count === 0) {
        toxicDetails.innerHTML = '<div style="text-align: center; color: #27ae60; font-weight: bold;">✅ Không phát hiện mối đe dọa!</div>';
    } else {
        let detailsHTML = '';
        toxicity.results.forEach((item, idx) => {
            if ((item["Is Toxic"] || item["is_toxic"]) && idx < 20) {
                const category = item.Category || item.category || "Unknown";
                const comment = item.Comment || item.comment || "";
                const confidence = (item.Confidence || item.confidence || 0);
                const confPercent = (confidence * 100).toFixed(0);

                let badgeColor = '#e74c3c';
                if (category.includes("Hate")) badgeColor = '#f39c12';
                else if (category.includes("Sexual")) badgeColor = '#9b59b6';

                detailsHTML += `
                    <div class="toxic-item">
                        <span class="badge" style="background: ${badgeColor}">${category}</span>
                        <span style="font-size: 10px; color: #999;">${confPercent}%</span>
                        <div style="margin-top: 4px; font-size: 11px; color: #555;">"${comment.substring(0, 60)}${comment.length > 60 ? '...' : ''}"</div>
                    </div>
                `;
            }
        });

        toxicDetails.innerHTML = detailsHTML;
    }

    document.getElementById('commentsStatus').innerHTML = '(Xem phần nội dung độc hại ở trên)';
    document.getElementById('commentsDetails').innerHTML = '';

    console.log("✅ v2 results rendered (legacy mode)");

    // ===== SHOW WARNING MODAL for v2 if risky =====
    const isRisky = riskScore >= 6 || sentiment.label === "Negative" || toxicity.toxic_count > 0;
    if (isRisky) {
        setTimeout(() => {
            showWarningModal(fake, sentiment, toxicity);
        }, 12000);
    }
}

function showWarningModalV7(riskScore, sentiment, toxicity, factCheck) {
    const warningModal = document.getElementById('warningModal');
    const warningContent = document.getElementById('warningContent');

    const riskLevelVi = {
        'Low': 'Thấp', 'Medium': 'Trung bình', 'High': 'Cao', 'Critical': 'Nguy hiểm'
    };

    let warningHTML = '';

    const riskValue = riskScore.risk_score || 0;
    const riskLevel = riskScore.risk_level || "Low";

    if (riskValue >= 50) {
        warningHTML += `
            <h4>⚠️ Phát hiện nội dung rủi ro ${riskLevelVi[riskLevel] || riskLevel}</h4>
            <p><strong>Điểm rủi ro:</strong> ${riskValue.toFixed(1)}/100</p>
            <p><strong>Mức độ:</strong> ${riskLevelVi[riskLevel] || riskLevel}</p>
        `;

        if (riskScore.warnings && riskScore.warnings.length > 0) {
            warningHTML += '<p><strong>Cảnh báo:</strong></p><ul>';
            riskScore.warnings.slice(0, 3).forEach(w => {
                warningHTML += `<li>${w}</li>`;
            });
            warningHTML += '</ul>';
        }
    }

    if (toxicity.is_toxic) {
        warningHTML += `
            <h4>🛡️ Phát hiện nội dung độc hại</h4>
            <p><strong>Mức độ:</strong> ${{None:'Không',Low:'Thấp',Medium:'Trung bình',High:'Cao',Critical:'Nguy hiểm'}[toxicity.severity] || toxicity.severity}</p>
            <p><strong>Điểm:</strong> ${(toxicity.overall_score * 100).toFixed(0)}%</p>
        `;
    }

    if (factCheck.score < 40) {
        warningHTML += `
            <h4>📰 Cảnh báo độ tin cậy thấp</h4>
            <p><strong>Độ tin cậy:</strong> ${factCheck.score}/100</p>
            <p><strong>Kết luận:</strong> ${{  'Verified True':'Đã xác minh đúng','Likely True':'Có thể đúng','Unclear':'Chưa rõ','Likely False':'Có thể sai','False':'Sai'}[factCheck.verdict] || factCheck.verdict}</p>
        `;
    }

    warningContent.innerHTML = warningHTML;
    warningModal.classList.remove('hidden');

    // Button handlers
    const continueBtn = document.getElementById('warningContinue');
    const leaveBtn = document.getElementById('warningLeave');

    const newContinueBtn = continueBtn.cloneNode(true);
    const newLeaveBtn = leaveBtn.cloneNode(true);
    continueBtn.parentNode.replaceChild(newContinueBtn, continueBtn);
    leaveBtn.parentNode.replaceChild(newLeaveBtn, leaveBtn);

    newContinueBtn.addEventListener('click', () => {
        warningModal.classList.add('hidden');
    });

    newLeaveBtn.addEventListener('click', async () => {
        const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
        if (tab) {
            try {
                const url = new URL(tab.url);
                const homepage = `${url.protocol}//${url.hostname}`;
                chrome.tabs.update(tab.id, { url: homepage });
            } catch (err) {
                console.error("Error:", err);
            }
        }
        warningModal.classList.add('hidden');
    });
}

// Keep original v2 warning modal for backward compatibility

function showWarningModal(fake, sentiment, toxicity) {
    const warningModal = document.getElementById('warningModal');
    const warningContent = document.getElementById('warningContent');

    let warningHTML = '';

    // Fake news warning
    if ((fake.risk_score || 0) >= 6) {
        warningHTML += `
            <h4>📰 Có thể là tin giả/sai lệch</h4>
            <p><strong>Mức rủi ro:</strong> ${fake.risk_score}/10</p>
            <p><strong>Kết luận:</strong> ${fake.verdict || "Rủi ro cao"}</p>
            <p><strong>Chi tiết:</strong> ${fake.summary || "Nội dung này có thể chứa thông tin sai lệch hoặc tin giả."}</p>
        `;
    }

    // Negative sentiment warning
    if (sentiment.label === "Negative" || sentiment.label === "Very Negative") {
        warningHTML += `
            <h4>😞 Phát hiện nội dung tiêu cực/có hại</h4>
            <p><strong>Cảm xúc:</strong> ${{Positive:'Tích cực',Negative:'Tiêu cực',Neutral:'Trung lập','Very Negative':'Rất tiêu cực','Very Positive':'Rất tích cực'}[sentiment.label] || sentiment.label}</p>
            <p><strong>Độ tin cậy:</strong> ${(sentiment.score * 100).toFixed(0)}%</p>
            <p>Nội dung này được phát hiện có tính chất tiêu cực hoặc có hại.</p>
        `;
    }

    // Toxicity warning
    if (toxicity.toxic_count > 0) {
        const topThreats = toxicity.results
            .filter(item => item["Is Toxic"] || item["is_toxic"])
            .slice(0, 3);

        warningHTML += `
            <h4>💬 Phát hiện bình luận độc hại/xúc phạm</h4>
            <p><strong>Số lượng:</strong> ${toxicity.toxic_count} bình luận có vấn đề</p>
            <p><strong>Đã quét:</strong> ${toxicity.total} bình luận tổng cộng</p>
        `;

        if (topThreats.length > 0) {
            warningHTML += '<p><strong>Ví dụ:</strong></p><ul>';
            topThreats.forEach(item => {
                const category = item.Category || item.category || "Toxic";
                const comment = item.Comment || item.comment || "";
                warningHTML += `<li><strong>${category}:</strong> "${comment.substring(0, 50)}${comment.length > 50 ? '...' : ''}"</li>`;
            });
            warningHTML += '</ul>';
        }
    }

    warningContent.innerHTML = warningHTML;
    warningModal.classList.remove('hidden');

    // ===== WARNING BUTTON HANDLERS =====
    const continueBtn = document.getElementById('warningContinue');
    const leaveBtn = document.getElementById('warningLeave');

    // Remove existing listeners by cloning
    const newContinueBtn = continueBtn.cloneNode(true);
    const newLeaveBtn = leaveBtn.cloneNode(true);
    continueBtn.parentNode.replaceChild(newContinueBtn, continueBtn);
    leaveBtn.parentNode.replaceChild(newLeaveBtn, leaveBtn);

    // Click: Continue Reading - Show results anyway
    newContinueBtn.addEventListener('click', () => {
        warningModal.classList.add('hidden');
        document.getElementById('results').classList.remove('hidden');
        // Results already rendered, just show them
    });

    // Click: Don't Read - Go back to site homepage
    newLeaveBtn.addEventListener('click', async () => {
        const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
        if (tab) {
            try {
                const url = new URL(tab.url);
                const homepage = `${url.protocol}//${url.hostname}`;
                chrome.tabs.update(tab.id, { url: homepage });
                console.log("↩️ Redirected to:", homepage);
            } catch (err) {
                console.error("Error navigating to homepage:", err);
            }
        }
        warningModal.classList.add('hidden');
    });
}

// ============================================================================
// SCAN HISTORY
// ============================================================================

async function toggleHistory() {
    const historyPanel = document.getElementById('historyPanel');
    if (!historyPanel) return;

    if (historyPanel.classList.contains('hidden')) {
        // Show history
        await renderHistory();
        historyPanel.classList.remove('hidden');
        document.getElementById('results').classList.add('hidden');
        document.getElementById('confirmation').classList.add('hidden');
    } else {
        // Hide history, show results if available
        historyPanel.classList.add('hidden');
        if (currentResultsData) {
            document.getElementById('results').classList.remove('hidden');
        }
    }
}

async function renderHistory() {
    const historyList = document.getElementById('historyList');
    if (!historyList) return;

    const data = await chrome.storage.local.get(['scanHistory']);
    const history = data.scanHistory || [];

    if (history.length === 0) {
        historyList.innerHTML = '<div style="text-align: center; color: #999; padding: 20px;">Chưa có lịch sử quét</div>';
        return;
    }

    const riskLevelVi = { 'Low': 'Thấp', 'Medium': 'Trung bình', 'High': 'Cao', 'Critical': 'Nguy hiểm' };
    const riskColors = { 'Low': '#27ae60', 'Medium': '#f39c12', 'High': '#e74c3c', 'Critical': '#c0392b' };

    let html = '';
    history.forEach((entry, idx) => {
        const timeAgo = getTimeAgo(entry.timestamp);
        const riskColor = riskColors[entry.riskLevel] || '#3498db';
        const riskLabel = riskLevelVi[entry.riskLevel] || entry.riskLevel;
        const domain = entry.domain || getDomain(entry.url);
        const articleTitle = entry.title && entry.title !== domain ? entry.title : '';
        const displayTitle = articleTitle || domain;

        html += `
            <div class="history-card" data-url="${entry.url}">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div style="flex: 1; overflow: hidden;">
                        <div style="font-size: 12px; font-weight: bold; color: var(--text-primary, #333); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="${displayTitle.replace(/"/g, '&quot;')}">
                            ${displayTitle}
                        </div>
                        <div style="font-size: 10px; color: var(--text-secondary, #999); margin-top: 2px;">${domain} · ${timeAgo}</div>
                    </div>
                    <div style="text-align: right; margin-left: 8px;">
                        <div style="font-size: 16px; font-weight: bold; color: ${riskColor};">${Math.round(entry.riskScore)}</div>
                        <div style="font-size: 9px; color: ${riskColor};">${riskLabel}</div>
                    </div>
                </div>
                ${entry.toxicCount > 0 ? `<div style="font-size: 10px; color: #e74c3c; margin-top: 4px;">⚠️ ${entry.toxicCount} bình luận độc hại</div>` : ''}
            </div>
        `;
    });

    historyList.innerHTML = html;

    // Use event delegation instead of inline onclick (CSP compliant)
    historyList.querySelectorAll('.history-card').forEach(card => {
        card.addEventListener('click', () => {
            const url = card.getAttribute('data-url');
            if (url) chrome.tabs.create({ url: url, active: true });
        });
    });
}

function getTimeAgo(timestamp) {
    const now = new Date();
    const then = new Date(timestamp);
    const diffMs = now - then;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Vừa xong';
    if (diffMins < 60) return `${diffMins} phút trước`;
    if (diffHours < 24) return `${diffHours} giờ trước`;
    if (diffDays < 7) return `${diffDays} ngày trước`;
    return then.toLocaleDateString('vi-VN');
}

// Clear history handler
document.addEventListener('DOMContentLoaded', () => {
    const clearHistoryBtn = document.getElementById('clearHistoryBtn');
    if (clearHistoryBtn) {
        clearHistoryBtn.addEventListener('click', async () => {
            await chrome.storage.local.remove(['scanHistory']);
            renderHistory();
        });
    }
});

// ============================================================================
// EXPORT REPORT
// ============================================================================

function exportReport(data, url) {
    const isSupported = !!(data.sentiment_v7 || data.version === "7.0");
    if (!isSupported) return;

    const sentiment = data.sentiment_v7 || {};
    const toxicity = data.toxicity_v7 || {};
    const factCheck = data.fact_check_v7 || {};
    const riskScore = data.risk_score_v7 || {};
    const comments = data.comments_analysis || {};
    const summary = data.article_summary || {};

    const riskLevelVi = { 'Low': 'Thấp', 'Medium': 'Trung bình', 'High': 'Cao', 'Critical': 'Nguy hiểm' };
    const sentLabelVi = { 'Positive': 'Tích cực', 'Negative': 'Tiêu cực', 'Neutral': 'Trung lập', 'Mixed': 'Hỗn hợp', 'Very Positive': 'Rất tích cực', 'Very Negative': 'Rất tiêu cực' };
    const severityVi = { 'None': 'Không', 'Low': 'Thấp', 'Medium': 'Trung bình', 'High': 'Cao', 'Critical': 'Nguy hiểm' };

    const riskValue = riskScore.risk_score || 0;
    const riskColor = riskValue < 25 ? '#27ae60' : riskValue < 50 ? '#f39c12' : riskValue < 75 ? '#e74c3c' : '#c0392b';

    const now = new Date();
    const dateStr = now.toLocaleDateString('vi-VN', { year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit' });
    const domain = url ? new URL(url).hostname.replace('www.', '') : 'unknown';

    const htmlReport = `<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="utf-8">
    <title>Báo cáo VnContentGuard Pro — ${domain}</title>
    <style>
        body { font-family: 'Segoe UI', Roboto, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; color: #333; }
        h1 { color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }
        h2 { color: #2c3e50; margin-top: 25px; }
        .risk-badge { display: inline-block; padding: 8px 24px; border-radius: 8px; color: white; font-size: 24px; font-weight: bold; }
        .card { background: #f9f9f9; padding: 15px; border-radius: 8px; margin: 10px 0; border-left: 4px solid #3498db; }
        .toxic { border-left-color: #e74c3c; background: #fff5f5; }
        .safe { border-left-color: #27ae60; background: #f0fff0; }
        table { width: 100%; border-collapse: collapse; margin: 10px 0; }
        th, td { padding: 8px 12px; border: 1px solid #ddd; text-align: left; }
        th { background: #f0f0f0; }
        .footer { margin-top: 30px; padding-top: 15px; border-top: 2px solid #eee; color: #999; font-size: 12px; text-align: center; }
        @media print {
            body { margin: 0; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
            .risk-badge { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
            .no-print { display: none !important; }
            a { color: #333; text-decoration: none; }
        }
        @page { margin: 15mm 12mm; size: A4; }
        .print-hint { text-align: center; margin: 15px 0; padding: 10px; background: #e8f4fd; border-radius: 8px; font-size: 13px; color: #2980b9; }
    </style>
</head>
<body>
    <div class="print-hint no-print">💡 Chọn <strong>"Save as PDF"</strong> / <strong>"Lưu dưới dạng PDF"</strong> trong hộp thoại in để tải báo cáo PDF</div>
    <h1>🛡️ VnContentGuard Pro — Báo cáo phân tích</h1>
    <p><strong>URL:</strong> <a href="${url || '#'}">${url || 'N/A'}</a></p>
    <p><strong>Ngày quét:</strong> ${dateStr}</p>
    <p><strong>Phiên bản:</strong> V7.0</p>

    <h2>📊 Điểm Rủi Ro Tổng Thể</h2>
    <div style="text-align: center; margin: 15px 0;">
        <span class="risk-badge" style="background: ${riskColor};">${riskValue.toFixed(1)}/100</span>
        <p style="font-size: 18px; color: ${riskColor}; font-weight: bold;">${riskLevelVi[riskScore.risk_level] || riskScore.risk_level || 'N/A'}</p>
    </div>
    ${riskScore.breakdown ? `
    <table>
        <tr><th>Thành phần</th><th>Điểm</th></tr>
        <tr><td>Tin giả</td><td>${(riskScore.breakdown.fake_news_component || 0).toFixed(1)}</td></tr>
        <tr><td>Độc hại</td><td>${(riskScore.breakdown.toxicity_component || 0).toFixed(1)}</td></tr>
        <tr><td>Cảm xúc</td><td>${(riskScore.breakdown.sentiment_component || 0).toFixed(1)}</td></tr>
        <tr><td>Nguồn</td><td>${(riskScore.breakdown.source_component || 0).toFixed(1)}</td></tr>
        <tr><td>Thao túng</td><td>${(riskScore.breakdown.manipulation_component || 0).toFixed(1)}</td></tr>
    </table>` : ''}

    ${summary.summary ? `
    <h2>📰 Tóm tắt bài viết</h2>
    <div class="card">${summary.summary}</div>` : ''}

    <h2>🎭 Phân tích cảm xúc</h2>
    <div class="card">
        <strong>${sentLabelVi[sentiment.overall] || sentiment.overall || 'N/A'}</strong>
        (Độ tin cậy: ${((sentiment.confidence || 0) * 100).toFixed(0)}%)
    </div>

    <h2>🛡️ Phát hiện nội dung độc hại</h2>
    <div class="card ${toxicity.is_toxic ? 'toxic' : 'safe'}">
        <strong>${toxicity.is_toxic ? '⚠️ ĐỘC HẠI' : '✅ AN TOÀN'}</strong>
        — Mức độ: ${severityVi[toxicity.severity] || toxicity.severity || 'N/A'}
        (${((toxicity.overall_score || 0) * 100).toFixed(0)}%)
    </div>

    <h2>📰 Kiểm tra thực tế</h2>
    <div class="card">
        <strong>${factCheck.verdict || 'N/A'}</strong> — Độ tin cậy: ${factCheck.score || 50}/100
    </div>

    <h2>💬 Phân tích bình luận</h2>
    <div class="card">
        <p>Tổng bình luận: ${comments.total || 0} | Độc hại: ${comments.toxic_count || 0} (${comments.toxic_percentage || 0}%)</p>
    </div>
    ${(comments.toxic_comments || []).length > 0 ? `
    <table>
        <tr><th>Bình luận</th><th>Mức độ</th><th>Lý do</th></tr>
        ${(comments.toxic_comments || []).slice(0, 10).map(tc => `
        <tr>
            <td>${(tc.comment || '').substring(0, 80)}${(tc.comment || '').length > 80 ? '...' : ''}</td>
            <td>${severityVi[tc.severity] || tc.severity || 'N/A'}</td>
            <td>${tc.reason || ''}</td>
        </tr>`).join('')}
    </table>` : ''}

    ${(riskScore.recommendations || []).length > 0 ? `
    <h2>💡 Khuyến nghị</h2>
    <ul>${riskScore.recommendations.map(r => `<li>${r}</li>`).join('')}</ul>` : ''}

    <div class="footer">
        <p>Báo cáo được tạo bởi VnContentGuard Pro V7.0</p>
        <p>⚠️ Kết quả phân tích mang tính tham khảo. Hãy luôn kiểm chứng thông tin từ nhiều nguồn.</p>
    </div>
</body>
</html>`;

    // Open report in new tab and auto-trigger print-to-PDF
    const blob = new Blob([htmlReport], { type: 'text/html;charset=utf-8' });
    const reportDataUrl = URL.createObjectURL(blob);

    chrome.tabs.create({ url: reportDataUrl, active: true }, (tab) => {
        // Inject auto-print script after page loads
        setTimeout(() => {
            chrome.scripting.executeScript({
                target: { tabId: tab.id },
                func: () => { window.print(); }
            }).catch(() => {
                // If scripting fails, user can manually Ctrl+P
                console.log('Auto-print failed — user can press Ctrl+P');
            });
        }, 800);

        // Clean up blob URL after a delay
        setTimeout(() => URL.revokeObjectURL(reportDataUrl), 10000);
    });
}

// ============================================================================
// USER FEEDBACK (V7.0)
// ============================================================================

let feedbackRating = null;

function handleFeedback(rating) {
    feedbackRating = rating;

    // Highlight selected button
    const upBtn = document.getElementById('feedbackUp');
    const downBtn = document.getElementById('feedbackDown');
    upBtn.disabled = true;
    downBtn.disabled = true;

    if (rating === 'positive') {
        upBtn.style.transform = 'scale(1.3)';
        // For positive, submit immediately
        submitFeedbackToBackend(rating, '');
    } else {
        downBtn.style.transform = 'scale(1.3)';
        // For negative, show correction input
        document.getElementById('feedbackExtra').classList.remove('hidden');
    }
}

function submitFeedbackWithCorrection() {
    const correction = document.getElementById('feedbackText').value.trim();
    submitFeedbackToBackend(feedbackRating || 'negative', correction);
}

async function submitFeedbackToBackend(rating, correction) {
    try {
        const data = {
            url: currentTabUrl || '',
            rating: rating,
            correction: correction,
            modules: {},
            scan_results: currentResultsData || {}
        };

        // Also save to local feedback history for weekly report
        chrome.storage.local.get(['feedbackHistory'], (stored) => {
            const history = stored.feedbackHistory || [];
            history.unshift({
                url: currentTabUrl,
                feedback: rating === 'positive' ? 'agree' : 'disagree',
                is_correct: rating === 'positive',
                correction: correction,
                timestamp: new Date().toISOString()
            });
            if (history.length > 100) history.splice(100);
            chrome.storage.local.set({ feedbackHistory: history });
        });

        // Send via background service worker
        const result = await chrome.runtime.sendMessage({
            type: 'SUBMIT_FEEDBACK',
            data: data
        });

        console.log('📝 Feedback result:', result);

    } catch (err) {
        console.error('Feedback error:', err);
    }

    // Show thank you message
    document.getElementById('feedbackExtra').classList.add('hidden');
    document.getElementById('feedbackThanks').classList.remove('hidden');

    setTimeout(() => {
        document.getElementById('feedbackThanks').classList.add('hidden');
    }, 3000);
}

// ============================================================================
// COMPARISON MODE (V7.0)
// ============================================================================

async function toggleComparePanel() {
    const comparePanel = document.getElementById('comparePanel');
    if (!comparePanel) return;

    if (comparePanel.classList.contains('hidden')) {
        // Show panel and populate selects from history
        await populateCompareSelects();
        comparePanel.classList.remove('hidden');
        document.getElementById('results').classList.add('hidden');
        document.getElementById('historyPanel').classList.add('hidden');
        document.getElementById('confirmation').classList.add('hidden');
    } else {
        comparePanel.classList.add('hidden');
        if (currentResultsData) {
            document.getElementById('results').classList.remove('hidden');
        }
    }
}

async function populateCompareSelects() {
    const data = await chrome.storage.local.get(['scanHistory']);
    const history = data.scanHistory || [];

    const select1 = document.getElementById('compareSelect1');
    const select2 = document.getElementById('compareSelect2');

    // Clear existing options
    select1.innerHTML = '<option value="">— Chọn trang 1 —</option>';
    select2.innerHTML = '<option value="">— Chọn trang 2 —</option>';

    history.forEach((entry, idx) => {
        const domain = entry.domain || getDomain(entry.url);
        const articleTitle = entry.title && entry.title !== domain ? entry.title : domain;
        const shortTitle = articleTitle.length > 50 ? articleTitle.substring(0, 50) + '...' : articleTitle;
        const risk = Math.round(entry.riskScore);
        const label = `${shortTitle} [${domain}] (Rủi ro: ${risk})`;
        const opt1 = new Option(label, entry.url);
        const opt2 = new Option(label, entry.url);
        select1.add(opt1);
        select2.add(opt2);
    });
}

async function runComparison() {
    const url1 = document.getElementById('compareSelect1').value;
    const url2 = document.getElementById('compareSelect2').value;

    if (!url1 || !url2) {
        document.getElementById('compareResults').innerHTML = '<div style="color: #e74c3c; font-size: 12px;">⚠️ Vui lòng chọn 2 trang để so sánh.</div>';
        return;
    }

    if (url1 === url2) {
        document.getElementById('compareResults').innerHTML = '<div style="color: #e74c3c; font-size: 12px;">⚠️ Vui lòng chọn 2 trang khác nhau.</div>';
        return;
    }

    // Load cached results for both URLs
    const cached = await chrome.storage.local.get([url1, url2]);
    const data1 = cached[url1];
    const data2 = cached[url2];

    if (!data1 || !data2) {
        document.getElementById('compareResults').innerHTML = '<div style="color: #e74c3c; font-size: 12px;">⚠️ Không tìm thấy dữ liệu đầy đủ. Hãy quét cả 2 trang trước.</div>';
        return;
    }

    await renderComparison(data1, data2, url1, url2);
}

async function renderComparison(data1, data2, url1, url2) {
    const risk1 = data1.risk_score_v7?.risk_score || 0;
    const risk2 = data2.risk_score_v7?.risk_score || 0;
    const level1 = data1.risk_score_v7?.risk_level || 'Low';
    const level2 = data2.risk_score_v7?.risk_level || 'Low';
    const sent1 = data1.sentiment_v7?.overall || 'Neutral';
    const sent2 = data2.sentiment_v7?.overall || 'Neutral';
    const toxic1 = data1.toxicity_v7?.is_toxic || false;
    const toxic2 = data2.toxicity_v7?.is_toxic || false;
    const fact1 = data1.fact_check_v7?.score || 50;
    const fact2 = data2.fact_check_v7?.score || 50;
    const verdict1 = data1.fact_check_v7?.verdict || '?';
    const verdict2 = data2.fact_check_v7?.verdict || '?';
    const toxicCount1 = data1.comments_analysis?.toxic_count || 0;
    const toxicCount2 = data2.comments_analysis?.toxic_count || 0;
    const totalComments1 = data1.comments_analysis?.total || 0;
    const totalComments2 = data2.comments_analysis?.total || 0;

    const domain1 = getDomain(url1);
    const domain2 = getDomain(url2);

    // Get article titles from history for display
    const historyData = await chrome.storage.local.get(['scanHistory']);
    const historyList = historyData.scanHistory || [];
    const entry1 = historyList.find(h => h.url === url1);
    const entry2 = historyList.find(h => h.url === url2);
    const title1 = (entry1?.title && entry1.title !== domain1) ? entry1.title : domain1;
    const title2 = (entry2?.title && entry2.title !== domain2) ? entry2.title : domain2;
    const shortTitle1 = title1.length > 35 ? title1.substring(0, 35) + '...' : title1;
    const shortTitle2 = title2.length > 35 ? title2.substring(0, 35) + '...' : title2;
    const header1 = `${shortTitle1}<br/><span style="font-size:9px;color:var(--text-secondary,#999);">${domain1}</span>`;
    const header2 = `${shortTitle2}<br/><span style="font-size:9px;color:var(--text-secondary,#999);">${domain2}</span>`;

    const riskColor = (r) => r < 25 ? '#27ae60' : r < 50 ? '#f39c12' : r < 75 ? '#e74c3c' : '#c0392b';
    const sentColor = (s) => s === 'Positive' || s === 'Very Positive' ? '#27ae60' : s === 'Negative' || s === 'Very Negative' ? '#e74c3c' : s === 'Mixed' ? '#f39c12' : '#3498db';
    const riskLabelVi = { 'Low': 'Thấp', 'Medium': 'TB', 'High': 'Cao', 'Critical': 'Nguy hiểm' };
    const sentLabelVi = { 'Positive': 'Tích cực', 'Negative': 'Tiêu cực', 'Neutral': 'Trung lập', 'Mixed': 'Hỗn hợp', 'Very Positive': 'Rất tích cực', 'Very Negative': 'Rất tiêu cực' };

    // Which is more reliable?
    const moreReliable = fact1 > fact2 ? shortTitle1 : fact2 > fact1 ? shortTitle2 : 'Ngang nhau';
    const lowerRisk = risk1 < risk2 ? shortTitle1 : risk2 < risk1 ? shortTitle2 : 'Ngang nhau';

    const html = `
        <div style="margin-top: 8px;">
            <table style="width: 100%; border-collapse: collapse; font-size: 11px;">
                <thead>
                    <tr style="background: var(--bg-card-hover); border-bottom: 2px solid var(--border-color);">
                        <th style="padding: 6px; text-align: left;">Tiêu chí</th>
                        <th style="padding: 6px; text-align: center; max-width: 140px; overflow: hidden; text-overflow: ellipsis; font-size: 10px;">${header1}</th>
                        <th style="padding: 6px; text-align: center; max-width: 140px; overflow: hidden; text-overflow: ellipsis; font-size: 10px;">${header2}</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td style="padding: 6px; border-bottom: 1px solid var(--border-color);">📊 Rủi ro</td>
                        <td style="padding: 6px; text-align: center; border-bottom: 1px solid var(--border-color); color: ${riskColor(risk1)}; font-weight: bold;">${risk1.toFixed(0)}/100 (${riskLabelVi[level1] || level1})</td>
                        <td style="padding: 6px; text-align: center; border-bottom: 1px solid var(--border-color); color: ${riskColor(risk2)}; font-weight: bold;">${risk2.toFixed(0)}/100 (${riskLabelVi[level2] || level2})</td>
                    </tr>
                    <tr>
                        <td style="padding: 6px; border-bottom: 1px solid var(--border-color);">🎭 Cảm xúc</td>
                        <td style="padding: 6px; text-align: center; border-bottom: 1px solid var(--border-color); color: ${sentColor(sent1)};">${sentLabelVi[sent1] || sent1}</td>
                        <td style="padding: 6px; text-align: center; border-bottom: 1px solid var(--border-color); color: ${sentColor(sent2)};">${sentLabelVi[sent2] || sent2}</td>
                    </tr>
                    <tr>
                        <td style="padding: 6px; border-bottom: 1px solid var(--border-color);">🛡️ Độc hại</td>
                        <td style="padding: 6px; text-align: center; border-bottom: 1px solid var(--border-color);">${toxic1 ? '⚠️ Có' : '✅ Không'}</td>
                        <td style="padding: 6px; text-align: center; border-bottom: 1px solid var(--border-color);">${toxic2 ? '⚠️ Có' : '✅ Không'}</td>
                    </tr>
                    <tr>
                        <td style="padding: 6px; border-bottom: 1px solid var(--border-color);">📰 Tin cậy</td>
                        <td style="padding: 6px; text-align: center; border-bottom: 1px solid var(--border-color);">${fact1}/100 (${verdict1})</td>
                        <td style="padding: 6px; text-align: center; border-bottom: 1px solid var(--border-color);">${fact2}/100 (${verdict2})</td>
                    </tr>
                    <tr>
                        <td style="padding: 6px; border-bottom: 1px solid var(--border-color);">💬 BL độc hại</td>
                        <td style="padding: 6px; text-align: center; border-bottom: 1px solid var(--border-color);">${toxicCount1}/${totalComments1}</td>
                        <td style="padding: 6px; text-align: center; border-bottom: 1px solid var(--border-color);">${toxicCount2}/${totalComments2}</td>
                    </tr>
                </tbody>
            </table>
            <div style="margin-top: 10px; padding: 8px; background: var(--summary-bg); border-radius: 6px; font-size: 11px;">
                <strong>📋 Kết luận:</strong><br/>
                🏆 Đáng tin hơn: <strong>${moreReliable}</strong><br/>
                🛡️ An toàn hơn: <strong>${lowerRisk}</strong>
            </div>
        </div>
    `;

    document.getElementById('compareResults').innerHTML = html;
}

function getDomain(url) {
    try { return new URL(url).hostname.replace('www.', ''); } catch { return url.substring(0, 30); }
}

// ============================================================================
// STREAMING PROGRESS (V7.0)
// ============================================================================

const MODULE_NAMES = {
    article_summary: '📰 Tóm tắt',
    sentiment_v7: '🎭 Cảm xúc',
    toxicity_v7: '🛡️ Độc hại',
    fact_check_v7: '📰 Kiểm tra TT',
    risk_score_v7: '📊 Rủi ro',
    comments_analysis: '💬 Bình luận'
};

function updateStreamProgress(count, modules) {
    const total = 6;
    const pct = Math.round((count / total) * 100);
    const fill = document.getElementById('streamProgressFill');
    const text = document.getElementById('streamProgressText');
    const progressEl = document.getElementById('streamProgress');

    if (fill) fill.style.width = `${pct}%`;
    if (text) {
        const names = Object.keys(modules).map(m => MODULE_NAMES[m] || m).join(', ');
        text.textContent = `${count}/${total} bước hoàn tất${names ? ' — ' + names : ''}`;
    }
    if (progressEl && count > 0) progressEl.classList.remove('hidden');
}

// ============================================================================
// BLOCKLIST CHECK (V7.0)
// ============================================================================

async function checkBlocklistStatus(url) {
    try {
        const result = await chrome.runtime.sendMessage({ type: 'CHECK_BLOCKLIST', url: url });
        const warning = document.getElementById('blocklistWarning');
        if (result && result.blocked && warning) {
            warning.classList.remove('hidden');
            const detail = document.getElementById('blocklistDetail');
            if (detail) detail.textContent = `${result.domain} — đã bị cộng đồng báo cáo.`;
        }
    } catch {
        // Background service worker not yet ready
    }
}

// ============================================================================
// REPORT PAGE (V7.0)
// ============================================================================

function toggleReportPanel() {
    const panel = document.getElementById('reportPanel');
    if (!panel) return;

    if (panel.classList.contains('hidden')) {
        panel.classList.remove('hidden');
        document.getElementById('results').classList.add('hidden');
        document.getElementById('historyPanel').classList.add('hidden');
        document.getElementById('comparePanel').classList.add('hidden');
        document.getElementById('parentalPanel').classList.add('hidden');
        // Set current URL
        const reportUrl = document.getElementById('reportUrl');
        if (reportUrl) reportUrl.textContent = currentTabUrl || 'N/A';
        // Reset result
        const reportResult = document.getElementById('reportResult');
        if (reportResult) reportResult.classList.add('hidden');
    } else {
        panel.classList.add('hidden');
        if (currentResultsData) document.getElementById('results').classList.remove('hidden');
    }
}

async function submitPageReport() {
    const reason = document.getElementById('reportReason')?.value || 'other';
    const resultEl = document.getElementById('reportResult');

    if (!currentTabUrl) {
        if (resultEl) {
            resultEl.textContent = '❌ Không có URL để báo cáo.';
            resultEl.style.color = '#e74c3c';
            resultEl.classList.remove('hidden');
        }
        return;
    }

    const riskScore = currentResultsData?.risk_score_v7?.risk_score || 50;
    const btn = document.getElementById('reportSubmitBtn');
    if (btn) { btn.disabled = true; btn.textContent = '⏳ Đang gửi...'; }

    try {
        const result = await chrome.runtime.sendMessage({
            type: 'SUBMIT_REPORT',
            data: {
                url: currentTabUrl,
                risk_score: riskScore,
                reason: reason
            }
        });

        if (resultEl) {
            if (result && result.status === 'reported') {
                resultEl.textContent = `✅ Đã báo cáo! (${result.report_count || 1} lượt)`;
                resultEl.style.color = '#27ae60';
            } else if (result && result.status === 'already_blocked') {
                resultEl.textContent = '🚫 Trang này đã bị chặn.';
                resultEl.style.color = '#f39c12';
            } else {
                resultEl.textContent = '❌ Không thể gửi báo cáo.';
                resultEl.style.color = '#e74c3c';
            }
            resultEl.classList.remove('hidden');
        }
    } catch {
        if (resultEl) {
            resultEl.textContent = '❌ Lỗi kết nối.';
            resultEl.style.color = '#e74c3c';
            resultEl.classList.remove('hidden');
        }
    } finally {
        if (btn) { btn.disabled = false; btn.textContent = '🚩 Gửi báo cáo'; }
    }
}

// ============================================================================
// PARENTAL CONTROL (V7.0)
// ============================================================================

function toggleParentalPanel() {
    const panel = document.getElementById('parentalPanel');
    if (!panel) return;

    if (panel.classList.contains('hidden')) {
        panel.classList.remove('hidden');
        document.getElementById('results').classList.add('hidden');
        document.getElementById('historyPanel').classList.add('hidden');
        document.getElementById('comparePanel').classList.add('hidden');
        document.getElementById('reportPanel').classList.add('hidden');

        // Load current parental settings
        chrome.runtime.sendMessage({ type: 'GET_PARENTAL_CONTROL' }, (response) => {
            if (response) {
                const toggle = document.getElementById('parentalToggle');
                const threshold = document.getElementById('parentalThreshold');
                const thresholdVal = document.getElementById('parentalThresholdVal');
                const pin = document.getElementById('parentalPinInput');

                if (toggle) toggle.checked = response.enabled;
                if (threshold) threshold.value = response.threshold;
                if (thresholdVal) thresholdVal.textContent = response.threshold;
                if (pin) pin.value = response.pin;
            }
        });

        // Load incognito mode setting + log count
        chrome.runtime.sendMessage({ type: 'GET_INCOGNITO_LOG' }, (r) => {
            if (r) {
                const sel = document.getElementById('incognitoBlockMode');
                if (sel) sel.value = r.mode || 'off';
                const badge = document.getElementById('incognitoLogCount');
                if (badge) badge.textContent = r.log.length;
            }
        });

        // Load domain lists for 6.2
        loadDomainLists();
    } else {
        panel.classList.add('hidden');
        if (currentResultsData) document.getElementById('results').classList.remove('hidden');
    }
}

async function saveParentalSettings() {
    const enabled = document.getElementById('parentalToggle')?.checked || false;
    const pin = document.getElementById('parentalPinInput')?.value || '0000';
    const threshold = parseInt(document.getElementById('parentalThreshold')?.value || '70');
    const incognitoMode = document.getElementById('incognitoBlockMode')?.value || 'off';

    if (pin.length < 4) {
        alert('Mã PIN phải từ 4 ký tự trở lên.');
        return;
    }

    // Save parental + incognito mode in parallel
    await Promise.all([
        chrome.runtime.sendMessage({
            type: 'SET_PARENTAL_CONTROL',
            enabled: enabled,
            pin: pin,
            threshold: threshold
        }),
        chrome.runtime.sendMessage({ type: 'SET_INCOGNITO_MODE', mode: incognitoMode })
    ]);

    const statusEl = document.getElementById('status');
    if (statusEl) {
        statusEl.textContent = enabled ? `🔒 Kiểm soát gia đình: BẬT (ngưỡng ${threshold})` : '🔓 Kiểm soát gia đình: TẮT';
        setTimeout(() => { statusEl.textContent = 'Sẵn sàng quét'; }, 3000);
    }
}

// ============================================================================
// feature 7.2 — DOMAIN BLACKLIST / WHITELIST (V7.0)
// ============================================================================

function switchDomainTab(tab) {
    document.getElementById('blacklistTab').classList.toggle('hidden', tab !== 'blacklist');
    document.getElementById('whitelistTab').classList.toggle('hidden', tab !== 'whitelist');
    document.getElementById('blacklistTabBtn').classList.toggle('active', tab === 'blacklist');
    document.getElementById('whitelistTabBtn').classList.toggle('active', tab === 'whitelist');
}

async function loadDomainLists() {
    const [bl, wl] = await Promise.all([
        chrome.runtime.sendMessage({ type: 'GET_DOMAIN_BLACKLIST' }),
        chrome.runtime.sendMessage({ type: 'GET_DOMAIN_WHITELIST' })
    ]);
    renderDomainList('blacklist', bl?.list || []);
    renderDomainList('whitelist', wl?.list || []);
}

function renderDomainList(listType, list) {
    const container = document.getElementById(listType === 'blacklist' ? 'blacklistItems' : 'whitelistItems');
    if (!container) return;

    if (!list.length) {
        container.innerHTML = `<div class="domain-list-empty">Chưa có tên miền nào.</div>`;
        return;
    }

    container.innerHTML = list.map(domain => `
        <div class="domain-item">
            <span class="domain-item-text">${escapeHtml(domain)}</span>
            <button class="domain-item-remove" data-domain="${escapeHtml(domain)}"
                    data-list="${listType}" title="Xóa">✕</button>
        </div>
    `).join('');

    // Attach remove handlers
    container.querySelectorAll('.domain-item-remove').forEach(btn => {
        btn.addEventListener('click', async () => {
            const domain = btn.dataset.domain;
            const msgType = listType === 'blacklist' ? 'REMOVE_FROM_BLACKLIST' : 'REMOVE_FROM_WHITELIST';
            await chrome.runtime.sendMessage({ type: msgType, domain });
            await loadDomainLists();
        });
    });
}

async function addDomainToList(listType) {
    const inputId = listType === 'blacklist' ? 'blacklistInput' : 'whitelistInput';
    const input = document.getElementById(inputId);
    const raw = input?.value?.trim();
    if (!raw) return;

    const msgType = listType === 'blacklist' ? 'ADD_TO_BLACKLIST' : 'ADD_TO_WHITELIST';
    const result = await chrome.runtime.sendMessage({ type: msgType, domain: raw });

    if (result?.ok) {
        if (input) input.value = '';
        await loadDomainLists();
    } else {
        showStatusMessage('⚠️ ' + (result?.error || 'Không thể thêm tên miền'));
    }
}

async function importDomainList(listType) {
    const text = prompt(`Nhập danh sách tên miền (mỗi dòng một tên):\nVD: xvideos.com\ncasino.vn`);
    if (!text) return;
    const result = await chrome.runtime.sendMessage({
        type: 'IMPORT_DOMAIN_LIST',
        listType,
        text,
        replace: false
    });
    if (result?.ok) {
        showStatusMessage(`✅ Đã thêm ${result.added} tên miền (tổng: ${result.total})`);
        await loadDomainLists();
    }
}

async function exportDomainList(listType) {
    const result = await chrome.runtime.sendMessage({ type: 'EXPORT_DOMAIN_LIST', listType });
    if (!result?.text) {
        showStatusMessage('Danh sách trống, không có gì để xuất.');
        return;
    }
    const blob = new Blob([result.text], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `vcg-${listType}-${new Date().toISOString().slice(0,10)}.txt`;
    a.click();
    URL.revokeObjectURL(url);
}

// ============================================================================
// feature 7.6 — INCOGNITO LOG (V7.0)
// ============================================================================

async function renderIncognitoLog() {
    const result = await chrome.runtime.sendMessage({ type: 'GET_INCOGNITO_LOG' });
    const log = result?.log || [];
    const container = document.getElementById('incognitoLogList');
    if (!container) return;

    const badge = document.getElementById('incognitoLogCount');
    if (badge) badge.textContent = log.length;

    if (!log.length) {
        container.innerHTML = '<div style="color:var(--text-secondary);text-align:center;padding:8px;">Nhật ký trống.</div>';
        return;
    }

    container.innerHTML = log.map(entry => {
        const d = new Date(entry.time);
        const timeStr = d.toLocaleTimeString('vi-VN') + ' ' + d.toLocaleDateString('vi-VN');
        const urlShort = entry.url ? entry.url.substring(0, 50) : '(mới mở)';
        return `<div class="incognito-log-entry">
            <span class="incognito-log-time">🕵️ ${timeStr}</span>
            <span class="incognito-log-url">${escapeHtml(urlShort)}</span>
        </div>`;
    }).join('');
}

// ============================================================================
// API USAGE DASHBOARD (V7.0)
// ============================================================================

async function loadUsageDashboard() {
    const dashboard = document.getElementById('usageDashboard');
    if (!dashboard) return;

    try {
        const stats = await chrome.runtime.sendMessage({ type: 'GET_STATS' });

        if (!stats || stats.error || stats.status === '🔴 Offline' || stats.status === '🔴 Error') {
            // Server offline
            updateUsageUI({
                text: '🔴 Offline',
                percent: 0,
                color: '#e74c3c',
                keys: '--/--',
                cache: '--',
                uptime: '--'
            });
            return;
        }

        const usage = stats.usage || {};
        const keys = stats.api_keys || {};
        const cache = stats.cache || {};

        const dailyRequests = usage.daily_requests || 0;
        const dailyLimit = usage.daily_limit || 1;
        const dailyRemaining = usage.daily_remaining || 0;
        const usagePercent = usage.usage_percent || 0;
        const remainPercent = 100 - usagePercent;

        // Color coding: 🟢 >50% remaining, 🟡 20-50%, 🔴 <20%
        let color, emoji;
        if (remainPercent > 50) {
            color = '#27ae60'; emoji = '🟢';
        } else if (remainPercent > 20) {
            color = '#f39c12'; emoji = '🟡';
        } else {
            color = '#e74c3c'; emoji = '🔴';
        }

        // Format numbers — show exact count when small, 'k' only for large
        const formatNum = (n) => n >= 1000 ? (n / 1000).toFixed(1) + 'k' : String(n);

        // Cache hit rate
        const hitRate = cache.hit_rate || 'N/A';

        // Uptime format
        const uptimeSec = stats.uptime_seconds || 0;
        const uptimeStr = formatUptime(uptimeSec);

        // Show "used / limit" so small usage is visible (not "remaining / limit" which rounds the same)
        updateUsageUI({
            text: `${emoji} Đã dùng ${formatNum(dailyRequests)}/${formatNum(dailyLimit)} lượt`,
            percent: remainPercent,
            color: color,
            keys: `🔑 ${keys.available || 0}/${keys.total || 0}`,
            cache: `� ${hitRate}`,
            uptime: `⏱️ ${uptimeStr}`
        });

    } catch (err) {
        console.log('[Popup] Stats fetch error:', err.message);
        updateUsageUI({
            text: '⚠️ Không kết nối',
            percent: 0,
            color: '#95a5a6',
            keys: '--/--',
            cache: '--',
            uptime: '--'
        });
    }
}

function updateUsageUI({ text, percent, color, keys, cache, uptime }) {
    const textEl = document.getElementById('usageText');
    const fillEl = document.getElementById('usageBarFill');
    const keysEl = document.getElementById('usageKeys');
    const cacheEl = document.getElementById('usageCache');
    const uptimeEl = document.getElementById('usageUptime');

    if (textEl) { textEl.textContent = text; textEl.style.color = color; }
    if (fillEl) { fillEl.style.width = `${Math.max(0, Math.min(100, percent))}%`; fillEl.style.background = color; }
    if (keysEl) keysEl.textContent = keys;
    if (cacheEl) cacheEl.textContent = cache;
    if (uptimeEl) uptimeEl.textContent = uptime;
}

function formatUptime(seconds) {
    if (seconds < 60) return `${seconds}s`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    return m > 0 ? `${h}h${m}m` : `${h}h`;
}

// ============================================================================
// feature 7.3 — EXPLAINABLE AI EVIDENCE HELPERS
// ============================================================================

/**
 * Wraps matching toxic-span text occurrences within `commentText` with
 * <mark class="evidence-mark {severity}"> tags for in-popup highlighting.
 * Returns an HTML string safe for innerHTML (comment text is HTML-escaped
 * first, then spans are injected).
 */
function highlightEvidenceInText(commentText, evidenceSpans) {
    // Cap comment display at 180 chars
    const displayText = commentText.substring(0, 180) + (commentText.length > 180 ? '…' : '');
    if (!evidenceSpans || evidenceSpans.length === 0) {
        return `"${escapeHtml(displayText)}"`;
    }

    // Build a plain-text version and find spans to highlight
    // Work on the display-capped version
    let result = escapeHtml(displayText);

    // Sort spans longest-first to avoid nested replacements
    const sorted = [...evidenceSpans].sort((a, b) => (b.text || '').length - (a.text || '').length);

    sorted.forEach(span => {
        const raw = span.text;
        if (!raw || raw.length < 3) return;
        const sev = (span.severity || 'medium').toLowerCase();
        const escapedSpan = escapeHtml(raw);
        const title = escapeHtml(span.reason || '');
        // Replace first occurrence only in the working string
        const idx = result.indexOf(escapedSpan);
        if (idx !== -1) {
            result = result.substring(0, idx)
                + `<mark class="evidence-mark ${sev}" title="${title}">${escapedSpan}</mark>`
                + result.substring(idx + escapedSpan.length);
        }
    });

    return `"${result}"`;
}

/**
 * Renders a row of pill badges, one per evidence span,
 * for display below a toxic comment.
 */
function renderEvidenceTags(evidenceSpans) {
    if (!evidenceSpans || evidenceSpans.length === 0) return '';
    const pills = evidenceSpans.slice(0, 5).map(span => {
        const sev  = (span.severity || 'medium').toLowerCase();
        const icon = sev === 'high' ? '🔴' : sev === 'medium' ? '🟠' : '🔵';
        const text = escapeHtml((span.text || '').substring(0, 30));
        const tip  = escapeHtml(span.reason || '');
        return `<span class="evidence-tag ${sev}" title="${tip}">${icon} ${text}</span>`;
    }).join('');
    return `<div class="evidence-tags">${pills}</div>`;
}

// ============================================================================
// feature 7.9 — User Correction + Model Re-Ranking
// ============================================================================

const CORRECTION_API = 'https://vncontentguard-pro.onrender.com/api/correction';

/**
 * Populate correction panel with current scan scores and show it.
 */
function renderCorrectionPanel(data, url) {
    const panel = document.getElementById('correctionPanel');
    if (!panel) return;

    const riskScore = Math.round(data?.risk_score_v7?.risk_score || data?.risk_score || 0);
    const toxScore  = Math.round((data?.toxicity_v7?.overall_score || 0) * 100);

    const riskSlider = document.getElementById('corrRiskSlider');
    const toxSlider  = document.getElementById('corrToxSlider');
    if (riskSlider) { riskSlider.value = riskScore; document.getElementById('corrRiskVal').textContent = riskScore; }
    if (toxSlider)  { toxSlider.value = toxScore;   document.getElementById('corrToxVal').textContent = toxScore; }

    // Store original values as data attributes for submission
    panel.dataset.originalRisk = riskScore;
    panel.dataset.originalTox  = toxScore;
    panel.dataset.url           = url || currentTabUrl || '';

    panel.classList.remove('hidden');

    // Reset result message
    const resultEl = document.getElementById('corrResult');
    if (resultEl) resultEl.classList.add('hidden');
}

/**
 * Submit the user's score correction to the API.
 */
async function submitCorrection() {
    const panel = document.getElementById('correctionPanel');
    if (!panel) return;

    const url              = panel.dataset.url || currentTabUrl || '';
    const originalRisk     = parseFloat(panel.dataset.originalRisk || '0');
    const originalTox      = parseFloat(panel.dataset.originalTox  || '0') / 100;
    const correctedRisk    = parseInt(document.getElementById('corrRiskSlider')?.value || '50', 10);
    const correctedTox     = parseInt(document.getElementById('corrToxSlider')?.value  || '0', 10) / 100;
    const reason           = document.getElementById('corrReasonSelect')?.value || 'other';

    const submitBtn = document.getElementById('corrSubmitBtn');
    if (submitBtn) { submitBtn.disabled = true; submitBtn.textContent = '⏳ Đang gửi...'; }

    try {
        const resp = await fetch(CORRECTION_API, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                url,
                domain: '',
                original_risk_score: originalRisk,
                corrected_risk_score: correctedRisk,
                original_toxicity: originalTox,
                corrected_toxicity: correctedTox,
                reason,
                category: 'other',
                examples: [],
            }),
        });
        const result = await resp.json();
        const resultEl = document.getElementById('corrResult');
        if (resultEl) {
            resultEl.textContent = result.message || '✅ Đã lưu hiệu chỉnh!';
            resultEl.style.background = 'rgba(39,174,96,0.15)';
            resultEl.style.color      = '#27ae60';
            resultEl.classList.remove('hidden');
        }
        console.log('[Correction] Submitted:', result);
    } catch (e) {
        const resultEl = document.getElementById('corrResult');
        if (resultEl) {
            resultEl.textContent = '❌ Gửi thất bại — thử lại sau';
            resultEl.style.background = 'rgba(231,76,60,0.1)';
            resultEl.style.color      = '#e74c3c';
            resultEl.classList.remove('hidden');
        }
    } finally {
        if (submitBtn) { submitBtn.disabled = false; submitBtn.textContent = '📤 Gửi hiệu chỉnh'; }
    }
}

// ============================================================================
// feature 7.12 — Scam URL Prompt + Reporting
// ============================================================================

const SCAM_REPORT_API = 'https://vncontentguard-pro.onrender.com/api/report/scam';
const SCAM_TYPE_LABELS = {
    financial_phishing: 'Giả mạo ngân hàng / OTP',
    lottery_scam:       'Lừa đảo trúng thưởng',
    fake_government:    'Giả mạo cơ quan nhà nước',
    investment_scam:    'Lừa đảo đầu tư / kiếm tiền online',
    impersonation:      'Giả mạo thương hiệu',
    fake_software:      'Phần mềm giả mạo / virus',
    health_scam:        'Lừa đảo sức khỏe / thuốc giả',
    other:              'Lừa đảo không xác định',
};

/** Current scam data stored for confirm/deny handlers */
let _pendingScam = null;

/**
 * Show or hide the scam prompt card based on scam_detection data.
 */
function renderScamPrompt(scam, url) {
    const card = document.getElementById('scamPromptCard');
    if (!card) return;

    if (!scam || !scam.is_scam || parseFloat(scam.confidence || 0) < 0.55) {
        card.classList.add('hidden');
        return;
    }

    _pendingScam = { scam, url: url || currentTabUrl };

    const typeLabel   = SCAM_TYPE_LABELS[scam.scam_type] || scam.scam_type || 'Lừa đảo';
    const confPct     = Math.round(parseFloat(scam.confidence || 0) * 100);
    const detailEl    = document.getElementById('scamPromptDetail');
    const evidenceEl  = document.getElementById('scamEvidenceList');
    const resultEl    = document.getElementById('scamReportResult');

    if (detailEl) detailEl.textContent = `${typeLabel} — Độ tin cậy AI: ${confPct}%. ${scam.reasoning || ''}`;
    if (evidenceEl) {
        const phrases = (scam.evidence_phrases || []).slice(0, 3);
        evidenceEl.innerHTML = phrases.length
            ? '🔍 Bằng chứng: ' + phrases.map(p => `<em>"${escapeHtml(p)}"</em>`).join(', ')
            : '';
    }
    if (resultEl) resultEl.classList.add('hidden');

    card.classList.remove('hidden');
}

/**
 * Submit scam report (called when user clicks "Xác nhận báo cáo").
 */
async function confirmScamReport() {
    if (!_pendingScam) return;
    const { scam, url } = _pendingScam;

    const confirmBtn = document.getElementById('scamConfirmBtn');
    if (confirmBtn) { confirmBtn.disabled = true; confirmBtn.textContent = '⏳ Đang báo cáo...'; }

    try {
        const resp = await fetch(SCAM_REPORT_API, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                url: url || currentTabUrl,
                scam_type:        scam.scam_type || 'unknown',
                ai_confidence:    parseFloat(scam.confidence || 0),
                user_confirmed:   true,
                evidence_phrases: scam.evidence_phrases || [],
            }),
        });
        const result = await resp.json();
        const resultEl = document.getElementById('scamReportResult');
        if (resultEl) {
            resultEl.textContent   = result.message || `✅ Mã theo dõi: ${result.tracking_id || ''}`;
            resultEl.style.background = 'rgba(192,57,43,0.12)';
            resultEl.style.color      = '#c0392b';
            resultEl.classList.remove('hidden');
        }
        // Hide buttons after reporting
        if (confirmBtn) confirmBtn.style.display = 'none';
        const denyBtn = document.getElementById('scamDenyBtn');
        if (denyBtn) denyBtn.textContent = '✖ Đóng';
        _pendingScam = null;
        console.log('[Scam] Reported:', result);
    } catch (e) {
        const resultEl = document.getElementById('scamReportResult');
        if (resultEl) {
            resultEl.textContent = '❌ Báo cáo thất bại — thử lại sau';
            resultEl.classList.remove('hidden');
        }
    } finally {
        if (confirmBtn) { confirmBtn.disabled = false; confirmBtn.textContent = '🚨 Xác nhận báo cáo'; }
    }
}

// ============================================================================
// feature 7.13 — Bulk Analysis Mode
// ============================================================================

const BULK_API = 'https://vncontentguard-pro.onrender.com/analyze/v7/bulk';

/** Store last bulk results for CSV export */
let _lastBulkResults = null;

function toggleBulkPanel() {
    const panel = document.getElementById('bulkPanel');
    if (!panel) return;

    const isHidden = panel.classList.contains('hidden');
    // Hide other panels
    ['historyPanel','comparePanel','reportPanel','parentalPanel'].forEach(id => {
        document.getElementById(id)?.classList.add('hidden');
    });
    if (isHidden) {
        panel.classList.remove('hidden');
        document.getElementById('results').classList.add('hidden');
    } else {
        panel.classList.add('hidden');
        if (currentResultsData) document.getElementById('results').classList.remove('hidden');
    }
}

async function runBulkScan() {
    const textarea = document.getElementById('bulkUrlInput');
    const depthSel = document.getElementById('bulkDepthSelect');
    const statusEl = document.getElementById('bulkStatus');
    const resultsEl = document.getElementById('bulkResults');
    const scanBtn  = document.getElementById('bulkScanBtn');

    if (!textarea || !depthSel) return;

    const urls = textarea.value
        .split('\n')
        .map(u => u.trim())
        .filter(u => u.length > 3);

    if (urls.length === 0) {
        if (statusEl) { statusEl.textContent = '⚠️ Vui lòng nhập ít nhất 1 URL'; statusEl.classList.remove('hidden'); }
        return;
    }
    if (urls.length > 100) {
        if (statusEl) { statusEl.textContent = '⚠️ Tối đa 100 URL mỗi lần'; statusEl.classList.remove('hidden'); }
        return;
    }

    const depth = depthSel.value || 'quick';
    if (scanBtn) { scanBtn.disabled = true; scanBtn.textContent = '⏳ Đang phân tích...'; }
    if (statusEl) { statusEl.textContent = `⏳ Đang phân tích ${urls.length} URL (chế độ ${depth === 'quick' ? 'nhanh' : 'đầy đủ'})...`; statusEl.classList.remove('hidden'); }
    if (resultsEl) resultsEl.classList.add('hidden');

    try {
        const resp = await fetch(BULK_API, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ urls, scan_depth: depth }),
        });
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const data = await resp.json();
        _lastBulkResults = data;
        renderBulkResults(data);
        if (statusEl) statusEl.classList.add('hidden');
    } catch (e) {
        if (statusEl) { statusEl.textContent = `❌ Lỗi: ${e.message}`; }
    } finally {
        if (scanBtn) { scanBtn.disabled = false; scanBtn.textContent = '📊 Bắt đầu phân tích'; }
    }
}

function renderBulkResults(data) {
    const resultsEl = document.getElementById('bulkResults');
    const summaryEl = document.getElementById('bulkSummaryText');
    const tbody     = document.getElementById('bulkResultBody');
    if (!resultsEl || !tbody) return;

    const results = data.results || [];
    const highRisk = data.high_risk_count || 0;

    if (summaryEl) {
        summaryEl.textContent = `${results.length} URL — ${highRisk} rủi ro cao`;
        summaryEl.style.color = highRisk > 0 ? '#e74c3c' : '#27ae60';
    }

    tbody.innerHTML = '';
    results.forEach(r => {
        const risk     = r.risk_score || 0;
        const level    = (r.risk_level || 'Low').toLowerCase();
        const blocked  = r.blocklist_blocked ? '🚫' : '✅';
        const domain   = r.domain || (r.url || '').replace(/^https?:\/\//, '').split('/')[0];
        const shortUrl = (r.url || '').length > 40 ? (r.url || '').substring(0, 37) + '…' : (r.url || '');

        const row = document.createElement('tr');
        row.className = `risk-${level}`;
        row.innerHTML = `
            <td title="${escapeHtml(r.url || '')}"><a href="${escapeHtml(r.url || '')}" target="_blank" style="color: inherit; text-decoration: none; font-size: 10px;">${escapeHtml(shortUrl)}</a></td>
            <td><span class="bulk-risk-badge ${level}">${risk}</span></td>
            <td style="font-size: 10px;">${escapeHtml(r.risk_level || 'Low')}</td>
            <td style="font-size: 10px;">${risk > 0 ? (r.source_credibility_score || '—') : '—'}</td>
            <td style="text-align: center;">${blocked}</td>
        `;
        tbody.appendChild(row);
    });

    resultsEl.classList.remove('hidden');
}

function exportBulkCsv() {
    if (!_lastBulkResults) return;
    const rows = [
        ['URL', 'Domain', 'Risk Score', 'Risk Level', 'Blocked', 'Source Score', 'Scan Depth'],
        ...(_lastBulkResults.results || []).map(r => [
            r.url || '',
            r.domain || '',
            r.risk_score || 0,
            r.risk_level || 'Low',
            r.blocklist_blocked ? 'Yes' : 'No',
            r.source_credibility_score || '',
            r.scan_depth || '',
        ]),
    ];
    const csv = rows.map(row => row.map(cell => `"${String(cell).replace(/"/g,'""')}"`).join(',')).join('\n');
    const blob = new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8;' });
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href     = url;
    a.download = `bulk_scan_${new Date().toISOString().slice(0,10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
}

// ============================================================================
// Feature message listener — handle PROMPT_SCAM_CONFIRM from background
// ============================================================================

chrome.runtime.onMessage.addListener((message) => {
    if (message.type === 'PROMPT_SCAM_CONFIRM') {
        renderScamPrompt(message.scam, message.url);
    }
});

// ============================================================================
// SHARED HELPERS
// ============================================================================

/**
 * Trim a summary string to at most `maxSentences` complete sentences.
 * A sentence ends with . ! ? or Vietnamese ellipsis …
 * If the text is already short enough it is returned as-is.
 */
function truncateSummary(text, maxSentences = 5) {
    if (!text) return '';
    // Split on sentence-ending punctuation followed by whitespace or end-of-string
    const sentenceEnds = /[.!?…]+(?:\s|$)/g;
    const sentences = [];
    let lastIndex = 0;
    let match;
    while ((match = sentenceEnds.exec(text)) !== null) {
        sentences.push(text.slice(lastIndex, match.index + match[0].length).trim());
        lastIndex = match.index + match[0].length;
        if (sentences.length >= maxSentences) break;
    }
    if (sentences.length === 0) return text; // no sentence endings found — return as-is
    return sentences.join(' ');
}

function escapeHtml(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function showStatusMessage(msg, durationMs = 3000) {
    const el = document.getElementById('status');
    if (!el) return;
    const prev = el.textContent;
    el.textContent = msg;
    setTimeout(() => { if (el.textContent === msg) el.textContent = prev; }, durationMs);
}
