/**
 * VnContentGuard Pro v4.9 — Popup Script
 * ========================================
 * - Delegates API calls to background.js (survives popup close)
 * - Resumes scan state on popup reopen
 * - Scan history support
 * - Dark mode support
 * - Export report support
 * - Auto-scan toggle
 * - Offline regex mode with instant partial results
 * - Comparison mode
 * - User feedback loop with learning
 * - SSE Streaming results (1.5)
 * - Community report & blocklist (4.1)
 * - Parental control UI (4.2)
 * - Weekly safety report (4.4)
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

        // Check blocklist for current URL (4.1)
        checkBlocklistStatus(tab.url);

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
                    document.getElementById('status').textContent = 'Đã xóa bộ nhớ đệm — Sẵn sàng quét';
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

    // v5.0 — Auto-scan toggle handler
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

    // v5.0 — Comparison mode button handler
    const compareBtn = document.getElementById('compareBtn');
    if (compareBtn) {
        compareBtn.addEventListener('click', toggleComparePanel);
    }

    // v5.0 — Compare Go button
    const compareGoBtn = document.getElementById('compareGoBtn');
    if (compareGoBtn) {
        compareGoBtn.addEventListener('click', runComparison);
    }

    // v5.0 — Feedback button handlers
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

    // v4.9 — Report page button handler (4.1)
    const reportPageBtn = document.getElementById('reportPageBtn');
    if (reportPageBtn) {
        reportPageBtn.addEventListener('click', toggleReportPanel);
    }

    const reportSubmitBtn = document.getElementById('reportSubmitBtn');
    if (reportSubmitBtn) {
        reportSubmitBtn.addEventListener('click', submitPageReport);
    }

    // v4.9 — Weekly report button handler (4.4)
    const weeklyReportBtn = document.getElementById('weeklyReportBtn');
    if (weeklyReportBtn) {
        weeklyReportBtn.addEventListener('click', () => {
            chrome.runtime.sendMessage({ type: 'OPEN_WEEKLY_REPORT' });
        });
    }

    // v4.9 — Parental control button handler (4.2)
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
            } else {
                // Check URL cache
                chrome.storage.local.get([url], (result) => {
                    if (result[url]) {
                        currentResultsData = result[url];
                        document.getElementById('scanBtn').disabled = false;
                        document.getElementById('scanBtn').textContent = '🚀 QUÉT TRANG NÀY';
                        renderResults(result[url], url);
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

            // Update streaming progress bar if available (1.5)
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

        // Scrape content
        const scrapeResult = await chrome.scripting.executeScript({
            target: { tabId: tab.id },
            func: scrapePageContent
        });

        if (!scrapeResult || !scrapeResult[0] || !scrapeResult[0].result) {
            throw new Error("Không thể thu thập nội dung");
        }

        const scrapedData = scrapeResult[0].result;
        
        console.log(`📊 Scraped Data:`, {
            textLength: scrapedData.text.length,
            commentsCount: scrapedData.comments.length,
            hasText: scrapedData.text.length > 0
        });
        
        if (!scrapedData.text || scrapedData.text.trim().length === 0) {
            throw new Error("Không tìm thấy nội dung — trang có thể đang tải hoặc trống");
        }

        console.log(`✂️ Scraped: ${scrapedData.text.length} chars, ${scrapedData.comments.length} comments`);

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

    // Show preview
    const preview = data.text.substring(0, 200).replace(/\n\n/g, ' ').trim();
    document.getElementById('confirmPreview').textContent = preview + (data.text.length > 200 ? '...' : '');

    // Show comment count
    document.getElementById('confirmComments').textContent = data.comments.length;
}

document.getElementById('confirmYes').addEventListener('click', async () => {
    if (!scannedDataCache || !currentTabUrl) return;

    const btn = document.getElementById('confirmYes');
    btn.disabled = true;
    btn.textContent = '⏳ Đang gửi...';

    try {
        // v5.0 — Show INSTANT offline results while waiting for AI
        if (typeof offlineFullAnalysis === 'function') {
            const offlineResults = offlineFullAnalysis(scannedDataCache.text, scannedDataCache.comments, currentTabUrl);
            currentResultsData = offlineResults;
            document.getElementById('confirmation').classList.add('hidden');
            renderResults(offlineResults, currentTabUrl);
            document.getElementById('status').textContent = '⚡ Chế độ nhanh — Đang chờ AI phân tích đầy đủ...';
        }

        // Delegate to background service worker (SSE streaming mode v4.9!)
        const response = await chrome.runtime.sendMessage({
            type: 'START_SCAN_STREAM',
            data: {
                url: currentTabUrl,
                article_text: scannedDataCache.text,
                comments: scannedDataCache.comments
            }
        });

        if (response && response.status === 'started') {
            console.log("✅ Scan delegated to background service worker");

            // Show in-progress state
            document.getElementById('confirmation').classList.add('hidden');
            document.getElementById('scanBtn').disabled = true;
            document.getElementById('scanBtn').textContent = '⏳ Đang phân tích...';
            if (!currentResultsData || !currentResultsData.offline_mode) {
                document.getElementById('status').textContent = 'Đang streaming phân tích... (có thể đóng popup)';
                // Show streaming progress bar
                document.getElementById('streamProgress').classList.remove('hidden');
                updateStreamProgress(0, {});
            }

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

    if (msg.includes('localhost') || msg.includes('Failed to fetch')) {
        errorMessage.textContent = 'Chưa kết nối máy chủ\nKhởi động API: python api.py';
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

            // ===== EXTRACT COMMENTS - Handle Dynamic Content =====
            // VnExpress comments are loaded dynamically, so we look for various containers
            const commentSet = new Set();

            // Strategy 1: Look for comment container ID used by VnExpress
            const commentBox = document.getElementById('box_comment_app_inner') || 
                              document.getElementById('box_comment_vne') ||
                              document.querySelector('[data-component-type="comment_library"]') ||
                              document.querySelector('[data-component-function="showComment"]');

            if (commentBox && commentBox.innerText) {
                // If comments are loaded, extract them from container
                const commentItems = commentBox.querySelectorAll(
                    '[data-comment-id], ' +
                    '.comment-item, ' +
                    '.comment-content, ' +
                    '[class*="comment"], ' +
                    '[class*="reply"]'
                );
                
                commentItems.forEach(item => {
                    const txt = item.innerText || item.textContent;
                    if (txt && txt.length > 8 && txt.length < 1000) {
                        const trimmed = txt.trim();
                        if (!trimmed.match(/^(Like|Reply|Share|Delete|Edit|Thích|Trả lời|Chia sẻ|Xóa|Chỉnh sửa|Xem thêm)$/i) &&
                            !trimmed.match(/^\d+\s*(giờ|phút|ngày|tuần|tháng|hour|minute|day|week)$/i) &&
                            !commentSet.has(trimmed)) {
                            commentSet.add(trimmed);
                        }
                    }
                });
            }

            // Strategy 2: Look for loaded comment HTML structures
            const commentSelectors = [
                '.comment-content',
                '.comment-text',
                '.comments',
                '[data-component="comment"]',
                '.comment-item',
                '.user-comment',
                '[class*="cmt_content"]',
                '[class*="comment-body"]'
            ];

            if (commentSet.size === 0) {
                commentSelectors.forEach(selector => {
                    document.querySelectorAll(selector).forEach(el => {
                        const commentText = el.innerText || el.textContent;
                        if (commentText && commentText.length > 8 && commentText.length < 1000) {
                            const trimmed = commentText.trim();
                            if (!trimmed.match(/^(Like|Reply|Share|Delete|Edit)$/i) && !commentSet.has(trimmed)) {
                                commentSet.add(trimmed);
                            }
                        }
                    });
                });
            }

            // Strategy 3: Look for any div with substantial text in comment section
            if (commentSet.size === 0 && commentBox) {
                const allDivs = commentBox.querySelectorAll('div[class*="item"], div[class*="content"]');
                allDivs.forEach(div => {
                    const txt = div.innerText;
                    if (txt && txt.length > 15 && txt.length < 800) {
                        const trimmed = txt.trim();
                        if (!trimmed.match(/^(Like|Reply|Share|Like|Delete|Edit)$/i) && 
                            !trimmed.match(/^\d+\s*(giờ|phút|ngày|tuần|tháng|hour|minute|day|week)$/i) &&
                            !commentSet.has(trimmed) &&
                            !trimmed.includes('loading')) {
                            commentSet.add(trimmed);
                        }
                    }
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
// RESULT RENDERING WITH WARNING MODAL - v3 Enhanced
// ============================================================================

function renderResults(data, urlInfo) {
    // Check if v3 or v2 response
    const isV3 = data.version === "3.0" || data.version === "3.1" || data.version === "4.0" || data.version === "4.5" || data.version === "4.9" || data.version === "5.0" || data.sentiment_v3;
    
    // ===== RESET ALL UI STATES FIRST =====
    document.getElementById('confirmation').classList.add('hidden');
    document.getElementById('errorBox').classList.add('hidden');
    document.getElementById('warningModal').classList.add('hidden');
    
    // Show results container
    document.getElementById('results').classList.remove('hidden');

    if (isV3) {
        renderV3Results(data, urlInfo);
    } else {
        renderV2Results(data, urlInfo);
    }
}

function renderV3Results(data, urlInfo) {
    const sentiment = data.sentiment_v3 || { overall: "Neutral", confidence: 0, intensity: "Weak" };
    const toxicity = data.toxicity_v3 || { is_toxic: false, overall_score: 0, severity: "Low" };
    const factCheck = data.fact_check_v3 || { score: 50, verdict: "Unknown" };
    const riskScore = data.risk_score_v3 || { risk_score: 0, risk_level: "Low" };
    const comments = data.comments_analysis || { total: 0, toxic_count: 0, toxic_comments: [], details: [] };
    const articleSummary = data.article_summary || null;
    const isOffline = data.offline_mode === true;

    console.log("📊 Rendering v3.1 results:", { sentiment, toxicity, factCheck, riskScore, articleSummary, isOffline });

    // Hide streaming progress bar
    const streamEl = document.getElementById('streamProgress');
    if (streamEl) streamEl.classList.add('hidden');

    // Show learning indicator if AI used feedback (v4.9)
    const learningIndicator = document.getElementById('learningIndicator');
    if (learningIndicator && data.learning_applied) {
        learningIndicator.classList.remove('hidden');
        const learningCount = document.getElementById('learningCount');
        if (learningCount) learningCount.textContent = data.domain_feedback?.total || '?';
    } else if (learningIndicator) {
        learningIndicator.classList.add('hidden');
    }

    // Show blocklist warning if applicable (4.1)
    const blockWarning = document.getElementById('blocklistWarning');
    if (blockWarning && data.blocklist_info && data.blocklist_info.is_blocked) {
        blockWarning.classList.remove('hidden');
        const detail = document.getElementById('blocklistDetail');
        if (detail) detail.textContent = `${data.blocklist_info.report_count || 5}+ lượt báo cáo từ cộng đồng`;
    } else if (blockWarning) {
        blockWarning.classList.add('hidden');
    }

    // ===== 0. ARTICLE SUMMARY (NEW in v3.1) =====
    const summaryCard = document.getElementById('summaryCard');
    const summaryContent = articleSummary?.summary || articleSummary?.text || '';
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
    } else {
        summaryCard.style.display = 'none';
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

    // ===== 2. SENTIMENT v3 (PhoBERT) =====
    const sentLabel = sentiment.overall || "Neutral";
    const sentConf = sentiment.confidence || 0;
    const sentIntensity = sentiment.intensity || "Weak";
    const sentMethod = sentiment.method || "unknown";

    // Vietnamese sentiment labels
    const sentLabelVi = {
        'Positive': 'Tích cực', 'Negative': 'Tiêu cực', 'Neutral': 'Trung lập'
    };
    const sentIntensityVi = {
        'Weak': 'Yếu', 'Moderate': 'Vừa', 'Strong': 'Mạnh', 'Very Strong': 'Rất mạnh'
    };

    let sentColor = '#3498db';  // Blue for Neutral
    if (sentLabel === 'Positive') sentColor = '#27ae60';  // Green
    else if (sentLabel === 'Negative') sentColor = '#e74c3c';  // Red

    document.getElementById('sentimentStatus').innerHTML = 
        `<strong style="color: ${sentColor};">${sentLabelVi[sentLabel] || sentLabel}</strong> (độ tin cậy ${(sentConf * 100).toFixed(0)}%)`;
    
    document.getElementById('sentimentDetails').innerHTML = `
        <div style="font-size: 11px; color: #666;">
            <strong>Cường độ:</strong> ${sentIntensityVi[sentIntensity] || sentIntensity}<br/>
            <strong>Phương pháp:</strong> ${sentMethod === 'phobert' ? 'PhoBERT (AI)' : 'Phân tích từ khóa'}<br/>
            <div style="margin-top: 4px; background: #f0f0f0; border-radius: 3px; overflow: hidden;">
                <div style="width: ${sentConf * 100}%; background: ${sentColor}; height: 8px;"></div>
            </div>
        </div>
    `;

    // ===== 3. TOXICITY v3 (4-Layer) =====
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
        <div style="font-size: 11px; color: #666; margin-top: 8px;">
            <strong>Lớp phát hiện:</strong> ${(toxLayers || []).map(l => ({'regex':'Regex','gemini':'Gemini AI','perspective':'Perspective API','detoxify':'Detoxify'}[l] || l)).join(', ') || 'không'}<br/>
            <strong>Điểm:</strong> ${(toxScore * 100).toFixed(0)}%<br/>
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

    // ===== 4. FACT CHECK v3 (Multi-Source) =====
    const credScore = factCheck.score || 50;
    const verdict = factCheck.verdict || "Unknown";
    const evidence = factCheck.evidence || [];
    const verificationMethods = factCheck.verification_methods || [];

    // Vietnamese verdict labels
    const verdictVi = {
        'Verified True': 'Đã xác minh đúng', 'Likely True': 'Có thể đúng',
        'Unclear': 'Chưa rõ', 'Likely False': 'Có thể sai', 'False': 'Sai',
        'Unknown': 'Không xác định', 'Quota Limit': '⏱️ Hết hạn mức API'
    };
    const verdictDisplay = verdictVi[verdict] || verdict;

    let credColor = '#27ae60';  // Green for high credibility
    if (credScore < 70) credColor = '#f39c12';  // Orange
    if (credScore < 40) credColor = '#e74c3c';  // Red

    document.getElementById('fakeStatus').innerHTML = 
        `<strong style="color: ${credColor};">${verdictDisplay}</strong><br/>Độ tin cậy: ${credScore}/100`;
    
    document.getElementById('fakeSummary').textContent = 
        `Đã kiểm tra ${verificationMethods.length} nguồn. Tìm thấy ${evidence.length} bằng chứng.`;
    
    // Show evidence
    if (evidence.length > 0) {
        let evidenceHTML = '<div style="margin-top: 8px; padding: 8px; background: #f9f9f9; border-radius: 4px;"><strong>Bằng chứng:</strong><br/>';
        evidence.slice(0, 3).forEach(ev => {
            const detail = ev.analysis || ev.claim || ev.description || 'Không có chi tiết';
            evidenceHTML += `<div style="font-size: 10px; margin: 4px 0;">• ${ev.source || 'Không rõ'}: ${detail.substring(0, 120)}</div>`;
        });
        if (evidence.length > 3) {
            evidenceHTML += `<div style="font-size: 10px; color: #999;">... và ${evidence.length - 3} bằng chứng khác</div>`;
        }
        evidenceHTML += '</div>';
        document.getElementById('fakeEvidence').innerHTML = evidenceHTML;
    }

    // ===== 5. COMMENTS ANALYSIS v3.1 (Enhanced) =====
    const totalComments = comments.total || 0;
    const toxicCount = comments.toxic_count || 0;
    const toxicComments = comments.toxic_comments || [];
    const commentDetails = comments.details || [];
    const filterStats = comments.filter_stats || {};
    const apiCallsSaved = comments.api_calls_saved || 0;

    document.getElementById('commentsStatus').innerHTML = 
        `Đã quét: ${totalComments} bình luận | Độc hại: <strong style="color: ${toxicCount > 0 ? '#e74c3c' : '#27ae60'};">${toxicCount}</strong>` +
        (totalComments > 0 ? ` (${comments.toxic_percentage || 0}%)` : '');

    // Show API savings bar
    const savingsBar = document.getElementById('commentsApiSavings');
    if (totalComments > 0 && apiCallsSaved > 0) {
        const savingsPercent = Math.round(apiCallsSaved / totalComments * 100);
        savingsBar.style.display = 'block';
        savingsBar.innerHTML = `
            <div style="display: flex; align-items: center; gap: 6px; margin: 6px 0;">
                <span style="font-size: 11px; color: #27ae60; font-weight: bold;">⚡ Tiết kiệm ${apiCallsSaved}/${totalComments} lần gọi API (${savingsPercent}%)</span>
            </div>
            <div style="font-size: 10px; color: #888;">
                Phát hiện nhanh: ${filterStats.obvious_toxic || 0} độc hại, ${filterStats.obvious_clean || 0} sạch, ${filterStats.spam || 0} spam
                 — Gửi AI phân tích sâu: ${filterStats.sent_to_ai || 0} bình luận
            </div>
        `;
    } else {
        savingsBar.style.display = 'none';
    }
    
    if (toxicCount > 0) {
        let commentsHTML = '<div style="margin-top: 8px;">';
        toxicComments.forEach((tc, idx) => {
            if (idx < 8) {
                const sevColor = tc.severity === 'Critical' ? '#c0392b' : tc.severity === 'High' ? '#e74c3c' : '#f39c12';
                const sevLabel = severityVi[tc.severity] || tc.severity;
                const method = tc.method || 'unknown';
                const methodBadge = method === 'gemini_context' ? '🤖 AI' : method === 'regex' ? '🔍 Regex' : '📋 Bộ lọc';
                commentsHTML += `
                    <div style="margin: 6px 0; padding: 8px; background: #fff3cd; border-left: 3px solid ${sevColor}; border-radius: 3px;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span style="font-size: 10px; color: ${sevColor}; font-weight: bold;">${sevLabel} - ${(tc.score * 100).toFixed(0)}%</span>
                            <span style="font-size: 9px; color: #999; background: #f0f0f0; padding: 1px 5px; border-radius: 8px;">${methodBadge}</span>
                        </div>
                        <div style="font-size: 11px; margin-top: 3px;">"${(tc.comment || '').substring(0, 120)}${(tc.comment || '').length > 120 ? '...' : ''}"</div>
                        ${tc.reason ? `<div style="font-size: 10px; color: #666; font-style: italic; margin-top: 3px;">💡 ${tc.reason}</div>` : ''}
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

    console.log("✅ v3 results rendered");

    // ===== v4.9 — SHOW FEEDBACK SECTION (after results) =====
    const feedbackSection = document.getElementById('feedbackSection');
    if (feedbackSection && !isOffline) {
        feedbackSection.classList.remove('hidden');
        // Reset feedback state
        document.getElementById('feedbackExtra').classList.add('hidden');
        document.getElementById('feedbackThanks').classList.add('hidden');
        document.getElementById('feedbackUp').disabled = false;
        document.getElementById('feedbackDown').disabled = false;
    }

    // ===== SHOW WARNING MODAL if high risk (after delay) =====
    if (riskValue >= 50) {  // Medium-High or higher (0-100 scale)
        setTimeout(() => {
            showWarningModalV3(riskScore, sentiment, toxicity, factCheck);
        }, 12000);
    }
}

function renderV2Results(data, urlInfo) {
    const fake = data.fake_check || {};
    const sentiment = data.sentiment || { label: "Neutral", score: 0 };
    const toxicity = data.toxicity || { total: 0, toxic_count: 0, results: [] };

    // Clear v3-specific elements
    document.getElementById('riskScore').textContent = 'Chế độ v2';
    document.getElementById('riskLevel').textContent = 'Đang dùng API v2';
    document.getElementById('riskBreakdown').innerHTML = '';
    document.getElementById('sentimentDetails').innerHTML = '';
    document.getElementById('fakeEvidence').innerHTML = '';
    document.getElementById('warningsCard').style.display = 'none';
    document.getElementById('recommendationsCard').style.display = 'none';

    // Sentiment
    const sentLabelVi2 = {'Positive':'Tích cực','Negative':'Tiêu cực','Neutral':'Trung lập','Very Negative':'Rất tiêu cực','Very Positive':'Rất tích cực'};
    document.getElementById('sentimentStatus').innerHTML = 
        `<strong>${sentLabelVi2[sentiment.label] || sentiment.label}</strong> (độ tin cậy ${(sentiment.score * 100).toFixed(0)}%)`;

    // Fact check
    const riskScore = parseInt(fake.risk_score) || 0;
    let riskClass = riskScore <= 3 ? 'risk-low' : 'risk-high';
    let verdict = fake.verdict || "Unknown";
    const verdictVi2 = {'Verified True':'Đã xác minh đúng','Likely True':'Có thể đúng','Unclear':'Chưa rõ','Likely False':'Có thể sai','False':'Sai','Unknown':'Không xác định','Quota Limit':'⏱️ Hết hạn mức API'};
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

    document.getElementById('commentsStatus').innerHTML = 'Chế độ v2 (xem phần Phát hiện độc hại ở trên)';
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

function showWarningModalV3(riskScore, sentiment, toxicity, factCheck) {
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
// SCAN HISTORY — Feature 1.1
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

        html += `
            <div class="history-card" data-url="${entry.url}">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div style="flex: 1; overflow: hidden;">
                        <div style="font-size: 12px; font-weight: bold; color: var(--text-primary, #333); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                            ${entry.title || 'Unknown'}
                        </div>
                        <div style="font-size: 10px; color: var(--text-secondary, #999); margin-top: 2px;">${timeAgo}</div>
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
// EXPORT REPORT — Feature 1.2
// ============================================================================

function exportReport(data, url) {
    const isSupported = data.version === "3.0" || data.version === "3.1" || data.version === "4.0" || data.version === "4.5" || data.version === "4.9" || data.version === "5.0" || data.sentiment_v3;
    if (!isSupported) return;

    const sentiment = data.sentiment_v3 || {};
    const toxicity = data.toxicity_v3 || {};
    const factCheck = data.fact_check_v3 || {};
    const riskScore = data.risk_score_v3 || {};
    const comments = data.comments_analysis || {};
    const summary = data.article_summary || {};

    const riskLevelVi = { 'Low': 'Thấp', 'Medium': 'Trung bình', 'High': 'Cao', 'Critical': 'Nguy hiểm' };
    const sentLabelVi = { 'Positive': 'Tích cực', 'Negative': 'Tiêu cực', 'Neutral': 'Trung lập' };
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
    <p><strong>Phiên bản:</strong> v4.9</p>

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
        <p>Báo cáo được tạo bởi VnContentGuard Pro v4.9</p>
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
// USER FEEDBACK — Feature 3.3 (v5.0)
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
// COMPARISON MODE — Feature 2.5 (v5.0)
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
        const domain = entry.title || entry.url;
        const risk = Math.round(entry.riskScore);
        const opt1 = new Option(`${domain} (Rủi ro: ${risk})`, entry.url);
        const opt2 = new Option(`${domain} (Rủi ro: ${risk})`, entry.url);
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

    renderComparison(data1, data2, url1, url2);
}

function renderComparison(data1, data2, url1, url2) {
    const risk1 = data1.risk_score_v3?.risk_score || 0;
    const risk2 = data2.risk_score_v3?.risk_score || 0;
    const level1 = data1.risk_score_v3?.risk_level || 'Low';
    const level2 = data2.risk_score_v3?.risk_level || 'Low';
    const sent1 = data1.sentiment_v3?.overall || 'Neutral';
    const sent2 = data2.sentiment_v3?.overall || 'Neutral';
    const toxic1 = data1.toxicity_v3?.is_toxic || false;
    const toxic2 = data2.toxicity_v3?.is_toxic || false;
    const fact1 = data1.fact_check_v3?.score || 50;
    const fact2 = data2.fact_check_v3?.score || 50;
    const verdict1 = data1.fact_check_v3?.verdict || '?';
    const verdict2 = data2.fact_check_v3?.verdict || '?';
    const toxicCount1 = data1.comments_analysis?.toxic_count || 0;
    const toxicCount2 = data2.comments_analysis?.toxic_count || 0;
    const totalComments1 = data1.comments_analysis?.total || 0;
    const totalComments2 = data2.comments_analysis?.total || 0;

    const domain1 = getDomain(url1);
    const domain2 = getDomain(url2);

    const riskColor = (r) => r < 25 ? '#27ae60' : r < 50 ? '#f39c12' : r < 75 ? '#e74c3c' : '#c0392b';
    const sentColor = (s) => s === 'Positive' ? '#27ae60' : s === 'Negative' ? '#e74c3c' : '#3498db';
    const riskLabelVi = { 'Low': 'Thấp', 'Medium': 'TB', 'High': 'Cao', 'Critical': 'Nguy hiểm' };
    const sentLabelVi = { 'Positive': 'Tích cực', 'Negative': 'Tiêu cực', 'Neutral': 'Trung lập' };

    // Which is more reliable?
    const moreReliable = fact1 > fact2 ? domain1 : fact2 > fact1 ? domain2 : 'Ngang nhau';
    const lowerRisk = risk1 < risk2 ? domain1 : risk2 < risk1 ? domain2 : 'Ngang nhau';

    const html = `
        <div style="margin-top: 8px;">
            <table style="width: 100%; border-collapse: collapse; font-size: 11px;">
                <thead>
                    <tr style="background: var(--bg-card-hover); border-bottom: 2px solid var(--border-color);">
                        <th style="padding: 6px; text-align: left;">Tiêu chí</th>
                        <th style="padding: 6px; text-align: center; max-width: 120px; overflow: hidden; text-overflow: ellipsis;">${domain1}</th>
                        <th style="padding: 6px; text-align: center; max-width: 120px; overflow: hidden; text-overflow: ellipsis;">${domain2}</th>
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
// STREAMING PROGRESS — Feature 1.5 (v4.9)
// ============================================================================

const MODULE_NAMES = {
    summary: '📰 Tóm tắt',
    sentiment: '🎭 Cảm xúc',
    toxicity: '🛡️ Độc hại',
    fact_check: '📰 Kiểm tra TT',
    risk_score: '📊 Rủi ro',
    comments: '💬 Bình luận'
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
        text.textContent = `${count}/${total} mô-đun hoàn tất${names ? ' — ' + names : ''}`;
    }
    if (progressEl && count > 0) progressEl.classList.remove('hidden');
}

// ============================================================================
// BLOCKLIST CHECK — Feature 4.1 (v4.9)
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
// REPORT PAGE — Feature 4.1 (v4.9)
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

    const riskScore = currentResultsData?.risk_score_v3?.risk_score || 50;
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
// PARENTAL CONTROL — Feature 4.2 (v4.9)
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
    } else {
        panel.classList.add('hidden');
        if (currentResultsData) document.getElementById('results').classList.remove('hidden');
    }
}

async function saveParentalSettings() {
    const enabled = document.getElementById('parentalToggle')?.checked || false;
    const pin = document.getElementById('parentalPinInput')?.value || '0000';
    const threshold = parseInt(document.getElementById('parentalThreshold')?.value || '70');

    if (pin.length < 4) {
        alert('Mã PIN phải từ 4 ký tự trở lên.');
        return;
    }

    const result = await chrome.runtime.sendMessage({
        type: 'SET_PARENTAL_CONTROL',
        enabled: enabled,
        pin: pin,
        threshold: threshold
    });

    const statusEl = document.getElementById('status');
    if (statusEl) {
        statusEl.textContent = enabled ? `🔒 Kiểm soát gia đình: BẬT (ngưỡng ${threshold})` : '🔓 Kiểm soát gia đình: TẮT';
        setTimeout(() => { statusEl.textContent = 'Sẵn sàng quét'; }, 3000);
    }
}