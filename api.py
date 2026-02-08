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

from src.models.article_summarizer_v3 import ArticleSummarizer
from src.models.fact_checker_v3 import FactCheckerV3
from src.models.gemini_llm import API_KEY_POOL, MODEL_NAME, APIKeyRotator, GeminiAgent
from src.models.risk_scorer_v3 import RiskScorerV3
from src.models.sentiment import SentimentAnalyzer

# v3 Enhanced Components
from src.models.sentiment_v3 import SentimentAnalyzerV3
from src.models.toxicity import ToxicityAnalyzer
from src.models.toxicity_v3 import ToxicityAnalyzerV3
from src.utils.cache_manager import CacheManager
from src.utils.comment_filter import CommentFilter

app = FastAPI(title="VnContentGuard Pro API", version="3.1")

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

    # v3 Enhanced Engines (use fallback mode for faster startup)
    sentiment_v3_engine = SentimentAnalyzerV3(use_phobert=False)
    toxicity_v3_engine = ToxicityAnalyzerV3(use_detoxify=False)
    fact_checker_v3_engine = FactCheckerV3(key_rotator=shared_key_rotator)
    risk_scorer_v3_engine = RiskScorerV3(
        sentiment_analyzer=sentiment_v3_engine,
        toxicity_analyzer=toxicity_v3_engine,
        fact_checker=fact_checker_v3_engine,
    )

    # v3.1 New Components
    cache_manager = CacheManager(ttl_seconds=86400)  # 24-hour cache
    comment_filter = CommentFilter()
    article_summarizer = ArticleSummarizer(cache_manager, key_rotator=shared_key_rotator)

    # Reuse same shared key rotator for batch comment analysis
    batch_key_rotator = shared_key_rotator

    print("✅ AI Server Ready! (v3.1 with Summary + Batch Analysis)")
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
    v3.1 Enhanced full content scan endpoint.

    New features:
    - Article summary (AI-generated, cached per URL)
    - Context-aware batch comment analysis (1 API call for N comments)
    - Smart comment filtering (skip obvious toxic/clean/spam)
    - API usage optimization (70-80% fewer Gemini calls)
    """
    print(f"📥 [v3.1] Received Scan Request for: {req.url}")
    try:
        # ========== 0. ARTICLE SUMMARY (NEW) ==========
        article_summary = {"text": "", "method": "none", "cached": False}
        summary_text = ""

        if len(req.article_text) > 30:
            try:
                article_summary = article_summarizer.summarize(
                    req.article_text, req.url
                )
                summary_text = article_summary.get("summary", "")
                print(
                    f"✅ [v3.1] Summary: {article_summary['method']} ({len(summary_text)} chars)"
                )
            except Exception as e:
                print(f"⚠️  [v3.1] Summary failed: {e}")

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
                    f"✅ [v3.1] Sentiment: {sentiment_v3['overall']} (confidence: {sentiment_v3['confidence']:.2f})"
                )
            except Exception as e:
                print(f"⚠️  [v3.1] Sentiment analysis failed: {e}")
                sentiment_v3 = {
                    "label": "Neutral",
                    "confidence": 0.0,
                    "intensity": "Weak",
                    "method": "error",
                }
        else:
            print(
                f"⚠️  [v3.1] Article too short for sentiment ({len(req.article_text)} chars)"
            )

        # ========== 2. TOXICITY DETECTION v3 (4-layer, article body) ==========
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
                    f"✅ [v3.1] Toxicity: {toxicity_v3['severity']} (score: {toxicity_v3['overall_score']:.2f})"
                )
            except Exception as e:
                print(f"⚠️  [v3.1] Toxicity detection failed: {e}")

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
                    f"✅ [v3.1] Fact Check: {fact_check_v3['verdict']} (credibility: {fact_check_v3['score']})"
                )
            except Exception as e:
                print(f"⚠️  [v3.1] Fact-checking failed: {e}")
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
                    f"✅ [v3.1] Risk Score: {risk_score_v3['risk_score']:.1f}/100 ({risk_score_v3['risk_level']})"
                )
            except Exception as e:
                print(f"⚠️  [v3.1] Risk scoring failed: {e}")

        # ========== 5. COMMENTS ANALYSIS (v3.1 - Context-Aware Batch) ==========
        comments_analysis = {
            "total": 0,
            "toxic_count": 0,
            "toxic_percentage": 0.0,
            "toxic_comments": [],
            "filter_stats": {},
            "api_calls_saved": 0,
        }

        if req.comments:
            comments_analysis = _analyze_comments_v31(
                req.comments[:50], summary_text, req.url
            )

        # ========== 6. COMPILE v3.1 RESPONSE ==========
        response = {
            "version": "3.1",
            "article_summary": article_summary,
            "sentiment_v3": sentiment_v3,
            "toxicity_v3": toxicity_v3,
            "fact_check_v3": fact_check_v3,
            "risk_score_v3": risk_score_v3,
            "comments_analysis": comments_analysis,
            "url": req.url,
            "cache_stats": cache_manager.get_stats(),
        }

        print(
            f"✅ [v3.1] Analysis complete. Risk: {risk_score_v3['risk_score']:.1f}/100, "
            f"Toxics: {comments_analysis['toxic_count']}, "
            f"API saved: {comments_analysis.get('api_calls_saved', 0)}"
        )
        return response

    except Exception as e:
        print(f"❌ [v3.1] Critical Error: {e}")
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"v3.1 analysis error: {str(e)}")


def _analyze_comments_v31(
    comments: List[str], article_summary: str, url: str
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

    api_calls_saved = len(filtered["obvious_toxic"]) + len(filtered["obvious_clean"]) + len(filtered["spam"])

    print(f"📊 [v3.1] Comment filtering:")
    print(f"   Total: {total}")
    print(f"   Obvious toxic: {len(filtered['obvious_toxic'])}")
    print(f"   Obvious clean: {len(filtered['obvious_clean'])}")
    print(f"   Spam: {len(filtered['spam'])}")
    print(f"   Ambiguous (need AI): {len(filtered['ambiguous'])}")
    print(f"   API calls saved: {api_calls_saved}/{total}")

    all_results = []

    # --- Handle obvious toxic (regex-detected, no API needed) ---
    for comment in filtered["obvious_toxic"]:
        # Still run full regex analysis to get the category
        tox_result = toxicity_v3_engine.analyze(comment)
        all_results.append({
            "comment": comment[:200],
            "is_toxic": True,
            "severity": tox_result.get("severity", "High"),
            "score": tox_result.get("overall_score", 0.8),
            "sentiment": "negative",
            "method": "regex",
            "reason": "Khớp mẫu ngôn ngữ độc hại đã biết",
            "categories": tox_result.get("categories", {}),
        })

    # --- Handle obvious clean (no API needed) ---
    for comment in filtered["obvious_clean"]:
        all_results.append({
            "comment": comment[:200],
            "is_toxic": False,
            "severity": "None",
            "score": 0.0,
            "sentiment": "positive",
            "method": "filter",
            "reason": "Bình luận tích cực rõ ràng",
            "categories": {},
        })

    # --- Handle spam (no API needed) ---
    for comment in filtered["spam"]:
        all_results.append({
            "comment": comment[:200],
            "is_toxic": False,
            "severity": "None",
            "score": 0.0,
            "sentiment": "neutral",
            "method": "filter",
            "reason": "Spam/bình luận trống",
            "categories": {},
        })

    # --- Handle ambiguous comments: regex first, then batch Gemini ---
    ambiguous = filtered["ambiguous"]
    still_ambiguous = []

    for comment in ambiguous:
        tox_result = toxicity_v3_engine.analyze(comment)
        if tox_result.get("is_toxic"):
            all_results.append({
                "comment": comment[:200],
                "is_toxic": True,
                "severity": tox_result.get("severity", "Medium"),
                "score": tox_result.get("overall_score", 0.6),
                "sentiment": "negative",
                "method": "regex",
                "reason": "Phát hiện bởi regex pattern",
                "categories": tox_result.get("categories", {}),
            })
            api_calls_saved += 1
        else:
            still_ambiguous.append(comment)

    # --- Batch Gemini analysis for truly ambiguous comments ---
    if still_ambiguous:
        # Check cache first
        cache_key = f"batch:{hash(url)}:{hash(str(sorted(still_ambiguous)))}"
        cached = cache_manager.get(cache_key)

        if cached:
            print(f"✅ [v3.1] Batch cache hit ({len(still_ambiguous)} comments)")
            all_results.extend(cached)
        else:
            batch_results = _batch_gemini_analyze(still_ambiguous, article_summary)
            all_results.extend(batch_results)
            if batch_results:
                cache_manager.set(cache_key, batch_results)

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
    comments: List[str], article_summary: str
) -> List[dict]:
    """
    Send multiple comments in ONE Gemini API call with article context.
    Returns list of analysis dicts.
    """
    from google import genai
    from google.genai import types

    if not comments:
        return []

    try:
        api_key = batch_key_rotator.get_current_key()
        if not api_key:
            print("⚠️ [v3.1] No API key available for batch analysis")
            return _fallback_results(comments)

        client = genai.Client(api_key=api_key)

        # Build numbered comment list for clear parsing
        comments_text = "\n".join(
            f"{i+1}. \"{c[:300]}\"" for i, c in enumerate(comments)
        )

        context_line = ""
        if article_summary:
            context_line = f"Bối cảnh bài báo: {article_summary[:500]}\n\n"

        prompt = f"""{context_line}Phân tích {len(comments)} bình luận sau:
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

        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.2,
                max_output_tokens=1500,
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

        parsed = json.loads(raw)

        results = []
        for item in parsed:
            idx = item.get("index", 0) - 1
            comment_text = comments[idx] if 0 <= idx < len(comments) else ""
            results.append({
                "comment": comment_text[:200],
                "is_toxic": item.get("is_toxic", False),
                "severity": item.get("severity", "none").capitalize(),
                "score": 0.8 if item.get("is_toxic") else 0.1,
                "sentiment": item.get("sentiment", "neutral"),
                "method": "gemini_context",
                "reason": item.get("reason", ""),
                "categories": {},
            })

        # If we got fewer results than comments, fill in the rest
        processed_indices = {item.get("index", 0) - 1 for item in parsed}
        for i, c in enumerate(comments):
            if i not in processed_indices:
                results.append({
                    "comment": c[:200],
                    "is_toxic": False,
                    "severity": "None",
                    "score": 0.0,
                    "sentiment": "neutral",
                    "method": "gemini_context",
                    "reason": "Không phát hiện vấn đề",
                    "categories": {},
                })

        print(f"✅ [v3.1] Batch analyzed {len(comments)} comments (1 API call)")
        return results

    except json.JSONDecodeError as e:
        print(f"⚠️ [v3.1] Batch JSON parse failed: {e}")
        return _fallback_results(comments)
    except Exception as e:
        error_str = str(e).lower()
        print(f"⚠️ [v3.1] Batch analysis failed: {e}")
        if "429" in error_str or "quota" in error_str:
            batch_key_rotator.mark_key_exhausted()
        return _fallback_results(comments)


def _fallback_results(comments: List[str]) -> List[dict]:
    """Fallback: run regex-only analysis on comments when Gemini unavailable."""
    results = []
    for c in comments:
        tox = toxicity_v3_engine.analyze(c)
        results.append({
            "comment": c[:200],
            "is_toxic": tox.get("is_toxic", False),
            "severity": tox.get("severity", "None"),
            "score": tox.get("overall_score", 0.0),
            "sentiment": "neutral",
            "method": "regex_fallback",
            "reason": "AI không khả dụng, dùng regex",
            "categories": tox.get("categories", {}),
        })
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
