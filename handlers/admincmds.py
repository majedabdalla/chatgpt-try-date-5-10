from telegram import Update
from admin import block_user, unblock_user, send_admin_message, get_stats, add_blocked_word, remove_blocked_word
from db import get_user, get_room, get_chat_history

async def admin_block(update: Update, context):
    if not context.user_data.get("is_admin"):
        return
    user_id = int(context.args[0])
    await block_user(user_id)
    await update.message.reply_text(f"User {user_id} blocked.")

async def admin_unblock(update: Update, context):
    if not context.user_data.get("is_admin"):
        return
    user_id = int(context.args[0])
    await unblock_user(user_id)
    await update.message.reply_text(f"User {user_id} unblocked.")

async def admin_message(update: Update, context):
    if not context.user_data.get("is_admin"):
        return
    user_id_or_username = context.args[0]
    text = " ".join(context.args[1:])
    success = await send_admin_message(context.bot, user_id_or_username, text)
    if success:
        await update.message.reply_text("Message sent.")
    else:
        await update.message.reply_text("Failed to send message.")

async def admin_stats(update: Update, context):
    if not context.user_data.get("is_admin"):
        return
    stats = await get_stats()
    await update.message.reply_text(f"Stats:\nUsers: {stats['users']}\nRooms: {stats['rooms']}\nReports: {stats['reports']}")

async def admin_blockword(update: Update, context):
    if not context.user_data.get("is_admin"):
        return
    word = context.args[0]
    await add_blocked_word(word)
    await update.message.reply_text(f"Blocked word '{word}' added.")

async def admin_unblockword(update: Update, context):
    if not context.user_data.get("is_admin"):
        return
    word = context.args[0]
    await remove_blocked_word(word)
    await update.message.reply_text(f"Blocked word '{word}' removed.")

async def admin_userinfo(update: Update, context):
    if not context.user_data.get("is_admin"):
        return
    identifier = context.args[0]
    user = await get_user(identifier)
    await update.message.reply_text(str(user))

async def admin_roominfo(update: Update, context):
    if not context.user_data.get("is_admin"):
        return
    room_id = context.args[0]
    room = await get_room(room_id)
    await update.message.reply_text(str(room))

async def admin_viewhistory(update: Update, context):
    if not context.user_data.get("is_admin"):
        return
    room_id = context.args[0]
    history = await get_chat_history(room_id)
    await update.message.reply_text("\n".join([str(msg) for msg in history]))