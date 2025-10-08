from telegram import Update
from admin import block_user, unblock_user, send_admin_message, get_stats, add_blocked_word, remove_blocked_word, approve_premium
from db import get_user, get_user_by_username, get_room, get_chat_history
from datetime import datetime, timedelta

def _is_admin(update, context):
    ADMIN_ID = context.bot_data.get("ADMIN_ID")
    ADMIN_GROUP_ID = context.bot_data.get("ADMIN_GROUP_ID")
    return (
        (update.effective_user and update.effective_user.id == ADMIN_ID)
        or (update.effective_chat and update.effective_chat.id == ADMIN_GROUP_ID)
    )

async def admin_block(update: Update, context):
    if not _is_admin(update, context):
        await update.message.reply_text("Unauthorized.")
        return
    identifier = context.args[0]
    user = await get_user(identifier)
    if not user and identifier.startswith("@"):
        user = await get_user_by_username(identifier[1:])
    if not user:
        user = await get_user_by_username(identifier)
    if not user:
        await update.message.reply_text("User not found.")
        return
    await block_user(user["user_id"])
    await update.message.reply_text(f"User {user['user_id']} blocked.")

async def admin_unblock(update: Update, context):
    if not _is_admin(update, context):
        await update.message.reply_text("Unauthorized.")
        return
    identifier = context.args[0]
    user = await get_user(identifier)
    if not user and identifier.startswith("@"):
        user = await get_user_by_username(identifier[1:])
    if not user:
        user = await get_user_by_username(identifier)
    if not user:
        await update.message.reply_text("User not found.")
        return
    await unblock_user(user["user_id"])
    await update.message.reply_text(f"User {user['user_id']} unblocked.")

async def admin_setpremium(update: Update, context):
    if not _is_admin(update, context):
        await update.message.reply_text("Unauthorized.")
        return
    identifier = context.args[0]
    user = await get_user(identifier)
    if not user and identifier.startswith("@"):
        user = await get_user_by_username(identifier[1:])
    if not user:
        user = await get_user_by_username(identifier)
    if not user:
        await update.message.reply_text("User not found.")
        return
    expiry = await approve_premium(user["user_id"])
    await update.message.reply_text(f"User {user['user_id']} promoted to premium until {expiry}")

async def admin_message(update: Update, context):
    if not _is_admin(update, context):
        await update.message.reply_text("Unauthorized.")
        return
    user_id_or_username = context.args[0]
    text = " ".join(context.args[1:])
    success = await send_admin_message(context.bot, user_id_or_username, text)
    if not success and user_id_or_username.startswith("@"):
        success = await send_admin_message(context.bot, user_id_or_username[1:], text)
    if success:
        await update.message.reply_text("Message sent.")
    else:
        await update.message.reply_text("Failed to send message.")

async def admin_stats(update: Update, context):
    if not _is_admin(update, context):
        await update.message.reply_text("Unauthorized.")
        return
    stats = await get_stats()
    await update.message.reply_text(
        f"Stats:\nUsers: {stats['users']}\nRooms: {stats['rooms']}\nReports: {stats['reports']}"
    )

async def admin_blockword(update: Update, context):
    if not _is_admin(update, context):
        await update.message.reply_text("Unauthorized.")
        return
    word = context.args[0]
    await add_blocked_word(word)
    await update.message.reply_text(f"Blocked word '{word}' added.")

async def admin_unblockword(update: Update, context):
    if not _is_admin(update, context):
        await update.message.reply_text("Unauthorized.")
        return
    word = context.args[0]
    await remove_blocked_word(word)
    await update.message.reply_text(f"Blocked word '{word}' removed.")

async def admin_userinfo(update: Update, context):
    if not _is_admin(update, context):
        await update.message.reply_text("Unauthorized.")
        return
    identifier = context.args[0]
    user = await get_user(identifier)
    if not user and identifier.startswith("@"):
        user = await get_user_by_username(identifier[1:])
    if not user:
        user = await get_user_by_username(identifier)
    if not user:
        await update.message.reply_text("User not found.")
        return
    txt = (
        f"ID: {user['user_id']}\nUsername: @{user.get('username','')}\n"
        f"Phone: {user.get('phone_number','N/A')}\nLanguage: {user.get('language','en')}\n"
        f"Gender: {user.get('gender','')}\nRegion: {user.get('region','')}\nCountry: {user.get('country','')}\n"
        f"Premium: {user.get('is_premium', False)}"
    )
    await update.message.reply_text(txt)
    # Send profile photos if available
    for pid in user.get('profile_photos', []):
        await context.bot.send_photo(chat_id=update.effective_chat.id, photo=pid)

async def admin_roominfo(update: Update, context):
    if not _is_admin(update, context):
        await update.message.reply_text("Unauthorized.")
        return
    room_id = context.args[0]
    room = await get_room(room_id)
    if room:
        users_info = []
        for uid in room["users"]:
            u = await get_user(uid)
            if u:
                txt = (
                    f"ID: {u['user_id']}\nUsername: @{u.get('username','')}\n"
                    f"Phone: {u.get('phone_number','N/A')}\nLanguage: {u.get('language','en')}\n"
                    f"Gender: {u.get('gender','')}\nRegion: {u.get('region','')}\nCountry: {u.get('country','')}\n"
                    f"Premium: {u.get('is_premium', False)}"
                )
                users_info.append(txt)
                for pid in u.get('profile_photos', []):
                    await context.bot.send_photo(chat_id=update.effective_chat.id, photo=pid)
        await update.message.reply_text(f"RoomID: {room['room_id']}\nUsers:\n" + "\n---\n".join(users_info))
    else:
        await update.message.reply_text("Room not found.")

async def admin_viewhistory(update: Update, context):
    if not _is_admin(update, context):
        await update.message.reply_text("Unauthorized.")
        return
    room_id = context.args[0]
    history = await get_chat_history(room_id)
    if history:
        await update.message.reply_text("\n".join([str(msg) for msg in history]))
    else:
        await update.message.reply_text("No chat history found.")
