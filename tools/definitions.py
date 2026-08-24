"""
تعريف الأدوات (Tools) التي يمكن لـ Claude استدعاءها.
كل أداة = وظيفة إدارية واحدة (إدخال بيانات، صور، أخبار، طيران، إيميل).
لاحقاً سنربط كل tool هنا بدالة تنفيذ فعلية في executors.py
"""

TOOLS = [
    {
        "name": "add_customer_data",
        "description": "إضافة أو تحديث بيانات عميل في قاعدة البيانات (الاسم، رقم الهاتف، البريد، تفاصيل الحجز).",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "اسم العميل الكامل"},
                "phone": {"type": "string", "description": "رقم هاتف العميل"},
                "email": {"type": "string", "description": "البريد الإلكتروني للعميل"},
                "booking_details": {"type": "string", "description": "تفاصيل الحجز أو الملاحظات"},
            },
            "required": ["name"],
        },
    },
    {
        "name": "resize_image",
        "description": "معالجة صورة جواز سفر/تأشيرة حسب المواصفات الرسمية: مقاس 35x45mm، خلفية بيضاء، تحسين عام للإضاءة والوضوح فقط بدون أي تعديل لملامح الوجه، وضغط الحجم لأقل من 1 ميجابايت.",
        "input_schema": {
            "type": "object",
            "properties": {
                "image_path": {"type": "string", "description": "مسار الصورة الأصلية"},
                "output_path": {"type": "string", "description": "مسار حفظ الصورة النهائية (اختياري)"},
                "width_mm": {"type": "number", "description": "العرض بالملم (افتراضي 35)"},
                "height_mm": {"type": "number", "description": "الارتفاع بالملم (افتراضي 45)"},
            },
            "required": ["image_path"],
        },
    },
    {
        "name": "summarize_daily_news",
        "description": "تلخيص سريع لأخبار السفر والطيران والعمرة (مصدر: NewsAPI - تغطية محدودة للمصادر المحلية).",
        "input_schema": {
            "type": "object",
            "properties": {
                "topic": {"type": "string", "description": "موضوع الأخبار (مثلاً: سياحة، طيران، عروض سفر)"},
            },
            "required": ["topic"],
        },
    },
    {
        "name": "generate_daily_intelligence_report",
        "description": "تقرير استخباراتي يومي شامل ومفصّل عن الطيران والسفر والحج والعمرة والتأشيرات، مبني على بحث حقيقي متعدد المصادر (أدق وأشمل من الملخص السريع، لكنه أبطأ وأغلى تكلفة). استخدمها فقط عند طلب صريح لـ'التقرير اليومي الكامل' أو 'تقرير الاستخبارات'.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "search_flights",
        "description": "البحث عن تذاكر طيران بين مدينتين في تاريخ محدد.",
        "input_schema": {
            "type": "object",
            "properties": {
                "origin": {"type": "string", "description": "مدينة/مطار الانطلاق (كود IATA مثل RUH)"},
                "destination": {"type": "string", "description": "مدينة/مطار الوصول (كود IATA مثل DXB)"},
                "date": {"type": "string", "description": "تاريخ الرحلة بصيغة YYYY-MM-DD"},
            },
            "required": ["origin", "destination", "date"],
        },
    },
    {
        "name": "send_email",
        "description": "إرسال بريد إلكتروني لعميل أو جهة معينة يحتوي على تفاصيل الحجز أو أي محتوى آخر.",
        "input_schema": {
            "type": "object",
            "properties": {
                "to": {"type": "string", "description": "البريد الإلكتروني للمستلم"},
                "subject": {"type": "string", "description": "عنوان الرسالة"},
                "body": {"type": "string", "description": "محتوى الرسالة"},
            },
            "required": ["to", "subject", "body"],
        },
    },
]
