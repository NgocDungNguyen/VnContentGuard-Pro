"""
VnContentGuard Pro V7 - Source Credibility Analyzer
====================================================
Analyze domain/URL credibility using multiple signals:
1. Domain age (older = more credible)
2. SSL certificate validation
3. Reputation scoring (Vietnamese news source whitelist/blacklist)
4. URL patterns (suspicious patterns detection)
"""

import re
import socket
import ssl
from datetime import datetime
from typing import Dict, Optional
from urllib.parse import urlparse

import validators
import whois  # python-whois


class SourceAnalyzer:
    """
    Source Credibility Analysis System

    Analyzes:
    - Domain age and registration
    - SSL certificate status
    - Reputation (Vietnamese news source databases)
    - URL pattern analysis

    Reputation Score: 0-100 (0=untrusted, 100=highly trusted)
    """

    def __init__(self):
        print("⏳ Initializing Source Analyzer V7...")

        # Vietnamese credible news sources (whitelist)
        self.trusted_domains = {
            # State media
            "vnexpress.net": 95,
            "tuoitre.vn": 95,
            "thanhnien.vn": 95,
            "dantri.com.vn": 90,
            "vietnamnet.vn": 90,
            "baomoi.com": 85,
            "vov.vn": 95,  # Voice of Vietnam
            "vtv.vn": 95,  # Vietnam Television
            "nhandan.vn": 90,  # Nhân Dân
            "vietnamplus.vn": 90,  # VietnamPlus
            # International trusted
            "bbc.com": 95,
            "reuters.com": 95,
            "apnews.com": 95,
            "bloomberg.com": 90,
            "theguardian.com": 90,
            "nytimes.com": 90,
            "washingtonpost.com": 90,
            # Academic/Government
            ".edu.vn": 90,
            ".gov.vn": 95,
            ".edu": 85,
            ".gov": 90,
        }

        # Known unreliable patterns (blacklist)
        self.suspicious_patterns = [
            r".*fakene.*",
            r".*clickbait.*",
            r".*viral.*news.*",
            r".*shocking.*",
            r".*\d{4,}\.xyz$",  # Random numbers + .xyz
            r".*free-.*\.com$",
            r".*-free\.com$",
        ]

        print("✅ Source Analyzer V7 Ready!")

    def analyze(self, url: str) -> Optional[Dict]:
        """
        Analyze URL/domain credibility

        Args:
            url: Full URL or domain to analyze

        Returns:
            Dict with:
            - domain: str
            - reputation_score: int (0-100)
            - domain_age_days: int
            - ssl_valid: bool
            - risk_factors: list
            - verdict: str (Trusted/Questionable/Untrusted)
        """
        if not url or not url.strip():
            return None

        # Validate URL format
        if not validators.url(url):
            # Try adding http:// prefix
            if validators.url(f"http://{url}"):
                url = f"http://{url}"
            else:
                return self._invalid_url_result(url)

        # Parse domain
        parsed = urlparse(url)
        domain = parsed.netloc or parsed.path.split("/")[0]
        domain = domain.lower().strip()

        results = {
            "domain": domain,
            "reputation_score": 50,  # Neutral start
            "domain_age_days": None,
            "ssl_valid": None,
            "risk_factors": [],
            "verdict": "Unknown",
        }

        # Check 1: Reputation (whitelist/blacklist)
        reputation_score = self._check_reputation(domain)
        results["reputation_score"] = reputation_score

        # Check 2: Domain age
        age_info = self._check_domain_age(domain)
        if age_info:
            results["domain_age_days"] = age_info["age_days"]
            # Older domains more credible
            if age_info["age_days"] > 3650:  # >10 years
                results["reputation_score"] += 15
            elif age_info["age_days"] > 1825:  # >5 years
                results["reputation_score"] += 10
            elif age_info["age_days"] < 90:  # <3 months
                results["reputation_score"] -= 20
                results["risk_factors"].append("Tên miền rất mới")

        # Check 3: SSL certificate
        ssl_valid = self._check_ssl(domain)
        results["ssl_valid"] = ssl_valid
        if ssl_valid:
            results["reputation_score"] += 5
        else:
            results["risk_factors"].append("Không có chứng chỉ SSL hợp lệ")
            results["reputation_score"] -= 10

        # Check 4: Suspicious patterns
        if self._is_suspicious_pattern(domain):
            results["risk_factors"].append("Tên miền có dấu hiệu đáng ngờ")
            results["reputation_score"] -= 15

        # Clamp score to 0-100
        results["reputation_score"] = max(0, min(100, results["reputation_score"]))

        # Final verdict
        results["verdict"] = self._calculate_verdict(results["reputation_score"])

        return results

    def _check_reputation(self, domain: str) -> int:
        """Check domain against whitelist/blacklist"""
        # Exact match in trusted domains
        if domain in self.trusted_domains:
            return self.trusted_domains[domain]

        # Check for domain suffixes (e.g., .edu.vn, .gov.vn)
        for trusted_suffix, score in self.trusted_domains.items():
            if trusted_suffix.startswith(".") and domain.endswith(trusted_suffix):
                return score

        # Check for subdomain of trusted source
        for trusted_domain, score in self.trusted_domains.items():
            if not trusted_domain.startswith(".") and domain.endswith(
                "." + trusted_domain
            ):
                return score - 5  # Slightly lower for subdomain

        return 50  # Neutral if not found

    def _check_domain_age(self, domain: str) -> Optional[Dict]:
        """Get domain age via WHOIS"""
        try:
            w = whois.whois(domain)

            # Extract creation date
            creation_date = w.creation_date
            if isinstance(creation_date, list):
                creation_date = creation_date[0]

            if creation_date:
                # Handle both naive and aware datetimes
                now = (
                    datetime.now(creation_date.tzinfo)
                    if creation_date.tzinfo
                    else datetime.now()
                )
                age = now - creation_date
                return {
                    "age_days": age.days,
                    "creation_date": creation_date.strftime("%Y-%m-%d"),
                    "registrar": w.registrar,
                }
        except Exception as e:
            print(f"⚠️ WHOIS lookup failed for {domain}: {e}")

        return None

    def _check_ssl(self, domain: str) -> bool:
        """Check if domain has valid SSL certificate"""
        try:
            # Remove www. prefix if present
            domain = domain.replace("www.", "")

            context = ssl.create_default_context()
            with socket.create_connection((domain, 443), timeout=5) as sock:
                with context.wrap_socket(sock, server_hostname=domain) as ssock:
                    cert = ssock.getpeercert()
                    return cert is not None
        except Exception:
            return False

    def _is_suspicious_pattern(self, domain: str) -> bool:
        """Check if domain matches suspicious patterns"""
        for pattern in self.suspicious_patterns:
            if re.match(pattern, domain):
                return True
        return False

    def _calculate_verdict(self, score: int) -> str:
        """Calculate verdict from reputation score"""
        if score >= 80:
            return "Đáng tin cậy"
        elif score >= 60:
            return "Tương đối đáng tin"
        elif score >= 40:
            return "Đáng ngờ"
        else:
            return "Không đáng tin"

    def _invalid_url_result(self, url: str) -> Dict:
        """Return result for invalid URL"""
        return {
            "domain": url,
            "reputation_score": 0,
            "domain_age_days": None,
            "ssl_valid": False,
            "risk_factors": ["URL không hợp lệ"],
            "verdict": "Invalid",
        }


# Convenience function
def analyze_source(url: str) -> Optional[Dict]:
    """Quick source analysis"""
    analyzer = SourceAnalyzer()
    return analyzer.analyze(url)


if __name__ == "__main__":
    # Quick test
    analyzer = SourceAnalyzer()

    test_urls = [
        "https://vnexpress.net",
        "https://bbc.com",
        "https://random-news-2024.xyz",
        "https://vietnamnet.vn/tin-tuc",
    ]

    print("\n🧪 Testing Source Analyzer V7:")
    for url in test_urls:
        result = analyzer.analyze(url)
        if result:
            print(f"\nURL: {url}")
            print(f"Domain: {result['domain']}")
            print(f"Reputation: {result['reputation_score']}/100")
            print(f"Verdict: {result['verdict']}")
            print(f"SSL Valid: {result['ssl_valid']}")
            if result["domain_age_days"]:
                print(f"Age: {result['domain_age_days']} days")
            if result["risk_factors"]:
                print(f"Risks: {', '.join(result['risk_factors'])}")
