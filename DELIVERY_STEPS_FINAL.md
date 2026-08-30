# دليل إنشاء المساعد الإداري - خطوة بخطوة

## المرحلة 1: تجهيز الحسابات (مرة واحدة فقط)

### 1.1 حساب Anthropic (المساعد نفسه)
- console.anthropic.com → سجلي حساب
- من API Keys → Create Key → احفظي المفتاح
- من Billing → اشحني رصيد بسيط (5-10 دولار كافية للبداية)

### 1.2 حساب GitHub (لتخزين الكود)
- github.com → سجلي حساب
- New repository → اسم مثلاً `travel-assistant` → Public → Create

### 1.3 حساب Render (لنشر التطبيق)
- render.com → Sign up with GitHub

---

## المرحلة 2: رفع الملفات على GitHub

ارفعي هذي الملفات بالضبط بهذا الترتيب من مجلد المشروع المرفق لك:

```
travel-assistant/
├── app.py
├── database.py
├── requirements.txt
└── tools/
    ├── __init__.py
    ├── definitions.py
    ├── executors.py
    └── id_photo_processor.py
```

**الطريقة:** من صفحة المستودع → Add file → Upload files → اسحبي كل الملفات دفعة وحدة (المتصفح يحافظ على بنية مجلد tools تلقائياً لو سحبتيه كمجلد كامل) → Commit changes

---

## المرحلة 3: إنشاء الخدمة على Render

1. Render Dashboard → **New +** → **Web Service**
2. اختاري مستودع `travel-assistant` → Connect
3. عبّي:
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `streamlit run app.py --server.port $PORT --server.address 0.0.0.0`
   - **Instance Type:** Free
4. **لا تضغطي Create بعد** — أول أضيفي المفاتيح بالخطوة الجاية

---

## المرحلة 4: إضافة المفاتيح (Environment Variables)

بنفس صفحة الإنشاء (أو من Environment بعدين)، أضيفي هذي المفاتيح **بالاسم بالضبط**:

| الاسم بالضبط | من وين تجيبينه |
|---|---|
| `ANTHROPIC_API_KEY` | من الخطوة 1.1 |
| `DATABASE_URL` | supabase.com → مشروع جديد → Settings → Database → Connection String (URI) |
| `NEWS_API_KEY` | newsapi.org → Get API Key (مجاني) |
| `AMADEUS_CLIENT_ID` و `AMADEUS_CLIENT_SECRET` | developers.amadeus.com → My Self-Service Workspace → Create App (مجاني) |
| `SMTP_USER` و `SMTP_PASSWORD` | بريد Gmail الشركة (لازم App Password، مو كلمة المرور العادية) |

**كيف تسوين App Password لـ Gmail:**
1. myaccount.google.com/security
2. فعّلي "التحقق بخطوتين" (لو مو مفعّل)
3. دوري عن "App Passwords" → أنشئي وحدة جديدة → انسخيها كـ `SMTP_PASSWORD`

---

## المرحلة 5: النشر والتجربة

1. اضغطي **Create Web Service**
2. راقبي تبويب **Logs** لين تشوفي: `Your service is live 🎉`
3. افتحي الرابط اللي يظهر بالأعلى (شكله: `https://travel-assistant-xxxx.onrender.com`)
4. أول فتح قد ياخذ 30-50 ثانية (طبيعي بالخطة المجانية)

---

## المرحلة 6: اختبار كل ميزة (وحدة وحدة)

جربي هذي الرسائل بالترتيب، وحطي ✅ أو ❌ قدام كل وحدة:

- [ ] "سجل بيانات عميل اسمه أحمد"
- [ ] "أعطني أخبار السفر اليوم"
- [ ] "ابحث لي رحلة من دبي RUH لدبي DXB بتاريخ 2026-09-15"
- [ ] "أرسل إيميل تجريبي لـ [بريدك الشخصي] بعنوان تجربة"
- [ ] ارفعي صورة من زر 📎 واطلبي "عدّل هذي لمقاس جواز سفر"

---

## لو أي خطوة ما اشتغلت

ابعتيلي:
1. **نص الرسالة اللي كتبتيها بالضبط**
2. **نص الرد اللي جاك بالضبط** (نسخ ولصق، مو وصف)
3. لو أمكن، لقطة شاشة لتبويب Logs بـ Render وقتها

وأنا أحدد المشكلة وأحلها مباشرة.
