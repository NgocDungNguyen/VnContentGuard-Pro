import asyncio
import json
import platform
import sys
import time
from typing import List, Optional

# Fix CP1258 encoding issues on Windows (emoji in print statements)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

if platform.system() == "Windows":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from src.models.article_summarizer_v4 import ArticleSummarizer
from src.models.fact_checker_v4 import FactCheckerV4
from src.models.gemini_llm import API_KEY_POOL, MODEL_NAME, APIKeyRotator, GeminiAgent
from src.models.risk_scorer_v4 import RiskScorerV4
from src.models.sentiment import SentimentAnalyzer

# v4 Enhanced Components
from src.models.sentiment_v4 import SentimentAnalyzerV4
from src.models.toxicity import ToxicityAnalyzer
from src.models.toxicity_v4 import ToxicityAnalyzerV4
from src.utils.blocklist import CommunityBlocklist
from src.utils.cache_manager import CacheManager
from src.utils.comment_filter import CommentFilter
from src.utils.feedback_store import FeedbackStore

app = FastAPI(title="VnContentGuard Pro API", version="4.9")

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
    # SINGLE shared key rotator for ALL Gemini calls (prevents burning keys)
    shared_key_rotator = APIKeyRotator(API_KEY_POOL)

    # v2 Engines
    toxicity_engine = ToxicityAnalyzer()
    gemini_agent = GeminiAgent(key_rotator=shared_key_rotator)
    sentiment_engine = SentimentAnalyzer()

    # v4 Enhanced Engines (use fallback mode for faster startup)
    sentiment_v4_engine = SentimentAnalyzerV4(use_phobert=False)
    toxicity_v4_engine = ToxicityAnalyzerV4(use_detoxify=False)
    fact_checker_v4_engine = FactCheckerV4(key_rotator=shared_key_rotator)
    risk_scorer_v4_engine = RiskScorerV4(
        sentiment_analyzer=sentiment_v4_engine,
        toxicity_analyzer=toxicity_v4_engine,
        fact_checker=fact_checker_v4_engine,
    )

    # v4 New Components
    cache_manager = CacheManager(ttl_seconds=86400)  # 24-hour cache
    comment_filter = CommentFilter()
    article_summarizer = ArticleSummarizer(
        cache_manager, key_rotator=shared_key_rotator
    )

    # v5.0 Feedback Store
    feedback_store = FeedbackStore()

    # v4.9 Community Blocklist
    community_blocklist = CommunityBlocklist()

    # Reuse same shared key rotator for batch comment analysis
    batch_key_rotator = shared_key_rotator

    print("✅ AI Server Ready! (v4 with Summary + Batch Analysis)")
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


@app.get("/api/stats")
def api_stats():
    """v4.9 — API usage statistics and model status."""
    try:
        gemini_status = gemini_agent.get_status()
        feedback_stats = feedback_store.get_stats()
        blocklist_stats = community_blocklist.get_stats()
        return {
            "version": "4.9.0",
            "model": gemini_status.get("model", "unknown"),
            "using_fallback": gemini_status.get("using_fallback", False),
            "api_keys": {
                "total": gemini_status.get("total_keys", 0),
                "available": gemini_status.get("available_count", 0),
                "exhausted": gemini_status.get("exhausted_count", 0),
                "current": gemini_status.get("current_key", 0),
            },
            "feedback": feedback_stats,
            "blocklist": blocklist_stats,
            "status": "🟢 Online",
        }
    except Exception as e:
        return {"version": "4.9.0", "status": "🔴 Error", "error": str(e)}


# ============================================================================
# User Feedback Endpoint (v5.0)
# ============================================================================


class FeedbackRequest(BaseModel):
    """Request model for user feedback."""

    url: str
    rating: str  # "positive" or "negative"
    correction: str = ""
    modules: dict = {}
    scan_results: dict = {}


