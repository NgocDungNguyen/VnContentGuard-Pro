from urllib.parse import urlparse

from bs4 import BeautifulSoup

from src.crawlers.base_crawler import BaseCrawler
from src.utils.text_cleaner import TextCleaner


class NewsCrawler(BaseCrawler):
    """
    News article crawler with site-specific support.
    Inherits from BaseCrawler for user-agent rotation and error handling.
    """

    def __init__(self):
        super().__init__()
        # Site-specific selectors for removing ads and extracting content
        self.site_config = {
            "vnexpress.net": {
                "title_selector": ["h1.title", "h1", ".fck_heading1"],
                "content_selector": [
                    "article",
                    ".fck_content",
                    ".content_detail",
                    "div.article-content",
                ],
                "date_selector": [".date", ".published-date", "time"],
                "ads_to_remove": [
                    ".ad",
                    ".adv",
                    ".advertisement",
                    ".banner",
                    ".promotional",
                ],
            },
            "dantri.com.vn": {
                "title_selector": ["h1.title", "h1", ".news-title"],
                "content_selector": [".news-content", "article", ".ArticleContent"],
                "date_selector": [".date", ".publish-date", ".published-date"],
                "ads_to_remove": [".ad", ".ads", ".banner", ".box-ads"],
            },
            "tuoitre.vn": {
                "title_selector": ["h1", "h1.title", ".detail-title"],
                "content_selector": [
                    ".fck_detail_content",
                    ".detail-content",
                    "article",
                ],
                "date_selector": [".date", ".publish-date", ".created-date"],
                "ads_to_remove": [".ad-container", ".ads", ".banner-ad"],
            },
        }

    def _get_domain(self, url):
        """Extract domain from URL."""
        try:
            parsed = urlparse(url)
            return parsed.netloc.replace("www.", "")
        except:
            return ""

    def _extract_title(self, soup, domain):
        """Extract title using site-specific selectors."""
        if domain in self.site_config:
            selectors = self.site_config[domain]["title_selector"]
        else:
            selectors = ["h1", "h1.title", ".title"]

        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                return element.get_text().strip()

        return "No Title Found"

    def _extract_date(self, soup, domain):
        """Extract publication date using site-specific selectors."""
        if domain in self.site_config:
            selectors = self.site_config[domain]["date_selector"]
        else:
            selectors = [".date", ".published-date", "time", ".publish-date"]

        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                return element.get_text().strip()

        return None

    def _remove_ads_and_junk(self, soup, domain):
        """Remove advertisement and sidebar elements."""
        if domain in self.site_config:
            ads_selectors = self.site_config[domain]["ads_to_remove"]
        else:
            ads_selectors = [
                ".ad",
                ".ads",
                ".advertisement",
                ".banner",
                ".sidebar",
                ".related-news",
            ]

        for selector in ads_selectors:
            elements = soup.select(selector)
            for el in elements:
                el.decompose()

    def _extract_content(self, soup, domain):
        """Extract article content using site-specific selectors."""
        # First, remove ads
        self._remove_ads_and_junk(soup, domain)

        # Then extract content
        if domain in self.site_config:
            selectors = self.site_config[domain]["content_selector"]
        else:
            selectors = [
                "article",
                ".article-content",
                ".content-detail",
                "div.content",
            ]

        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                paragraphs = element.find_all("p")
                content_text = " ".join([p.get_text() for p in paragraphs])
                if content_text.strip():
                    return content_text

        # Fallback: grab all paragraphs
        paragraphs = soup.find_all("p")
        return " ".join([p.get_text() for p in paragraphs])

    def extract(self, url):
        """
        Extract article from URL with site-specific optimization.

        Args:
            url (str): The article URL

        Returns:
            dict: Contains url, title, content, date, and error fields
        """
        try:
            print(f"🕷️ Crawling: {url}")

            soup = self.get_soup(url, timeout=10)

            # Check if get_soup returned an error
            if isinstance(soup, dict) and "error" in soup:
                return soup

            domain = self._get_domain(url)

            # Extract components
            title = self._extract_title(soup, domain)
            content = self._extract_content(soup, domain)
            date = self._extract_date(soup, domain)

            # Clean the text
            cleaned_text = TextCleaner.clean(content)

            return {
                "url": url,
                "title": title,
                "content": cleaned_text,
                "date": date,
                "domain": domain,
                "error": None,
            }

        except Exception as e:
            self.log_error("Error extracting article", e)
            return {"error": str(e)}


# Quick Test
if __name__ == "__main__":
    crawler = NewsCrawler()
    # Test with a real article
    result = crawler.extract("https://vnexpress.net/thoi-su")
    print(result)
