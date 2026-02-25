"""
Unit Tests for VnContentGuard Pro v5 - Advanced Toxicity Detection
===================================================================
Tests multi-layer toxicity detection system with fallback mechanisms
"""

import os
import sys

import pytest

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.models.toxicity_v6 import ToxicityAnalyzerV6


class TestToxicityV5Initialization:
    """Test toxicity analyzer initialization"""

    def test_analyzer_initialization(self):
        """Test that analyzer initializes successfully"""
        analyzer = ToxicityAnalyzerV6()
        assert analyzer is not None
        assert analyzer.detoxify_model is not None
        assert analyzer.regex_analyzer is not None

    def test_detoxify_model_loaded(self):
        """Test that Detoxify model loads"""
        analyzer = ToxicityAnalyzerV6()
        assert analyzer.detoxify_model is not None


class TestCleanContent:
    """Test detection of clean (non-toxic) content"""

    def test_clean_vietnamese_text(self):
        """Test clean Vietnamese text"""
        analyzer = ToxicityAnalyzerV6()
        result = analyzer.analyze("Bài viết rất hay và hữu ích!")

        assert result["is_toxic"] == False
        assert result["overall_score"] < 0.5
        assert result["severity"] in ["None", "Low"]

    def test_neutral_news_content(self):
        """Test neutral news content"""
        analyzer = ToxicityAnalyzerV6()
        result = analyzer.analyze("Hôm nay trời nắng đẹp, nhiệt độ 25 độ C")

        assert result["is_toxic"] == False
        assert result["overall_score"] < 0.5

    def test_positive_feedback(self):
        """Test positive feedback"""
        analyzer = ToxicityAnalyzerV6()
        result = analyzer.analyze("Thông tin rất bổ ích, cảm ơn bạn nhiều!")

        assert result["is_toxic"] == False
        assert result["overall_score"] < 0.5


class TestToxicContent:
    """Test detection of toxic content"""

    def test_vietnamese_insult(self):
        """Test Vietnamese insult detection"""
        analyzer = ToxicityAnalyzerV6()
        result = analyzer.analyze("Đồ ngu ngốc, mày là thằng đần")

        assert result["is_toxic"] == True
        assert result["overall_score"] >= 0.5
        assert result["severity"] in ["Medium", "High", "Critical"]
        assert (
            "detoxify" in result["detection_layers"]
            or "regex" in result["detection_layers"]
        )

    def test_threat_detection(self):
        """Test threat detection"""
        analyzer = ToxicityAnalyzerV6()
        result = analyzer.analyze("Tao sẽ giết mày")

        assert result["is_toxic"] == True
        assert result["overall_score"] >= 0.7  # Should be high severity
        assert result["severity"] in ["High", "Critical"]

    def test_profanity_detection(self):
        """Test profanity detection"""
        analyzer = ToxicityAnalyzerV6()
        result = analyzer.analyze("Đồ chó chết, đụ má mày")

        assert result["is_toxic"] == True
        assert result["overall_score"] >= 0.5


class TestDetectionLayers:
    """Test individual detection layers"""

    def test_detoxify_layer(self):
        """Test Detoxify layer works"""
        analyzer = ToxicityAnalyzerV6()
        result = analyzer.analyze("You are stupid and ugly")

        assert "detoxify" in result["detection_layers"]
        assert result["details"]["detoxify"] is not None
        assert "categories" in result["details"]["detoxify"]

    def test_regex_layer(self):
        """Test regex layer works for Vietnamese"""
        analyzer = ToxicityAnalyzerV6()
        result = analyzer.analyze("Mày là thằng ngu")

        assert "regex" in result["detection_layers"]
        assert result["details"]["regex"] is not None

    def test_multi_layer_detection(self):
        """Test that both layers can detect toxicity"""
        analyzer = ToxicityAnalyzerV6()
        result = analyzer.analyze("Đồ ngu, stupid idiot")

        # Should detect in at least one layer
        assert len(result["detection_layers"]) >= 1
        assert result["is_toxic"] == True


class TestSeverityLevels:
    """Test severity level classification"""

    def test_low_severity(self):
        """Test low severity content"""
        analyzer = ToxicityAnalyzerV6()
        # Slightly negative but not toxic
        result = analyzer.analyze("Không hay lắm")

        assert result["severity"] in ["None", "Low"]

    def test_medium_severity(self):
        """Test medium severity"""
        analyzer = ToxicityAnalyzerV6()
        result = analyzer.analyze("Mày ngu quá")

        assert result["severity"] in ["Low", "Medium", "High"]

    def test_high_severity(self):
        """Test high severity"""
        analyzer = ToxicityAnalyzerV6()
        result = analyzer.analyze("Đồ chó chết, tao giết mày")

        assert result["severity"] in ["High", "Critical"]
        assert result["overall_score"] >= 0.7


