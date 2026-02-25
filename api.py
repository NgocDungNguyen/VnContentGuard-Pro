import asyncio
import json
import platform
import sys
import threading
import time
from datetime import datetime
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

from src.models.article_summarizer_v6 import ArticleSummarizer
from src.models.fact_checker_v6 import FactCheckerV6
from src.models.gemini_llm import API_KEY_POOL, MODEL_NAME, APIKeyRotator, GeminiAgent
from src.models.reranker import ScoreReranker
from src.models.risk_scorer_v6 import RiskScorerV6
from src.models.sentiment import SentimentAnalyzer

# v6 Enhanced Components
from src.models.sentiment_v6 import SentimentAnalyzerV6
from src.models.toxicity import ToxicityAnalyzer
from src.models.toxicity_v6 import ToxicityAnalyzerV6
from src.models.unified_analyzer import UnifiedAnalyzer
from src.utils.blocklist import CommunityBlocklist
from src.utils.cache_manager import CacheManager
from src.utils.comment_filter import CommentFilter
from src.utils.feedback_store import FeedbackStore

app = FastAPI(title="VnContentGuard Pro API", version="6.0")

# Enable CORS for Chrome Extension
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Chrome extension can reach from any origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Server boot timestamp for uptime tracking
SERVER_START_TIME = time.time()


class RequestTracker:
    """Thread-safe daily Gemini API call counter.
    Resets automatically at UTC midnight."""

    def __init__(self):
        self._lock = threading.Lock()
        self._count = 0
        self._date = datetime.utcnow().date()

    def increment(self, n: int = 1):
        with self._lock:
            self._check_reset()
            self._count += n

    def get_count(self) -> int:
        with self._lock:
            self._check_reset()
            return self._count

    def _check_reset(self):
        today = datetime.utcnow().date()
        if today > self._date:
            self._count = 0
            self._date = today


request_tracker = RequestTracker()

print("⏳ Booting up AI Engine...")
try:
    # SINGLE shared key rotator for ALL Gemini calls (prevents burning keys)
    shared_key_rotator = APIKeyRotator(API_KEY_POOL)

    # v2 Engines
    toxicity_engine = ToxicityAnalyzer()
    gemini_agent = GeminiAgent(key_rotator=shared_key_rotator)
    sentiment_engine = SentimentAnalyzer()

    # v6 Enhanced Engines (use fallback mode for faster startup)
    sentiment_v6_engine = SentimentAnalyzerV6(use_phobert=False)
    toxicity_v6_engine = ToxicityAnalyzerV6(use_detoxify=False)
    fact_checker_v6_engine = FactCheckerV6(key_rotator=shared_key_rotator)
    risk_scorer_v6_engine = RiskScorerV6(
        sentiment_analyzer=sentiment_v6_engine,
        toxicity_analyzer=toxicity_v6_engine,
        fact_checker=fact_checker_v6_engine,
    )

    # v6 New Components
    cache_manager = CacheManager(ttl_seconds=86400)  # 24-hour cache
    comment_filter = CommentFilter()
    article_summarizer = ArticleSummarizer(
        cache_manager, key_rotator=shared_key_rotator
    )

    # v6.0 Feedback Store
    feedback_store = FeedbackStore()

    # v6.0 Community Blocklist
    community_blocklist = CommunityBlocklist()

    # v6 ARCH-01: Unified Single-Pass Analyzer
    unified_analyzer = UnifiedAnalyzer(key_rotator=shared_key_rotator)

    # v6.9: Score Re-Ranker (domain-level calibration from user corrections)
    reranker = ScoreReranker()

    # Reuse same shared key rotator for batch comment analysis
    batch_key_rotator = shared_key_rotator

    print("✅ AI Server Ready! (v6 with Unified Analysis + Summary + Batch + Reranker)")
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


# ============================================================================
# ARCH-01: Structured Scan Models (v6 Unified Analysis)
# ============================================================================


class StructuredArticle(BaseModel):
    title: str = ""
    author: str = ""
    published_date: str = ""
    body: str = ""
    word_count: int = 0


class StructuredComment(BaseModel):
    text: str
    author: str = ""
    timestamp: str = ""
    reactions: int = 0
    is_reply: bool = False


class StructuredMetadata(BaseModel):
    domain: str = ""
    comment_count_visible: int = 0
    comment_count_total: int = 0
    reactions_total: int = 0
    shares: int = 0
    page_language: str = "vi"


class StructuredScanRequest(BaseModel):
    """
    ARCH-01: Structured page data from structuredScrape() in popup.js.
    Enables single-pass unified Gemini analysis (70-80% fewer API calls).
    """

    page_type: str = (
        "generic"  # facebook_post|news_article|youtube_video|tiktok|generic
    )
    url: str
    scraped_at: str = ""
    article: StructuredArticle = StructuredArticle()
    comments: List[StructuredComment] = []
    metadata: StructuredMetadata = StructuredMetadata()


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
    """v6.0 — API usage statistics, daily usage tracking, and system health."""
    try:
        gemini_status = gemini_agent.get_status()
        feedback_stats = feedback_store.get_stats()
        blocklist_stats = community_blocklist.get_stats()
        cache_stats = cache_manager.get_stats()

        # Daily usage from server-level request tracker (thread-safe)
        key_status = shared_key_rotator.get_status()
        daily_requests = request_tracker.get_count()

        # Gemini free tier: 1,500 requests/day/key → total daily capacity
        total_keys = len(API_KEY_POOL)
        daily_limit = total_keys * 1500
        daily_remaining = max(0, daily_limit - daily_requests)

        # Uptime
        uptime_seconds = int(time.time() - SERVER_START_TIME)

        return {
            "version": "6.0.0",
            "model": gemini_status.get("model", "unknown"),
            "using_fallback": gemini_status.get("using_fallback", False),
            "api_keys": {
                "total": total_keys,
                "available": gemini_status.get("available_count", 0),
                "exhausted": gemini_status.get("exhausted_count", 0),
                "cooldown": key_status.get("cooldown_count", 0),
                "current": gemini_status.get("current_key", 0),
            },
            "usage": {
                "daily_requests": daily_requests,
                "daily_limit": daily_limit,
                "daily_remaining": daily_remaining,
                "usage_percent": (
                    round(daily_requests / daily_limit * 100, 1)
                    if daily_limit > 0
                    else 0
                ),
            },
            "cache": cache_stats,
            "feedback": feedback_stats,
            "blocklist": blocklist_stats,
            "uptime_seconds": uptime_seconds,
            "status": "🟢 Online",
        }
    except Exception as e:
        return {"version": "6.0.0", "status": "🔴 Error", "error": str(e)}


