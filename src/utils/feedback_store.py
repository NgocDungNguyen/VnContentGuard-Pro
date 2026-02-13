"""
VnContentGuard Pro v5.0 — User Feedback Store
===============================================
Stores user feedback (thumbs up/down + optional corrections)
in a local JSON file for evaluation dataset building.
"""

import json
import os
import threading
from datetime import datetime

FEEDBACK_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "feedback_data.json"
)
MAX_ENTRIES = 5000


class FeedbackStore:
    """Thread-safe JSON-based feedback storage."""

    def __init__(self, filepath=None):
        self.filepath = filepath or FEEDBACK_FILE
        self._lock = threading.Lock()
        self._ensure_file()
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
        self, url: str, rating: str, correction: str = "", modules: dict = None
    ) -> dict:
        """
        Add a user feedback entry.

        Args:
            url: The scanned URL
            rating: "positive" or "negative"
            correction: Optional user correction text
            modules: Optional dict of per-module ratings

        Returns:
            dict with status and total count
        """
        with self._lock:
            try:
                data = self._read()

                entry = {
                    "url": url,
                    "rating": rating,
                    "correction": correction[:500] if correction else "",
                    "modules": modules or {},
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
