import os
import sqlite3
import asyncio
import re
import tempfile
import yt_dlp
import subprocess
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
try:
    cursor.execute("ALTER TABLE users ADD COLUMN points INTEGER DEFAULT 0")
    conn.commit()
except sqlite3.OperationalError:
    pass
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

def change_points(user_id, amount):
    cursor.execute(
        "UPDATE users SET points = COALESCE(points, 0) + ? WHERE user_id = ?",
        (amount, user_id)
    )
    conn.commit()

def get_points(user_id):
    cursor.execute(
        "SELECT points FROM users WHERE user_id=?",
        (user_id,)
    )
    row = cursor.fetchone()
    return row[0] if row else 0    

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
gamble_games = {}
async def is_member(bot, user_id):
    try:
        member = await bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False
async def delete_luck_game(context, chat_id, message_id):
    await asyncio.sleep(60)

    if chat_id in gamble_games:
        del gamble_games[chat_id]

        try:
            await context.bot.delete_message(
                chat_id=chat_id,
                message_id=message_id
            )
        except:
            pass
def download_instagram(url):
    temp_dir = tempfile.mkdtemp()

    ydl_opts = {
        "outtmpl": os.path.join(temp_dir, "%(id)s.%(ext)s"),
        "format": "bestvideo+bestaudio/best",
        "merge_output_format": "mp4",
        "noplaylist": True,
        "quiet": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        video_path = ydl.prepare_filename(info)

        if not video_path.endswith(".mp4"):
            video_path = os.path.splitext(video_path)[0] + ".mp4"

    return video_path, temp_dir
async def instagram_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    match = re.search(
        r"https?://(?:www\.)?instagram\.com/(?:reel|p|tv)/[^\s]+",
        text
    )

    if not match:
        return

    url = match.group(0)

    status = await update.message.reply_text(
        "⏳ در حال دریافت ویدئو..."
    )

    video_path = None
    temp_dir = None

    try:
        video_path, temp_dir = download_instagram(url)

        # ارسال ویدئو
        with open(video_path, "rb") as video:
            await update.message.reply_video(
                video=video,
                caption="🎬 ویدئو"
            )

        # استخراج صدا با FFmpeg
        audio_path = os.path.splitext(video_path)[0] + ".mp3"

        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                video_path,
                "-vn",
                "-codec:a",
                "libmp3lame",
                "-b:a",
                "192k",
                audio_path
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        # ارسال صدا
        with open(audio_path, "rb") as audio:
            await update.message.reply_audio(
                audio=audio,
                caption="🎵 صدای ویدئو"
            )

    except Exception as e:
        await update.message.reply_text(
            f"❌ خطا:\n{str(e)[:3000]}"
        )

    finally:
        if temp_dir:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

        try:
            await status.delete()
        except:
            pass
async def luck_accept(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if maintenance_mode and update.effective_user.id != ADMIN_ID:
        await update.callback_query.answer(
            "🛠 ربات در حال تعمیر است.",
            show_alert=True
        )
        return

    query = update.callback_query
    await query.answer()

    chat_id = query.message.chat_id
    accepter = query.from_user

    if accepter.id not in get_users():
        await query.answer(
            "⛔ ابتدا ربات را استارت کنید.",
            show_alert=True
        )
        return

    if not await is_member(context.bot, accepter.id):
        await query.answer(
            "⛔ برای بازی باید عضو کانال باشید.",
            show_alert=True
        )
        return

    if chat_id not in gamble_games:
        await query.answer(
            "❌ این بازی دیگر فعال نیست.",
            show_alert=True
        )
        return

    game = gamble_games[chat_id]

    if accepter.id == game["creator_id"]:
        await query.answer(
            "❌ خودت نمی‌تونی بازی خودت رو قبول کنی!",
            show_alert=True
        )
        return

    creator_name = game["creator_name"]

    await query.edit_message_text(
        f"🍀 بازی شانس شروع شد!\n\n"
        f"👤 {creator_name}\n"
        f"👤 {accepter.first_name}\n\n"
        "🎲 تاس‌ها در حال پرتاب هستند..."
    )

    creator_dice = await context.bot.send_dice(
        chat_id=chat_id,
        emoji="🎲"
    )

    accepter_dice = await context.bot.send_dice(
        chat_id=chat_id,
        emoji="🎲"
    )

    creator_score = creator_dice.dice.value
    accepter_score = accepter_dice.dice.value

    if creator_score > accepter_score:
        change_points(game["creator_id"], 3)
        change_points(accepter.id, -2)

        result = (
            f"🏆 {creator_name} برنده شد!\n"
            f"🎯 {creator_name}: +3 امتیاز\n"
            f"💀 {accepter.first_name}: -2 امتیاز"
        )

    elif accepter_score > creator_score:
        change_points(game["creator_id"], -2)
        change_points(accepter.id, 3)

        result = (
            f"🏆 {accepter.first_name} برنده شد!\n"
            f"🎯 {accepter.first_name}: +3 امتیاز\n"
            f"💀 {creator_name}: -2 امتیاز"
        )

    else:
        change_points(game["creator_id"], 1)
        change_points(accepter.id, 1)

        result = (
            "🤝 مساوی شد!\n"
            "🎯 هر دو بازیکن: +1 امتیاز"
        )

    creator_points = get_points(game["creator_id"])
    accepter_points = get_points(accepter.id)

    await context.bot.send_message(
        chat_id=chat_id,
        text=(
            f"🍀 نتیجه بازی شانس\n\n"
            f"👤 {creator_name}: 🎲 {creator_score}\n"
            f"👤 {accepter.first_name}: 🎲 {accepter_score}\n\n"
            f"{result}\n\n"
            f"📊 امتیاز {creator_name}: {creator_points}\n"
            f"📊 امتیاز {accepter.first_name}: {accepter_points}"
        )
    )

    del gamble_games[chat_id]
async def luck_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if maintenance_mode and update.effective_user.id != ADMIN_ID:
        await update.message.reply_text(
            "🛠 ربات در حال تعمیر و بروزرسانی است.\nلطفاً بعداً دوباره تلاش کنید."
        )
        return

    if update.effective_chat.type not in ["group", "supergroup"]:
        return

    user = update.effective_user
    chat_id = update.effective_chat.id

    if user.id not in get_users():
        await update.message.reply_text(
            "⛔ برای بازی شانس ابتدا ربات را استارت کنید."
        )
        return

    if not await is_member(context.bot, user.id):
        await update.message.reply_text(
            "⛔ برای بازی شانس باید ابتدا عضو کانال باشید."
        )
        return

    if chat_id in gamble_games:
        await update.message.reply_text(
            "🍀 یک بازی شانس همین الان در این گروه در حال انتظار است."
        )
        return

    gamble_games[chat_id] = {
        "creator_id": user.id,
        "creator_name": user.first_name
    }

    keyboard = [
        [
            InlineKeyboardButton(
                "🎲 قبول بازی",
                callback_data=f"luck_accept_{user.id}"
            )
        ]
    ]

    sent_message = await update.message.reply_text(
        f"🍀 {user.first_name} بازی شانس پیشنهاد داد!\n\n"
        "چه کسی قبول می‌کند؟",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    asyncio.create_task(
        delete_luck_game(
            context,
            chat_id,
            sent_message.message_id
        )
    )
async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton(
                "📥 ارسال ویدئوی اینستاگرام",
                callback_data="instagram_help"
            )
        ],
        [
            InlineKeyboardButton(
                "🏆 دیدن لیدربورد",
                callback_data="show_leaderboard"
            )
        ]
    ]

    text = (
        "🎉 خوش اومدی رفیق! 😎\n\n"
        "✨ عضویتت با موفقیت تأیید شد.\n\n"
        "یکی از گزینه‌های زیر رو انتخاب کن 👇"
    )

    if update.callback_query:
        await update.callback_query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )    
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
        
