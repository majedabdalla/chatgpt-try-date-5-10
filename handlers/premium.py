from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from db import get_user, update_user
from admin import approve_premium
from datetime import datetime, timedelta

# Track which users are sending proof (only after upgrade button)
premium_proof_state = {}

async def start_upgrade(update: Update, context):
    user_id = update.effective_user.id
    premium_proof_state[user_id] = True
    await update.effective_message.edit_text('Please upload payment proof (photo, screenshot, or document)')

async def handle_proof(update: Update, context):
    user_id = update.effective_user.id
    admin_group = int(context.bot_data.get('ADMIN_GROUP_ID'))
    if not premium_proof_state.get(user_id, False):
        return  # Ignore proofs unless upgrade button pressed
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton('Approve', callback_data=f'approve:{user_id}'), InlineKeyboardButton('Decline', callback_data=f'decline:{user_id}')]
    ])
    await context.bot.send_message(chat_id=admin_group, text=f'Payment proof from user {user_id}', reply_markup=kb)
    if update.message.photo or update.message.document:
        await context.bot.copy_message(chat_id=admin_group, from_chat_id=update.effective_chat.id, message_id=update.message.message_id)
    await update.message.reply_text('Proof sent to admins for review.')
    premium_proof_state[user_id] = False
    # After submitting, show main menu
    from bot import main_menu
    await main_menu(update, context)

async def admin_callback(update: Update, context):
    query = update.callback_query
    await query.answer()
    if ':' not in query.data:
        return
    action, uid = query.data.split(':', 1)
    uid = int(uid)
    if action == 'approve':
        expiry = await approve_premium(uid)
        try:
            await context.bot.send_message(chat_id=uid, text=f'You are premium until {expiry}')
        except Exception:
            pass
        await query.edit_message_text(f'Approved user {uid}')
    else:
        await query.edit_message_text(f'Declined user {uid}')
        try:
            await context.bot.send_message(chat_id=uid, text='Your request was declined.')
        except Exception:
            pass
