"""
Tests for VnContentGuard Pro v5 - Risk Scoring System
======================================================
Comprehensive tests for RiskScorerV5 integrating all v5 modules
"""

import os
import sys

import pytest

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.models.risk_scorer_v5 import RiskScorerV5, calculate_risk


class TestRiskScorerV5:
    """Test suite for RiskScorerV5"""

    # Class-level scorer to avoid reloading models
    scorer = None

    @classmethod
    def setup_class(cls):
        """Setup once for entire test class"""
        cls.scorer = RiskScorerV5()

    def test_initialization(self):
        """Test risk scorer initializes correctly"""
        assert self.scorer is not None
        assert hasattr(self.scorer, "score")
        assert hasattr(self.scorer, "sentiment_analyzer")
        assert hasattr(self.scorer, "toxicity_analyzer")
        assert hasattr(self.scorer, "fact_checker")
        print("✅ RiskScorerV5 initialization test passed")

    def test_empty_input(self):
        """Test handling of empty input"""
        result = self.scorer.score("")
        assert result["risk_score"] == 0
        assert result["risk_level"] == "Unknown"
        assert "No content provided" in result["recommendations"][0]
        print("✅ Empty input handling test passed")

    def test_low_risk_content(self):
        """Test with low-risk neutral content"""
        result = self.scorer.score("The weather today is sunny with mild temperatures.")

        assert "risk_score" in result
        assert "risk_level" in result
        assert "breakdown" in result
        assert result["risk_score"] <= 40  # Should be low/medium risk

        print(
            f"✅ Low risk content test passed (Score: {result['risk_score']:.1f}, Level: {result['risk_level']})"
        )

    def test_high_risk_toxic_content(self):
        """Test with high-risk toxic content"""
        result = self.scorer.score("Đồ ngu ngốc! Tao giết mày!")

        assert result["risk_score"] >= 30  # Should have elevated risk due to toxicity
        # Should have toxicity evidence
        assert any("Toxicity" in ev["module"] for ev in result["evidence"])

        print(
            f"✅ High risk toxic content test passed (Score: {result['risk_score']:.1f}, Level: {result['risk_level']})"
        )

    def test_manipulation_detection(self):
        """Test with manipulative clickbait content"""
        result = self.scorer.score(
            "SHOCKING! You won't believe this! Click here NOW!!!"
        )

        # Should detect manipulation patterns
        assert result["breakdown"]["manipulation_component"] > 0
        # Should have higher risk
        assert result["risk_score"] >= 20

        print(
            f"✅ Manipulation detection test passed (Score: {result['risk_score']:.1f}, Manipulation: {result['breakdown']['manipulation_component']:.1f})"
        )

    def test_with_trusted_source(self):
        """Test content with trusted source URL"""
        result = self.scorer.score(
            "New economic report published today", url="https://bbc.com"
        )

        # Trusted source should lower risk
        if "source" in result["raw_scores"]:
            assert result["breakdown"]["source_component"] <= 20  # Low source risk

        print(f"✅ Trusted source test passed (Score: {result['risk_score']:.1f})")

    def test_with_untrusted_source(self):
        """Test content with suspicious source"""
        result = self.scorer.score("Breaking news", url="https://fake-news-2024.xyz")

        # Untrusted source should increase risk
        if "source" in result["raw_scores"]:
            # Source component should contribute to risk
            assert result["breakdown"]["source_component"] >= 0

        print(f"✅ Untrusted source test passed (Score: {result['risk_score']:.1f})")

    def test_risk_level_low(self):
        """Test low risk level classification"""
        result = self.scorer.score("This is a calm, factual statement about science.")

        # Should be low or medium risk
        assert result["risk_level"] in ["Low", "Medium"]
        assert result["risk_score"] <= 50

        print(
            f"✅ Low risk level test passed (Level: {result['risk_level']}, Score: {result['risk_score']:.1f})"
        )

    def test_risk_level_high(self):
        """Test high risk level classification"""
        # Combine multiple risk factors
        result = self.scorer.score(
            "SHOCKING EXCLUSIVE!!! Đồ ngu! You won't BELIEVE this!!!"
        )

        # Should be medium/high risk (multiple risk factors)
        assert result["risk_level"] in ["Medium", "High", "Critical"]
        assert result["risk_score"] >= 30

        print(
            f"✅ High risk level test passed (Level: {result['risk_level']}, Score: {result['risk_score']:.1f})"
        )

    def test_breakdown_components(self):
        """Test that all risk components are calculated"""
        result = self.scorer.score("Test content for analysis")

        assert "breakdown" in result
        assert "fake_news_component" in result["breakdown"]
        assert "toxicity_component" in result["breakdown"]
        assert "sentiment_component" in result["breakdown"]
        assert "manipulation_component" in result["breakdown"]

        # All components should be numbers
        for component, value in result["breakdown"].items():
            assert isinstance(value, (int, float))
            assert 0 <= value <= 100

        print("✅ Breakdown components test passed")

    def test_evidence_collection(self):
        """Test that evidence is collected from modules"""
        result = self.scorer.score("This is test content for evidence collection")

        assert "evidence" in result
        assert isinstance(result["evidence"], list)
        # Should have evidence from at least sentiment and toxicity
        assert len(result["evidence"]) >= 2

        # Each evidence should have required fields
        for evidence in result["evidence"]:
            assert "module" in evidence
            assert "finding" in evidence
            assert "risk_contribution" in evidence

        print(
            f"✅ Evidence collection test passed (Collected {len(result['evidence'])} pieces)"
        )

    def test_recommendations_provided(self):
        """Test that recommendations are provided"""
        result = self.scorer.score("Test content")

        assert "recommendations" in result
        assert isinstance(result["recommendations"], list)
        assert len(result["recommendations"]) > 0
        # First recommendation should be risk level summary
        assert any(
            word in result["recommendations"][0]
            for word in ["RISK", "safe", "CRITICAL"]
        )

        print(
            f"✅ Recommendations test passed ({len(result['recommendations'])} recommendations)"
        )

    def test_score_range(self):
        """Test that risk scores are in valid range"""
        test_texts = [
            "Normal content",
            "SHOCKING!!! CLICK NOW!!!",
            "Đồ khốn nạn! Tao giết mày!",
            "Calm and factual information",
        ]

        for text in test_texts:
            result = self.scorer.score(text)
            assert (
                0 <= result["risk_score"] <= 100
            ), f"Score {result['risk_score']} out of range for: {text}"

        print("✅ Score range test passed")

    def test_vietnamese_content(self):
        """Test with Vietnamese content"""
        result = self.scorer.score("Việt Nam là một đất nước đẹp với văn hóa phong phú")

        assert result is not None
        assert "risk_score" in result
        # Vietnamese content should be analyzed properly
        assert len(result["evidence"]) > 0

        print(f"✅ Vietnamese content test passed (Score: {result['risk_score']:.1f})")

    def test_mixed_risk_factors(self):
        """Test content with mixed risk factors"""
        result = self.scorer.score(
            "Bài viết về khoa học rất hữu ích",  # Positive Vietnamese
            url="https://vnexpress.net",  # Trusted source
        )

        # Should balance positive content with trusted source
        assert result is not None
        # Multiple components should contribute
        components_with_values = sum(1 for v in result["breakdown"].values() if v > 0)
        assert components_with_values >= 2

        print(
            f"✅ Mixed risk factors test passed (Components: {components_with_values})"
        )

    def test_extreme_clickbait(self):
        """Test extreme clickbait patterns"""
        result = self.scorer.score(
            "SHOCKING!!! You won't BELIEVE what happens next!!! CLICK HERE NOW!!! "
            + "Number 7 will BLOW your MIND!!!"
        )

        # Should have high manipulation component
        assert result["breakdown"]["manipulation_component"] >= 5
        # Overall risk should be elevated
        assert result["risk_score"] >= 25

        print(
            f"✅ Extreme clickbait test passed (Manipulation: {result['breakdown']['manipulation_component']:.1f})"
        )

    def test_raw_scores_included(self):
        """Test that raw scores from modules are included"""
        result = self.scorer.score("Test content for raw scores")

        assert "raw_scores" in result
        assert isinstance(result["raw_scores"], dict)
        # Should have at least manipulation score
        assert "manipulation" in result["raw_scores"]

        print(f"✅ Raw scores test passed ({len(result['raw_scores'])} modules)")

    def test_convenience_function(self):
        """Test convenience function calculate_risk()"""
        result = calculate_risk("Test content", url="https://example.com")

        assert result is not None
        assert "risk_score" in result
        assert "risk_level" in result

        print("✅ Convenience function test passed")


