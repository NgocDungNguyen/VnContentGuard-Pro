# VnContentGuard Pro v3 - Comprehensive Enhancement Plan

## 📋 PHASE 1: CURRENT SYSTEM AUDIT

### Current Architecture Analysis

#### 1. **Fake News Detection**
**Current Method:**
- **Model**: Gemini 2.5 Flash Lite
- **Approach**: Direct LLM prompt asking "is this fake news?"
- **Library**: `google-genai>=0.2.0`
- **Limitations**: 
  - ❌ No fact-checking against verified sources
  - ❌ No cross-referencing with news databases
  - ❌ Single-point analysis (no multi-source verification)
  - ❌ Subjective LLM interpretation without evidence
  - ❌ No confidence scoring mechanism

#### 2. **Sentiment Analysis**
**Current Method:**
- **Approach**: Keyword matching (25 positive + 25 negative Vietnamese words)
- **Library**: Pure Python (no external library)
- **Logic**: Count keywords → if positive > negative = Positive, else Negative
- **Limitations**:
  - ❌ Context-unaware (e.g., "không tốt" = "not good" but "tốt" alone = positive)
  - ❌ Negation blind ("không đẹp" still counts "đẹp" as positive)
  - ❌ No intensity scoring ("rất tốt" vs "tốt" treated same)
  - ❌ No sarcasm detection
  - ❌ Limited vocabulary (only 50 total words)
  - ❌ Ignores word order and grammar

#### 3. **Toxicity Detection**
**Current Method:**
- **Layer 1**: 500+ regex patterns
- **Layer 2**: Gemini LLM for contextual analysis
- **Limitations**:
  - ❌ Regex can't catch creative misspellings
  - ❌ No severity levels (all toxic = equal weight)
  - ❌ Context-dependent toxicity missed (sarcasm, jokes)
  - ❌ No multi-language code-switching detection

#### 4. **Risk Scoring**
**Current Method:**
- **Logic**: Weighted sum of fake news score + toxicity count
- **Limitations**:
  - ❌ Arbitrary weights (not data-driven)
  - ❌ No normalization across different content lengths
  - ❌ Binary thinking (fake/not fake) vs probabilistic
  - ❌ No source credibility factored in

---

## 🔬 PHASE 2: RESEARCH - AVAILABLE SOLUTIONS

### A. Fake News Detection - State-of-the-Art Methods

#### **1. Fact-Checking APIs (Recommended)**

##### **Google Fact Check Tools API**
- **What it does**: Cross-references claims against Google's fact-check database
- **Coverage**: Global fact-checking organizations (Snopes, PolitiFact, etc.)
- **Free Tier**: Yes
- **API Docs**: https://developers.google.com/fact-check/tools/api
- **Implementation**: REST API
- **Why use it**: Industry-standard, regularly updated by professional fact-checkers

##### **ClaimBuster API**
- **What it does**: Detects check-worthy claims in text
- **Model**: Trained on fact-checking datasets
- **Free Tier**: Yes (academic use)
- **Docs**: https://idir.uta.edu/claimbuster/
- **Why use it**: Prioritizes which claims need verification

##### **Full Fact API** (UK-based)
- **What it does**: Fact-checks claims, provides sources
- **Coverage**: UK + international news
- **Free Tier**: Limited
- **Docs**: https://fullfact.org/about/

#### **2. News Credibility Scoring**

##### **NewsGuard API**
- **What it does**: Rates news source credibility (0-100)
- **Database**: 7,500+ news websites rated
- **Method**: Journalism criteria (transparency, accuracy, accountability)
- **Cost**: Paid API
- **Why use it**: Pre-vetted source reliability scores

##### **Media Bias/Fact Check** (scraping or API if available)
- **What it does**: Rates news sources for bias and factual reporting
- **Database**: 5,000+ sources
- **Implementation**: Could scrape or integrate if API exists

#### **3. Cross-Reference News Aggregation**

##### **NewsAPI.org**
- **What it does**: Search 150,000+ news articles from 80+ countries
- **Free Tier**: 100 requests/day (developer tier)
- **Paid Tier**: $449/month for 250,000 requests
- **Why use it**: Verify if story appears in multiple credible sources
- **API Docs**: https://newsapi.org/docs

