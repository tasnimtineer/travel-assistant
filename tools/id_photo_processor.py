"""
معالجة صور جواز السفر / التأشيرة حسب مواصفات قياسية:
- مقاس 35x45mm (يُحوَّل لبكسل حسب دقة الطباعة DPI)
- خلفية بيضاء نظيفة
- تحسينات عامة فقط (سطوع/تباين/وضوح) - بدون أي تعديل على ملامح الوجه
- الحجم النهائي لا يتجاوز 1 ميجابايت

المكتبات المطلوبة:
    pip install Pillow rembg onnxruntime
"""

import io
from PIL import Image, ImageEnhance
# ملاحظة: rembg تُستورد داخل الدالة نفسها (lazy import) وليس هنا بالأعلى،
# لأنها مكتبة ثقيلة على الذاكرة (تجر معها onnxruntime/numba/scipy).
# استيرادها هنا كان يحمّلها مع كل إقلاع للتطبيق حتى لو محد يستخدم أداة الصور،
# وهذا كان يسبب تعليق/تعطل صامت على خطط الاستضافة المجانية محدودة الرام.

MM_TO_INCH = 1 / 25.4


def mm_to_pixels(width_mm: float, height_mm: float, dpi: int = 300) -> tuple[int, int]:
    width_px = round(width_mm * MM_TO_INCH * dpi)
    height_px = round(height_mm * MM_TO_INCH * dpi)
    return width_px, height_px


def replace_background_with_white(image: Image.Image) -> Image.Image:
    """
    إزالة الخلفية الأصلية واستبدالها بأبيض نقي، مع الحفاظ الكامل على حواف
    الوجه والملابس كما هي (بدون أي إعادة رسم أو تعديل للشخص نفسه).
    """
    from rembg import remove  # تحميل المكتبة فقط عند الاستخدام الفعلي
    no_bg = remove(image)  # يرجع صورة RGBA بخلفية شفافة
    white_bg = Image.new("RGBA", no_bg.size, (255, 255, 255, 255))
    white_bg.paste(no_bg, (0, 0), no_bg)
    return white_bg.convert("RGB")


def apply_global_enhancement(image: Image.Image) -> Image.Image:
    """
    تحسينات عامة فقط على الصورة كاملة (سطوع/تباين/وضوح):
    لا تلمس ملامح الوجه أو تعيد رسم أي جزء من الشخص - فقط تصحيح إضاءة/وضوح عام.
    """
    image = ImageEnhance.Brightness(image).enhance(1.05)   # سطوع خفيف
    image = ImageEnhance.Contrast(image).enhance(1.08)     # تباين خفيف
    image = ImageEnhance.Sharpness(image).enhance(1.15)    # وضوح خفيف
    return image


def compress_to_max_size(image: Image.Image, max_kb: int = 1024) -> bytes:
    """ضغط تدريجي لضمان ألا يتجاوز حجم الملف 1 ميجابايت."""
    quality = 95
    buffer = io.BytesIO()
    while quality > 10:
        buffer.seek(0)
        buffer.truncate()
        image.save(buffer, format="JPEG", quality=quality, optimize=True)
        if buffer.tell() <= max_kb * 1024:
            break
        quality -= 5
    return buffer.getvalue()


def process_id_photo(
    input_path: str,
    output_path: str,
    width_mm: float = 35,
    height_mm: float = 45,
    dpi: int = 300,
) -> str:
    """
    الدالة الرئيسية: تنفّذ كامل الخطوات المطلوبة على صورة جواز السفر.
    """
    image = Image.open(input_path).convert("RGB")

    # 1) استبدال الخلفية بأبيض (بدون المساس بالوجه/الملابس)
    image = replace_background_with_white(image)

    # 2) تحسينات عامة فقط - سطوع/تباين/وضوح
    image = apply_global_enhancement(image)

    # 3) الضبط على المقاس المطلوب 35x45mm
    target_size = mm_to_pixels(width_mm, height_mm, dpi)
    image = image.resize(target_size)

    # 4) الضغط لضمان الحجم أقل من 1 ميجابايت
    final_bytes = compress_to_max_size(image, max_kb=1024)
    with open(output_path, "wb") as f:
        f.write(final_bytes)

    size_kb = len(final_bytes) / 1024
    return f"تم إنشاء الصورة بنجاح: {output_path} ({size_kb:.0f} KB, {target_size[0]}x{target_size[1]}px)"


# ---------------------------------------------------------------
# ربط الدالة كأداة (Tool) يستدعيها Claude عبر executors.py
# ---------------------------------------------------------------
def resize_image(input_data: dict) -> str:
    image_path = input_data.get("image_path")
    output_path = input_data.get("output_path", image_path.replace(".", "_id_photo."))
    width_mm = input_data.get("width_mm", 35)
    height_mm = input_data.get("height_mm", 45)

    try:
        return process_id_photo(image_path, output_path, width_mm, height_mm)
    except Exception as e:
        return f"حدث خطأ أثناء معالجة الصورة: {e}"
