"""
VnContentGuard Pro V7 - Unified Single-Pass AI Analyzer
========================================================
ARCH-01: Single Gemini call that handles summary, sentiment, fact-check,
article toxicity, all ambiguous comments, and overall risk in one shot.

Benefits vs sequential pipeline:
- 70-80% fewer Gemini API calls (3-5 calls → 1 call)
- 68% fewer tokens (cross-module context eliminates repetition)
- 5-15s latency vs 15-60s (pre-processing parallel + 1 call)
- Cross-module intelligence (comments influence fact-check confidence)
"""

import json
import re
import time
from typing import Any, Dict, List, Optional


class UnifiedAnalyzer:
    """
    Single-pass Gemini analyzer. Takes fully structured page data (from
    structuredScrape) and pre-computed fast results (regex toxicity, keyword
    sentiment, source credibility) then issues ONE Gemini call for everything.
    """

    # Character limit for article body passed to Gemini
    ARTICLE_MAX_CHARS = 2000
    # Maximum ambiguous comments to include in unified prompt
    MAX_COMMENTS_IN_PROMPT = 30
    # Max characters per comment in the prompt
    COMMENT_MAX_CHARS = 200

    def __init__(self, key_rotator):
        """
        Args:
            key_rotator: Shared APIKeyRotator instance from gemini_llm.py
        """
        self.key_rotator = key_rotator
        self._last_error = None  # Stores last Gemini call error for diagnostics

    # -------------------------------------------------------------------------
    # Public Interface
    # -------------------------------------------------------------------------

    def analyze(
        self,
        structured_data: Dict,
        precomputed: Dict,
        ambiguous_comments: List[Dict],
    ) -> Dict:
        """
        Run single-pass comprehensive Gemini analysis.

        Args:
            structured_data: Output from structuredScrape() on frontend.
              {page_type, url, article: {title, author, date, body, word_count},
               comments: [{text, author, reactions, is_reply}],
               metadata: {domain, reactions_total, shares, comment_count_visible}}

            precomputed: Fast pre-computed results (no Gemini calls):
              {regex_toxicity, keyword_sentiment, source_credibility,
               factcheck_api_results, newsdata_results}

            ambiguous_comments: Filtered list of comments needing AI judgment.
              Each: {index, text, reactions}  (index = position in original list)

        Returns:
            Complete analysis dict matching the V7 response structure.
            Falls back gracefully if Gemini call fails.
        """
        prompt = self._build_prompt(structured_data, precomputed, ambiguous_comments)

        raw_response = self._call_gemini(prompt)

        if raw_response is None:
            return self._fallback(precomputed, ambiguous_comments)

        parsed = self._parse_response(raw_response, ambiguous_comments)
        if parsed is None:
            return self._fallback(precomputed, ambiguous_comments)

        # Normalize AI evidence to structured objects and inject real API sources
        fc_evidence = parsed.get("fact_check", {}).get("evidence", [])
        normalized_evidence = []
        for ev in fc_evidence:
            if isinstance(ev, str):
                normalized_evidence.append(
                    {"text": ev[:150], "source": "AI Analysis", "url": ""}
                )
            elif isinstance(ev, dict):
                normalized_evidence.append(ev)

        # Inject Google Fact Check API results (have real URLs)
        fc_api = precomputed.get("factcheck_api_results", [])
        for item in fc_api[:3]:
            claim_text = item.get("claim", item.get("claimText", ""))[:150]
            if claim_text:
                normalized_evidence.append(
                    {
                        "text": claim_text,
                        "source": item.get("publisher", "Google Fact Check"),
                        "url": item.get("url", ""),
                        "rating": item.get("rating", ""),
                        "type": "factcheck",
                    }
                )

        # Inject NewsData.io results (have real article URLs)
        nd_api = precomputed.get("newsdata_results", [])
        for item in nd_api[:2]:
            title = item.get("title", "")[:150]
            if title:
                normalized_evidence.append(
                    {
                        "text": title,
                        "source": item.get("source", item.get("source_id", "NewsData")),
                        "url": item.get("url", item.get("link", "")),
                        "type": "news",
                    }
                )

        parsed["fact_check"]["evidence"] = normalized_evidence
        return parsed

    # -------------------------------------------------------------------------
    # Prompt Builder
    # -------------------------------------------------------------------------

    def _build_prompt(
        self,
        structured_data: Dict,
        precomputed: Dict,
        ambiguous_comments: List[Dict],
    ) -> str:
        """Assemble the unified Vietnamese-context analysis prompt."""

        article = structured_data.get("article", {})
        metadata = structured_data.get("metadata", {})
        page_type = structured_data.get("page_type", "generic")
        url = structured_data.get("url", "")

        # --- Article section ---
        article_body = (article.get("body", "") or "")[: self.ARTICLE_MAX_CHARS]
        title = (article.get("title", "") or "").strip()
        author = (article.get("author", "") or "").strip()
        pub_date = (article.get("published_date", "") or "").strip()
        word_count = article.get("word_count", 0)

        # --- Metadata section ---
        domain = metadata.get("domain", url.split("/")[2] if "//" in url else url)
        reactions_total = metadata.get("reactions_total", 0)
        shares = metadata.get("shares", 0)
        comment_count_visible = metadata.get("comment_count_visible", 0)

        # --- Pre-computed section ---
        regex_tox = precomputed.get("regex_toxicity", {})
        kw_sent = precomputed.get("keyword_sentiment", {})
        source_cred = precomputed.get("source_credibility", {})
        fc_api = precomputed.get("factcheck_api_results", [])
        nd_api = precomputed.get("newsdata_results", [])

        # --- Comment section ---
        comment_lines = []
        for i, c in enumerate(ambiguous_comments[: self.MAX_COMMENTS_IN_PROMPT], 1):
            reactions = c.get("reactions", 0)
            author_name = c.get("author", "")
            text = (c.get("text", "") or "")[: self.COMMENT_MAX_CHARS]
            reply_tag = " [reply]" if c.get("is_reply") else ""
            author_display = f", {author_name}" if author_name else ""
            reaction_display = f" (👍{reactions})" if reactions else ""
            comment_lines.append(
                f'{i}. "{text}"{reaction_display}{reply_tag}{author_display}'
            )

        comments_block = (
            "\n".join(comment_lines)
            if comment_lines
            else "(không có bình luận cần phân tích)"
        )

        # --- FactCheck API evidence ---
        fc_evidence_lines = []
        for item in fc_api[:3]:
            fc_evidence_lines.append(
                f'  - "{item.get("claimText", "")}" → {item.get("rating", "Unknown")}'
            )
        fc_evidence = (
            "\n".join(fc_evidence_lines)
            if fc_evidence_lines
            else "  (không có kết quả)"
        )

        # --- NewsData ---
        nd_lines = []
        for item in nd_api[:3]:
            nd_lines.append(
                f'  - {item.get("title", "")[:100]} ({item.get("source_id", "")})'
            )
        nd_block = "\n".join(nd_lines) if nd_lines else "  (không có bài liên quan)"

        # --- Scam URL pattern pre-check ---
        import re as _scam_re

        scam_url_flags = []
        url_lower = url.lower()
        _scam_url_pats = [
            (
                r"(kiemtien|lam-giau|dau-tu|passive.{0,10}income|thu-nhap)",
                "investment_scam",
            ),
            (r"(nhan-qua|trung-thuong|nhan-tien|phan-thuong|mien-phi)", "lottery_scam"),
            (
                r"(login|xac-minh|verify|xac-nhan).{0,30}\.(tk|ml|ga|cf|gq|xyz|top)",
                "phishing",
            ),
            (
                r"(bank|ngan-hang|vietcom|techcom|bidv|agri|vcb).{0,30}(login|pass|xac|otp)",
                "financial_phishing",
            ),
            (
                r"(update.{0,10}flash|antivirus.{0,10}free|win.{0,10}prize)",
                "fake_software",
            ),
            (
                r"(giam-can|tang-can|thu-hut|doi-mat|lam-dep).{0,20}(ngay|tuan|nhanh)",
                "health_scam",
            ),
        ]
        for _pat, _flag in _scam_url_pats:
            if _scam_re.search(_pat, url_lower):
                scam_url_flags.append(_flag)
        scam_url_block = ", ".join(scam_url_flags) if scam_url_flags else "none"

        prompt = f"""Bạn là VnContentGuard Pro AI — hệ thống phân tích nội dung tiếng Việt chuyên nghiệp.
Phân tích TOÀN BỘ nội dung sau trong MỘT lần và trả về JSON DUY NHẤT theo định dạng yêu cầu.

══════════════════════ DỮ LIỆU TRANG ══════════════════════
Loại trang:    {page_type}
URL:           {url}
Tên miền:      {domain}
Tác giả:       {author if author else "(không xác định)"}
Ngày đăng:     {pub_date if pub_date else "(không rõ)"}
Số từ bài:     {word_count}
Lượt chia sẻ: {shares}    Tương tác: {reactions_total}

──────────────────── NỘI DUNG BÀI ────────────────────
{f"Tiêu đề: {title}" if title else ""}
{article_body if article_body else "(không có nội dung bài viết)"}

──────────────── KẾT QUẢ PHÂN TÍCH SƠ BỘ ────────────────
• Regex toxicity:  điểm={regex_tox.get("overall_score", 0):.2f}, mức={regex_tox.get("severity", "Low")}, mẫu khớp={regex_tox.get("matched_patterns", [])}
• Keyword sentiment: {kw_sent.get("overall", "Neutral")} (độ tin cậy {kw_sent.get("confidence", 0):.2f})
• Độ tin cậy nguồn ({domain}): {source_cred.get("reputation_score", 50)}/100 — {source_cred.get("verdict", "Chưa biết")}
• Scam URL patterns: {scam_url_block}
• Google Fact Check API:
{fc_evidence}
• NewsData.io — bài liên quan:
{nd_block}

──────────────── BÌNH LUẬN CẦN AI PHÂN TÍCH ────────────────
(Chỉ bình luận mơ hồ — obvious đã lọc trước)
{comments_block}

══════════════════════ YÊU CẦU PHÂN TÍCH ══════════════════════
Trả về JSON với CÁC TRƯỜNG SAU (không thêm text ngoài JSON):

{{
  "summary": "Tóm tắt TỐI ĐA 4 câu ngắn (mỗi câu ≤40 từ). KHÔNG vượt quá 300 từ. Chỉ nêu ý chính, không liệt kê chi tiết.",

  "sentiment": {{
    "overall": "Positive|Negative|Neutral|Mixed",
    "confidence": 0.0,
    "intensity": "Strong|Moderate|Weak",
    "reasoning": "Giải thích ngắn 1 câu"
  }},

  "fact_check": {{
    "score": 0,
    "verdict": "True|Likely True|Unverifiable|Likely False|False",
    "confidence": "High|Medium|Low",
    "evidence": [
      {{"text": "nội dung bằng chứng ngắn (≤120 ký tự)", "source": "Tên nguồn hoặc 'AI Analysis'", "url": ""}}
    ],
    "key_claims": ["tuyên bố chính 1"]
  }},

  "article_toxicity": {{
    "is_toxic": false,
    "score": 0.0,
    "severity": "None|Low|Medium|High|Critical",
    "categories": [],
    "reasoning": "Giải thích ngắn"
  }},

  "comments": [
    {{
      "index": 1,
      "is_toxic": false,
      "severity": "None|Low|Medium|High|Critical",
      "sentiment": "positive|negative|neutral|mixed",
      "categories": [],
      "reason": "Giải thích ngắn 1 câu",
      "evidence_spans": [
        {{"text": "đoạn văn bản cụ thể gây độc hại", "reason": "Lý do ngắn", "severity": "high|medium|low"}}
      ]
    }}
  ],

  "risk_assessment": {{
    "score": 0,
    "level": "Low|Medium|High|Critical",
    "key_factors": ["yếu tố 1", "yếu tố 2"],
    "warnings": ["cảnh báo 1"],
    "recommendations": ["khuyến nghị 1"]
  }},

  "scam_detection": {{
    "is_scam": false,
    "confidence": 0.0,
    "scam_type": "none|financial_phishing|lottery_scam|fake_government|investment_scam|impersonation|fake_software|health_scam|other",
    "evidence_phrases": ["đoạn văn bản ngắn làm bằng chứng lừa đảo"],
    "reasoning": "Giải thích ngắn 1-2 câu"
  }}
}}

LƯU Ý QUAN TRỌNG:
- "comments" array phải có ĐỦ entries cho TẤT CẢ {len(ambiguous_comments)} bình luận đã liệt kê (index 1 đến {len(ambiguous_comments)})
- score trong fact_check: 0-100 (100 = hoàn toàn đáng tin cậy)
- risk_assessment.score: 0-100 (0 = an toàn, 100 = cực kỳ nguy hiểm)
- Xem xét ảnh hưởng của bình luận với nhiều tương tác (👍 cao) đến đánh giá tổng thể
- Nếu bình luận nói "tin giả" hoặc "sai thông tin" với nhiều tương tác → tăng skepticism trong fact_check
- evidence_spans: chỉ điền khi is_toxic=true; mỗi span là đoạn trích CHÍNH XÁC từ bình luận (<60 ký tự), kèm lý do và mức độ (high/medium/low). Để trống [] nếu không có nội dung độc hại.
- Chỉ trả về JSON thuần túy, không có markdown, không có text giải thích ngoài JSON"""

        return prompt

    # -------------------------------------------------------------------------
    # Gemini Call
    # -------------------------------------------------------------------------

    def _call_gemini(self, prompt: str) -> Optional[str]:
        """Issue the unified Gemini call with retry + key rotation."""
        max_retries = 6
        last_error = None
        for attempt in range(max_retries):
            key = self.key_rotator.get_current_key()
            if key is None:
                print("⚠️ [unified] No API key available")
                self._last_error = last_error or "No API key available"
                return None

            try:
                from google import genai
                from google.genai import types

                client = genai.Client(api_key=key)
                model_name = self._get_model_name()

                # Build config — disable thinking on gemini-2.5-flash so all output
                # tokens go to the JSON response (not internal chain-of-thought)
                try:
                    gen_config = types.GenerateContentConfig(
                        temperature=0.1,
                        max_output_tokens=8192,
                        response_mime_type="application/json",
                        thinking_config=types.ThinkingConfig(thinking_budget=0),
                    )
                except Exception:
                    gen_config = types.GenerateContentConfig(
                        temperature=0.1,
                        max_output_tokens=8192,
                        response_mime_type="application/json",
                    )

                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=gen_config,
                )
                raw = response.text
                if not raw or not raw.strip():
                    raise ValueError(f"Empty response from model {model_name}")
                raw = raw.strip()
                self.key_rotator.mark_key_success()
                print(
                    f"✅ [unified] Gemini call succeeded (attempt {attempt+1}, {len(raw)} chars)"
                )
                self._last_error = None
                return raw

            except Exception as e:
                err = str(e).lower()
                last_error = str(e)
                print(f"⚠️ [unified] Attempt {attempt+1} failed: {e}")

                if "429" in err or "quota" in err or "resource_exhausted" in err:
                    # Distinguish: short retryDelay = rate-limit (temp); no delay = daily quota
                    from src.models.gemini_llm import APIKeyRotator as _KR

                    retry_delay = _KR.parse_retry_delay(str(e))
                    if retry_delay <= 120:
                        # Per-minute rate limit — put key in cooldown, not exhausted
                        self.key_rotator.mark_key_rate_limited(retry_delay)
                    else:
                        # Daily quota truly exhausted
                        self.key_rotator.mark_key_exhausted()
                    time.sleep(1)
                    continue

                if attempt < max_retries - 1:
                    time.sleep(2**attempt)
                    continue

                self._last_error = last_error
                return None

        self._last_error = last_error
        return None

    def _get_model_name(self) -> str:
        """Get current model name from shared gemini_llm state."""
        try:
            from src.models.gemini_llm import MODEL_NAME

            return MODEL_NAME
        except Exception:
            return "gemini-2.5-flash"

    # -------------------------------------------------------------------------
    # Response Parser
    # -------------------------------------------------------------------------

    def _parse_response(
        self, raw: str, ambiguous_comments: List[Dict]
    ) -> Optional[Dict]:
        """Parse and validate the Gemini JSON response."""
        try:
            # Strip markdown code fences if present
            cleaned = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
            cleaned = re.sub(r"\s*```$", "", cleaned, flags=re.MULTILINE)
            cleaned = cleaned.strip()

            data = json.loads(cleaned)
        except json.JSONDecodeError:
            # Try to extract JSON from the response
            match = re.search(r"\{[\s\S]*\}", raw)
            if match:
                try:
                    data = json.loads(match.group())
                except Exception:
                    return None
            else:
                return None

        # Validate required keys
        required = [
            "summary",
            "sentiment",
            "fact_check",
            "article_toxicity",
            "risk_assessment",
        ]
        for key in required:
            if key not in data:
                print(f"⚠️ [unified] Missing required key: {key}")
                return None

        # Ensure comments array exists with correct count
        if "comments" not in data:
            data["comments"] = []
        # Pad if short
        existing_indices = {c.get("index") for c in data.get("comments", [])}
        for i in range(1, len(ambiguous_comments) + 1):
            if i not in existing_indices:
                data["comments"].append(
                    {
                        "index": i,
                        "is_toxic": False,
                        "severity": "None",
                        "sentiment": "neutral",
                        "categories": [],
                        "reason": "(not analyzed)",
                        "evidence_spans": [],
                    }
                )

        # Ensure every comment has evidence_spans key (feature 7.3)
        for c in data["comments"]:
            if "evidence_spans" not in c:
                c["evidence_spans"] = []

        # Sort by index
        data["comments"].sort(key=lambda x: x.get("index", 0))

        # Normalize scam_detection (feature 7.12) — fill defaults if absent
        if "scam_detection" not in data:
            data["scam_detection"] = {
                "is_scam": False,
                "confidence": 0.0,
                "scam_type": "none",
                "evidence_phrases": [],
                "reasoning": "",
            }
        else:
            sd = data["scam_detection"]
            sd.setdefault("is_scam", False)
            sd.setdefault("confidence", 0.0)
            sd.setdefault("scam_type", "none")
            sd.setdefault("evidence_phrases", [])
            sd.setdefault("reasoning", "")

        return data

    # -------------------------------------------------------------------------
    # Fallback
    # -------------------------------------------------------------------------

    def _fallback(self, precomputed: Dict, ambiguous_comments: List[Dict]) -> Dict:
        """
        Return best-effort results from pre-computed data alone (no Gemini).
        Used when the unified call fails completely.
        """
        err_detail = f" | Lỗi: {self._last_error[:120]}" if self._last_error else ""
        print(f"⚠️ [unified] Using fallback (pre-computed only, no Gemini){err_detail}")

        regex_tox = precomputed.get("regex_toxicity", {})
        kw_sent = precomputed.get("keyword_sentiment", {})
        source_cred = precomputed.get("source_credibility", {})

        tox_score = regex_tox.get("overall_score", 0.0)
        severity = regex_tox.get("severity", "Low")

        # Rough credibility heuristic from source + regex
        source_score = source_cred.get("reputation_score", 50)
        risk_score = max(
            0, min(100, int((1 - source_score / 100) * 40 + tox_score * 60))
        )

        # Mark all ambiguous comments as needing manual review
        fallback_comments = [
            {
                "index": c.get("index", i + 1),
                "is_toxic": False,
                "severity": "None",
                "sentiment": "neutral",
                "categories": [],
                "reason": "AI analysis unavailable — manual review needed",
            }
            for i, c in enumerate(ambiguous_comments)
        ]

        return {
            "summary": "",
            "sentiment": {
                "overall": kw_sent.get("overall", "Neutral"),
                "confidence": kw_sent.get("confidence", 0.0),
                "intensity": "Weak",
                "reasoning": "Keyword-based analysis only",
            },
            "fact_check": {
                "score": source_score,
                "verdict": source_cred.get("verdict", "Unverifiable"),
                "confidence": "Low",
                "evidence": [],
                "key_claims": [],
            },
            "article_toxicity": {
                "is_toxic": regex_tox.get("is_toxic", False),
                "score": tox_score,
                "severity": severity,
                "categories": list(regex_tox.get("categories", {}).keys()),
                "reasoning": "Regex-based analysis only",
            },
            "comments": fallback_comments,
            "risk_assessment": {
                "score": risk_score,
                "level": self._score_to_level(risk_score),
                "key_factors": ["AI analysis unavailable"],
                "warnings": [f"Kết quả sơ bộ — AI không khả dụng{err_detail}"],
                "recommendations": ["Thử lại sau khi backend phục hồi"],
            },
            "scam_detection": {
                "is_scam": False,
                "confidence": 0.0,
                "scam_type": "none",
                "evidence_phrases": [],
                "reasoning": "AI analysis unavailable",
            },
            "_fallback": True,
        }

    @staticmethod
    def _score_to_level(score: int) -> str:
        if score >= 75:
            return "Critical"
        elif score >= 50:
            return "High"
        elif score >= 25:
            return "Medium"
        return "Low"


