import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_USERNAME = "@Axyoy"
ADMIN_ID = 6888248201
users = set()

async def is_member(bot, user_id):
    try:
        member = await bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):  
    users.add(update.effective_user.id)
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
        [InlineKeyboardButton("📢 ارسال همگانی", callback_data="broadcast")]
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
            f"👥 تعداد کاربران: {len(users)}"
        )

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(check, pattern="check"))
app.add_handler(CommandHandler("panel", panel))
app.add_handler(CallbackQueryHandler(admin_buttons, pattern="^(user_count|broadcast)$"))

print("Bot is running...")
app.run_polling()
