import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
import random
import time


class BaseCrawler:
    """
    Base class for all web crawlers.
    Provides common utilities for:
    - User-Agent rotation
    - Beautiful Soup parsing
    - Playwright browser setup
    - Error logging
    """

    # User-Agent pool for rotation
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.82 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:91.0) Gecko/20100101 Firefox/91.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    ]

    def __init__(self):
        """Initialize the base crawler."""
        self.session = requests.Session()

    def get_random_user_agent(self):
        """
        Get a random User-Agent string for rotation.

        Returns:
            str: A random User-Agent header
        """
        return random.choice(self.USER_AGENTS)

    def get_headers(self):
        """
        Get headers with a rotated User-Agent.

        Returns:
            dict: HTTP headers with random User-Agent
        """
        return {
            "User-Agent": self.get_random_user_agent(),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
        }

    def get_soup(self, url, timeout=10):
        """
        Fetch a URL and return a BeautifulSoup object.

        Args:
            url (str): The URL to fetch
            timeout (int): Request timeout in seconds

        Returns:
            BeautifulSoup or dict: BeautifulSoup object if successful, else error dict
        """
        try:
            response = self.session.get(url, headers=self.get_headers(), timeout=timeout)
            
            if response.status_code != 200:
                return {"error": f"Failed to load page: {response.status_code}"}
            
            return BeautifulSoup(response.content, "html.parser")
        
        except requests.Timeout:
            return {"error": f"Request timeout after {timeout}s"}
        except requests.ConnectionError as e:
            return {"error": f"Connection error: {str(e)}"}
        except Exception as e:
            return {"error": f"Error fetching URL: {str(e)}"}

    def setup_playwright(self, headless=True):
        """
        Setup and return a Playwright browser instance.

        Args:
            headless (bool): Whether to run in headless mode

        Returns:
            playwright browser: Chromium browser instance
        """
        try:
            p = sync_playwright().start()
            browser = p.chromium.launch(headless=headless)
            return browser, p
        except Exception as e:
            print(f"❌ Error launching Playwright: {str(e)}")
            return None, None

    def log_error(self, message, error=None):
        """
        Log an error message (can be extended with file logging).

        Args:
            message (str): Error description
            error (Exception, optional): The exception object
        """
        if error:
            print(f"⚠️  {message}: {str(error)}")
        else:
            print(f"⚠️  {message}")
