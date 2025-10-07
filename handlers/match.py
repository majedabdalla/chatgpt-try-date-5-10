from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ConversationHandler, CallbackQueryHandler, CommandHandler
from db import get_user, update_user
from rooms import add_to_pool, find_match_for
import random

# State constants for premium search
SELECT_FILTER, SELECT_GENDER, SELECT_REGION, SELECT_COUNTRY, CONFIRM_SEARCH = range(5)

REGIONS = ['Africa', 'Europe', 'Asia', 'North America', 'South America', 'Oceania', 'Antarctica']
COUNTRIES = ['Indonesia', 'Malaysia', 'India', 'Russia', 'Arab', 'USA', 'Iran', 'Nigeria', 'Brazil', 'Turkey']
GENDERS = ['male', 'female', 'other']

# --- Free users: /find ---
async def find_command(update: Update, context):
    user_id = update.effective_user.id
    user = await get_user(user_id)
    if not user:
        await update.message.reply_text("Please setup your profile first with /profile.")
        return
    # Add to pool for random matching
    add_to_pool(user_id)
    await update.message.reply_text("You have been added to the finding pool! Wait for a match.")

# --- Premium users: /search ---
async def search_command(update: Update, context):
    user_id = update.effective_user.id
    user = await get_user(user_id)
    if not user or not user.get("is_premium", False):
        await update.message.reply_text("This feature is for premium users only.")
        return ConversationHandler.END
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("Filter by Gender", callback_data="filter_gender")],
        [InlineKeyboardButton("Filter by Region", callback_data="filter_region")],
        [InlineKeyboardButton("Filter by Country", callback_data="filter_country")],
        [InlineKeyboardButton("Proceed without filters", callback_data="filter_none")]
    ])
    await update.message.reply_text(
        "Choose your search filters. You can apply one or more (repeat this menu to add more filters). When ready, press 'Proceed without filters' to search.",
        reply_markup=kb
    )
    # Store chosen filters in context.user_data
    context.user_data["search_filters"] = {}
    return SELECT_FILTER

async def select_filter_cb(update: Update, context):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data == "filter_gender":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("Male", callback_data="gender_male"),
             InlineKeyboardButton("Female", callback_data="gender_female"),
             InlineKeyboardButton("Other", callback_data="gender_other")]
        ])
        await query.edit_message_text("Select preferred gender:", reply_markup=kb)
        return SELECT_GENDER
    if data == "filter_region":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(region, callback_data=f"region_{region}")] for region in REGIONS
        ])
        await query.edit_message_text("Select preferred region:", reply_markup=kb)
        return SELECT_REGION
    if data == "filter_country":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(country, callback_data=f"country_{country}")] for country in COUNTRIES
        ])
        await query.edit_message_text("Select preferred country:", reply_markup=kb)
        return SELECT_COUNTRY
    if data == "filter_none":
        # Proceed to search with current filters
        return await do_search(update, context)

async def set_gender_cb(update: Update, context):
    query = update.callback_query
    await query.answer()
    gender = query.data.split('_', 1)[1]
    context.user_data["search_filters"]["gender"] = gender
    # Go back to filter menu to allow adding more filters or proceed
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("Add Region Filter", callback_data="filter_region")],
        [InlineKeyboardButton("Add Country Filter", callback_data="filter_country")],
        [InlineKeyboardButton("Proceed to Search", callback_data="filter_none")]
    ])
    await query.edit_message_text(f"Gender filter set: {gender}. Add more filters or proceed.", reply_markup=kb)
    return SELECT_FILTER

async def set_region_cb(update: Update, context):
    query = update.callback_query
    await query.answer()
    region = query.data.split('_', 1)[1]
    context.user_data["search_filters"]["region"] = region
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("Add Gender Filter", callback_data="filter_gender")],
        [InlineKeyboardButton("Add Country Filter", callback_data="filter_country")],
        [InlineKeyboardButton("Proceed to Search", callback_data="filter_none")]
    ])
    await query.edit_message_text(f"Region filter set: {region}. Add more filters or proceed.", reply_markup=kb)
    return SELECT_FILTER

async def set_country_cb(update: Update, context):
    query = update.callback_query
    await query.answer()
    country = query.data.split('_', 1)[1]
    context.user_data["search_filters"]["country"] = country
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("Add Gender Filter", callback_data="filter_gender")],
        [InlineKeyboardButton("Add Region Filter", callback_data="filter_region")],
        [InlineKeyboardButton("Proceed to Search", callback_data="filter_none")]
    ])
    await query.edit_message_text(f"Country filter set: {country}. Add more filters or proceed.", reply_markup=kb)
    return SELECT_FILTER

# --- Actual search logic for premium ---
async def do_search(update: Update, context):
    query = update.callback_query
    filters = context.user_data.get("search_filters", {})
    # Find all users in the pool and filter
    from rooms import users_online  # Assume this set holds user_ids of waiting users
    from db import get_user

    candidates = []
    for uid in users_online:
        if uid == query.from_user.id:
            continue
        u = await get_user(uid)
        if not u:
            continue
        # Apply filters
        ok = True
        if filters.get("gender") and u.get("gender") != filters["gender"]:
            ok = False
        if filters.get("region") and u.get("region") != filters["region"]:
            ok = False
        if filters.get("country") and u.get("country") != filters["country"]:
            ok = False
        if ok:
            candidates.append(uid)
    if not candidates:
        await query.edit_message_text("No users found matching your criteria. Try again later.")
        return ConversationHandler.END
    # Randomly pick a partner
    partner = random.choice(candidates)
    # Remove both from pool (and start room logic here!)
    users_online.discard(query.from_user.id)
    users_online.discard(partner)
    await query.edit_message_text(f"Match found! Your partner's user ID is {partner}. (Implement room/chat logic here.)")
    return ConversationHandler.END

# --- ConversationHandler for /search ---
search_conv = ConversationHandler(
    entry_points=[CommandHandler('search', search_command)],
    states={
        SELECT_FILTER: [CallbackQueryHandler(select_filter_cb, pattern="^filter_")],
        SELECT_GENDER: [CallbackQueryHandler(set_gender_cb, pattern="^gender_")],
        SELECT_REGION: [CallbackQueryHandler(set_region_cb, pattern="^region_")],
        SELECT_COUNTRY: [CallbackQueryHandler(set_country_cb, pattern="^country_")]
    },
    fallbacks=[]
)