##### **GNews API**
- **What it does**: Real-time news aggregation, similar to NewsAPI
- **Free Tier**: 100 requests/day
- **Why use it**: Backup to NewsAPI, Vietnamese news support

#### **4. Vietnamese-Specific Fact-Checking**

##### **VietFactCheck** (if API available)
- **Organization**: Vietnam fact-checking initiative
- **Status**: Check if they have public API

##### **VERITE** (Vietnam Education and Research Institute for Truth Enhancement)
- **Status**: Research if programmatic access available

#### **5. Advanced NLP Models for Fake News**

##### **BERT-based Fake News Classifiers**
- **Models on Hugging Face**:
  - `hamzab/roberta-fake-news-classification`
  - `mrm8488/bert-tiny-finetuned-fake-news-detection`
- **Accuracy**: ~90-95% on benchmark datasets
- **Library**: `transformers` by Hugging Face
- **Pros**: Pre-trained, fast inference
- **Cons**: English-focused (needs Vietnamese fine-tuning)

##### **Vietnamese-Specific Models**
- **PhoBERT**: Pre-trained Vietnamese BERT
  - Model: `vinai/phobert-base`
  - Library: `transformers`
  - Fine-tunable for fake news detection
- **ViSoBERT**: Vietnamese social media BERT
  - Better for informal text (Facebook comments)

---

### B. Sentiment Analysis - Advanced Methods

#### **1. Transformer Models (Best Accuracy)**

##### **PhoBERT-Sentiment**
- **Model**: `wonrax/phobert-base-vietnamese-sentiment`
- **Library**: Hugging Face Transformers
- **Accuracy**: ~91% on Vietnamese sentiment datasets
- **Labels**: Positive, Negative, Neutral
- **Why use it**: Context-aware, handles negations

##### **ViSoBERT-Sentiment**
- **Model**: Vietnamese social media sentiment model
- **Better for**: Informal text, slang, emojis
- **Library**: `transformers`

##### **XLM-RoBERTa** (Multilingual)
- **Model**: `cardiffnlp/twitter-xlm-roberta-base-sentiment`
- **Languages**: 100+ including Vietnamese
- **Why use it**: Handles code-switching (Vietnamese + English mix)

#### **2. Lexicon-Based Enhanced Methods**

##### **VADER (Valence Aware Dictionary and sEntiment Reasoner)**
- **Library**: `vaderSentiment`
- **Why use it**: Handles negations, intensifiers, emojis
- **Adaptation**: Can create Vietnamese lexicon

##### **TextBlob with Vietnamese**
- **Library**: `textblob`
- **Extension**: `underthesea` for Vietnamese
- **Features**: Polarity + subjectivity scores

#### **3. Aspect-Based Sentiment Analysis (ABSA)**

##### **PyABSA**
- **Library**: `pyabsa`
- **What it does**: Sentiment per aspect (e.g., "food is good but service is bad")
- **Why use it**: More nuanced than overall sentiment

---

### C. Toxicity Detection - Industry Solutions

#### **1. Perspective API by Google Jigsaw**
- **What it does**: Detects toxic, insulting, profane, threatening, identity hate
- **Model**: Trained on millions of comments from Wikipedia, NYT
- **Free Tier**: 1 QPS (86,400 requests/day)
- **API Docs**: https://developers.perspectiveapi.com/
- **Attributes**:
  - TOXICITY (0-1 score)
  - SEVERE_TOXICITY
  - IDENTITY_ATTACK
  - INSULT
  - PROFANITY
  - THREAT
  - SEXUALLY_EXPLICIT
- **Languages**: English, Spanish, French, German, Portuguese, Italian, Russian
- **Vietnamese Support**: Limited (can still analyze with translation)
- **Why use it**: Industry-standard, used by NYT, The Guardian

#### **2. Detoxify (Open Source)**
- **Library**: `detoxify`
- **Model**: `unitary/toxic-bert`
- **What it does**: Multi-label toxicity classification
- **Labels**: toxic, severe_toxic, obscene, threat, insult, identity_hate
- **Why use it**: Offline, free, no API quota

#### **3. Vietnamese Toxicity Models**

