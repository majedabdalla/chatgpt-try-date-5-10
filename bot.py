import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler, ConversationHandler, filters
)
from db import db
from handlers.profile import (
    start_profile, profile_menu, gender_cb, region_cb, country_cb, 
    ASK_GENDER, ASK_REGION, ASK_COUNTRY, PROFILE_MENU
)
from handlers.premium import start_upgrade, handle_proof, admin_callback
from handlers.chat import process_message
from handlers.report import report_partner
from handlers.admincmds import (
    admin_block, admin_unblock, admin_message, admin_stats, admin_blockword, admin_unblockword,
    admin_userinfo, admin_roominfo, admin_viewhistory
)
from handlers.match import find_command, search_conv
from handlers.forward import forward_to_admin  # <-- Only import, DO NOT define again!
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

# --- ADMIN FLAG HANDLER FUNCTION ---
async def set_admin_flag(update: Update, context):
    ADMIN_ID = context.application.bot_data.get("ADMIN_ID")
    ADMIN_GROUP_ID = context.application.bot_data.get("ADMIN_GROUP_ID")
    user_id = update.effective_user.id if update.effective_user else None
    chat_id = update.effective_chat.id if update.effective_chat else None
    if user_id == ADMIN_ID or chat_id == ADMIN_GROUP_ID:
        context.user_data["is_admin"] = True
    else:
        context.user_data["is_admin"] = False
# --- END ADMIN FLAG HANDLER FUNCTION ---

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.bot_data["ADMIN_GROUP_ID"] = ADMIN_GROUP_ID
    app.bot_data["ADMIN_ID"] = ADMIN_ID  # For set_admin_flag

    # --- REGISTER ADMIN FLAG HANDLER FIRST! ---
    app.add_handler(MessageHandler(filters.ALL, set_admin_flag), group=-1)

    # Conversation for profile setup (MUST be first after admin flag!)
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
    app.add_handler(profile_conv)  # <-- This must be first after admin flag!

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

    # User commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("profile", start_profile))
    app.add_handler(CommandHandler("upgrade", start_upgrade))
    app.add_handler(CommandHandler("report", report_partner))
    app.add_handler(CommandHandler("find", find_command))  # <-- Add /find here

    # Admin approve/decline callback (should come AFTER profile_conv!)
    app.add_handler(CallbackQueryHandler(admin_callback))

    # Premium proof (must be after conversation handler)
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.ALL, handle_proof))

    # Register the universal forward-to-admin handler for ALL non-command messages:
    app.add_handler(MessageHandler(~filters.COMMAND, forward_to_admin), group=0)  # <--- ALL message types except commands

    # Chat message handler (for actual in-room chat)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_message), group=1)

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
