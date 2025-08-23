import os
import logging
import pandas as pd
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    ConversationHandler,
    filters
)
from dotenv import load_dotenv

# Load bot token from .env
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Conversation states
(
    CHOOSING_MENU,
    SELECT_MAJOR,
    SELECT_YEAR,
    COURSE_INQUIRY,
    SERVICE_MENU,
    DESC_MAJOR,
    DESC_YEAR,
) = range(7)

# File paths and lists
COURSE_XLSX = "course_details.xlsx"
PDF_FOLDER = "pdfs"
SERVICE_FILES = [
    "خطوات الانسحاب من مقرر.pdf",
    "خطوات التسجيل في مقرر.pdf",
    "طلب تسجيل مقرر عن طريق منصه الارشاد.pdf"
]

# Logging configuration
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot texts
WELCOME_TEXT = (
    "🤖 مرحبًا بك في المساعد الآلي \"مرشد\"\n"
    "📍 قسم الإدارة ونظم المعلومات - جامعة حائل\n"
    "🧾 يمكنك الاستفادة من الخدمات التالية:\n"
    "1️⃣ الخطة الدراسية\n"
    "2️⃣ تفاصيل المقررات\n"
    "3️⃣ دليل خدمات الطالب\n"
    "4️⃣ مكاتب أعضاء هيئة التدريس\n"
    "📝 وصف المقرات\n"
    "يرجى اختيار خيار:"
)

goodbye_text = (
    "📌 شكراً لاستخدامك المساعد الآلي مرشد.\n"
    "اكتب /start للعودة."
)

def build_main_keyboard():
    keyboard = [
        ["📒 الخطة الدراسية"],
        ["📖 تفاصيل المقررات"],
        ["3️⃣ دليل خدمات الطالب"],
        ["4️⃣ مكاتب أعضاء هيئة التدريس"],
        ["📝 وصف المقرات"],
        ["✅ إنهاء"],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# Start handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(WELCOME_TEXT, reply_markup=build_main_keyboard())
    return CHOOSING_MENU

# ===== الخطة الدراسية =====
async def study_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ["MIS - نظم معلومات ادارية"],
        ["MGT - إدارة"],
        ["⬅️ رجوع"],
    ]
    await update.message.reply_text(
        "اختر التخصص:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
    )
    return SELECT_MAJOR

