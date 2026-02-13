"""
VnContentGuard Pro v4.9 — User Feedback Store with Learning
=============================================================
Stores user feedback (thumbs up/down + optional corrections)
in a local JSON file. Provides learning context to improve
future scans based on accumulated user corrections.
"""

import json
import os
import threading
from datetime import datetime
from urllib.parse import urlparse

FEEDBACK_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "feedback_data.json"
)
MAX_ENTRIES = 5000


class FeedbackStore:
    """Thread-safe JSON-based feedback storage with learning capabilities."""

    def __init__(self, filepath=None):
        self.filepath = filepath or FEEDBACK_FILE
        self._lock = threading.Lock()
        self._ensure_file()
        self._learning_cache = {}  # domain -> learning context cache
        print(f"✅ FeedbackStore initialized: {self.filepath}")

    def _ensure_file(self):
        """Create feedback file if it doesn't exist."""
        if not os.path.exists(self.filepath):
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "feedbacks": [],
                        "stats": {"total": 0, "positive": 0, "negative": 0},
                    },
                    f,
                    ensure_ascii=False,
                    indent=2,
                )

    def add_feedback(
        self,
        url: str,
        rating: str,
        correction: str = "",
        modules: dict = None,
        scan_results: dict = None,
    ) -> dict:
        """
        Add a user feedback entry.

        Args:
            url: The scanned URL
            rating: "positive" or "negative"
            correction: Optional user correction text
            modules: Optional dict of per-module ratings
            scan_results: Optional snapshot of scan results for learning

        Returns:
            dict with status and total count
        """
        with self._lock:
            try:
                data = self._read()

                entry = {
                    "url": url,
                    "domain": self._extract_domain(url),
                    "rating": rating,
                    "correction": correction[:500] if correction else "",
                    "modules": modules or {},
                    "scan_snapshot": (
                        self._compress_snapshot(scan_results) if scan_results else {}
                    ),
                    "timestamp": datetime.now().isoformat(),
                }

                data["feedbacks"].append(entry)
                data["stats"]["total"] += 1
                if rating == "positive":
                    data["stats"]["positive"] += 1
                else:
                    data["stats"]["negative"] += 1

                # Cap at MAX_ENTRIES (FIFO)
                if len(data["feedbacks"]) > MAX_ENTRIES:
                    data["feedbacks"] = data["feedbacks"][-MAX_ENTRIES:]

                self._write(data)

                return {
                    "status": "ok",
                    "total": data["stats"]["total"],
                    "message": "Cảm ơn phản hồi của bạn! 🙏",
                }

            except Exception as e:
                print(f"⚠️ FeedbackStore error: {e}")
                return {"status": "error", "message": str(e)}

    def get_stats(self) -> dict:
        """Get feedback statistics."""
        try:
            data = self._read()
            return data.get("stats", {"total": 0, "positive": 0, "negative": 0})
        except Exception:
            return {"total": 0, "positive": 0, "negative": 0}

    def get_recent(self, limit: int = 20) -> list:
        """Get recent feedback entries."""
        try:
            data = self._read()
            return data.get("feedbacks", [])[-limit:]
        except Exception:
            return []

    def _read(self) -> dict:
        """Read feedback data from file."""
        self._ensure_file()
        with open(self.filepath, "r", encoding="utf-8") as f:
            return json.load(f)

    def _write(self, data: dict):
        """Write feedback data to file."""
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # ========================================================================
    # LEARNING SYSTEM — Use feedback history to improve future scans
    # ========================================================================

    def get_learning_context(self, url: str, max_examples: int = 5) -> str:
        """
        Generate a learning context string from past feedback for Gemini prompts.
        This teaches the AI from user corrections so it improves over time.

        Returns a string to inject into Gemini analysis prompts.
        """
        domain = self._extract_domain(url)

        # Check cache first
        cache_key = f"{domain}_{max_examples}"
        if cache_key in self._learning_cache:
            return self._learning_cache[cache_key]

        try:
            data = self._read()
            feedbacks = data.get("feedbacks", [])

            # Get negative feedbacks with corrections (most valuable for learning)
            corrections = [
                f
                for f in feedbacks
                if f.get("correction") and f.get("rating") == "negative"
            ]

            # Also get domain-specific feedbacks
            domain_feedbacks = [f for f in feedbacks if f.get("domain") == domain]

            if not corrections and not domain_feedbacks:
                return ""

            lines = []
            lines.append("=== HỌC TỪ PHẢN HỒI NGƯỜI DÙNG ===")

            # Domain-specific accuracy
            if domain_feedbacks:
                pos = sum(1 for f in domain_feedbacks if f.get("rating") == "positive")
                neg = sum(1 for f in domain_feedbacks if f.get("rating") == "negative")
                total = pos + neg
                if total > 0:
                    accuracy = pos / total * 100
                    lines.append(
                        f"Trang {domain}: {total} lần quét, {accuracy:.0f}% chính xác."
                    )
                    if accuracy < 60:
                        lines.append(
                            f"⚠️ Độ chính xác thấp cho {domain} — hãy thận trọng hơn."
                        )

            # User corrections (most recent, most valuable)
            recent_corrections = corrections[-max_examples:]
            if recent_corrections:
                lines.append("\nNhững lần phân tích SAI trước đây (user đã sửa):")
                for i, fb in enumerate(recent_corrections, 1):
                    snap = fb.get("scan_snapshot", {})
                    correction_text = fb.get("correction", "")
                    fb_domain = fb.get("domain", "?")

                    detail = f"{i}. [{fb_domain}]"
                    if snap.get("verdict"):
                        detail += f" Hệ thống nói: '{snap['verdict']}'"
                    if snap.get("risk_level"):
                        detail += f" (rủi ro: {snap['risk_level']})"
                    if correction_text:
                        detail += f" → User sửa: '{correction_text}'"
                    lines.append(detail)

                lines.append(
                    "\nHãy tránh lặp lại các sai lầm trên. Ưu tiên độ chính xác."
                )

            # Aggregate patterns from negative feedback
            neg_count = data["stats"].get("negative", 0)
            pos_count = data["stats"].get("positive", 0)
            total = neg_count + pos_count
            if total >= 10:
                overall_accuracy = pos_count / total * 100
                lines.append(
                    f"\nĐộ chính xác tổng thể: {overall_accuracy:.0f}% ({pos_count}/{total})"
                )
                if overall_accuracy < 70:
                    lines.append(
                        "⚠️ Hệ thống cần cải thiện — hãy phân tích kỹ hơn trước khi đưa kết luận."
                    )

            context = "\n".join(lines)
            self._learning_cache[cache_key] = context
            return context

        except Exception as e:
            print(f"⚠️ Learning context error: {e}")
            return ""

    def get_domain_feedback(self, url: str) -> dict:
        """Get feedback summary for a specific domain."""
        domain = self._extract_domain(url)
        try:
            data = self._read()
            feedbacks = data.get("feedbacks", [])
            domain_fb = [f for f in feedbacks if f.get("domain") == domain]

            if not domain_fb:
                return {"domain": domain, "total": 0, "accuracy": None}

            pos = sum(1 for f in domain_fb if f.get("rating") == "positive")
            neg = sum(1 for f in domain_fb if f.get("rating") == "negative")
            total = pos + neg
            corrections = [
                f.get("correction") for f in domain_fb if f.get("correction")
            ]

            return {
                "domain": domain,
                "total": total,
                "positive": pos,
                "negative": neg,
                "accuracy": round(pos / total * 100, 1) if total > 0 else None,
                "recent_corrections": corrections[-3:],
            }
        except Exception:
            return {"domain": domain, "total": 0, "accuracy": None}

    def _compress_snapshot(self, scan_results: dict) -> dict:
        """Compress scan results to essential fields for learning storage."""
        if not scan_results:
            return {}
        try:
            return {
                "verdict": scan_results.get("fact_check_v3", {}).get("verdict", ""),
                "risk_score": scan_results.get("risk_score_v3", {}).get(
                    "risk_score", 0
                ),
                "risk_level": scan_results.get("risk_score_v3", {}).get(
                    "risk_level", ""
                ),
                "sentiment": scan_results.get("sentiment_v3", {}).get("overall", ""),
                "is_toxic": scan_results.get("toxicity_v3", {}).get("is_toxic", False),
                "severity": scan_results.get("toxicity_v3", {}).get("severity", ""),
            }
        except Exception:
            return {}

    def invalidate_cache(self):
        """Clear learning cache (call after new feedback is added)."""
        self._learning_cache.clear()

    def _extract_domain(self, url: str) -> str:
        try:
            parsed = urlparse(url)
            domain = parsed.hostname or ""
            return domain.replace("www.", "")
        except Exception:
            return url[:50]
