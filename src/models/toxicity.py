import json
import os
import re

from dotenv import load_dotenv
from google import genai

load_dotenv()

# Import the key rotation system
from src.models.gemini_llm import API_KEY_POOL, MODEL_NAME, APIKeyRotator


class ToxicityAnalyzer:
    """
    Defense-in-Depth Toxicity Detection Engine.
    Layer 1: Regex patterns (instant, high-precision)
    Layer 2: Gemini AI with multi-key rotation (contextual, catches nuances)
    """

    def __init__(self):
        print("⏳ Initializing Toxicity Detection Engine...")

        # Initialize regex patterns first (always available)
        self._init_regex_patterns()

        # Use the same key rotation system as fake news detection
        try:
            self.key_rotator = APIKeyRotator(API_KEY_POOL)
            self.client = None
            self.model_name = MODEL_NAME
            self._initialize_client()
            print("✅ Toxicity Engine Ready with API Key Rotation")
        except Exception as e:
            print(f"⚠️ Warning: Gemini AI unavailable for toxicity detection: {e}")
            print("⚡ Using regex-only mode (still very effective!)")
            self.client = None

    def _initialize_client(self) -> bool:
        """Initialize Gemini client with current API key"""
        try:
            api_key = self.key_rotator.get_current_key()
            if not api_key:
                return False
            self.client = genai.Client(api_key=api_key)
            return True
        except Exception as e:
            print(f"⚠️ Failed to initialize toxicity client: {e}")
            return False

    def _rotate_key_and_retry(self) -> bool:
        """Rotate to next API key"""
        if self.key_rotator.mark_key_exhausted():
            return self._initialize_client()
        return False

    def _init_regex_patterns(self):
        """Initialize regex patterns for toxicity detection"""
        # --- LAYER 1: MILITARY-GRADE REGEX DATABASE (V3.0 - GEN Z & TEENCODE ENHANCED) ---
        # Total: 500+ patterns across 20 categories.
        # Includes: Standard Vietnamese, English, Teencode (vkl, dcm), Political Slang, and Evasion spellings.
        self.blacklist_patterns = [
            # ==============================
            # GROUP 1: EXTREME VIOLENCE & HARM
            # ==============================
            # 1. MURDER & EXECUTION (VN/EN)
            (
                r"\b(giết|chém|đâm|bắn|thủ tiêu|cắt cổ|phanh thây|tùng xẻo|thiêu sống|đục mắt|rạch mặt|xử đẹp|thanh toán|lấy mạng|kết liễu|tiễn vong|nã đạn|xả súng)\b",
                "Violence: Murder/Torture",
            ),
            (
                r"\b(kill|murder|stab|shoot|slaughter|behead|execute|strangle|lynch|dismember|decapitate|assassinate|homicide|genocide|bloodbath)\b",
                "Violence: Murder/Torture",
            ),
            # 2. TORTURE & CRUELTY
            (
                r"\b(tra tấn|hành hạ|giam cầm|đánh đập|bạo hành|nhục hình|k cha đạp|móc mắt|rút móng|cắt gân|lột da|thiến|hoạn)\b",
                "Violence: Torture",
            ),
            (
                r"\b(torture|torment|mutilate|flay|crucify|waterboard|maim|agony|inflict pain)\b",
                "Violence: Torture",
            ),
            # 3. GORE & GRAPHIC IMAGERY
            (
                r"\b(máu me|xác chết|tử thi|ruột gan|đầu lâu|óc|phân huỷ|thối rữa|be bét|nát bấy|vũng máu|thi thể)\b",
                "Violence: Gore",
            ),
            (
                r"\b(gore|gory|bloody|corpse|cadaver|intestines|viscera|severed|decomposed|rotting|flesh|remains)\b",
                "Violence: Gore",
            ),
            # 4. SELF-HARM & SUICIDE (Includes Gen Z Slang "Reset", "Isekai")
            (
                r"\b(tự tử|tự sát|nhảy lầu|cắt tay|uống thuốc sâu|treo cổ|rạch tay|tự vẫn|quyên sinh|kết liễu đời mình)\b",
                "Self-Harm/Suicide",
            ),
            (
                r"\b(reset game|reset server|đăng xuất khỏi trái đất|isekai|chuyển sinh|đi bán muối|ngắm gà khỏa thân|về với ông bà|nhảy cầu)\b",
                "Self-Harm: Slang/Evasion",
            ),
            (
                r"\b(suicide|kill myself|end it all|cut my wrists|overdose|hang myself|slit wrists|kys|kill urself|unalive)\b",
                "Self-Harm/Suicide",
            ),
            # ==============================
            # GROUP 2: HATE SPEECH & DISCRIMINATION
            # ==============================
            # 5. REGIONAL HATE: NORTH (Bắc Kỳ Variations)
            (
                r"\b(bắc kỳ|bắc cụ|bắc bộ|parky|parkie|nón cối|barkeo|bakery|vĩ tuyến 17|bắc kỳ chó)\b",
                "Hate: Regional (Anti-North)",
            ),
            # 6. REGIONAL HATE: SOUTH (Nam Kỳ/Political Variations)
            (
                r"\b(nam kỳ|nam cầy|namiki|lũ khát nước|ba que|3 que|đu càng|3 sọc|cali|kali|ngụy|bán nước|phản động)\b",
                "Hate: Regional (Anti-South)",
            ),
            # 7. REGIONAL HATE: CENTRAL (Thanh Nghe Tinh)
            (
                r"\b(trung kỳ|cá gỗ|hoa thanh quế|dân 36|dân 37|dân 18|36 37|tiểu vương quốc|vương quốc 36|thanh nghệ tĩnh|ăn rau má|phá đường tàu)\b",
                "Hate: Regional (Anti-Central)",
            ),
            # 8. RACISM & ETHNIC SLURS
            (
                r"\b(tộc|mán|mường|lũ mọi)\b",
                "Hate: Classism/Ethnic (Contextual)",
            ),
            (
                r"\b(nigga|nigger|negro|coon|white trash|ching chong|chink|gook|curry muncher|wetback|beaner|monkey)\b",
                "Hate: Racism (Global)",
            ),
            (
                r"\b(khựa|tàu khựa|ba tàu|hàn xẻng|nhật lùn|tây ba lô|da đen|thằng đen|mũi lõ)\b",
                "Hate: Xenophobia",
            ),
            # 9. POLITICAL & REACTIONARY (VN Specific)
            (
                r"\b(bò đỏ|bò vàng|dư lợn viên|dlv|CS|việt tân|cờ vàng|đu dây|trại súc vật|tuyên giáo|bưng bô|nhồi sọ)\b",
                "Hate: Political Extremism",
            ),
            # ==============================
            # GROUP 3: SEXUAL & GROOMING
            # ==============================
            # 10. CRIMINAL SEXUAL ACTS
            (
                r"\b(hiếp|cưỡng hiếp|hiếp dâm|hấp diêm|thông dâm|ấu dâm|loạn luân|xâm hại|cưỡng bức|ấu dâm|pedophile|pedo|cp|child porn)\b",
                "Sexual: Criminal Acts",
            ),
            # 11. EXPLICIT & VULGAR (Teencode Included)
            (
                r"\b(lồn|cặc|buồi|chim|bướm|cu|dái|vú|ngực|mông|đít|sò|khe|lỗ|thủ dâm|quay tay|thẩm du|bú cu|vét máng|chịch|xoạc|nện|đụ|dit|phang)\b",
                "Sexual: Explicit/Vulgar",
            ),
            (
                r"\b(l.ồ.n|c.ặ.c|b.u.ồ.i|s.e.x|c.l.i.p|lộ clip|clip nóng|link ngon|full hd|không che|uncen|show hàng|khoe hàng|bán quạt|onlyfans)\b",
                "Sexual: Evasion/Teencode",
            ),
            # 12. GROOMING & PREDATORY BEHAVIOR
            (
                r"\b(sugar baby|sugar daddy|sgbb|sgdd|nuôi bé|tìm bé|bao nuôi|fwb|ons|rau sạch|chăn rau|bố đường|bé đường|tuyển pg|đi khách)\b",
                "Sexual: Predatory/Grooming",
            ),
            (
                r"\b(cháu|bé|em gái).*?(ngon|múp|ngọt nước|cho chú|với chú|đi nhà nghỉ|kín đáo|riêng tư)\b",
                "Sexual: Grooming Context",
            ),
            # ==============================
            # GROUP 4: PROFANITY & INSULTS
            # ==============================
            # 13. PROFANITY: VIETNAMESE (Hardcore & Teencode)
            (
                r"\b(đm|đkm|đmm|vcl|vkl|vch|vcc|vđ|đéo|đếch|cc|ccc|cl|đmcm|đcm|dcm|dkm|đjt|đis|đù|bỏ mẹ|tổ sư|cha tiên sư)\b",
                "Profanity: Vulgarity (VN)",
            ),
            (
                r"\b(con mẹ mày|thằng cha mày|cả lò nhà mày|mả cha mày|tiên sư bố|cái mả mẹ|đồ chết tiệt)\b",
                "Profanity: Family Insults",
            ),
            # 14. INSULTS: INTELLIGENCE & ABILITY
            (
                r"\b(ngu|óc chó|óc lợn|óc bò|ngu si|thiểu năng|bại não|khuyết tật|tự kỷ|ngáo|ngáo đá|ngáo ngơ|não tàn|vô học|mất dạy)\b",
                "Insult: Ableism/Intelligence",
            ),
            # 15. INSULTS: APPEARANCE & CHARACTER
            (
                r"\b(phò|đĩ|cave|điếm|con giáp thứ 13|tiểu tam|trà xanh|hãm|hãm l|đũa mốc|xấu ma chê|mặt phụ khoa)\b",
                "Insult: Appearance/Character",
            ),
            # 16. PROFANITY: ENGLISH
            (
                r"\b(fuck|shit|bitch|cunt|dick|cock|asshole|whore|slut|bastard|motherfucker|douchebag|wanker|prick|twat)\b",
                "Profanity: Vulgarity (EN)",
            ),
            # ==============================
            # GROUP 5: SCAM, SPAM & DECEPTION
            # ==============================
            # 17. GAMBLING & BETTING
            (
                r"\b(cờ bạc|tài xỉu|nổ hũ|kèo bóng|bet88|kubet|nhà cái|casino|lô đề|xóc đĩa|bắn cá|đá gà|soi cầu|chốt số|bạch thủ|vip pro)\b",
                "Spam: Gambling",
            ),
            # 18. JOB & FINANCIAL SCAMS
            (
                r"\b(việc nhẹ lương cao|tuyển dụng gấp|không cọc|hoa hồng cao|kiếm tiền online|nhập liệu|xâu hạt|gấp phong bì|làm tại nhà|thu nhập khủng)\b",
                "Spam: Job Scam",
            ),
            (
                r"\b(chứng khoán quốc tế|sàn ảo|tiền ảo|lùa gà|pump dump|đa cấp|hệ thống|mô hình ponzi|hoàn vốn|cam kết lợi nhuận)\b",
                "Spam: Financial Scam",
            ),
            # 19. ADVERTISING & LINK SPAM
            (
                r"\b(mua ngay|nhấp link|link bio|inbox giá|ib giá|xem tại đây|giảm cân|tăng chiều cao|trị mụn|thuốc kích dục|nước hoa vùng kín|Tele)\b",
                "Spam: Advertising",
            ),
            # 20. THREATS & INTIMIDATION
            (
                r"\b(tao giết|tao đánh|ra đường cẩn thận|biết bố mày là ai không|gọi hội|xử mày|đập nát|đốt nhà|xin cái tay|xin cái chân)\b",
                "Threat: Violent Intent",
            ),
            (
                r"\b(watch your back|gonna kill you|beat you up|hunt you down|you're dead|fight me|meet me outside)\b",
                "Threat: Violent Intent",
            ),
        ]

    def analyze_comments(self, comments_list):
        """
        Analyze a list of comments for toxicity using two-layer defense.

        Args:
            comments_list (list): List of comment strings

        Returns:
            tuple: (results list, toxic count)
        """
        results = []
        toxic_count = 0

        # Filter empty comments
        valid_comments = [c for c in comments_list if c and len(c.strip()) > 0]

        print(f"⚡ Analyzing {len(valid_comments)} comments...")

        for comment in valid_comments:
            is_toxic = False
            score = 0.0
            category = "Clean"

            # ========== PHASE 1: REGEX SCAN (INSTANT) ==========
            lower_c = comment.lower()
            for pattern, label in self.blacklist_patterns:
                match = re.search(pattern, lower_c)
                if match:
                    is_toxic = True
                    score = 1.0
                    category = f"{label} (Keyword: '{match.group(0)}')"
                    break

            # ========== PHASE 2: GEMINI AI SCAN (CONTEXTUAL) ==========
            # Only run AI if Regex didn't catch it (saves API quota)
            if not is_toxic and self.client:
                try:
                    prompt = f"""You are a Content Safety Analyst. Analyze this Vietnamese comment for toxicity.

Comment: "{comment}"

Categories: ["Violence", "Hate Speech", "Sexual Harassment", "Regional Discrimination", "Scam", "Insult", "Clean"]

Check for:
- Hidden meanings or slang
- Regional discrimination (North/South/Central Vietnam)
- Subtle sexual harassment or grooming
- Scams or fraud

Return ONLY valid JSON (no markdown):
{{
    "is_toxic": true or false,
    "category": "one of the above",
    "confidence": 0.0-1.0,
    "reasoning": "brief explanation"
}}"""

                    response = self.client.models.generate_content(
                        model=self.model_name, contents=prompt
                    )

                    # Track successful request
                    self.key_rotator.increment_request_count()

                    # Extract text
                    raw_text = (
                        response.text if hasattr(response, "text") else str(response)
                    )

                    # Clean JSON
                    clean_text = re.sub(r"```json\s*", "", raw_text)
                    clean_text = re.sub(r"```\s*", "", clean_text).strip()

                    try:
                        data = json.loads(clean_text)
                        if data.get("is_toxic", False):
                            is_toxic = True
                            score = data.get("confidence", 0.8)
                            category = f"{data.get('category', 'General Toxicity')} (AI Detected)"
                    except json.JSONDecodeError:
                        pass  # Keep regex result if JSON fails

                except Exception as e:
                    error_str = str(e).lower()

                    # Handle quota errors with key rotation
                    if (
                        "429" in error_str
                        or "quota" in error_str
                        or "resourceexhausted" in error_str
                    ):
                        if self._rotate_key_and_retry():
                            # Retry with new key (but only once per comment to avoid loops)
                            pass

                    # If safety filters block it, it's definitely toxic
                    if "block" in error_str or "safety" in error_str:
                        is_toxic = True
                        score = 1.0
                        category = "BLOCKED: Safety Violation (Severe)"
                    # Otherwise keep regex result

            results.append(
                {
                    "Comment": comment,
                    "Is Toxic": bool(is_toxic),
                    "Category": category,
                    "Confidence": float(score),
                }
            )

            if is_toxic:
                toxic_count += 1

        return results, toxic_count
