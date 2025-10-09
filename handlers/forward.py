from db import get_room, get_user

async def forward_to_admin(update, context):
    user = update.effective_user
    user_id = user.id
    username = user.username or "none"
    room_id = context.bot_data.get("user_room_map", {}).get(user_id, 0)
    admin_group_id = context.bot_data.get("ADMIN_GROUP_ID")

    room = await get_room(room_id)
    receiver_id = None
    if room and "users" in room:
        receiver_id = [uid for uid in room["users"] if uid != user_id]
        receiver_id = receiver_id[0] if receiver_id else None
    receiver = await get_user(receiver_id) if receiver_id else None

    header = f"📢 Room #{room_id}\n👤 Sender: {user_id} (username: @{username})"
    if receiver:
        header += f"\n👥 Receiver: {receiver['user_id']} (username: @{receiver.get('username','')})"
    header += f"\nRoom Created: {room['created_at'] if room else 'N/A'}\n"

    msg = None
    m = update.message
    if m.text:
        msg = f"{header}\n💬 Message: {m.text}"
        await context.bot.send_message(chat_id=admin_group_id, text=msg)
    elif m.photo:
        caption = f"{header}\n[Photo message]"
        await context.bot.send_photo(chat_id=admin_group_id, photo=m.photo[-1].file_id, caption=caption)
    elif m.video:
        caption = f"{header}\n[Video message]"
        await context.bot.send_video(chat_id=admin_group_id, video=m.video.file_id, caption=caption)
    elif getattr(m, "video_note", None):
        caption = f"{header}\n[Video Note]"
        await context.bot.send_video_note(chat_id=admin_group_id, video_note=m.video_note.file_id)
        await context.bot.send_message(chat_id=admin_group_id, text=caption)
    elif m.audio:
        caption = f"{header}\n[Audio message]"
        await context.bot.send_audio(chat_id=admin_group_id, audio=m.audio.file_id, caption=caption)
    elif m.voice:
        caption = f"{header}\n[Voice message]"
        await context.bot.send_voice(chat_id=admin_group_id, voice=m.voice.file_id, caption=caption)
    elif m.document:
        caption = f"{header}\n[Document message]"
        await context.bot.send_document(chat_id=admin_group_id, document=m.document.file_id, caption=caption)
    elif m.sticker:
        caption = f"{header}\n[Sticker]"
        await context.bot.send_sticker(chat_id=admin_group_id, sticker=m.sticker.file_id)
        await context.bot.send_message(chat_id=admin_group_id, text=header + "\n[Sticker sent above]")
    else:
        try:
            await m.forward(chat_id=admin_group_id)
            await context.bot.send_message(chat_id=admin_group_id, text=header + "\n[Above: unknown message type forwarded]")
        except Exception as e:
            await context.bot.send_message(chat_id=admin_group_id, text=header + f"\n[Could not forward message: {e}]\nType: {type(m)}\n{m}")