class TestCategories:
    """Test toxicity category detection"""

    def test_categories_present(self):
        """Test that categories are returned"""
        analyzer = ToxicityAnalyzerV6()
        result = analyzer.analyze("You are an idiot")

        assert "categories" in result
        assert isinstance(result["categories"], dict)

    def test_detoxify_categories(self):
        """Test Detoxify categories"""
        analyzer = ToxicityAnalyzerV6()
        result = analyzer.analyze("Stupid ugly person")

        if "detoxify" in result["detection_layers"]:
            detoxify_cats = result["details"]["detoxify"]["categories"]
            assert "toxicity" in detoxify_cats
            assert "insult" in detoxify_cats
            assert "threat" in detoxify_cats


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_empty_text(self):
        """Test empty text handling"""
        analyzer = ToxicityAnalyzerV6()
        result = analyzer.analyze("")

        assert result["is_toxic"] == False
        assert result["overall_score"] == 0.0

    def test_whitespace_only(self):
        """Test whitespace-only text"""
        analyzer = ToxicityAnalyzerV6()
        result = analyzer.analyze("   \n\t  ")

        assert result["is_toxic"] == False
        assert result["overall_score"] == 0.0

    def test_very_long_text(self):
        """Test very long text"""
        analyzer = ToxicityAnalyzerV6()
        long_text = "Bài viết hay. " * 100
        result = analyzer.analyze(long_text)

        assert result is not None
        assert "is_toxic" in result

    def test_special_characters(self):
        """Test text with special characters"""
        analyzer = ToxicityAnalyzerV6()
        result = analyzer.analyze("Đồ @#$%^& ngu!")

        assert result is not None
        assert "is_toxic" in result


class TestBatchAnalysis:
    """Test batch analysis functionality"""

    def test_batch_analysis(self):
        """Test analyzing multiple texts"""
        analyzer = ToxicityAnalyzerV6()
        texts = ["Bài viết hay", "Đồ ngu", "Thông tin hữu ích"]

        results = analyzer.analyze_batch(texts)

        assert len(results) == 3
        assert all("is_toxic" in r for r in results)

    def test_batch_statistics(self):
        """Test statistics calculation"""
        analyzer = ToxicityAnalyzerV6()
        texts = ["Bài viết hay", "Đồ ngu ngốc", "Tao giết mày", "Thông tin tốt"]

        results = analyzer.analyze_batch(texts)
        stats = analyzer.get_statistics(results)

        assert stats["total_analyzed"] == 4
        assert "toxic_count" in stats
        assert "avg_score" in stats
        assert "severity_distribution" in stats


class TestFallbackMechanism:
    """Test fallback mechanisms"""

    def test_still_works_if_detoxify_fails(self):
        """Test that analyzer still works if Detoxify fails"""
        analyzer = ToxicityAnalyzerV6()

        # Temporarily disable Detoxify
        original_model = analyzer.detoxify_model
        analyzer.detoxify_model = None

        result = analyzer.analyze("Đồ ngu")

        # Should still work with regex
        assert result is not None
        assert "is_toxic" in result

        # Restore
        analyzer.detoxify_model = original_model

    def test_fallback_to_regex(self):
        """Test fallback to regex when Detoxify unavailable"""
        analyzer = ToxicityAnalyzerV6()
        analyzer.detoxify_model = None

        result = analyzer.analyze("Mày là thằng ngu")

        assert result is not None
        assert "regex" in result["detection_layers"]
        assert result["primary_method"] == "regex"


class TestResultStructure:
    """Test result structure consistency"""

    def test_result_has_required_fields(self):
        """Test that result has all required fields"""
        analyzer = ToxicityAnalyzerV6()
        result = analyzer.analyze("Test text")

        required_fields = [
            "is_toxic",
            "overall_score",
            "severity",
            "categories",
            "detection_layers",
            "primary_method",
            "details",
        ]

        for field in required_fields:
            assert field in result

    def test_score_range(self):
        """Test that scores are in valid range [0, 1]"""
        analyzer = ToxicityAnalyzerV6()
        texts = ["Clean text", "Đồ ngu", "Very toxic shit fuck"]

        for text in texts:
            result = analyzer.analyze(text)
            assert 0.0 <= result["overall_score"] <= 1.0


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
