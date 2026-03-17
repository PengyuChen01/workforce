"""Telegram Bot - connects Telegram to the voice agent.

Run standalone:
    python3 -m services.telegram_bot
"""

import os
import re
import logging

from dotenv import load_dotenv

load_dotenv()

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
    ConversationHandler,
)

from services.channel import process_message
from services.user_store import get_user_email, set_user_email
from skills.registry import list_skills

logger = logging.getLogger("telegram-bot")
logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

# Conversation states
WAITING_EMAIL = 1


# ---------- Helpers ----------

def _user_id(update: Update) -> str:
    return str(update.effective_user.id)


def _username(update: Update) -> str:
    u = update.effective_user
    return u.username or u.first_name or str(u.id)


# ---------- /start flow ----------

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start - check if user has email, if not ask for it."""
    uid = _user_id(update)
    email = get_user_email("telegram", uid)

    if email:
        skills = list_skills()
        skill_lines = "\n".join(f"  - *{s['name']}*: {s['description']}" for s in skills)
        await update.message.reply_text(
            f"Welcome back! Your email is set to `{email}`.\n\n"
            f"I can help with:\n{skill_lines}\n\n"
            f"Send me text or voice messages!\n"
            f"Use /email to change your email.",
            parse_mode="Markdown",
        )
        return ConversationHandler.END

    await update.message.reply_text(
        "Hi! I'm your AI voice agent.\n\n"
        "Before we start, what's your email address?\n"
        "I'll use it when you say things like \"send to my email\"."
    )
    return WAITING_EMAIL


async def receive_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive and validate the user's email during onboarding."""
    text = update.message.text.strip()

    # Simple email validation
    if not re.match(r'^[\w.+-]+@[\w-]+\.[\w.-]+$', text):
        await update.message.reply_text(
            "That doesn't look like a valid email. Please try again:"
        )
        return WAITING_EMAIL

    uid = _user_id(update)
    set_user_email("telegram", uid, text)

    skills = list_skills()
    skill_lines = "\n".join(f"  - *{s['name']}*: {s['description']}" for s in skills)
    await update.message.reply_text(
        f"Got it! Your email is set to `{text}`.\n\n"
        f"I can help with:\n{skill_lines}\n\n"
        f"Send me text or voice messages! Try saying:\n"
        f"  \"Send an email to my mailbox with subject Hello\"\n"
        f"  \"Schedule a meeting with Alice tomorrow\"\n\n"
        f"Use /email to change your email anytime.",
        parse_mode="Markdown",
    )
    return ConversationHandler.END


async def cancel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Cancelled. Use /start to try again.")
    return ConversationHandler.END


# ---------- /email command ----------

async def email_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set or update email via /email <address>."""
    uid = _user_id(update)
    args = context.args

    if not args:
        current = get_user_email("telegram", uid)
        if current:
            await update.message.reply_text(
                f"Your current email: `{current}`\n\n"
                f"To change it: /email your@new-email.com",
                parse_mode="Markdown",
            )
        else:
            await update.message.reply_text(
                "No email set yet.\n\nUsage: /email your@email.com"
            )
        return

    email = args[0].strip()
    if not re.match(r'^[\w.+-]+@[\w-]+\.[\w.-]+$', email):
        await update.message.reply_text("Invalid email format. Try again.")
        return

    set_user_email("telegram", uid, email)
    await update.message.reply_text(f"Email updated to `{email}`", parse_mode="Markdown")


# ---------- /skills command ----------

async def skills_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    skills = list_skills()
    lines = "\n".join(f"- *{s['name']}*: {s['description']}" for s in skills)
    await update.message.reply_text(f"Available skills:\n{lines}", parse_mode="Markdown")


# ---------- Message handlers ----------

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming text messages."""
    uid = _user_id(update)
    user_text = update.message.text
    user_email = get_user_email("telegram", uid) or ""

    # If no email set, nudge them
    if not user_email:
        await update.message.reply_text(
            "Please set your email first with /start or /email your@email.com"
        )
        return

    logger.info("[telegram] user=%s: %s", _username(update), user_text)
    await update.message.chat.send_action("typing")

    result = await process_message(user_text, channel="telegram", user_email=user_email)

    reply = result.get("response_text", "Sorry, something went wrong.")
    skill = result.get("selected_skill", "")
    if skill:
        reply = f"[{skill}]\n\n{reply}"

    await update.message.reply_text(reply)


async def voice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming voice messages."""
    uid = _user_id(update)
    user_email = get_user_email("telegram", uid) or ""

    if not user_email:
        await update.message.reply_text(
            "Please set your email first with /start or /email your@email.com"
        )
        return

    logger.info("[telegram] voice from user=%s", _username(update))
    await update.message.chat.send_action("typing")

    voice = update.message.voice
    voice_file = await voice.get_file()
    audio_bytes = await voice_file.download_as_bytearray()

    from services.stt import transcribe
    transcript = await transcribe(bytes(audio_bytes), filename="voice.ogg")
    logger.info("[telegram] transcript: %s", transcript)

    result = await process_message(transcript, channel="telegram", user_email=user_email)

    reply = result.get("response_text", "Sorry, something went wrong.")
    skill = result.get("selected_skill", "")

    response = f"*Heard:* _{transcript}_\n\n"
    if skill:
        response += f"[{skill}]\n\n"
    response += reply

    await update.message.reply_text(response, parse_mode="Markdown")


# ---------- Bot startup ----------

def start_bot():
    """Start the Telegram bot (blocking)."""
    if not TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not set in .env")
        return

    logger.info("Starting Telegram bot...")
    app = ApplicationBuilder().token(TOKEN).build()

    # Onboarding conversation (asks for email)
    onboarding = ConversationHandler(
        entry_points=[CommandHandler("start", start_handler)],
        states={
            WAITING_EMAIL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_email),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_handler)],
    )

    app.add_handler(onboarding)
    app.add_handler(CommandHandler("email", email_cmd))
    app.add_handler(CommandHandler("skills", skills_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    app.add_handler(MessageHandler(filters.VOICE, voice_handler))

    logger.info("Telegram bot is running!")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    start_bot()
