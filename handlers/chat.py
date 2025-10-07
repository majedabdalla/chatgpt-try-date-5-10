from telegram import Update
from telegram.ext import ContextTypes
from db import get_room, update_room, log_chat, get_blocked_words
import time

# Rate limit dict (user_id: last_msg_time)
user_rate_limit = {}

async def process_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    room_id = context.bot_data.get("user_room_map", {}).get(user_id)
    blocked_words = await get_blocked_words()
    for word in blocked_words:
        if word.lower() in text.lower():
            await update.message.reply_text("Your message contains a blocked word. Please be respectful.")
            return
    # Rate limit: 2s between messages
    now = time.time()
    last_time = user_rate_limit.get(user_id, 0)
    if now - last_time < 2.0:
        await update.message.reply_text("Rate limit: Please wait before sending another message.")
        return
    user_rate_limit[user_id] = now
    # Save to chat log
    await log_chat(room_id, {
        "user_id": user_id,
        "text": text,
        "timestamp": now
    })
    # Forward to other user in room
    room = await get_room(room_id)
    other_id = [uid for uid in room["users"] if uid != user_id][0]
    await context.bot.send_message(chat_id=other_id, text=text)
