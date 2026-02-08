"""
VnContentGuard Pro v3 - Smart Comment Filter
=============================================
Pre-filters comments into categories to avoid wasting API calls
on obvious cases. Only ambiguous comments are sent to Gemini.

Categories:
- obvious_toxic: Matched known toxic regex patterns → skip API
- obvious_clean: Matched known positive patterns → skip API
- spam: Empty, too short, URL spam, repeated chars → skip API
- ambiguous: Needs AI analysis → send to Gemini batch
"""

import re
from typing import Dict, List


class CommentFilter:
    """
    Pre-classify comments to reduce unnecessary API calls.

    Typical savings: 60-80% of comments can be classified without API.
    """

    def __init__(self):
        # Quick toxic patterns (high-confidence Vietnamese + English)
        self.toxic_patterns = [
            # Direct insults
            r"\b(đồ|thằng|con)\s+(ngu|khờ|dốt|ngốc|đần|hèn|mạt|chó|lợn|bò|khốn|ranh|điên|khùng)\b",
            # Insult comparisons
            r"\b(ngu|ngốc|khùng|điên)\s+(như|kiểu)\s+(lợn|chó|bò|trâu)\b",
            # Vietnamese profanity acronyms (VERY common online)
            r"\b(đm|đkm|đmm|vcl|vkl|vcc|dcm|dkm|đcm|cc|vl|cmm|cmn|clm|dm|d\.m|đ\.m|v\.l)\b",
            # Family insults
            r"\b(con mẹ|thằng cha|mả cha|tiên sư)\s*(mày|nó|chúng|bọn)?\b",
            # Explicit profanity
            r"\b(lồn|cặc|buồi|đụ|địt|đĩ|phò|cave)\b",
            # Death/violence threats
            r"\b(giết|chém|đâm|bắn|tao giết|tao đánh)\b",
            r"\b(chết|giết|đập|đánh|đấm|đá)\s+(mày|bạn|người|nó|họ)\b",
            r"\b(tao|mày)\s+(giết|đập|đấm)\b",
            # Hostile commands
            r"\b(câm|câm\s+mồm|câm\s+họng|câm\s+đi)\b",
            r"\b(cút|cút\s+đi|biến|biến\s+đi)\b",
            r"\b(đi\s+chết|chết\s+đi|chết\s+mẹ)\b",
            # Brain/intelligence insults
            r"\b(óc\s+chó|não\s+chó|đầu\s+gối|ngu\s+vl|ngu\s+vcl)\b",
            r"\b(thằng\s+ngu|con\s+ngu|đồ\s+khốn|đồ\s+rác)\b",
            # English profanity
            r"\b(fuck|shit|bitch|cunt|asshole|motherfucker|stfu|wtf|damn)\b",
        ]

        # Quick positive patterns
        self.positive_patterns = [
            # Praise
            r"\b(hay|tốt|đẹp|tuyệt|xuất\s*sắc)\s*(quá|lắm|vời|thật)?\b",
            r"\b(rất|cực\s*kỳ|vô\s*cùng|thực\s*sự)\s+(hay|tốt|đẹp|thích|ổn|ok)\b",
            r"\b(thích|yêu|mê)\s*(quá|lắm)\b",
            r"\b(tuyệt\s*vời|tuyệt\s*đối|xuất\s*sắc)\b",
            # Gratitude
            r"\b(cảm\s*ơn|thanks|thank\s*you|cám\s*ơn)\b",
            r"\b(chúc\s*mừng|xin\s*chúc)\b",
            # Agreement
            r"\b(ủng\s*hộ|đồng\s*ý|chính\s*xác|đúng\s*rồi|chuẩn)\b",
            # Emoji-only (positive)
            r"^\s*[👍👏❤️😍🙏💯✨🎉😄😊🥰💕]+\s*$",
            # Simple affirmations (standalone)
            r"^\s*(ok|okie|oke|good|nice|great|cool|👍)\s*$",
        ]

        # Spam detection
        self.spam_patterns = [
            r"^\s*$",  # Empty
            r"^(.)\1{5,}$",  # Repeated chars: "!!!!!!"
            r"^[!.?]{3,}$",  # Only punctuation: "..." or "!!!"
            r"^\s*[.!?]+\s*$",  # Whitespace + punctuation only
            r"^(.{1,5})\1{3,}$",  # Repeated short phrases: "haha haha haha"
            r"https?://\S{10,}",  # URLs (likely spam links)
            r"\b(inbox|ib|dm)\s+(giá|ngay|mình)\b",  # Sales spam
            r"\b(mua ngay|nhấp link|link bio|giảm\s*\d+%)\b",  # Ad spam
            r"^[0-9\s\-\(\)+]+$",  # Only numbers/phone
        ]

        # Short neutral words — definitely don't need AI
        self.short_neutral_words = {
            'ok', 'oke', 'okie', 'ừ', 'uh', 'à', 'vâng', 'dạ', 'không',
            'có', 'vậy', 'thôi', 'hì', 'hehe', 'hihi', 'ờ', 'ừm', 'uhm',
            'ah', 'oh', 'ồ', 'ủa', 'hmm', 'hm', 'okay', 'k', 'ko',
        }

        # Compile patterns for performance
        self._toxic_compiled = [
            re.compile(p, re.IGNORECASE) for p in self.toxic_patterns
        ]
        self._positive_compiled = [
            re.compile(p, re.IGNORECASE) for p in self.positive_patterns
        ]
        self._spam_compiled = [
            re.compile(p, re.IGNORECASE) for p in self.spam_patterns
        ]

    def classify(self, comment: str) -> str:
        """
        Classify a single comment.

        Returns one of: 'obvious_toxic', 'obvious_clean', 'spam', 'ambiguous'
        """
        if not comment or not comment.strip():
            return "spam"

        stripped = comment.strip()

        # Too short to be meaningful
        if len(stripped) < 2:
            return "spam"

        # Too long (likely bot/copypaste spam)
        if len(stripped) > 500:
            return "spam"

        # Check spam patterns
        for pattern in self._spam_compiled:
            if pattern.search(stripped):
                return "spam"

        # Check obvious toxic
        lower = stripped.lower()
        for pattern in self._toxic_compiled:
            if pattern.search(lower):
                return "obvious_toxic"

        # Check obvious positive/clean
        for pattern in self._positive_compiled:
            if pattern.search(lower):
                return "obvious_clean"

        # Short neutral words don't need AI ("ok", "ừ", "vâng", etc.)
        if lower in self.short_neutral_words:
            return "obvious_clean"

        # Very short comments without strong sentiment are likely clean
        # "hì hì", "vậy à", "thật hả" — not worth an API call
        if len(stripped) < 15 and not any(c in stripped for c in ['?', '!']):
            return "obvious_clean"

        # Default: needs deeper analysis
        return "ambiguous"

    def filter_comments(self, comments: List[str]) -> Dict[str, List[str]]:
        """
        Sort all comments into categories.

        Returns dict with keys: 'ambiguous', 'obvious_toxic', 'obvious_clean', 'spam'
        """
        result: Dict[str, List[str]] = {
            "ambiguous": [],
            "obvious_toxic": [],
            "obvious_clean": [],
            "spam": [],
        }

        for comment in comments:
            category = self.classify(comment)
            result[category].append(comment)

        return result
