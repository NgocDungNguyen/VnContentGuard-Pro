"""
VnContentGuard Pro v4.9 — Community Blocklist
================================================
Stores user reports of toxic/misleading pages.
Domains with 5+ reports are added to community blocklist.
"""

import json
import os
import threading
from datetime import datetime
from urllib.parse import urlparse

BLOCKLIST_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "blocklist_data.json"
)


class CommunityBlocklist:
    """Thread-safe community-powered blocklist."""

    REPORT_THRESHOLD = 5  # Reports needed to blocklist a domain
    MAX_REPORTS = 10000

    def __init__(self, filepath=None):
        self.filepath = filepath or BLOCKLIST_FILE
        self._lock = threading.Lock()
        self._ensure_file()
        print(f"✅ CommunityBlocklist initialized: {self.filepath}")

    def _ensure_file(self):
        if not os.path.exists(self.filepath):
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "reports": [],
                        "domain_counts": {},
                        "blocklist": [],
                        "whitelist": [],
                        "stats": {"total_reports": 0, "blocked_domains": 0},
                    },
                    f,
                    ensure_ascii=False,
                    indent=2,
                )

    def add_report(self, url: str, risk_score: float, reason: str = "") -> dict:
        """Add a user report for a URL/domain."""
        with self._lock:
            try:
                data = self._read()
                domain = self._extract_domain(url)

                report = {
                    "url": url,
                    "domain": domain,
                    "risk_score": risk_score,
                    "reason": reason[:300] if reason else "",
                    "timestamp": datetime.now().isoformat(),
                }

                data["reports"].append(report)
                data["stats"]["total_reports"] += 1

                # Update domain count
                data["domain_counts"][domain] = data["domain_counts"].get(domain, 0) + 1

                # Auto-blocklist if threshold reached
                newly_blocked = False
                if (
                    data["domain_counts"][domain] >= self.REPORT_THRESHOLD
                    and domain not in data["blocklist"]
                    and domain not in data["whitelist"]
                ):
                    data["blocklist"].append(domain)
                    data["stats"]["blocked_domains"] += 1
                    newly_blocked = True
                    print(
                        f"🚫 Domain blocklisted: {domain} ({data['domain_counts'][domain]} reports)"
                    )

                # Cap reports
                if len(data["reports"]) > self.MAX_REPORTS:
                    data["reports"] = data["reports"][-self.MAX_REPORTS :]

                self._write(data)

                return {
                    "status": "ok",
                    "domain": domain,
                    "report_count": data["domain_counts"][domain],
                    "newly_blocked": newly_blocked,
                    "message": (
                        "Cảm ơn báo cáo của bạn! 🙏"
                        if not newly_blocked
                        else f"🚫 {domain} đã bị chặn bởi cộng đồng!"
                    ),
                }
            except Exception as e:
                print(f"⚠️ Blocklist error: {e}")
                return {"status": "error", "message": str(e)}

    def get_blocklist(self) -> list:
        """Get list of blocked domains."""
        try:
            data = self._read()
            return data.get("blocklist", [])
        except Exception:
            return []

    def is_blocked(self, url: str) -> bool:
        """Check if a URL's domain is blocklisted."""
        try:
            domain = self._extract_domain(url)
            blocklist = self.get_blocklist()
            return domain in blocklist
        except Exception:
            return False

    def get_domain_report_count(self, url: str) -> int:
        """Get report count for a URL's domain."""
        try:
            domain = self._extract_domain(url)
            data = self._read()
            return data.get("domain_counts", {}).get(domain, 0)
        except Exception:
            return 0

    def get_stats(self) -> dict:
        """Get blocklist statistics."""
        try:
            data = self._read()
            return data.get("stats", {"total_reports": 0, "blocked_domains": 0})
        except Exception:
            return {"total_reports": 0, "blocked_domains": 0}

    def _extract_domain(self, url: str) -> str:
        try:
            parsed = urlparse(url)
            domain = parsed.hostname or ""
            return domain.replace("www.", "")
        except Exception:
            return url[:50]

    def _read(self) -> dict:
        self._ensure_file()
        with open(self.filepath, "r", encoding="utf-8") as f:
            return json.load(f)

    def _write(self, data: dict):
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
