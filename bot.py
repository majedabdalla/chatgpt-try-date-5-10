import os
import json
import logging
from uuid import uuid4
from typing import Dict, Any
from datetime import datetime, timezone, timedelta

from dotenv import load_dotenv
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, MessageHandler, ConversationHandler, ContextTypes, filters
)

# --- Load environment variables ---
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
TARGET_GROUP_ID = int(os.getenv("TARGET_GROUP_ID"))
PAYEER_ACCOUNT = os.getenv("PAYEER_ACCOUNT")
BITCOIN_WALLET_ADDRESS = os.getenv("BITCOIN_WALLET_ADDRESS")

USER_DATA_FILE = "user_data.json"
ROOMS_FILE = "rooms.json"
LOCALES_DIR = "locales"
CHAT_LOG_FILE = "chatlog.txt"  # Added for persistent chat log

LANGUAGES = {
    "en": "English",
    "ar": "العربية",
    "hi": "हिन्दी",
    "id": "Bahasa Indonesia"
}

# --- Logging ---
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- In-Memory Chat State ---
active_rooms: Dict[str, Dict[str, Any]] = {}
user_room_map: Dict[int, str] = {}  # user_id -> room_id

# --- Utilities ---
def load_json(file_path, default):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def save_json(file_path, data):
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def load_user_data():
    return load_json(USER_DATA_FILE, {})

def save_user_data(data):
    save_json(USER_DATA_FILE, data)

def log_rooms():
    save_json(ROOMS_FILE, active_rooms)

def load_translation(lang):
    path = os.path.join(LOCALES_DIR, f"{lang}.json")
    if not os.path.isfile(path):
        path = os.path.join(LOCALES_DIR, "en.json")
    return load_json(path, {})

def tr(user, key):
    lang = user.get("language", "en")
    translations = load_translation(lang)
    return translations.get(key, key)

def get_profile(user, user_data_store):
    uid = str(user.id)
    profile = user_data_store.get(uid)
    if not profile:
        profile = {
            "user_id": user.id,
            "username": user.username or "",
            "phone_number": "",
            "language": "en",
            "gender": "",
            "region": "",
            "country": "",
            "is_premium": False,
            "premium_expiry": ""
        }
        user_data_store[uid] = profile
        save_user_data(user_data_store)
    return profile

def update_profile(user_id, updates, user_data_store):
    uid = str(user_id)
    user_data_store[uid].update(updates)
    save_user_data(user_data_store)

def check_premium_expiry(profile):
    expiry = profile.get("premium_expiry")
    if expiry:
        expiry_date = datetime.strptime(expiry, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        if expiry_date < datetime.now(timezone.utc):
            profile["is_premium"] = False
            profile["premium_expiry"] = ""
            user_data_store = load_user_data()
            user_data_store[str(profile["user_id"])] = profile
            save_user_data(user_data_store)

def safe_reply(update, context, text):
    """Safely reply to user regardless of update type."""
    try:
        if hasattr(update, "message") and update.message:
            return update.message.reply_text(text)
        elif hasattr(update, "callback_query") and update.callback_query and update.callback_query.message:
            return update.callback_query.message.reply_text(text)
        elif getattr(update, "effective_user", None):
            return context.bot.send_message(update.effective_user.id, text)
    except Exception as e:
        logger.error("safe_reply error: %s", e)

# --- Keyboards ---
def language_keyboard():
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(v, callback_data=f"lang_{k}")] for k, v in LANGUAGES.items()]
    )

def gender_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Male", callback_data="gender_Male"),
            InlineKeyboardButton("Female", callback_data="gender_Female"),
            InlineKeyboardButton("Other", callback_data="gender_Other")
        ]
    ])

def region_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Asia", callback_data="region_Asia"),
            InlineKeyboardButton("Europe", callback_data="region_Europe"),
            InlineKeyboardButton("Other", callback_data="region_Other")
        ]
    ])

def back_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="back")]])

