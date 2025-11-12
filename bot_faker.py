!pip install python-telegram-bot==21.6 faker nest_asyncio --quiet

import logging
import secrets
import string
import nest_asyncio
import asyncio
from faker import Faker
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

nest_asyncio.apply()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.DEBUG,
)
logger = logging.getLogger(__name__)

TOKEN = "your_token_here"

if not TOKEN:
    raise RuntimeError("invalid token")

faker = Faker("en_US")

def generate_password(length: int = 12, use_symbols: bool = True) -> str:
    alphabet = string.ascii_letters + string.digits
    if use_symbols:
        alphabet += "!@#$%^&*()-_=+"
    return "".join(secrets.choice(alphabet) for _ in range(length))

def generate_user() -> dict:
    return {
        "name": faker.name(),
        "email": faker.email(),
        "phone": faker.phone_number(),
        "password": generate_password(),
    }

def main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("generate user", callback_data="generate")],
        [InlineKeyboardButton("stop", callback_data="stop")]
    ])

def user_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("generate another", callback_data="generate")],
        [InlineKeyboardButton("stop", callback_data="stop")]
    ])

async def safe_reply(update: Update, text: str, **kwargs):
    if update.effective_message:
        await update.effective_message.reply_html(text, **kwargs)
    elif update.callback_query and update.callback_query.message:
        await update.callback_query.message.reply_html(text, **kwargs)
    else:
        logger.warning("Нет места для ответа (update не содержит message/callback.message): %s", update)

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("Received /start update: chat_id=%s user=%s",
                update.effective_chat.id if update.effective_chat else None,
                update.effective_user.id if update.effective_user else None)
    text = (
        "hi! i'll generate you a test user🧑‍💻\n\n"
        "press <b>generate user</b> to get one"
    )
    await safe_reply(update, text, reply_markup=main_keyboard())

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cq = update.callback_query
    if not cq:
        logger.warning("button_handler вызван без callback_query: %s", update)
        return
    logger.debug("CallbackQuery from chat_id=%s data=%s", update.effective_chat.id if update.effective_chat else None, cq.data)
    await cq.answer()  

    if cq.data == "generate":
        user = generate_user()
        msg = (
            "<b>Generated test user</b>\n\n"
            f"👤 name: <code>{user['name']}</code>\n"
            f"📧 email: <code>{user['email']}</code>\n"
            f"📱 phone: <code>{user['phone']}</code>\n"
            f"🔑 password: <code>{user['password']}</code>\n\n"
            "press 'generate another' for more"
        )
        if cq.message:
            await cq.message.reply_html(msg, reply_markup=user_keyboard())
        else:
            await safe_reply(update, msg, reply_markup=user_keyboard())

    elif cq.data == "stop":
        await safe_reply(update, "ok, press /start to continue")

async def log_all_updates(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.debug("RAW update handler: %s", update)
    if update.effective_message and update.effective_message.text:
        text = update.effective_message.text.strip().lower()
        if text == "ping":
            await update.effective_message.reply_text("pong")

async def main_app():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.ALL, log_all_updates))

    logger.info("Starting bot: run_polling()")
    await app.run_polling()

try:
    asyncio.run(main_app())
except RuntimeError as e:
    logger.warning("asyncio.run failed (%s). Falling back to creating task in existing loop.", e)
    loop = asyncio.get_event_loop()
    loop.create_task(main_app())