# ============================================================================
# User Feedback Endpoint (v6.0)
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
    """v6.0 \u2014 Accept user feedback on scan results. Feeds into learning system."""
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
# Community Blocklist Endpoints (v6.0)
# ============================================================================


class ReportRequest(BaseModel):
    """Request model for community report."""

    url: str
    risk_score: float = 0.0
    reason: str = ""


@app.post("/api/report")
def report_page(req: ReportRequest):
    """v6.0 \u2014 Report a page/domain to the community blocklist."""
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
    """v6.0 \u2014 Get community blocklist (domains with 5+ reports)."""
    try:
        domains = community_blocklist.get_blocklist()
        return {"blocklist": domains, "count": len(domains)}
    except Exception as e:
        return {"blocklist": [], "count": 0, "error": str(e)}


@app.get("/api/blocklist/check")
def check_blocklist(url: str):
    """v6.0 \u2014 Check if a URL is blocked."""
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
    """v6.0 \u2014 Get feedback learning data for a domain."""
    try:
        return feedback_store.get_domain_feedback(url)
    except Exception as e:
        return {"domain": url, "total": 0, "error": str(e)}


# ============================================================================
# Feature 6.9 — User Correction + Model Re-Ranking
# ============================================================================


class CorrectionRequest(BaseModel):
    """Request model for score correction submission."""

    url: str
    domain: str = ""
    original_risk_score: float
    corrected_risk_score: float
    original_toxicity: float = 0.0
    corrected_toxicity: float = 0.0
    reason: str = ""  # too_high|too_low|cultural_context|sarcasm|wrong_category
    category: str = "other"  # news|social|video|other
    examples: List[str] = []  # specific phrases AI got wrong


@app.post("/api/correction")
def submit_correction(req: CorrectionRequest):
    """Feature 6.9 — Accept user score correction; feeds into domain re-ranker."""
    try:
        # Derive domain from URL if not provided
        domain = req.domain
        if not domain and req.url:
            try:
                from urllib.parse import urlparse

                domain = urlparse(req.url).hostname or req.url
            except Exception:
                domain = req.url

        # Record corrections in re-ranker
        reranker.record_correction(
            domain, "risk_score", req.original_risk_score, req.corrected_risk_score
        )
        if req.corrected_toxicity != req.original_toxicity:
            reranker.record_correction(
                domain, "toxicity", req.original_toxicity, req.corrected_toxicity
            )

        # Also persist to feedback store for learning context
        try:
            feedback_store.add_feedback(
                url=req.url,
                rating="negative",
                correction=f"[{req.reason}] Risk corrected from {req.original_risk_score:.0f} to {req.corrected_risk_score:.0f}. Examples: {', '.join(req.examples)}",
                modules={},
                scan_results={},
            )
        except Exception:
            pass  # non-critical

        adjustment = reranker.get_adjustment(domain, "risk_score")
        stats = reranker.get_stats()

        print(
            f"📐 Correction: {domain} risk {req.original_risk_score:.0f}→"
            f"{req.corrected_risk_score:.0f} (reason: {req.reason})"
        )
        return {
            "status": "recorded",
            "domain": domain,
            "adjustment_now": round(adjustment, 1),
            "reranker_stats": stats,
            "message": f"Đã lưu hiệu chỉnh cho {domain}. Các lần quét tiếp theo sẽ được điều chỉnh.",
        }
    except Exception as e:
        print(f"⚠️ Correction error: {e}")
        return {"status": "error", "message": str(e)}


@app.get("/api/reranker/stats")
def get_reranker_stats():
    """Feature 6.9 — Return re-ranker statistics."""
    return reranker.get_stats()


# ============================================================================
# Feature 6.12 — Scam URL Database Contribution
# ============================================================================


class ScamReportRequest(BaseModel):
    """Request model for scam page report."""

    url: str
    scam_type: str = (
        "unknown"  # financial_phishing|lottery_scam|fake_government|investment_scam|impersonation
    )
    ai_confidence: float = 0.0
    user_confirmed: bool = False
    evidence_phrases: List[str] = []


@app.post("/api/report/scam")
async def report_scam(req: ScamReportRequest):
    """Feature 6.12 — Report a scam URL to communal blocklist + PhishTank (best-effort)."""
    import hashlib

    try:
        url_hash = hashlib.sha256(req.url.encode()).hexdigest()
        tracking_id = url_hash[:12].upper()

        # Add to community blocklist with scam reason
        try:
            community_blocklist.add_report(
                url=req.url,
                risk_score=95.0,  # Scam = always high risk
                reason=f"scam:{req.scam_type}",
            )
        except Exception:
            pass

        # Attempt PhishTank submission (fire-and-forget, optional)
        submitted_to = ["community_blocklist"]
        phishtank_key = __import__("os").getenv("PHISHTANK_API_KEY", "")
        if phishtank_key:
            try:
                import requests as _req

                _req.post(
                    "https://www.phishtank.com/api/",
                    data={"url": req.url, "app_key": phishtank_key, "format": "json"},
                    timeout=8,
                )
                submitted_to.append("phishtank")
            except Exception:
                pass  # non-critical

        # Log scam report to feedback store for analytics
        try:
            feedback_store.add_feedback(
                url=req.url,
                rating="negative",
                correction=f"[SCAM:{req.scam_type}] confidence={req.ai_confidence:.0%} user_confirmed={req.user_confirmed} evidence={req.evidence_phrases[:3]}",
                modules={},
                scan_results={},
            )
        except Exception:
            pass

        scam_labels = {
            "financial_phishing": "Giả mạo ngân hàng / OTP",
            "lottery_scam": "Lừa đảo trúng thưởng",
            "fake_government": "Giả mạo cơ quan nhà nước",
            "investment_scam": "Lừa đảo đầu tư",
            "impersonation": "Giả mạo thương hiệu",
            "unknown": "Lừa đảo không xác định",
        }

        print(
            f"🦈 Scam report: {req.url} ({req.scam_type}) confidence={req.ai_confidence:.0%}"
        )
        return {
            "status": "reported",
            "tracking_id": tracking_id,
            "scam_type": scam_labels.get(req.scam_type, req.scam_type),
            "submitted_to": submitted_to,
            "user_confirmed": req.user_confirmed,
            "message": f"Đã báo cáo lừa đảo. Mã theo dõi: {tracking_id}",
        }
    except Exception as e:
        print(f"⚠️ Scam report error: {e}")
        return {"status": "error", "message": str(e)}


