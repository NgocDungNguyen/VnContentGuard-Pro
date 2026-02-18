/**
 * VnContentGuard Pro v4.9 — Offline Regex Analyzer
 * ==
 * Instant local analysis using regex patterns + keyword sentiment.
 * Runs entirely in the extension (no backend needed).
 * Shows partial results with "⚡ Chế độ nhanh" badge while
 * waiting for full AI analysis from the server.
 *
 * Ported from:
 *   - src/models/toxicity.py (500+ regex patterns)
 *   - src/models/sentiment.py (keyword lists)
 */

// ============================================================================
// TOXICITY REGEX PATTERNS (ported from toxicity.py)
// ============================================================================

const TOXIC_PATTERNS = [
    // GROUP 1: EXTREME VIOLENCE & HARM
    { pattern: /\b(giết|chém|đâm|bắn|thủ tiêu|cắt cổ|phanh thây|tùng xẻo|thiêu sống|đục mắt|rạch mặt|xử đẹp|thanh toán|lấy mạng|kết liễu|tiễn vong|nã đạn|xả súng)\b/i, category: "Violence: Murder/Torture" },
    { pattern: /\b(kill|murder|stab|shoot|slaughter|behead|execute|strangle|lynch|dismember|decapitate|assassinate|homicide|genocide|bloodbath)\b/i, category: "Violence: Murder/Torture" },
    { pattern: /\b(tra tấn|hành hạ|giam cầm|đánh đập|bạo hành|nhục hình|móc mắt|rút móng|cắt gân|lột da|thiến)\b/i, category: "Violence: Torture" },
    { pattern: /\b(torture|torment|mutilate|flay|crucify|waterboard|maim|agony|inflict pain)\b/i, category: "Violence: Torture" },
    { pattern: /\b(máu me|xác chết|tử thi|ruột gan|đầu lâu|óc|phân huỷ|thối rữa|be bét|nát bấy|vũng máu|thi thể)\b/i, category: "Violence: Gore" },
    { pattern: /\b(gore|gory|bloody|corpse|cadaver|intestines|viscera|severed|decomposed|rotting|flesh|remains)\b/i, category: "Violence: Gore" },

    // Self-Harm & Suicide
    { pattern: /\b(tự tử|tự sát|nhảy lầu|cắt tay|uống thuốc sâu|treo cổ|rạch tay|tự vẫn|quyên sinh|kết liễu đời mình)\b/i, category: "Self-Harm/Suicide" },
    { pattern: /\b(reset game|reset server|đăng xuất khỏi trái đất|isekai|chuyển sinh|đi bán muối|ngắm gà khỏa thân|về với ông bà|nhảy cầu)\b/i, category: "Self-Harm: Slang" },
    { pattern: /\b(suicide|kill myself|end it all|cut my wrists|overdose|hang myself|slit wrists|kys|kill urself|unalive)\b/i, category: "Self-Harm/Suicide" },

    // GROUP 2: HATE SPEECH & DISCRIMINATION
    { pattern: /\b(bắc kỳ|bắc cụ|bắc bộ|parky|parkie|nón cối|barkeo|bakery|vĩ tuyến 17|bắc kỳ chó)\b/i, category: "Hate: Regional (Anti-North)" },
    { pattern: /\b(nam kỳ|nam cầy|namiki|lũ khát nước|ba que|3 que|đu càng|3 sọc|cali|kali|ngụy|bán nước|phản động)\b/i, category: "Hate: Regional (Anti-South)" },
    { pattern: /\b(trung kỳ|cá gỗ|hoa thanh quế|dân 36|dân 37|dân 18|36 37|tiểu vương quốc|vương quốc 36|thanh nghệ tĩnh|ăn rau má|phá đường tàu)\b/i, category: "Hate: Regional (Anti-Central)" },
    { pattern: /\b(lũ mán|lũ mường|lũ mọi|bọn mọi|đồ mọi)\b/i, category: "Hate: Ethnic" },
    { pattern: /\b(nigga|nigger|negro|coon|white trash|ching chong|chink|gook|curry muncher|wetback|beaner|monkey)\b/i, category: "Hate: Racism" },
    { pattern: /\b(khựa|tàu khựa|ba tàu|hàn xẻng|nhật lùn|tây ba lô|da đen|thằng đen|mũi lõ)\b/i, category: "Hate: Xenophobia" },
    { pattern: /\b(bò đỏ|bò vàng|dư lợn viên|dlv|việt tân|cờ vàng|đu dây|trại súc vật|tuyên giáo|bưng bô|nhồi sọ)\b/i, category: "Hate: Political" },

    // GROUP 3: SEXUAL & GROOMING
    { pattern: /\b(hiếp|cưỡng hiếp|hiếp dâm|hấp diêm|thông dâm|ấu dâm|loạn luân|xâm hại|cưỡng bức|pedophile|pedo)\b/i, category: "Sexual: Criminal" },
    { pattern: /\b(lồn|cặc|buồi|dái|thủ dâm|quay tay|thẩm du|bú cu|vét máng|chịch|xoạc|nện|đụ|dit|phang)\b/i, category: "Sexual: Explicit" },
    { pattern: /\b(cái lồn|cái lỗ|con cu|cái cu|bú chim|cặp vú|hai vú|bóp vú|sờ ngực|sờ mông|sờ đít|cái sò|cái khe)\b/i, category: "Sexual: Explicit Context" },
    { pattern: /\b(sugar baby|sugar daddy|sgbb|sgdd|nuôi bé|tìm bé|bao nuôi|fwb|ons|rau sạch|chăn rau|bố đường|bé đường|tuyển pg|đi khách)\b/i, category: "Sexual: Grooming" },

    // GROUP 4: PROFANITY & INSULTS
    { pattern: /\b(đm|đkm|đmm|vcl|vkl|vch|vcc|vđ|đéo|đếch|cc|ccc|cl|đmcm|đcm|dcm|dkm|đjt|đis|đù|bỏ mẹ|tổ sư|cha tiên sư)\b/i, category: "Profanity: VN" },
    { pattern: /\b(con mẹ mày|thằng cha mày|cả lò nhà mày|mả cha mày|tiên sư bố|cái mả mẹ|đồ chết tiệt)\b/i, category: "Profanity: Family Insults" },
    { pattern: /\b(ngu\s+si|ngu\s+ngốc|ngu\s+vl|ngu\s+vcl|đồ\s+ngu|thằng\s+ngu|con\s+ngu|ngu\s+lắm|ngu\s+quá)\b/i, category: "Insult: Intelligence" },
    { pattern: /\b(óc chó|óc lợn|óc bò|thiểu năng|bại não|khuyết tật|tự kỷ|ngáo|ngáo đá|ngáo ngơ|não tàn|vô học|mất dạy)\b/i, category: "Insult: Intelligence" },
    { pattern: /\b(phò|đĩ|cave|điếm|con giáp thứ 13|tiểu tam|trà xanh|hãm|đũa mốc|xấu ma chê|mặt phụ khoa)\b/i, category: "Insult: Appearance" },
    { pattern: /\b(fuck|shit|bitch|cunt|dick|cock|asshole|whore|slut|bastard|motherfucker|douchebag|wanker|prick|twat)\b/i, category: "Profanity: EN" },

    // GROUP 5: SCAM, SPAM & THREATS
    { pattern: /\b(cờ bạc|tài xỉu|nổ hũ|kèo bóng|bet88|kubet|nhà cái|casino|lô đề|xóc đĩa|bắn cá|đá gà|soi cầu|chốt số|bạch thủ|vip pro)\b/i, category: "Spam: Gambling" },
    { pattern: /\b(việc nhẹ lương cao|tuyển dụng gấp|không cọc|hoa hồng cao|kiếm tiền online|nhập liệu|xâu hạt|gấp phong bì|làm tại nhà|thu nhập khủng)\b/i, category: "Spam: Job Scam" },
    { pattern: /\b(chứng khoán quốc tế|sàn ảo|tiền ảo|lùa gà|pump dump|đa cấp|mô hình ponzi|hoàn vốn nhanh|cam kết lợi nhuận)\b/i, category: "Spam: Financial Scam" },
    { pattern: /\b(tao giết|tao đánh|ra đường cẩn thận|biết bố mày là ai không|gọi hội|xử mày|đập nát|đốt nhà|xin cái tay|xin cái chân)\b/i, category: "Threat: Violence" },
    { pattern: /\b(watch your back|gonna kill you|beat you up|hunt you down|you're dead|fight me|meet me outside)\b/i, category: "Threat: Violence" },
];

// ============================================================================
// SENTIMENT KEYWORDS (ported from sentiment.py)
// ============================================================================

const POSITIVE_WORDS = [
    "tốt", "hay", "đẹp", "tuyệt", "xuất sắc", "hoàn hảo", "thích", "yêu",
    "vui", "hạnh phúc", "tốt lành", "hữu ích", "tích cực", "thành công",
    "cảm ơn", "tuyệt vời", "tốt đẹp", "ưu việt", "đáng yêu", "chất lượng",
    "tâm lý", "hiệu quả", "hài lòng", "thỏa mãn", "tin tưởng", "uy tín",
    "giỏi", "tài năng", "xuất chúng", "phi thường", "ấn tượng", "tận tâm",
    "chuyên nghiệp", "trách nhiệm", "đáng tin", "minh bạch", "công bằng"
];

const NEGATIVE_WORDS = [
    "tệ", "xấu", "kém", "dở", "tồi", "ghét", "chán", "buồn", "thất vọng",
    "thảm họa", "tối tệ", "vô dụng", "lừa đảo", "gian lận", "khủng khiếp",
    "thất bại", "tệ hại", "không tốt", "rác", "phí tiền", "không đáng",
    "nguy hiểm", "đáng sợ", "kinh hoàng", "lo lắng", "sợ hãi", "phẫn nộ",
    "bất công", "thiên vị", "sai lệch", "tin giả", "giả mạo", "bịa đặt",
    "tham nhũng", "oan sai", "bức xúc", "phản đối", "tẩy chay"
];

// ============================================================================
// OFFLINE ANALYSIS FUNCTIONS
// ============================================================================

/**
 * Analyze article text for toxicity using regex patterns.
 * @param {string} text - Article text
 * @returns {object} Toxicity analysis result
 */
function offlineAnalyzeToxicity(text) {
    if (!text || text.length < 5) {
        return { is_toxic: false, overall_score: 0, severity: "None", categories: {}, detection_layers: ["offline_regex"], matches: [] };
    }

    const lower = text.toLowerCase();
    const matches = [];
    const categories = {};

    for (const { pattern, category } of TOXIC_PATTERNS) {
        const match = lower.match(pattern);
        if (match) {
            matches.push({ keyword: match[0], category });
            categories[category] = (categories[category] || 0) + 1;
        }
    }

    const is_toxic = matches.length > 0;
    const score = Math.min(1.0, matches.length * 0.2);
    let severity = "None";
    if (score >= 0.8) severity = "Critical";
    else if (score >= 0.5) severity = "High";
    else if (score >= 0.3) severity = "Medium";
    else if (score > 0) severity = "Low";

    return {
        is_toxic,
        overall_score: score,
        severity,
        categories,
        detection_layers: ["offline_regex"],
        matches: matches.slice(0, 5)
    };
}

/**
 * Analyze text sentiment using keyword matching.
 * @param {string} text - Article text
 * @returns {object} Sentiment result
 */
function offlineAnalyzeSentiment(text) {
    if (!text || text.length < 5) {
        return { overall: "Neutral", confidence: 0, intensity: "Weak", method: "offline_keywords" };
    }

    const lower = text.toLowerCase();
    let posCount = 0, negCount = 0;

    for (const word of POSITIVE_WORDS) {
        if (lower.includes(word)) posCount++;
    }
    for (const word of NEGATIVE_WORDS) {
        if (lower.includes(word)) negCount++;
    }

    const total = posCount + negCount;
    if (total === 0 || total === 1) {
        return { overall: "Neutral", confidence: 0.3, intensity: "Weak", method: "offline_keywords" };
    }

    let label, confidence, intensity;
    if (posCount > negCount) {
        label = "Positive";
        confidence = posCount / total;
    } else if (negCount > posCount) {
        label = "Negative";
        confidence = negCount / total;
    } else {
        label = "Neutral";
        confidence = 0.5;
    }

    if (confidence >= 0.8) intensity = "Very Strong";
    else if (confidence >= 0.6) intensity = "Strong";
    else if (confidence >= 0.4) intensity = "Moderate";
    else intensity = "Weak";

    return { overall: label, confidence: Math.round(confidence * 100) / 100, intensity, method: "offline_keywords" };
}

/**
 * Analyze comments for toxicity using regex patterns.
 * @param {string[]} comments - Array of comment strings
 * @returns {object} Comment analysis result
 */
function offlineAnalyzeComments(comments) {
    if (!comments || comments.length === 0) {
        return { total: 0, toxic_count: 0, toxic_percentage: 0, toxic_comments: [], details: [] };
    }

    const details = [];
    let toxicCount = 0;

    for (const comment of comments) {
        const lower = (comment || "").toLowerCase();
        let isToxic = false;
        let matchedCategory = "";
        let matchedKeyword = "";

        for (const { pattern, category } of TOXIC_PATTERNS) {
            const match = lower.match(pattern);
            if (match) {
                isToxic = true;
                matchedCategory = category;
                matchedKeyword = match[0];
                break;
            }
        }

        const result = {
            comment: comment.substring(0, 200),
            is_toxic: isToxic,
            severity: isToxic ? "High" : "None",
            score: isToxic ? 0.8 : 0.0,
            sentiment: "neutral",
            method: "offline_regex",
            reason: isToxic ? `Phát hiện: "${matchedKeyword}" (${matchedCategory})` : "Không phát hiện vấn đề (chế độ nhanh)",
            categories: {}
        };

        if (isToxic) toxicCount++;
        details.push(result);
    }

    return {
        total: comments.length,
        toxic_count: toxicCount,
        toxic_percentage: comments.length > 0 ? Math.round(toxicCount / comments.length * 1000) / 10 : 0,
        toxic_comments: details.filter(d => d.is_toxic).slice(0, 10),
        details,
        filter_stats: { offline_regex: comments.length },
        api_calls_saved: comments.length
    };
}

/**
 * Run full offline analysis on scraped content.
 * Returns a result object in the same format as /analyze/v4 API.
 * @param {string} articleText - Article text
 * @param {string[]} comments - Comment array
 * @param {string} url - Page URL
 * @returns {object} Full analysis result (offline)
 */
function offlineFullAnalysis(articleText, comments, url) {
    const toxicity = offlineAnalyzeToxicity(articleText);
    const sentiment = offlineAnalyzeSentiment(articleText);
    const commentAnalysis = offlineAnalyzeComments(comments);

    // Calculate a basic risk score
    let riskScore = 0;
    if (toxicity.is_toxic) riskScore += 30;
    if (sentiment.overall === "Negative") riskScore += 15;
    if (commentAnalysis.toxic_count > 0) {
        riskScore += Math.min(30, commentAnalysis.toxic_count * 5);
    }
    riskScore = Math.min(100, riskScore);

    let riskLevel = "Low";
    if (riskScore >= 75) riskLevel = "Critical";
    else if (riskScore >= 50) riskLevel = "High";
    else if (riskScore >= 25) riskLevel = "Medium";

    return {
        version: "5.0",
        offline_mode: true,
        article_summary: {
            summary: "⚡ Chế độ nhanh — Đang chờ phân tích AI đầy đủ...",
            method: "offline",
            cached: false
        },
        sentiment_v4: sentiment,
        toxicity_v4: toxicity,
        fact_check_v4: {
            score: 50,
            verdict: "Chờ AI",
            confidence: "Low",
            evidence: [],
            verification_methods: ["offline_pending"]
        },
        risk_score_v4: {
            risk_score: riskScore,
            risk_level: riskLevel,
            confidence: 0.3,
            breakdown: {
                fake_news_component: 0,
                toxicity_component: toxicity.is_toxic ? 30 : 0,
                sentiment_component: sentiment.overall === "Negative" ? 15 : 0,
                source_component: 0,
                manipulation_component: 0
            },
            warnings: toxicity.is_toxic ? ["⚡ Phát hiện nội dung độc hại (chế độ nhanh)"] : [],
            recommendations: ["Đợi phân tích AI đầy đủ để có kết quả chính xác hơn"]
        },
        comments_analysis: commentAnalysis,
        url: url
    };
}
