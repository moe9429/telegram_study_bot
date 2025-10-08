# -*- coding: utf-8 -*-
import os
import logging
import pandas as pd
from telegram import Update, ReplyKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    ConversationHandler,
    filters
)
from dotenv import load_dotenv

# ========= Config =========
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

COURSE_XLSX = "course_details.xlsx"
PDF_FOLDER = "pdfs"

# Student Services
SERVICE_FILES = [
    "خطوات الانسحاب من مقرر.pdf",
    "خطوات التسجيل في مقرر.pdf",
    "طلب تسجيل مقرر عن طريق منصه الارشاد.pdf",
]

# Cooperative Training
COOP_FILES = [
    "دليل التدريب التعاوني.pdf",
    "نموذج خطاب جهة التدريب.pdf",
    "نموذج تقييم الطالب.pdf",
    "نموذج تقرير التدريب.pdf",
]

# Executive Programs (single plan each)
EXEC_PROGRAM_FILES = {
    "EMBA": "EMBA.pdf",
    "EHRM": "EHRM.pdf",
    "ENPO": "ENPO.pdf",
}

# ========= States =========
(
    CHOOSING_MENU,
    SELECT_MAJOR,
    SELECT_YEAR,
    COURSE_INQUIRY,
    SERVICE_MENU,
    DESC_MAJOR,
    DESC_YEAR,
    COOP_MENU,
) = range(8)

# ========= Logging =========
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ========= UI Text =========
WELCOME_TEXT = """<b>🤖 مرحبًا بك في المساعد الآلي "مرشد"</b>
📍 كلية إدارة الأعمال - جامعة حائل

<b>💼 الخدمات المتاحة:</b>
1. الخطة الدراسية
2. تفاصيل المقررات
3. دليل خدمات الطالب
4. مكاتب أعضاء هيئة التدريس
5. وصف المقررات
6. التدريب التعاوني

📌 اختر الخدمة من القائمة أدناه:"""

GOODBYE_TEXT = (
    "📌 شكرًا لاستخدامك المساعد الآلي \"مرشد\".\n"
    "اكتب /start للعودة إلى القائمة الرئيسية."
)

def build_main_keyboard():
    keyboard = [
        ["📒 الخطة الدراسية"],
        ["📖 تفاصيل المقررات"],
        ["📂 دليل خدمات الطالب"],
        ["🏢 مكاتب أعضاء هيئة التدريس"],
        ["📝 وصف المقررات"],
        ["🤝 التدريب التعاوني"],
        ["✅ إنهاء"],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# ========= Handlers =========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        WELCOME_TEXT,
        parse_mode=ParseMode.HTML,
        reply_markup=build_main_keyboard()
    )
    return CHOOSING_MENU

# ---- Study Plan (5 UG majors + 3 Executive programs) ----
async def study_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ["MIS - نظم معلومات إدارية"],
        ["MGT - إدارة"],
        ["FIN - المالية والاقتصاد"],
        ["ACC - المحاسبة"],
        ["MKT - التسويق"],
        ["EMBA - ماجستير إدارة الأعمال التنفيذي"],
        ["EHRM - ماجستير إدارة الموارد البشرية التنفيذي"],
        ["ENPO - ماجستير إدارة المنظمات غير الربحية التنفيذي"],
        ["⬅️ رجوع"],
    ]
    await update.message.reply_text(
        "اختر التخصص أو البرنامج:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
    )
    return SELECT_MAJOR

