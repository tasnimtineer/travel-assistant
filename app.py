"""
واجهة Streamlit للمساعد الإداري - جاهزة للنشر المجاني على Hugging Face Spaces.
"""

import os
import streamlit as st
from anthropic import Anthropic

from tools.definitions import TOOLS
from tools.executors import execute_tool

st.set_page_config(page_title="المساعد الإداري - شركة السفر والسياحة", page_icon="✈️")

# المفتاح يُقرأ من Secrets الخاصة بـ Hugging Face Space (وليس مكتوباً بالكود أبداً)
api_key = os.environ.get("ANTHROPIC_API_KEY")

if not api_key:
    st.error("⚠️ لم يتم إعداد ANTHROPIC_API_KEY. أضيفيه من Settings → Repository secrets في الـ Space.")
    st.stop()

client = Anthropic(api_key=api_key)
MODEL = "claude-sonnet-4-6"

SYSTEM_PROMPT = """أنت المساعد الإداري الذكي لشركة سفر وسياحة.
مهامك: إدخال بيانات العملاء، معالجة صور جواز السفر، تلخيص الأخبار اليومية،
البحث عن تذاكر الطيران، وإرسال الإيميلات. تحدث بالعربية دائماً."""

st.title("✈️ المساعد الإداري لشركة السفر والسياحة")
st.caption("نسخة تجريبية مجانية")

if "history" not in st.session_state:
    st.session_state.history = []

# عرض المحادثة السابقة
for msg in st.session_state.history:
    if msg["role"] == "user" and isinstance(msg["content"], str):
        with st.chat_message("user"):
            st.write(msg["content"])
    elif msg["role"] == "assistant":
        text = "".join(b.text for b in msg["content"] if getattr(b, "type", None) == "text")
        if text:
            with st.chat_message("assistant"):
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
                with st.status(f"🔧 تنفيذ: {block.name}"):
                    result = execute_tool(block.name, block.input)
                tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": result})
        st.session_state.history.append({"role": "user", "content": tool_results})


user_input = st.chat_input("اكتب طلبك هنا... (مثال: سجل بيانات عميل اسمه أحمد)")
if user_input:
    with st.chat_message("user"):
        st.write(user_input)
    with st.chat_message("assistant"):
        with st.spinner("جاري المعالجة..."):
            reply = run_agent(user_input)
        st.write(reply)