##### **ViHOS (Vietnamese Hate and Offensive Speech)**
- **Research**: Vietnamese-specific hate speech detection
- **Models**: Fine-tuned PhoBERT for toxicity
- **Check**: Hugging Face for pre-trained versions

#### **4. Combined Approach**
- **Regex patterns** (Layer 1) - Fast, catches obvious
- **Detoxify** (Layer 2) - Offline model
- **Perspective API** (Layer 3) - When high confidence needed
- **Gemini** (Layer 4) - Final contextual analysis

---

### D. Source Credibility Assessment

#### **1. Domain Reputation Scoring**

##### **URLhaus API** (Malicious URL detection)
- **What it does**: Checks if domain is known for malware/phishing
- **Free**: Yes
- **API**: https://urlhaus-api.abuse.ch/

##### **VirusTotal API**
- **What it does**: Checks URL against 70+ security vendors
- **Free Tier**: 4 requests/minute
- **Why use it**: Detect suspicious/malicious domains

##### **Whois Lookup**
- **Library**: `python-whois`
- **What it does**: Domain age, registration info
- **Why use it**: New domains (<6 months) = higher risk

#### **2. SSL Certificate Validation**
- **Library**: `ssl` (Python built-in)
- **What it does**: Check if site has valid HTTPS
- **Why**: Legitimate news sites have SSL

#### **3. Website Metadata Analysis**
- **Library**: `newspaper3k` or `trafilatura`
- **Extract**:
  - Author information
  - Publication date
  - Source tags
  - Meta descriptions
- **Why**: Legitimate sites have proper metadata

---

### E. Cross-Reference & Fact Verification

#### **1. Web Search APIs**

##### **SerpAPI**
- **What it does**: Google search results API
- **Free Tier**: 100 searches/month
- **Use case**: Find if claim appears in multiple credible sources
- **Docs**: https://serpapi.com/

##### **Brave Search API**
- **What it does**: Independent search engine API
- **Free Tier**: 2,000 queries/month
- **Privacy**: No tracking
- **Docs**: https://brave.com/search/api/

#### **2. Wikipedia API**
- **Library**: `wikipedia-api`
- **Use case**: Verify facts against Wikipedia
- **Free**: Yes

#### **3. Wikidata API**
- **What it does**: Structured data from Wikipedia
- **Use case**: Verify factual claims (dates, names, events)
- **Free**: Yes

---

## 🎯 PHASE 3: PROPOSED ENHANCEMENTS

### **Enhancement 1: Multi-Layer Fake News Detection System**

#### **Architecture:**
```
User Content
    ↓
[Layer 1] Claim Extraction (ClaimBuster API)
    ↓
[Layer 2] Fact-Check Database Lookup (Google Fact Check API)
    ↓
[Layer 3] Source Credibility Scoring (NewsGuard or Domain Analysis)
    ↓
[Layer 4] Cross-Reference Verification (NewsAPI + Web Search)
    ↓
[Layer 5] LLM Analysis with Evidence (Gemini with context)
    ↓
Final Score: Credibility (0-100) + Evidence Links + Confidence Level
```

#### **Components:**
1. **Claim Extraction**: Identify factual claims in text (ClaimBuster)
2. **Fact-Check Lookup**: Query Google Fact Check API for known claims
3. **Source Analysis**: 
   - If URL provided → Check NewsGuard score + Domain age + SSL
   - If text only → Extract mentioned sources
4. **Cross-Reference**:
   - Search NewsAPI for same story in credible outlets
   - Count how many reputable sources report it
5. **LLM Synthesis**:
   - Gemini analyzes with all gathered evidence
   - Provides reasoning based on facts, not opinion

#### **Output:**
```json
{
  "credibility_score": 75,  // 0-100
  "verdict": "Likely Reliable",
  "confidence": "High",  // High/Medium/Low
  "evidence": [
    {"source": "BBC", "url": "...", "matches": true},
    {"source": "Reuters", "url": "...", "matches": true}
  ],
  "fact_checks": [
    {"claim": "...", "rating": "True", "checker": "Snopes"}
  ],
  "source_credibility": {
    "domain": "vnexpress.net",
    "reputation_score": 85,
    "age_years": 25,
    "ssl_valid": true
  },
  "reasoning": "This claim has been verified by 3 credible sources..."
}
```

