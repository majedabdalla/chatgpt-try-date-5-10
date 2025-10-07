import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler, ConversationHandler, filters
)
from db import db
from handlers.profile import start_profile, gender_cb, region_text, country_text, prefs_text, ASK_GENDER, ASK_REGION, ASK_COUNTRY, ASK_PREFS
from handlers.premium import start_upgrade, handle_proof, admin_callback
from handlers.chat import process_message
from handlers.report import report_partner
from handlers.admincmds import (
    admin_block, admin_unblock, admin_message, admin_stats, admin_blockword, admin_unblockword,
    admin_userinfo, admin_roominfo, admin_viewhistory
)
from admin import downgrade_expired_premium

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
ADMIN_GROUP_ID = int(os.getenv("ADMIN_GROUP_ID"))

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

async def start(update: Update, context):
    await update.message.reply_text("Welcome! Use /profile to set up your profile.")

async def check_blocked(update: Update, context):
    user = update.effective_user
    dbuser = await db.users.find_one({"user_id": user.id})
    if dbuser and dbuser.get("blocked"):
        await update.message.reply_text("You are blocked. Please contact support for help.")
        return True
    return False

def is_admin(update: Update):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    return user_id == ADMIN_ID or chat_id == ADMIN_GROUP_ID

# Error handler for debugging
async def error_handler(update, context):
    logger.error(msg="Exception while handling an update:", exc_info=context.error)

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.bot_data["ADMIN_GROUP_ID"] = ADMIN_GROUP_ID

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

    # User commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("profile", start_profile))
    app.add_handler(CommandHandler("upgrade", start_upgrade))
    app.add_handler(CommandHandler("report", report_partner))

    # Conversation for profile setup (MUST use named constants)
    profile_conv = ConversationHandler(
        entry_points=[CommandHandler('profile', start_profile)],
        states={
            ASK_GENDER: [CallbackQueryHandler(gender_cb)],
            ASK_REGION: [MessageHandler(filters.TEXT & ~filters.COMMAND, region_text)],
            ASK_COUNTRY: [MessageHandler(filters.TEXT & ~filters.COMMAND, country_text)],
            ASK_PREFS: [MessageHandler(filters.TEXT & ~filters.COMMAND, prefs_text)]
        },
        fallbacks=[]
    )
    app.add_handler(profile_conv)

    # Premium proof (must be after conversation handler)
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.ALL, handle_proof))

    # Admin approve/decline callback (should not interfere with profile conversation)
    app.add_handler(CallbackQueryHandler(admin_callback))

    # Chat message handler (room logic must wire up context.user_data["room_id"])
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_message))

    # Register error handler
    app.add_error_handler(error_handler)

    # Periodic premium expiry downgrade
    async def expiry_job(context):
        await downgrade_expired_premium()
    app.job_queue.run_repeating(expiry_job, interval=3600, first=10)

    logger.info("AnonindoChat Bot started (polling).")
    app.run_polling()

if __name__ == "__main__":
    main()