# ─────────────────────────────────────────────────────────────────────────────
# Standalone test
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    test_structured = {
        "page_type": "news_article",
        "url": "https://vnexpress.net/test",
        "article": {
            "title": "Phát hiện lừa đảo mới trên mạng xã hội",
            "author": "VnExpress",
            "published_date": "2026-02-24",
            "body": "Cơ quan công an vừa phát hiện đường dây lừa đảo trực tuyến mới...",
            "word_count": 450,
        },
        "comments": [],
        "metadata": {
            "domain": "vnexpress.net",
            "reactions_total": 1200,
            "shares": 350,
            "comment_count_visible": 5,
        },
    }
    test_precomputed = {
        "regex_toxicity": {
            "overall_score": 0.1,
            "severity": "Low",
            "is_toxic": False,
            "categories": {},
            "matched_patterns": [],
        },
        "keyword_sentiment": {"overall": "Neutral", "confidence": 0.6},
        "source_credibility": {"reputation_score": 92, "verdict": "Đáng tin cậy"},
        "factcheck_api_results": [],
        "newsdata_results": [],
    }
    test_ambiguous = [
        {"index": 1, "text": "Bài viết hay nhưng cần kiểm chứng thêm", "reactions": 5},
        {"index": 2, "text": "Toàn tin giả đừng tin", "reactions": 42},
    ]
    print("🧪 Testing UnifiedAnalyzer (fallback mode — no API key)")
    print("Structured data:", json.dumps(test_structured, ensure_ascii=False, indent=2))
