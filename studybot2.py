from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
import logging
import sqlite3
import os

TOKEN = "8419293835:AAFTBIyv1Wh06ik0GJyg9yExLMOcNEOfH9Y"
DB_FILE = "database.db"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ============================================================
# 📂 إدارة قاعدة البيانات (SQLite)
# ============================================================

def init_db():
    """إنشاء جدول الملفات إذا لم يكن موجوداً"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject TEXT NOT NULL,
            chapter TEXT NOT NULL,
            file_id TEXT NOT NULL UNIQUE
        )
    """)
    conn.commit()
    conn.close()

def add_file_to_db(subject, chapter, file_id):
    """إضافة ملف جديد لقاعدة البيانات (مع منع التكرار)"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO files (subject, chapter, file_id) VALUES (?, ?, ?)",
            (subject, chapter, file_id)
        )
        conn.commit()
        success = True
    except sqlite3.IntegrityError:
        success = False # الملف موجود مسبقاً
    conn.close()
    return success

def get_files_from_db(subject, chapter):
    """جلب جميع الملفات الخاصة بقسم معين"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT file_id FROM files WHERE subject = ? AND chapter = ?",
        (subject, chapter)
    )
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows]

def count_files_in_chapter(subject, chapter):
    """حساب عدد الملفات في قسم معين"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM files WHERE subject = ? AND chapter = ?",
        (subject, chapter)
    )
    count = cursor.fetchone()[0]
    conn.close()
    return count

def check_chapter_has_files(subject, chapter):
    """التحقق مما إذا كان القسم يحتوي على ملفات على الأقل لعرض علامة الصح ✅"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT 1 FROM files WHERE subject = ? AND chapter = ? LIMIT 1",
        (subject, chapter)
    )
    result = cursor.fetchone()
    conn.close()
    return result is not None

# ============================================================
# 📚 التقسيمات الدقيقة والمعتمدة لكل المواد بالعدد المطلوب تماماً
# ============================================================

SUBJECTS_INFO = {
    "physics_summary": {
        "name": "تلخيص الفيزياء",
        "chapters": {f"ch{i}": f"الفصل {i}" for i in range(1, 9)} # 8 فصول
    },
    "chemistry": {
        "name": "الكيمياء",
        "chapters": {
            "ch1": "الباب الأول",
            "ch2": "الباب الثاني",
            "ch3": "الباب الثالث",
            "ch4": "الباب الرابع",
            "hydro": "الهيدروكربونات (عضوية)",
            "derivatives": "مشتقات الهيدروكربونات (عضوية)"
        }
    },
    "biology": {
        "name": "الأحياء",
        "chapters": {f"ch{i}": f"الباب {i}" for i in range(1, 8)} # 7 أبواب
    },
    "geology": {
        "name": "الجيولوجيا",
        "chapters": {f"ch{i}": f"الباب {i}" for i in range(1, 4)} # 3 أبواب
    },
    "arabic": {
        "name": "اللغة العربية",
        "chapters": {f"sec{i}": f"القسم {i}" for i in range(1, 13)} # 12 قسم
    },
    "english": {
        "name": "اللغة الإنجليزية",
        "chapters": {
            f"unit{u}_{t}": f"Unit {u} ({'Vocab' if t=='vocab' else 'Grammar'})" 
            for u in range(1, 13) for t in ["vocab", "grammar"]
        } # 24 قسم (12 وحدة × كلمات وقواعد)
    }
}

# ============================================================
# 🏠 الكيبوردات
# ============================================================

def back_button():
    return [InlineKeyboardButton("🏠 الرئيسية", callback_data="main_menu")]

def main_menu_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("🔥 تلخيص الفيزياء", callback_data="subject_physics_summary"),
            InlineKeyboardButton("🧪 الكيمياء", callback_data="subject_chemistry")
        ],
        [
            InlineKeyboardButton("🧬 الأحياء", callback_data="subject_biology"),
            InlineKeyboardButton("🌍 الجيولوجيا", callback_data="subject_geology")
        ],
        [
            InlineKeyboardButton("📖 اللغة العربية", callback_data="subject_arabic"),
            InlineKeyboardButton("🇬🇧 اللغة الإنجليزية", callback_data="subject_english")
        ],
    ]
    return InlineKeyboardMarkup(keyboard)

def subject_keyboard(subject):
    chapters = SUBJECTS_INFO[subject]["chapters"]
    
    keyboard = []
    row = []
    
    for key, name in chapters.items():
        # التحقق من قاعدة البيانات مباشرة لمعرفة هل القسم به ملفات أم لا
        has_files = check_chapter_has_files(subject, key)
        status = "✅" if has_files else "✨"
        
        callback = f"file|{subject}|{key}"
        row.append(InlineKeyboardButton(f"{status} {name}", callback_data=callback))
        
        if len(row) == 2:
            keyboard.append(row)
            row = []
            
    if row:
        keyboard.append(row)
        
    keyboard.append(back_button())
    return InlineKeyboardMarkup(keyboard)

