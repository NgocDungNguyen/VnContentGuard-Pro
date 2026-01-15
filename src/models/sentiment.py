import torch
from transformers import pipeline


class SentimentAnalyzer:
    """
    Vietnamese Sentiment Analyzer with safety and performance optimizations.
    Handles text truncation and error handling to prevent crashes.
    """

    def __init__(self):
        print("⏳ Loading Sentiment Model (this may take a while first time)...")
        try:
            # Use Vietnamese-specific model from Hugging Face
            self.pipe = pipeline(
                "sentiment-analysis",
                model="wonrax/phobert-base-vietnamese-sentiment",
                device=(
                    0 if torch.cuda.is_available() else -1
                ),  # GPU if available, else CPU
            )
            print("✅ Sentiment Model Loaded Successfully")
        except Exception as e:
            print(f"⚠️  Error loading sentiment model: {e}")
            self.pipe = None

    def analyze(self, text):
        """
        Analyze sentiment of Vietnamese text.

        Args:
            text (str): Input text to analyze

        Returns:
            dict: Contains 'label' and 'score' keys
        """
        try:
            if not text or not self.pipe:
                return {"label": "Neutral", "score": 0.0}

            # SAFETY: Truncate text to prevent memory overflow
            # Max 512 tokens is safe for transformer models
            max_chars = 256  # Approximately 256 tokens
            truncated_text = text[:max_chars]

            if not truncated_text.strip():
                return {"label": "Neutral", "score": 0.0}

            # Run sentiment analysis
            result = self.pipe(truncated_text)[0]

            # Map model labels to readable format
            label_map = {
                "POS": "Positive",
                "NEG": "Negative",
                "NEU": "Neutral",
                "POSITIVE": "Positive",
                "NEGATIVE": "Negative",
                "NEUTRAL": "Neutral",
            }

            clean_label = label_map.get(result["label"], result["label"])
            confidence = round(result["score"], 2)

            return {"label": clean_label, "score": confidence}

        except RuntimeError as e:
            # Handle CUDA or memory errors
            if "out of memory" in str(e).lower():
                print(f"⚠️  Out of memory: {str(e)}")
                return {"label": "Neutral", "score": 0.0}
            else:
                print(f"⚠️  Runtime error in sentiment analysis: {e}")
                return {"label": "Neutral", "score": 0.0}

        except Exception as e:
            # Catch all other errors and return safe default
            print(f"⚠️  Error analyzing sentiment: {e}")
            return {"label": "Neutral", "score": 0.0}


# Test
if __name__ == "__main__":
    analyzer = SentimentAnalyzer()
    print(analyzer.analyze("Sản phẩm này tệ quá, phí tiền!"))  # Should be Negative
    print(analyzer.analyze("Tuyệt vời, tôi rất yêu thích!"))  # Should be Positive
