from playwright.sync_api import sync_playwright
import time
from bs4 import BeautifulSoup
from src.utils.text_cleaner import TextCleaner


class SocialCrawler:
    def extract_comments(self, url):
        comments = []

        with sync_playwright() as p:
            print(f"🕵️ Launching Ghost Browser for: {url}")
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            try:
                page.goto(url, timeout=60000)

                # 1. Scroll logic (VnExpress loads comments via AJAX)
                print("⬇️ Scrolling to load comments...")
                for _ in range(5):
                    page.mouse.wheel(0, 3000)  # Scroll deeper
                    time.sleep(1.5)  # Wait longer for AJAX

                # 2. Get HTML
                html = page.content()
                soup = BeautifulSoup(html, "html.parser")

                # 3. Extract text
                raw_texts = []

                # Specific selectors for Vietnamese sites
                selectors = [
                    ".comment_content",  # Generic
                    ".full_content",  # VnExpress specific
                    ".content_more",  # VnExpress specific
                    'div[data-component="comment"]',  # Facebook/Social
                ]

                for selector in selectors:
                    elements = soup.select(selector)
                    for el in elements:
                        raw_texts.append(el.get_text())

                # If specific selectors fail, grab all Paragraphs inside comment containers
                if not raw_texts:
                    comment_blocks = soup.select(
                        "#box_comment, .box-comment, .comments"
                    )
                    for block in comment_blocks:
                        ps = block.find_all("p")
                        for p_tag in ps:
                            raw_texts.append(p_tag.get_text())

                # 4. AGGRESSIVE CLEANING (Filter out UI noise)
                ignored_keywords = [
                    "Thích",
                    "Trả lời",
                    "Vi phạm",
                    "Chia sẻ",
                    "Đăng nhập",
                    "Bản quyền",
                    "VnExpress",
                    "Kinh doanh",
                    "Góc nhìn",
                    "Theo dõi",
                    "Quảng cáo",
                    "Liên hệ",
                ]

                for text in raw_texts:
                    clean_t = TextCleaner.clean(text)

                    # Filtering Logic
                    if len(clean_t) < 15:
                        continue  # Too short (e.g., "Đúng rồi")
                    if len(clean_t) > 1000:
                        continue  # Too long (likely an article part)

                    # Check if it contains UI keywords
                    is_noise = False
                    for kw in ignored_keywords:
                        if kw.lower() in clean_t.lower() and len(clean_t) < 50:
                            is_noise = True
                            break

                    if not is_noise:
                        comments.append(clean_t)

                # Remove duplicates
                comments = list(set(comments))

            except Exception as e:
                print(f"⚠️ Error crawling comments: {e}")
            finally:
                browser.close()

        return comments[:30]  # Limit to 30 to save AI processing time
