import os
import logging
import json
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler, ConversationHandler, filters
)
from db import db, get_user, update_user
from handlers.profile import (
    start_profile, profile_menu, gender_cb, region_cb, country_cb, 
    ASK_GENDER, ASK_REGION, ASK_COUNTRY, PROFILE_MENU
)
from handlers.premium import start_upgrade, handle_proof, admin_callback
from handlers.chat import process_message
from handlers.report import report_partner
from handlers.admincmds import (
    admin_block, admin_unblock, admin_message, admin_stats, admin_blockword, admin_unblockword,
    admin_userinfo, admin_roominfo, admin_viewhistory, admin_setpremium
)
from handlers.match import find_command, search_conv, end_command, next_command
from handlers.forward import forward_to_admin
from admin import downgrade_expired_premium
from handlers.message_router import route_message

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
ADMIN_GROUP_ID = int(os.getenv("ADMIN_GROUP_ID"))
LOCALE_DIR = os.path.join(os.path.dirname(__file__), "locales")

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

LANGS = {
    "en": "English",
    "ar": "Arabic",
    "hi": "Hindi",
    "id": "Indonesian"
}

def load_locale(lang):
    path = os.path.join(LOCALE_DIR, f"{lang}.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

async def reply_translated(update, context, key, **kwargs):
    user = update.effective_user
    lang = "en"
    dbuser = await get_user(user.id)
    if dbuser and dbuser.get("language"):
        lang = dbuser["language"]
    locale = load_locale(lang)
    msg = locale.get(key, key)
    if kwargs:
        msg = msg.format(**kwargs)
    await update.message.reply_text(msg)

async def start(update: Update, context):
    # Language selection on /start
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(locale, callback_data=f"lang_{code}")]
        for code, locale in LANGS.items()
    ])
    await update.message.reply_text(
        load_locale("en")["welcome"],
        reply_markup=kb
    )

async def language_select_callback(update: Update, context):
    query = update.callback_query
    await query.answer()
    lang = query.data.split("_", 1)[1]
    await update_user(query.from_user.id, {"language": lang})
    locale = load_locale(lang)
    kb = InlineKeyboardMarkup([[InlineKeyboardButton(locale["menu_back"], callback_data="back")]])
    await query.edit_message_text(locale["profile_setup"], reply_markup=kb)
    # Now go to profile setup
    await start_profile(update, context)

async def check_blocked(update: Update, context):
    user = update.effective_user
    dbuser = await db.users.find_one({"user_id": user.id})
    if dbuser and dbuser.get("blocked"):
        await reply_translated(update, context, "user_blocked", user_id=user.id)
        return True
    return False

def is_admin(update: Update):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    return user_id == ADMIN_ID or chat_id == ADMIN_GROUP_ID

async def error_handler(update, context):
    logger.error(msg="Exception while handling an update:", exc_info=context.error)

async def set_admin_flag(update: Update, context):
    ADMIN_ID = context.application.bot_data.get("ADMIN_ID")
    ADMIN_GROUP_ID = context.application.bot_data.get("ADMIN_GROUP_ID")
    user_id = update.effective_user.id if update.effective_user else None
    chat_id = update.effective_chat.id if update.effective_chat else None
    if user_id == ADMIN_ID or chat_id == ADMIN_GROUP_ID:
        context.user_data["is_admin"] = True
    else:
        context.user_data["is_admin"] = False

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.bot_data["ADMIN_GROUP_ID"] = ADMIN_GROUP_ID
    app.bot_data["ADMIN_ID"] = ADMIN_ID

    app.add_handler(MessageHandler(filters.ALL, set_admin_flag), group=-1)

    # Language selection keyboard
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(language_select_callback, pattern="^lang_"))

    # Profile setup conversation
    profile_conv = ConversationHandler(
        entry_points=[CommandHandler('profile', start_profile)],
        states={
            PROFILE_MENU: [CallbackQueryHandler(profile_menu, pattern="^edit_profile$")],
            ASK_GENDER: [CallbackQueryHandler(gender_cb, pattern="^gender_")],
            ASK_REGION: [CallbackQueryHandler(region_cb, pattern="^region_")],
            ASK_COUNTRY: [CallbackQueryHandler(country_cb, pattern="^country_")]
        },
        fallbacks=[]
    )
    app.add_handler(profile_conv)

    # Add premium search conversation
    app.add_handler(search_conv)

    # Admin commands
    app.add_handler(CommandHandler("block", admin_block, filters.User(ADMIN_ID) | filters.Chat(ADMIN_GROUP_ID)))
    app.add_handler(CommandHandler("unblock", admin_unblock, filters.User(ADMIN_ID) | filters.Chat(ADMIN_GROUP_ID)))
    app.add_handler(CommandHandler("message", admin_message, filters.User(ADMIN_ID) | filters.Chat(ADMIN_GROUP_ID)))
    app.add_handler(CommandHandler("stats", admin_stats, filters.User(ADMIN_ID) | filters.Chat(ADMIN_GROUP_ID)))
    app.add_handler(CommandHandler("blockword", admin_blockword, filters.User(ADMIN_ID) | filters.Chat(ADMIN_GROUP_ID)))
    app.add_handler(CommandHandler("unblockword", admin_unblockword, filters.User(ADMIN_ID) | filters.Chat(ADMIN_GROUP_ID)))
    app.add_handler(CommandHandler("userinfo", admin_userinfo, filters.User(ADMIN_ID) | filters.Chat(ADMIN_GROUP_ID)))
    app.add_handler(CommandHandler("roominfo", admin_roominfo, filters.User(ADMIN_ID) | filters.Chat(ADMIN_GROUP_ID)))
    app.add_handler(CommandHandler("viewhistory", admin_viewhistory, filters.User(ADMIN_ID) | filters.Chat(ADMIN_GROUP_ID)))
    app.add_handler(CommandHandler("setpremium", admin_setpremium, filters.User(ADMIN_ID) | filters.Chat(ADMIN_GROUP_ID)))
    app.add_handler(CommandHandler("promote", admin_setpremium, filters.User(ADMIN_ID) | filters.Chat(ADMIN_GROUP_ID)))

    # User commands
    app.add_handler(CommandHandler("profile", start_profile))
    app.add_handler(CommandHandler("upgrade", start_upgrade))
    app.add_handler(CommandHandler("report", report_partner))
    app.add_handler(CommandHandler("find", find_command))
    app.add_handler(CommandHandler("end", end_command))
    app.add_handler(CommandHandler("next", next_command))

    # Admin approve/decline callback
    app.add_handler(CallbackQueryHandler(admin_callback))

    # Premium proof
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.ALL, handle_proof))

    app.add_handler(MessageHandler(~filters.COMMAND, route_message))
    app.add_error_handler(error_handler)

    async def expiry_job(context):
        await downgrade_expired_premium()
    app.job_queue.run_repeating(expiry_job, interval=3600, first=10)

    logger.info("AnonindoChat Bot started (polling).")
    app.run_polling()

if __name__ == "__main__":
    main()
