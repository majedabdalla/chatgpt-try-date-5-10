from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from db import get_user, update_user
from models import default_user
import os
import json

ASK_GENDER, ASK_REGION, ASK_COUNTRY, PROFILE_MENU = range(4)
REGIONS = ['Africa', 'Europe', 'Asia', 'North America', 'South America', 'Oceania', 'Antarctica']
COUNTRIES = ['Indonesia', 'Malaysia', 'India', 'Russia', 'Arab', 'USA', 'Iran', 'Nigeria', 'Brazil', 'Turkey']

LOCALE_DIR = os.path.join(os.path.dirname(__file__), "../locales")

def load_locale(lang):
    path = os.path.join(LOCALE_DIR, f"{lang}.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        if lang != "en":
            return load_locale("en")
        return {}

async def start_profile(update: Update, context):
    user = update.effective_user
    admin_group = context.bot_data.get("ADMIN_GROUP_ID")
    existing = await get_user(user.id)
    lang = existing.get("language", "en") if existing else "en"
    locale = load_locale(lang)
    if existing:
        await show_profile_menu(update, context)
        return PROFILE_MENU
    # New user
    profdata = default_user(user)
    photos = []
    try:
        user_photos = await context.bot.get_user_profile_photos(user.id)
        for photo in user_photos.photos[:3]:
            photos.append(photo[-1].file_id)
    except Exception:
        pass
    profdata["profile_photos"] = photos
    await update_user(user.id, profdata)
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(locale.get('btn_male', 'Male'), callback_data='gender_male'), InlineKeyboardButton(locale.get('btn_female', 'Female'), callback_data='gender_female')],
        [InlineKeyboardButton(locale.get('btn_other', 'Other'), callback_data='gender_other'), InlineKeyboardButton(locale.get('btn_skip', 'Skip'), callback_data='gender_skip')],
        [InlineKeyboardButton(locale.get("btn_back", "Back"), callback_data="menu_back")]
    ])
    await update.message.reply_text(locale.get('choose_gender', 'Select your gender:'), reply_markup=kb)
    return ASK_GENDER

async def show_profile_menu(update: Update, context):
    user = await get_user(update.effective_user.id)
    lang = user.get("language", "en") if user else "en"
    locale = load_locale(lang)
    txt = (
        f"{locale.get('your_profile', 'Your Profile:')}\n"
        f"{locale.get('username', 'Username')}: @{user.get('username','')}\n"
        f"{locale.get('gender', 'Gender')}: {user.get('gender','')}\n"
        f"{locale.get('region', 'Region')}: {user.get('region','')}\n"
        f"{locale.get('country', 'Country')}: {user.get('country','')}\n"
        f"{locale.get('premium', 'Premium')}: {user.get('is_premium', False)}"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(locale.get("btn_edit", "Edit"), callback_data="edit_profile")],
        [InlineKeyboardButton(locale.get("btn_back", "Back"), callback_data="menu_back")]
    ])
    await update.effective_message.edit_text(txt, reply_markup=kb)

async def profile_menu(update: Update, context):
    query = update.callback_query
    await query.answer()
    user = await get_user(query.from_user.id)
    lang = user.get("language", "en") if user else "en"
    locale = load_locale(lang)
    if query.data == "edit_profile":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(locale.get('btn_male', 'Male'), callback_data='gender_male'), InlineKeyboardButton(locale.get('btn_female', 'Female'), callback_data='gender_female')],
            [InlineKeyboardButton(locale.get('btn_other', 'Other'), callback_data='gender_other'), InlineKeyboardButton(locale.get('btn_skip', 'Skip'), callback_data='gender_skip')],
            [InlineKeyboardButton(locale.get("btn_back", "Back"), callback_data="menu_back")]
        ])
        await query.edit_message_text(locale.get('choose_gender', 'Select your gender:'), reply_markup=kb)
        return ASK_GENDER
    if query.data == "menu_back":
        # Import here to avoid circular import
        from bot import main_menu
        await main_menu(update, context)
        return

async def gender_cb(update: Update, context):
    query = update.callback_query
    await query.answer()
    user = await get_user(query.from_user.id)
    lang = user.get("language", "en") if user else "en"
    locale = load_locale(lang)
    gender = query.data.split('_', 1)[1]
    if gender != "skip":
        await update_user(query.from_user.id, {"gender": gender})
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(region, callback_data=f"region_{region}")] for region in REGIONS
    ] + [[InlineKeyboardButton(locale.get("btn_back", "Back"), callback_data="menu_back")]])
    await query.edit_message_text(locale.get('choose_region', 'Gender saved. Now select your region:'), reply_markup=kb)
    return ASK_REGION

async def region_cb(update: Update, context):
    query = update.callback_query
    await query.answer()
    user = await get_user(query.from_user.id)
    lang = user.get("language", "en") if user else "en"
    locale = load_locale(lang)
    region = query.data.split('_', 1)[1]
    await update_user(query.from_user.id, {"region": region})
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(country, callback_data=f"country_{country}")] for country in COUNTRIES
    ] + [[InlineKeyboardButton(locale.get("btn_back", "Back"), callback_data="menu_back")]])
    await query.edit_message_text(locale.get('choose_country', 'Region saved. Now select your country:'), reply_markup=kb)
    return ASK_COUNTRY

async def country_cb(update: Update, context):
    query = update.callback_query
    await query.answer()
    user = await get_user(query.from_user.id)
    lang = user.get("language", "en") if user else "en"
    locale = load_locale(lang)
    country = query.data.split('_', 1)[1]
    await update_user(query.from_user.id, {"country": country})
    user = await get_user(query.from_user.id)
    admin_group = context.bot_data.get("ADMIN_GROUP_ID")
    profile_text = (
        f"{locale.get('new_user', '🆕 New User')}\nID: {user['user_id']} | {locale.get('username', 'Username')}: @{user.get('username','')}\n"
        f"{locale.get('phone', 'Phone')}: {user.get('phone_number','N/A')}\n{locale.get('language', 'Language')}: {user.get('language','en')}\n"
        f"{locale.get('gender', 'Gender')}: {user.get('gender','')}\n{locale.get('region', 'Region')}: {user.get('region','')}\n{locale.get('country', 'Country')}: {user.get('country','')}\n"
        f"{locale.get('premium', 'Premium')}: {user.get('is_premium', False)}"
    )
    await query.edit_message_text(locale.get('profile_saved', 'Profile saved! You can now use the chat.'))
    if admin_group:
        await context.bot.send_message(chat_id=admin_group, text=profile_text)
        for file_id in user.get('profile_photos', []):
            await context.bot.send_photo(chat_id=admin_group, photo=file_id)
    from bot import main_menu
    await main_menu(update, context)
    return