@app.post("/api/feedback")
def submit_feedback(req: FeedbackRequest):
    """v4.9 — Accept user feedback on scan results. Feeds into learning system."""
    try:
        result = feedback_store.add_feedback(
            url=req.url,
            rating=req.rating,
            correction=req.correction,
            modules=req.modules,
            scan_results=req.scan_results,
        )
        feedback_store.invalidate_cache()  # Reset learning cache
        print(f"📝 Feedback received: {req.rating} for {req.url}")
        return result
    except Exception as e:
        print(f"⚠️ Feedback error: {e}")
        return {"status": "error", "message": str(e)}


# ============================================================================
# Community Blocklist Endpoints (v4.9)
# ============================================================================


class ReportRequest(BaseModel):
    """Request model for community report."""

    url: str
    risk_score: float = 0.0
    reason: str = ""


@app.post("/api/report")
def report_page(req: ReportRequest):
    """v4.9 — Report a page/domain to the community blocklist."""
    try:
        result = community_blocklist.add_report(
            url=req.url,
            risk_score=req.risk_score,
            reason=req.reason,
        )
        print(f"🚩 Report: {req.url} (risk: {req.risk_score})")
        return result
    except Exception as e:
        print(f"⚠️ Report error: {e}")
        return {"status": "error", "message": str(e)}


@app.get("/api/blocklist")
def get_blocklist():
    """v4.9 — Get community blocklist (domains with 5+ reports)."""
    try:
        domains = community_blocklist.get_blocklist()
        return {"blocklist": domains, "count": len(domains)}
    except Exception as e:
        return {"blocklist": [], "count": 0, "error": str(e)}


@app.get("/api/blocklist/check")
def check_blocklist(url: str):
    """v4.9 — Check if a URL is blocked."""
    try:
        is_blocked = community_blocklist.is_blocked(url)
        report_count = community_blocklist.get_domain_report_count(url)
        return {
            "url": url,
            "is_blocked": is_blocked,
            "report_count": report_count,
        }
    except Exception as e:
        return {"url": url, "is_blocked": False, "error": str(e)}


@app.get("/api/feedback/domain")
def get_domain_feedback(url: str):
    """v4.9 — Get feedback learning data for a domain."""
    try:
        return feedback_store.get_domain_feedback(url)
    except Exception as e:
        return {"domain": url, "total": 0, "error": str(e)}


# ============================================================================
# v4.9 Streaming Analysis Endpoint (SSE)
# ============================================================================