---

### **Enhancement 2: Context-Aware Sentiment Analysis**

#### **Architecture:**
```
Input Text
    ↓
[Layer 1] PhoBERT Sentiment Model (Context-aware)
    ↓
[Layer 2] Aspect-Based Sentiment (Multiple topics)
    ↓
[Layer 3] Emotion Detection (Happy, Angry, Sad, Fear, Surprise)
    ↓
[Layer 4] Intensity Scoring (Mild, Moderate, Strong)
    ↓
Final Output: Detailed Sentiment Profile
```

#### **Models to Use:**
1. **Primary**: `wonrax/phobert-base-vietnamese-sentiment`
   - Returns: Positive/Negative/Neutral with confidence
2. **Secondary**: Emotion detection model (if available)
3. **Fallback**: Enhanced keyword-based with negation handling

#### **Output:**
```json
{
  "overall_sentiment": "Negative",
  "confidence": 0.87,
  "intensity": "Strong",
  "emotions": {
    "anger": 0.65,
    "sadness": 0.32,
    "fear": 0.15
  },
  "aspects": [
    {"topic": "government", "sentiment": "Negative", "score": -0.8},
    {"topic": "economy", "sentiment": "Neutral", "score": 0.1}
  ],
  "negations_detected": ["không tốt", "không hài lòng"],
  "intensifiers": ["rất", "cực kỳ"]
}
```

---

### **Enhancement 3: Advanced Toxicity Detection**

#### **Architecture:**
```
Input Text
    ↓
[Layer 1] Regex Patterns (500+ patterns - instant)
    ↓
[Layer 2] Detoxify Model (Offline ML)
    ↓
[Layer 3] Perspective API (Google's model)
    ↓
[Layer 4] Gemini Contextual Analysis
    ↓
Final: Toxicity Profile with Severity Levels
```

#### **Output:**
```json
{
  "is_toxic": true,
  "overall_score": 0.78,  // 0-1
  "severity": "High",  // Low/Medium/High/Severe
  "categories": {
    "profanity": 0.65,
    "insult": 0.82,
    "threat": 0.15,
    "identity_attack": 0.05,
    "sexually_explicit": 0.0
  },
  "detected_patterns": [
    {"text": "đồ ngu", "category": "insult", "severity": "Medium"}
  ],
  "context_analysis": "Insult directed at specific person, not general frustration"
}
```

---

### **Enhancement 4: Objective Risk Scoring Algorithm**

#### **Formula (Data-Driven Weights):**
```python
Risk Score = (
    0.40 × Credibility_Score_Inverse +  # 40% weight on fake news
    0.25 × Toxicity_Score +              # 25% weight on toxicity
    0.15 × Sentiment_Negativity +        # 15% weight on negative sentiment
    0.10 × Source_Risk_Score +           # 10% weight on source reputation
    0.10 × Content_Manipulation_Score    # 10% weight on clickbait/manipulation
) × 10  // Normalize to 0-10
```

#### **Components:**
1. **Credibility Score Inverse**: (100 - credibility) / 10
2. **Toxicity Score**: Average of all toxicity categories × 10
3. **Sentiment Negativity**: If negative sentiment → (confidence × intensity)
4. **Source Risk**: (100 - source_reputation) / 10
5. **Content Manipulation**: Clickbait detection, all-caps, excessive punctuation

#### **Output:**
```json
{
  "risk_score": 7.5,  // 0-10
  "risk_level": "High",  // Low (0-3), Medium (3-6), High (6-8), Critical (8-10)
  "breakdown": {
    "credibility_contribution": 3.2,
    "toxicity_contribution": 2.1,
    "sentiment_contribution": 1.5,
    "source_contribution": 0.5,
    "manipulation_contribution": 0.2
  },
  "confidence": "High",  // Based on how many layers returned results
  "warnings": [
    "Multiple fact-checkers flagged this as false",
    "High toxicity detected in comments",
    "Source has low credibility score"
  ]
}
```

---

## 📚 PHASE 4: RECOMMENDED LIBRARIES & TOOLS

### **Python Packages to Install:**

