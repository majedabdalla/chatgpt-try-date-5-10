from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ConversationHandler, CallbackQueryHandler, MessageHandler, filters
from db import get_user, update_user
from models import default_user

ASK_GENDER, ASK_REGION, ASK_COUNTRY, PROFILE_MENU = range(4)

REGIONS = ['Africa', 'Europe', 'Asia', 'North America', 'South America', 'Oceania', 'Antarctica']
COUNTRIES = ['Indonesia', 'Malaysia', 'India', 'Russia', 'Arab', 'USA', 'Iran', 'Nigeria', 'Brazil', 'Turkey']

async def start_profile(update: Update, context):
    user = update.effective_user
    existing = await get_user(user.id)
    if existing:
        # Show profile summary with "Edit" button
        prof = existing
        txt = f"Your Profile:\nGender: {prof.get('gender','')}\nRegion: {prof.get('region','')}\nCountry: {prof.get('country','')}"
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("Edit", callback_data="edit_profile")]
        ])
        await update.message.reply_text(txt, reply_markup=kb)
        return PROFILE_MENU
    # New user: go to gender selection
    await update_user(user.id, default_user(user))
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
    # Region menu
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
    # Country menu
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
    await query.edit_message_text('Profile saved! You can now use the chat.')
    return ConversationHandler.END

# Update ConversationHandler in bot.py accordingly:
# states={
#     PROFILE_MENU: [CallbackQueryHandler(profile_menu)],
#     ASK_GENDER: [CallbackQueryHandler(gender_cb, pattern="^gender_")],
#     ASK_REGION: [CallbackQueryHandler(region_cb, pattern="^region_")],
#     ASK_COUNTRY: [CallbackQueryHandler(country_cb, pattern="^country_")],
# }
