"""
Tests for VnContentGuard Pro v5 - Fact-Checking System
=======================================================
Comprehensive tests for:
- FactCheckerV5
- SourceAnalyzer
- NewsAggregator
"""

import os
import sys
from datetime import datetime

import pytest

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.models.fact_checker_v5 import FactCheckerV5, check_fact
from src.models.news_aggregator_v5 import NewsAggregator, search_news
from src.models.source_analyzer_v5 import SourceAnalyzer, analyze_source

# ==================== FactCheckerV5 Tests ====================


class TestFactCheckerV5:
    """Test suite for FactCheckerV5"""

    def setup_method(self):
        """Setup before each test"""
        self.checker = FactCheckerV5()

    def test_initialization(self):
        """Test fact checker initializes correctly"""
        assert self.checker is not None
        assert hasattr(self.checker, "check")
        assert hasattr(self.checker, "source_analyzer")
        assert hasattr(self.checker, "gemini_client")
        print("✅ FactCheckerV5 initialization test passed")

    def test_empty_input(self):
        """Test handling of empty input"""
        result = self.checker.check("")
        assert result["score"] == 50
        assert result["verdict"] == "Unclear"
        assert result["confidence"] == "Low"
        print("✅ Empty input handling test passed")

    def test_check_without_url(self):
        """Test fact checking without source URL"""
        result = self.checker.check("Việt Nam có 54 dân tộc")

        assert "score" in result
        assert "verdict" in result
        assert "confidence" in result
        assert "evidence" in result
        assert "verification_methods" in result

        assert 0 <= result["score"] <= 100
        assert result["verdict"] in [
            "Verified True",
            "Likely True",
            "Unclear",
            "Likely False",
            "False",
        ]
        assert result["confidence"] in ["Low", "Medium", "High"]

        print(f"✅ Fact check without URL test passed (Score: {result['score']})")

    def test_check_with_url(self):
        """Test fact checking with source URL"""
        result = self.checker.check(
            "Breaking news about technology", url="https://vnexpress.net/tin-tuc"
        )

        assert "source_credibility" in result
        # Source credibility should be present if URL provided
        if result["source_credibility"]:
            assert "reputation_score" in result["source_credibility"]
            assert "domain" in result["source_credibility"]

        print(f"✅ Fact check with URL test passed")

    def test_likely_true_claim(self):
        """Test with a likely true claim"""
        result = self.checker.check("The Earth orbits around the Sun")

        # Should have verification methods (unless API quota exhausted)
        # At minimum, we get a result structure
        assert result is not None
        assert "verification_methods" in result
        # Score should be reasonable (not extreme)
        assert 30 <= result["score"] <= 100

        print(
            f"✅ Likely true claim test passed (Score: {result['score']}, Verdict: {result['verdict']}, Methods: {len(result['verification_methods'])})"
        )

    def test_likely_false_claim(self):
        """Test with a likely false claim"""
        result = self.checker.check("The Earth is flat")

        # Should have verification methods (unless API quota exhausted)
        assert result is not None
        assert "verification_methods" in result
        # Score should be low or moderate
        assert result["score"] <= 80

        print(
            f"✅ Likely false claim test passed (Score: {result['score']}, Verdict: {result['verdict']}, Methods: {len(result['verification_methods'])})"
        )

    def test_vietnamese_claim(self):
        """Test with Vietnamese text"""
        result = self.checker.check("Hà Nội là thủ đô của Việt Nam")

        assert result is not None
        assert "score" in result
        # Should return reasonable verdict
        assert result["verdict"] in [
            "Verified True",
            "Likely True",
            "Unclear",
            "Likely False",
            "False",
        ]

        print(f"✅ Vietnamese claim test passed (Verdict: {result['verdict']})")

    def test_ambiguous_claim(self):
        """Test with ambiguous/unclear claim"""
        result = self.checker.check("This product is the best in the world")

        # Ambiguous claims should have lower confidence
        assert result["confidence"] in ["Low", "Medium"]
        assert result["verdict"] in ["Unclear", "Likely True", "Likely False"]

        print(f"✅ Ambiguous claim test passed (Confidence: {result['confidence']})")

    def test_score_clamping(self):
        """Test that scores are clamped to 0-100 range"""
        # Test with various inputs
        test_cases = [
            "Completely verified true fact",
            "Highly questionable claim",
            "Neutral statement without claims",
        ]

        for text in test_cases:
            result = self.checker.check(text)
            assert (
                0 <= result["score"] <= 100
            ), f"Score {result['score']} out of range for: {text}"

        print("✅ Score clamping test passed")

    def test_convenience_function(self):
        """Test convenience function check_fact()"""
        result = check_fact("Test claim", url="https://example.com")

        assert result is not None
        assert "score" in result
        assert "verdict" in result

        print("✅ Convenience function test passed")


