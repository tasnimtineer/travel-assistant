"""
واجهة Streamlit للمساعد الإداري - تصميم مبسّط يشبه واجهة Claude (نظيف، أبيض، هادي).
"""

import os
import streamlit as st
from anthropic import Anthropic

from tools.definitions import TOOLS
from tools.executors import execute_tool

st.set_page_config(
    page_title="المساعد الإداري - شركة تنير للسفر والسياحة",
    page_icon="✈️",
    layout="centered",
)

# ---------------------------------------------------------------
# تصميم مبسّط: خلفية بيضاء، خط عربي واضح، فقاعات هادية، صندوق كتابة ثابت بالأسفل
# ---------------------------------------------------------------
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Tajawal', sans-serif !important;
        direction: rtl;
    }

    .stApp {
        background: #ffffff;
    }

    .main-header {
        text-align: center;
        padding: 0.5rem 0 1.5rem 0;
        border-bottom: 1px solid #eee;
        margin-bottom: 1rem;
    }
    .main-header h1 {
        color: #1a1a1a;
        font-size: 1.4rem;
        font-weight: 700;
        margin-bottom: 0.1rem;
    }
    .main-header p {
        color: #888;
        font-size: 0.85rem;
        margin-top: 0;
    }

    div[data-testid="stChatMessage"] {
        background: transparent;
        padding: 0.8rem 0.2rem;
        border-bottom: 1px solid #f2f2f2;
    }

    .stChatInput textarea {
        border-radius: 14px !important;
        border: 1px solid #ddd !important;
    }

    #MainMenu, footer, header {visibility: hidden;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="main-header">
        <h1>✈️ المساعد الإداري</h1>
        <p>شركة تنير للسفر والسياحة</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------
# منطق الاتصال بـ Claude (بدون تغيير)
# ---------------------------------------------------------------
api_key = os.environ.get("ANTHROPIC_API_KEY")

if not api_key:
    st.error("⚠️ لم يتم إعداد ANTHROPIC_API_KEY في Environment Variables.")
    st.stop()

client = Anthropic(api_key=api_key)
MODEL = "claude-sonnet-4-6"

SYSTEM_PROMPT = """أنت المساعد الإداري الذكي لشركة سفر وسياحة.
مهامك: إدخال بيانات العملاء، معالجة صور جواز السفر، تلخيص الأخبار اليومية،
البحث عن تذاكر الطيران، وإرسال الإيميلات والمساعدة عموما في امور السفر. تحدث بالعربية دائماً، وكن ودوداً ومهنياً."""

if "history" not in st.session_state:
    st.session_state.history = []

if not st.session_state.history:
    with st.chat_message("assistant", avatar="✈️"):
        st.write("أهلاً بك 👋 كيف أقدر أساعدك اليوم؟")

for msg in st.session_state.history:
    if msg["role"] == "user" and isinstance(msg["content"], str):
        with st.chat_message("user"):
            st.write(msg["content"])
    elif msg["role"] == "assistant":
        text = "".join(b.text for b in msg["content"] if getattr(b, "type", None) == "text")
        if text:
            with st.chat_message("assistant", avatar="✈️"):
                st.write(text)


def run_agent(user_message: str):
    st.session_state.history.append({"role": "user", "content": user_message})

    while True:
        response = client.messages.create(
            model=MODEL,
            max_tokens=1500,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=st.session_state.history,
        )
        st.session_state.history.append({"role": "assistant", "content": response.content})

        if response.stop_reason != "tool_use":
            return "".join(b.text for b in response.content if b.type == "text")

        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                with st.status(f"🔧 {block.name}", expanded=False):
                    result = execute_tool(block.name, block.input)
                tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": result})
        st.session_state.history.append({"role": "user", "content": tool_results})


user_input = st.chat_input("اكتب رسالتك هنا...")
if user_input:
    with st.chat_message("user"):
        st.write(user_input)
    with st.chat_message("assistant", avatar="✈️"):
        with st.spinner("جاري المعالجة..."):
            reply = run_agent(user_input)
        st.write(reply)