# ============================================================================
# Feature 6.13 — Bulk Analysis Mode
# ============================================================================


class BulkScanRequest(BaseModel):
    """Request model for bulk URL analysis."""

    urls: List[str]  # max 100 URLs
    scan_depth: str = "quick"  # "quick" = domain-level only | "full" = fetch + AI
    include_summary: bool = False


@app.post("/analyze/v6/bulk")
async def bulk_analyze(req: BulkScanRequest):
    """
    Feature 6.13 — Bulk analysis of up to 100 URLs.

    quick mode: domain credibility + blocklist + URL scam patterns. Very fast, 0 Gemini calls.
    full  mode: fetch page HTML → extract text → sequential AI analysis (rate-limited).
    """
    import asyncio
    import re as _re
    from urllib.parse import urlparse

    if len(req.urls) > 100:
        raise HTTPException(status_code=400, detail="Tối đa 100 URL mỗi lần")

    if not req.urls:
        return {"total": 0, "high_risk_count": 0, "results": []}

    # ── QUICK MODE: domain-level analysis, no page fetch, no Gemini ─────────
    async def quick_analyze_url(url: str) -> dict:
        import time as _time

        t_start = _time.time()
        try:
            parsed = urlparse(url if "://" in url else "https://" + url)
            domain = parsed.hostname or url

            # Source credibility
            source_score = 50
            source_verdict = "Chưa biết"
            try:
                if fact_checker_v6_engine.source_analyzer:
                    sc = fact_checker_v6_engine.source_analyzer.analyze(url)
                    source_score = sc.get("reputation_score", 50)
                    source_verdict = sc.get("verdict", "Chưa biết")
            except Exception:
                pass

            # Community blocklist
            is_blocked = community_blocklist.is_blocked(url)
            report_count = community_blocklist.get_domain_report_count(url)

            # URL-level scam pattern detection
            url_lower = url.lower()
            scam_url_patterns = [
                r"(free|mien-phi|trung-thuong|phan-thuong)",
                r"(kiemtien|lam-giau|thu-nhap|loi-nhuan)",
                r"(login|signin|account|verify|xac-minh).*\.(tk|ml|ga|cf|gq)",
                r"(bank|ngan-hang|vietcom|techcom|bidv|agri).*(?<!\.(com\.vn|vn)$)",
                r"update.*flash|antivirus.*free|win.*prize",
            ]
            url_scam_hit = any(_re.search(p, url_lower) for p in scam_url_patterns)

            # Seed blacklist check
            seed_blocked = domain in [
                "xvideos.com",
                "xnxx.com",
                "pornhub.com",
                "sunwin.me",
                "fb88.com",
                "w88.com",
                "bet365.com",
                "kiemtienonline.vip",
            ]

            # Quick risk estimation
            risk = 100 - source_score
            if is_blocked or seed_blocked:
                risk = min(100, risk + 40)
            if url_scam_hit:
                risk = min(100, risk + 30)
            if report_count >= 3:
                risk = min(100, risk + 20)
            risk = max(0, min(100, int(risk)))

            risk_level = (
                "Critical"
                if risk >= 75
                else "High" if risk >= 50 else "Medium" if risk >= 25 else "Low"
            )

            return {
                "url": url,
                "domain": domain,
                "risk_score": risk,
                "risk_level": risk_level,
                "source_credibility_score": source_score,
                "source_verdict": source_verdict,
                "blocklist_blocked": is_blocked or seed_blocked,
                "report_count": report_count,
                "url_scam_pattern": url_scam_hit,
                "toxicity_score": 0.0,
                "sentiment": "Neutral",
                "fact_check_status": "Quick scan only — no AI analysis",
                "title": "",
                "error": None,
                "scan_depth": "quick",
                "scan_time_ms": int((_time.time() - t_start) * 1000),
            }
        except Exception as e:
            return {
                "url": url,
                "domain": "",
                "risk_score": 0,
                "risk_level": "Unknown",
                "error": str(e),
                "scan_depth": "quick",
                "scan_time_ms": 0,
            }

    # ── FULL MODE: fetch page + AI analysis ─────────────────────────────────
    async def full_analyze_url(url: str) -> dict:
        import time as _time

        t_start = _time.time()
        try:
            from urllib.parse import urlparse as _up

            import aiohttp
            from bs4 import BeautifulSoup

            parsed = _up(url if "://" in url else "https://" + url)
            domain = parsed.hostname or url
            fetch_url = url if url.startswith("http") else "https://" + url

            # Fetch page (7s timeout)
            title = ""
            article_text = ""
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        fetch_url,
                        timeout=aiohttp.ClientTimeout(total=7),
                        headers={"User-Agent": "Mozilla/5.0 VnContentGuard/6.0"},
                        ssl=False,
                    ) as resp:
                        if resp.status == 200:
                            html = await resp.text(errors="replace")
                            soup = BeautifulSoup(html, "html.parser")
                            title = soup.title.string.strip() if soup.title else ""
                            # Remove scripts/styles
                            for tag in soup(["script", "style", "nav", "footer"]):
                                tag.decompose()
                            article_text = " ".join(
                                soup.get_text(separator=" ").split()
                            )[:2000]
            except Exception as fetch_err:
                article_text = ""
                title = f"(fetch failed: {fetch_err})"

            # Quick analysis first
            quick = await quick_analyze_url(url)

            if not article_text:
                quick["title"] = title
                quick["scan_depth"] = "full_fetch_failed"
                quick["scan_time_ms"] = int((_time.time() - t_start) * 1000)
                return quick

            # AI analysis on fetched content
            sentiment_result = {"overall": "Neutral", "confidence": 0.0}
            toxicity_result = {
                "is_toxic": False,
                "overall_score": 0.0,
                "severity": "Low",
            }
            fact_result = {"score": 50, "verdict": "Chưa xác minh"}
            try:
                sentiment_result = sentiment_v6_engine.analyze(article_text[:512])
            except Exception:
                pass
            try:
                toxicity_result = toxicity_v6_engine.analyze(article_text[:1000])
            except Exception:
                pass
            try:
                fact_result = fact_checker_v6_engine.check(article_text, url)
            except Exception:
                pass

            # Refined risk score
            ai_risk = max(
                quick["risk_score"],
                int(
                    (1 - fact_result.get("score", 50) / 100) * 60
                    + toxicity_result.get("overall_score", 0) * 40
                ),
            )
            ai_risk = max(0, min(100, ai_risk))
            risk_level = (
                "Critical"
                if ai_risk >= 75
                else "High" if ai_risk >= 50 else "Medium" if ai_risk >= 25 else "Low"
            )

            return {
                **quick,
                "title": title,
                "risk_score": ai_risk,
                "risk_level": risk_level,
                "toxicity_score": round(toxicity_result.get("overall_score", 0.0), 3),
                "sentiment": sentiment_result.get("overall", "Neutral"),
                "fact_check_status": fact_result.get("verdict", "Chưa xác minh"),
                "scan_depth": "full",
                "scan_time_ms": int((_time.time() - t_start) * 1000),
            }
        except Exception as e:
            return {
                "url": url,
                "domain": "",
                "risk_score": 0,
                "risk_level": "Unknown",
                "error": str(e),
                "scan_depth": "full",
                "scan_time_ms": 0,
            }

    # ── Execute ──────────────────────────────────────────────────────────────
    print(f"📊 [bulk] Scanning {len(req.urls)} URLs (depth: {req.scan_depth})")
    import asyncio as _asyncio

    if req.scan_depth == "quick":
        tasks = [quick_analyze_url(url) for url in req.urls]
        results = await _asyncio.gather(*tasks)
    else:
        # Full mode: process 3 at a time to respect rate limits
        results = []
        for i in range(0, len(req.urls), 3):
            batch = req.urls[i : i + 3]
            batch_results = await _asyncio.gather(*[full_analyze_url(u) for u in batch])
            results.extend(batch_results)
            if i + 3 < len(req.urls):
                await _asyncio.sleep(2)

    results = list(results)  # ensure plain list
    high_risk = sum(1 for r in results if r.get("risk_score", 0) >= 70)

    print(f"✅ [bulk] Done — {len(results)} URLs, {high_risk} high-risk")
    return {
        "total": len(results),
        "high_risk_count": high_risk,
        "scan_depth": req.scan_depth,
        "results": sorted(results, key=lambda r: -r.get("risk_score", 0)),
        "timestamp": datetime.now().isoformat(),
    }


