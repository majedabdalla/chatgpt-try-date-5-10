
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
from storage import load_users, save_users
import logging

logger = logging.getLogger(__name__)

async def start_upgrade(update: Update, context):
    await update.message.reply_text('Please upload proof (photo or document)')

async def handle_proof(update: Update, context):
    user = update.effective_user
    tg = int(context.bot_data.get('TARGET_GROUP_ID'))
    kb = InlineKeyboardMarkup([[InlineKeyboardButton('Approve', callback_data=f'approve:{user.id}'), InlineKeyboardButton('Decline', callback_data=f'decline:{user.id}')]])
    await context.bot.send_message(chat_id=tg, text=f'Payment proof from user {user.id}', reply_markup=kb)
    if update.message.photo or update.message.document:
        await context.bot.copy_message(chat_id=tg, from_chat_id=update.effective_chat.id, message_id=update.message.message_id)
    await update.message.reply_text('Proof sent to admins for review.')

async def admin_callback(update: Update, context):
    query = update.callback_query
    await query.answer()
    action, uid = query.data.split(':', 1)
    uid = int(uid)
    users = load_users()
    profile = users.get(str(uid), {})
    if action == 'approve':
        from datetime import datetime, timedelta
        profile['is_premium'] = True
        profile['premium_expiry'] = (datetime.utcnow() + timedelta(days=90)).isoformat()
        users[str(uid)] = profile
        save_users(users)
        try:
            await context.bot.send_message(chat_id=uid, text=f'You are premium until {profile["premium_expiry"]}')
        except Exception:
            pass
        await query.edit_message_text(f'Approved user {uid}')
    else:
        await query.edit_message_text(f'Declined user {uid}')
        try:
            await context.bot.send_message(chat_id=uid, text='Your request was declined.')
        except Exception:
            pass
