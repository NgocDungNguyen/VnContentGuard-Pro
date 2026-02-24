"""
VnContentGuard Pro v5 - Article Summarizer
============================================
Generates detailed 12-15 sentence summaries of Vietnamese news articles
using Gemini AI. Results are cached per URL to avoid redundant API calls.

Features:
- Gemini 2.5 Flash for detailed summaries
- Automatic caching (24h TTL per URL)
- Fallback to first-3-sentences extraction if API fails
- Input truncation to 8000 chars for maximum context
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
                    # Truncate to save tokens (first 8000 chars for maximum context)
                    truncated = article_text[:8000]

                    prompt = (
                        "Bạn là chuyên gia tóm tắt tin tức tiếng Việt và tiếng Anh.\n"
                        "Hãy viết MỘT ĐOẠN VĂN tóm tắt RẤT CHI TIẾT bài báo dưới đây.\n\n"
                        "QUY TẮC BẮT BUỘC (QUAN TRỌNG - PHẢI TUÂN THỦ):\n"
                        "1. Đoạn tóm tắt BẮT BUỘC PHẢI có TỐI THIỂU 12-15 câu đầy đủ\n"
                        "2. Đoạn tóm tắt PHẢI dài TỐI THIỂU 1500 ký tự (khoảng 700-900 từ)\n"
                        "3. Câu 1-2: Nêu chủ đề chính, ai/cái gì đang xảy ra, ở đâu, khi nào\n"
                        "4. Câu 3-4: Nêu con số, dữ liệu, giá cả, thống kê cụ thể quan trọng nhất\n"
                        "5. Câu 5-7: Giải thích nguyên nhân, bối cảnh lịch sử, diễn biến chi tiết từng bước\n"
                        "6. Câu 8-9: Nêu phản ứng, ý kiến của các bên liên quan (chính phủ, chuyên gia, người dân)\n"
                        "7. Câu 10-11: So sánh với tình huống tương tự, bối cảnh quốc tế hoặc lịch sử\n"
                        "8. Câu 12-15: Nêu tác động ngắn/dài hạn, hệ quả, dự báo, khuyến nghị và kết luận\n"
                        "9. Giữ nguyên tên riêng, địa danh, tổ chức và số liệu cụ thể từ bài gốc\n"
                        "10. Viết liền mạch thành MỘT đoạn văn duy nhất, KHÔNG xuống dòng, KHÔNG đánh số\n"
                        "11. Chỉ trả về đoạn tóm tắt, KHÔNG thêm tiêu đề hay giải thích\n"
                        "12. NẾU đoạn tóm tắt dưới 1500 ký tự → BẠN ĐÃ LÀM SAI, hãy viết dài hơn\n\n"
                        f"BÀI BÁO:\n{truncated}\n\n"
                        "ĐOẠN TÓM TẮT RẤT CHI TIẾT (12-15 câu, tối thiểu 1500 ký tự, khoảng 700-900 từ):"
                    )

                    response = self.client.models.generate_content(
                        model=self.model_name,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            temperature=0.5,
                            max_output_tokens=4096,
                        ),
                    )

                    summary = response.text.strip()

                    # Strip Gemini meta-text prefixes (echoed instructions)
                    summary = self._strip_meta_prefix(summary)

                    # If summary is too short, retry with stronger prompt
                    if summary and len(summary) < 1000:
                        retry_prompt = (
                            f"Đoạn tóm tắt sau đây quá ngắn (CHỈ {len(summary)} ký tự, cần TỐI THIỂU 1500):\n"
                            f'"{summary}"\n\n'
                            "Hãy VIẾT LẠI đoạn tóm tắt DÀI HƠN RẤT NHIỀU với ít nhất 12-15 câu đầy đủ "
                            "và tối thiểu 1500 ký tự. BẮT BUỘC thêm chi tiết về: con số cụ thể, thống kê, "
                            "nguyên nhân, bối cảnh lịch sử, diễn biến từng bước, phản ứng các bên, "
                            "so sánh quốc tế, tác động ngắn/dài hạn, và khuyến nghị.\n\n"
                            f"BÀI BÁO GỐC:\n{truncated[:6000]}\n\n"
                            "ĐOẠN TÓM TẮT MỚI (12-15 câu, 1500+ ký tự, PHẢI cực kỳ chi tiết):"
                        )
                        retry_resp = self.client.models.generate_content(
                            model=self.model_name,
                            contents=retry_prompt,
                            config=types.GenerateContentConfig(
                                temperature=0.6,
                                max_output_tokens=4096,
                            ),
                        )
                        retry_text = retry_resp.text.strip()
                        retry_text = self._strip_meta_prefix(retry_text)
                        if retry_text and len(retry_text) > len(summary):
                            summary = retry_text
                    if summary:
                        # Mark key as successful (resets 429 counter)
                        if self.key_rotator:
                            self.key_rotator.mark_key_success()
                        self.cache.set(cache_key, summary)
                        print(f"✅ Generated AI summary for {url[:60]}...")
                        return {
                            "summary": summary,
                            "method": "gemini",
                            "cached": False,
                        }

                except Exception as e:
                    error_str = str(e)
                    error_lower = error_str.lower()
                    is_quota = (
                        "429" in error_lower
                        or "quota" in error_lower
                        or "exhausted" in error_lower
                    )
                    print(f"⚠️ Summary attempt {attempt+1}/{max_attempts} failed: {e}")

                    if is_quota and self.key_rotator and attempt < max_attempts - 1:
                        # Parse retry delay and use cooldown instead of burning the key
                        retry_delay = APIKeyRotator.parse_retry_delay(error_str)
                        self.key_rotator.mark_key_rate_limited(retry_delay)
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
            r"^Dưới đây là[^.,:]*[.,:]\s*",
            r"^Đây là[^.,:]*[.,:]\s*",
            r"^Tóm tắt[^.,:]*[.,:]\s*",
            r"^Đoạn tóm tắt[^.,:]*[.,:]\s*",
            r"^Theo yêu cầu[^.,:]*[.,:]\s*",
            r"^Bài viết[^.,:]*[.,:]\s*",
        ]
        result = text
        for pattern in meta_patterns:
            result = re.sub(pattern, "", result, count=1, flags=re.IGNORECASE)
            if result != text:
                break  # Only strip one prefix

        return result.strip()

    def _fallback_summary(self, article_text: str) -> Dict[str, Any]:
        """
        Extract first 3 sentences as a basic summary.
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
            # No sentence boundaries found, just take first 300 chars
            summary = text[:300] + ("..." if len(text) > 300 else "")
        else:
            summary = " ".join(sentences[:3])
            if len(summary) > 500:
                summary = summary[:500] + "..."

        return {
            "summary": summary,
            "method": "fallback",
            "cached": False,
        }