# ============================================================================
# Feature 6.2 — Seed Blacklist Endpoint
# ============================================================================


@app.get("/api/blacklist/seed")
def get_blacklist_seed():
    """Feature 6.2 — Return curated seed list of harmful Vietnamese domains.
    Includes adult content, gambling, scam, & malware domains.
    The extension merges this into the user's local blacklist on first load.
    """
    seed_domains = [
        # Adult / NSFW
        "xvideos.com",
        "xnxx.com",
        "pornhub.com",
        "xhamster.com",
        "redtube.com",
        "youporn.com",
        "tube8.com",
        "spankbang.com",
        "txxx.com",
        "tnaflix.com",
        "beeg.com",
        "drtuber.com",
        "nuvid.com",
        "hclips.com",
        "4tube.com",
        "vporn.com",
        "fuq.com",
        "xtube.com",
        "slutload.com",
        "3movs.com",
        "faphouse.com",
        "sexhd.xxx",
        "porntrex.com",
        "fapvid.com",
        "phimset.com",
        "xemphim18.com",
        "phimsex.cc",
        "phimsexviet.org",
        "xem18.com",
        "18sex.vn",
        "truyen18.net",
        "truyen-sex.net",
        # Gambling / Ca do
        "bet188.com",
        "88bet.com",
        "fb88.com",
        "bk8.com",
        "m88.com",
        "w88.com",
        "188bet.com",
        "12bet.com",
        "fun88.com",
        "dafabet.com",
        "188.com",
        "bet365.com",
        "casino.vn",
        "casinovn.com",
        "betwin.vn",
        "lode88.com",
        "lo-de.net",
        "xoso.com.vn",
        "xsmb.info",
        "vietlott.xyz",
        "daga.live",
        "gamenhanh.com",
        "taixiu.com",
        "tanchuong.com",
        "gowin.io",
        "1xbet.com",
        "22bet.com",
        "melbet.com",
        # Scam / Lua dao
        "kiemtienonline.vip",
        "lamgiau.vn",
        "dautuvang.com",
        "binaryoption.vn",
        "forex-viet.com",
        "coinfast.vn",
        "bitcoin-viet.net",
        "dautu24h.net",
        "thuhappassive.com",
        "thuhap-passiveincome.com",
        "vieclamtainha.net",
        "vieclam247.net",
        "nhacaiso1.com",
        "topnhacai.com",
        # Malware / Phishing
        "update-flash.com",
        "flashplayer-vn.com",
        "antivirus-vn.com",
        "win-prizes.vn",
        "congratulation-gift.com",
        "survey-reward.vn",
        # Hate / Extremist
        "bacviet.org",
        "bacviet.net",
        "rfavietnam.com",
    ]

    deduped = sorted(set(seed_domains))
    return {
        "domains": deduped,
        "count": len(deduped),
        "version": "6.0",
        "description": "Danh sach den mac dinh - noi dung nguoi lon, co bac, lua dao, phan mem doc hai.",
    }


# ============================================================================
# v6.0 Streaming Analysis Endpoint (SSE)
# ============================================================================