async def check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if await is_member(context.bot, query.from_user.id):
        await main_menu(update, context)
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
async def menu_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "instagram_help":
        keyboard = [
            [
                InlineKeyboardButton(
                    "🔙 بازگشت",
                    callback_data="back_menu"
                )
            ]
        ]

        await query.edit_message_text(
            "📥 ارسال ویدئوی اینستاگرام\n\n"
            "🔗 فقط لینک پست یا ریلز اینستاگرام رو همینجا بفرست.\n\n"
            "🎬 ربات ویدئو رو دریافت می‌کنه و برات ارسال می‌کنه.\n"
            "🎵 صدای ویدئو هم جداگانه برات فرستاده میشه.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data == "show_leaderboard":
        cursor.execute("""
            SELECT first_name, points
            FROM users
            ORDER BY points DESC
            LIMIT 30
        """)

        users = cursor.fetchall()

        if not users:
            text = "🏆 هنوز کسی امتیازی ندارد."
        else:
            text = "🏆 جدول ۳۰ نفر برتر\n\n"
            medals = ["🥇", "🥈", "🥉"]

            for index, (name, points) in enumerate(users, start=1):
                name = name or "کاربر"

                if index <= 3:
                    rank = medals[index - 1]
                else:
                    rank = f"{index}."

                text += f"{rank} {name} — 🎯 {points}\n"

        keyboard = [
            [
                InlineKeyboardButton(
                    "🔙 بازگشت",
                    callback_data="back_menu"
                )
            ]
        ]

        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data == "back_menu":
        await main_menu(update, context)    
async def admin_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global maintenance_mode

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

    elif query.data == "maintenance":
        maintenance_mode = not maintenance_mode

        if maintenance_mode:
            await query.edit_message_text(
                "🛠 حالت تعمیر فعال شد."
            )
        else:
            await query.edit_message_text(
                "✅ حالت تعمیر خاموش شد."
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
async def score(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if user.id not in get_users():
        await update.message.reply_text(
            "⛔ ابتدا ربات را استارت کنید."
        )
        return

    points = get_points(user.id)

    await update.message.reply_text(
        f"🎯 امتیاز شما\n\n"
        f"👤 {user.first_name}\n"
        f"🏆 امتیاز: {points}"
    )
async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cursor.execute("""
        SELECT user_id, points
        FROM users
        ORDER BY points DESC
        LIMIT 30
    """)

    users = cursor.fetchall()

    if not users:
        await update.message.reply_text(
            "🏆 هنوز کسی امتیازی ندارد."
        )
        return

    text = "🏆 جدول برترین بازیکنان شانس\n\n"

    medals = ["🥇", "🥈", "🥉"]

    for index, (user_id, points) in enumerate(users, start=1):
        try:
            member = await context.bot.get_chat_member(
                update.effective_chat.id,
                user_id
            )
            name = member.user.first_name
        except:
            name = f"کاربر {user_id}"

        medal = medals[index - 1] if index <= 3 else f"{index}."

        text += f"{medal} {name} — 🎯 {points}\n"

    await update.message.reply_text(text)    
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("score", score))
app.add_handler(CommandHandler("leaderboard", leaderboard))
app.add_handler(CommandHandler("panel", panel))
app.add_handler(CommandHandler("ban", ban))
app.add_handler(CommandHandler("unban", unban))

app.add_handler(CallbackQueryHandler(check, pattern="check"))

app.add_handler(
    CallbackQueryHandler(
        luck_accept,
        pattern="^luck_accept_"
    )
)

app.add_handler(
    CallbackQueryHandler(
        admin_buttons,
        pattern="^(user_count|broadcast|maintenance)$"
    )
)

app.add_handler(
    MessageHandler(
        filters.TEXT & filters.Regex(r"https?://(?:www\.)?instagram\.com/"),
        instagram_handler
    )
)

app.add_handler(
    MessageHandler(
        filters.TEXT & filters.Regex(r"^شانس$"),
        luck_game
    )
)
app.add_handler(
    CallbackQueryHandler(
        menu_buttons,
        pattern="^(instagram_help|show_leaderboard|back_menu)$"
    )
)
app.add_handler(MessageHandler(filters.TEXT, broadcast_message))

print("Bot is running...")
app.run_polling()
