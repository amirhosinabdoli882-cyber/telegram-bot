import os
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)
from telegram.ext import MessageHandler, filters

TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_USERNAME = "@Axyoy"
ADMIN_ID = 6888248201
conn = sqlite3.connect("users.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS banned_users (
    user_id INTEGER PRIMARY KEY
)
""")

conn.commit()


def save_user(user_id):
    cursor.execute(
        "INSERT OR IGNORE INTO users (user_id) VALUES (?)",
        (user_id,)
    )
    conn.commit()

def get_users():
    cursor.execute("SELECT user_id FROM users")
    return [row[0] for row in cursor.fetchall()]


def ban_user(user_id):
    cursor.execute(
        "INSERT OR IGNORE INTO banned_users (user_id) VALUES (?)",
        (user_id,)
    )
    conn.commit()
def unban_user(user_id):
    cursor.execute(
        "DELETE FROM banned_users WHERE user_id=?",
        (user_id,)
    )
    conn.commit()

def is_banned(user_id):
    cursor.execute(
        "SELECT 1 FROM banned_users WHERE user_id=?",
        (user_id,)
    )
    return cursor.fetchone() is not None


broadcast_mode = set()
maintenance_mode = False
async def is_member(bot, user_id):
    try:
        member = await bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    save_user(update.effective_user.id)
    if maintenance_mode and update.effective_user.id != ADMIN_ID:
        await update.message.reply_text(
            "🛠 ربات در حال تعمیر و بروزرسانی است.\nلطفاً بعداً دوباره تلاش کنید."
        )
        return
    if is_banned(update.effective_user.id):
        await update.message.reply_text(
            "⛔ شما از استفاده از این ربات مسدود شده‌اید."
        )
        return

    keyboard = [
        [InlineKeyboardButton("📢 عضویت در کانال", url="https://t.me/Axyoy")],
        [InlineKeyboardButton("✅ عضو شدم", callback_data="check")]
    ]

    if await is_member(context.bot, update.effective_user.id):
        await update.message.reply_text("✅ خوش اومدی، عضویتت تأیید شد.")
    else:
        await update.message.reply_text(
            "سلام 👋\n\nلطفاً ابتدا عضو کانال شوید.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    if await is_member(context.bot, update.effective_user.id):
        await update.message.reply_text("✅ خوش اومدی، عضویتت تأیید شد.")
    else:
        await update.message.reply_text(
            "سلام 👋\n\nلطفاً ابتدا عضو کانال شوید.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


async def check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if await is_member(context.bot, query.from_user.id):
        await query.edit_message_text("✅ عضویت شما تأیید شد. خوش اومدی!")
    else:
        await query.answer(
            "❌ هنوز عضو کانال نشدی.",
            show_alert=True
        )
async def panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ دسترسی ندارید")
        return

    keyboard = [
    [InlineKeyboardButton("👥 تعداد کاربران", callback_data="user_count")],
    [InlineKeyboardButton("📢 ارسال همگانی", callback_data="broadcast")],
    [InlineKeyboardButton("🛠 حالت تعمیر", callback_data="maintenance")]
]

    await update.message.reply_text(
        "🎛 پنل مدیریت",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
async def admin_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        return

    if query.data == "user_count":
        await query.edit_message_text(
            f"👥 تعداد کاربران: {len(get_users())}"
        )

    elif query.data == "broadcast":
        broadcast_mode.add(query.from_user.id)

        await query.edit_message_text(
            "📢 پیام همگانی را ارسال کنید:"
        )
async def broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in broadcast_mode:
        return

    text = update.message.text

    for user_id in get_users():
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=text
            )
        except:
            pass

    broadcast_mode.remove(update.effective_user.id)
    await update.message.reply_text("✅ پیام برای همه ارسال شد.")
async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    if len(context.args) != 1:
        await update.message.reply_text("استفاده:\n/ban USER_ID")
        return

    try:
        user_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ آیدی نامعتبر است.")
        return

    ban_user(user_id)
    await update.message.reply_text("✅ کاربر مسدود شد.")


async def unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    if len(context.args) != 1:
        await update.message.reply_text("استفاده:\n/unban USER_ID")
        return

    try:
        user_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ آیدی نامعتبر است.")
        return

    unban_user(user_id)
    await update.message.reply_text("✅ کاربر از بن خارج شد.")


app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("panel", panel))
app.add_handler(CommandHandler("ban", ban))
app.add_handler(CommandHandler("unban", unban))
app.add_handler(CallbackQueryHandler(check, pattern="check"))
app.add_handler(CallbackQueryHandler(admin_buttons, pattern="^(user_count|broadcast)$"))

app.add_handler(MessageHandler(filters.TEXT, broadcast_message))

print("Bot is running...")
app.run_polling()