async def select_major(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "⬅️ رجوع":
        return await start(update, context)

    context.user_data['major'] = text.split(" - ")[0]
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
    filename = f"{major}{text}.pdf"  # e.g. MIS2021.pdf
    path = os.path.join(PDF_FOLDER, filename)

    if os.path.exists(path):
        with open(path, 'rb') as f:
            await update.message.reply_document(f, filename=filename)
    else:
        await update.message.reply_text("⚠️ ملف الخطة غير موجود.")
    return await start(update, context)

# ===== تفاصيل المقررات =====
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
        await update.message.reply_text(
            "⚠️ ملف تفاصيل المقررات غير موجود.",
            reply_markup=build_main_keyboard(),
        )
        return CHOOSING_MENU

    try:
        df = pd.read_excel(COURSE_XLSX)
        # Detect columns
        def find_col(keywords):
            return next((c for c in df.columns if any(k in c.lower() for k in keywords)), None)

        code_col = find_col(['code', 'رمز']) or df.columns[0]
        crn_col = find_col(['crn', 'مرجعي', 'reference', 'الرقم'])
        df[code_col] = df[code_col].astype(str).str.upper()
        user_code = text.upper()
        matched = df[df[code_col] == user_code]
        if matched.empty:
            raise ValueError("Course not found")

        building_col = find_col(['bldg', 'مبنى']) or df.columns[1]
        section_col = find_col(['section', 'شعبة']) or df.columns[2]
        time_col = find_col(['time', 'وقت']) or df.columns[3]
        days_col = find_col(['day', 'يوم']) or df.columns[4]
        room_col = find_col(['room', 'قاعة']) or df.columns[5]

        messages = []
        for _, row in matched.iterrows():
            crn_line = f"🔢 {crn_col}: {row[crn_col]}\n" if crn_col else ""
            msg = (
                f"{crn_line}✅ {code_col}: {row[code_col]}\n"
                f"🔸 {section_col}: {str(row[section_col]).replace('.0','')}\n"
                f"📅 {days_col}: {row[days_col]}\n"
                f"🕒 {time_col}: {row[time_col]}\n"
                f"🏢 {building_col}: {row[building_col]}\n"
                f"📍 {room_col}: {row[room_col]}"
            )
            messages.append(msg)
        full_msg = "\n\n".join(messages)
        await update.message.reply_text(full_msg, reply_markup=build_main_keyboard())
    except Exception as e:
        logger.error(f"Error in inquiry_course: {e}")
        await update.message.reply_text(
            "⚠️ لم أتمكن من العثور على المقرر. تحقق من الرمز وحاول مرة أخرى.",
            reply_markup=build_main_keyboard(),
        )
    return CHOOSING_MENU

# ===== دليل خدمات الطالب =====
async def service_manual(update: Update, context: ContextTypes.DEFAULT_TYPE):
    manuals = [f for f in SERVICE_FILES if os.path.exists(os.path.join(PDF_FOLDER, f))]
    if not manuals:
        await update.message.reply_text("⚠️ لا توجد ملفات للخدمات.", reply_markup=build_main_keyboard())
        return CHOOSING_MENU
    keyboard = [[m] for m in manuals] + [["⬅️ رجوع"]]
    await update.message.reply_text(
        "اختر خدمة:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
    )
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

# ===== مكاتب أعضاء هيئة التدريس =====
async def faculty_offices(update: Update, context: ContextTypes.DEFAULT_TYPE):
    path = os.path.join(PDF_FOLDER, "office_number.pdf")
    if os.path.exists(path):
        with open(path, 'rb') as f:
            await update.message.reply_document(f, filename="office_number.pdf")
    else:
        await update.message.reply_text("⚠️ ملف مكتب هيئة التدريس غير موجود.", reply_markup=build_main_keyboard())
    return CHOOSING_MENU

# ===== 📝 وصف المقرات =====
async def describe_courses(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["نظم المعلومات"], ["الإدارة"], ["⬅️ رجوع"]]
    await update.message.reply_text(
        "اختر المسار:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
    )
    return DESC_MAJOR

async def desc_select_major(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "⬅️ رجوع":
        return await start(update, context)
    context.user_data['desc_major'] = 'MIS' if 'نظم' in text else 'MGT'

    keyboard = [["خطة 2024"], ["خطة 2021-2022-2023"], ["خطة 2020"], ["⬅️ رجوع"]]
    await update.message.reply_text(
        f"المسار: {text}\nاختر الخطة:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
    )
    return DESC_YEAR

async def desc_select_year(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "⬅️ رجوع":
        return await describe_courses(update, context)

    major = context.user_data.get('desc_major')  # MIS or MGT
    # Map choices to filenames
    mapping = {
        ('MIS', 'خطة 2024'): 'MisC2024.pdf',
        ('MIS', 'خطة 2021-2022-2023'): 'MisC2021.pdf',
        ('MIS', 'خطة 2020'): 'MisC2020.pdf',
        ('MGT', 'خطة 2024'): 'MgtC2024.pdf',  # NOTE: add this file if available
        ('MGT', 'خطة 2021-2022-2023'): 'MgtC2021.pdf',
        ('MGT', 'خطة 2020'): 'MgtC2020.pdf',
    }
    filename = mapping.get((major, text))
    if not filename:
        await update.message.reply_text("⚠️ لم يتم العثور على الملف المطلوب.")
        return await start(update, context)

    path = os.path.join(PDF_FOLDER, filename)
    if os.path.exists(path):
        with open(path, 'rb') as f:
            await update.message.reply_document(f, filename=filename)
    else:
        await update.message.reply_text("⚠️ الملف غير موجود في مجلد pdfs.")
    return await start(update, context)

# End handler
async def end(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(goodbye_text)
    return ConversationHandler.END

# Unknown handler
async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await start(update, context)

# Main function
if __name__ == '__main__':
    app = Application.builder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            CHOOSING_MENU: [
                MessageHandler(filters.Regex('^📒 الخطة الدراسية$'), study_plan),
                MessageHandler(filters.Regex('^📖 تفاصيل المقررات$'), course_details),
                MessageHandler(filters.Regex('^3️⃣ دليل خدمات الطالب$'), service_manual),
                MessageHandler(filters.Regex('^4️⃣ مكاتب أعضاء هيئة التدريس$'), faculty_offices),
                MessageHandler(filters.Regex('^📝 وصف المقرات$'), describe_courses),
                MessageHandler(filters.Regex('^✅ إنهاء$'), end),
                MessageHandler(filters.ALL, unknown),
            ],
            SELECT_MAJOR: [MessageHandler(filters.ALL, select_major)],
            SELECT_YEAR: [MessageHandler(filters.ALL, select_year)],
            COURSE_INQUIRY: [MessageHandler(filters.ALL, inquiry_course)],
            SERVICE_MENU: [MessageHandler(filters.ALL, send_manual)],
            DESC_MAJOR: [MessageHandler(filters.ALL, desc_select_major)],
            DESC_YEAR: [MessageHandler(filters.ALL, desc_select_year)],
        },
        fallbacks=[CommandHandler('start', start)],
    )

    app.add_handler(conv)
    app.run_polling()
