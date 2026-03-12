"""
VnContentGuard Pro V7 - Fact-Checking System
=============================================
Multi-source fact verification system with:
1. Google Fact Check Tools API - Known fact-checks from multiple organizations
2. Source credibility analysis - Domain age, SSL, reputation scoring
3. NewsData.io cross-reference - Verify against credible news sources
4. Gemini AI synthesis - Final verification with evidence

Fallback chain: Source analysis → Gemini (always available)
External APIs (Google Fact Check, NewsData) enhance results when available
"""

import os
import re
import urllib.parse
from datetime import datetime
from typing import Dict, List, Optional

import validators
from dotenv import load_dotenv

load_dotenv()


class FactCheckerV7:
    """
    Advanced Multi-Source Fact-Checking System

    Verification Layers:
    1. Google Fact Check API - Check against known fact-checks
    2. Source Credibility - Analyze domain reputation, age, SSL
    3. NewsData.io - Cross-reference with credible news
    4. Gemini AI - Contextual verification and synthesis

    Credibility Score: 0-100 (0=fake, 100=verified true)
    """

    def __init__(self, key_rotator=None):
        print("⏳ Initializing Fact-Checking System V7...")

        # API Keys
        self.google_factcheck_key = os.getenv("GOOGLE_FACT_CHECK_API_KEY")
        self.newsdata_key = os.getenv("NEWSDATA_API_KEY")
        self.gnews_key = os.getenv("GNEWS_API_KEY")

        # Feature flags
        self.use_fact_checking = (
            os.getenv("USE_FACT_CHECKING", "true").lower() == "true"
        )
        self.use_news_crossref = (
            os.getenv("USE_NEWS_CROSS_REF", "true").lower() == "true"
        )

        # Import source analyzer
        try:
            from .source_analyzer_v7 import SourceAnalyzer

            self.source_analyzer = SourceAnalyzer()
            print("✅ Source analyzer loaded")
        except Exception as e:
            print(f"⚠️ Source analyzer unavailable: {e}")
            self.source_analyzer = None

        # Initialize Gemini for AI verification (use shared rotator if provided)
        try:
            from google import genai

            from .gemini_llm import API_KEY_POOL, MODEL_NAME, APIKeyRotator

            self.key_rotator = (
                key_rotator if key_rotator else APIKeyRotator(API_KEY_POOL)
            )
            api_key = self.key_rotator.get_current_key()
            self.gemini_client = genai.Client(api_key=api_key) if api_key else None
            self.model_name = MODEL_NAME
            if self.gemini_client:
                print("✅ Gemini AI verification ready")
            else:
                print("⚠️ Gemini AI: no available API key")
        except Exception as e:
            print(f"⚠️ Gemini unavailable: {e}")
            self.gemini_client = None
            self.key_rotator = None

        # Log API availability
        if self.google_factcheck_key:
            print("✅ Google Fact Check API configured")
        else:
            print("⚠️ Google Fact Check API not configured (optional)")

        if self.newsdata_key:
            print("✅ NewsData.io API configured")
        else:
            print("⚠️ NewsData.io API not configured (optional)")

        print("✅ Fact-Checker V7 Ready!")

    def check(self, text: str, url: Optional[str] = None) -> Dict:
        """
        Check factuality of text/claim using multiple sources

        Args:
            text: Text or claim to verify
            url: Optional source URL for credibility analysis

        Returns:
            Dict with verification results including:
            - score: int (0-100, credibility score)
            - verdict: str (Verified True/Likely True/Unclear/Likely False/False)
            - confidence: str (Low/Medium/High)
            - evidence: list of evidence from various sources
            - source_credibility: dict (if URL provided)
        """
        if not text or not text.strip():
            return self._empty_result()

        results = {
            "score": 50,  # Neutral starting point
            "verdict": "Chưa rõ",
            "confidence": "Thấp",
            "evidence": [],
            "source_credibility": None,
            "cross_references": 0,
            "verification_methods": [],
        }

        # Layer 1: Source credibility analysis (if URL provided)
        if url and self.source_analyzer:
            source_result = self.source_analyzer.analyze(url)
            if source_result:
                results["source_credibility"] = source_result
                results["verification_methods"].append("source_analysis")
                # Influence score based on source credibility
                if source_result["reputation_score"] >= 80:
                    results["score"] += 10
                elif source_result["reputation_score"] <= 30:
                    results["score"] -= 15

        # Layer 2: Google Fact Check API (if configured)
        if self.google_factcheck_key and self.use_fact_checking:
            factcheck_result = self._check_google_factcheck(text)
            if factcheck_result:
                results["evidence"].extend(factcheck_result["claims"])
                results["verification_methods"].append("google_factcheck")
                # Adjust score based on fact-check ratings
                results["score"] = self._adjust_score_from_factchecks(
                    results["score"], factcheck_result["claims"]
                )

        # Layer 3: NewsData.io cross-reference (if configured)
        if self.newsdata_key and self.use_news_crossref:
            crossref_result = self._check_news_crossreference(text)
            if crossref_result:
                results["cross_references"] = crossref_result["match_count"]
                results["verification_methods"].append("news_crossref")
                # More credible sources = higher score
                if crossref_result["match_count"] >= 3:
                    results["score"] += 15
                elif crossref_result["match_count"] == 0:
                    results["score"] -= 10

        # Layer 4: Gemini AI verification (always available)
        if self.gemini_client:
            ai_result = self._verify_with_gemini(text, url)
            if ai_result:
                results["evidence"].append(ai_result)
                results["verification_methods"].append("gemini_ai")
                # AI provides additional confidence
                if ai_result["assessment"] == "likely_true":
                    results["score"] += 5
                elif ai_result["assessment"] == "likely_false":
                    results["score"] -= 5

        # Final verdict and confidence
        results["score"] = max(0, min(100, results["score"]))  # Clamp to 0-100
        results["verdict"] = self._calculate_verdict(results["score"])
        results["confidence"] = self._calculate_confidence(results)

        return results

    def _check_google_factcheck(self, query: str) -> Optional[Dict]:
        """Check Google Fact Check Tools API"""
        if not self.google_factcheck_key:
            return None
        try:
            import requests
            import urllib.parse as _up
            endpoint = "https://factchecktools.googleapis.com/v1alpha1/claims:search"
            params = {
                "query": query[:500],
                "key": self.google_factcheck_key,
                "languageCode": "vi",
                "pageSize": 5,
            }
            resp = requests.get(endpoint, params=params, timeout=8)
            if resp.status_code != 200:
                print(f"⚠️ Google Fact Check API error {resp.status_code}: {resp.text[:200]}")
                return None
            data = resp.json()
            claims_raw = data.get("claims", [])
            if not claims_raw:
                return None
            claims = []
            for item in claims_raw:
                text = item.get("text", "")
                for review in item.get("claimReview", []):
                    claims.append({
                        "claim": text,
                        "publisher": review.get("publisher", {}).get("name", ""),
                        "rating": review.get("textualRating", ""),
                        "url": review.get("url", ""),
                    })
            print(f"✅ Google Fact Check: found {len(claims)} claim reviews")
            return {"claims": claims}
        except Exception as e:
            print(f"⚠️ Google Fact Check request failed: {e}")
            return None

    def _check_news_crossreference(self, text: str) -> Optional[Dict]:
        """Cross-reference with NewsData.io, fallback to GNews"""
        if not self.newsdata_key and not self.gnews_key:
            return None
        try:
            import requests
            # Extract short query (first ~80 chars of meaningful text)
            query = text.strip()[:80]
            if not query:
                return None

            # Try NewsData.io first
            if self.newsdata_key:
                params = {
                    "apikey": self.newsdata_key,
                    "q": query,
                    "language": "vi",
                    "size": 5,
                }
                resp = requests.get("https://newsdata.io/api/1/news",
                                    params=params, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    articles = data.get("results", [])
                    sources = list({a.get("source_id", "") for a in articles if a.get("source_id")})
                    match_count = len(articles)
                    print(f"✅ NewsData.io: found {match_count} matching articles")
                    return {
                        "match_count": match_count,
                        "sources": sources,
                        "articles": [
                            {"title": a.get("title", ""), "source": a.get("source_id", ""),
                             "url": a.get("link", ""), "published": a.get("pubDate", "")}
                            for a in articles[:5]
                        ],
                    }
                else:
                    print(f"⚠️ NewsData.io error {resp.status_code}: {resp.text[:200]}")

            # Fallback to GNews
            if self.gnews_key:
                params = {
                    "apikey": self.gnews_key,
                    "q": query,
                    "lang": "vi",
                    "max": 5,
                }
                resp = requests.get("https://gnews.io/api/v4/search",
                                    params=params, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    articles = data.get("articles", [])
                    sources = list({a.get("source", {}).get("name", "") for a in articles})
                    match_count = len(articles)
                    print(f"✅ GNews fallback: found {match_count} matching articles")
                    return {
                        "match_count": match_count,
                        "sources": sources,
                        "articles": [
                            {"title": a.get("title", ""), "source": a.get("source", {}).get("name", ""),
                             "url": a.get("url", ""), "published": a.get("publishedAt", "")}
                            for a in articles[:5]
                        ],
                    }
                else:
                    print(f"⚠️ GNews error {resp.status_code}: {resp.text[:200]}")
        except Exception as e:
            print(f"⚠️ News cross-reference failed: {e}")
        return None

    def _check_newsdata(self, text: str) -> Optional[list]:
        """Alias used by api.py unified endpoint — returns list of article dicts."""
        result = self._check_news_crossreference(text)
        if result and result.get("articles"):
            return result["articles"]
        return []

    def _verify_with_gemini(self, text: str, url: Optional[str]) -> Optional[Dict]:
        """Verify using Gemini AI with key rotation on 429"""
        if not self.gemini_client:
            return None

        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Create verification prompt
                prompt = f"""Phân tích tính chính xác của nội dung sau:

Nội dung: "{text[:2000]}"
{f'URL nguồn: {url}' if url else ''}

Hãy đánh giá ngắn gọn bằng tiếng Việt:
1. Nội dung này có khả năng đúng, sai, hay không rõ ràng?
2. Các sự kiện hoặc vấn đề chính là gì?
3. Đánh giá tổng thể trong 2-3 câu.

Trả lời ngắn gọn, khách quan, bằng tiếng Việt."""

                response = self.gemini_client.models.generate_content(
                    model=self.model_name, contents=prompt
                )

                if self.key_rotator:
                    self.key_rotator.increment_request_count()

                analysis = response.text

                # Simple assessment extraction
                assessment = "unclear"
                if any(
                    word in analysis.lower()
                    for word in [
                        "likely true",
                        "appears true",
                        "verified",
                        "có khả năng đúng",
                        "đúng sự thật",
                        "chính xác",
                        "khả năng cao là đúng",
                        "tương đối chính xác",
                    ]
                ):
                    assessment = "likely_true"
                elif any(
                    word in analysis.lower()
                    for word in [
                        "likely false",
                        "appears false",
                        "misleading",
                        "fake",
                        "có khả năng sai",
                        "sai sự thật",
                        "gây hiểu lầm",
                        "thông tin giả",
                        "không chính xác",
                    ]
                ):
                    assessment = "likely_false"

                return {
                    "source": "Gemini AI",
                    "assessment": assessment,
                    "analysis": analysis[:500],
                }
            except Exception as e:
                error_str = str(e)
                error_lower = error_str.lower()
                print(f"⚠️ Gemini verification failed: {e}")
                if (
                    "429" in error_lower
                    or "quota" in error_lower
                    or "exhausted" in error_lower
                ) and self.key_rotator:
                    from src.models.gemini_llm import APIKeyRotator

                    retry_delay = APIKeyRotator.parse_retry_delay(error_str)
                    self.key_rotator.mark_key_rate_limited(retry_delay)
                    from google import genai

                    api_key = self.key_rotator.get_current_key()
                    if api_key:
                        self.gemini_client = genai.Client(api_key=api_key)
                        continue
                return None
        return None

    def _adjust_score_from_factchecks(
        self, current_score: int, claims: List[Dict]
    ) -> int:
        """Adjust score based on fact-check ratings"""
        if not claims:
            return current_score

        # Map fact-check ratings to score adjustments
        rating_adjustments = {
            "true": 20,
            "mostly true": 10,
            "half true": 0,
            "mostly false": -10,
            "false": -20,
            "pants on fire": -30,
        }

        total_adjustment = 0
        for claim in claims:
            rating = claim.get("rating", "").lower()
            for key, adjustment in rating_adjustments.items():
                if key in rating:
                    total_adjustment += adjustment
                    break

        return current_score + total_adjustment

    def _calculate_verdict(self, score: int) -> str:
        """Calculate verdict from score"""
        if score >= 80:
            return "Đã xác minh đúng"
        elif score >= 60:
            return "Có thể đúng"
        elif score >= 40:
            return "Chưa rõ"
        elif score >= 20:
            return "Có thể sai"
        else:
            return "Sai"

    def _calculate_confidence(self, results: Dict) -> str:
        """Calculate confidence level"""
        method_count = len(results["verification_methods"])
        evidence_count = len(results["evidence"])

        if method_count >= 3 and evidence_count >= 2:
            return "Cao"
        elif method_count >= 2 or evidence_count >= 1:
            return "Trung bình"
        else:
            return "Thấp"

    def _empty_result(self) -> Dict:
        """Return empty result for invalid input"""
        return {
            "score": 50,
            "verdict": "Chưa rõ",
            "confidence": "Thấp",
            "evidence": [],
            "source_credibility": None,
            "cross_references": 0,
            "verification_methods": [],
        }


# Convenience function
def check_fact(text: str, url: Optional[str] = None) -> Dict:
    """Quick fact check"""
    checker = FactCheckerV7()
    return checker.check(text, url)


if __name__ == "__main__":
    # Quick test
    checker = FactCheckerV7()

    test_cases = [
        ("Việt Nam có 54 dân tộc", None),
        ("Trái đất là phẳng", None),
        ("COVID-19 vaccine causes autism", None),
    ]

    print("\n🧪 Testing Fact-Checker V7:")
    for text, url in test_cases:
        result = checker.check(text, url)
        print(f"\nClaim: {text}")
        print(f"Score: {result['score']}/100")
        print(f"Verdict: {result['verdict']}")
        print(f"Confidence: {result['confidence']}")
        print(f"Methods: {result['verification_methods']}")
