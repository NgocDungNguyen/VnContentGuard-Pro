"""
VnContentGuard Pro V7 - Advanced Multi-Layer Toxicity Detection
================================================================
Implements 4-layer defense-in-depth toxicity detection:
1. Regex patterns (500+ Vietnamese patterns) - Fast, offline
2. Detoxify model (ML-based) - Offline, multilingual
3. Perspective API (Google) - Online, advanced
4. Gemini AI (contextual) - Online, context-aware

Fallback chain: Detoxify → Regex → Perspective (if available) → Gemini (if available)
"""

import os
import re
from typing import Dict, List, Optional

from dotenv import load_dotenv

# Import v2 toxicity for fallback
from .toxicity import ToxicityAnalyzer as ToxicityV2

load_dotenv()


class ToxicityAnalyzerV7:
    """
    Advanced Multi-Layer Toxicity Detection System

    Detection Layers:
    1. Regex (v2) - Instant, high-precision Vietnamese patterns
    2. Detoxify - ML model, offline, multilingual
    3. Perspective API - Google's advanced detection (if available)
    4. Gemini AI - Contextual analysis (if available)

    Severity Levels: Low (0.3-0.5), Medium (0.5-0.7), High (0.7-0.9), Critical (0.9-1.0)
    """

    def __init__(self, use_detoxify: bool = False):
        print("⏳ Initializing Advanced Toxicity Detection V7...")

        # Layer 1: v2 Regex patterns (fallback)
        try:
            self.regex_analyzer = ToxicityV2()
            print("✅ Layer 1: Regex patterns loaded (500+ patterns)")
        except Exception as e:
            print(f"⚠️ Warning: Regex analyzer failed: {e}")
            self.regex_analyzer = None

        # Layer 2: Detoxify model (disabled by default for faster startup)
        self.detoxify_model = None
        if use_detoxify:
            try:
                from detoxify import Detoxify

                # Use 'multilingual' model for better Vietnamese support
                self.detoxify_model = Detoxify("multilingual")
                print("✅ Layer 2: Detoxify multilingual model loaded")
            except Exception as e:
                print(f"⚠️ Warning: Detoxify model failed to load: {e}")
        else:
            print("⚠️ Layer 2: Detoxify model disabled (use_detoxify=False)")

        # Layer 3: Perspective API (optional)
        self.perspective_api_key = os.getenv("GOOGLE_PERSPECTIVE_API_KEY")
        if self.perspective_api_key:
            print("✅ Layer 3: Perspective API key configured")
        else:
            print("⚠️ Layer 3: Perspective API not configured (optional)")

        # Layer 4: Gemini AI (optional, for context)
        self.use_gemini = os.getenv("USE_GEMINI_TOXICITY", "false").lower() == "true"
        if self.use_gemini:
            print("✅ Layer 4: Gemini AI context analysis enabled")
        else:
            print(
                "⚠️ Layer 4: Gemini AI disabled (enable with USE_GEMINI_TOXICITY=true)"
            )

        print("✅ Toxicity Analyzer V7 Ready!")

    def analyze(self, text: str) -> Dict:
        """
        Analyze text for toxicity using multi-layer detection

        Args:
            text: Text to analyze

        Returns:
            Dict with toxicity analysis results including:
            - is_toxic: bool
            - overall_score: float (0-1)
            - severity: str (Low/Medium/High/Critical)
            - categories: dict of category scores
            - detection_method: str (which layer detected)
            - details: detailed breakdown
        """
        if not text or not text.strip():
            return self._empty_result()

        results = {
            "is_toxic": False,
            "overall_score": 0.0,
            "severity": "None",
            "categories": {},
            "detection_layers": [],
            "primary_method": None,
            "details": {},
        }

        # Layer 1: Detoxify model (primary)
        detoxify_result = self._analyze_detoxify(text)
        if detoxify_result:
            results["detection_layers"].append("detoxify")
            results["primary_method"] = "detoxify"
            results["categories"].update(detoxify_result["categories"])
            results["overall_score"] = max(
                results["overall_score"], detoxify_result["max_score"]
            )
            results["details"]["detoxify"] = detoxify_result

        # Layer 2: Regex patterns (always run for Vietnamese-specific patterns)
        regex_result = self._analyze_regex(text)
        if regex_result:
            results["detection_layers"].append("regex")
            if not results["primary_method"]:
                results["primary_method"] = "regex"
            if regex_result["is_toxic"]:
                results["categories"]["regex_patterns"] = 1.0
                results["overall_score"] = max(
                    results["overall_score"], 0.8
                )  # High confidence for regex
            results["details"]["regex"] = regex_result

        # Layer 3: Perspective API (if configured)
        if self.perspective_api_key:
            perspective_result = self._analyze_perspective(text)
            if perspective_result:
                results["detection_layers"].append("perspective")
                results["categories"].update(perspective_result["categories"])
                results["overall_score"] = max(
                    results["overall_score"], perspective_result["max_score"]
                )
                results["details"]["perspective"] = perspective_result

        # Determine toxicity and severity
        results["is_toxic"] = results["overall_score"] >= 0.5
        results["severity"] = self._calculate_severity(results["overall_score"])

        return results

    def _analyze_detoxify(self, text: str) -> Optional[Dict]:
        """Analyze using Detoxify model"""
        if not self.detoxify_model:
            return None

        try:
            predictions = self.detoxify_model.predict(text)

            # Detoxify categories: toxicity, severe_toxicity, obscene, threat, insult, identity_attack
            categories = {
                "toxicity": float(predictions.get("toxicity", 0)),
                "severe_toxicity": float(predictions.get("severe_toxicity", 0)),
                "obscene": float(predictions.get("obscene", 0)),
                "threat": float(predictions.get("threat", 0)),
                "insult": float(predictions.get("insult", 0)),
                "identity_attack": float(predictions.get("identity_attack", 0)),
            }

            max_score = max(categories.values())

            return {
                "categories": categories,
                "max_score": max_score,
                "method": "detoxify",
            }
        except Exception as e:
            print(f"⚠️ Detoxify analysis failed: {e}")
            return None

    def _analyze_regex(self, text: str) -> Optional[Dict]:
        """Analyze using ONLY v2 regex patterns (no Gemini AI calls).

        IMPORTANT: We directly scan against the regex blacklist patterns here
        instead of calling regex_analyzer.analyze_comments() because that method
        also triggers Gemini AI calls, burning API quota per comment.

        NEWS CONTEXT DETECTION: If the text appears to be a news article (contains
        journalistic indicators), we skip regex matching for violence/gore categories
        because words like "chết", "cháy", "thi thể" are normal in news reporting.
        """
        if not self.regex_analyzer:
            return None

        try:
            import re as _re

            lower_text = text.lower()

            # ----- NEWS CONTEXT DETECTION -----
            news_indicators = [
                r"(theo|nguồn|tin từ|phóng viên|báo cáo|thông tin từ|trả lời phỏng vấn)",
                r"(công an|cảnh sát|csgt|chính quyền|ubnd|chủ tịch|thủ tướng|bộ trưởng)",
                r"(bệnh viện|cấp cứu|nạn nhân|thiệt hại|hiện trường|nguyên nhân)",
                r"(ngày \d|tháng \d|\d+/\d+|\d+ giờ|sáng nay|tối qua|rạng sáng)",
                r"(quận|huyện|phường|xã|tỉnh|thành phố|tp\.|đường|phố)",
                r"(vụ việc|sự cố|sự kiện|vụ án|vụ cháy|vụ tai nạn|vụ va chạm)",
            ]

            news_score = sum(1 for p in news_indicators if _re.search(p, lower_text))
            is_news_context = news_score >= 3

            # Categories safe to skip for news articles
            news_safe_categories = {
                "Violence: Murder/Torture",
                "Violence: Torture",
                "Violence: Gore",
                "Self-Harm/Suicide",
                "Self-Harm: Slang/Evasion",
            }

            is_toxic = False
            matched_category = None
            matched_keyword = None

            for pattern, label in self.regex_analyzer.blacklist_patterns:
                if is_news_context and label in news_safe_categories:
                    continue

                match = _re.search(pattern, lower_text)
                if match:
                    is_toxic = True
                    matched_category = label
                    matched_keyword = match.group(0)
                    break

            return {
                "is_toxic": is_toxic,
                "toxic_count": 1 if is_toxic else 0,
                "news_context_detected": is_news_context,
                "patterns_matched": (
                    [
                        {
                            "category": matched_category,
                            "keyword": matched_keyword,
                        }
                    ]
                    if is_toxic
                    else []
                ),
                "method": "regex",
            }
        except Exception as e:
            print(f"⚠️ Regex analysis failed: {e}")
            return None

    def _analyze_perspective(self, text: str) -> Optional[Dict]:
        """Analyze using Google Perspective API (English text only)"""
        if not self.perspective_api_key:
            return None

        # Skip for Vietnamese text — Perspective doesn't support Vietnamese well
        # even with languages=["en"]. Only use for English-dominant text.
        import re as _re

        vietnamese_chars = _re.search(
            r"[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]",
            text.lower(),
        )
        if vietnamese_chars:
            return None  # Skip — Perspective can't handle Vietnamese

        try:
            import requests

            url = f"https://commentanalyzer.googleapis.com/v1alpha1/comments:analyze?key={self.perspective_api_key}"
            payload = {
                "comment": {"text": text[:3000]},
                "languages": [
                    "en"
                ],  # Vietnamese not supported by any attribute — use English detection
                "requestedAttributes": {
                    "TOXICITY": {},
                    "SEVERE_TOXICITY": {},
                    "INSULT": {},
                    "THREAT": {},
                },
            }

            resp = requests.post(url, json=payload, timeout=10)
            if resp.status_code != 200:
                # Log full error for debugging
                try:
                    err_body = resp.json()
                    err_msg = err_body.get("error", {}).get("message", resp.text[:200])
                except Exception:
                    err_msg = resp.text[:200]
                print(f"⚠️ Perspective API error {resp.status_code}: {err_msg}")
                return None

            data = resp.json()
            scores = data.get("attributeScores", {})

            categories = {}
            for attr, info in scores.items():
                score = info.get("summaryScore", {}).get("value", 0.0)
                categories[attr.lower()] = float(score)

            max_score = max(categories.values()) if categories else 0.0

            return {
                "categories": categories,
                "max_score": max_score,
                "method": "perspective",
            }
        except Exception as e:
            print(f"⚠️ Perspective API failed: {e}")
            return None

    def _calculate_severity(self, score: float) -> str:
        """Calculate severity level from score"""
        if score >= 0.9:
            return "Critical"
        elif score >= 0.7:
            return "High"
        elif score >= 0.5:
            return "Medium"
        elif score >= 0.3:
            return "Low"
        else:
            return "None"

    def _empty_result(self) -> Dict:
        """Return empty result for invalid input"""
        return {
            "is_toxic": False,
            "overall_score": 0.0,
            "severity": "None",
            "categories": {},
            "detection_layers": [],
            "primary_method": None,
            "details": {},
        }

    def analyze_batch(self, texts: List[str]) -> List[Dict]:
        """
        Analyze multiple texts for toxicity

        Args:
            texts: List of texts to analyze

        Returns:
            List of analysis results
        """
        return [self.analyze(text) for text in texts]

    def get_statistics(self, results: List[Dict]) -> Dict:
        """
        Calculate statistics from batch analysis results

        Args:
            results: List of analysis results

        Returns:
            Dict with statistics (toxic_count, avg_score, severity_distribution, etc.)
        """
        if not results:
            return {
                "total_analyzed": 0,
                "toxic_count": 0,
                "toxic_percentage": 0,
                "avg_score": 0,
                "severity_distribution": {},
            }

        toxic_count = sum(1 for r in results if r["is_toxic"])
        avg_score = sum(r["overall_score"] for r in results) / len(results)

        severity_counts = {}
        for r in results:
            severity = r["severity"]
            severity_counts[severity] = severity_counts.get(severity, 0) + 1

        return {
            "total_analyzed": len(results),
            "toxic_count": toxic_count,
            "toxic_percentage": (toxic_count / len(results)) * 100 if results else 0,
            "avg_score": round(avg_score, 3),
            "max_score": max(r["overall_score"] for r in results),
            "min_score": min(r["overall_score"] for r in results),
            "severity_distribution": severity_counts,
        }


# Convenience function
def analyze_toxicity(text: str) -> Dict:
    """Quick toxicity analysis"""
    analyzer = ToxicityAnalyzerV7()
    return analyzer.analyze(text)


if __name__ == "__main__":
    # Quick test
    analyzer = ToxicityAnalyzerV7()

    test_cases = [
        "Bài viết rất hay và hữu ích!",  # Clean
        "Đồ ngu ngốc, mày là thằng đần",  # Toxic insult
        "Tao sẽ giết mày",  # Severe threat
        "Thông tin rất bổ ích, cảm ơn bạn",  # Clean
    ]

    print("\n🧪 Testing Toxicity Analyzer V7:")
    for text in test_cases:
        result = analyzer.analyze(text)
        print(f"\nText: {text}")
        print(f"Toxic: {result['is_toxic']}")
        print(f"Score: {result['overall_score']:.3f}")
        print(f"Severity: {result['severity']}")
        print(f"Method: {result['primary_method']}")
        print(f"Layers: {result['detection_layers']}")
