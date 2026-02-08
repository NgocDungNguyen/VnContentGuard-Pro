import asyncio
import json
import platform
from typing import List, Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

if platform.system() == "Windows":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from src.models.fact_checker_v3 import FactCheckerV3
from src.models.gemini_llm import GeminiAgent
from src.models.risk_scorer_v3 import RiskScorerV3
from src.models.sentiment import SentimentAnalyzer

# v3 Enhanced Components
from src.models.sentiment_v3 import SentimentAnalyzerV3
from src.models.toxicity import ToxicityAnalyzer
from src.models.toxicity_v3 import ToxicityAnalyzerV3

app = FastAPI(title="VnContentGuard Pro API", version="3.0")

# Enable CORS for Chrome Extension
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Chrome extension can reach from any origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

print("⏳ Booting up AI Engine...")
try:
    toxicity_engine = ToxicityAnalyzer()
    gemini_agent = GeminiAgent()
    sentiment_engine = SentimentAnalyzer()

    # v3 Enhanced Engines (use fallback mode for faster startup)
    sentiment_v3_engine = SentimentAnalyzerV3(use_phobert=False)
    toxicity_v3_engine = ToxicityAnalyzerV3(use_detoxify=False)
    fact_checker_v3_engine = FactCheckerV3()
    risk_scorer_v3_engine = RiskScorerV3()

    print("✅ AI Server Ready!")
except Exception as e:
    print(f"❌ Error during initialization: {e}")
    raise


# ============================================================================
# Request/Response Models
# ============================================================================


class ScanRequest(BaseModel):
    """Request model for full content scan from Chrome Extension."""

    url: str  # Source URL (Facebook, news site, etc.)
    article_text: str  # Main article/post text
    comments: List[str] = []  # List of comments to analyze


class ToxicityResult(BaseModel):
    """Single toxicity result for a comment."""

    Comment: str
    Is_Toxic: bool
    Category: str
    Confidence: float


class FullScanResponse(BaseModel):
    """Complete analysis response."""

    fake_check: dict  # From Gemini
    sentiment: dict  # From Sentiment Analyzer
    toxicity: dict  # From Toxicity Analyzer


# ============================================================================
# Health Check Endpoint
# ============================================================================


@app.get("/health")
def health_check():
    """Check if the server is running."""
    return {"status": "🟢 VnContentGuard Pro Server is Running"}


# ============================================================================
# Main Analysis Endpoint
# ============================================================================


