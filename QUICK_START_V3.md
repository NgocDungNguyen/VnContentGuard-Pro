# VnContentGuard Pro v3 - Quick Start Guide

**Get up and running in 5 minutes** ⚡

---

## ⚙️ Prerequisites

Before you begin, ensure you have:

✅ Python 3.9+ installed  
✅ Git installed  
✅ 4GB+ RAM available  
✅ 2.5GB+ free disk space  
✅ API keys ready (20 Gemini + 4 external APIs)

---

## 🚀 Installation (5 Steps)

### Step 1: Clone & Navigate

```bash
git clone https://github.com/yourusername/vncontentguard-pro.git
cd vncontentguard-pro
git checkout v3-enhancement
```

### Step 2: Create Virtual Environment

```bash
# Create venv
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Linux/Mac)
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

⏱️ **Wait time:** 5-10 minutes (downloads PhoBERT ~500MB + Detoxify ~1GB on first run)

### Step 4: Configure Environment

Create `.env` file in project root:

```bash
# Gemini API Keys (20 total)
GEMINI_API_KEY_1=AIzaSy...your-key-1
GEMINI_API_KEY_2=AIzaSy...your-key-2
GEMINI_API_KEY_3=AIzaSy...your-key-3
# ... (add keys 4-20)

# External APIs
GOOGLE_FACT_CHECK_API_KEY=AIzaSyC...your-key
GOOGLE_PERSPECTIVE_API_KEY=AIzaSyC...your-key
NEWSDATA_API_KEY=pub_...your-key
GNEWS_API_KEY=e3dc0...your-key
```

💡 **Tip:** Copy from `.env.example` if available

### Step 5: Verify Installation

```bash
pytest -v
```

✅ **Expected output:** `96 passed, 2 warnings in ~2 minutes`

---

## 🎮 Usage Examples

### Run Local Server

```bash
python api.py
```

Server starts at: `http://localhost:8000`

### Test Health Endpoint

```bash
curl http://localhost:8000/health
```

### Analyze Vietnamese Text

```bash
curl -X POST http://localhost:8000/analyze/v3 \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Tin này hoàn toàn sai sự thật! Cảnh báo mọi người!",
    "url": "https://example.com"
  }'
```

### Run Specific Component

```python
# Sentiment Analysis
from src.models.sentiment_v3 import analyze_sentiment_v3
result = analyze_sentiment_v3("Tôi rất hài lòng với sản phẩm này!")
print(result)
# Output: {'label': 'Positive', 'confidence': 0.92, 'intensity': 'Strong'}

# Toxicity Detection
from src.models.toxicity_v3 import detect_toxicity_v3
result = detect_toxicity_v3("Đây là văn bản bình thường")
print(result)
# Output: {'is_toxic': False, 'overall_score': 0.1, 'severity': 'Low'}

# Fact-Checking
from src.models.fact_checker_v3 import check_facts_v3
result = check_facts_v3("COVID-19 vaccine caused 5G", "https://example.com")
print(result)
# Output: {'credibility_score': 15, 'verdict': 'Mostly False', ...}

# Risk Scoring (Full Pipeline)
from src.models.risk_scorer_v3 import calculate_risk_score_v3
result = calculate_risk_score_v3("Clickbait tin giả đầy độc hại!", "https://spam.com")
print(result)
# Output: {'risk_score': 7.8, 'risk_level': 'Critical', ...}
```

---

## 🧪 Testing

### Run All Tests

```bash
pytest -v
```

### Run Specific Module

```bash
pytest tests/test_sentiment_v3.py -v
pytest tests/test_toxicity_v3.py -v
pytest tests/test_fact_checking_v3.py -v
pytest tests/test_risk_scorer_v3.py -v
```

### Run with Coverage

```bash
pytest --cov=src --cov-report=html
open htmlcov/index.html
```

---

## 🌐 Chrome Extension Setup

### Step 1: Load Extension

1. Open Chrome browser
2. Navigate to `chrome://extensions/`
3. Enable "Developer mode" (top-right toggle)
4. Click "Load unpacked"
5. Select `vncontentguard-pro/extension` folder

### Step 2: Test Extension

1. Click extension icon in toolbar
2. Paste Vietnamese text in textarea
3. Click "Analyze Content"
4. View results (sentiment, toxicity, risk score)

### Step 3: Update API Endpoint (Optional)

If using custom endpoint:

```javascript
// extension/popup.js (line 5)
const API_URLS = [
    'http://localhost:8000/analyze/v3',
    'http://127.0.0.1:8000/analyze/v3',
    'https://your-custom-domain.com/analyze/v3'
];
```

---

## 🚨 Common Issues & Fixes

### Issue: "ModuleNotFoundError: No module named 'transformers'"

**Fix:**
```bash
pip install --upgrade -r requirements.txt
```

---

### Issue: "OSError: Can't load model 'wonrax/phobert-base-vietnamese-sentiment'"

**Fix:**
```bash
# Clear cache and retry
rm -rf ~/.cache/huggingface/
python -c "from transformers import AutoModel; AutoModel.from_pretrained('wonrax/phobert-base-vietnamese-sentiment')"
```

---

### Issue: "429 Quota Exceeded" on Gemini

**Fix:**
- Wait for quota reset (00:00 UTC daily)
- Ensure all 20 keys are in `.env`
- System auto-rotates keys

---

### Issue: Slow First Run (~30 seconds)

**Reason:** Model loading (PhoBERT + Detoxify = 1.5GB)

**Solution:** Normal behavior. Subsequent calls are fast (~200-500ms).

---

### Issue: Tests Failing

**Fix:**
```bash
# Verify Python version
python --version  # Should be 3.9+

# Reinstall dependencies
pip install --upgrade pip
pip install --upgrade -r requirements.txt

# Run tests again
pytest -v
```

---

## 📚 Next Steps

1. ✅ Read full documentation: `VNCONTENTGUARD_V3_COMPLETE_SYSTEM_DOCUMENTATION.md`
2. ✅ Review version comparison: `VERSION_COMPARISON_REPORT.md`
3. ✅ Explore v3 enhancement plan: `VNCONTENTGUARD_V3_ENHANCEMENT_PLAN.md`
4. ✅ Check archived v2 docs: `archive/v2_docs/`
5. ✅ Deploy to production (see deployment section in full docs)

---

## 🎯 Key Commands Reference

| Command | Purpose |
|---------|---------|
| `python api.py` | Start local server |
| `pytest -v` | Run all tests |
| `pytest --cov=src` | Test coverage |
| `git status` | Check changes |
| `git log --oneline` | View commits |

---

## 💡 Pro Tips

✅ Use `pytest -k "test_name"` to run specific test  
✅ Set `TRANSFORMERS_VERBOSITY=error` to reduce logs  
✅ Use `pytest -x` to stop on first failure  
✅ Check `.env.example` for required variables  
✅ Monitor API usage: `grep "API_KEY" logs/app.log`

---

## 📞 Need Help?

- 📖 **Full Docs:** `VNCONTENTGUARD_V3_COMPLETE_SYSTEM_DOCUMENTATION.md`
- 🐛 **Report Issues:** GitHub Issues tab
- 💬 **Discussions:** GitHub Discussions
- 📧 **Email:** support@vncontentguard.com (if available)

---

**Document Version:** 1.0  
**Last Updated:** February 8, 2026  
**Estimated Setup Time:** 5-10 minutes  
**Difficulty:** Beginner-friendly 🟢
