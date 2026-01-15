import json
import os
import re

import google.generativeai as genai
from dotenv import load_dotenv

# Load API Key
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

# Model fallback chain - ordered by preference (only verified available models)
MODEL_FALLBACK_CHAIN = [
    "gemini-2.0-flash",  # Latest flash model (2025)
    "gemini-2.0-flash-lite",  # Lightweight variant
    "gemini-2.0-pro",  # Pro model
    "gemini-1.5-flash",  # Reliable older model
    "gemini-1.5-pro",  # Pro older model
    "gemini-pro",  # Legacy fallback
]


class GeminiAgent:
    def __init__(self):
        if not API_KEY:
            raise ValueError("❌ No API Key found in .env file!")

        genai.configure(api_key=API_KEY)

        # Try models in fallback order
        self.model = None
        self.current_model_name = None
        self.failed_models = set()
        self.retry_count = 0  # Track retry attempts
        self.max_retries = 5  # Prevent infinite loops

        for model_name in MODEL_FALLBACK_CHAIN:
            try:
                test_model = genai.GenerativeModel(model_name)
                self.model = test_model
                self.current_model_name = model_name
                print(f"✅ Using model: {model_name}")
                break
            except Exception as e:
                self.failed_models.add(model_name)
                print(f"⚠️  {model_name} not available: {e}")
                continue

        if not self.model:
            raise ValueError("❌ No Gemini models available!")

    def _try_next_model(self, skip_current=True):
        """
        Switch to the next available model in the fallback chain.

        Args:
            skip_current (bool): If True, skip the current model

        Returns:
            bool: True if successfully switched to a new model, False if no models left
        """
        for model_name in MODEL_FALLBACK_CHAIN:
            # Skip the current model and previously failed models
            if skip_current and model_name == self.current_model_name:
                continue
            if model_name in self.failed_models:
                continue

            try:
                new_model = genai.GenerativeModel(model_name)
                self.model = new_model
                self.current_model_name = model_name
                print(f"🔄 Switched to model: {model_name}")
                return True
            except Exception as e:
                self.failed_models.add(model_name)
                print(f"⚠️  Failed to switch to {model_name}: {e}")
                continue

        return False

    def check_fake_news(self, article_text):
        """
        Analyze article for misinformation with 2026 date context.
        Automatically falls back to alternative models if quota exceeded.

        Args:
            article_text (str): The article text to analyze

        Returns:
            str: JSON string with analysis results
        """
        if not self.model:
            return '{"risk_score": 0, "verdict": "Service Unavailable", "summary": "Model not loaded"}'

        # CRITICAL: Inject 2026 date context to prevent false positives on future events
        prompt = f"""You are a professional Fact Checker specializing in Vietnamese content.

ESSENTIAL CONTEXT: Today is January 15, 2026.
- Events from 2024-2025 are HISTORICAL FACTS - evaluate them normally
- Events dated 2026 are CURRENT or FUTURE - do NOT automatically flag them as fake
- Accept 2026 events as potentially legitimate unless they contradict known facts

ARTICLE TO ANALYZE:
"{article_text[:2000]}"

TASK:
1. Assess if this content is reliable, opinionated, or misinformation
2. Consider the 2026 date context - do not penalize future-dated claims
3. Provide a 1-sentence summary

RESPONSE (VALID JSON ONLY, NO MARKDOWN):
{{
    "risk_score": (1-10 integer, 1=Safe, 10=Definitely Fake),
    "verdict": ("Reliable", "Opinion Piece", or "Likely Fake"),
    "summary": "One sentence assessment"
}}"""

        try:
            response = self.model.generate_content(prompt)
            raw_text = response.text

            # Clean markdown formatting if present
            clean_text = re.sub(r"```json\s*", "", raw_text)  # Remove ```json
            clean_text = re.sub(r"```\s*", "", clean_text)  # Remove trailing ```
            clean_text = clean_text.strip()

            # Validate JSON before returning
            try:
                json.loads(clean_text)  # Test if valid JSON
                return clean_text
            except json.JSONDecodeError:
                # If JSON is invalid, try to extract it
                return self._extract_json(clean_text)

        except Exception as e:
            error_msg = str(e).lower()
            error_full = str(e)
            print(f"❌ Current model ({self.current_model_name}) error: {error_full}")

            # Check if it's a quota/rate limit error
            is_quota_error = (
                "429" in error_full
                or "quota" in error_msg
                or "exceeded" in error_msg
                or "rate limit" in error_msg
                or "too many requests" in error_msg
            )

            # If quota error, try next model
            if is_quota_error:
                print(
                    f"⚠️  Quota limit reached for {self.current_model_name}. Trying alternative models..."
                )

                # Mark current model as failed to prevent infinite loop
                self.failed_models.add(self.current_model_name)
                print(
                    f"🚫 Marked {self.current_model_name} as failed (quota exhausted)"
                )

                # Increment retry counter
                self.retry_count += 1

                # Check if we've exceeded max retries
                if self.retry_count > self.max_retries:
                    print(f"❌ Max retries ({self.max_retries}) exceeded!")
                    raise Exception(
                        "All Gemini models have exceeded their quota limits. Please try again later."
                    )

                if self._try_next_model(skip_current=True):
                    print(
                        f"🔄 Retrying with {self.current_model_name}... (Attempt {self.retry_count}/{self.max_retries})"
                    )
                    # Recursively retry with new model
                    return self.check_fake_news(article_text)
                else:
                    print("❌ All models exhausted their quota!")
                    raise Exception(
                        "All Gemini models have exceeded their quota limits. Please try again later."
                    )

            # If it's not a quota error, just re-raise
            raise e

    def _extract_json(self, text):
        """
        Attempt to extract valid JSON from malformed responses.

        Args:
            text (str): Response text that may contain JSON

        Returns:
            str: Valid JSON string or error response
        """
        try:
            # Find JSON object boundaries
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                json_str = text[start:end]
                json.loads(json_str)  # Validate
                return json_str
        except:
            pass

        # Return safe default if extraction fails
        return '{"risk_score": 5, "verdict": "Unable to process", "summary": "Could not analyze content"}'


if __name__ == "__main__":
    agent = GeminiAgent()
    if agent.model:
        test_result = agent.check_fake_news(
            "Công ty XYZ sẽ phát hành sản phẩm mới vào tháng 6 năm 2026."
        )
        print("Test Result:", test_result)