# ============================================================
# 🚀 /start
# ============================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎓 أهلاً بك في البوت العلمي المتطور!\n\n"
        "📚 اختر المادة التي تريد تصفح ملفاتها:",
        reply_markup=main_menu_keyboard()
    )

# ============================================================
# 📥 التخزين الأوتوماتيكي (متعدد الملفات لكل قسم)
# ============================================================

async def auto_save_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message.document:
        return

    caption = message.caption
    if not caption:
        await message.reply_text(
            "⚠️ لتخزين الملف أوتوماتيكياً، اكتب وصف الملف في الكابتشن كالأمثلة التالية:\n\n"
            "• **الفيزياء (من 1 لـ 8):** `physics_summary ch1` ... `ch8`\n"
            "• **الكيمياء:** `chemistry ch1` ... `ch4` أو `chemistry hydro` / `chemistry derivatives`\n"
            "• **الأحياء (من 1 لـ 7):** `biology ch1` ... `ch7`\n"
            "• **الجيولوجيا (من 1 لـ 3):** `geology ch1` ... `ch3`\n"
            "• **العربي (من 1 لـ 12):** `arabic sec1` ... `arabic sec12`\n"
            "• **الإنجليزي (12 وحدة كودين لكل وحدة):** `english unit1_vocab` أو `english unit1_grammar`",
            parse_mode="Markdown"
        )
        return

    parts = caption.strip().split()
    if len(parts) < 2:
        await message.reply_text("❌ الصيغة غير صحيحة. تأكد من كتابة اسم المادة وكود القسم.", parse_mode="Markdown")
        return

    subject = parts[0]
    chapter = parts[1]

    if subject not in SUBJECTS_INFO:
        await message.reply_text(f"❌ اسم المادة '{subject}' غير صحيح.")
        return

    if chapter not in SUBJECTS_INFO[subject]["chapters"]:
        await message.reply_text(f"❌ كود القسم '{chapter}' غير صحيح لهذه المادة.")
        return

    file_id = message.document.file_id
    
    # حفظ الملف في قاعدة بيانات SQLite
    added = add_file_to_db(subject, chapter, file_id)
    
    file_count = count_files_in_chapter(subject, chapter)
    chapter_name = SUBJECTS_INFO[subject]["chapters"][chapter]

    if added:
        await message.reply_text(
            f"✅ تم إضافة الملف بنجاح إلى ({chapter_name})!\n"
            f"📂 إجمالي الملفات المخزنة في هذا القسم حتى الآن: **{file_count}** ملف",
            parse_mode="Markdown"
        )
    else:
        await message.reply_text(
            f"⚠️ هذا الملف مخزن مسبقاً في هذا القسم.\n"
            f"📂 إجمالي الملفات المخزنة في هذا القسم: **{file_count}** ملف",
            parse_mode="Markdown"
        )

# ============================================================
# 🖱️ معالجة الأزرار وإرسال الملفات
# ============================================================

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "main_menu":
        await query.edit_message_text(
            "🎓 اختر المادة المطلوبة:",
            reply_markup=main_menu_keyboard()
        )
        return

    if data.startswith("subject_"):
        subject = data.replace("subject_", "", 1)
        if subject not in SUBJECTS_INFO:
            await query.edit_message_text("❌ المادة غير موجودة.")
            return

        subject_info = SUBJECTS_INFO[subject]
        await query.edit_message_text(
            f"📚 {subject_info['name']}\n\nاختر القسم المطلوب:",
            reply_markup=subject_keyboard(subject)
        )
        return

    if data.startswith("file|"):
        _, subject, chapter = data.split("|", 2)

        # جلب الملفات من قاعدة بيانات SQLite
        file_list = get_files_from_db(subject, chapter)

        if not file_list:
            await query.message.reply_text("⚠️ عذراً، لا توجد ملفات مرفوعة لهذا القسم حتى الآن.")
            return

        subject_name = SUBJECTS_INFO[subject]["name"]
        chapter_name = SUBJECTS_INFO[subject]["chapters"][chapter]

        await query.message.reply_text(f"📁 جاري إرسال ملفات ({subject_name} — {chapter_name})... عددها: {len(file_list)}")

        for index, file_id in enumerate(file_list, start=1):
            await context.bot.send_document(
                chat_id=query.message.chat_id,
                document=file_id,
                caption=f"📚 {subject_name}\n📖 {chapter_name} (ملف رقم {index})\n\n✅ بالتوفيق!"
            )

# ============================================================
# ▶️ التشغيل الأساسي
# ============================================================

def main():
    # تجهيز قاعدة البيانات عند بدء التشغيل
    init_db()
    bot_token = os.environ.get("TOKEN") or os.environ.get("BOT_TOKEN")
    app = Application.builder().token(bot_token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_click))
    app.add_handler(MessageHandler(filters.Document.ALL, auto_save_file))

    print("⚡ البوت يعمل الآن بقاعدة بيانات SQLite الثابتة والمستقرة...")
    app.run_polling()

if __name__ == "__main__":
    main()
