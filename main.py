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


async def is_member(bot, user_id):
    try:
        member = await bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
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


app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(check, pattern="check"))

print("Bot is running...")
app.run_polling()
