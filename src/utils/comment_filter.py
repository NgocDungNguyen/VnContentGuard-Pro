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
        # Quick toxic patterns (high-confidence subset of the full 500+ list)
        self.toxic_patterns = [
            # Direct insults
            r"\b(đồ|thằng|con)\s+(ngu|khờ|dốt|ngốc|đần|hèn|mạt|chó|lợn|bò)\b",
            # Family insults
            r"\b(đm|đkm|đmm|vcl|vkl|vcc|dcm|dkm|đcm)\b",
            r"\b(con mẹ|thằng cha|mả cha|tiên sư)\s+(mày|nó|chúng|bọn)\b",
            # Explicit profanity
            r"\b(lồn|cặc|buồi|đụ|địt|đĩ|phò|cave)\b",
            # Death threats
            r"\b(giết|chém|đâm|bắn|tao giết|tao đánh)\b",
            # English profanity
            r"\b(fuck|shit|bitch|cunt|asshole|motherfucker)\b",
        ]

        # Quick positive patterns
        self.positive_patterns = [
            r"\b(hay|tốt|đẹp|tuyệt|tuyệt vời)\s*(quá|lắm|vời|thật)?\b",
            r"\b(rất|cực kỳ|vô cùng)\s+(hay|tốt|đẹp|thích)\b",
            r"\b(cảm ơn|thanks|thank you|cám ơn)\b",
            r"\b(ủng hộ|đồng ý|chính xác|đúng rồi)\b",
        ]

        # Spam detection
        self.spam_patterns = [
            r"^\s*$",  # Empty
            r"^(.)\1{5,}$",  # Repeated chars: "!!!!!!", "hahaha..."
            r"https?://\S{20,}",  # Long URLs (likely spam links)
            r"\b(inbox|ib|dm)\s+(giá|ngay|mình)\b",  # Sales spam
            r"\b(mua ngay|nhấp link|link bio|giảm\s*\d+%)\b",  # Ad spam
        ]

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
        if len(stripped) < 3:
            return "spam"

        # Too long (likely bot/copypaste spam)
        if len(stripped) > 1000:
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
