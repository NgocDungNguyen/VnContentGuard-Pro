import streamlit as st
import pandas as pd
import asyncio
import sys
import platform
import json

if platform.system() == "Windows":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from src.crawlers.news_crawler import NewsCrawler
from src.crawlers.social_crawler import SocialCrawler
from src.models.sentiment import SentimentAnalyzer
from src.models.toxicity import ToxicityAnalyzer
from src.models.gemini_llm import GeminiAgent

st.set_page_config(page_title="VnContentGuard Pro", page_icon="🛡️", layout="wide")
st.title("🛡️ VnContentGuard: Dashboard")

with st.sidebar:
    st.header("⚙️ Control Center")
    if st.button("🔄 Initialize System"):
        with st.spinner("Loading Modules..."):
            st.session_state["news_crawler"] = NewsCrawler()
            st.session_state["social_crawler"] = SocialCrawler()
            st.session_state["sentiment"] = SentimentAnalyzer()
            st.session_state["toxicity"] = ToxicityAnalyzer()
            st.session_state["gemini"] = GeminiAgent()
            st.success("✅ System Armed")
    st.divider()
    test_text = st.text_input("Test a phrase:", "DM")
    if st.button("Analyze Input"):
        if "toxicity" in st.session_state:
            res, count = st.session_state["toxicity"].analyze_comments([test_text])
            if res:
                r = res[0]
                if r["Is Toxic"]:
                    st.error(f"🔴 BLOCKED: {r['Category']}")
                    st.write(f"**Confidence:** {r['Confidence']}")
                else:
                    st.success(f"🟢 PASSED")
        else:
            st.error("⚠️ Initialize System First")

url = st.text_input("Target URL (News):", placeholder="https://vnexpress.net/...")
if st.button("🚀 Execute Scan"):
    if "toxicity" not in st.session_state:
        st.error("⚠️ Please Initialize System in Sidebar first.")
    else:
        tab1, tab2 = st.tabs(["📄 Content Analysis", "💬 Comment Scan"])

        with tab1:
            with st.spinner("Reading Content..."):
                data = st.session_state["news_crawler"].extract(url)
            if data.get("error"):
                st.error(data["error"])
            else:
                st.subheader(data["title"])
                st.markdown(f"_{data['content'][:500]}..._")
                st.markdown("---")
                c1, c2 = st.columns(2)
                c1.metric(
                    "Sentiment",
                    st.session_state["sentiment"].analyze(data["content"][:500])[
                        "label"
                    ],
                )
                with c2:
                    st.write("🕵️ **Fact Check:**")
                    fc = st.session_state["gemini"].check_fake_news(data["content"])
                    try:
                        st.json(json.loads(fc))
                    except:
                        st.info(fc)

        with tab2:
            with st.spinner("Scanning Comments..."):
                comments = st.session_state["social_crawler"].extract_comments(url)
            if not comments:
                st.warning("No comments found.")
            else:
                st.success(f"Scanned {len(comments)} comments.")
                results, count = st.session_state["toxicity"].analyze_comments(comments)
                if results:
                    df = pd.DataFrame(results)

                    def highlight_toxic(row):
                        return [
                            "background-color: #ffcdd2" if row["Is Toxic"] else ""
                            for _ in row
                        ]

                    st.dataframe(
                        df.style.apply(highlight_toxic, axis=1),
                        use_container_width=True,
                    )
                if count > 0:
                    st.error(f"⚠️ {count} Threats Detected!")
                else:
                    st.success("✅ Clean Comment Section")
