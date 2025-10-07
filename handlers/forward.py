from telegram import Update
from telegram.ext import ContextTypes

async def forward_to_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    username = user.username or "none"
    room_id = context.bot_data.get("user_room_map", {}).get(user_id, 0)
    admin_group_id = context.bot_data.get("ADMIN_GROUP_ID")

    # Compose a common header
    header = f"🆕 From user {user_id} (@{username})\nRoom: {room_id}"

    # Forward text
    if update.message.text:
        msg = f"{header}\nText: {update.message.text}"
        await context.bot.send_message(chat_id=admin_group_id, text=msg)
    # Forward photo
    elif update.message.photo:
        caption = f"{header}\n[Photo message]"
        await context.bot.send_photo(
            chat_id=admin_group_id,
            photo=update.message.photo[-1].file_id,
            caption=caption
        )
    # Forward video
    elif update.message.video:
        caption = f"{header}\n[Video message]"
        await context.bot.send_video(
            chat_id=admin_group_id,
            video=update.message.video.file_id,
            caption=caption
        )
    # Forward audio
    elif update.message.audio:
        caption = f"{header}\n[Audio message]"
        await context.bot.send_audio(
            chat_id=admin_group_id,
            audio=update.message.audio.file_id,
            caption=caption
        )
    # Forward voice
    elif update.message.voice:
        caption = f"{header}\n[Voice message]"
        await context.bot.send_voice(
            chat_id=admin_group_id,
            voice=update.message.voice.file_id,
            caption=caption
        )
    # Forward document
    elif update.message.document:
        caption = f"{header}\n[Document message]"
        await context.bot.send_document(
            chat_id=admin_group_id,
            document=update.message.document.file_id,
            caption=caption
        )
    # Forward sticker
    elif update.message.sticker:
        caption = f"{header}\n[Sticker]"
        await context.bot.send_sticker(
            chat_id=admin_group_id,
            sticker=update.message.sticker.file_id
        )
        await context.bot.send_message(chat_id=admin_group_id, text=header + "\n[Sticker sent above]")
    else:
        # fallback: forward as copy if possible
        try:
            await update.message.forward(chat_id=admin_group_id)
            await context.bot.send_message(chat_id=admin_group_id, text=header + "\n[Above: unknown message type forwarded]")
        except Exception as e:
            await context.bot.send_message(chat_id=admin_group_id, text=header + f"\n[Could not forward message: {e}]")