def menu_keyboard(profile):
    buttons = [
        [InlineKeyboardButton("🧑 Profile", callback_data="profile"), InlineKeyboardButton("🌐 Language", callback_data="change_lang")],
        [InlineKeyboardButton("🔎 Find Partner", callback_data="find_partner"), InlineKeyboardButton("💎 Premium", callback_data="premium")]
    ]
    if profile.get("is_premium"):
        buttons.append([InlineKeyboardButton("Filter Partner", callback_data="filter_partner")])
    return InlineKeyboardMarkup(buttons)

def payment_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Pay via Payeer", url=f"https://payeer.com/en/account/{PAYEER_ACCOUNT}/")],
        [InlineKeyboardButton("Pay via Bitcoin", url=f"https://www.blockchain.com/explorer/addresses/btc/{BITCOIN_WALLET_ADDRESS}")]
    ])

# --- Room System ---
def create_room(u1, u2):
    room_id = str(uuid4())[:8]
    now = datetime.now(timezone.utc).isoformat()
    active_rooms[room_id] = {
        "room_id": room_id,
        "created_at": now,
        "participants": [u1, u2],
        "messages": []
    }
    user_room_map[u1] = room_id
    user_room_map[u2] = room_id
    log_rooms()
    return room_id

def close_room(room_id):
    room = active_rooms.get(room_id)
    if room:
        for uid in room["participants"]:
            user_room_map.pop(uid, None)
        active_rooms.pop(room_id)
        log_rooms()

def find_partner(user_id, user_data_store, filters=None, premium=False):
    candidates = []
    for uid, profile in user_data_store.items():
        if int(uid) == user_id: continue
        if int(uid) in user_room_map: continue
        check_premium_expiry(profile)
        if premium and not profile.get("is_premium"):
            continue
        if filters:
            match = True
            for k, v in filters.items():
                if v and profile.get(k) != v:
                    match = False
                    break
            if not match: continue
        candidates.append(int(uid))
    return candidates

# --- Conversation States ---
(
    LANG_SELECT,
    PROFILE_GENDER,
    PROFILE_REGION,
    PROFILE_COUNTRY,
    PARTNER_FILTER,
    PREMIUM_PROOF
) = range(6)

# --- Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data_store = load_user_data()
    profile = get_profile(user, user_data_store)
    await safe_reply(update, context,
        tr(profile, "start")
    )
    await update.message.reply_text(
        tr(profile, "start"),
        reply_markup=language_keyboard()
    )
    return LANG_SELECT

async def select_lang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang_code = query.data.split("_")[1]
    user = query.from_user
    user_data_store = load_user_data()
    profile = get_profile(user, user_data_store)
    update_profile(user.id, {"language": lang_code}, user_data_store)
    await query.edit_message_text(
        load_translation(lang_code).get("profile_gender", "Select your gender:"),
        reply_markup=gender_keyboard()
    )
    return PROFILE_GENDER

async def select_gender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    gender = query.data.split("_")[1]
    user = query.from_user
    user_data_store = load_user_data()
    update_profile(user.id, {"gender": gender}, user_data_store)
    await query.edit_message_text("Select your region:", reply_markup=region_keyboard())
    return PROFILE_REGION

