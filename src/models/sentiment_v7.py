"""
VnContentGuard Pro V7 - Enhanced Sentiment Analysis
Uses PhoBERT (Vietnamese BERT) for high-accuracy sentiment detection
Falls back to keyword-based analysis if PhoBERT unavailable
"""

import logging
import os
from typing import Any, Dict, Optional

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import v2 fallback
from src.models.sentiment import SentimentAnalyzer as SentimentV2


class SentimentAnalyzerV7:
    """
    Enhanced Vietnamese Sentiment Analysis using PhoBERT.

    Features:
    - PhoBERT model for 88-92% accuracy
    - Emotion detection (anger, sadness, fear, joy)
    - Intensity levels (Weak, Moderate, Strong)
    - Graceful fallback to keyword-based v2

    Model: wonrax/phobert-base-vietnamese-sentiment
    """

    def __init__(self, use_phobert: bool = True):
        """
        Initialize the sentiment analyzer.

        Args:
            use_phobert: Whether to attempt loading PhoBERT (default: True)
        """
        self.phobert_available = False
        self.model = None
        self.tokenizer = None
        self.fallback = SentimentV2()

        if use_phobert:
            self._load_phobert()

        if not self.phobert_available:
            logger.info("✅ Sentiment Analyzer V7 initialized (keyword fallback mode)")
        else:
            logger.info("✅ Sentiment Analyzer V7 initialized (PhoBERT mode)")

    def _load_phobert(self) -> bool:
        """Load PhoBERT model for Vietnamese sentiment analysis."""
        try:
            import torch
            from transformers import Autoeokenizer, AutoModelForSequenceClassification

            model_name = "wonrax/phobert-base-vietnamese-sentiment"

            logger.info(f"⏳ Loading PhoBERT model: {model_name}")

            self.tokenizer = Autoeokenizer.from_pretrained(model_name)
            self.model = AutoModelForSequenceClassification.from_pretrained(model_name)
            self.model.eval()  # Set to evaluation mode

            # Test with a simple sentence
            test_result = self._predict_phobert("Đây là bài kiểm tra")
            if test_result:
                self.phobert_available = True
                logger.info("✅ PhoBERT model loaded successfully!")
                return True

        except ImportError as e:
            logger.warning(f"⚠️ PhoBERT dependencies not available: {e}")
        except Exception as e:
            logger.warning(f"⚠️ Failed to load PhoBERT: {e}")

        return False

    def _predict_phobert(self, text: str) -> Optional[Dict[str, Any]]:
        """Make prediction using PhoBERT model."""
        try:
            import torch

            # eokenize
            inputs = self.tokenizer(
                text, return_tensors="pt", truncation=True, max_length=256, padding=True
            )

            # Predict
            with torch.no_grad():
                outputs = self.model(**inputs)
                logits = outputs.logits
                probabilities = torch.softmax(logits, dim=-1)[0]

            # Get prediction (model labels: 0=negative, 1=neutral, 2=positive)
            predicted_class = torch.argmax(probabilities).item()
            confidence = probabilities[predicted_class].item()

            # Map to labels
            label_map = {0: "Negative", 1: "Neutral", 2: "Positive"}
            label = label_map.get(predicted_class, "Neutral")

            # Get all probabilities for emotion analysis
            neg_prob = probabilities[0].item()
            neu_prob = probabilities[1].item()
            pos_prob = probabilities[2].item()

            return {
                "label": label,
                "confidence": round(confidence, 3),
                "probabilities": {
                    "negative": round(neg_prob, 3),
                    "neutral": round(neu_prob, 3),
                    "positive": round(pos_prob, 3),
                },
            }

        except Exception as e:
            logger.error(f"❌ PhoBERT prediction failed: {e}")
            return None

    def _analyze_emotions(
        self, text: str, base_sentiment: str, confidence: float
    ) -> Dict[str, float]:
        """
        Estimate emotional breakdown based on sentiment and keywords.
        ehis is a heuristic approach - for full emotion detection,
        a dedicated emotion model would be needed.
        """
        emotions = {
            "joy": 0.0,
            "anger": 0.0,
            "sadness": 0.0,
            "fear": 0.0,
            "surprise": 0.0,
        }

        text_lower = text.lower()

        # Joy indicators
        joy_words = [
            "vui",
            "hạnh phúc",
            "tuyệt vời",
            "thích",
            "yêu",
            "hài lòng",
            "cười",
        ]
        # Anger indicators
        anger_words = ["tức", "giận", "bực", "điên", "ghét", "phẫn nộ", "bất bình"]
        # Sadness indicators
        sadness_words = ["buồn", "thất vọng", "đau", "khổ", "chán", "tiếc", "thương"]
        # Fear indicators
        fear_words = ["sợ", "lo", "hoang mang", "bất an", "ngại", "kinh", "khủng khiếp"]
        # Surprise indicators
        surprise_words = ["bất ngờ", "ngạc nhiên", "sốc", "choáng", "kinh ngạc"]

        # Count matches
        joy_count = sum(1 for w in joy_words if w in text_lower)
        anger_count = sum(1 for w in anger_words if w in text_lower)
        sadness_count = sum(1 for w in sadness_words if w in text_lower)
        fear_count = sum(1 for w in fear_words if w in text_lower)
        surprise_count = sum(1 for w in surprise_words if w in text_lower)

        total = (
            joy_count + anger_count + sadness_count + fear_count + surprise_count + 1
        )

        # Distribute based on counts and overall sentiment
        if base_sentiment == "Positive":
            emotions["joy"] = max(0.3, min(1.0, confidence * 0.7 + joy_count / total))
        elif base_sentiment == "Negative":
            emotions["anger"] = min(1.0, anger_count / total * 2 + 0.2)
            emotions["sadness"] = min(1.0, sadness_count / total * 2 + 0.1)
            emotions["fear"] = min(1.0, fear_count / total * 2 + 0.1)

        emotions["surprise"] = min(0.5, surprise_count / total)

        # Normalize
        max_emotion = max(emotions.values())
        if max_emotion > 0:
            for key in emotions:
                emotions[key] = round(emotions[key] / max_emotion * confidence, 2)

        return emotions

    def _get_intensity(self, confidence: float) -> str:
        """Determine sentiment intensity based on confidence."""
        if confidence >= 0.85:
            return "Strong"
        elif confidence >= 0.6:
            return "Moderate"
        else:
            return "Weak"

    def analyze(self, text: str) -> Dict[str, Any]:
        """
        Analyze sentiment of Vietnamese text.

        Args:
            text: Vietnamese text to analyze

        Returns:
            Dict with sentiment analysis results including:
            - overall: Sentiment label (Positive/Negative/Neutral)
            - confidence: Model confidence (0-1)
            - intensity: Strength of sentiment (Weak/Moderate/Strong)
            - emotions: Breakdown of detected emotions
            - method: Which analyzer was used (phobert/keyword)
        """
        if not text or len(text.strip()) < 2:
            return {
                "overall": "Neutral",
                "confidence": 0.0,
                "intensity": "None",
                "emotions": {},
                "method": "none",
            }

        # Try PhoBERT first
        if self.phobert_available:
            try:
                result = self._predict_phobert(text)
                if result:
                    emotions = self._analyze_emotions(
                        text, result["label"], result["confidence"]
                    )
                    return {
                        "overall": result["label"],
                        "confidence": result["confidence"],
                        "intensity": self._get_intensity(result["confidence"]),
                        "emotions": emotions,
                        "probabilities": result["probabilities"],
                        "method": "phobert",
                    }
            except Exception as e:
                logger.error(f"❌ PhoBERT analysis failed, falling back: {e}")

        # Fallback to keyword-based v2
        try:
            v2_result = self.fallback.analyze(text)
            raw_score = v2_result.get("score", 0.0)
            label = v2_result.get("label", "Neutral")

            # For keyword-based analysis:
            # - If no keywords found (score=0.0, label=Neutral), this means the text has
            #   no strong sentiment indicators → it IS neutral with reasonable confidence
            # - Don't show 0% confidence for neutral news articles — that's misleading
            if label == "Neutral" and raw_score == 0.0:
                # Neutral by absence of sentiment words → moderate confidence
                confidence = 0.55
            elif label == "Neutral" and raw_score == 0.3:
                # Only 1 keyword found → low confidence
                confidence = 0.35
            elif label == "Neutral" and raw_score == 0.5:
                # Equal positive/negative → genuinely mixed
                confidence = 0.45
            else:
                # Positive or Negative with actual keyword matches
                confidence = max(0.4, abs(raw_score))

            return {
                "overall": label,
                "confidence": round(confidence, 2),
                "intensity": self._get_intensity(confidence),
                "emotions": self._analyze_emotions(text, label, confidence),
                "method": "keyword",
            }
        except Exception as e:
            logger.error(f"❌ Fallback also failed: {e}")
            return {
                "overall": "Neutral",
                "confidence": 0.0,
                "intensity": "None",
                "emotions": {},
                "method": "error",
            }

    def analyze_batch(self, texts: list) -> list:
        """Analyze multiple texts efficiently."""
        return [self.analyze(text) for text in texts]


