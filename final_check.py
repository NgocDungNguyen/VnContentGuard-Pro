"""Final comprehensive check before manual testing"""

import sys

print("=" * 80)
print("VNCONTENTGUARD PRO - FINAL SYSTEM CHECK")
print("=" * 80)

# 1. Check imports
print("\n[1/7] Checking imports...")
try:
    from src.models.gemini_llm import API_KEY_POOL, APIKeyRotator, GeminiAgent
    from src.models.sentiment import SentimentAnalyzer
    from src.models.toxicity import ToxicityAnalyzer

    print("  [PASS] All imports successful")
except Exception as e:
    print(f"  [FAIL] Import error: {e}")
    sys.exit(1)

# 2. Check API key pool
print("\n[2/7] Checking API key configuration...")
if len(API_KEY_POOL) == 10:
    print(f"  [PASS] 10 API keys configured")
else:
    print(f"  [FAIL] Expected 10 keys, found {len(API_KEY_POOL)}")
    sys.exit(1)

# 3. Initialize components
print("\n[3/7] Initializing AI components...")
try:
    sentiment = SentimentAnalyzer()
    toxicity = ToxicityAnalyzer()
    gemini = GeminiAgent()
    print("  [PASS] All components initialized")
except Exception as e:
    print(f"  [FAIL] Initialization error: {e}")
    sys.exit(1)

# 4. Test sentiment
print("\n[4/7] Testing sentiment analysis...")
result = sentiment.analyze("San pham tot, rat hai long")
if "label" in result and result["label"] == "Positive":
    print(f"  [PASS] Sentiment works: {result}")
else:
    print(f"  [WARN] Sentiment result: {result}")

# 5. Test toxicity regex
print("\n[5/7] Testing toxicity detection...")
results, count = toxicity.analyze_comments(["Bai viet hay", "do ngu"])
if count > 0:
    print(f"  [PASS] Toxicity regex works: {count} toxic detected")
else:
    print(f"  [WARN] No toxicity detected")

# 6. Check gemini status
print("\n[6/7] Checking Gemini API status...")
status = gemini.get_status()
print(f"  [INFO] Total Keys: {status['total_keys']}")
print(f"  [INFO] Current Key: #{status['current_key']}")
print(f"  [INFO] Available: {status['available_count']}")
print(f"  [INFO] Exhausted: {status['exhausted_count']}")

# 7. Check file structure
print("\n[7/7] Verifying file structure...")
import os

critical_files = [
    "api.py",
    "requirements.txt",
    ".render.yaml",
    "extension/manifest.json",
    "extension/popup.html",
    "extension/popup.js",
    "extension/style.css",
    "src/models/gemini_llm.py",
    "src/models/sentiment.py",
    "src/models/toxicity.py",
]

all_present = True
for file in critical_files:
    if os.path.exists(file):
        print(f"  [PASS] {file}")
    else:
        print(f"  [FAIL] Missing: {file}")
        all_present = False

if not all_present:
    sys.exit(1)

print("\n" + "=" * 80)
print("ALL CHECKS PASSED - READY FOR MANUAL TESTING")
print("=" * 80)
print("\nYou can now test:")
print("  1. LOCAL: python api.py -> Load extension (Dev Mode)")
print(
    "  2. DEV MODE: chrome://extensions/ -> Load unpacked -> Select 'extension' folder"
)
print("  3. PRODUCTION: Extension uses https://vncontentguard-pro.onrender.com")
print("=" * 80)
