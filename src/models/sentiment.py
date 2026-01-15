class SentimentAnalyzer:
    """
    Lightweight Vietnamese Sentiment Analyzer (no heavy ML dependencies).
    Uses keyword-based heuristics for fast, memory-efficient sentiment analysis.
    """

    def __init__(self):
        print("✅ Sentiment Model Ready (lightweight keyword-based)")
        
        # Vietnamese sentiment keywords
        self.positive_keywords = {
            'tuyệt vời', 'tốt', 'yêu thích', 'xuất sắc', 'tuyệt',
            'hay', 'giỏi', 'đỉnh', 'thích', 'tốt lắm', 'perfect',
            'tuyệt đỉnh', 'hài lòng', 'vui', 'mê', 'mười điểm',
            'like', 'love', 'awesome', 'excellent', 'great',
            'wonderful', 'fantastic', 'beautiful', 'brilliant',
            'good', 'best', 'amazing', 'nice', 'brilliant'
        }
        
        self.negative_keywords = {
            'tệ', 'xấu', 'ghét', 'tồi', 'không tốt', 'tệ quá',
            'kinh khủng', 'khủng khiếp', 'tệ hại', 'phí', 'lỗi',
            'vô dụng', 'cáu', 'buồn', 'tức giận', 'thất vọng',
            'hate', 'bad', 'terrible', 'awful', 'horrible', 
            'poor', 'worst', 'sad', 'angry', 'disappointed',
            'disgusting', 'pathetic', 'useless', 'waste'
        }

    def analyze(self, text):
        """
        Analyze sentiment of Vietnamese text using keywords.

        Args:
            text (str): Input text to analyze

        Returns:
            dict: Contains 'label' and 'score' keys
        """
        try:
            if not text:
                return {"label": "Neutral", "score": 0.0}

            # Convert to lowercase for matching
            text_lower = text.lower()
            
            # Count positive and negative keywords
            positive_count = sum(1 for word in self.positive_keywords if word in text_lower)
            negative_count = sum(1 for word in self.negative_keywords if word in text_lower)
            
            # Determine sentiment based on keyword counts
            if positive_count > negative_count > 0:
                # Mixed but more positive
                score = 0.5 + (positive_count / (positive_count + negative_count)) * 0.5
                return {"label": "Positive", "score": min(score, 1.0)}
            elif negative_count > positive_count > 0:
                # Mixed but more negative
                score = 1.0 - (negative_count / (positive_count + negative_count)) * 0.5
                return {"label": "Negative", "score": min(score, 1.0)}
            elif positive_count > 0:
                return {"label": "Positive", "score": min(0.5 + positive_count * 0.1, 1.0)}
            elif negative_count > 0:
                return {"label": "Negative", "score": min(0.5 + negative_count * 0.1, 1.0)}
            else:
                return {"label": "Neutral", "score": 0.5}

        except Exception as e:
            # Return safe default on any error
            print(f"⚠️  Error analyzing sentiment: {e}")
            return {"label": "Neutral", "score": 0.0}


# Test
if __name__ == "__main__":
    analyzer = SentimentAnalyzer()
    print(analyzer.analyze("Sản phẩm này tệ quá, phí tiền!"))  # Should be Negative
    print(analyzer.analyze("Tuyệt vời, tôi rất yêu thích!"))  # Should be Positive
    print(analyzer.analyze("Bình thường thôi"))  # Should be Neutral
