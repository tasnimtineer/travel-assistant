"""
التنفيذ الفعلي الكامل لكل أداة:
- add_customer_data      -> قاعدة بيانات SQLite/Postgres حقيقية (database.py)
- resize_image            -> مكتبة Pillow
- summarize_daily_news    -> NewsAPI + تلخيص عبر Claude نفسه
- search_flights          -> Amadeus API (تجريبي مجاني)
- send_email              -> SMTP (Gmail/أي مزوّد)

كل دالة معلّمة بمكان وضع المفتاح السري المطلوب في .env
"""

import os
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from PIL import Image

from database import get_session, Customer, init_db
from tools.id_photo_processor import resize_image  # معالجة صور جواز السفر (35x45mm، خلفية بيضاء، تحسين عام)
from tools.daily_intelligence import generate_daily_intelligence_report  # تقرير الاستخبارات اليومي الشامل

init_db()

# ---------------------------------------------------------------
# 1) إدخال بيانات العملاء - قاعدة بيانات حقيقية
# ---------------------------------------------------------------
def add_customer_data(input_data: dict) -> str:
    session = get_session()
    try:
        customer = Customer(
            name=input_data.get("name"),
            phone=input_data.get("phone"),
            email=input_data.get("email"),
            booking_details=input_data.get("booking_details"),
        )
        session.add(customer)
        session.commit()
        return f"تم حفظ بيانات العميل '{customer.name}' بنجاح برقم مرجعي #{customer.id}."
    except Exception as e:
        session.rollback()
        return f"حدث خطأ أثناء حفظ البيانات: {e}"
    finally:
        session.close()


# ---------------------------------------------------------------
# 2) تعديل الصور -> مستوردة من tools/id_photo_processor.py
# ---------------------------------------------------------------


# ---------------------------------------------------------------
# 3) ملخص الأخبار اليومي - NewsAPI (newsapi.org، مفتاح مجاني)
# ---------------------------------------------------------------
def summarize_daily_news(input_data: dict) -> str:
    # لو ما حدد المستخدم موضوع، نركز افتراضياً على سفر/طيران/عمرة/شركات سودانية
    topic = input_data.get("topic") or "سفر طيران عمرة تاركو بدر السودانية للطيران"
    api_key = os.environ.get("NEWS_API_KEY")

    if not api_key:
        return "لم يتم إعداد NEWS_API_KEY في .env بعد. سجّل مجاناً في newsapi.org واحصل على مفتاح."

    try:
        response = requests.get(
            "https://newsapi.org/v2/everything",
            params={"q": topic, "language": "ar", "sortBy": "publishedAt", "pageSize": 6, "apiKey": api_key},
            timeout=10,
        )
        data = response.json()
        articles = data.get("articles", [])
        if not articles:
            return (
                f"لم يتم العثور على أخبار حديثة عن '{topic}' حالياً. "
                "ملاحظة: تغطية NewsAPI المجانية للمصادر العربية المحلية (زي شركات الطيران السودانية) محدودة، "
                "وقد لا تظهر أخبارهم يومياً حتى لو كانت موجودة فعلياً."
            )

        summary_lines = [f"- {a['title']}" for a in articles[:6]]
        return f"أهم أخبار السفر/الطيران اليوم:\n" + "\n".join(summary_lines)
    except Exception as e:
        return f"حدث خطأ أثناء جلب الأخبار: {e}"


# ---------------------------------------------------------------
# 4) البحث عن تذاكر الطيران
#    أساسي: Amadeus API (بيانات حقيقية بالأسعار)
#    احتياطي: رابط بحث جاهز على Akbar Travels (لو Amadeus فشل أو ما فيه نتائج)
# ---------------------------------------------------------------
def _get_amadeus_token() -> str | None:
    client_id = os.environ.get("AMADEUS_CLIENT_ID")
    client_secret = os.environ.get("AMADEUS_CLIENT_SECRET")
    if not client_id or not client_secret:
        return None

    resp = requests.post(
        "https://test.api.amadeus.com/v1/security/oauth2/token",
        data={
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
        },
        timeout=10,
    )
    return resp.json().get("access_token")


