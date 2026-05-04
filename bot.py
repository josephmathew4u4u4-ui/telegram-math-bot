import random
import sqlite3
from datetime import date, datetime, timedelta
import asyncio

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = "8694259063:AAEJ046-njelq_ta_rpIpSxDt4Rt3WPASC0"

# ---------------- DATABASE ----------------
conn = sqlite3.connect("math_bot.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    q_index INTEGER,
    score INTEGER,
    level INTEGER,
    last_date TEXT,
    weekly_total INTEGER,
    weekly_days INTEGER
)
""")
conn.commit()

active_sessions = {}


# ---------------- HELPERS ----------------
def get_user(user_id):
    cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    return cursor.fetchone()


def create_user(user_id):
    today = str(date.today())
    cursor.execute(
        "INSERT INTO users VALUES (?, 0, 0, 1, ?, 0, 0)",
        (user_id, today)
    )
    conn.commit()


def update_user(user_id, q_index, score, level, last_date, weekly_total, weekly_days):
    cursor.execute("""
        UPDATE users
        SET q_index=?, score=?, level=?, last_date=?, weekly_total=?, weekly_days=?
        WHERE user_id=?
    """, (q_index, score, level, last_date, weekly_total, weekly_days, user_id))
    conn.commit()


def generate_question(level):
    count = 3 if level == 1 else 4
    nums = [random.randint(10, 99) for _ in range(count)]
    return " + ".join(map(str, nums)), sum(nums)


# ---------------- CORE LOGIC ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    today = str(date.today())

    user = get_user(user_id)

    if not user:
        create_user(user_id)
        user = get_user(user_id)

    _, q_index, score, level, last_date, weekly_total, weekly_days = user

    # 🧠 NEW DAY LOGIC
    if last_date != today:
        if q_index == 10:
            weekly_total += score
            weekly_days += 1

        # 📊 Weekly check (every 7 days)
        if weekly_days >= 7:
            avg = weekly_total / weekly_days
            if avg >= 9:
                level += 1
                await update.message.reply_text("🔥 Weekly Level Up!")

            weekly_total = 0
            weekly_days = 0

        q_index = 0
        score = 0

    update_user(user_id, q_index, score, level, today, weekly_total, weekly_days)

    await update.message.reply_text(
        f"🧠 Daily Maths Started!\nLevel: {level}\n\nAnswer the questions:"
    )

    await send_next_question(update, user_id)


async def send_next_question(update, user_id):
    user = get_user(user_id)
    _, q_index, score, level, *_ = user

    if q_index >= 10:
        await update.message.reply_text(f"🎯 Done! Score: {score}/10")
        return

    question, answer = generate_question(level)

    active_sessions[user_id] = answer

    await update.message.reply_text(f"Q{q_index+1}: {question} = ?")


async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    if user_id not in active_sessions:
        return

    try:
        user_answer = int(text)
    except:
        await update.message.reply_text("❌ Send a number.")
        return

    correct = active_sessions[user_id]

    user = get_user(user_id)
    _, q_index, score, level, last_date, weekly_total, weekly_days = user

    if user_answer == correct:
        score += 1
        await update.message.reply_text("✅ Correct!")
    else:
        await update.message.reply_text(f"❌ Wrong. Answer: {correct}")

    q_index += 1

    update_user(user_id, q_index, score, level, last_date, weekly_total, weekly_days)

    await send_next_question(update, user_id)


# ---------------- MAIN ----------------
async def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer))

    print("Bot is running...")
    await app.initialize()
    await app.start()
    await app.updater.start_polling()

    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())