from telegram import Update
from admin import block_user, unblock_user, send_admin_message, get_stats, add_blocked_word, remove_blocked_word
from db import get_user, get_room, get_chat_history
import os

# Pull IDs from env, as in bot.py
ADMIN_ID = int(os.getenv("ADMIN_ID"))
ADMIN_GROUP_ID = int(os.getenv("ADMIN_GROUP_ID"))

def _is_admin(update):
    return (
        (update.effective_user and update.effective_user.id == ADMIN_ID)
        or (update.effective_chat and update.effective_chat.id == ADMIN_GROUP_ID)
    )

async def admin_block(update: Update, context):
    if not _is_admin(update):
        await update.message.reply_text("Unauthorized.")
        return
    user_id = int(context.args[0])
    await block_user(user_id)
    await update.message.reply_text(f"User {user_id} blocked.")

async def admin_unblock(update: Update, context):
    if not _is_admin(update):
        await update.message.reply_text("Unauthorized.")
        return
    user_id = int(context.args[0])
    await unblock_user(user_id)
    await update.message.reply_text(f"User {user_id} unblocked.")

async def admin_message(update: Update, context):
    if not _is_admin(update):
        await update.message.reply_text("Unauthorized.")
        return
    user_id_or_username = context.args[0]
    text = " ".join(context.args[1:])
    success = await send_admin_message(context.bot, user_id_or_username, text)
    if success:
        await update.message.reply_text("Message sent.")
    else:
        await update.message.reply_text("Failed to send message.")

async def admin_stats(update: Update, context):
    if not _is_admin(update):
        await update.message.reply_text("Unauthorized.")
        return
    stats = await get_stats()
    await update.message.reply_text(f"Stats:\nUsers: {stats['users']}\nRooms: {stats['rooms']}\nReports: {stats['reports']}")

async def admin_blockword(update: Update, context):
    if not _is_admin(update):
        await update.message.reply_text("Unauthorized.")
        return
    word = context.args[0]
    await add_blocked_word(word)
    await update.message.reply_text(f"Blocked word '{word}' added.")

async def admin_unblockword(update: Update, context):
    if not _is_admin(update):
        await update.message.reply_text("Unauthorized.")
        return
    word = context.args[0]
    await remove_blocked_word(word)
    await update.message.reply_text(f"Blocked word '{word}' removed.")

async def admin_userinfo(update: Update, context):
    if not _is_admin(update):
        await update.message.reply_text("Unauthorized.")
        return
    identifier = context.args[0]
    user = await get_user(identifier)
    if user:
        await update.message.reply_text(str(user))
    else:
        await update.message.reply_text("User not found.")

async def admin_roominfo(update: Update, context):
    if not _is_admin(update):
        await update.message.reply_text("Unauthorized.")
        return
    room_id = context.args[0]
    room = await get_room(room_id)
    if room:
        await update.message.reply_text(str(room))
    else:
        await update.message.reply_text("Room not found.")

async def admin_viewhistory(update: Update, context):
    if not _is_admin(update):
        await update.message.reply_text("Unauthorized.")
        return
    room_id = context.args[0]
    history = await get_chat_history(room_id)
    if history:
        await update.message.reply_text("\n".join([str(msg) for msg in history]))
    else:
        await update.message.reply_text("No chat history found.")