async def select_region(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    region = query.data.split("_")[1]
    user = query.from_user
    user_data_store = load_user_data()
    update_profile(user.id, {"region": region}, user_data_store)
    await query.edit_message_text("Type your country name:", reply_markup=back_keyboard())
    return PROFILE_COUNTRY

async def input_country(update: Update, context: ContextTypes.DEFAULT_TYPE):
    country = update.message.text.strip()
    user = update.effective_user
    user_data_store = load_user_data()
    update_profile(user.id, {"country": country}, user_data_store)
    await safe_reply(update, context,
        tr(get_profile(user, user_data_store), "profile_complete")
    )
    await update.message.reply_text(
        tr(get_profile(user, user_data_store), "profile_complete"),
        reply_markup=menu_keyboard(get_profile(user, user_data_store))
    )
    return ConversationHandler.END

async def back_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    user_data_store = load_user_data()
    await query.edit_message_text(
        tr(get_profile(user, user_data_store), "main_menu"),
        reply_markup=menu_keyboard(get_profile(user, user_data_store))
    )
    return ConversationHandler.END

# --- Menu Actions ---
async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    user_data_store = load_user_data()
    profile = get_profile(user, user_data_store)
    if query.data == "profile":
        await query.edit_message_text(
            f"Profile:\nGender: {profile['gender']}\nRegion: {profile['region']}\nCountry: {profile['country']}\nPremium: {'Yes' if profile['is_premium'] else 'No'}",
            reply_markup=menu_keyboard(profile)
        )
    elif query.data == "change_lang":
        await query.edit_message_text("Choose your language:", reply_markup=language_keyboard())
        return LANG_SELECT
    elif query.data == "find_partner":
        return await find_partner_start(update, context)
    elif query.data == "premium":
        await query.edit_message_text(
            f"💸 To upgrade to premium:\n\n"
            f"• Payeer: `{PAYEER_ACCOUNT}`\n"
            f"• Bitcoin: `{BITCOIN_WALLET_ADDRESS}`\n\n"
            f"Send your payment proof (photo/file) here.",
            reply_markup=payment_keyboard()
        )
        return PREMIUM_PROOF
    elif query.data == "filter_partner":
        await query.edit_message_text("Type partner filter: gender,region,country", reply_markup=back_keyboard())
        return PARTNER_FILTER
    else:
        await query.edit_message_text(tr(profile, "main_menu"), reply_markup=menu_keyboard(profile))
    return ConversationHandler.END

# --- Partner Matching ---
async def find_partner_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user if hasattr(update, "message") and update.message else update.callback_query.from_user
    user_data_store = load_user_data()
    profile = get_profile(user, user_data_store)
    premium = profile.get("is_premium")
    await safe_reply(update, context, tr(profile, "searching_partner"))
    candidates = []
    if premium:
        # If premium, ask for filter
        return PARTNER_FILTER
    else:
        candidates = find_partner(user.id, user_data_store)
        if candidates:
            partner_id = candidates[0]
            room_id = create_room(user.id, partner_id)
            await context.bot.send_message(user.id, f"🔒 Connected to room #{room_id}. Chat anonymously!")
            await context.bot.send_message(partner_id, f"🔒 Connected to room #{room_id}. Chat anonymously!")
        else:
            await safe_reply(update, context, tr(profile, "no_partner_found"))
        return ConversationHandler.END

async def partner_filter_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data_store = load_user_data()
    profile = get_profile(user, user_data_store)
    filter_vals = update.message.text.split(",")
    if len(filter_vals) < 3:
        await safe_reply(update, context, tr(profile, "invalid_filter_format") if "invalid_filter_format" in load_translation(profile["language"]) else "Invalid format. Type: gender,region,country")
        return PARTNER_FILTER
    filters = {"gender": filter_vals[0].strip(), "region": filter_vals[1].strip(), "country": filter_vals[2].strip()}
    candidates = find_partner(user.id, user_data_store, filters=filters, premium=True)
    if candidates:
        partner_id = candidates[0]
        room_id = create_room(user.id, partner_id)
        await context.bot.send_message(user.id, f"🔒 Connected to room #{room_id}. Chat anonymously!")
        await context.bot.send_message(partner_id, f"🔒 Connected to room #{room_id}. Chat anonymously!")
    else:
        await safe_reply(update, context, tr(profile, "no_partner_found"))
    return ConversationHandler.END

# --- Anonymous Chat ---
async def anonymous_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    if user_id not in user_room_map:
        return
    room_id = user_room_map[user_id]
    room = active_rooms.get(room_id)
    partner_id = [uid for uid in room["participants"] if uid != user_id][0]
    msg_obj = None
    user_data_store = load_user_data()
    sender_prof = user_data_store[str(user_id)]
    receiver_prof = user_data_store[str(partner_id)]
    admin_msg = (
        f"📢 Room #{room_id}\n"
        f"👤 Sender: {user_id} (username: @{sender_prof.get('username','')}, phone: {sender_prof.get('phone_number','N/A')})\n"
        f"👥 Receiver: {partner_id} (username: @{receiver_prof.get('username','')}, phone: {receiver_prof.get('phone_number','N/A')})\n"
        f"💬 Message: "
    )
    # Text
    if update.message.text:
        msg_obj = {"sender": user_id, "receiver": partner_id, "content": update.message.text, "time": datetime.now(timezone.utc).isoformat()}
        await context.bot.send_message(partner_id, f"Anon: {update.message.text}")
        await context.bot.send_message(TARGET_GROUP_ID, admin_msg + f'"{update.message.text}"')
    # Photo
    elif update.message.photo:
        file_id = update.message.photo[-1].file_id
        msg_obj = {"sender": user_id, "receiver": partner_id, "content": f"[photo] {file_id}", "time": datetime.now(timezone.utc).isoformat()}
        await context.bot.send_photo(partner_id, file_id)
        await context.bot.send_photo(TARGET_GROUP_ID, file_id, caption=admin_msg + f'[photo]')
    # Document
    elif update.message.document:
        file_id = update.message.document.file_id
        msg_obj = {"sender": user_id, "receiver": partner_id, "content": f"[document] {file_id}", "time": datetime.now(timezone.utc).isoformat()}
        await context.bot.send_document(partner_id, file_id)
        await context.bot.send_document(TARGET_GROUP_ID, file_id, caption=admin_msg + f'[document]')
    # Voice
    elif update.message.voice:
        file_id = update.message.voice.file_id
        msg_obj = {"sender": user_id, "receiver": partner_id, "content": f"[voice] {file_id}", "time": datetime.now(timezone.utc).isoformat()}
        await context.bot.send_voice(partner_id, file_id)
        await context.bot.send_voice(TARGET_GROUP_ID, file_id, caption=admin_msg + f'[voice]')
    # Video
    elif update.message.video:
        file_id = update.message.video.file_id
        msg_obj = {"sender": user_id, "receiver": partner_id, "content": f"[video] {file_id}", "time": datetime.now(timezone.utc).isoformat()}
        await context.bot.send_video(partner_id, file_id)
        await context.bot.send_video(TARGET_GROUP_ID, file_id, caption=admin_msg + f'[video]')
    # Sticker
    elif update.message.sticker:
        file_id = update.message.sticker.file_id
        msg_obj = {"sender": user_id, "receiver": partner_id, "content": f"[sticker] {file_id}", "time": datetime.now(timezone.utc).isoformat()}
        await context.bot.send_sticker(partner_id, file_id)
        await context.bot.send_sticker(TARGET_GROUP_ID, file_id)
        await context.bot.send_message(TARGET_GROUP_ID, admin_msg + f'[sticker]')
    # Save message
    if msg_obj:
        room["messages"].append(msg_obj)
        try:
            with open(CHAT_LOG_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(msg_obj) + "\n")
        except Exception as e:
            logger.error("Failed to write chat log: %s", e)
        log_rooms()

async def stop_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    if user_id not in user_room_map:
        await safe_reply(update, context, "You are not in a room.")
        return
    room_id = user_room_map[user_id]
    close_room(room_id)
    await safe_reply(update, context, "You have left the room.")
    return ConversationHandler.END

# --- Premium Request ---
async def premium_proof_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    proof = None
    kind = None
    if update.message.photo:
        proof = update.message.photo[-1].file_id
        kind = "photo"
    elif update.message.document:
        proof = update.message.document.file_id
        kind = "document"
    else:
        await safe_reply(update, context, "Send a photo or document.")
        return PREMIUM_PROOF
    caption = f"Premium request from @{user.username or ''} (ID: {user.id})"
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Approve", callback_data=f"approve_{user.id}"), InlineKeyboardButton("Decline", callback_data=f"decline_{user.id}")]
    ])
    if kind == "photo":
        await context.bot.send_photo(TARGET_GROUP_ID, proof, caption=caption, reply_markup=keyboard)
    else:
        await context.bot.send_document(TARGET_GROUP_ID, proof, caption=caption, reply_markup=keyboard)
    await safe_reply(update, context, "Your proof was sent. Await admin approval.")
    return ConversationHandler.END