@app.post("/analyze/v4/stream")
def analyze_content_v4_stream(req: ScanRequest):
    """
    v4.9 — Streaming analysis endpoint using Server-Sent Events.
    Yields each module result as it completes so the frontend can render progressively.
    """

    def event_stream():
        try:
            # Get learning context from feedback history
            learning_ctx = feedback_store.get_learning_context(req.url)

            # Module 1: Article Summary
            yield _sse_event(
                "progress", {"module": "summary", "status": "running", "step": "1/6"}
            )
            article_summary = {"summary": "", "method": "none", "cached": False}
            summary_text = ""
            if len(req.article_text) > 30:
                try:
                    article_summary = article_summarizer.summarize(
                        req.article_text, req.url
                    )
                    summary_text = article_summary.get("summary", "")
                except Exception as e:
                    print(f"⚠️ [SSE] Summary failed: {e}")
            yield _sse_event(
                "module", {"module": "article_summary", "data": article_summary}
            )

            # Module 2: Sentiment
            yield _sse_event(
                "progress", {"module": "sentiment", "status": "running", "step": "2/6"}
            )
            sentiment_v4 = {
                "label": "Neutral",
                "confidence": 0.0,
                "intensity": "Weak",
                "method": "none",
            }
            if len(req.article_text) > 5:
                try:
                    sentiment_v4 = sentiment_v4_engine.analyze(req.article_text[:512])
                except Exception as e:
                    print(f"⚠️ [SSE] Sentiment failed: {e}")
            yield _sse_event("module", {"module": "sentiment_v4", "data": sentiment_v4})

            # Module 3: Toxicity
            yield _sse_event(
                "progress", {"module": "toxicity", "status": "running", "step": "3/6"}
            )
            toxicity_v4 = {
                "is_toxic": False,
                "overall_score": 0.0,
                "severity": "Low",
                "categories": {},
                "detection_layers": [],
            }
            if len(req.article_text) > 5:
                try:
                    toxicity_v4 = toxicity_v4_engine.analyze(req.article_text[:1000])
                except Exception as e:
                    print(f"⚠️ [SSE] Toxicity failed: {e}")
            yield _sse_event("module", {"module": "toxicity_v4", "data": toxicity_v4})

            # Module 4: Fact Check
            yield _sse_event(
                "progress", {"module": "fact_check", "status": "running", "step": "4/6"}
            )
            fact_check_v4 = {
                "score": 50,
                "verdict": "Unverifiable",
                "confidence": "Low",
                "evidence": [],
                "verification_methods": [],
            }
            if len(req.article_text) > 20:
                try:
                    fact_check_v4 = fact_checker_v4_engine.check(
                        req.article_text, req.url
                    )
                except Exception as e:
                    print(f"⚠️ [SSE] Fact check failed: {e}")
            yield _sse_event(
                "module", {"module": "fact_check_v4", "data": fact_check_v4}
            )

            # Module 5: Risk Score — use pre-computed modules to avoid contradictions
            yield _sse_event(
                "progress", {"module": "risk_score", "status": "running", "step": "5/6"}
            )
            risk_score_v4 = {
                "risk_score": 0.0,
                "risk_level": "Low",
                "confidence": 0.0,
                "risk_breakdown": {},
                "warnings": [],
                "recommendations": [],
            }
            if len(req.article_text) > 20:
                try:
                    risk_score_v4 = risk_scorer_v4_engine.score_from_results(
                        req.article_text,
                        req.url,
                        sentiment_result=sentiment_v4,
                        toxicity_result=toxicity_v4,
                        fact_check_result=fact_check_v4,
                    )
                except Exception as e:
                    print(f"⚠️ [SSE] Risk score failed: {e}")
            yield _sse_event(
                "module", {"module": "risk_score_v4", "data": risk_score_v4}
            )

            # Module 6: Comments
            yield _sse_event(
                "progress", {"module": "comments", "status": "running", "step": "6/6"}
            )
            comments_analysis = {
                "total": 0,
                "toxic_count": 0,
                "toxic_percentage": 0.0,
                "toxic_comments": [],
                "filter_stats": {},
                "api_calls_saved": 0,
            }
            if req.comments:
                comments_analysis = _analyze_comments_v4(
                    req.comments[:50], summary_text, req.url, learning_ctx
                )
            yield _sse_event(
                "module", {"module": "comments_analysis", "data": comments_analysis}
            )

            # Check blocklist
            blocklist_info = {
                "is_blocked": community_blocklist.is_blocked(req.url),
                "report_count": community_blocklist.get_domain_report_count(req.url),
            }

            # Domain feedback
            domain_feedback = feedback_store.get_domain_feedback(req.url)

            # Final complete event
            final = {
                "version": "4.9",
                "article_summary": article_summary,
                "sentiment_v4": sentiment_v4,
                "toxicity_v4": toxicity_v4,
                "fact_check_v4": fact_check_v4,
                "risk_score_v4": risk_score_v4,
                "comments_analysis": comments_analysis,
                "url": req.url,
                "cache_stats": cache_manager.get_stats(),
                "blocklist_info": blocklist_info,
                "domain_feedback": domain_feedback,
                "learning_applied": bool(learning_ctx),
            }
            yield _sse_event("complete", final)

        except Exception as e:
            yield _sse_event("error", {"message": str(e)})

    return StreamingResponse(event_stream(), media_type="text/event-stream")


def _sse_event(event_type: str, data: dict) -> str:
    """Format a Server-Sent Event."""
    return f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


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
# v4 Enhanced Analysis Endpoint
# ============================================================================


