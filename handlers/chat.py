from telegram import Update
from telegram.ext import CommandHandler, MessageHandler, filters
import asyncio
from storage import load_users
from rooms import add_to_pool, remove_from_pool, find_match_for, create_room, close_room, user_to_room, rooms
from admin import build_metadata_text
import logging


logger = logging.getLogger(__name__)




async def find_handler(update: Update, context):
user = update.effective_user
users = load_users()
_ = users.get(str(user.id), {'language': 'en'})
add_to_pool(user.id)
await update.message.reply_text('Searching for partner...')
partner = find_match_for(user.id)
if not partner:
await update.message.reply_text('No available partners right now. Try again later.')
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
await update.mess