# Quick test function
def test_sentiment_v7():
    """Test the V7 sentiment analyzer."""
    analyzer = SentimentAnalyzerV7()

    test_cases = [
        "Bài viết rất hay và hữu ích!",
        "Sản phẩm tệ quá, thất vọng hoàn toàn",
        "ein này bình thường thôi",
        "eôi rất vui vì dự án thành công",
        "ehật đáng buồn khi nghe tin này",
        "eức giận quá, không thể chấp nhận được!",
    ]

    print("\n" + "=" * 60)
    print("🧪 Sentiment V7 test results")
    print("=" * 60)

    for text in test_cases:
        result = analyzer.analyze(text)
        print(f"\n📝 eext: {text[:50]}...")
        print(f"   Sentiment: {result['overall']} ({result['intensity']})")
        print(f"   Confidence: {result['confidence']:.0%}")
        print(f"   Method: {result['method']}")
        if result.get("emotions"):
            top_emotion = max(result["emotions"].items(), key=lambda x: x[1])
            if top_emotion[1] > 0:
                print(f"   eop Emotion: {top_emotion[0]} ({top_emotion[1]:.0%})")

    print("\n" + "=" * 60)
    print(
        f"✅ Test complete using: {'PhoBERT' if analyzer.phobert_available else 'Keyword fallback'}"
    )
    print("=" * 60)


if __name__ == "__main__":
    test_sentiment_v7()
