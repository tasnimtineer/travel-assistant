"""
واجهة Streamlit النهائية للمساعد الإداري.
- تصميم مبسّط أنيق (يشبه Claude)
- حفظ دائم للمحادثات بقاعدة البيانات (يمكن الرجوع لها لاحقاً، زي Claude بالضبط)
"""

import os
import json
import streamlit as st
from anthropic import Anthropic

from tools.definitions import TOOLS
from tools.executors import execute_tool
from database import get_session, Conversation, init_db

init_db()

st.set_page_config(
    page_title="المساعد الإداري - شركة السفر والسياحة",
    page_icon="✈️",
    layout="centered",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700&display=swap');
    html, body, [class*="css"] { font-family: 'Tajawal', sans-serif !important; direction: rtl; }
    .stApp { background: #ffffff; }
    .main-header { text-align: center; padding: 0.5rem 0 1.5rem 0; border-bottom: 1px solid #eee; margin-bottom: 1rem; }
    .main-header h1 { color: #1a1a1a; font-size: 1.4rem; font-weight: 700; margin-bottom: 0.1rem; }
    .main-header p { color: #888; font-size: 0.85rem; margin-top: 0; }
    div[data-testid="stChatMessage"] { background: transparent; padding: 0.8rem 0.2rem; border-bottom: 1px solid #f2f2f2; }
    .stChatInput textarea { border-radius: 14px !important; border: 1px solid #ddd !important; }
    #MainMenu, footer, header {visibility: hidden;}
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------
# حفظ/تحميل المحادثات من قاعدة البيانات
# ---------------------------------------------------------------
def save_conversation(conversation_id, history):
    """يحفظ المحادثة كاملة بقاعدة البيانات (بشكل قابل للاسترجاع لاحقاً)."""
    session = get_session()
    try:
        serializable = []
        for msg in history:
            content = msg["content"]
            if isinstance(content, str):
                serializable.append({"role": msg["role"], "content": content})
            else:
                text = "".join(getattr(b, "text", "") for b in content if getattr(b, "type", None) == "text")
                if text:
                    serializable.append({"role": msg["role"], "content": text})

        title = serializable[0]["content"][:50] if serializable else "محادثة جديدة"

        if conversation_id:
            conv = session.get(Conversation, conversation_id)
            if conv:
                conv.messages_json = json.dumps(serializable, ensure_ascii=False)
                session.commit()
                return conversation_id

        conv = Conversation(title=title, messages_json=json.dumps(serializable, ensure_ascii=False))
        session.add(conv)
        session.commit()
        return conv.id
    finally:
        session.close()


def load_conversation_list():
    session = get_session()
    try:
        convs = session.query(Conversation).order_by(Conversation.updated_at.desc()).limit(20).all()
        return [(c.id, c.title) for c in convs]
    finally:
        session.close()


def load_conversation(conversation_id):
    session = get_session()
    try:
        conv = session.get(Conversation, conversation_id)
        if conv:
            return json.loads(conv.messages_json)
        return []
    finally:
        session.close()


# ---------------------------------------------------------------
# الشريط الجانبي: المحادثات السابقة (زي Claude بالضبط)
# ---------------------------------------------------------------
with st.sidebar:
    st.markdown("### ✈️ المساعد الإداري")
    if st.button("➕ محادثة جديدة", use_container_width=True):
        st.session_state.history = []
        st.session_state.conversation_id = None
        st.rerun()

    st.markdown("---")
    st.markdown("#### 🕑 المحادثات السابقة")
    for conv_id, conv_title in load_conversation_list():
        if st.button(conv_title or "محادثة", key=f"conv_{conv_id}", use_container_width=True):
            st.session_state.history = load_conversation(conv_id)
            st.session_state.conversation_id = conv_id
            st.rerun()

st.markdown(
    """<div class="main-header"><h1>✈️ المساعد الإداري</h1><p>شركة السفر والسياحة</p></div>""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------
# رفع صورة لمعالجتها (صورة جواز سفر مثلاً) - اختياري
# ---------------------------------------------------------------
uploaded_file = st.file_uploader("📎 ارفع صورة هنا لو حابة تعدّليها (اختياري)", type=["jpg", "jpeg", "png"])
uploaded_image_path = None
if uploaded_file is not None:
    os.makedirs("/tmp/uploads", exist_ok=True)
    uploaded_image_path = f"/tmp/uploads/{uploaded_file.name}"
    with open(uploaded_image_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    st.image(uploaded_file, caption="الصورة المرفوعة", width=150)
    st.caption(f"✅ جاهزة — اكتبي مثلاً: عدّل هذي الصورة لمقاس جواز سفر")

# ---------------------------------------------------------------
# الاتصال بـ Claude
# ---------------------------------------------------------------
api_key = os.environ.get("ANTHROPIC_API_KEY")
if not api_key:
    st.error("⚠️ لم يتم إعداد ANTHROPIC_API_KEY.")
    st.stop()

client = Anthropic(api_key=api_key)
MODEL = "claude-sonnet-4-6"

SYSTEM_PROMPT = """أنت المساعد الإداري الذكي لشركة سفر وسياحة.
مهامك: إدخال بيانات العملاء (بقاعدة بياناتنا الداخلية فقط)، معالجة صور جواز السفر،
تلخيص أخبار السفر والطيران والعمرة، البحث عن تذاكر الطيران، وإرسال الإيميلات.
تحدث بالعربية دائماً، وكن ودوداً ومهنياً."""

if "history" not in st.session_state:
    st.session_state.history = []
if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = None

if not st.session_state.history:
    with st.chat_message("assistant", avatar="✈️"):
        st.write("أهلاً بك 👋 كيف أقدر أساعدك اليوم؟")

for msg in st.session_state.history:
    if msg["role"] == "user" and isinstance(msg["content"], str):
        with st.chat_message("user"):
            st.write(msg["content"])
    elif msg["role"] == "assistant":
        content = msg["content"]
        if isinstance(content, str):
            text = content
        else:
            text = "".join(getattr(b, "text", "") for b in content if getattr(b, "type", None) == "text")
        if text:
            with st.chat_message("assistant", avatar="✈️"):
                st.write(text)


def run_agent(user_message: str):
    st.session_state.history.append({"role": "user", "content": user_message})

    while True:
        response = client.messages.create(
            model=MODEL, max_tokens=1500, system=SYSTEM_PROMPT,
            tools=TOOLS, messages=st.session_state.history,
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

    # حفظ دائم للمحادثة بقاعدة البيانات بعد كل رد
    st.session_state.conversation_id = save_conversation(
        st.session_state.conversation_id, st.session_state.history
    )
