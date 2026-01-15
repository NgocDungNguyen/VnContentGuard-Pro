import google.generativeai as genai
import os
import re
import json
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")


class SentimentAnalyzer:
    def __init__(self):
        if not API_KEY:
            print("⚠️ No API Key for Sentiment!")
        else:
            genai.configure(api_key=API_KEY)
            self.model = genai.GenerativeModel("gemini-1.5-flash")

    def analyze(self, text):
        if not text:
            return {"label": "Neutral", "score": 0.0}

        try:
            # Ask Gemini to do the work. It is smarter than keywords.
            prompt = f"""
            Analyze the sentiment of this Vietnamese text: "{text[:1000]}"
            Classify as: Positive, Negative, or Neutral.
            Provide a confidence score (0.0 to 1.0).
            
            Return ONLY JSON:
            {{ "label": "String", "score": Float }}
            """

            response = self.model.generate_content(prompt)
            clean_res = re.sub(r"```json|```", "", response.text).strip()
            data = json.loads(clean_res)

            return {
                "label": data.get("label", "Neutral"),
                "score": data.get("score", 0.0),
            }
        except Exception as e:
            print(f"Sentiment Error: {e}")
            # Fallback
            return {"label": "Neutral", "score": 0.0}