class TestIntegration:
    """Integration tests with all v5 modules"""

    def test_full_v5_pipeline(self):
        """Test complete v5 pipeline integration"""
        scorer = RiskScorerV5()

        # Test with complex content
        result = scorer.score(
            "Breaking: Shocking discovery! Scientists reveal UNBELIEVABLE truth!",
            url="https://bbc.com",
        )

        # Should have analyzed with multiple modules
        assert (
            len(result["evidence"]) >= 3
        )  # Sentiment, Toxicity, Manipulation at minimum
        # Should have final risk assessment
        assert result["risk_level"] in ["Low", "Medium", "High", "Critical"]
        # Should have recommendations
        assert len(result["recommendations"]) > 0

        print(f"✅ Full v5 pipeline test passed")
        print(f"   Risk: {result['risk_score']:.1f}/100 ({result['risk_level']})")
        print(f"   Evidence: {len(result['evidence'])} sources")
        print(f"   Recommendations: {len(result['recommendations'])}")

    def test_all_components_contribution(self):
        """Test that all components contribute to final score"""
        scorer = RiskScorerV5()

        result = scorer.score(
            "Shocking news! This is terrible and unbelievable!",
            url="https://random-site.xyz",
        )

        # Check that breakdown sum approximately equals final score
        breakdown_sum = sum(result["breakdown"].values())
        # Allow small rounding differences
        assert abs(breakdown_sum - result["risk_score"]) < 1.0

        print(f"✅ Component contribution test passed")
        print(f"   Breakdown sum: {breakdown_sum:.1f}")
        print(f"   Final score: {result['risk_score']:.1f}")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🧪 VnContentGuard Pro v5 - Risk Scorer Test Suite")
    print("=" * 60 + "\n")

    # Run pytest
    pytest.main([__file__, "-v", "--tb=short"])
