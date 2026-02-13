import json
import os
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from dotenv import load_dotenv
from google import genai

# Load API Keys
load_dotenv()

# Multi-API-Key Pool (30 projects) - Load from environment variables ONLY
API_KEY_POOL = [
    os.getenv("GEMINI_API_KEY"),
    os.getenv("GEMINI_API_KEY_2"),
    os.getenv("GEMINI_API_KEY_3"),
    os.getenv("GEMINI_API_KEY_4"),
    os.getenv("GEMINI_API_KEY_5"),
    os.getenv("GEMINI_API_KEY_6"),
    os.getenv("GEMINI_API_KEY_7"),
    os.getenv("GEMINI_API_KEY_8"),
    os.getenv("GEMINI_API_KEY_9"),
    os.getenv("GEMINI_API_KEY_10"),
    os.getenv("GEMINI_API_KEY_11"),
    os.getenv("GEMINI_API_KEY_12"),
    os.getenv("GEMINI_API_KEY_13"),
    os.getenv("GEMINI_API_KEY_14"),
    os.getenv("GEMINI_API_KEY_15"),
    os.getenv("GEMINI_API_KEY_16"),
    os.getenv("GEMINI_API_KEY_17"),
    os.getenv("GEMINI_API_KEY_18"),
    os.getenv("GEMINI_API_KEY_19"),
    os.getenv("GEMINI_API_KEY_20"),
    os.getenv("GEMINI_API_KEY_21"),
    os.getenv("GEMINI_API_KEY_22"),
    os.getenv("GEMINI_API_KEY_23"),
    os.getenv("GEMINI_API_KEY_24"),
    os.getenv("GEMINI_API_KEY_25"),
    os.getenv("GEMINI_API_KEY_26"),
    os.getenv("GEMINI_API_KEY_27"),
    os.getenv("GEMINI_API_KEY_28"),
    os.getenv("GEMINI_API_KEY_29"),
    os.getenv("GEMINI_API_KEY_30"),
]

# Filter out None values
API_KEY_POOL = [key for key in API_KEY_POOL if key]

if not API_KEY_POOL:
    raise ValueError(
        "❌ No API keys found! Please set GEMINI_API_KEY_* in environment variables or .env file"
    )

    API_KEY_POOL = [os.getenv("GEMINI_API_KEY", "")]

# Model configuration — v4.0 upgrade to Gemini 2.5 Flash (auto-fallback to Lite)
MODEL_NAME = "gemini-2.5-flash"  # Primary model (faster, smarter)
MODEL_NAME_FALLBACK = "gemini-2.5-flash-lite"  # Fallback if primary quota exceeded


class APIKeyRotator:
    """
    Intelligent API Key Rotation System
    - Automatically switches to next key when quota exhausted
    - Tracks exhausted keys
    - Resets daily (quota resets at UTC midnight)
    """

    def __init__(self, api_keys: List[str]):
        self.api_keys = [key for key in api_keys if key and key.strip()]
        self.current_index = 0
        self.exhausted_keys = set()
        self.last_reset_date = datetime.utcnow().date()
        self.request_counts = {i: 0 for i in range(len(self.api_keys))}

        if not self.api_keys:
            raise ValueError("❌ No valid API keys provided!")

        print(f"✅ API Key Rotator initialized with {len(self.api_keys)} keys")

    def _check_daily_reset(self):
        """Check if we need to reset exhausted keys (new day in UTC)"""
        current_date = datetime.utcnow().date()
        if current_date > self.last_reset_date:
            print(f"🔄 Daily reset: Clearing exhausted keys")
            self.exhausted_keys.clear()
            self.request_counts = {i: 0 for i in range(len(self.api_keys))}
            self.last_reset_date = current_date
            self.current_index = 0

    def get_current_key(self) -> Optional[str]:
        """Get the current API key"""
        self._check_daily_reset()

        if self.current_index in self.exhausted_keys:
            # Current key exhausted, try to find next available
            if not self._rotate_to_next_available():
                return None

        return self.api_keys[self.current_index]

    def mark_key_exhausted(self):
        """Mark current API key as exhausted and rotate to next"""
        print(
            f"🚫 API Key #{self.current_index + 1} exhausted (used {self.request_counts[self.current_index]} times)"
        )
        self.exhausted_keys.add(self.current_index)

        if not self._rotate_to_next_available():
            print("❌ All API keys exhausted! Waiting for daily reset...")
            return False
        return True

    def _rotate_to_next_available(self) -> bool:
        """Rotate to next available (non-exhausted) key"""
        start_index = self.current_index

        for _ in range(len(self.api_keys)):
            self.current_index = (self.current_index + 1) % len(self.api_keys)

            if self.current_index not in self.exhausted_keys:
                print(f"🔄 Switched to API Key #{self.current_index + 1}")
                return True

            # Avoid infinite loop
            if self.current_index == start_index:
                break

        return False

    def increment_request_count(self):
        """Track successful request"""
        self.request_counts[self.current_index] += 1

    def get_status(self) -> Dict:
        """Get current status of all keys"""
        return {
            "total_keys": len(self.api_keys),
            "current_key": self.current_index + 1,
            "exhausted_count": len(self.exhausted_keys),
            "available_count": len(self.api_keys) - len(self.exhausted_keys),
            "request_counts": self.request_counts,
            "last_reset": self.last_reset_date.isoformat(),
        }


