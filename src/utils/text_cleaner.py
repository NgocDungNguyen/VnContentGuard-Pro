import re

import emoji
from underthesea import text_normalize


class TextCleaner:
    # Vietnamese "Teen Code" dictionary for normalization
    TEEN_CODE_MAP = {
        # Common slang replacements
        "khum": "không",
        "kh": "không",
        "k": "không",
        "j": "gì",
        "vk": "vậy khác",
        "ck": "chứ khác",
        "mk": "mình",
        "cj": "cái gì",
        "dj": "đó",
        "sj": "sao",
        "tl": "trả lời",
        "rep": "trả lời",
        "nt": "note",
        "vs": "versus",
        "nó": "nó",
        "nó": "nó",
        "cx": "cũng",
        "thật": "thật",
        "hộp": "hộp",
        "hôm": "hôm",
        "bh": "bây giờ",
        "sao": "sao",
        "dc": "được",
        "đc": "được",
        "th": "thì",
        "ak": "à",
        "uk": "ừ",
        "hì": "hì",
        "hơi": "hơi",
        "giật": "giật",
        "vãi": "vãi",
        "ngu": "ngu",
        "nát": "nát",
        "thang": "thằng",
        "tàn": "tàn",
        "lmao": "cười",
        "lol": "cười",
        "omg": "ôi",
    }

    @staticmethod
    def normalize_teencode(text):
        """
        Replace Vietnamese teen code and slang with proper words.

        Args:
            text (str): Input text with teen code

        Returns:
            str: Text with teen code normalized
        """
        if not text:
            return ""

        words = text.split()
        normalized_words = []

        for word in words:
            lower_word = word.lower()
            # Check if word (or stripped punctuation) is in teen code map
            word_clean = re.sub(r"[^\w]", "", lower_word)

            if word_clean in TextCleaner.TEEN_CODE_MAP:
                normalized_words.append(TextCleaner.TEEN_CODE_MAP[word_clean])
            else:
                normalized_words.append(word)

        return " ".join(normalized_words)

    @staticmethod
    def normalize_accents(text):
        """
        Normalize Vietnamese accent inconsistencies (e.g., òa -> oà).

        Args:
            text (str): Input text with potential accent variations

        Returns:
            str: Text with normalized accents using underthesea
        """
        if not text:
            return ""

        # Use underthesea's text_normalize for Vietnamese accent normalization
        return text_normalize(text)

    @staticmethod
    def clean(text):
        """
        Comprehensive text cleaning pipeline.

        Args:
            text (str): Raw input text

        Returns:
            str: Cleaned and normalized text
        """
        if not text:
            return ""

        # 1. Remove Emojis
        text = emoji.replace_emoji(text, replace="")

        # 2. Normalize Vietnamese accents
        text = TextCleaner.normalize_accents(text)

        # 3. Normalize teen code to proper words
        text = TextCleaner.normalize_teencode(text)

        # 4. Remove URLs
        text = re.sub(r"http\S+", "", text)
        text = re.sub(r"www\.\S+", "", text)

        # 5. Remove email addresses
        text = re.sub(r"\S+@\S+", "", text)

        # 6. Remove extra spaces and newlines
        text = re.sub(r"\s+", " ", text).strip()

        # 7. Remove excessive punctuation repeats (!!!! -> !)
        text = re.sub(r"([!?.])\1{2,}", r"\1", text)

        return text


# Test it quickly
if __name__ == "__main__":
    raw = "Tin nóng!!! 🔥🔥 khum biết j vk. Click xem tại: http://fake.com.   Việt Nam vô địch!!!"
    print(f"Original: {raw}")
    cleaned = TextCleaner.clean(raw)
    print(f"Cleaned:  {cleaned}")

    # Test teen code specifically
    teen_text = "bh mk đang bh, sao bạn k rep tl j? cx dc vs dc j"
    print(f"\nTeen Code: {teen_text}")
    print(f"Normalized: {TextCleaner.normalize_teencode(teen_text)}")