@app.post("/analyze/v4", response_model=dict)
def analyze_content_v4(req: ScanRequest):
    """
    v4 Enhanced full content scan endpoint.

    New features:
    - Article summary (AI-generated, cached per URL)
    - Context-aware batch comment analysis (1 API call for N comments)
    - Smart comment filtering (skip obvious toxic/clean/spam)
    - API usage optimization (70-80% fewer Gemini calls)
    """
    print(f"📥 [v4] Received Scan Request for: {req.url}")
    try:
        # ========== LEARNING CONTEXT (v4.9) ==========
        learning_ctx = feedback_store.get_learning_context(req.url)
        if learning_ctx:
            print(f"🧠 [v4.9] Learning context loaded for {req.url}")

        # ========== 0. ARTICLE SUMMARY (NEW) ==========
        article_summary = {"summary": "", "method": "none", "cached": False}
        summary_text = ""

        if len(req.article_text) > 30:
            try:
                article_summary = article_summarizer.summarize(
                    req.article_text, req.url
                )
                summary_text = article_summary.get("summary", "")
                print(
                    f"✅ [v4] Summary: {article_summary['method']} ({len(summary_text)} chars)"
                )
            except Exception as e:
                print(f"⚠️  [v4] Summary failed: {e}")

        # ========== 1. SENTIMENT ANALYSIS v4 (PhoBERT) ==========
        sentiment_v4 = {
            "label": "Neutral",
            "confidence": 0.0,
            "intensity": "Weak",
            "method": "none",
        }

        if len(req.article_text) > 5:
            try:
                sentiment_v4 = sentiment_v4_engine.analyze(req.article_text[:512])
                print(
                    f"✅ [v4] Sentiment: {sentiment_v4['overall']} (confidence: {sentiment_v4['confidence']:.2f})"
                )
            except Exception as e:
                print(f"⚠️  [v4] Sentiment analysis failed: {e}")
                sentiment_v4 = {
                    "label": "Neutral",
                    "confidence": 0.0,
                    "intensity": "Weak",
                    "method": "error",
                }
        else:
            print(
                f"⚠️  [v4] Article too short for sentiment ({len(req.article_text)} chars)"
            )

        # ========== 2. Toxicity Detection v4 (4-layer, article body) ==========
        toxicity_v4 = {
            "is_toxic": False,
            "overall_score": 0.0,
            "severity": "Low",
            "categories": {},
            "detection_layers": [],
        }

        if len(req.article_text) > 5:
            try:
                toxicity_v4 = toxicity_v4_engine.analyze(req.article_text[:1000])
                print(
                    f"✅ [v4] Toxicity: {toxicity_v4['severity']} (score: {toxicity_v4['overall_score']:.2f})"
                )
            except Exception as e:
                print(f"⚠️  [v4] Toxicity detection failed: {e}")

        # ========== 3. FACT-CHECKING v4 (Multi-source) ==========
        fact_check_v4 = {
            "score": 50,
            "verdict": "Unverifiable",
            "confidence": "Low",
            "evidence": [],
            "verification_methods": [],
        }

        if len(req.article_text) > 20:
            try:
                fact_check_v4 = fact_checker_v4_engine.check(req.article_text, req.url)
                print(
                    f"✅ [v4] Fact Check: {fact_check_v4['verdict']} (credibility: {fact_check_v4['score']})"
                )
            except Exception as e:
                print(f"⚠️  [v4] Fact-checking failed: {e}")
                error_msg = str(e).lower()
                if "429" in str(e) or "quota" in error_msg:
                    fact_check_v4["verdict"] = "Quota Exceeded"
                else:
                    fact_check_v4["verdict"] = "Service Unavailable"

        # ========== 4. RISK SCORING v4 (Comprehensive) ==========
        risk_score_v4 = {
            "risk_score": 0.0,
            "risk_level": "Low",
            "confidence": 0.0,
            "risk_breakdown": {},
            "warnings": [],
            "recommendations": [],
        }

        if len(req.article_text) > 20:
            try:
                risk_score_v4 = risk_scorer_v4_engine.score(req.article_text, req.url)
                print(
                    f"✅ [v4] Risk Score: {risk_score_v4['risk_score']:.1f}/100 ({risk_score_v4['risk_level']})"
                )
            except Exception as e:
                print(f"⚠️  [v4] Risk scoring failed: {e}")

        # ========== 5. COMMENTS ANALYSIS (v4 - Context-Aware Batch) ==========
        comments_analysis = {
            "total": 0,
            "toxic_count": 0,
            "toxic_percentage": 0.0,
            "toxic_comments": [],
            "filter_stats": {},
            "api_calls_saved": 0,
        }

        if req.comments:
            comments_analysis = _analyze_comments_v4(
                req.comments[:50], summary_text, req.url, learning_ctx
            )

        # ========== 6. BLOCKLIST CHECK (v4.9) ==========
        blocklist_info = {
            "is_blocked": community_blocklist.is_blocked(req.url),
            "report_count": community_blocklist.get_domain_report_count(req.url),
        }

        # ========== 7. DOMAIN FEEDBACK (v4.9) ==========
        domain_feedback = feedback_store.get_domain_feedback(req.url)

        # ========== 8. COMPILE v4.9 RESPONSE ==========
        response = {
            "version": "4.9",
            "article_summary": article_summary,
            "sentiment_v4": sentiment_v4,
            "toxicity_v4": toxicity_v4,
            "fact_check_v4": fact_check_v4,
            "risk_score_v4": risk_score_v4,
            "comments_analysis": comments_analysis,
            "url": req.url,
            "cache_stats": cache_manager.get_stats(),
            "blocklist_info": blocklist_info,
            "domain_feedback": domain_feedback,
            "learning_applied": bool(learning_ctx),
        }

        print(
            f"✅ [v4] Analysis complete. Risk: {risk_score_v4['risk_score']:.1f}/100, "
            f"Toxics: {comments_analysis['toxic_count']}, "
            f"API saved: {comments_analysis.get('api_calls_saved', 0)}"
        )
        return response

    except Exception as e:
        print(f"❌ [v4] Critical Error: {e}")
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"v4 analysis error: {str(e)}")