class GeminiAgent:
    """
    Advanced Gemini Agent with:
    - Multi-API-key rotation
    - Intelligent quota handling
    - Static fallbacks
    - New google-genai package
    """

    def __init__(self, key_rotator: "APIKeyRotator | None" = None):
        # Use shared key rotator if provided, otherwise create own
        self.key_rotator = key_rotator or APIKeyRotator(API_KEY_POOL)
        self.client: Optional[genai.Client] = None
        self.model_name = MODEL_NAME
        self.fallback_model_name = MODEL_NAME_FALLBACK
        self.using_fallback_model = False

        # Initialize with first key
        self._initialize_client()

        # Retry configuration
        self.max_retries = len(API_KEY_POOL)  # Try all keys before giving up
        self.retry_count = 0

    def _initialize_client(self) -> bool:
        """Initialize Gemini client with current API key"""
        try:
            api_key = self.key_rotator.get_current_key()
            if not api_key:
                print("❌ No available API keys")
                return False

            self.client = genai.Client(api_key=api_key)
            print(
                f"✅ Gemini client initialized with API Key #{self.key_rotator.current_index + 1}"
            )
            return True

        except Exception as e:
            print(f"❌ Failed to initialize Gemini client: {e}")
            return False

    def _is_quota_error(self, error: Exception) -> bool:
        """Check if error is quota/rate limit related"""
        error_str = str(error).lower()
        quota_indicators = [
            "429",
            "quota",
            "exceeded",
            "rate limit",
            "too many requests",
            "resource_exhausted",
            "resourceexhausted",
        ]
        return any(indicator in error_str for indicator in quota_indicators)

    def _try_fallback_model(self) -> bool:
        """Switch to fallback model if primary model fails"""
        if not self.using_fallback_model:
            print(
                f"⚠️ Primary model {self.model_name} failing, switching to fallback: {self.fallback_model_name}"
            )
            self.model_name = self.fallback_model_name
            self.using_fallback_model = True
            # Reset key rotator to try all keys with fallback model
            self.key_rotator.exhausted_keys.clear()
            self.key_rotator.current_index = 0
            self._initialize_client()
            return True
        return False

    def _rotate_key_and_retry(self) -> bool:
        """Rotate to next API key and reinitialize client"""
        if self.key_rotator.mark_key_exhausted():
            return self._initialize_client()
        # All keys exhausted for current model — try fallback model
        return self._try_fallback_model()

    def check_fake_news(self, article_text: str) -> str:
        """
        Analyze article for misinformation with API key rotation.
        """
        if not self.client:
            return self._get_fallback_fake_news()

        # Truncate to save tokens
        max_chars = 5000
        if len(article_text) > max_chars:
            print(
                f"⚠️ Article too long ({len(article_text)} chars), truncating to {max_chars}"
            )
            article_text = article_text[:max_chars]

        # Build prompt
        prompt = f"""You are a professional Fact Checker specializing in Vietnamese content.

ESSENTIAL CONTEXT: Today is January 24, 2026.
- Events from 2024-2025 are HISTORICAL FACTS
- Events dated 2026 are CURRENT - do NOT flag them as fake
- Accept 2026 events unless they contradict known facts

Analyze this article and determine if it's reliable or potentially fake news.

ARTICLE:
{article_text}

Return ONLY a JSON object (no markdown):
{{
    "risk_score": (1-10 integer, 1=Safe, 10=Definitely Fake),
    "verdict": ("Reliable", "Opinion Piece", or "Likely Fake"),
    "summary": "One sentence assessment"
}}"""

        # Retry with key rotation
        for attempt in range(self.max_retries):
            try:
                response = self.client.models.generate_content(
                    model=self.model_name, contents=prompt
                )

                # Track successful request
                self.key_rotator.increment_request_count()

                # Extract text
                if hasattr(response, "text") and response.text:
                    raw_text = response.text
                    clean_text = re.sub(r"```json\s*", "", raw_text)
                    clean_text = re.sub(r"```\s*", "", clean_text)
                    clean_text = clean_text.strip()

                    # Validate JSON
                    try:
                        json.loads(clean_text)
                        return clean_text
                    except json.JSONDecodeError:
                        return self._extract_json(clean_text)

            except Exception as e:
                error_msg = str(e)
                print(
                    f"❌ Attempt {attempt + 1}/{self.max_retries} failed: {error_msg[:100]}"
                )

                # Check if quota error
                if self._is_quota_error(e):
                    print(
                        f"⚠️ Quota exceeded for API Key #{self.key_rotator.current_index + 1}"
                    )

                    # Try to rotate to next key
                    if self._rotate_key_and_retry():
                        print(
                            f"🔄 Retrying with API Key #{self.key_rotator.current_index + 1}..."
                        )
                        continue
                    else:
                        # All keys exhausted
                        print("❌ All API keys exhausted!")
                        return self._get_fallback_fake_news()
                else:
                    # Non-quota error, return fallback
                    print(f"❌ Non-quota error: {error_msg[:100]}")
                    return self._get_fallback_fake_news()

        # Max retries reached
        return self._get_fallback_fake_news()

    def _get_fallback_fake_news(self) -> str:
        """Return safe fallback when all API keys exhausted"""
        return json.dumps(
            {
                "risk_score": 5,
                "verdict": "Unable to Verify",
                "summary": "AI verification temporarily unavailable due to high demand. Please verify source credibility manually and check official news sources.",
            }
        )

    def _extract_json(self, text: str) -> str:
        """Extract JSON from messy text"""
        try:
            # Try to find JSON pattern
            json_match = re.search(r'\{[^{}]*"risk_score"[^{}]*\}', text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                json.loads(json_str)  # Validate
                return json_str
        except:
            pass

        return self._get_fallback_fake_news()

    def get_status(self) -> Dict:
        """Get current status of API key rotation"""
        status = self.key_rotator.get_status()
        status["model"] = self.model_name
        status["using_fallback"] = self.using_fallback_model
        return status


# Test function
if __name__ == "__main__":
    print("=" * 80)
    print("Testing Multi-API-Key Gemini Agent")
    print("=" * 80)

    agent = GeminiAgent()

    # Show initial status
    print("\n📊 Initial Status:")
    status = agent.get_status()
    print(json.dumps(status, indent=2))

    # Test with sample article
    test_article = """
    Breaking News: Thủ tướng Phạm Minh Chính công bố kế hoạch phát triển AI Việt Nam 2026.
    Chính phủ sẽ đầu tư 10 tỷ USD vào nghiên cứu trí tuệ nhân tạo trong 5 năm tới.
    """

    print("\n🧪 Testing fake news detection...")
    result = agent.check_fake_news(test_article)
    print(f"\nResult:\n{result}")

    # Show final status
    print("\n📊 Final Status:")
    status = agent.get_status()
    print(json.dumps(status, indent=2))
