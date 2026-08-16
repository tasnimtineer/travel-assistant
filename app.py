"""
واجهة Streamlit للمساعد الإداري - نسخة مجمّلة (تصميم عربي RTL، ألوان سفر، شريط جانبي).
جاهزة للنشر المجاني على Render / Streamlit Cloud.
"""

import os
import streamlit as st
from anthropic import Anthropic

from tools.definitions import TOOLS
from tools.executors import execute_tool

st.set_page_config(
    page_title="المساعد الإداري - شركة السفر والسياحة",
    page_icon="✈️",
    layout="centered",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------
# تنسيق عام: اتجاه عربي RTL، خط واضح، ألوان سفر (أزرق/ذهبي)، فقاعات محادثة
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
        background: linear-gradient(180deg, #0f2440 0%, #13315c 100%);
    }

    /* رأس الصفحة */
    .main-header {
        text-align: center;
        padding: 1.2rem 0 0.5rem 0;
    }
    .main-header h1 {
        color: #ffffff;
        font-size: 1.9rem;
        margin-bottom: 0.2rem;
    }
    .main-header p {
        color: #d4af37;
        font-size: 0.95rem;
        margin-top: 0;
    }

    /* صندوق المحادثة */
    section[data-testid="stChatMessageContainer"], .block-container {
        background: transparent;
    }

    div[data-testid="stChatMessage"] {
        border-radius: 16px;
        padding: 0.6rem 1rem;
        margin-bottom: 0.6rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.15);
    }

    /* فقاعة المستخدم */
    div[data-testid="stChatMessage"]:has(div[data-testid="chatAvatarIcon-user"]) {
        background: #d4af37;
    }
    div[data-testid="stChatMessage"]:has(div[data-testid="chatAvatarIcon-user"]) p {
        color: #0f2440 !important;
        font-weight: 500;
    }

    /* فقاعة المساعد */
    div[data-testid="stChatMessage"]:has(div[data-testid="chatAvatarIcon-assistant"]) {
        background: #ffffff;
    }
    div[data-testid="stChatMessage"]:has(div[data-testid="chatAvatarIcon-assistant"]) p {
        color: #13315c !important;
    }

    /* صندوق الكتابة */
    .stChatInput textarea {
        border-radius: 12px !important;
        border: 2px solid #d4af37 !important;
    }

    /* الشريط الجانبي */
    section[data-testid="stSidebar"] {
        background: #0a1a30;
    }
    section[data-testid="stSidebar"] * {
        color: #f0f0f0 !important;
    }

    #MainMenu, footer, header {visibility: hidden;}
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------
# الشريط الجانبي: هوية الشركة + المميزات + إعادة تعيين المحادثة
# ---------------------------------------------------------------
with st.sidebar:
    st.markdown("### ✈️ شركة السفر والسياحة")
    st.markdown("**المساعد الإداري الذكي**")
    st.markdown("---")
    st.markdown("#### 🧰 المميزات المتاحة")
    st.markdown(
        """
        - 📋 إدخال بيانات العملاء
        - 🖼️ معالجة صور جواز السفر
        - 📰 ملخص الأخبار اليومي
        - ✈️ البحث عن تذاكر الطيران
        - 📧 إرسال الإيميلات
        """
    )
    st.markdown("---")
    if st.button("🗑️ محادثة جديدة", use_container_width=True):
        st.session_state.history = []
        st.rerun()
    st.caption("نسخة تجريبية")

# ---------------------------------------------------------------
# رأس الصفحة
# ---------------------------------------------------------------
st.markdown(
    """
    <div class="main-header">
        <h1>✈️ المساعد الإداري</h1>
        <p>لشركة السفر والسياحة — مدعوم بالذكاء الاصطناعي</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------
# منطق الاتصال بـ Claude (بدون أي تغيير عن النسخة السابقة)
# ---------------------------------------------------------------
api_key = os.environ.get("ANTHROPIC_API_KEY")

if not api_key:
    st.error("⚠️ لم يتم إعداد ANTHROPIC_API_KEY في Environment Variables.")
    st.stop()

client = Anthropic(api_key=api_key)
MODEL = "claude-sonnet-4-6"

SYSTEM_PROMPT = """أنت المساعد الإداري الذكي لشركة سفر وسياحة.
مهامك: إدخال بيانات العملاء، معالجة صور جواز السفر، تلخيص الأخبار اليومية،
البحث عن تذاكر الطيران، وإرسال الإيميلات. تحدث بالعربية دائماً، وكن ودوداً ومهنياً."""

if "history" not in st.session_state:
    st.session_state.history = []

# رسالة ترحيب إذا المحادثة فاضية
if not st.session_state.history:
    with st.chat_message("assistant", avatar="✈️"):
        st.write("أهلاً بك! 👋 كيف أقدر أساعدك اليوم؟ (تسجيل بيانات عميل، معالجة صورة، أخبار، تذاكر طيران، أو إرسال إيميل)")

# عرض المحادثة السابقة
for msg in st.session_state.history:
    if msg["role"] == "user" and isinstance(msg["content"], str):
        with st.chat_message("user", avatar="🧑"):
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
                with st.status(f"🔧 تنفيذ: {block.name}", expanded=False):
                    result = execute_tool(block.name, block.input)
                tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": result})
        st.session_state.history.append({"role": "user", "content": tool_results})


user_input = st.chat_input("اكتب طلبك هنا... (مثال: سجل بيانات عميل اسمه أحمد)")
if user_input:
    with st.chat_message("user", avatar="🧑"):
        st.write(user_input)
    with st.chat_message("assistant", avatar="✈️"):
        with st.spinner("جاري المعالجة..."):
            reply = run_agent(user_input)
        st.write(reply)