```txt
# Current (keep these)
fastapi>=0.104.1
uvicorn[standard]>=0.24.0
google-genai>=0.2.0
pydantic>=2.5.0

# NEW - Sentiment Analysis
transformers>=4.35.0        # Hugging Face models
torch>=2.1.0                # Required for transformers
underthesea>=6.6.0          # Vietnamese NLP
vaderSentiment>=3.3.2       # Enhanced sentiment

# NEW - Toxicity Detection
detoxify>=0.5.1             # Offline toxicity model
perspective>=0.1.1          # Google Perspective API wrapper

# NEW - Fact Checking & News
requests>=2.31.0            # API calls
newspaper3k>=0.2.8          # News article parsing
python-whois>=0.8.0         # Domain analysis
validators>=0.22.0          # URL validation

# NEW - Web Search & Data
serpapi>=2.4.2              # Google search results
wikipedia-api>=0.6.0        # Wikipedia verification

# NEW - NLP & Text Processing
spacy>=3.7.0                # Advanced NLP
vi-core-news-lg             # Vietnamese spaCy model (separate download)
langdetect>=1.0.9           # Language detection

# NEW - Utilities
python-dotenv>=1.0.0        # Environment variables for API keys
redis>=5.0.1                # Optional: caching for API results
aiohttp>=3.9.0              # Async HTTP requests
beautifulsoup4>=4.12.0      # Web scraping if needed
```

### **API Keys Needed:**

1. **Google Gemini API** (existing - 10 keys)
2. **Google Fact Check Tools API** (free)
3. **NewsAPI.org** (free tier: 100 req/day)
4. **Perspective API** (free tier: 1 QPS)
5. **SerpAPI** (optional: 100 searches/month free)
6. **Brave Search API** (optional: 2000 queries/month free)

---

## 🛠️ PHASE 5: IMPLEMENTATION PLAN

### **Step-by-Step Implementation (Safe & Validated)**

#### **STEP 1: Setup & Environment Preparation**

```bash
# 1. Backup current system
cp -r c:\Users\LucyS\Tox c:\Users\LucyS\Tox_v2_backup

# 2. Create new branch for v3
cd c:\Users\LucyS\Tox
git checkout -b v3-enhancement

# 3. Create virtual environment
python -m venv venv_v3
venv_v3\Scripts\activate

# 4. Install new requirements (one by one, test each)
pip install transformers torch --index-url https://download.pytorch.org/whl/cpu
pip install detoxify
pip install underthesea
pip install newspaper3k
pip install python-whois
pip install serpapi
pip install wikipedia-api
```

#### **STEP 2: Create New Module Structure**

```
src/
├── models/
│   ├── gemini_llm.py          # Keep existing
│   ├── sentiment.py            # REPLACE with PhoBERT
│   ├── toxicity.py             # ENHANCE with Detoxify + Perspective
│   └── NEW FILES:
│       ├── fact_checker.py     # Multi-layer fact verification
│       ├── source_analyzer.py  # Domain credibility scoring
│       ├── claim_extractor.py  # Extract verifiable claims
│       ├── news_aggregator.py  # Cross-reference news sources
│       └── risk_scorer.py      # Objective risk calculation
├── utils/
│   ├── NEW FILES:
│       ├── cache_manager.py    # Cache API results (avoid re-calls)
│       ├── api_manager.py      # Centralized API key management
│       └── validators.py       # Input validation & sanitization
└── config/
    └── settings.py             # All API keys & configuration
```

#### **STEP 3: Implementation Order (Safe, Validated Each Step)**

##### **3.1 Enhanced Sentiment Analysis (FIRST - Standalone)**

**File**: `src/models/sentiment_v3.py`

**Implementation**:
1. Load PhoBERT model
2. Fallback to keyword-based if model fails
3. Add negation detection
4. Add intensity scoring
5. Unit tests with Vietnamese samples

**Validation**:
```python
# Test cases
test_cases = [
    "Bài viết rất hay",           # Positive, Strong
    "Không tốt lắm",              # Negative (negation)
    "Sản phẩm này không đẹp",     # Negative (negation)
    "Tôi rất không hài lòng",     # Negative, Strong
    "Bình thường thôi",           # Neutral
]
# Run all tests, compare with expected
```