async def admin_approval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = int(data.split("_")[1])
    user_data_store = load_user_data()
    if data.startswith("approve_"):
        expiry = (datetime.now(timezone.utc) + timedelta(days=90)).strftime("%Y-%m-%d")
        update_profile(user_id, {"is_premium": True, "premium_expiry": expiry}, user_data_store)
        await context.bot.send_message(user_id, "✅ Premium approved. You now have premium for 3 months.")
        await query.edit_message_caption(caption="✅ Approved.")
    elif data.startswith("decline_"):
        await context.bot.send_message(user_id, "❌ Premium request declined.")
        await query.edit_message_caption(caption="❌ Declined.")

# --- Premium Grant Command (Admin Only) ---
async def setpremium_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id != ADMIN_ID:
        await safe_reply(update, context, "You are not authorized.")
        return
    if not context.args or len(context.args) < 1:
        await safe_reply(update, context, "Usage: /setpremium <user_id>")
        return
    target_user_id = int(context.args[0])
    expiry = (datetime.now(timezone.utc) + timedelta(days=90)).strftime("%Y-%m-%d")
    user_data_store = load_user_data()
    update_profile(target_user_id, {"is_premium": True, "premium_expiry": expiry}, user_data_store)
    await context.bot.send_message(target_user_id, "✅ Premium approved by admin.")
    await safe_reply(update, context, f"User {target_user_id} is now premium for 3 months.")

