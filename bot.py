
import os, logging
from dotenv import load_dotenv
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ConversationHandler
load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')
TARGET_GROUP_ID = int(os.getenv('TARGET_GROUP_ID') or 0)
if not BOT_TOKEN:
    raise RuntimeError('BOT_TOKEN must be set')
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
from handlers.profile import start_profile, gender_cb, region_text, country_text, ASK_GENDER, ASK_REGION, ASK_COUNTRY
from handlers.chat import find_handler, stop_handler, relay
from handlers.premium import start_upgrade, handle_proof, admin_callback
def build_app():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.bot_data['TARGET_GROUP_ID'] = TARGET_GROUP_ID
    app.add_handler(CommandHandler('start', lambda u,c: u.message.reply_text('Welcome — use /find to find partner')))
    conv = ConversationHandler(
        entry_points=[CommandHandler('profile', start_profile)],
        states={
            ASK_GENDER: [CallbackQueryHandler(gender_cb, pattern=r'^gender_')],
            ASK_REGION: [MessageHandler(filters.TEXT & ~filters.COMMAND, region_text)],
            ASK_COUNTRY: [MessageHandler(filters.TEXT & ~filters.COMMAND, country_text)],
        },
        fallbacks=[],
        allow_reentry=True,
    )
    app.add_handler(conv)
    app.add_handler(CommandHandler('find', find_handler))
    app.add_handler(CommandHandler('stop', stop_handler))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, relay))
    app.add_handler(CommandHandler('upgrade', start_upgrade))
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.ALL, handle_proof))
    app.add_handler(CallbackQueryHandler(admin_callback, pattern=r'^(approve:|decline:)'))
    return app
if __name__ == '__main__':
    app = build_app()
    logger.info('Starting bot') 
    app.run_polling()
