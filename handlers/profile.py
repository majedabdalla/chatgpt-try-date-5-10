from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ConversationHandler, CallbackQueryHandler, MessageHandler, filters
from db import get_user, update_user
from models import default_user

ASK_GENDER, ASK_REGION, ASK_COUNTRY, ASK_PREFS = range(4)

async def start_profile(update: Update, context):
    user = update.effective_user
    existing = await get_user(user.id)
    if not existing:
        await update_user(user.id, default_user(user))
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton('Male', callback_data='gender_male'), InlineKeyboardButton('Female', callback_data='gender_female')],
        [InlineKeyboardButton('Other', callback_data='gender_other'), InlineKeyboardButton('Skip', callback_data='gender_skip')]
    ])
    await update.message.reply_text('Select your gender:', reply_markup=kb)
    return ASK_GENDER

async def gender_cb(update: Update, context):
    query = update.callback_query
    await query.answer()
    gender = query.data.split('_', 1)[1]
    if gender != "skip":
        await update_user(query.from_user.id, {"gender": gender})
    await query.edit_message_text('Gender saved. Now send your region name (text):')
    return ASK_REGION

async def region_text(update: Update, context):
    await update_user(update.effective_user.id, {"region": update.message.text})
    await update.message.reply_text('Region saved. Now send your country:')
    return ASK_COUNTRY

async def country_text(update: Update, context):
    await update_user(update.effective_user.id, {"country": update.message.text})
    await update.message.reply_text('Profile saved! Now set your matching preferences (gender, region, country, premium-only, comma separated or type "skip")')
    return ASK_PREFS

async def prefs_text(update: Update, context):
    prefs = update.message.text
    if prefs.lower().strip() != "skip":
        # Parse prefs, e.g., "male,egypt,premium"
        prefs_dict = {}
        parts = [p.strip() for p in prefs.split(",")]
        for p in parts:
            if p.lower() in ["male", "female", "other"]:
                prefs_dict["gender"] = p.lower()
            elif p.lower() == "premium":
                prefs_dict["premium_only"] = True
            elif len(p) > 2:
                if "region" not in prefs_dict:
                    prefs_dict["region"] = p
                else:
                    prefs_dict["country"] = p
        await update_user(update.effective_user.id, {"matching_preferences": prefs_dict})
    await update.message.reply_text('Preferences saved! You can now use the chat.')
    return ConversationHandler.END