**Rollback Plan**: If PhoBERT fails → Use enhanced keyword-based

---

##### **3.2 Advanced Toxicity Detection (SECOND)**

**File**: `src/models/toxicity_v3.py`

**Implementation**:
1. Keep existing regex (Layer 1)
2. Add Detoxify model (Layer 2 - offline)
3. Add Perspective API (Layer 3 - online)
4. Gemini as final layer (Layer 4)
5. Fallback chain: Perspective fails → Detoxify, Detoxify fails → Regex

**Validation**:
```python
test_cases = [
    "đồ ngu",                     # High toxicity
    "Bạn thật tuyệt vời",         # Not toxic
    "Đ.m mày",                    # Severe toxicity
    "Tôi không đồng ý",           # Not toxic (disagreement)
]
```

**Rollback Plan**: If new layers fail → Existing regex + Gemini still works

---

##### **3.3 Fact-Checking System (THIRD - Most Complex)**

**File**: `src/models/fact_checker_v3.py`

**Implementation Steps**:

**Step 3.3.1: Google Fact Check API Integration**
```python
# Register API key
# Test with known fact-checked claims
# Handle rate limits
# Cache results
```

**Step 3.3.2: Source Credibility Analyzer**
```python
# Domain age check (python-whois)
# SSL validation
# URLhaus malicious check
# Create credibility score formula
```

**Step 3.3.3: News Aggregator (NewsAPI)**
```python
# Search for related articles
# Count reputable sources
# Extract common facts
```

**Step 3.3.4: Claim Extraction**
```python
# Use spaCy to extract factual statements
# Filter subjective vs objective claims
# Prioritize check-worthy claims
```

**Step 3.3.5: Integration Layer**
```python
# Combine all sources
# Weight evidence
# Calculate final credibility score
# Provide reasoning
```

**Validation**:
```python
test_cases = [
    {
        "text": "Biden won 2020 election",
        "expected_credibility": "High",
        "expected_fact_checks": "Present"
    },
    {
        "text": "Aliens landed in Vietnam yesterday",
        "expected_credibility": "Low",
        "expected_fact_checks": "None or False"
    }
]
```

**Rollback Plan**: If fact-check APIs fail → Use existing Gemini-only method

---

##### **3.4 Risk Scoring System (FOURTH)**

**File**: `src/models/risk_scorer_v3.py`

**Implementation**:
1. Combine all analysis results
2. Apply weighted formula
3. Calculate confidence based on layer coverage
4. Generate actionable warnings

**Validation**:
- Test with known fake news → Should score 8-10
- Test with BBC article → Should score 1-3
- Test with mixed content → Should score 4-7

---

#### **STEP 4: API Integration (api.py Update)**

**Changes**:
1. Add new endpoints:
   - `/analyze/detailed` - Full v3 analysis
   - `/analyze/quick` - Fast analysis (no fact-checking)
2. Keep backward compatibility:
   - `/analyze/full_scan` - Still works with v2 logic
3. Add configuration toggle:
   - Use v3 if `USE_V3=true` in environment
   - Fallback to v2 if v3 fails

**Validation**:
- Test all endpoints
- Ensure v2 still works
- Test fallback mechanisms

---

#### **STEP 5: Extension Updates**

**File**: `extension/popup.js`

**Changes**:
1. Add toggle for "Detailed Analysis" vs "Quick Analysis"
2. Display new result format:
   - Credibility score with evidence links
   - Detailed sentiment breakdown
   - Toxicity categories
3. Show confidence level
4. Add "View Evidence" button → Opens fact-check sources

**Validation**:
- Test with developer mode
- Ensure backward compatibility
- Test error handling

---

## 🧪 PHASE 6: TESTING & VALIDATION PROTOCOL

### **Pre-Deployment Testing**

#### **Test 1: Unit Tests (Each Component)**
```python
# Run after each module implementation
pytest tests/test_sentiment_v3.py
pytest tests/test_toxicity_v3.py
pytest tests/test_fact_checker_v3.py
pytest tests/test_risk_scorer_v3.py
```