@app.post("/analyze/v6/stream")
def analyze_content_v6_stream(req: ScanRequest):
    """
    v6.0 — Streaming analysis endpoint using Server-Sent Events.
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
                    # Track Gemini call (skip if cached)
                    if article_summary.get("method") == "gemini":
                        request_tracker.increment(1)
                except Exception as e:
                    print(f"⚠️ [SSE] Summary failed: {e}")
            yield _sse_event(
                "module", {"module": "article_summary", "data": article_summary}
            )

            # Module 2: Sentiment
            yield _sse_event(
                "progress", {"module": "sentiment", "status": "running", "step": "2/6"}
            )
            sentiment_v6 = {
                "label": "Neutral",
                "confidence": 0.0,
                "intensity": "Weak",
                "method": "none",
            }
            if len(req.article_text) > 5:
                try:
                    sentiment_v6 = sentiment_v6_engine.analyze(req.article_text[:512])
                except Exception as e:
                    print(f"⚠️ [SSE] Sentiment failed: {e}")
            yield _sse_event("module", {"module": "sentiment_v6", "data": sentiment_v6})

            # Module 3: Toxicity
            yield _sse_event(
                "progress", {"module": "toxicity", "status": "running", "step": "3/6"}
            )
            toxicity_v6 = {
                "is_toxic": False,
                "overall_score": 0.0,
                "severity": "Low",
                "categories": {},
                "detection_layers": [],
            }
            if len(req.article_text) > 5:
                try:
                    toxicity_v6 = toxicity_v6_engine.analyze(req.article_text[:1000])
                except Exception as e:
                    print(f"⚠️ [SSE] Toxicity failed: {e}")
            yield _sse_event("module", {"module": "toxicity_v6", "data": toxicity_v6})

            # Module 4: Fact Check
            yield _sse_event(
                "progress", {"module": "fact_check", "status": "running", "step": "4/6"}
            )
            fact_check_v6 = {
                "score": 50,
                "verdict": "Unverifiable",
                "confidence": "Low",
                "evidence": [],
                "verification_methods": [],
            }
            if len(req.article_text) > 20:
                try:
                    fact_check_v6 = fact_checker_v6_engine.check(
                        req.article_text, req.url
                    )
                    # Track Gemini verification call
                    if fact_check_v6.get("verification_methods"):
                        request_tracker.increment(1)
                except Exception as e:
                    print(f"⚠️ [SSE] Fact check failed: {e}")
            yield _sse_event(
                "module", {"module": "fact_check_v6", "data": fact_check_v6}
            )

            # Module 5: Risk Score — use pre-computed modules to avoid contradictions
            yield _sse_event(
                "progress", {"module": "risk_score", "status": "running", "step": "5/6"}
            )
            risk_score_v6 = {
                "risk_score": 0.0,
                "risk_level": "Low",
                "confidence": 0.0,
                "risk_breakdown": {},
                "warnings": [],
                "recommendations": [],
            }
            if len(req.article_text) > 20:
                try:
                    risk_score_v6 = risk_scorer_v6_engine.score_from_results(
                        req.article_text,
                        req.url,
                        sentiment_result=sentiment_v6,
                        toxicity_result=toxicity_v6,
                        fact_check_result=fact_check_v6,
                    )
                except Exception as e:
                    print(f"⚠️ [SSE] Risk score failed: {e}")
            yield _sse_event(
                "module", {"module": "risk_score_v6", "data": risk_score_v6}
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
                comments_analysis = _analyze_comments_v6(
                    req.comments[:50], summary_text, req.url, learning_ctx
                )
                # Track Gemini calls for ambiguous comments
                sent_to_ai = comments_analysis.get("filter_stats", {}).get(
                    "sent_to_ai", 0
                )
                if sent_to_ai > 0:
                    # Each batch of up to 25 = 1 Gemini call
                    batch_calls = max(1, (sent_to_ai + 24) // 25)
                    request_tracker.increment(batch_calls)
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
                "version": "6.0",
                "article_summary": article_summary,
                "sentiment_v6": sentiment_v6,
                "toxicity_v6": toxicity_v6,
                "fact_check_v6": fact_check_v6,
                "risk_score_v6": risk_score_v6,
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
                request_tracker.increment(1)  # Track Gemini call
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
# v6 Enhanced Analysis Endpoint
# ============================================================================


@app.post("/analyze/v6", response_model=dict)
def analyze_content_v6(req: ScanRequest):
    """
    v6 Enhanced full content scan endpoint.

    New features:
    - Unified structured analysis (70% fewer API calls)
    - Article summary (AI-generated, cached per URL)
    - Context-aware batch comment analysis (1 API call for N comments)
    - Smart comment filtering (skip obvious toxic/clean/spam)
    - API usage optimization (70-80% fewer Gemini calls)
    """
    print(f"📥 [v6] Received Scan Request for: {req.url}")
    try:
        # ========== LEARNING CONTEXT (v6.0) ==========
        learning_ctx = feedback_store.get_learning_context(req.url)
        if learning_ctx:
            print(f"🧠 [v6.0] Learning context loaded for {req.url}")

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
                    f"✅ [v6] Summary: {article_summary['method']} ({len(summary_text)} chars)"
                )
            except Exception as e:
                print(f"⚠️  [v6] Summary failed: {e}")

        # ========== 1. SENTIMENT ANALYSIS v6 (PhoBERT) ========== (PhoBERT) ==========
        sentiment_v6 = {
            "label": "Neutral",
            "confidence": 0.0,
            "intensity": "Weak",
            "method": "none",
        }

        if len(req.article_text) > 5:
            try:
                sentiment_v6 = sentiment_v6_engine.analyze(req.article_text[:512])
                print(
                    f"✅ [v6] Sentiment: {sentiment_v6['overall']} (confidence: {sentiment_v6['confidence']:.2f})"
                )
            except Exception as e:
                print(f"⚠️  [v6] Sentiment analysis failed: {e}")
                sentiment_v6 = {
                    "label": "Neutral",
                    "confidence": 0.0,
                    "intensity": "Weak",
                    "method": "error",
                }
        else:
            print(
                f"⚠️  [v6] Article too short for sentiment ({len(req.article_text)} chars)"
            )

        # ========== 2. Toxicity Detection v6 (4-layer, article body) ==========
        toxicity_v6 = {
            "is_toxic": False,
            "overall_score": 0.0,
            "severity": "Low",
            "categories": {},
            "detection_layers": [],
        }

        if len(req.article_text) > 5:
            try:
                toxicity_v6 = toxicity_v6_engine.analyze(req.article_text[:1000])
                print(
                    f"✅ [v6] Toxicity: {toxicity_v6['severity']} (score: {toxicity_v6['overall_score']:.2f})"
                )
            except Exception as e:
                print(f"⚠️  [v6] Toxicity detection failed: {e}")

        # ========== 3. FACT-CHECKING v6 (Multi-source) ========== (Multi-source) ==========
        fact_check_v6 = {
            "score": 50,
            "verdict": "Unverifiable",
            "confidence": "Low",
            "evidence": [],
            "verification_methods": [],
        }

        if len(req.article_text) > 20:
            try:
                fact_check_v6 = fact_checker_v6_engine.check(req.article_text, req.url)
                print(
                    f"✅ [v6] Fact Check: {fact_check_v6['verdict']} (credibility: {fact_check_v6['score']})"
                )
            except Exception as e:
                print(f"⚠️  [v6] Fact-checking failed: {e}")
                error_msg = str(e).lower()
                if "429" in str(e) or "quota" in error_msg:
                    fact_check_v6["verdict"] = "Quota Exceeded"
                else:
                    fact_check_v6["verdict"] = "Service Unavailable"

        # ========== 4. RISK SCORING v6 (Comprehensive) ========== (Comprehensive) ==========
        risk_score_v6 = {
            "risk_score": 0.0,
            "risk_level": "Low",
            "confidence": 0.0,
            "risk_breakdown": {},
            "warnings": [],
            "recommendations": [],
        }

        if len(req.article_text) > 20:
            try:
                risk_score_v6 = risk_scorer_v6_engine.score(req.article_text, req.url)
                print(
                    f"✅ [v6] Risk Score: {risk_score_v6['risk_score']:.1f}/100 ({risk_score_v6['risk_level']})"
                )
            except Exception as e:
                print(f"⚠️  [v6] Risk scoring failed: {e}")

        # ========== 5. COMMENTS ANALYSIS (v6 - Context-Aware Batch) ==========
        comments_analysis = {
            "total": 0,
            "toxic_count": 0,
            "toxic_percentage": 0.0,
            "toxic_comments": [],
            "filter_stats": {},
            "api_calls_saved": 0,
        }

        if req.comments:
            comments_analysis = _analyze_comments_v6(
                req.comments[:50], summary_text, req.url, learning_ctx
            )

        # ========== 6. BLOCKLIST CHECK (v6.0) ==========
        blocklist_info = {
            "is_blocked": community_blocklist.is_blocked(req.url),
            "report_count": community_blocklist.get_domain_report_count(req.url),
        }

        # ========== 7. DOMAIN FEEDBACK (v6.0) ==========
        domain_feedback = feedback_store.get_domain_feedback(req.url)

        # ========== 8. COMPILE v6.0 RESPONSE ==========
        response = {
            "version": "6.0",
            "article_summary": article_summary,
            "sentiment_v6": sentiment_v6,
            "toxicity_v6": toxicity_v6,
            "fact_check_v6": fact_check_v6,
            "risk_score_v6": risk_score_v6,
            "comments_analysis": comments_analysis,
            "url": req.url,
            "cache_stats": cache_manager.get_stats(),
            "blocklist_info": blocklist_info,
            "domain_feedback": domain_feedback,
            "learning_applied": bool(learning_ctx),
        }

        print(
            f"✅ [v6] Analysis complete. Risk: {risk_score_v6['risk_score']:.1f}/100, "
            f"Toxics: {comments_analysis['toxic_count']}, "
            f"API saved: {comments_analysis.get('api_calls_saved', 0)}"
        )
        return response

    except Exception as e:
        print(f"❌ [v6] Critical Error: {e}")
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"v6 analysis error: {str(e)}")


def _analyze_comments_v6(
    comments: List[str], article_summary: str, url: str, learning_ctx: str = ""
) -> dict:
    """
    Context-aware batch comment analysis (v6).

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

    print(f"📊 [v6] Comment filtering:")
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
                hasattr(toxicity_v6_engine, "regex_analyzer")
                and toxicity_v6_engine.regex_analyzer
            ):
                regex_result = toxicity_v6_engine._analyze_regex(comment)
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
            print(f"✅ [v6] Batch cache hit ({len(still_ambiguous)} comments)")
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
        print("⚠️ [v6] All API keys exhausted — using regex fallback for batch")
        return _fallback_results(comments)

    max_batch_attempts = min(3, available)  # Try up to 3 different keys
    for attempt in range(max_batch_attempts):
        api_key = batch_key_rotator.get_current_key()
        if not api_key:
            print("⚠️ [v6] No API key available for batch analysis")
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
                    f"⚠️ [v6] Batch attempt {attempt+1}/{max_batch_attempts} got 429, cooldown {retry_delay:.0f}s..."
                )
                batch_key_rotator.mark_key_rate_limited(retry_delay)
                continue
            else:
                print(f"⚠️ [v6] Batch analysis failed: {e}")
                return _fallback_results(comments)

    print("⚠️ [v6] All batch attempts exhausted — using regex fallback")
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

    # v6.0: Inject learning from user feedback
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
                    print(f"✅ [v6] Repaired truncated JSON ({len(parsed)} items)")
                except json.JSONDecodeError:
                    pass

        if parsed is None:
            # Try adding missing closing brackets to the whole response
            try:
                repaired = _repair_truncated_json(raw)
                parsed = json.loads(repaired)
                print(f"✅ [v6] Repaired raw JSON ({len(parsed)} items)")
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
                        f"✅ [v6] Extracted {len(parsed)} objects from malformed JSON"
                    )
                else:
                    print(f"⚠️ [v6] Could not parse Gemini response, using fallback")
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

    print(f"✅ [v6] Batch analyzed {len(comments)} comments (1 API call)")
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
        # Use v2 regex engine DIRECTLY — do NOT call toxicity_v6_engine.analyze()
        # because that triggers Perspective API + Gemini calls per comment = API storm
        is_toxic = False
        score = 0.0
        severity = "None"
        try:
            if (
                hasattr(toxicity_v6_engine, "regex_analyzer")
                and toxicity_v6_engine.regex_analyzer
            ):
                regex_result = toxicity_v6_engine._analyze_regex(c)
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
# ARCH-01: Unified Single-Pass Analysis Endpoint (v6)
# ============================================================================


