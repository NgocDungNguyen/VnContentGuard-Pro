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
            print(
                "✅ Article Summarizer initialized"
                + (" (shared rotator)" if key_rotator else "")
            )
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
                        "Bạn là chuyên gia tóm tắt tin tức tiếng Việt và tiếng Anh.\n"
                        "Hãy viết MỘT ĐOẠN VĂN tóm tắt bài báo dưới đây.\n\n"
                        "QUY TẮC BẮT BUỘC:\n"
                        "1. Đoạn tóm tắt BẮT BUỘC PHẢI có TỐI THIỂU 5-6 câu đầy đủ\n"
                        "2. Đoạn tóm tắt PHẢI dài TỐI THIỂU 700 ký tự (khoảng 300-400 từ)\n"
                        "3. Câu 1: Nêu chủ đề chính, ai/cái gì đang xảy ra\n"
                        "4. Câu 2: Nêu con số, dữ liệu, giá cả cụ thể quan trọng nhất\n"
                        "5. Câu 3: Giải thích nguyên nhân hoặc bối cảnh sự việc\n"
                        "6. Câu 4-5: Nêu các chi tiết bổ sung, so sánh, hoặc phản ứng liên quan\n"
                        "7. Câu 6-7: Nêu tác động, ý nghĩa, dự báo hoặc khuyến nghị\n"
                        "8. Giữ nguyên tên riêng và số liệu cụ thể\n"
                        "9. Viết liền mạch, KHÔNG xuống dòng, KHÔNG đánh số\n"
                        "10. Chỉ trả về đoạn tóm tắt, không thêm tiêu đề\n\n"
                        f"BÀI BÁO:\n{truncated}\n\n"
                        "ĐOẠN TÓM TẮT (5-6 câu, tối thiểu 700 ký tự):"
                    )

                    response = self.client.models.generate_content(
                        model=self.model_name,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            temperature=0.4,
                            max_output_tokens=1024,
                        ),
                    )

                    summary = response.text.strip()

                    # Strip Gemini meta-text prefixes (echoed instructions)
                    summary = self._strip_meta_prefix(summary)

                    # If summary is too short, retry with stronger prompt
                    if summary and len(summary) < 300:
                        retry_prompt = (
                            f"Đoạn tóm tắt sau đây quá ngắn ({len(summary)} ký tự):\n"
                            f'"{summary}"\n\n'
                            "Hãy VIẾT LẠI đoạn tóm tắt DÀI HƠN NHIỀU với ít nhất 5-6 câu đầy đủ "
                            "và tối thiểu 700 ký tự. Thêm chi tiết về con số, "
                            "nguyên nhân, so sánh, phản ứng, và tác động.\n\n"
                            f"BÀI BÁO GỐC:\n{truncated[:2000]}\n\n"
                            "ĐOẠN TÓM TẮT MỚI (5-6 câu, 700+ ký tự):"
                        )
                        retry_resp = self.client.models.generate_content(
                            model=self.model_name,
                            contents=retry_prompt,
                            config=types.GenerateContentConfig(
                                temperature=0.5,
                                max_output_tokens=1024,
                            ),
                        )
                        retry_text = retry_resp.text.strip()
                        retry_text = self._strip_meta_prefix(retry_text)
                        if retry_text and len(retry_text) > len(summary):
                            summary = retry_text
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
                    is_quota = (
                        "429" in error_str
                        or "quota" in error_str
                        or "exhausted" in error_str
                    )
                    print(f"⚠️ Summary attempt {attempt+1}/{max_attempts} failed: {e}")

                    if is_quota and self.key_rotator and attempt < max_attempts - 1:
                        self.key_rotator.mark_key_exhausted()
                        self._init_client()
                        print(f"🔄 Rotated key, retrying summary...")
                        continue
                    break  # Non-quota error or last attempt

        # 3. Fallback: extract first 2 sentences
        return self._fallback_summary(article_text)

    def _strip_meta_prefix(self, text: str) -> str:
        """
        Remove Gemini meta-text prefixes where it echoes prompt instructions
        like 'Dưới đây là đoạn tóm tắt...' before the actual summary.
        """
        import re

        # Common Vietnamese meta-prefixes Gemini adds
        meta_patterns = [
            r'^Dưới đây là[^.,:]*[.,:]\s*',
            r'^Đây là[^.,:]*[.,:]\s*',
            r'^Tóm tắt[^.,:]*[.,:]\s*',
            r'^Đoạn tóm tắt[^.,:]*[.,:]\s*',
            r'^Theo yêu cầu[^.,:]*[.,:]\s*',
            r'^Bài viết[^.,:]*[.,:]\s*',
        ]
        result = text
        for pattern in meta_patterns:
            result = re.sub(pattern, '', result, count=1, flags=re.IGNORECASE)
            if result != text:
                break  # Only strip one prefix

        return result.strip()

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