def _build_akbar_travels_fallback_link(origin: str, destination: str, date: str) -> str:
    """رابط بحث جاهز على Akbar Travels بنفس بيانات الرحلة (احتياطي فقط)."""
    return (
        f"https://www.akbartravels.com/ae/flight/search"
        f"?trip=O&from={origin}&to={destination}&departdate={date}&adults=1&class=E"
    )


def search_flights(input_data: dict) -> str:
    origin = input_data.get("origin")
    destination = input_data.get("destination")
    date = input_data.get("date")
    fallback_link = _build_akbar_travels_fallback_link(origin, destination, date)

    token = _get_amadeus_token()
    if not token:
        return (
            "لم يتم إعداد مفاتيح Amadeus بعد، لذا هذا رابط بحث جاهز بنفس بيانات رحلتك:\n"
            f"{fallback_link}"
        )

    try:
        resp = requests.get(
            "https://test.api.amadeus.com/v2/shopping/flight-offers",
            headers={"Authorization": f"Bearer {token}"},
            params={
                "originLocationCode": origin,
                "destinationLocationCode": destination,
                "departureDate": date,
                "adults": 1,
                "max": 5,
            },
            timeout=15,
        )
        offers = resp.json().get("data", [])

        # لا توجد نتائج من Amadeus -> استخدمي الرابط الاحتياطي
        if not offers:
            return (
                f"لم يتم العثور على رحلات من {origin} إلى {destination} بتاريخ {date} عبر Amadeus.\n"
                f"جربي البحث مباشرة هنا: {fallback_link}"
            )

        lines = []
        for offer in offers[:5]:
            price = offer["price"]["total"]
            currency = offer["price"]["currency"]
            lines.append(f"- السعر: {price} {currency}")
        return f"رحلات متاحة من {origin} إلى {destination} بتاريخ {date}:\n" + "\n".join(lines)

    except Exception:
        # أي خطأ بـ Amadeus (اتصال، انتهاء صلاحية، إلخ) -> استخدمي الرابط الاحتياطي فوراً
        return (
            f"تعذّر الوصول لنتائج Amadeus حالياً. جربي البحث مباشرة هنا:\n{fallback_link}"
        )


# ---------------------------------------------------------------
# 5) إرسال الإيميلات - SMTP
# ---------------------------------------------------------------
def send_email(input_data: dict) -> str:
    to_email = input_data.get("to")
    subject = input_data.get("subject")
    body = input_data.get("body")

    smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", 587))
    smtp_user = os.environ.get("SMTP_USER")
    smtp_password = os.environ.get("SMTP_PASSWORD")

    if not smtp_user or not smtp_password:
        return "لم يتم إعداد SMTP_USER و SMTP_PASSWORD في .env بعد (استخدم App Password إذا Gmail)."

    try:
        msg = MIMEMultipart()
        msg["From"] = smtp_user
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))

        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)

        return f"تم إرسال البريد بنجاح إلى {to_email}."
    except Exception as e:
        return f"حدث خطأ أثناء إرسال البريد: {e}"


# ---------------------------------------------------------------
# خريطة اسم الأداة -> الدالة المنفذة لها
# ---------------------------------------------------------------
TOOL_EXECUTORS = {
    "add_customer_data": add_customer_data,
    "resize_image": resize_image,
    "summarize_daily_news": summarize_daily_news,
    "generate_daily_intelligence_report": generate_daily_intelligence_report,
    "search_flights": search_flights,
    "send_email": send_email,
}


def execute_tool(tool_name: str, tool_input: dict) -> str:
    executor = TOOL_EXECUTORS.get(tool_name)
    if not executor:
        return f"خطأ: لا توجد أداة باسم {tool_name}"
    return executor(tool_input)