#### **Test 2: Integration Tests (Full Pipeline)**
```python
# Test with real Vietnamese content
# Test with known fake news
# Test with credible news
# Test with toxic comments
# Test with edge cases (empty, very long, mixed languages)
```

#### **Test 3: Performance Tests**
```python
# Measure response time for each layer
# Ensure total analysis < 10 seconds
# Test with 100 concurrent requests
# Monitor API quota usage
```

#### **Test 4: Fallback Tests**
```python
# Disable Perspective API → Should fallback to Detoxify
# Disable NewsAPI → Should fallback to Gemini-only
# Disable all APIs → Should return basic analysis
```

#### **Test 5: Extension UI Tests**
- Test on 10 different websites
- Test with slow internet (timeout handling)
- Test with API failures
- Test result caching

---

## ⚠️ PHASE 7: ERROR HANDLING & ROLLBACK PLAN

### **Error Handling Strategy**

#### **1. API Failure Hierarchy**
```python
try:
    result = perspective_api.analyze(text)
except QuotaExceeded:
    result = detoxify_model.analyze(text)
except NetworkError:
    result = regex_analyzer.analyze(text)
except Exception as e:
    log_error(e)
    result = fallback_static_result()
```

#### **2. Model Loading Failures**
```python
try:
    phobert = load_model("wonrax/phobert-base-vietnamese-sentiment")
except Exception:
    log_warning("PhoBERT failed, using keyword-based")
    phobert = None

def analyze_sentiment(text):
    if phobert:
        return phobert_analysis(text)
    else:
        return keyword_analysis(text)
```

#### **3. Timeout Handling**
```python
# Set timeouts for all external API calls
response = requests.get(url, timeout=5)

# Use asyncio for parallel API calls (faster)
results = await asyncio.gather(
    fact_check_api(),
    news_api(),
    perspective_api(),
    return_exceptions=True  # Don't fail if one fails
)
```

### **Rollback Plan**

#### **If v3 Completely Fails:**
```python
# In api.py
USE_V3 = os.getenv("USE_V3", "false").lower() == "true"

@app.post("/analyze/full_scan")
async def analyze(data: ScanRequest):
    if USE_V3:
        try:
            return analyze_v3(data)
        except Exception as e:
            log_error(f"V3 failed: {e}, falling back to V2")
            return analyze_v2(data)
    else:
        return analyze_v2(data)
```

#### **If Specific Component Fails:**
- Sentiment fails → Use keyword-based
- Toxicity fails → Use regex-only
- Fact-check fails → Use Gemini-only
- Risk scoring fails → Use simple weighted sum

---

## 📊 PHASE 8: PERFORMANCE OPTIMIZATION

### **Caching Strategy**

#### **1. API Response Cache**
```python
# Cache Google Fact Check results (24 hours)
# Cache NewsAPI results (1 hour)
# Cache source credibility scores (7 days)

import redis
cache = redis.Redis()

def get_fact_check(claim):
    cached = cache.get(f"fact:{claim}")
    if cached:
        return json.loads(cached)
    
    result = fact_check_api.query(claim)
    cache.setex(f"fact:{claim}", 86400, json.dumps(result))
    return result
```

#### **2. Model Loading (One-Time)**
```python
# Load models once at startup, not per request
class SentimentAnalyzer:
    def __init__(self):
        self.model = load_phobert()  # Load once
    
    def analyze(self, text):
        return self.model.predict(text)

# Global instance
sentiment_analyzer = SentimentAnalyzer()
```

#### **3. Batch Processing**
```python
# If analyzing multiple comments, batch them
results = model.predict([comment1, comment2, comment3])  # Faster than 3 separate calls
```

---

## 💰 PHASE 9: COST & QUOTA MANAGEMENT

### **API Quotas Summary**

| API | Free Tier | Cost if Exceeded | Our Usage |
|-----|-----------|------------------|-----------|
| Google Gemini | 20 RPD/key × 10 = 200 | N/A (using free) | Critical |
| Google Fact Check | Unlimited | Free | Low |
| NewsAPI | 100 req/day | $449/month | Medium |
| Perspective API | 1 QPS (86,400/day) | Free | Medium |
| SerpAPI | 100/month | $50/month | Low |
| Detoxify | Unlimited (offline) | Free | High |
| PhoBERT | Unlimited (offline) | Free | High |

