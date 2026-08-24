"""
تقرير الاستخبارات اليومي للسفر والطيران والحج والعمرة.

الفكرة:
1) نبحث فعلياً بجوجل (عبر Serper.dev) عن أهم الفئات ذات الأولوية للشركة
   (طيران السودان، تأشيرات عمان/السعودية، عروض شركات الطيران الخليجية...)
2) نجمع النتائج الخام (عناوين + مقتطفات + روابط)
3) نمررها لـ Claude مع "البرومبت الرئيسي" كتعليمات نظام، فيكتب التقرير
   بنفس الهيكل والتصنيفات المطلوبة بالضبط (🟢 مؤكد / 🟡 قيد التطور ...)

ملاحظة صادقة: هذا تنفيذ واقعي مصغّر من فكرة البرومبت الأصلي (مراقبة يومية
لعشرات المصادر الرسمية) - يغطي أهم الفئات لشركتك تحديداً، مو كل مصدر
مذكور بالبرومبت حرفياً (هذا يحتاج بنية استخبارات ضخمة غير عملية هنا).
"""

import os
import requests
from anthropic import Anthropic

# ---------------------------------------------------------------
# البرومبت الرئيسي الكامل (كما زوّدتنا به) - يُستخدم كتعليمات نظام لـ Claude
# ---------------------------------------------------------------
MASTER_PROMPT = """
[ضعي هنا نص البرومبت الكامل الذي أرسلتيه بالضبط - تم اختصاره في هذا العرض
لتوفير المساحة، لكن في الملف الفعلي الذي سترفعينه يجب لصق النص كاملاً
كما أرسلتيه حرفياً، من "# CLAUDE MASTER PROMPT V2" إلى "END OF MASTER PROMPT"]
"""

# ---------------------------------------------------------------
# استعلامات بحث مركّزة على أولويات شركتك تحديداً (مو كل مصدر بالقائمة)
# ---------------------------------------------------------------
PRIORITY_SEARCH_QUERIES = [
    "Port Sudan airport flights news today",
    "Sudan Airways Badr Airlines Tarco Aviation news",
    "Saudi Umrah visa rules update Nusuk",
    "Oman visa border UAE Royal Oman Police news",
    "Gulf airlines new offers promotion Umrah Hajj",
    "Emirates Etihad flydubai new route announcement",
    "Saudi Arabia tourist visa rule change",
    "GACA Saudi civil aviation notice",
    "Yemen Red Sea airspace NOTAM aviation",
    "Oman Air SalamAir Sudan flights",
]


def _serper_search(query: str, api_key: str, num_results: int = 4) -> list[dict]:
    """بحث حقيقي بجوجل عبر Serper.dev - يرجع أهم النتائج (عنوان/مقتطف/رابط)."""
    try:
        resp = requests.post(
            "https://google.serper.dev/search",
            headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
            json={"q": query, "num": num_results},
            timeout=10,
        )
        data = resp.json()
        results = []
        for item in data.get("organic", [])[:num_results]:
            results.append({
                "title": item.get("title", ""),
                "snippet": item.get("snippet", ""),
                "link": item.get("link", ""),
            })
        return results
    except Exception:
        return []


def _gather_raw_intelligence(serper_key: str) -> str:
    """يشغّل كل استعلامات البحث المحددة ويجمع النتائج بصيغة نصية منظمة."""
    sections = []
    for query in PRIORITY_SEARCH_QUERIES:
        results = _serper_search(query, serper_key)
        if not results:
            continue
        block = [f"### نتائج بحث: {query}"]
        for r in results:
            block.append(f"- {r['title']}\n  {r['snippet']}\n  المصدر: {r['link']}")
        sections.append("\n".join(block))
    return "\n\n".join(sections) if sections else ""


def generate_daily_intelligence_report(input_data: dict) -> str:
    serper_key = os.environ.get("SERPER_API_KEY")
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")

    if not serper_key:
        return (
            "لم يتم إعداد SERPER_API_KEY بعد. سجّلي مجاناً في serper.dev "
            "(2500 استعلام مجاني بدون بطاقة ائتمان) وأضيفي المفتاح كـ Environment Variable."
        )

    raw_intel = _gather_raw_intelligence(serper_key)
    if not raw_intel:
        return "تعذّر جلب أي نتائج بحث حالياً. تأكدي من صحة SERPER_API_KEY وحاولي مجدداً."

    # الآن نمرر النتائج الخام لـ Claude مع البرومبت الرئيسي ليكتب التقرير المهيكل
    client = Anthropic(api_key=anthropic_key)
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4000,
        system=MASTER_PROMPT,
        messages=[
            {
                "role": "user",
                "content": (
                    "هذه نتائج بحث حقيقية جُمعت اليوم من مصادر متعددة. "
                    "اكتبي التقرير اليومي الكامل بناءً عليها فقط، بنفس الهيكل والتصنيفات "
                    "المطلوبة بالضبط. لا تخترعي معلومات غير موجودة بالنتائج أدناه:\n\n"
                    f"{raw_intel}"
                ),
            }
        ],
    )
    return "".join(b.text for b in response.content if b.type == "text")
