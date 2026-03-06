"""
VnContentGuard Pro V7.9 — Score Re-Ranker
==========================================
Learns per-domain score calibration from user corrections.

For each (domain, category) pair, the re-ranker stores historical
Gemini scores alongside user-corrected scores.  When enough samples
accumulate (≥ MIN_SAMPLES) it applies a bounded adjustment to future
predictions so the system continuously improves on Vietnamese content.

Storage: JSON file at RERANKER_DATA env path (defaults to project root).
Thread-safe: uses threading.Lock for all reads and writes.
"""

import json
import logging
import os
import statistics
import threading
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class ScoreReranker:
    """
    Lightweight domain+category re-ranker.

    For each (domain, category) pair, stores:
      - gemini_scores  : list of raw Gemini-predicted scores
      - user_scores    : list of user-corrected scores

    Adjustment = mean(user_scores) - mean(gemini_scores)
    Capped at ±MAX_ADJUSTMENT points.
    Only applied when n >= MIN_SAMPLES per side.
    """

    MIN_SAMPLES = 5
    MAX_ADJUSTMENT = 20.0
    MAX_HISTORY = 200  # samples retained per key

    _DATA_FILE = Path(os.getenv("RERANKER_DATA", "reranker_data.json"))

    def __init__(self):
        self._lock = threading.Lock()
        self._data: Dict = self._load()
        logger.info(
            f"✅ ScoreReranker initialised — {len(self._data)} domain entries loaded"
        )

    # -------------------------------------------------------------------------
    # Persistence
    # -------------------------------------------------------------------------

    def _load(self) -> Dict:
        """Load existing reranker data from file."""
        try:
            if self._DATA_FILE.exists():
                return json.loads(self._DATA_FILE.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning(f"⚠️ Reranker load failed ({e}), starting fresh")
        return {}

    def _save(self):
        """Persist reranker data (caller must hold self._lock)."""
        try:
            self._DATA_FILE.write_text(
                json.dumps(self._data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as e:
            logger.warning(f"⚠️ Reranker save failed: {e}")

    # -------------------------------------------------------------------------
    # Core API
    # -------------------------------------------------------------------------

    def record_correction(
        self,
        domain: str,
        category: str,
        gemini_score: float,
        user_score: float,
    ):
        """
        Record one user correction for a domain + category pair.

        Args:
            domain:       bare hostname, e.g. "vnexpress.net"
            category:     "risk_score" | "toxicity" | "sentiment"
            gemini_score: score that Gemini predicted (0-100)
            user_score:   score the user believes is correct (0-100)
        """
        key = f"{domain}:{category}"
        with self._lock:
            entry = self._data.setdefault(key, {"gemini": [], "user": []})
            entry["gemini"].append(float(gemini_score))
            entry["user"].append(float(user_score))

            # Trim to MAX_HISTORY most-recent samples
            for side in ("gemini", "user"):
                if len(entry[side]) > self.MAX_HISTORY:
                    entry[side] = entry[side][-self.MAX_HISTORY :]

            self._save()

        logger.debug(
            f"📝 Correction recorded: {key} "
            f"gemini={gemini_score:.1f} → user={user_score:.1f}"
        )

    def get_adjustment(self, domain: str, category: str) -> float:
        """
        Return the learned score adjustment for this domain + category.

        Returns 0.0 if there are not enough samples yet.
        The value is clamped to ±MAX_ADJUSTMENT.
        """
        key = f"{domain}:{category}"
        with self._lock:
            entry = self._data.get(key, {})

        gemini_scores = entry.get("gemini", [])
        user_scores = entry.get("user", [])

        if len(gemini_scores) < self.MIN_SAMPLES or len(user_scores) < self.MIN_SAMPLES:
            return 0.0

        adjustment = statistics.mean(user_scores) - statistics.mean(gemini_scores)
        return max(-self.MAX_ADJUSTMENT, min(self.MAX_ADJUSTMENT, adjustment))

    def apply(self, domain: str, results: Dict) -> Dict:
        """
        Apply learned adjustments to a full scan result dict.

        Modifies (a copy of) `results`:
          - risk_score adjusted by risk_score calibration
          - toxicity_score adjusted by toxicity calibration
          - adds reranker_applied flag and reranker_adjustments breakdown

        Args:
            domain:  bare hostname of the scanned page
            results: combined scan result from unified endpoint

        Returns:
            New dict with adjustments applied.
        """
        adjusted = dict(results)

        risk_adj = self.get_adjustment(domain, "risk_score")
        tox_adj = self.get_adjustment(domain, "toxicity")

        samples = 0
        try:
            key = f"{domain}:risk_score"
            with self._lock:
                samples = len(self._data.get(key, {}).get("gemini", []))
        except Exception:
            pass

        if abs(risk_adj) >= 0.5:
            orig = float(adjusted.get("risk_score", 0))
            adjusted["risk_score"] = int(max(0, min(100, round(orig + risk_adj))))

        # Nested toxicity dict adjustment
        tox_data = adjusted.get("toxicity_v7", {})
        if isinstance(tox_data, dict) and abs(tox_adj) >= 0.5:
            orig_tox = float(tox_data.get("overall_score", 0))
            tox_data = dict(tox_data)
            tox_data["overall_score"] = round(
                max(0.0, min(1.0, orig_tox + tox_adj / 100.0)), 3
            )
            adjusted["toxicity_v7"] = tox_data

        adjusted["reranker_applied"] = abs(risk_adj) >= 0.5 or abs(tox_adj) >= 0.5
        adjusted["reranker_adjustments"] = {
            "risk_score": round(risk_adj, 1),
            "toxicity": round(tox_adj, 1),
            "samples": samples,
        }

        return adjusted

    # -------------------------------------------------------------------------
    # Diagnostics
    # -------------------------------------------------------------------------

    def get_stats(self) -> Dict:
        """Return summary statistics for all tracked domain+category pairs."""
        with self._lock:
            total_corrections = sum(len(v.get("user", [])) for v in self._data.values())
            domains_tracked = len({k.split(":")[0] for k in self._data.keys()})
        return {
            "domains_tracked": domains_tracked,
            "total_corrections": total_corrections,
            "pairs_with_enough_data": sum(
                1
                for v in self._data.values()
                if len(v.get("gemini", [])) >= self.MIN_SAMPLES
            ),
        }