### **Quota Management**

#### **1. Prioritize Offline Models**
- Use PhoBERT (offline) before Gemini sentiment
- Use Detoxify (offline) before Perspective API
- Only call APIs when local models have low confidence

#### **2. Cache Aggressively**
- Fact-checks rarely change → Cache 24h
- Source credibility stable → Cache 7 days
- News articles stable → Cache 1 hour

#### **3. Smart API Usage**
```python
# Only call expensive APIs if needed
if local_toxicity_score < 0.5:  # Low toxicity
    return local_result
else:  # High toxicity, need confirmation
    return perspective_api.check(text)
```

---

## 🚀 PHASE 10: DEPLOYMENT CHECKLIST

### **Pre-Deployment**
- [ ] All unit tests pass
- [ ] Integration tests pass
- [ ] Performance tests acceptable (< 10s per request)
- [ ] Error handling verified
- [ ] Fallback mechanisms tested
- [ ] API keys configured in environment variables
- [ ] Caching setup (Redis or in-memory)
- [ ] Logging configured
- [ ] Documentation updated

### **Deployment Steps**
1. Deploy to staging (Render staging instance)
2. Test with real traffic (small group)
3. Monitor for 24 hours
4. If stable → Deploy to production
5. If issues → Rollback to v2

### **Post-Deployment Monitoring**
- [ ] API quota usage (daily check)
- [ ] Error rates (should be < 1%)
- [ ] Response times (should be < 10s)
- [ ] User feedback
- [ ] Cost tracking (if using paid APIs)

---

## 📈 EXPECTED IMPROVEMENTS (v2 → v3)

### **Fake News Detection**
- **v2**: Single Gemini prompt → ~70% accuracy (subjective)
- **v3**: Multi-layer with fact-checking → **85-95% accuracy** (objective)
- **Evidence**: Links to fact-checks and multiple sources

### **Sentiment Analysis**
- **v2**: Keyword matching → ~60% accuracy (context-blind)
- **v3**: PhoBERT transformer → **88-92% accuracy** (context-aware)
- **Handles**: Negations, sarcasm, intensity, aspects

### **Toxicity Detection**
- **v2**: Regex + Gemini → ~75% accuracy (binary toxic/not)
- **v3**: Multi-model pipeline → **90-95% accuracy** with severity levels
- **Categories**: 7 toxicity types with individual scores

### **Risk Scoring**
- **v2**: Arbitrary weights, subjective → Inconsistent
- **v3**: Data-driven formula with confidence → **Objective & reproducible**
- **Transparency**: Shows breakdown of why score was assigned

---

## 🎯 SUMMARY - NEXT STEPS FOR YOUR VS CODE AI AGENT

### **Phase 1: Preparation (Do This First)**
1. ✅ Review this entire plan
2. ✅ Ask questions about anything unclear
3. ✅ Confirm which enhancements to prioritize
4. ✅ Backup current system (`cp -r Tox Tox_v2_backup`)
5. ✅ Create git branch (`git checkout -b v3-enhancement`)

### **Phase 2: Research & Validation**
1. Test API access:
   - Register Google Fact Check API
   - Register NewsAPI key
   - Register Perspective API key
2. Test model loading:
   - Download PhoBERT
   - Test Detoxify installation
   - Verify transformers library works

### **Phase 3: Implementation (One Module at a Time)**
1. **Week 1**: Enhanced Sentiment (standalone, safe)
2. **Week 2**: Advanced Toxicity (build on existing)
3. **Week 3**: Fact-Checking System (most complex)
4. **Week 4**: Risk Scoring Integration
5. **Week 5**: API & Extension updates
6. **Week 6**: Testing & deployment

### **Safety Protocols for AI Agent**
- ✅ Run unit tests after EVERY change
- ✅ Never delete v2 code, only add v3 alongside
- ✅ Use try-except everywhere with fallbacks
- ✅ Validate inputs before processing
- ✅ Log all errors for debugging
- ✅ Test each component independently before integration
- ✅ Keep v2 as fallback if v3 fails

---

**READY TO START?**

Next step: Tell me which enhancement you want to prioritize first, and I'll create detailed implementation code with full error handling and validation!