@app.post("/analyze/full_scan", response_model=dict)
def analyze_content(req: ScanRequest):
    """
    Full content scan endpoint.

    Accepts raw text scraped by Chrome Extension (NOT URLs).
    Returns comprehensive analysis with fake news, sentiment, and toxicity scores.

    Args:
        req: ScanRequest with url, article_text, and comments

    Returns:
        dict: Analysis results with fake_check, sentiment, and toxicity
    """
    print(f"📥 Received Scan Request for: {req.url}")
    try:
        # ========== 1. FAKE NEWS CHECK ==========
        fake_data = {
            "risk_score": 0,
            "verdict": "Skipped",
            "summary": "No text content found.",
        }

        if len(req.article_text) > 20:  # Lowered threshold
            try:
                fake_json = gemini_agent.check_fake_news(req.article_text)
                fake_data = json.loads(fake_json)
            except json.JSONDecodeError:
                fake_data = {
                    "risk_score": 0,
                    "verdict": "Parse Error",
                    "summary": "Could not parse AI response.",
                }
            except Exception as e:
                error_msg = str(e).lower()
                print(f"⚠️  Fake news check failed: {e}")
                # Handle quota errors gracefully
                if "429" in str(e) or "quota" in error_msg or "exceeded" in error_msg:
                    fake_data = {
                        "risk_score": 0,
                        "verdict": "Quota Limit",
                        "summary": "API quota exceeded. Please try again in a moment.",
                    }
                else:
                    fake_data = {
                        "risk_score": 0,
                        "verdict": "Service Busy",
                        "summary": "AI service is temporarily unavailable.",
                    }
        else:
            print(
                f"⚠️  Article too short ({len(req.article_text)} chars) for fake news check"
            )
            fake_data = {
                "risk_score": 0,
                "verdict": "Insufficient Content",
                "summary": "Post is too short to analyze.",
            }

        # ========== 2. SENTIMENT ANALYSIS ==========
        sentiment = {"label": "Neutral", "score": 0.0}

        if len(req.article_text) > 5:  # Lowered threshold
            try:
                sentiment = sentiment_engine.analyze(req.article_text[:512])
            except Exception as e:
                print(f"⚠️  Sentiment analysis failed: {e}")
                sentiment = {"label": "Neutral", "score": 0.0}
        else:
            print(f"⚠️  Article too short for sentiment ({len(req.article_text)} chars)")
            sentiment = {"label": "Neutral", "score": 0.0}

        # Toxicity check - accept empty comments list gracefully
        toxic_results = []
        toxic_count = 0

        if req.comments:
            actual_comment_count = len(req.comments)
            print(f"📋 Analyzing {actual_comment_count} comments for toxicity...")
            try:
                toxic_results, toxic_count = toxicity_engine.analyze_comments(
                    req.comments
                )
                print(
                    f"✅ Toxicity check complete: {toxic_count} toxic items found from {actual_comment_count} comments"
                )
            except Exception as e:
                print(f"⚠️  Toxicity analysis failed: {e}")
                toxic_count = 0
                toxic_results = []
        else:
            print(f"📋 No comments to analyze")
            toxic_results = []
            toxic_count = 0

        # ========== 4. COMPILE RESPONSE ==========
        response = {
            "fake_check": fake_data,
            "sentiment": sentiment,
            "toxicity": {
                "total": len(req.comments),
                "toxic_count": toxic_count,
                "results": toxic_results,
            },
        }

        print(
            f"✅ Analysis complete. Risk Score: {fake_data.get('risk_score', 0)}, Toxics: {toxic_count}"
        )
        return response

    except Exception as e:
        print(f"❌ Critical Error: {e}")
        raise HTTPException(
            status_code=500, detail=f"Server error during analysis: {str(e)}"
        )


# ============================================================================
# v3 Enhanced Analysis Endpoint
# ============================================================================


