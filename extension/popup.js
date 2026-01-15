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
        // Send to API
        const response = await fetch("https://vncontentguard-pro.onrender.com/analyze/full_scan", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                url: currentTabUrl,
                article_text: scannedDataCache.text,
                comments: scannedDataCache.comments
            }),
            timeout: 30000
        });

        if (!response.ok) {
            throw new Error(`API error: ${response.status}`);
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
// RESULT RENDERING WITH WARNING MODAL
// ============================================================================

function renderResults(data, urlInfo) {
    const fake = data.fake_check || {};
    const sentiment = data.sentiment || { label: "Neutral", score: 0 };
    const toxicity = data.toxicity || { total: 0, toxic_count: 0, results: [] };

    // ===== RESET ALL UI STATES FIRST =====
    document.getElementById('confirmation').classList.add('hidden');
    document.getElementById('errorBox').classList.add('hidden');
    document.getElementById('warningModal').classList.add('hidden');
    
    // Clear all content areas to prevent overlap
    document.getElementById('sentimentStatus').innerHTML = '';
    document.getElementById('fakeStatus').innerHTML = '';
    document.getElementById('fakeSummary').textContent = '';
    document.getElementById('toxicStatus').textContent = '';
    document.getElementById('toxicDetails').innerHTML = '';
    document.getElementById('toxicFindings').innerHTML = '';

    // ===== CHECK IF CONTENT IS FLAGGED AS RISKY =====
    const riskScore = parseInt(fake.risk_score) || 0;
    const sentimentLabel = sentiment.label || "Neutral";
    const isFakeNews = riskScore >= 6; // Risk score 6+ is high risk
    const isNegativeSentiment = sentimentLabel === "Negative" || sentimentLabel === "Very Negative";
    const hasToxicity = toxicity.toxic_count > 0;
    const isRisky = isFakeNews || isNegativeSentiment || hasToxicity;

    // ===== ALWAYS SHOW RESULTS FIRST (don't return) =====
    document.getElementById('results').classList.remove('hidden');

    // Sentiment
    document.getElementById('sentimentStatus').innerHTML = 
        `<strong>${sentiment.label}</strong> (${(sentiment.score * 100).toFixed(0)}% confident)`;

    // Fact check
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
    const toxicFindings = document.getElementById('toxicFindings');

    if (toxicity.toxic_count === 0) {
        toxicDetails.innerHTML = '<div style="text-align: center; color: #27ae60; font-weight: bold;">✅ No threats detected!</div>';
    } else {
        // Build findings list
        let findingsHTML = '<strong style="color: #c0392b; display: block; margin-bottom: 6px;">🚨 Detected Toxicity:</strong>';
        let detailsHTML = '';
        
        toxicity.results.forEach((item, idx) => {
            if ((item["Is Toxic"] || item["is_toxic"]) && idx < 20) {
                const category = item.Category || item.category || "Unknown";
                const comment = item.Comment || item.comment || "";
                const confidence = (item.Confidence || item.confidence || 0);
                const confPercent = (confidence * 100).toFixed(0);

                // Add to findings (main display)
                findingsHTML += `
                    <div class="finding-item">
                        <div class="finding-category">🚨 ${category}</div>
                        <div class="finding-text">"${comment.substring(0, 80)}${comment.length > 80 ? '...' : ''}"</div>
                        <div class="finding-confidence">Confidence: ${confPercent}%</div>
                    </div>
                `;

                // Add to details as well
                let badgeColor = '#e74c3c';
                if (category.includes("Hate") || category.includes("Regional") || category.includes("Discrimination")) badgeColor = '#f39c12';
                else if (category.includes("Sexual")) badgeColor = '#9b59b6';
                else if (category.includes("Scam") || category.includes("Advertising")) badgeColor = '#27ae60';

                detailsHTML += `
                    <div class="toxic-item">
                        <span class="badge" style="background: ${badgeColor}">${category}</span>
                        <span style="font-size: 10px; color: #999;">${confPercent}%</span>
                        <div style="margin-top: 4px; font-size: 11px; color: #555;">"${comment.substring(0, 60)}${comment.length > 60 ? '...' : ''}"</div>
                    </div>
                `;
            }
        });

        if (toxicity.toxic_count > 20) {
            findingsHTML += `<div style="text-align: center; font-size: 11px; color: #999; margin-top: 8px;">... and ${toxicity.toxic_count - 20} more</div>`;
        }

        toxicFindings.innerHTML = findingsHTML;
        toxicDetails.innerHTML = detailsHTML;
    }

    console.log("✅ Rendered");

    // ===== SHOW WARNING MODAL AFTER RESULTS ARE RENDERED (10-15 second delay) =====
    if (isRisky) {
        setTimeout(() => {
            showWarningModal(fake, sentiment, toxicity);
        }, 12000); // 12 second delay for user to read results
    }
}

// ============================================================================
// WARNING MODAL HANDLER
// ============================================================================

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