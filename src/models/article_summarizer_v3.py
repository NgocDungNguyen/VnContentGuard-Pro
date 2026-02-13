"""
VnContentGuard Pro v3 - Article Summarizer
============================================
Generates concise 2-3 sentence summaries of Vietnamese news articles
using Gemini AI. Results are cached per URL to avoid redundant API calls.

Features:
- Gemini 2.5 Flash Lite for fast, cheap summaries
- Automatic caching (24h TTL per URL)
- Fallback to first-2-sentences extraction if API fails
- Input truncation to 2000 chars to save tokens
"""

from typing import Any, Dict, Optional

from google import genai
from google.genai import types

from src.models.gemini_llm import API_KEY_POOL, MODEL_NAME, APIKeyRotator
from src.utils.cache_manager import CacheManager


class ArticleSummarizer:
    """
    AI-powered article summarizer with caching.

    Usage:
        summarizer = ArticleSummarizer(cache)
        result = summarizer.summarize(article_text, url)
        # result = {'summary': '...', 'method': 'gemini'|'cached'|'fallback', 'cached': bool}
    """

    def __init__(self, cache: CacheManager, key_rotator: "APIKeyRotator | None" = None):
        self.cache = cache
        self.client: Optional[genai.Client] = None
        self.model_name = MODEL_NAME

        try:
            # Use shared key rotator if provided, otherwise create own (not recommended)
            self.key_rotator = key_rotator or APIKeyRotator(API_KEY_POOL)
            self._init_client()
            print("✅ Article Summarizer initialized" + (" (shared rotator)" if key_rotator else ""))
        except Exception as e:
            print(f"⚠️ Article Summarizer init failed (will use fallback): {e}")
            self.key_rotator = None

    def _init_client(self):
        """Initialize Gemini client with current API key."""
        if not self.key_rotator:
            return
        api_key = self.key_rotator.get_current_key()
        if api_key:
            self.client = genai.Client(api_key=api_key)

    def summarize(self, article_text: str, url: str) -> Dict[str, Any]:
        """
        Generate or retrieve a cached article summary.

        Args:
            article_text: Full article text
            url: Article URL (used as cache key)

        Returns:
            Dict with 'summary', 'method', 'cached' keys
        """
        if not article_text or len(article_text.strip()) < 30:
            return {
                "summary": "Nội dung quá ngắn để tóm tắt.",
                "method": "fallback",
                "cached": False,
            }

        # 1. Check cache
        cache_key = f"summary:{url}"
        cached = self.cache.get(cache_key)
        if cached:
            print(f"✅ Summary cache hit for {url[:60]}...")
            return {
                "summary": cached,
                "method": "cached",
                "cached": True,
            }

        # 2. Try Gemini (with retry on 429)
        max_attempts = 3
        if self.client:
            for attempt in range(max_attempts):
                try:
                    # Truncate to save tokens (first 4000 chars for better context)
                    truncated = article_text[:4000]

                    prompt = (
                        "Bạn là chuyên gia tóm tắt tin tức tiếng Việt.\n"
                        "Hãy tóm tắt bài báo dưới đây thành 3-5 câu hoàn chỉnh, đầy đủ ý chính.\n"
                        "Yêu cầu:\n"
                        "- Nêu rõ chủ đề chính của bài viết\n"
                        "- Đề cập các con số, sự kiện quan trọng\n"
                        "- Giữ nguyên tên riêng, số liệu cụ thể\n"
                        "- Viết mạch lạc, dễ hiểu\n"
                        "- Chỉ trả về đoạn tóm tắt, không thêm gì khác\n\n"
                        f"BÀI BÁO:\n{truncated}\n\n"
                        "TÓM TẮT:"
                    )

                    response = self.client.models.generate_content(
                        model=self.model_name,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            temperature=0.3,
                            max_output_tokens=500,
                        ),
                    )

                    summary = response.text.strip()
                    if summary:
                        self.cache.set(cache_key, summary)
                        print(f"✅ Generated AI summary for {url[:60]}...")
                        return {
                            "summary": summary,
                            "method": "gemini",
                            "cached": False,
                        }

                except Exception as e:
                    error_str = str(e).lower()
                    is_quota = "429" in error_str or "quota" in error_str or "exhausted" in error_str
                    print(f"⚠️ Summary attempt {attempt+1}/{max_attempts} failed: {e}")

                    if is_quota and self.key_rotator and attempt < max_attempts - 1:
                        self.key_rotator.mark_key_exhausted()
                        self._init_client()
                        print(f"🔄 Rotated key, retrying summary...")
                        continue
                    break  # Non-quota error or last attempt

        # 3. Fallback: extract first 2 sentences
        return self._fallback_summary(article_text)

    def _fallback_summary(self, article_text: str) -> Dict[str, Any]:
        """
        Extract first 2 sentences as a basic summary.
        Used when Gemini API is unavailable.
        """
        # Try splitting by Vietnamese sentence endings
        text = article_text.strip()
        sentences = []
        for sep in [".", "。", "!", "?"]:
            if sep in text:
                parts = text.split(sep)
                for p in parts:
                    cleaned = p.strip()
                    if len(cleaned) > 15:
                        sentences.append(cleaned + sep)
                break

        if not sentences:
            # No sentence boundaries found, just take first 200 chars
            summary = text[:200] + ("..." if len(text) > 200 else "")
        else:
            summary = " ".join(sentences[:2])
            if len(summary) > 300:
                summary = summary[:300] + "..."

        return {
            "summary": summary,
            "method": "fallback",
            "cached": False,
        }