# --- Error Handling ---
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error("Error: %s", context.error)
    try:
        await safe_reply(update, context, "An error occurred. Please try again.")
    except Exception:
        pass

# --- Main Entrypoint ---
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # Profile setup conversation
    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            LANG_SELECT: [CallbackQueryHandler(select_lang, pattern=r"^lang_")],
            PROFILE_GENDER: [CallbackQueryHandler(select_gender, pattern=r"^gender_")],
            PROFILE_REGION: [CallbackQueryHandler(select_region, pattern=r"^region_")],
            PROFILE_COUNTRY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, input_country),
                CallbackQueryHandler(back_main_menu, pattern=r"^back$")
            ]
        },
        fallbacks=[CallbackQueryHandler(back_main_menu, pattern=r"^back$")]
    )

    # Partner find conversation
    find_conv = ConversationHandler(
        entry_points=[CommandHandler("find", find_partner_start)],
        states={
            PARTNER_FILTER: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, partner_filter_input),
                CallbackQueryHandler(back_main_menu, pattern=r"^back$")
            ]
        },
        fallbacks=[CallbackQueryHandler(back_main_menu, pattern=r"^back$")]
    )

    # Premium request conversation
    premium_conv = ConversationHandler(
        entry_points=[CommandHandler("premium", lambda u,c: menu_callback(u,c))],
        states={
            PREMIUM_PROOF: [
                MessageHandler(filters.PHOTO | filters.Document.ALL, premium_proof_handler),
                CallbackQueryHandler(back_main_menu, pattern=r"^back$")
            ]
        },
        fallbacks=[CallbackQueryHandler(back_main_menu, pattern=r"^back$")]
    )

    app.add_handler(conv)
    app.add_handler(find_conv)
    app.add_handler(premium_conv)
    app.add_handler(CommandHandler("stop", stop_chat))
    app.add_handler(CommandHandler("setpremium", setpremium_command))  # Added
    # Message handlers for all media types
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, anonymous_chat))
    app.add_handler(MessageHandler(filters.PHOTO, anonymous_chat))
    app.add_handler(MessageHandler(filters.Document.ALL, anonymous_chat))
    app.add_handler(MessageHandler(filters.VOICE, anonymous_chat))
    app.add_handler(MessageHandler(filters.VIDEO, anonymous_chat))
    app.add_handler(MessageHandler(filters.STICKER, anonymous_chat))
    app.add_handler(CallbackQueryHandler(menu_callback, pattern="^(profile|change_lang|find_partner|premium|filter_partner)$"))
    app.add_handler(CallbackQueryHandler(admin_approval, pattern=r"^(approve_|decline_)"))
    app.add_error_handler(error_handler)

    logger.info("AnonindoChat Bot started.")
    app.run_polling()

if __name__ == "__main__":
    main()
