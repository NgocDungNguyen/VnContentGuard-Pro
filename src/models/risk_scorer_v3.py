"""
VnContentGuard Pro v3 - Objective Risk Scoring System
=====================================================
Comprehensive risk assessment integrating all v3 detection modules:
- 40% Fake News Score (fact-checking credibility)
- 25% Toxicity Score (harmful content detection)
- 15% Sentiment Score (emotional manipulation detection)
- 10% Source Credibility (domain reputation)
- 10% Manipulation Indicators (patterns, clickbait, etc.)

Final Risk Score: 0-100 (0=safe, 100=high risk)
Risk Levels: Low (0-25), Medium (26-50), High (51-75), Critical (76-100)
"""

import os
from datetime import datetime
from typing import Dict, List, Optional

from dotenv import load_dotenv

load_dotenv()


class RiskScorerV3:
    """
    Objective Risk Scoring System

    Combines multiple detection modules into a single comprehensive risk score:
    - Sentiment Analysis (15%): Detects emotional manipulation
    - Toxicity Detection (25%): Identifies harmful content
    - Fact-Checking (40%): Verifies claims and sources
    - Source Credibility (10%): Assesses domain reputation
    - Manipulation Patterns (10%): Detects clickbait, sensationalism

    Risk Score Formula:
    Risk = 40×(100-Credibility) + 25×Toxicity + 15×|Sentiment| + 10×(100-Source) + 10×Manipulation

    All scores normalized to 0-100 scale
    """

    def __init__(self):
        print("⏳ Initializing Risk Scorer v3...")

        # Feature flags
        self.use_v3 = os.getenv("USE_V3", "true").lower() == "true"
        self.use_fact_checking = (
            os.getenv("USE_FACT_CHECKING", "true").lower() == "true"
        )

        # Import v3 modules
        self.sentiment_analyzer = None
        self.toxicity_analyzer = None
        self.fact_checker = None

        try:
            from .sentiment_v3 import SentimentAnalyzerV3

            self.sentiment_analyzer = SentimentAnalyzerV3(use_phobert=False)
            print("✅ Sentiment v3 loaded")
        except Exception as e:
            print(f"⚠️ Sentiment v3 unavailable: {e}")

        try:
            from .toxicity_v3 import ToxicityAnalyzerV3

            self.toxicity_analyzer = ToxicityAnalyzerV3(use_detoxify=False)
            print("✅ Toxicity v3 loaded")
        except Exception as e:
            print(f"⚠️ Toxicity v3 unavailable: {e}")

        try:
            from .fact_checker_v3 import FactCheckerV3

            self.fact_checker = FactCheckerV3()
            print("✅ Fact-Checker v3 loaded")
        except Exception as e:
            print(f"⚠️ Fact-Checker v3 unavailable: {e}")

        print("✅ Risk Scorer v3 Ready!")

    def score(self, text: str, url: Optional[str] = None) -> Dict:
        """
        Calculate comprehensive risk score for content

        Args:
            text: Content text to analyze
            url: Optional source URL

        Returns:
            Dict with:
            - risk_score: int (0-100, overall risk)
            - risk_level: str (Low/Medium/High/Critical)
            - breakdown: dict (scores for each component)
            - evidence: list (detailed findings from each module)
            - recommendations: list (suggested actions)
        """
        if not text or not text.strip():
            return self._empty_result()

        results = {
            "risk_score": 0,
            "risk_level": "Unknown",
            "breakdown": {
                "fake_news_component": 0,  # 40% weight
                "toxicity_component": 0,  # 25% weight
                "sentiment_component": 0,  # 15% weight
                "source_component": 0,  # 10% weight
                "manipulation_component": 0,  # 10% weight
            },
            "raw_scores": {},
            "evidence": [],
            "recommendations": [],
        }

        # Component 1: Sentiment Analysis (15% weight)
        if self.sentiment_analyzer:
            sentiment_result = self.sentiment_analyzer.analyze(text)
            results["raw_scores"]["sentiment"] = sentiment_result

            # Convert sentiment to risk (extreme emotions = higher risk)
            sentiment_risk = self._calculate_sentiment_risk(sentiment_result)
            results["breakdown"]["sentiment_component"] = sentiment_risk * 0.15

            # Get sentiment label (handle both v2 'sentiment' and v3 'label')
            sentiment_label = sentiment_result.get("sentiment") or sentiment_result.get(
                "label", "Unknown"
            )

            results["evidence"].append(
                {
                    "module": "Sentiment Analysis v3",
                    "finding": f"{sentiment_label} ({sentiment_result.get('confidence', 0)*100:.0f}% confidence)",
                    "risk_contribution": f"{sentiment_risk}/100",
                }
            )

        # Component 2: Toxicity Detection (25% weight)
        if self.toxicity_analyzer:
            toxicity_result = self.toxicity_analyzer.analyze(text)
            results["raw_scores"]["toxicity"] = toxicity_result

            # Convert toxicity to risk
            toxicity_risk = self._calculate_toxicity_risk(toxicity_result)
            results["breakdown"]["toxicity_component"] = toxicity_risk * 0.25

            results["evidence"].append(
                {
                    "module": "Toxicity Detection v3",
                    "finding": f"Severity: {toxicity_result['severity']} (Score: {toxicity_result['overall_score']:.2f})",
                    "risk_contribution": f"{toxicity_risk}/100",
                }
            )

            if toxicity_result["is_toxic"]:
                results["recommendations"].append(
                    f"⚠️ Toxic content detected: {', '.join(toxicity_result['categories'])}"
                )

        # Component 3: Fact-Checking (40% weight - most important)
        if self.fact_checker and self.use_fact_checking:
            fact_result = self.fact_checker.check(text, url)
            results["raw_scores"]["fact_check"] = fact_result

            # Convert credibility to risk (low credibility = high risk)
            credibility_risk = 100 - fact_result["score"]  # Invert score
            results["breakdown"]["fake_news_component"] = credibility_risk * 0.40

            results["evidence"].append(
                {
                    "module": "Fact-Checking v3",
                    "finding": f"{fact_result['verdict']} ({fact_result['confidence']} confidence)",
                    "risk_contribution": f"{credibility_risk}/100",
                }
            )

            if fact_result["verdict"] in ["False", "Likely False"]:
                results["recommendations"].append(
                    f"⚠️ Questionable claims detected - verify with multiple sources"
                )

        # Component 4: Source Credibility (10% weight)
        if url and self.fact_checker and self.fact_checker.source_analyzer:
            source_result = self.fact_checker.source_analyzer.analyze(url)
            if source_result:
                results["raw_scores"]["source"] = source_result

                # Convert source reputation to risk (low reputation = high risk)
                source_risk = 100 - source_result["reputation_score"]
                results["breakdown"]["source_component"] = source_risk * 0.10

                results["evidence"].append(
                    {
                        "module": "Source Analysis v3",
                        "finding": f"{source_result['verdict']} (Score: {source_result['reputation_score']}/100)",
                        "risk_contribution": f"{source_risk}/100",
                    }
                )

                if source_result["risk_factors"]:
                    results["recommendations"].append(
                        f"⚠️ Source risks: {', '.join(source_result['risk_factors'])}"
                    )

        # Component 5: Manipulation Indicators (10% weight)
        manipulation_risk = self._detect_manipulation_patterns(text)
        results["breakdown"]["manipulation_component"] = manipulation_risk * 0.10
        results["raw_scores"]["manipulation"] = manipulation_risk

        if manipulation_risk > 50:
            results["evidence"].append(
                {
                    "module": "Manipulation Detection",
                    "finding": "Potential manipulative patterns detected",
                    "risk_contribution": f"{manipulation_risk}/100",
                }
            )
            results["recommendations"].append(
                "⚠️ Content shows signs of manipulation (clickbait, sensationalism)"
            )

        # Calculate final risk score
        results["risk_score"] = sum(results["breakdown"].values())
        results["risk_score"] = max(
            0, min(100, results["risk_score"])
        )  # Clamp to 0-100

        # Determine risk level
        results["risk_level"] = self._calculate_risk_level(results["risk_score"])

        # Add summary recommendations
        if results["risk_level"] == "Critical":
            results["recommendations"].insert(
                0, "🚨 CRITICAL: Do NOT share or trust this content"
            )
        elif results["risk_level"] == "High":
            results["recommendations"].insert(
                0, "⚠️ HIGH RISK: Verify thoroughly before trusting"
            )
        elif results["risk_level"] == "Medium":
            results["recommendations"].insert(
                0, "⚠️ MODERATE RISK: Exercise caution and verify claims"
            )
        else:
            results["recommendations"].insert(
                0, "✅ LOW RISK: Content appears relatively safe"
            )

        return results

    def _calculate_sentiment_risk(self, sentiment_result: Dict) -> int:
        """
        Convert sentiment to risk score
        Extreme emotions (very positive/negative) indicate potential manipulation
        """
        # Handle both 'sentiment' (v2) and 'label' (v3) keys
        sentiment = sentiment_result.get("sentiment") or sentiment_result.get(
            "label", "Neutral"
        )
        sentiment = sentiment.lower()
        confidence = sentiment_result.get("confidence", 0.5)
        intensity = sentiment_result.get("intensity", "Moderate")

        # Base risk from sentiment
        if sentiment == "neutral":
            risk = 10  # Low risk
        elif sentiment == "positive":
            # Extremely positive can be misleading/clickbait
            if intensity == "Strong":
                risk = 40
            elif intensity == "Moderate":
                risk = 20
            else:
                risk = 10
        elif sentiment == "negative":
            # Negative sentiment can indicate fear-mongering
            if intensity == "Strong":
                risk = 50
            elif intensity == "Moderate":
                risk = 30
            else:
                risk = 15
        else:
            risk = 25  # Unknown

        # Adjust for confidence
        risk = int(risk * confidence)

        return min(100, risk)

    def _calculate_toxicity_risk(self, toxicity_result: Dict) -> int:
        """Convert toxicity to risk score"""
        if not toxicity_result["is_toxic"]:
            return 10  # Low baseline risk

        # Map severity to risk
        severity_map = {"None": 10, "Low": 30, "Medium": 55, "High": 75, "Critical": 95}

        severity = toxicity_result.get("severity", "None")
        return severity_map.get(severity, 50)

    def _detect_manipulation_patterns(self, text: str) -> int:
        """
        Detect manipulative patterns (clickbait, sensationalism, etc.)
        Returns risk score 0-100
        """
        risk = 0
        text_lower = text.lower()

        # Clickbait indicators
        clickbait_patterns = [
            "you won't believe",
            "shocking",
            "this will blow your mind",
            "doctors hate",
            "one weird trick",
            "what happens next",
            "number 7 will shock you",
            "click here",
            "urgent",
            "breaking:",
            "exclusive:",
            "secret",
            "revealed",
            "exposed",
        ]

        clickbait_count = sum(
            1 for pattern in clickbait_patterns if pattern in text_lower
        )
        risk += min(40, clickbait_count * 15)

        # Excessive punctuation
        exclamation_count = text.count("!")
        question_count = text.count("?")
        if exclamation_count > 3 or question_count > 3:
            risk += 20

        # ALL CAPS (shouting)
        words = text.split()
        caps_ratio = sum(1 for word in words if word.isupper() and len(word) > 2) / max(
            len(words), 1
        )
        if caps_ratio > 0.3:
            risk += 25

        # Emotional manipulation keywords (Vietnamese + English)
        emotional_keywords = [
            "khủng khiếp",
            "kinh hoàng",
            "sốc",
            "chấn động",
            "terrible",
            "horrible",
            "disaster",
            "crisis",
            "amazing",
            "incredible",
            "unbelievable",
            "miracle",
        ]

        emotional_count = sum(
            1 for keyword in emotional_keywords if keyword in text_lower
        )
        risk += min(30, emotional_count * 10)

        return min(100, risk)

    def _calculate_risk_level(self, score: int) -> str:
        """Determine risk level from score"""
        if score >= 76:
            return "Critical"
        elif score >= 51:
            return "High"
        elif score >= 26:
            return "Medium"
        else:
            return "Low"

    def _empty_result(self) -> Dict:
        """Return empty result for invalid input"""
        return {
            "risk_score": 0,
            "risk_level": "Unknown",
            "breakdown": {
                "fake_news_component": 0,
                "toxicity_component": 0,
                "sentiment_component": 0,
                "source_component": 0,
                "manipulation_component": 0,
            },
            "raw_scores": {},
            "evidence": [],
            "recommendations": ["No content provided"],
        }


# Convenience function
def calculate_risk(text: str, url: Optional[str] = None) -> Dict:
    """Quick risk calculation"""
    scorer = RiskScorerV3()
    return scorer.score(text, url)


if __name__ == "__main__":
    # Quick test
    scorer = RiskScorerV3()

    test_cases = [
        ("You won't believe this SHOCKING news! Click here NOW!!!", None),
        ("Việt Nam công bố kết quả kinh tế quý 1/2024", "https://vnexpress.net"),
        ("Đồ ngu ngốc, tao giết mày!", None),
        ("This is a neutral informative article about science.", "https://bbc.com"),
    ]

    print("\n🧪 Testing Risk Scorer v3:")
    for text, url in test_cases:
        result = scorer.score(text, url)
        print(f"\nText: {text[:60]}...")
        print(f"Risk Score: {result['risk_score']:.1f}/100")
        print(f"Risk Level: {result['risk_level']}")
        print(f"Recommendation: {result['recommendations'][0]}")
