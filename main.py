from telegram import InlineKeyboardButton, InlineKeyboardMarkup

ADMIN_ID = 6888248201

async def panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ شما دسترسی به پنل مدیریت ندارید.")
        return

    keyboard = [
        [InlineKeyboardButton("📢 ارسال همگانی", callback_data="broadcast")],
        [InlineKeyboardButton("📊 آمار ربات", callback_data="stats")],
        [InlineKeyboardButton("📢 مدیریت کانال‌ها", callback_data="channels")],
        [InlineKeyboardButton("⚙️ تنظیمات", callback_data="settings")]
    ]

    await update.message.reply_text(
        "👑 پنل مدیریت",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

app.add_handler(CommandHandler("panel", panel))