def _analyze_comments_v4(
    comments: List[str], article_summary: str, url: str, learning_ctx: str = ""
) -> dict:
    """
    Context-aware batch comment analysis.

    Steps:
    1. Pre-filter comments into categories (saves ~70% of API calls)
    2. Run regex toxicity on each comment for precise pattern matching
    3. Batch-analyze only ambiguous comments with Gemini + article context
    4. Cache results
    """
    from google import genai
    from google.genai import types

    total = len(comments)
    filtered = comment_filter.filter_comments(comments)

    api_calls_saved = (
        len(filtered["obvious_toxic"])
        + len(filtered["obvious_clean"])
        + len(filtered["spam"])
    )

    print(f"📊 [v4] Comment filtering:")
    print(f"   Total: {total}")
    print(f"   Obvious toxic: {len(filtered['obvious_toxic'])}")
    print(f"   Obvious clean: {len(filtered['obvious_clean'])}")
    print(f"   Spam: {len(filtered['spam'])}")
    print(f"   Ambiguous (need AI): {len(filtered['ambiguous'])}")
    print(f"   API calls saved: {api_calls_saved}/{total}")

    all_results = []

    # --- Handle obvious toxic (regex-detected, no API needed) ---
    for comment in filtered["obvious_toxic"]:
        # Use regex only — do NOT call .analyze() which triggers Perspective+Gemini
        all_results.append(
            {
                "comment": comment[:200],
                "is_toxic": True,
                "severity": "High",
                "score": 0.8,
                "sentiment": "negative",
                "method": "regex",
                "reason": "Khớp mẫu ngôn ngữ độc hại đã biết",
                "categories": {},
            }
        )

    # --- Handle obvious clean (no API needed) ---
    for comment in filtered["obvious_clean"]:
        all_results.append(
            {
                "comment": comment[:200],
                "is_toxic": False,
                "severity": "None",
                "score": 0.0,
                "sentiment": "positive",
                "method": "filter",
                "reason": "Bình luận tích cực rõ ràng",
                "categories": {},
            }
        )

    # --- Handle spam (no API needed) ---
    for comment in filtered["spam"]:
        all_results.append(
            {
                "comment": comment[:200],
                "is_toxic": False,
                "severity": "None",
                "score": 0.0,
                "sentiment": "neutral",
                "method": "filter",
                "reason": "Spam/bình luận trống",
                "categories": {},
            }
        )

    # --- Handle ambiguous comments: regex first, then batch Gemini ---
    ambiguous = filtered["ambiguous"]
    still_ambiguous = []

    for comment in ambiguous:
        # Use REGEX ONLY here (not full analyze() which triggers Perspective+Gemini per comment)
        regex_result = None
        try:
            if (
                hasattr(toxicity_v4_engine, "regex_analyzer")
                and toxicity_v4_engine.regex_analyzer
            ):
                regex_result = toxicity_v4_engine._analyze_regex(comment)
        except Exception:
            pass

        if regex_result and regex_result.get("is_toxic"):
            all_results.append(
                {
                    "comment": comment[:200],
                    "is_toxic": True,
                    "severity": "High",
                    "score": 0.8,
                    "sentiment": "negative",
                    "method": "regex",
                    "reason": "Phát hiện bởi regex pattern",
                    "categories": {},
                }
            )
            api_calls_saved += 1
        else:
            still_ambiguous.append(comment)

    # --- Batch Gemini analysis for truly ambiguous comments ---
    if still_ambiguous:
        # Check cache first
        cache_key = f"batch:{hash(url)}:{hash(str(sorted(still_ambiguous)))}"
        cached = cache_manager.get(cache_key)

        if cached:
            print(f"✅ [v4] Batch cache hit ({len(still_ambiguous)} comments)")
            all_results.extend(cached)
        else:
            # Process in chunks of 25 (safe token limit) with rate limit sleep
            import time

            BATCH_SIZE = 25
            all_batch_results = []

            for chunk_idx in range(0, len(still_ambiguous), BATCH_SIZE):
                chunk = still_ambiguous[chunk_idx : chunk_idx + BATCH_SIZE]
                chunk_num = chunk_idx // BATCH_SIZE + 1
                total_chunks = (len(still_ambiguous) + BATCH_SIZE - 1) // BATCH_SIZE

                if total_chunks > 1:
                    print(
                        f"⚡ Batch {chunk_num}/{total_chunks}: Analyzing {len(chunk)} comments..."
                    )

                chunk_results = _batch_gemini_analyze(
                    chunk, article_summary, learning_ctx
                )
                all_batch_results.extend(chunk_results)

                # Rate limit protection: sleep between chunks (10 RPM = ~6s between calls)
                if chunk_idx + BATCH_SIZE < len(still_ambiguous):
                    print(f"   ⏳ Rate limit protection: sleeping 7s...")
                    time.sleep(7)

            all_results.extend(all_batch_results)
            if all_batch_results:
                cache_manager.set(cache_key, all_batch_results)

    # Calculate stats
    toxic_results = [r for r in all_results if r.get("is_toxic")]
    toxic_count = len(toxic_results)

    return {
        "total": total,
        "toxic_count": toxic_count,
        "toxic_percentage": round(toxic_count / total * 100, 1) if total > 0 else 0.0,
        "toxic_comments": [r for r in all_results if r.get("is_toxic")][:10],
        "details": all_results,
        "filter_stats": {
            "obvious_toxic": len(filtered["obvious_toxic"]),
            "obvious_clean": len(filtered["obvious_clean"]),
            "spam": len(filtered["spam"]),
            "ambiguous": len(filtered["ambiguous"]),
            "sent_to_ai": len(still_ambiguous),
        },
        "api_calls_saved": api_calls_saved,
    }


