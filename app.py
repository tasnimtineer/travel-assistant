"""
واجهة Streamlit النهائية للمساعد الإداري - شركة تنير للسفر والسياحة.
- تصميم مبسّط أنيق (يشبه Claude)
- حفظ دائم للمحادثات بقاعدة البيانات
- يدعم إرسال الصور فعلياً لكلود (مش بس عرضها)
- موديل محدّث + system prompt مفصّل + معالجة أخطاء + تقليم للمحادثة الطويلة
"""

import os
import json
import base64
import mimetypes
import streamlit as st
from anthropic import Anthropic, APIError, APIConnectionError, RateLimitError

from tools.definitions import TOOLS
from tools.executors import execute_tool
from database import get_session, Conversation, init_db

init_db()

st.set_page_config(
    page_title="المساعد الإداري - شركة تنير للسفر والسياحة",
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
# إعدادات عامة
# ---------------------------------------------------------------
MODEL = "claude-sonnet-5"          # الموديل الحالي الأحدث في فئة Sonnet
MAX_TOKENS = 4096                  # كانت 1500 - قليلة جداً لمهام فيها tools
MAX_HISTORY_MESSAGES = 40          # سقف لعدد الرسائل المُرسلة للـ API عشان الكونتكست ما يكبرش من غير حد

SYSTEM_PROMPT = """أنتِ المساعدة الإدارية الذكية لشركة "تنير للسفر والسياحة".

# دورك
تساعدين فريق الشركة في: إدخال بيانات العملاء في قاعدة البيانات الداخلية، معالجة وقراءة
صور جوازات السفر، تلخيص أخبار السفر والطيران والعمرة، البحث عن تذاكر الطيران، وصياغة
وإرسال الإيميلات للعملاء والموردين.

# قواعد استخدام الأدوات (Tools)
- لا تخمّني بيانات ناقصة (رقم جواز، تاريخ ميلاد، اسم مطار). لو المعلومة غير مؤكدة، اسألي
  المستخدمة قبل تنفيذ أي إجراء يعتمد عليها.
- قبل تنفيذ أي إجراء لا يمكن التراجع عنه (إرسال إيميل فعلي، حفظ بيانات نهائي)، اعرضي
  ملخص لما ستفعلينه واطلبي تأكيد صريح، إلا إذا طلبت المستخدمة التنفيذ المباشر بوضوح.
- عند معالجة صورة جواز سفر: تأكدي من وضوح البيانات المطلوبة (الاسم، الرقم، تاريخ
  الانتهاء) قبل تثبيتها، ونبّهي لو الصورة غير واضحة بدل التخمين.
- لو الأداة المطلوبة غير متاحة أو فشلت، وضّحي هذا صراحة للمستخدمة بدل تأليف نتيجة.

# أسلوب الرد
- تحدثي بالعربية دائماً إلا إذا طلبت المستخدمة غير ذلك.
- كوني ودودة ومهنية، وباختصار مباشر - بدون حشو أو مقدمات طويلة.
- في المهام المركبة، رتّبي خطواتك بوضوح (نقاط أو أرقام) بدل فقرة طويلة متصلة.
- إذا كان الطلب غامضاً، اسألي سؤال توضيحي واحد محدد بدل الافتراض العشوائي.
"""

# ---------------------------------------------------------------
# حفظ/تحميل المحادثات من قاعدة البيانات
# ---------------------------------------------------------------
def _extract_text(content):
    """يسحب النص فقط من محتوى قد يكون str أو قائمة content blocks."""
    if isinstance(content, str):
        return content
    parts = []
    for b in content:
        btype = b.get("type") if isinstance(b, dict) else getattr(b, "type", None)
        if btype == "text":
            parts.append(b.get("text") if isinstance(b, dict) else b.text)
    return "".join(parts)


def save_conversation(conversation_id, history):
    session = get_session()
    try:
        serializable = []
        for msg in history:
            text = _extract_text(msg["content"])
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
# الشريط الجانبي
# ---------------------------------------------------------------
with st.sidebar:
    st.markdown("### ✈️ المساعد الإداري")
    if st.button("➕ محادثة جديدة", use_container_width=True):
        st.session_state.history = []
        st.session_state.conversation_id = None
        st.session_state.pending_image_b64 = None
        st.rerun()

    st.markdown("---")
    st.markdown("#### 🕑 المحادثات السابقة")
    for conv_id, conv_title in load_conversation_list():
        if st.button(conv_title or "محادثة", key=f"conv_{conv_id}", use_container_width=True):
            st.session_state.history = load_conversation(conv_id)
            st.session_state.conversation_id = conv_id
            st.session_state.pending_image_b64 = None
            st.rerun()

st.markdown(
    """<div class="main-header"><h1>✈️ المساعد الإداري</h1><p>شركة تنير للسفر والسياحة</p></div>""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------
# رفع صورة - وتجهيزها فعلياً عشان تتبعت لكلود
# ---------------------------------------------------------------
if "pending_image_b64" not in st.session_state:
    st.session_state.pending_image_b64 = None
if "pending_image_media_type" not in st.session_state:
    st.session_state.pending_image_media_type = None

uploaded_file = st.file_uploader("📎 ارفع صورة هنا لو حابة تعدّليها أو تستخرجي بيانات منها", type=["jpg", "jpeg", "png"])
if uploaded_file is not None:
    raw_bytes = uploaded_file.getbuffer()
    media_type = mimetypes.guess_type(uploaded_file.name)[0] or "image/jpeg"
    st.session_state.pending_image_b64 = base64.standard_b64encode(bytes(raw_bytes)).decode("utf-8")
    st.session_state.pending_image_media_type = media_type
    st.image(uploaded_file, caption="الصورة المرفوعة - جاهزة للإرسال مع رسالتك التالية", width=150)
    st.caption("✅ اكتبي مثلاً: استخرج بيانات جواز السفر من هذي الصورة")

# ---------------------------------------------------------------
# الاتصال بـ Claude
# ---------------------------------------------------------------
api_key = os.environ.get("ANTHROPIC_API_KEY")
if not api_key:
    st.error("⚠️ لم يتم إعداد ANTHROPIC_API_KEY.")
    st.stop()

client = Anthropic(api_key=api_key)

if "history" not in st.session_state:
    st.session_state.history = []
if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = None

if not st.session_state.history:
    with st.chat_message("assistant", avatar="✈️"):
        st.write("أهلاً بك 👋 كيف أقدر أساعدك اليوم؟")

for msg in st.session_state.history:
    if msg["role"] == "user":
        text = _extract_text(msg["content"])
        if text:
            with st.chat_message("user"):
                st.write(text)
    elif msg["role"] == "assistant":
        text = _extract_text(msg["content"])
        if text:
            with st.chat_message("assistant", avatar="✈️"):
                st.write(text)


def build_user_content(text: str):
    """يبني محتوى الرسالة، ويرفق الصورة المعلّقة (لو موجودة) فعلياً مع النص."""
    content = []
    if st.session_state.pending_image_b64:
        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": st.session_state.pending_image_media_type,
                "data": st.session_state.pending_image_b64,
            },
        })
        # نمسحها بعد الاستخدام عشان ما تتكررش في كل رسالة جاية
        st.session_state.pending_image_b64 = None
        st.session_state.pending_image_media_type = None
    content.append({"type": "text", "text": text})
    return content


def trimmed_history():
    """يرسل آخر MAX_HISTORY_MESSAGES رسالة فقط للـ API عشان الكونتكست ما يكبرش من غير حد."""
    return st.session_state.history[-MAX_HISTORY_MESSAGES:]


def run_agent(user_message: str):
    st.session_state.history.append({"role": "user", "content": build_user_content(user_message)})

    while True:
        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                messages=trimmed_history(),
            )
        except RateLimitError:
            return "⚠️ في ضغط على الخدمة حالياً، جربي بعد شوية من فضلك."
        except APIConnectionError:
            return "⚠️ فيه مشكلة اتصال بالشبكة، تأكدي من الإنترنت وحاولي تاني."
        except APIError as e:
            return f"⚠️ حصل خطأ من الخدمة: {e}"

        st.session_state.history.append({"role": "assistant", "content": response.content})

        if response.stop_reason != "tool_use":
            return "".join(b.text for b in response.content if b.type == "text")

        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                with st.status(f"🔧 {block.name}", expanded=False):
                    try:
                        result = execute_tool(block.name, block.input)
                    except Exception as e:
                        result = f"فشل تنفيذ الأداة: {e}"
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

    st.session_state.conversation_id = save_conversation(
        st.session_state.conversation_id, st.session_state.history
    )