@app.post("/analyze/v3", response_model=dict)
def analyze_content_v3(req: ScanRequest):
    """
    v3 Enhanced full content scan endpoint with multi-layer AI detection.

    Uses PhoBERT sentiment, 4-layer toxicity, multi-source fact-checking,
    and objective risk scoring.

    Args:
        req: ScanRequest with url, article_text, and comments

    Returns:
        dict: Enhanced analysis with sentiment_v3, toxicity_v3, fact_check_v3, risk_score_v3
    """
    print(f"📥 [v3] Received Scan Request for: {req.url}")
    try:
        # ========== 1. SENTIMENT ANALYSIS v3 (PhoBERT) ==========
        sentiment_v3 = {
            "label": "Neutral",
            "confidence": 0.0,
            "intensity": "Weak",
            "method": "none",
        }

        if len(req.article_text) > 5:
            try:
                sentiment_v3 = sentiment_v3_engine.analyze(req.article_text[:512])
                print(
                    f"✅ [v3] Sentiment: {sentiment_v3['overall']} (confidence: {sentiment_v3['confidence']:.2f})"
                )
            except Exception as e:
                print(f"⚠️  [v3] Sentiment analysis failed: {e}")
                sentiment_v3 = {
                    "label": "Neutral",
                    "confidence": 0.0,
                    "intensity": "Weak",
                    "method": "error",
                }
        else:
            print(
                f"⚠️  [v3] Article too short for sentiment ({len(req.article_text)} chars)"
            )

        # ========== 2. TOXICITY DETECTION v3 (4-layer) ==========
        toxicity_v3 = {
            "is_toxic": False,
            "overall_score": 0.0,
            "severity": "Low",
            "categories": {},
            "detection_layers": [],
        }

        if len(req.article_text) > 5:
            try:
                toxicity_v3 = toxicity_v3_engine.analyze(req.article_text[:1000])
                print(
                    f"✅ [v3] Toxicity: {toxicity_v3['severity']} (score: {toxicity_v3['overall_score']:.2f})"
                )
            except Exception as e:
                print(f"⚠️  [v3] Toxicity detection failed: {e}")

        # ========== 3. FACT-CHECKING v3 (Multi-source) ==========
        fact_check_v3 = {
            "score": 50,
            "verdict": "Unverifiable",
            "confidence": "Low",
            "evidence": [],
            "verification_methods": [],
        }

        if len(req.article_text) > 20:
            try:
                fact_check_v3 = fact_checker_v3_engine.check(req.article_text, req.url)
                print(
                    f"✅ [v3] Fact Check: {fact_check_v3['verdict']} (credibility: {fact_check_v3['score']})"
                )
            except Exception as e:
                print(f"⚠️  [v3] Fact-checking failed: {e}")
                error_msg = str(e).lower()
                if "429" in str(e) or "quota" in error_msg:
                    fact_check_v3["verdict"] = "Quota Exceeded"
                else:
                    fact_check_v3["verdict"] = "Service Unavailable"

        # ========== 4. RISK SCORING v3 (Comprehensive) ==========
        risk_score_v3 = {
            "risk_score": 0.0,
            "risk_level": "Low",
            "confidence": 0.0,
            "risk_breakdown": {},
            "warnings": [],
            "recommendations": [],
        }

        if len(req.article_text) > 20:
            try:
                risk_score_v3 = risk_scorer_v3_engine.score(req.article_text, req.url)
                print(
                    f"✅ [v3] Risk Score: {risk_score_v3['risk_score']:.1f}/100 ({risk_score_v3['risk_level']})"
                )
            except Exception as e:
                print(f"⚠️  [v3] Risk scoring failed: {e}")

        # ========== 5. COMMENTS TOXICITY (v3) ==========
        toxic_comments_v3 = []
        toxic_count_v3 = 0

        if req.comments:
            print(f"📋 [v3] Analyzing {len(req.comments)} comments for toxicity...")
            for comment in req.comments[:50]:  # Limit to 50 comments
                try:
                    result = toxicity_v3_engine.analyze(comment)
                    if result["is_toxic"]:
                        toxic_count_v3 += 1
                        toxic_comments_v3.append(
                            {
                                "comment": comment[:200],
                                "severity": result["severity"],
                                "score": result["overall_score"],
                                "categories": result["categories"],
                            }
                        )
                except Exception as e:
                    print(f"⚠️  [v3] Comment toxicity check failed: {e}")
            print(f"✅ [v3] Comments: {toxic_count_v3}/{len(req.comments)} toxic")

        # ========== 6. COMPILE v3 RESPONSE ==========
        response = {
            "version": "3.0",
            "sentiment_v3": sentiment_v3,
            "toxicity_v3": toxicity_v3,
            "fact_check_v3": fact_check_v3,
            "risk_score_v3": risk_score_v3,
            "comments_analysis": {
                "total": len(req.comments),
                "toxic_count": toxic_count_v3,
                "toxic_comments": toxic_comments_v3[
                    :10
                ],  # Return top 10 toxic comments
            },
            "url": req.url,
        }

        print(
            f"✅ [v3] Analysis complete. Risk: {risk_score_v3['risk_score']:.1f}/100, Toxics: {toxic_count_v3}"
        )
        return response

    except Exception as e:
        print(f"❌ [v3] Critical Error: {e}")
        raise HTTPException(status_code=500, detail=f"v3 analysis error: {str(e)}")


# ============================================================================
# Error Handlers
# ============================================================================


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for all unhandled errors."""
    return {"error": "Internal Server Error", "detail": str(exc), "status": 500}


# ============================================================================
# Main
# ============================================================================


def kill_port(port: int):
    """Kill any process occupying the given port (except ourselves)."""
    import os
    import subprocess

    my_pid = str(os.getpid())
    try:
        result = subprocess.run(["netstat", "-ano"], capture_output=True, text=True)
        for line in result.stdout.strip().split("\n"):
            if f":{port}" in line and "LISTENING" in line:
                pid = line.strip().split()[-1]
                if pid != my_pid:
                    subprocess.run(["taskkill", "/F", "/PID", pid], capture_output=True)
                    print(f"🔄 Killed old process on port {port} (PID: {pid})")
    except Exception:
        pass


if __name__ == "__main__":
    kill_port(8000)
    print("🚀 Starting VnContentGuard Pro Server on http://127.0.0.1:8000")
    print("📊 API Docs available at http://127.0.0.1:8000/docs")
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