def _batch_gemini_analyze(
    comments: List[str], article_summary: str, learning_ctx: str = ""
) -> List[dict]:
    """
    Send multiple comments in ONE Gemini API call with article context.
    Returns list of analysis dicts.
    """
    from google import genai
    from google.genai import types

    if not comments:
        return []

    # Circuit breaker: check how many keys are left
    available = len(batch_key_rotator.api_keys) - len(batch_key_rotator.exhausted_keys)
    if available <= 0:
        print("⚠️ [v4] All API keys exhausted — using regex fallback for batch")
        return _fallback_results(comments)

    max_batch_attempts = min(3, available)  # Try up to 3 different keys
    for attempt in range(max_batch_attempts):
        api_key = batch_key_rotator.get_current_key()
        if not api_key:
            print("⚠️ [v4] No API key available for batch analysis")
            return _fallback_results(comments)

        try:
            return _try_batch_gemini(comments, article_summary, api_key, learning_ctx)
        except Exception as e:
            error_str = str(e)
            error_lower = error_str.lower()
            if "429" in error_lower or "quota" in error_lower:
                from src.models.gemini_llm import APIKeyRotator

                retry_delay = APIKeyRotator.parse_retry_delay(error_str)
                print(
                    f"⚠️ [v4] Batch attempt {attempt+1}/{max_batch_attempts} got 429, cooldown {retry_delay:.0f}s..."
                )
                batch_key_rotator.mark_key_rate_limited(retry_delay)
                continue
            else:
                print(f"⚠️ [v4] Batch analysis failed: {e}")
                return _fallback_results(comments)

    print("⚠️ [v4] All batch attempts exhausted — using regex fallback")
    return _fallback_results(comments)