# ==================== SourceAnalyzer Tests ====================


class TestSourceAnalyzer:
    """Test suite for SourceAnalyzer"""

    def setup_method(self):
        """Setup before each test"""
        self.analyzer = SourceAnalyzer()

    def test_initialization(self):
        """Test source analyzer initializes correctly"""
        assert self.analyzer is not None
        assert hasattr(self.analyzer, "trusted_domains")
        assert hasattr(self.analyzer, "suspicious_patterns")
        assert len(self.analyzer.trusted_domains) > 0
        print("✅ SourceAnalyzer initialization test passed")

    def test_trusted_domain(self):
        """Test analysis of trusted Vietnamese domain"""
        result = self.analyzer.analyze("https://vnexpress.net")

        assert result is not None
        assert result["domain"] == "vnexpress.net"
        assert result["reputation_score"] >= 80  # Should be highly trusted
        assert result["verdict"] in ["Trusted", "Generally Credible"]

        print(f"✅ Trusted domain test passed (Score: {result['reputation_score']})")

    def test_international_trusted_domain(self):
        """Test analysis of trusted international domain"""
        result = self.analyzer.analyze("https://bbc.com")

        assert result is not None
        assert "bbc.com" in result["domain"]
        assert result["reputation_score"] >= 80

        print(f"✅ International trusted domain test passed")

    def test_unknown_domain(self):
        """Test analysis of unknown/neutral domain"""
        result = self.analyzer.analyze("https://example-news-site.com")

        assert result is not None
        # Unknown domains should have neutral score (~50)
        assert 30 <= result["reputation_score"] <= 70

        print(f"✅ Unknown domain test passed (Score: {result['reputation_score']})")

    def test_suspicious_domain(self):
        """Test analysis of suspicious domain patterns"""
        suspicious_urls = [
            "https://viral-news-2024.xyz",
            "https://fakene-ws.com",
            "https://clickbait-headlines.com",
        ]

        for url in suspicious_urls:
            result = self.analyzer.analyze(url)
            if result and "Suspicious domain pattern" in result["risk_factors"]:
                # Suspicious domains should have lower scores
                assert result["reputation_score"] < 60
                print(f"✅ Suspicious domain detected: {url}")

    def test_invalid_url(self):
        """Test handling of invalid URLs"""
        result = self.analyzer.analyze("not-a-valid-url")

        # Should return invalid result or handle gracefully
        assert result is not None
        # Either marked as invalid or has very low score
        if result["verdict"] == "Invalid":
            assert result["reputation_score"] == 0

        print("✅ Invalid URL handling test passed")

    def test_url_with_path(self):
        """Test URL with path/article"""
        result = self.analyzer.analyze(
            "https://vnexpress.net/tin-tuc/chinh-tri/article123"
        )

        assert result is not None
        assert "vnexpress.net" in result["domain"]
        # Should recognize trusted domain despite path
        assert result["reputation_score"] >= 80

        print("✅ URL with path test passed")

    def test_ssl_validation(self):
        """Test SSL certificate validation"""
        # Test with known HTTPS site
        result = self.analyzer.analyze("https://vnexpress.net")

        if result and result["ssl_valid"] is not None:
            # If SSL check ran, verify it's boolean
            assert isinstance(result["ssl_valid"], bool)
            print(f"✅ SSL validation test passed (Valid: {result['ssl_valid']})")
        else:
            print("⚠️ SSL validation skipped (check may have timed out)")

    def test_risk_factors(self):
        """Test risk factors detection"""
        # Very new or suspicious domain should have risk factors
        result = self.analyzer.analyze("https://brand-new-site-2025.xyz")

        assert "risk_factors" in result
        assert isinstance(result["risk_factors"], list)

        print(f"✅ Risk factors test passed (Factors: {len(result['risk_factors'])})")

    def test_score_range(self):
        """Test that reputation scores are in valid range"""
        test_urls = [
            "https://vnexpress.net",
            "https://example.com",
            "https://suspicious-site.xyz",
        ]

        for url in test_urls:
            result = self.analyzer.analyze(url)
            if result:
                assert 0 <= result["reputation_score"] <= 100

        print("✅ Score range test passed")

    def test_convenience_function(self):
        """Test convenience function analyze_source()"""
        result = analyze_source("https://vietnamnet.vn")

        assert result is not None
        assert "reputation_score" in result

        print("✅ Convenience function test passed")


