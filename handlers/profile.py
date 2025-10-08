from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ConversationHandler, CallbackQueryHandler, MessageHandler, filters
from db import get_user, update_user
from models import default_user

ASK_GENDER, ASK_REGION, ASK_COUNTRY, PROFILE_MENU = range(4)

REGIONS = ['Africa', 'Europe', 'Asia', 'North America', 'South America', 'Oceania', 'Antarctica']
COUNTRIES = ['Indonesia', 'Malaysia', 'India', 'Russia', 'Arab', 'USA', 'Iran', 'Nigeria', 'Brazil', 'Turkey']

async def start_profile(update: Update, context):
    user = update.effective_user
    admin_group = context.bot_data.get("ADMIN_GROUP_ID")
    existing = await get_user(user.id)
    # Try to fetch user's profile photos
    photos = []
    try:
        user_photos = await context.bot.get_user_profile_photos(user.id)
        for photo in user_photos.photos[:3]:
            photos.append(photo[-1].file_id)
    except Exception:
        pass
    if existing:
        prof = existing
        txt = f"Your Profile:\nGender: {prof.get('gender','')}\nRegion: {prof.get('region','')}\nCountry: {prof.get('country','')}"
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("Edit", callback_data="edit_profile")]
        ])
        await update.message.reply_text(txt, reply_markup=kb)
        return PROFILE_MENU
    # New user
    profdata = default_user(user)
    profdata["profile_photos"] = photos
    await update_user(user.id, profdata)
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton('Male', callback_data='gender_male'), InlineKeyboardButton('Female', callback_data='gender_female')],
        [InlineKeyboardButton('Other', callback_data='gender_other'), InlineKeyboardButton('Skip', callback_data='gender_skip')]
    ])
    await update.message.reply_text('Select your gender:', reply_markup=kb)
    return ASK_GENDER

async def profile_menu(update: Update, context):
    query = update.callback_query
    await query.answer()
    if query.data == "edit_profile":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton('Male', callback_data='gender_male'), InlineKeyboardButton('Female', callback_data='gender_female')],
            [InlineKeyboardButton('Other', callback_data='gender_other'), InlineKeyboardButton('Skip', callback_data='gender_skip')]
        ])
        await query.edit_message_text('Select your gender:', reply_markup=kb)
        return ASK_GENDER

async def gender_cb(update: Update, context):
    query = update.callback_query
    await query.answer()
    gender = query.data.split('_', 1)[1]
    if gender != "skip":
        await update_user(query.from_user.id, {"gender": gender})
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(region, callback_data=f"region_{region}")] for region in REGIONS
    ])
    await query.edit_message_text('Gender saved. Now select your region:', reply_markup=kb)
    return ASK_REGION

async def region_cb(update: Update, context):
    query = update.callback_query
    await query.answer()
    region = query.data.split('_', 1)[1]
    await update_user(query.from_user.id, {"region": region})
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(country, callback_data=f"country_{country}")] for country in COUNTRIES
    ])
    await query.edit_message_text('Region saved. Now select your country:', reply_markup=kb)
    return ASK_COUNTRY

async def country_cb(update: Update, context):
    query = update.callback_query
    await query.answer()
    country = query.data.split('_', 1)[1]
    await update_user(query.from_user.id, {"country": country})
    # Send profile to admin group
    user = await get_user(query.from_user.id)
    admin_group = context.bot_data.get("ADMIN_GROUP_ID")
    profile_text = (
        f"🆕 New User\nID: {user['user_id']} | Username: @{user.get('username','')}\n"
        f"Phone: {user.get('phone_number','N/A')}\nLanguage: {user.get('language','en')}\n"
        f"Gender: {user.get('gender','')}\nRegion: {user.get('region','')}\nCountry: {user.get('country','')}\n"
        f"Premium: {user.get('is_premium', False)}"
    )
    await query.edit_message_text('Profile saved! You can now use the chat.')
    if admin_group:
        await context.bot.send_message(chat_id=admin_group, text=profile_text)
        # Send profile photo(s) if available
        for file_id in user.get('profile_photos', []):
            await context.bot.send_photo(chat_id=admin_group, photo=file_id)
    return ConversationHandler.END