def _try_batch_gemini(
    comments: List[str], article_summary: str, api_key: str, learning_ctx: str = ""
) -> List[dict]:
    """Execute a single batch Gemini call. Raises on 429 for retry."""
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)

    # Build numbered comment list for clear parsing
    comments_text = "\n".join(f'{i+1}. "{c[:300]}"' for i, c in enumerate(comments))

    context_line = ""
    if article_summary:
        context_line = f"Bối cảnh bài báo: {article_summary[:500]}\n\n"

    # v4.9: Inject learning from user feedback
    learning_line = ""
    if learning_ctx:
        learning_line = f"\n{learning_ctx}\n\n"

    prompt = f"""{context_line}{learning_line}Phân tích {len(comments)} bình luận sau:
{comments_text}

Với MỖI bình luận, trả lời JSON array:
[
  {{"index": 1, "is_toxic": false, "severity": "none", "sentiment": "neutral", "reason": "Lý do ngắn gọn"}},
  ...
]

Quy tắc:
- severity: "none", "low", "medium", "high"
- sentiment: "positive", "negative", "neutral"
- XÉT THEO NGỮ CẢNH bài báo. VD: "quá tệ" về sản phẩm = negative nhưng KHÔNG toxic
- Chỉ đánh dấu toxic nếu có ngôn ngữ xúc phạm, đe dọa, hoặc kích động thù hận
- Trả lời CHỈ JSON array, không thêm gì khác"""

    # Scale tokens based on batch size (~150 tokens per comment result with Vietnamese text)
    max_tokens = min(8000, max(1500, len(comments) * 200))

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.1,  # Lower = more consistent JSON
            max_output_tokens=max_tokens,
        ),
    )

    batch_key_rotator.increment_request_count()

    # Parse response
    raw = response.text.strip()
    # Strip markdown fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        # Try to salvage partial/truncated JSON
        import re as _re

        parsed = None
        # First: try to extract a complete JSON array
        match = _re.search(r"\[.*\]", raw, _re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group())
            except json.JSONDecodeError:
                # Array found but still malformed — try repair
                try:
                    repaired = _repair_truncated_json(match.group())
                    parsed = json.loads(repaired)
                    print(f"✅ [v4] Repaired truncated JSON ({len(parsed)} items)")
                except json.JSONDecodeError:
                    pass

        if parsed is None:
            # Try adding missing closing brackets to the whole response
            try:
                repaired = _repair_truncated_json(raw)
                parsed = json.loads(repaired)
                print(f"✅ [v4] Repaired raw JSON ({len(parsed)} items)")
            except json.JSONDecodeError:
                # Last resort: extract individual complete JSON objects
                objects = _re.findall(r"\{[^{}]*\}", raw)
                if objects:
                    parsed = []
                    for obj_str in objects:
                        try:
                            parsed.append(json.loads(obj_str))
                        except json.JSONDecodeError:
                            continue
                    print(
                        f"✅ [v4] Extracted {len(parsed)} objects from malformed JSON"
                    )
                else:
                    print(f"⚠️ [v4] Could not parse Gemini response, using fallback")
                    return _fallback_results(comments)

    results = []
    for item in parsed:
        idx = item.get("index", 0) - 1
        comment_text = comments[idx] if 0 <= idx < len(comments) else ""
        results.append(
            {
                "comment": comment_text[:200],
                "is_toxic": item.get("is_toxic", False),
                "severity": item.get("severity", "none").capitalize(),
                "score": 0.8 if item.get("is_toxic") else 0.1,
                "sentiment": item.get("sentiment", "neutral"),
                "method": "gemini_context",
                "reason": item.get("reason", ""),
                "categories": {},
            }
        )

    # If we got fewer results than comments, fill in the rest
    processed_indices = {item.get("index", 0) - 1 for item in parsed}
    for i, c in enumerate(comments):
        if i not in processed_indices:
            results.append(
                {
                    "comment": c[:200],
                    "is_toxic": False,
                    "severity": "None",
                    "score": 0.0,
                    "sentiment": "neutral",
                    "method": "gemini_context",
                    "reason": "Không phát hiện vấn đề",
                    "categories": {},
                }
            )

    print(f"✅ [v4] Batch analyzed {len(comments)} comments (1 API call)")
    return results


