# Pure keyword-based sentiment analysis (no API needed)
# Lightweight, fast, and always available


class SentimentAnalyzer:
    def __init__(self):
        print("✅ Sentiment Analyzer initialized (keyword-based)")

        # Vietnamese sentiment keywords
        self.positive_words = [
            "tốt",
            "hay",
            "đẹp",
            "tuyệt",
            "xuất sắc",
            "hoàn hảo",
            "thích",
            "yêu",
            "vui",
            "hạnh phúc",
            "tốt lành",
            "hữu ích",
            "tích cực",
            "thành công",
            "cảm ơn",
            "tuyệt vời",
            "tốt đẹp",
            "ưu việt",
            "đáng yêu",
            "chất lượng",
            "tâm lý",
            "hiệu quả",
            "hài lòng",
            "thỏa mãn",
            "tin tưởng",
            "uy tín",
        ]

        self.negative_words = [
            "tệ",
            "xấu",
            "kém",
            "dở",
            "tồi",
            "ghét",
            "chán",
            "buồn",
            "thất vọng",
            "thảm họa",
            "tối tệ",
            "vô dụng",
            "lừa đảo",
            "gian lận",
            "khủng khiếp",
            "không hài lòng",
            "thất bại",
            "tệ hại",
            "không tốt",
            "rác",
            "phí tiền",
            "lãng phí",
            "không đáng",
            "không nên",
            "cẩn thận",
        ]

    def analyze(self, text):
        """Analyze sentiment using keyword matching"""
        if not text:
            return {"label": "Neutral", "score": 0.0}

        text_lower = text.lower()

        # Count positive and negative keywords
        positive_count = sum(1 for word in self.positive_words if word in text_lower)
        negative_count = sum(1 for word in self.negative_words if word in text_lower)

        # Calculate score
        total = positive_count + negative_count

        # If no sentiment keywords found, it's neutral
        if total == 0:
            return {"label": "Neutral", "score": 0.0}

        # Require at least 2 keywords for strong sentiment (reduces false positives)
        if total == 1:
            return {"label": "Neutral", "score": 0.3}

        # Determine sentiment
        if positive_count > negative_count:
            score = positive_count / total
            return {"label": "Positive", "score": round(score, 2)}
        elif negative_count > positive_count:
            score = negative_count / total
            return {"label": "Negative", "score": round(score, 2)}
        else:
            return {"label": "Neutral", "score": 0.5}
