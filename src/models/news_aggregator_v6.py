"""
VnContentGuard Pro v6 - News Aggregator & Cross-Reference
==========================================================
Cross-reference claims against credible news sources using:
1. NewsData.io API (200 req/day free tier)
2. GNews API (100 req/day free tier, backup)
3. Caching to minimize API usage
"""

import asyncio
import hashlib
import json
import os
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import aiohttp
from dotenv import load_dotenv

load_dotenv()


class NewsAggregator:
    """
    News Cross-Reference System

    Features:
    - Search credible news sources for related articles
    - Count matching/corroborating sources
    - Cache results to save API calls
    - Fallback between NewsData.io and GNews

    Match Score: 0-100 (0=no matches, 100=widely reported)
    """

    def __init__(self):
        print("⏳ Initializing News Aggregator v6...")

        # API Keys
        self.newsdata_key = os.getenv("NEWSDATA_API_KEY")
        self.gnews_key = os.getenv("GNEWS_API_KEY")

        # API endpoints
        self.newsdata_url = "https://newsdata.io/api/1/news"
        self.gnews_url = "https://gnews.io/api/v4/search"

        # Cache setup (simple in-memory for now)
        self.cache = {}
        self.cache_duration = 3600  # 1 hour

        # Rate limiting
        self.last_newsdata_call = None
        self.last_gnews_call = None
        self.min_interval = 2  # 2 seconds between calls

        # Log API availability
        if self.newsdata_key:
            print("✅ NewsData.io API configured (200 req/day)")
        else:
            print("⚠️ NewsData.io API not configured")

        if self.gnews_key:
            print("✅ GNews API configured (100 req/day, backup)")
        else:
            print("⚠️ GNews API not configured")

        print("✅ News Aggregator v6 Ready!")

    async def search_async(self, query: str, language: str = "vi") -> Dict:
        """
        Search news sources asynchronously

        Args:
            query: Search query (claim or keywords)
            language: Language code ('vi' for Vietnamese, 'en' for English)

        Returns:
            Dict with:
            - match_count: int (number of matching articles)
            - articles: list (relevant articles)
            - sources: list (unique news sources)
            - match_score: int (0-100)
        """
        if not query or not query.strip():
            return self._empty_result()

        # Check cache first
        cache_key = self._get_cache_key(query, language)
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            if datetime.now() - cached["timestamp"] < timedelta(
                seconds=self.cache_duration
            ):
                print(f"📦 Cache hit for: {query[:50]}")
                return cached["data"]

        # Try NewsData.io first
        result = None
        if self.newsdata_key:
            result = await self._search_newsdata(query, language)

        # Fallback to GNews if NewsData fails
        if not result and self.gnews_key:
            result = await self._search_gnews(query, language)

        # Default empty result if both fail
        if not result:
            result = self._empty_result()

        # Cache the result
        self.cache[cache_key] = {"timestamp": datetime.now(), "data": result}

        return result

    def search(self, query: str, language: str = "vi") -> Dict:
        """Synchronous wrapper for search_async"""
        return asyncio.run(self.search_async(query, language))

    async def _search_newsdata(self, query: str, language: str) -> Optional[Dict]:
        """Search NewsData.io API"""
        try:
            # Rate limiting
            await self._rate_limit_newsdata()

            params = {
                "apikey": self.newsdata_key,
                "q": query,
                "language": language,
                "size": 10,  # Get top 10 articles
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.newsdata_url, params=params, timeout=10
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._parse_newsdata_response(data)
                    else:
                        print(f"⚠️ NewsData.io error: {response.status}")
                        return None
        except Exception as e:
            print(f"⚠️ NewsData.io request failed: {e}")
            return None

    async def _search_gnews(self, query: str, language: str) -> Optional[Dict]:
        """Search GNews API (backup)"""
        try:
            # Rate limiting
            await self._rate_limit_gnews()

            params = {
                "apikey": self.gnews_key,
                "q": query,
                "lang": language,
                "max": 10,  # Get top 10 articles
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.gnews_url, params=params, timeout=10
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._parse_gnews_response(data)
                    else:
                        print(f"⚠️ GNews error: {response.status}")
                        return None
        except Exception as e:
            print(f"⚠️ GNews request failed: {e}")
            return None

    def _parse_newsdata_response(self, data: Dict) -> Dict:
        """Parse NewsData.io API response"""
        articles = data.get("results", [])

        parsed_articles = []
        sources = set()

        for article in articles:
            parsed = {
                "title": article.get("title", ""),
                "source": article.get("source_id", "Unknown"),
                "url": article.get("link", ""),
                "published": article.get("pubDate", ""),
                "description": article.get("description", "")[:200],
            }
            parsed_articles.append(parsed)
            sources.add(parsed["source"])

        match_count = len(articles)
        match_score = min(100, match_count * 10)  # 10 points per article, max 100

        return {
            "match_count": match_count,
            "articles": parsed_articles,
            "sources": list(sources),
            "match_score": match_score,
            "api_used": "NewsData.io",
        }

    def _parse_gnews_response(self, data: Dict) -> Dict:
        """Parse GNews API response"""
        articles = data.get("articles", [])

        parsed_articles = []
        sources = set()

        for article in articles:
            source_info = article.get("source", {})
            parsed = {
                "title": article.get("title", ""),
                "source": source_info.get("name", "Unknown"),
                "url": article.get("url", ""),
                "published": article.get("publishedAt", ""),
                "description": article.get("description", "")[:200],
            }
            parsed_articles.append(parsed)
            sources.add(parsed["source"])

        match_count = len(articles)
        match_score = min(100, match_count * 10)

        return {
            "match_count": match_count,
            "articles": parsed_articles,
            "sources": list(sources),
            "match_score": match_score,
            "api_used": "GNews",
        }

    async def _rate_limit_newsdata(self):
        """Enforce rate limiting for NewsData.io"""
        if self.last_newsdata_call:
            elapsed = (datetime.now() - self.last_newsdata_call).total_seconds()
            if elapsed < self.min_interval:
                await asyncio.sleep(self.min_interval - elapsed)
        self.last_newsdata_call = datetime.now()

    async def _rate_limit_gnews(self):
        """Enforce rate limiting for GNews"""
        if self.last_gnews_call:
            elapsed = (datetime.now() - self.last_gnews_call).total_seconds()
            if elapsed < self.min_interval:
                await asyncio.sleep(self.min_interval - elapsed)
        self.last_gnews_call = datetime.now()

    def _get_cache_key(self, query: str, language: str) -> str:
        """Generate cache key from query and language"""
        content = f"{query}_{language}"
        return hashlib.md5(content.encode()).hexdigest()

    def _empty_result(self) -> Dict:
        """Return empty result for invalid input or API failures"""
        return {
            "match_count": 0,
            "articles": [],
            "sources": [],
            "match_score": 0,
            "api_used": None,
        }


# Convenience function
def search_news(query: str, language: str = "vi") -> Dict:
    """Quick news search"""
    aggregator = NewsAggregator()
    return aggregator.search(query, language)


if __name__ == "__main__":
    # Quick test
    aggregator = NewsAggregator()

    test_queries = ["COVID-19 vaccine", "Việt Nam kinh tế 2024", "climate change"]

    print("\n🧪 Testing News Aggregator v6:")
    for query in test_queries:
        print(f"\n🔍 Searching: {query}")
        result = aggregator.search(query, language="en" if "COVID" in query else "vi")

        print(f"Match Count: {result['match_count']}")
        print(f"Match Score: {result['match_score']}/100")
        print(f"Unique Sources: {len(result['sources'])}")
        if result["api_used"]:
            print(f"API Used: {result['api_used']}")

        if result["articles"]:
            print(f"\nTop Article: {result['articles'][0]['title']}")