async def select_major(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "⬅️ رجوع":
        return await start(update, context)

    code = text.split(" - ")[0].strip()
    context.user_data['major'] = code

    if code in EXEC_PROGRAM_FILES:
        filename = EXEC_PROGRAM_FILES[code]
        path = os.path.join(PDF_FOLDER, filename)
        if os.path.exists(path):
            with open(path, 'rb') as f:
                await update.message.reply_document(f, filename=filename)
        else:
            await update.message.reply_text("⚠️ ملف الخطة غير موجود.")
        return await start(update, context)

    keyboard = [["2024"], ["2021"], ["2020"], ["⬅️ رجوع"]]
    await update.message.reply_text(
        f"التخصص: {text}\nاختر السنة:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
    )
    return SELECT_YEAR

async def select_year(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "⬅️ رجوع":
        return await study_plan(update, context)

    major = context.user_data.get('major')
    filename = f"{major}{text}.pdf"
    path = os.path.join(PDF_FOLDER, filename)

    if os.path.exists(path):
        with open(path, 'rb') as f:
            await update.message.reply_document(f, filename=filename)
    else:
        await update.message.reply_text("⚠️ ملف الخطة غير موجود.")
    return await start(update, context)

# ---- Course Details ----
async def course_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "✍️ أرسل رمز المقرر (مثال: MIS101):",
        reply_markup=ReplyKeyboardMarkup([["⬅️ رجوع"]], resize_keyboard=True),
    )
    return COURSE_INQUIRY

async def inquiry_course(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text == '⬅️ رجوع':
        return await start(update, context)

    if not os.path.exists(COURSE_XLSX):
        await update.message.reply_text("⚠️ ملف تفاصيل المقررات غير موجود.", reply_markup=build_main_keyboard())
        return CHOOSING_MENU

    try:
        df = pd.read_excel(COURSE_XLSX)

        def find_col(keys):
            return next((c for c in df.columns if any(k in c.lower() for k in keys)), None)

        code_col = find_col(['code', 'رمز']) or df.columns[0]
        crn_col = find_col(['crn', 'مرجعي', 'reference', 'الرقم'])
        building_col = find_col(['bldg', 'مبنى'])
        section_col = find_col(['section', 'شعبة'])
        time_col = find_col(['time', 'وقت'])
        days_col = find_col(['day', 'يوم'])
        room_col = find_col(['room', 'قاعة'])

        df[code_col] = df[code_col].astype(str).str.upper()
        matched = df[df[code_col] == text.upper()]
        if matched.empty:
            raise ValueError("not found")

        rows = []
        for _, row in matched.iterrows():
            crn_line = f"🔢 الرقم المرجعي: {row[crn_col]}\n" if crn_col else ""
            msg = (
                f"{crn_line}"
                f"رمز المقرر: {row.get(code_col, '-')}\n"
                f"الشعبة: {str(row.get(section_col, '-')).replace('.0','')}\n"
                f"اليوم: {row.get(days_col, '-')}\n"
                f"الوقت: {row.get(time_col, '-')}\n"
                f"المبنى: {row.get(building_col, '-')}\n"
                f"القاعة: {row.get(room_col, '-')}"
            )
            rows.append(msg)
        await update.message.reply_text("\n\n".join(rows), reply_markup=build_main_keyboard())
    except Exception as e:
        logger.error(f"inquiry_course error: {e}")
        await update.message.reply_text("⚠️ لم يتم العثور على المقرر.", reply_markup=build_main_keyboard())
    return CHOOSING_MENU

# ---- Student Services ----
async def service_manual(update: Update, context: ContextTypes.DEFAULT_TYPE):
    manuals = [f for f in SERVICE_FILES if os.path.exists(os.path.join(PDF_FOLDER, f))]
    if not manuals:
        await update.message.reply_text("⚠️ لا توجد ملفات متاحة حالياً.", reply_markup=build_main_keyboard())
        return CHOOSING_MENU
    keyboard = [[m] for m in manuals] + [["⬅️ رجوع"]]
    await update.message.reply_text("اختر الخدمة:", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
    return SERVICE_MENU

async def send_manual(update: Update, context: ContextTypes.DEFAULT_TYPE):
    choice = update.message.text
    if choice == "⬅️ رجوع":
        return await start(update, context)
    path = os.path.join(PDF_FOLDER, choice)
    if os.path.exists(path):
        with open(path, 'rb') as f:
            await update.message.reply_document(f, filename=choice)
    else:
        await update.message.reply_text("⚠️ الملف غير موجود.", reply_markup=build_main_keyboard())
    return CHOOSING_MENU

# ---- Cooperative Training ----
async def cooperative_training(update: Update, context: ContextTypes.DEFAULT_TYPE):
    files = [f for f in COOP_FILES if os.path.exists(os.path.join(PDF_FOLDER, f))]
    if not files:
        await update.message.reply_text("⚠️ لا توجد ملفات للتدريب التعاوني.", reply_markup=build_main_keyboard())
        return CHOOSING_MENU
    keyboard = [[f] for f in files] + [["⬅️ رجوع"]]
    await update.message.reply_text("اختر المستند المطلوب:", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
    return COOP_MENU

async def send_coop_doc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    choice = update.message.text
    if choice == "⬅️ رجوع":
        return await start(update, context)
    path = os.path.join(PDF_FOLDER, choice)
    if os.path.exists(path):
        with open(path, 'rb') as f:
            await update.message.reply_document(f, filename=choice)
    else:
        await update.message.reply_text("⚠️ الملف غير موجود.", reply_markup=build_main_keyboard())
    return CHOOSING_MENU

# ---- End ----
async def end(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(GOODBYE_TEXT)
    return ConversationHandler.END

# ---- Main ----
if __name__ == '__main__':
    app = Application.builder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            CHOOSING_MENU: [
                MessageHandler(filters.Regex('^📒 الخطة الدراسية$'), study_plan),
                MessageHandler(filters.Regex('^📖 تفاصيل المقررات$'), course_details),
                MessageHandler(filters.Regex('^📂 دليل خدمات الطالب$'), service_manual),
                MessageHandler(filters.Regex('^🏢 مكاتب أعضاء هيئة التدريس$'), send_manual),
                MessageHandler(filters.Regex('^📝 وصف المقررات$'), send_manual),
                MessageHandler(filters.Regex('^🤝 التدريب التعاوني$'), cooperative_training),
                MessageHandler(filters.Regex('^✅ إنهاء$'), end),
            ],
            SELECT_MAJOR: [MessageHandler(filters.ALL, select_major)],
            SELECT_YEAR: [MessageHandler(filters.ALL, select_year)],
            COURSE_INQUIRY: [MessageHandler(filters.ALL, inquiry_course)],
            SERVICE_MENU: [MessageHandler(filters.ALL, send_manual)],
            COOP_MENU: [MessageHandler(filters.ALL, send_coop_doc)],
        },
        fallbacks=[CommandHandler('start', start)],
    )

    app.add_handler(conv)
    app.run_polling()
