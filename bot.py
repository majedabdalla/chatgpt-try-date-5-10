# PATCHED CODE: KeyError fix for update_profile, and ensure correct profile creation in profile setup flow.
import os
import json
import logging
from uuid import uuid4
from typing import Dict, Any
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, User
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
CHAT_LOG_FILE = "chatlog.txt"

LANGUAGES = {
    "en": "English",
    "ar": "العربية",
    "hi": "हिन्दी",
    "id": "Bahasa Indonesia"
}

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

active_rooms: Dict[str, Dict[str, Any]] = {}
user_room_map: Dict[int, str] = {}

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
    name = getattr(user, "full_name", None) or getattr(user, "first_name", None) or ""
    if not profile:
        profile = {
            "user_id": user.id,
            "username": user.username or "",
            "phone_number": "",
            "language": "en",
            "name": name,
            "gender": "",
            "region": "",
            "country": "",
            "is_premium": False,
            "premium_expiry": "",
            "blocked": False
        }
        user_data_store[uid] = profile
        save_user_data(user_data_store)
    else:
        if not profile.get('name') and name:
            profile['name'] = name
            save_user_data(user_data_store)
    return profile

# PATCHED: update_profile now ensures user profile exists before updating
def update_profile(user_id, updates, user_data_store):
    uid = str(user_id)
    if uid not in user_data_store:
        # Create default profile if not present
        user_data_store[uid] = {
            "user_id": user_id,
            "username": "",
            "phone_number": "",
            "language": "en",
            "name": "",
            "gender": "",
            "region": "",
            "country": "",
            "is_premium": False,
            "premium_expiry": "",
            "blocked": False
        }
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
    try:
        if hasattr(update, "message") and update.message:
            return update.message.reply_text(text)
        elif hasattr(update, "callback_query") and update.callback_query and update.callback_query.message:
            return update.callback_query.message.reply_text(text)
        elif getattr(update, "effective_user", None):
            return context.bot.send_message(update.effective_user.id, text)
    except Exception as e:
        logger.error("safe_reply error: %s", e)

def is_admin(user_id):
    return user_id == ADMIN_ID

def log_room_message(room_id, msg_obj):
    if not os.path.isdir("rooms"):
        os.makedirs("rooms")
    room_file = f"rooms/room_{room_id}.json"
    try:
        with open(room_file, "r", encoding="utf-8") as f:
            history = json.load(f)
    except Exception:
        history = []
    history.append(msg_obj)
    with open(room_file, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)

def get_room_history(room_id):
    room_file = f"rooms/room_{room_id}.json"
    try:
        with open(room_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def get_user_history(user_id):
    user_msgs = []
    if not os.path.isdir("rooms"):
        return []
    for fname in os.listdir("rooms"):
        if fname.startswith("room_") and fname.endswith(".json"):
            room_file = os.path.join("rooms", fname)
            try:
                with open(room_file, "r", encoding="utf-8") as f:
                    history = json.load(f)
                for msg in history:
                    if msg["sender"] == user_id or msg["receiver"] == user_id:
                        user_msgs.append(msg)
            except Exception:
                continue
    return user_msgs

def format_user_info(user_profile):
    return (
        f"Name: {user_profile.get('name', '')}\n"
        f"Username: @{user_profile.get('username', '')}\n"
        f"Phone: {user_profile.get('phone_number', '')}\n"
        f"User ID: {user_profile.get('user_id', '')}\n"
    )

def get_profile_picture(context, user_id):
    try:
        photos = context.bot.get_user_profile_photos(user_id, limit=1)
        if photos.total_count > 0:
            return photos.photos[0][0].file_id
    except Exception:
        return None
    return None

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
        if profile.get("blocked"):
            continue
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

(
    LANG_SELECT,
    PROFILE_GENDER,
    PROFILE_REGION,
    PROFILE_COUNTRY,
    PROFILE_NAME,
    PARTNER_FILTER,
    PREMIUM_PROOF
) = range(7)

# --- Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data_store = load_user_data()
    uid = str(user.id)
    profile = user_data_store.get(uid)
    if profile and profile.get("name") and profile.get("gender") and profile.get("region") and profile.get("country"):
        # Existing profile, search for partner
        if profile.get("blocked"):
            await safe_reply(update, context, "You are blocked from using this bot.")
            return ConversationHandler.END
        await safe_reply(update, context, "Welcome back! Searching for a partner for you...")
        candidates = find_partner(user.id, user_data_store)
        if candidates:
            partner_id = candidates[0]
            room_id = create_room(user.id, partner_id)
            await context.bot.send_message(user.id, f"🔒 Connected to room #{room_id}. Chat anonymously!")
            await context.bot.send_message(partner_id, f"🔒 Connected to room #{room_id}. Chat anonymously!")
        else:
            await safe_reply(update, context, "No partners available now. Try again later.")
        return ConversationHandler.END
    else:
        # New user or incomplete profile
        await safe_reply(update, context, "Let's set up your profile.")
        tg_name = getattr(user, "full_name", None) or getattr(user, "first_name", None) or ""
        await update.message.reply_text(
            f"Your Telegram name is: {tg_name}\nPlease type the name you want to use in the bot:",
            reply_markup=back_keyboard()
        )
        return PROFILE_NAME

async def input_profile_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    name = update.message.text.strip()
    user_data_store = load_user_data()
    get_profile(user, user_data_store) # Ensure profile exists before update
    update_profile(user.id, {"name": name}, user_data_store)
    await update.message.reply_text(
        "Choose your language:",
        reply_markup=language_keyboard()
    )
    return LANG_SELECT

# --- The rest of your code/handlers remain unchanged ---
# No other logic, functions, or features are deleted or replaced.
# Only the profile setup flow and update_profile are patched for the KeyError bug.
