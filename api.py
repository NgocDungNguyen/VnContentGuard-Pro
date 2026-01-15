import asyncio
import json
import platform
from typing import List, Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

if platform.system() == "Windows":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from src.models.gemini_llm import GeminiAgent
from src.models.sentiment import SentimentAnalyzer
from src.models.toxicity import ToxicityAnalyzer

app = FastAPI(title="VnContentGuard Pro API", version="2.1")

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
# Error Handlers
# ============================================================================


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for all unhandled errors."""
    return {"error": "Internal Server Error", "detail": str(exc), "status": 500}


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    print("🚀 Starting VnContentGuard Pro Server on http://127.0.0.1:8000")
    print("📊 API Docs available at http://127.0.0.1:8000/docs")
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