def _repair_truncated_json(raw: str) -> str:
    """
    Attempt to repair truncated JSON from Gemini (e.g. unterminated strings, missing brackets).
    Common issue: Gemini hits max_output_tokens mid-string.
    """
    import re as _re

    s = raw.strip()

    # Remove trailing incomplete object/entry (after last complete },)
    # Find last complete JSON object ending with }
    last_complete = s.rfind("},")
    if last_complete > 0:
        s = s[: last_complete + 1]  # Keep up to the }

    # If we're inside an unterminated string, close it
    # Count unescaped quotes
    in_string = False
    for ch in s:
        if ch == '"' and (not in_string or s[max(0, s.index(ch) - 1)] != "\\"):
            in_string = not in_string
    if in_string:
        s += '"'

    # Close any open braces/brackets
    open_braces = s.count("{") - s.count("}")
    open_brackets = s.count("[") - s.count("]")
    s += "}" * max(0, open_braces)
    s += "]" * max(0, open_brackets)

    return s


def _fallback_results(comments: List[str]) -> List[dict]:
    """Fallback: REGEX ONLY (no Perspective/Gemini API calls) when AI is unavailable."""
    results = []
    for c in comments:
        # Use v2 regex engine DIRECTLY — do NOT call toxicity_v4_engine.analyze()
        # because that triggers Perspective API + Gemini calls per comment = API storm
        is_toxic = False
        score = 0.0
        severity = "None"
        try:
            if (
                hasattr(toxicity_v4_engine, "regex_analyzer")
                and toxicity_v4_engine.regex_analyzer
            ):
                regex_result = toxicity_v4_engine._analyze_regex(c)
                if regex_result and regex_result.get("is_toxic"):
                    is_toxic = True
                    score = 0.8
                    severity = "High"
        except Exception:
            pass
        results.append(
            {
                "comment": c[:200],
                "is_toxic": is_toxic,
                "severity": severity,
                "score": score,
                "sentiment": "neutral",
                "method": "regex_fallback",
                "reason": "AI không khả dụng, dùng regex",
                "categories": {},
            }
        )
    return results


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