@app.post("/analyze/v6/unified", response_model=dict)
def analyze_unified_v6(req: StructuredScanRequest):
    """
    ARCH-01 — Unified structured analysis endpoint.

    Accepts fully structured page data from structuredScrape() and runs:
    1. Parallel pre-processing (regex, keywords, source check) — 0 Gemini calls
    2. Smart comment filtering — skip obvious toxic/clean/spam
    3. Single unified Gemini call — summary + sentiment + fact check + comments + risk
    4. Fallback to sequential pipeline if unified call fails

    Result: 70-80% fewer API calls, 5-15s latency vs 15-60s.
    """
    url = req.url
    article_body = req.article.body or ""
    article_title = req.article.title or ""
    full_article_text = f"{article_title}\n{article_body}".strip()

    print(f"📥 [unified] Received structured scan for: {url} ({req.page_type})")
    print(f"   Article: {len(article_body)} chars, Comments: {len(req.comments)}")

    try:
        request_tracker.increment()

        # ─────────────────────────────────────────
        # STEP 1: PARALLEL PRE-PROCESSING (0 Gemini calls)
        # ─────────────────────────────────────────
        print("⚙️ [unified] Running parallel pre-processing...")
        t0 = time.time()

        # 1a. Regex toxicity on article body
        regex_toxicity = {
            "is_toxic": False,
            "overall_score": 0.0,
            "severity": "Low",
            "categories": {},
            "matched_patterns": [],
        }
        if len(article_body) > 5:
            try:
                regex_toxicity = toxicity_v6_engine.analyze(article_body[:1000])
            except Exception as e:
                print(f"⚠️ [unified] Regex toxicity failed: {e}")

        # 1b. Keyword sentiment on article
        keyword_sentiment = {
            "overall": "Neutral",
            "confidence": 0.0,
            "intensity": "Weak",
        }
        if len(article_body) > 5:
            try:
                keyword_sentiment = sentiment_v6_engine.analyze(article_body[:512])
            except Exception as e:
                print(f"⚠️ [unified] Keyword sentiment failed: {e}")

        # 1c. Source credibility from fact_checker's source_analyzer
        source_credibility = {"reputation_score": 50, "verdict": "Chưa biết"}
        try:
            if fact_checker_v6_engine.source_analyzer and url:
                sc = fact_checker_v6_engine.source_analyzer.analyze(url)
                if sc:
                    source_credibility = sc
        except Exception as e:
            print(f"⚠️ [unified] Source credibility check failed: {e}")

        # 1d. Google Fact Check API (via fact_checker)
        factcheck_api_results = []
        try:
            if len(full_article_text) > 20 and hasattr(
                fact_checker_v6_engine, "_check_google_factcheck"
            ):
                factcheck_api_results = (
                    fact_checker_v6_engine._check_google_factcheck(
                        full_article_text[:500]
                    )
                    or []
                )
        except Exception as e:
            print(f"⚠️ [unified] GoogleFactCheck API failed: {e}")

        # 1e. NewsData (cross-reference)
        newsdata_results = []
        try:
            if len(full_article_text) > 20 and hasattr(
                fact_checker_v6_engine, "_check_newsdata"
            ):
                newsdata_results = (
                    fact_checker_v6_engine._check_newsdata(full_article_text[:200])
                    or []
                )
        except Exception as e:
            print(f"⚠️ [unified] NewsData failed: {e}")

        precomputed = {
            "regex_toxicity": regex_toxicity,
            "keyword_sentiment": keyword_sentiment,
            "source_credibility": source_credibility,
            "factcheck_api_results": factcheck_api_results,
            "newsdata_results": newsdata_results,
        }

        print(f"   Pre-processing: {time.time()-t0:.1f}s")

        # ─────────────────────────────────────────
        # STEP 2: SMART COMMENT FILTERING
        # ─────────────────────────────────────────
        # Build text→struct map for metadata lookup after filtering
        text_to_struct = {}
        raw_comment_texts = []
        for sc in req.comments:
            text_to_struct[sc.text] = sc
            raw_comment_texts.append(sc.text)

        filter_result = comment_filter.filter_comments(raw_comment_texts)

        # Build ambiguous list with metadata from structured comments
        ambiguous_comments = []
        for text in filter_result.get("ambiguous", []):
            sc = text_to_struct.get(text)
            ambiguous_comments.append(
                {
                    "index": len(ambiguous_comments) + 1,
                    "text": text,
                    "author": sc.author if sc else "",
                    "reactions": sc.reactions if sc else 0,
                    "is_reply": sc.is_reply if sc else False,
                }
            )

        obvious_toxic_texts = filter_result.get("obvious_toxic", [])
        obvious_clean_texts = filter_result.get("obvious_clean", [])
        spam = filter_result.get("spam", [])

        print(
            f"   Comments: {len(req.comments)} total → "
            f"{len(obvious_toxic_texts)} obvious_toxic, {len(obvious_clean_texts)} clean, "
            f"{len(spam)} spam, {len(ambiguous_comments)} ambiguous"
        )

        # ─────────────────────────────────────────
        # STEP 3: SINGLE UNIFIED GEMINI CALL
        # ─────────────────────────────────────────
        print("🤖 [unified] Starting single-pass Gemini call...")
        t1 = time.time()

        # Convert StructuredScanRequest to plain dict for unified_analyzer
        structured_dict = {
            "page_type": req.page_type,
            "url": req.url,
            "article": {
                "title": req.article.title,
                "author": req.article.author,
                "published_date": req.article.published_date,
                "body": req.article.body,
                "word_count": req.article.word_count or len(article_body.split()),
            },
            "metadata": {
                "domain": req.metadata.domain
                or (url.split("/")[2] if "//" in url else url),
                "reactions_total": req.metadata.reactions_total,
                "shares": req.metadata.shares,
                "comment_count_visible": req.metadata.comment_count_visible
                or len(req.comments),
            },
        }

        ai_result = unified_analyzer.analyze(
            structured_dict, precomputed, ambiguous_comments
        )
        print(f"   Unified Gemini: {time.time()-t1:.1f}s")
        was_fallback = ai_result.get("_fallback", False)

        # ─────────────────────────────────────────
        # STEP 4: COMBINE ALL RESULTS
        # ─────────────────────────────────────────
        # Merge obvious toxic/clean with AI-analyzed comments
        all_comment_results = []

        # Obvious toxic (pre-classified, no AI needed)
        for text in obvious_toxic_texts:
            sc = text_to_struct.get(text)
            all_comment_results.append(
                {
                    "comment": text[:200],
                    "is_toxic": True,
                    "severity": "High",
                    "score": 0.9,
                    "sentiment": "negative",
                    "method": "regex_filter",
                    "reason": "Xác định là độc hại (regex)",
                    "categories": {},
                    "reactions": sc.reactions if sc else 0,
                    "author": sc.author if sc else "",
                }
            )

        # AI-analyzed ambiguous comments
        ai_comment_map = {c["index"]: c for c in ai_result.get("comments", [])}
        for ac in ambiguous_comments:
            ai_data = ai_comment_map.get(ac["index"], {})
            all_comment_results.append(
                {
                    "comment": ac["text"][:200],
                    "is_toxic": ai_data.get("is_toxic", False),
                    "severity": ai_data.get("severity", "None"),
                    "score": 0.8 if ai_data.get("is_toxic") else 0.1,
                    "sentiment": ai_data.get("sentiment", "neutral"),
                    "method": "unified_ai" if not was_fallback else "fallback",
                    "reason": ai_data.get("reason", ""),
                    "categories": {cat: 0.8 for cat in ai_data.get("categories", [])},
                    "reactions": ac.get("reactions", 0),
                    "author": ac.get("author", ""),
                    "evidence_spans": ai_data.get("evidence_spans", []),  # Feature 6.3
                }
            )

        # Build comments_analysis (matches /analyze/v6 format)
        toxic_comments = [c for c in all_comment_results if c["is_toxic"]]
        total_analyzed = len(req.comments)
        toxic_pct = (
            (len(toxic_comments) / total_analyzed * 100) if total_analyzed > 0 else 0.0
        )

        comments_analysis = {
            "total": total_analyzed,
            "toxic_count": len(toxic_comments),
            "toxic_percentage": round(toxic_pct, 1),
            "toxic_comments": toxic_comments,
            "all_results": all_comment_results,
            "filter_stats": {
                "obvious_toxic": len(obvious_toxic_texts),
                "obvious_clean": len(obvious_clean_texts),
                "spam": len(spam),
                "ai_analyzed": len(ambiguous_comments),
            },
            "api_calls_saved": max(0, len(req.comments) // 25 - 1),
        }

        # Format AI results to match /analyze/v6 response shape
        ai_sentiment = ai_result.get("sentiment", {})
        ai_fact_check = ai_result.get("fact_check", {})
        ai_article_tox = ai_result.get("article_toxicity", {})
        ai_risk = ai_result.get("risk_assessment", {})
        ai_summary = ai_result.get("summary", "")

        # Build sentiment_v6 compatible dict
        sentiment_v6_result = {
            "overall": ai_sentiment.get(
                "overall", keyword_sentiment.get("overall", "Neutral")
            ),
            "confidence": ai_sentiment.get(
                "confidence", keyword_sentiment.get("confidence", 0.0)
            ),
            "intensity": ai_sentiment.get("intensity", "Weak"),
            "method": "unified_ai" if not was_fallback else "keyword_fallback",
            "reasoning": ai_sentiment.get("reasoning", ""),
            "label": ai_sentiment.get("overall", "Neutral"),
        }

        # Build toxicity_v6 compatible dict
        toxicity_v6_result = {
            "is_toxic": ai_article_tox.get(
                "is_toxic", regex_toxicity.get("is_toxic", False)
            ),
            "overall_score": ai_article_tox.get(
                "score", regex_toxicity.get("overall_score", 0.0)
            ),
            "severity": ai_article_tox.get(
                "severity", regex_toxicity.get("severity", "Low")
            ),
            "categories": {cat: 0.8 for cat in ai_article_tox.get("categories", [])},
            "detection_layers": (
                ["regex", "unified_ai"] if not was_fallback else ["regex"]
            ),
            "reasoning": ai_article_tox.get("reasoning", ""),
        }

        # Build fact_check_v6 compatible dict
        fact_check_v6_result = {
            "score": ai_fact_check.get(
                "score", source_credibility.get("reputation_score", 50)
            ),
            "verdict": ai_fact_check.get(
                "verdict", source_credibility.get("verdict", "Unverifiable")
            ),
            "confidence": ai_fact_check.get("confidence", "Low"),
            "evidence": ai_fact_check.get("evidence", []),
            "key_claims": ai_fact_check.get("key_claims", []),
            "verification_methods": (
                ["unified_ai", "source_credibility"]
                if not was_fallback
                else ["source_credibility"]
            ),
        }

        # Build risk_score_v6 compatible dict
        risk_score_v6_result = {
            "risk_score": float(ai_risk.get("score", 0)),
            "risk_level": ai_risk.get("level", "Low"),
            "confidence": 0.8 if not was_fallback else 0.4,
            "risk_breakdown": {},
            "warnings": ai_risk.get("warnings", []),
            "recommendations": ai_risk.get("recommendations", []),
            "key_factors": ai_risk.get("key_factors", []),
        }

        article_summary = {
            "summary": ai_summary,
            "method": "unified_ai" if not was_fallback else "none",
            "cached": False,
        }

        # Blocklist + feedback
        blocklist_info = {
            "is_blocked": community_blocklist.is_blocked(url),
            "report_count": community_blocklist.get_domain_report_count(url),
        }
        domain_feedback = feedback_store.get_domain_feedback(url)

        # Feature 6.12 — extract scam_detection from unified AI result
        scam_detection = ai_result.get(
            "scam_detection",
            {
                "is_scam": False,
                "confidence": 0.0,
                "scam_type": "none",
                "evidence_phrases": [],
                "reasoning": "",
            },
        )

        total_time = time.time() - t0
        response = {
            "version": "6.0",
            "analysis_mode": "unified",
            "was_fallback": was_fallback,
            "processing_time_s": round(total_time, 2),
            "article_summary": article_summary,
            "sentiment_v6": sentiment_v6_result,
            "toxicity_v6": toxicity_v6_result,
            "fact_check_v6": fact_check_v6_result,
            "risk_score_v6": risk_score_v6_result,
            "comments_analysis": comments_analysis,
            "scam_detection": scam_detection,
            "url": url,
            "page_type": req.page_type,
            "page_metadata": {
                "author": req.article.author,
                "published_date": req.article.published_date,
                "word_count": req.article.word_count or len(article_body.split()),
                "reactions_total": req.metadata.reactions_total,
                "shares": req.metadata.shares,
                "domain": req.metadata.domain,
            },
            "cache_stats": cache_manager.get_stats(),
            "blocklist_info": blocklist_info,
            "domain_feedback": domain_feedback,
        }

        # ─────────────────────────────────────────
        # STEP 5: APPLY RE-RANKER (Feature 6.9)
        # ─────────────────────────────────────────
        domain_for_reranker = req.metadata.domain or (
            url.split("/")[2] if "//" in url else url
        )
        # Flatten risk score to top-level for reranker compatibility
        response["risk_score"] = risk_score_v6_result.get("risk_score", 0)
        response = reranker.apply(domain_for_reranker, response)
        # Re-sync nested risk_score_v6 with adjusted top-level risk
        if response.get("reranker_applied"):
            risk_score_v6_result["risk_score"] = response["risk_score"]
            risk_score_v6_result["reranker_adjustments"] = response.get(
                "reranker_adjustments", {}
            )
            response["risk_score_v6"] = risk_score_v6_result

        print(
            f"✅ [unified] Done in {total_time:.1f}s | Risk: {response['risk_score']}/100 | "
            f"Toxics: {len(toxic_comments)} | Mode: {'fallback' if was_fallback else 'unified_ai'}"
            + (" | Reranker applied" if response.get("reranker_applied") else "")
        )
        return response

    except Exception as e:
        print(f"❌ [unified] Critical Error: {e}")
        import traceback

        traceback.print_exc()
        raise HTTPException(
            status_code=500, detail=f"v6 unified analysis error: {str(e)}"
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
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
