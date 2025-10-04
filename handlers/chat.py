
from telegram import Update
from telegram.ext import CommandHandler, MessageHandler, filters
from storage import load_users
from rooms import add_to_pool, remove_from_pool, find_match_for, create_room, close_room, user_to_room, rooms
from admin import build_metadata_text
import logging

logger = logging.getLogger(__name__)

async def find_handler(update: Update, context):
    user = update.effective_user
    users = load_users()
    p = users.get(str(user.id), {'language': 'en'})
    add_to_pool(user.id)
    await update.message.reply_text('Searching for partner...')
    partner = find_match_for(user.id)
    if not partner:
        return
    remove_from_pool(user.id)
    remove_from_pool(partner)
    room_id = create_room(user.id, partner)
    await context.bot.send_message(chat_id=user.id, text=f'Connected to room #{room_id}')
    await context.bot.send_message(chat_id=partner, text=f'Connected to room #{room_id}')

async def stop_handler(update: Update, context):
    user = update.effective_user
    room_id = user_to_room.get(user.id)
    if not room_id:
        await update.message.reply_text('You are not in a room.')
        return
    room = rooms.get(room_id)
    for uid in room['users']:
        if uid != user.id:
            try:
                await context.bot.send_message(chat_id=uid, text='Partner left the chat')
            except Exception:
                pass
    close_room(room_id)
    await update.message.reply_text('Left room')

async def relay(update: Update, context):
    user = update.effective_user
    if not user:
        return
    room_id = user_to_room.get(user.id)
    if not room_id:
        await update.message.reply_text('Not in a room. Use /find')
        return
    room = rooms.get(room_id)
    other = [u for u in room['users'] if u != user.id]
    text = update.message.text
    room['messages'].append({'from': user.id, 'text': text})
    for uid in other:
        try:
            if update.message.photo or update.message.document or update.message.sticker:
                await context.bot.copy_message(chat_id=uid, from_chat_id=update.effective_chat.id, message_id=update.message.message_id)
            else:
                await context.bot.send_message(chat_id=uid, text=text)
        except Exception:
            logger.exception('Failed to forward to %s', uid)
    sender_profile = load_users().get(str(user.id), {})
    receiver_profile = load_users().get(str(other[0]), {}) if other else None
    meta = build_metadata_text(room, sender_profile, receiver_profile)
    try:
        tg = int(context.bot_data.get('TARGET_GROUP_ID'))
        await context.bot.send_message(chat_id=tg, text=meta)
        await context.bot.copy_message(chat_id=tg, from_chat_id=update.effective_chat.id, message_id=update.message.message_id)
    except Exception:
        logger.exception('Failed to forward to admin')
