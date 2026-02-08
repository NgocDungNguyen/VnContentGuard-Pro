/**
 * VnContentGuard Pro - Simple Popup Script with Persistent Storage & Warnings
 */

let currentResultsData = null;
let currentTabUrl = null;

document.addEventListener('DOMContentLoaded', async () => {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    
    if (tab) {
        currentTabUrl = tab.url;
        
        // Reset UI to clean state
        document.getElementById('results').classList.add('hidden');
        document.getElementById('confirmation').classList.add('hidden');
        document.getElementById('warningModal').classList.add('hidden');
        document.getElementById('errorBox').classList.add('hidden');
        document.getElementById('scanBtn').disabled = false;
        document.getElementById('scanBtn').textContent = '🚀 SCAN THIS PAGE';
        document.getElementById('status').textContent = 'Ready to Scan';
        
        // Check for cached results for THIS specific URL
        chrome.storage.local.get([tab.url], (result) => {
            if (result[tab.url]) {
                console.log("📂 Loading cached results for:", tab.url);
                currentResultsData = result[tab.url];
                renderResults(result[tab.url]);
            }
        });
    }

    // Clear cache button handler
    if (document.getElementById('clearCache')) {
        document.getElementById('clearCache').addEventListener('click', async () => {
            if (currentTabUrl) {
                chrome.storage.local.remove([currentTabUrl], () => {
                    console.log("🗑️ Cleared cache for:", currentTabUrl);
                    currentResultsData = null;
                    document.getElementById('results').classList.add('hidden');
                    document.getElementById('confirmation').classList.add('hidden');
                    document.getElementById('warningModal').classList.add('hidden');
                    document.getElementById('scanBtn').disabled = false;
                    document.getElementById('scanBtn').textContent = '🚀 SCAN THIS PAGE';
                    document.getElementById('status').textContent = 'Cache Cleared - Ready to Scan';
                });
            }
        });
    }
});

// ============================================================================
// SCAN BUTTON HANDLER WITH CONFIRMATION
// ============================================================================

let scannedDataCache = null;