# ==================== NewsAggregator Tests ====================


class TestNewsAggregator:
    """Test suite for NewsAggregator"""

    def setup_method(self):
        """Setup before each test"""
        self.aggregator = NewsAggregator()

    def test_initialization(self):
        """Test news aggregator initializes correctly"""
        assert self.aggregator is not None
        assert hasattr(self.aggregator, "search")
        assert hasattr(self.aggregator, "cache")
        print("✅ NewsAggregator initialization test passed")

    def test_empty_query(self):
        """Test handling of empty query"""
        result = self.aggregator.search("")

        assert result["match_count"] == 0
        assert result["match_score"] == 0
        assert len(result["articles"]) == 0

        print("✅ Empty query handling test passed")

    def test_search_returns_structure(self):
        """Test search returns correct structure"""
        # Note: May not return results if API keys not configured
        result = self.aggregator.search("test query")

        assert "match_count" in result
        assert "articles" in result
        assert "sources" in result
        assert "match_score" in result
        assert "api_used" in result

        assert isinstance(result["match_count"], int)
        assert isinstance(result["articles"], list)
        assert isinstance(result["sources"], list)
        assert 0 <= result["match_score"] <= 100

        print(f"✅ Search structure test passed (Matches: {result['match_count']})")

    def test_caching(self):
        """Test result caching"""
        query = "test query for caching"

        # First search
        result1 = self.aggregator.search(query)
        cache_size_before = len(self.aggregator.cache)

        # Second search (should hit cache)
        result2 = self.aggregator.search(query)
        cache_size_after = len(self.aggregator.cache)

        # Cache should contain the query
        assert cache_size_after >= cache_size_before
        # Results should be identical
        assert result1["match_count"] == result2["match_count"]

        print("✅ Caching test passed")

    def test_language_parameter(self):
        """Test language parameter handling"""
        # Test Vietnamese
        result_vi = self.aggregator.search("tin tức", language="vi")
        assert result_vi is not None

        # Test English
        result_en = self.aggregator.search("news", language="en")
        assert result_en is not None

        print("✅ Language parameter test passed")

    def test_match_score_calculation(self):
        """Test match score calculation"""
        result = self.aggregator.search("common topic")

        # Match score should be proportional to match count
        expected_score = min(100, result["match_count"] * 10)
        assert result["match_score"] == expected_score

        print(
            f"✅ Match score calculation test passed (Score: {result['match_score']})"
        )

    def test_no_api_keys_fallback(self):
        """Test graceful handling when API keys not configured"""
        # Even without API keys, should return empty result, not crash
        result = self.aggregator.search("any query")

        assert result is not None
        assert "match_count" in result
        # Without API keys, should return empty result
        if not self.aggregator.newsdata_key and not self.aggregator.gnews_key:
            assert result["match_count"] == 0

        print("✅ No API keys fallback test passed")

    def test_convenience_function(self):
        """Test convenience function search_news()"""
        result = search_news("test")

        assert result is not None
        assert "match_count" in result

        print("✅ Convenience function test passed")


# ==================== Integration Tests ====================


class TestIntegration:
    """Integration tests for all Week 3 components"""

    def test_full_pipeline_with_url(self):
        """Test full fact-checking pipeline with URL"""
        checker = FactCheckerV5()

        result = checker.check(
            text="Technology news update", url="https://vnexpress.net"
        )

        # Should have multiple verification methods
        assert len(result["verification_methods"]) > 0
        # Should have source credibility analysis
        assert result["source_credibility"] is not None
        # Should have final verdict
        assert result["verdict"] is not None

        print(f"✅ Full pipeline test passed")
        print(f"   Methods: {result['verification_methods']}")
        print(f"   Score: {result['score']}/100")
        print(f"   Verdict: {result['verdict']}")

    def test_components_integration(self):
        """Test that all components work together"""
        # Initialize all components
        checker = FactCheckerV5()
        analyzer = SourceAnalyzer()
        aggregator = NewsAggregator()

        # Each should work independently
        fact_result = checker.check("Test claim")
        source_result = analyzer.analyze("https://bbc.com")
        news_result = aggregator.search("test")

        assert fact_result is not None
        assert source_result is not None
        assert news_result is not None

        print("✅ Components integration test passed")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🧪 VnContentGuard Pro v5 - Fact-Checking Test Suite")
    print("=" * 60 + "\n")

    # Run pytest
    pytest.main([__file__, "-v", "--tb=short"])