document.getElementById('scanBtn').addEventListener('click', async () => {
    const btn = document.getElementById('scanBtn');
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

    if (!tab) return;

    btn.disabled = true;
    btn.textContent = '⏳ Scraping...';

    try {
        console.log(`📍 Scanning: ${tab.url}`);

        // Scrape content
        const scrapeResult = await chrome.scripting.executeScript({
            target: { tabId: tab.id },
            func: scrapePageContent
        });

        if (!scrapeResult || !scrapeResult[0] || !scrapeResult[0].result) {
            throw new Error("Failed to scrape");
        }

        const scrapedData = scrapeResult[0].result;
        
        console.log(`📊 Scraped Data:`, {
            textLength: scrapedData.text.length,
            commentsCount: scrapedData.comments.length,
            hasText: scrapedData.text.length > 0
        });
        
        if (!scrapedData.text || scrapedData.text.trim().length === 0) {
            throw new Error("No content found - page may be empty or loading");
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
        btn.textContent = '🚀 SCAN THIS PAGE';
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
    btn.textContent = '⏳ Analyzing...';

    try {
        // AUTO-DETECT: Try localhost first (for local testing), fallback to cloud
        const API_ENDPOINTS = [
            "http://127.0.0.1:8000/analyze/v3",     // Local server v3 (try first)
            "http://localhost:8000/analyze/v3",      // Alternative localhost v3
            "https://vncontentguard-pro.onrender.com/analyze/v3"  // Cloud v3 (fallback)
        ];

        let response = null;
        let lastError = null;
        
        for (const endpoint of API_ENDPOINTS) {
            try {
                console.log(`🔄 Trying: ${endpoint}`);
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), 5000); // 5s timeout for local
                
                response = await fetch(endpoint, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        url: currentTabUrl,
                        article_text: scannedDataCache.text,
                        comments: scannedDataCache.comments
                    }),
                    signal: controller.signal
                });
                
                clearTimeout(timeoutId);
                
                if (response.ok) {
                    console.log(`✅ Connected to: ${endpoint}`);
                    break; // Success! Stop trying other endpoints
                }
            } catch (err) {
                console.log(`❌ Failed: ${endpoint} (${err.message})`);
                lastError = err;
                response = null;
                // Continue to next endpoint
            }
        }

        if (!response || !response.ok) {
            throw new Error(lastError?.message || "All API endpoints failed");
        }

        const data = await response.json();
        console.log("✅ Got results");

        // 💾 SAVE TO PERSISTENT STORAGE with timestamp
        currentResultsData = data;
        const cacheData = {
            ...data,
            timestamp: new Date().toISOString(),
            url: currentTabUrl
        };
        chrome.storage.local.set({ [currentTabUrl]: cacheData }, () => {
            console.log("💾 Cached results for:", currentTabUrl);
        });

        // Render results (which will check for warnings first)
        renderResults(data, currentTabUrl);

    } catch (err) {
        console.error("Error:", err.message);
        showError(err.message);
    } finally {
        btn.disabled = false;
        btn.textContent = '✅ Scan';
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
        errorMessage.textContent = 'Server not connected\nStart Python API: python api.py';
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
    const isV3 = data.version === "3.0" || data.sentiment_v3;
    
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
    const sentiment = data.sentiment_v3 || { label: "Neutral", confidence: 0, intensity: "Weak" };
    const toxicity = data.toxicity_v3 || { is_toxic: false, overall_score: 0, severity: "Low" };
    const factCheck = data.fact_check_v3 || { credibility_score: 50, verdict: "Unknown" };
    const riskScore = data.risk_score_v3 || { risk_score: 0, risk_level: "Low" };
    const comments = data.comments_analysis || { total: 0, toxic_count: 0, toxic_comments: [] };

    console.log("📊 Rendering v3 results:", { sentiment, toxicity, factCheck, riskScore });

    // ===== 1. RISK SCORE (Overall) =====
    const riskValue = riskScore.risk_score || 0;
    const riskLevel = riskScore.risk_level || "Low";
    
    // Color based on risk level
    let riskColor = '#27ae60';  // Green for Low
    if (riskLevel === 'Medium') riskColor = '#f39c12';  // Orange
    else if (riskLevel === 'High') riskColor = '#e74c3c';  // Red
    else if (riskLevel === 'Critical') riskColor = '#c0392b';  // Dark Red

    document.getElementById('riskScore').innerHTML = `<span style="color: ${riskColor}">${riskValue.toFixed(1)}/10</span>`;
    document.getElementById('riskLevel').innerHTML = `<strong style="color: white;">${riskLevel} Risk</strong>`;
    
    // Risk Breakdown
    if (riskScore.risk_breakdown) {
        const breakdown = riskScore.risk_breakdown;
        let breakdownHTML = '<div style="margin-top: 10px; padding: 8px; background: rgba(255,255,255,0.1); border-radius: 4px;">';
        breakdownHTML += '<strong>Risk Breakdown:</strong><br/>';
        breakdownHTML += `Credibility: ${(breakdown.credibility || 0).toFixed(1)} | `;
        breakdownHTML += `Toxicity: ${(breakdown.toxicity || 0).toFixed(1)} | `;
        breakdownHTML += `Sentiment: ${(breakdown.sentiment || 0).toFixed(1)}<br/>`;
        breakdownHTML += `Source: ${(breakdown.source_quality || 0).toFixed(1)} | `;
        breakdownHTML += `Manipulation: ${(breakdown.manipulation || 0).toFixed(1)}`;
        breakdownHTML += '</div>';
        document.getElementById('riskBreakdown').innerHTML = breakdownHTML;
    }

    // ===== 2. SENTIMENT v3 (PhoBERT) =====
    const sentLabel = sentiment.label || "Neutral";
    const sentConf = sentiment.confidence || 0;
    const sentIntensity = sentiment.intensity || "Weak";
    const sentMethod = sentiment.method || "unknown";

    let sentColor = '#3498db';  // Blue for Neutral
    if (sentLabel === 'Positive') sentColor = '#27ae60';  // Green
    else if (sentLabel === 'Negative') sentColor = '#e74c3c';  // Red

    document.getElementById('sentimentStatus').innerHTML = 
        `<strong style="color: ${sentColor};">${sentLabel}</strong> (${(sentConf * 100).toFixed(0)}% confidence)`;
    
    document.getElementById('sentimentDetails').innerHTML = `
        <div style="font-size: 11px; color: #666;">
            <strong>Intensity:</strong> ${sentIntensity}<br/>
            <strong>Method:</strong> ${sentMethod === 'phobert' ? 'PhoBERT (AI)' : 'Keyword fallback'}<br/>
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

    let toxColor = '#27ae60';  // Green for Low
    if (toxSeverity === 'Medium') toxColor = '#f39c12';
    else if (toxSeverity === 'High') toxColor = '#e74c3c';
    else if (toxSeverity === 'Critical') toxColor = '#c0392b';

    document.getElementById('toxicStatus').innerHTML = 
        `<strong style="color: ${toxColor};">${isToxic ? '⚠️ TOXIC' : '✅ CLEAN'}</strong> - Severity: ${toxSeverity} (${(toxScore * 100).toFixed(0)}%)`;
    
    let toxDetailsHTML = `
        <div style="font-size: 11px; color: #666; margin-top: 8px;">
            <strong>Detection Layers:</strong> ${toxLayers.join(', ') || 'none'}<br/>
            <strong>Score:</strong> ${(toxScore * 100).toFixed(0)}%<br/>
    `;
    
    if (Object.keys(toxCategories).length > 0) {
        toxDetailsHTML += '<strong>Categories:</strong><br/>';
        for (const [cat, score] of Object.entries(toxCategories)) {
            if (score > 0.3) {
                toxDetailsHTML += `- ${cat}: ${(score * 100).toFixed(0)}%<br/>`;
            }
        }
    }
    toxDetailsHTML += '</div>';
    document.getElementById('toxicDetails').innerHTML = toxDetailsHTML;

    // ===== 4. FACT CHECK v3 (Multi-Source) =====
    const credScore = factCheck.credibility_score || 50;
    const verdict = factCheck.verdict || "Unknown";
    const evidence = factCheck.evidence || [];
    const sourcesChecked = factCheck.sources_checked || 0;

    let credColor = '#27ae60';  // Green for high credibility
    if (credScore < 70) credColor = '#f39c12';  // Orange
    if (credScore < 40) credColor = '#e74c3c';  // Red

    document.getElementById('fakeStatus').innerHTML = 
        `<strong style="color: ${credColor};">${verdict}</strong><br/>Credibility: ${credScore}/100`;
    
    document.getElementById('fakeSummary').textContent = 
        `Checked ${sourcesChecked} source(s). ${evidence.length} piece(s) of evidence found.`;
    
    // Show evidence
    if (evidence.length > 0) {
        let evidenceHTML = '<div style="margin-top: 8px; padding: 8px; background: #f9f9f9; border-radius: 4px;"><strong>Evidence:</strong><br/>';
        evidence.slice(0, 3).forEach(ev => {
            evidenceHTML += `<div style="font-size: 10px; margin: 4px 0;">• ${ev.source || 'Unknown'}: ${(ev.claim || ev.description || 'No details').substring(0, 80)}...</div>`;
        });
        if (evidence.length > 3) {
            evidenceHTML += `<div style="font-size: 10px; color: #999;">... and ${evidence.length - 3} more</div>`;
        }
        evidenceHTML += '</div>';
        document.getElementById('fakeEvidence').innerHTML = evidenceHTML;
    }

    // ===== 5. COMMENTS TOXICITY v3 =====
    const totalComments = comments.total || 0;
    const toxicCount = comments.toxic_count || 0;
    const toxicComments = comments.toxic_comments || [];

    document.getElementById('commentsStatus').innerHTML = 
        `Scanned: ${totalComments} comments | Toxic Found: <strong style="color: ${toxicCount > 0 ? '#e74c3c' : '#27ae60'};">${toxicCount}</strong>`;
    
    if (toxicCount > 0) {
        let commentsHTML = '<div style="margin-top: 8px;">';
        toxicComments.forEach((tc, idx) => {
            if (idx < 5) {
                const sevColor = tc.severity === 'Critical' ? '#c0392b' : tc.severity === 'High' ? '#e74c3c' : '#f39c12';
                commentsHTML += `
                    <div style="margin: 6px 0; padding: 6px; background: #fff3cd; border-left: 3px solid ${sevColor}; border-radius: 3px;">
                        <div style="font-size: 10px; color: ${sevColor}; font-weight: bold;">${tc.severity} - ${(tc.score * 100).toFixed(0)}%</div>
                        <div style="font-size: 11px; margin-top: 2px;">"${tc.comment.substring(0, 100)}..."</div>
                    </div>
                `;
            }
        });
        if (toxicCount > 5) {
            commentsHTML += `<div style="text-align: center; font-size: 10px; color: #999; margin-top: 4px;">... and ${toxicCount - 5} more</div>`;
        }
        commentsHTML += '</div>';
        document.getElementById('commentsDetails').innerHTML = commentsHTML;
    } else {
        document.getElementById('commentsDetails').innerHTML = '<div style="text-align: center; color: #27ae60; font-weight: bold; margin-top: 8px;">✅ No toxic comments detected!</div>';
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

    // ===== SHOW WARNING MODAL if high risk (after delay) =====
    if (riskValue >= 5.0) {  // Medium-High or higher
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
    document.getElementById('riskScore').textContent = 'v2 Mode';
    document.getElementById('riskLevel').textContent = 'Using v2 endpoint';
    document.getElementById('riskBreakdown').innerHTML = '';
    document.getElementById('sentimentDetails').innerHTML = '';
    document.getElementById('fakeEvidence').innerHTML = '';
    document.getElementById('warningsCard').style.display = 'none';
    document.getElementById('recommendationsCard').style.display = 'none';

    // Sentiment
    document.getElementById('sentimentStatus').innerHTML = 
        `<strong>${sentiment.label}</strong> (${(sentiment.score * 100).toFixed(0)}% confident)`;

    // Fact check
    const riskScore = parseInt(fake.risk_score) || 0;
    let riskClass = riskScore <= 3 ? 'risk-low' : 'risk-high';
    let verdict = fake.verdict || "Unknown";
    
    if (verdict === "Quota Limit") {
        verdict = "⏱️ API Quota Limit";
    }
    
    document.getElementById('fakeStatus').innerHTML = 
        `<strong class="${riskClass}">${verdict}</strong><br/>Risk: ${riskScore}/10`;
    document.getElementById('fakeSummary').textContent = fake.summary || "No summary";

    // Toxicity - Summary
    document.getElementById('toxicStatus').textContent = 
        `Scanned: ${toxicity.total} comments | Threats Found: ${toxicity.toxic_count}`;

    const toxicDetails = document.getElementById('toxicDetails');
    document.getElementById('toxicFindings').innerHTML = '';

    if (toxicity.toxic_count === 0) {
        toxicDetails.innerHTML = '<div style="text-align: center; color: #27ae60; font-weight: bold;">✅ No threats detected!</div>';
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

    document.getElementById('commentsStatus').innerHTML = 'v2 mode (see Toxicity Detection above)';
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

    let warningHTML = '';

    const riskValue = riskScore.risk_score || 0;
    const riskLevel = riskScore.risk_level || "Low";

    if (riskValue >= 5.0) {
        warningHTML += `
            <h4>⚠️ ${riskLevel} Risk Content Detected</h4>
            <p><strong>Risk Score:</strong> ${riskValue.toFixed(1)}/10</p>
            <p><strong>Level:</strong> ${riskLevel}</p>
        `;

        if (riskScore.warnings && riskScore.warnings.length > 0) {
            warningHTML += '<p><strong>Warnings:</strong></p><ul>';
            riskScore.warnings.slice(0, 3).forEach(w => {
                warningHTML += `<li>${w}</li>`;
            });
            warningHTML += '</ul>';
        }
    }

    if (toxicity.is_toxic) {
        warningHTML += `
            <h4>🛡️ Toxic Content Detected</h4>
            <p><strong>Severity:</strong> ${toxicity.severity}</p>
            <p><strong>Score:</strong> ${(toxicity.overall_score * 100).toFixed(0)}%</p>
        `;
    }

    if (factCheck.credibility_score < 40) {
        warningHTML += `
            <h4>📰 Low Credibility Warning</h4>
            <p><strong>Credibility:</strong> ${factCheck.credibility_score}/100</p>
            <p><strong>Verdict:</strong> ${factCheck.verdict}</p>
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
            <h4>📰 Potential Fake News/Misinformation</h4>
            <p><strong>Risk Level:</strong> ${fake.risk_score}/10</p>
            <p><strong>Verdict:</strong> ${fake.verdict || "High Risk"}</p>
            <p><strong>Details:</strong> ${fake.summary || "This content may contain misinformation or false claims."}</p>
        `;
    }

    // Negative sentiment warning
    if (sentiment.label === "Negative" || sentiment.label === "Very Negative") {
        warningHTML += `
            <h4>😞 Negative/Harmful Content Detected</h4>
            <p><strong>Sentiment:</strong> ${sentiment.label}</p>
            <p><strong>Confidence:</strong> ${(sentiment.score * 100).toFixed(0)}%</p>
            <p>This content has been detected as negative or potentially harmful.</p>
        `;
    }

    // Toxicity warning
    if (toxicity.toxic_count > 0) {
        const topThreats = toxicity.results
            .filter(item => item["Is Toxic"] || item["is_toxic"])
            .slice(0, 3);

        warningHTML += `
            <h4>💬 Toxic/Offensive Content Found</h4>
            <p><strong>Threats Found:</strong> ${toxicity.toxic_count} comments with issues</p>
            <p><strong>Scanned:</strong> ${toxicity.total} total comments</p>
        `;

        if (topThreats.length > 0) {
            warningHTML += '<p><strong>Examples:</strong></p><ul>';
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