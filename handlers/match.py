from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ConversationHandler, CallbackQueryHandler, CommandHandler
from db import get_user
from rooms import add_to_pool, remove_from_pool, users_online, create_room, close_room
import random

# State constants for premium search
SELECT_FILTER, SELECT_GENDER, SELECT_REGION, SELECT_COUNTRY, CONFIRM_SEARCH = range(5)

REGIONS = ['Africa', 'Europe', 'Asia', 'North America', 'South America', 'Oceania', 'Antarctica']
COUNTRIES = ['Indonesia', 'Malaysia', 'India', 'Russia', 'Arab', 'USA', 'Iran', 'Nigeria', 'Brazil', 'Turkey']
GENDERS = ['male', 'female', 'other']

async def set_users_room_map(context, user1, user2, room_id):
    if "user_room_map" not in context.bot_data:
        context.bot_data["user_room_map"] = {}
    context.bot_data["user_room_map"][user1] = room_id
    context.bot_data["user_room_map"][user2] = room_id

async def remove_users_room_map(context, user1, user2=None):
    if "user_room_map" not in context.bot_data:
        return
    context.bot_data["user_room_map"].pop(user1, None)
    if user2 is not None:
        context.bot_data["user_room_map"].pop(user2, None)

# --- Free users: /find ---
async def find_command(update: Update, context):
    user_id = update.effective_user.id
    user = await get_user(user_id)
    if not user:
        await update.message.reply_text("Please setup your profile first with /profile.")
        return

    if user_id in context.bot_data.get("user_room_map", {}):
        await update.message.reply_text("You are already in a chat. Use /end or /next to leave first.")
        return

    candidates = [uid for uid in users_online if uid != user_id]
    if candidates:
        partner = random.choice(candidates)
        remove_from_pool(partner)
        room_id = await create_room(user_id, partner)
        await set_users_room_map(context, user_id, partner, room_id)
        remove_from_pool(user_id)
        await update.message.reply_text("🎉 Match found! Say hi to your partner.")
        await context.bot.send_message(partner, "🎉 Match found! Say hi to your partner.")
    else:
        add_to_pool(user_id)
        await update.message.reply_text("You have been added to the finding pool! Wait for a match.")

# --- End chat: /end ---
async def end_command(update: Update, context):
    user_id = update.effective_user.id
    user_room_map = context.bot_data.get("user_room_map", {})
    room_id = user_room_map.pop(user_id, None)
    if not room_id:
        await update.message.reply_text("You are not in a room.")
        return
    from db import get_room
    room = await get_room(room_id)
    other_id = None
    if room and "users" in room:
        for uid in room["users"]:
            context.bot_data["user_room_map"].pop(uid, None)
            if uid != user_id:
                other_id = uid
    await close_room(room_id)
    await update.message.reply_text("You have left the chat.")
    if other_id:
        try:
            await context.bot.send_message(other_id, "Your chat partner has left the chat.")
        except Exception:
            pass

# --- Next chat: /next ---
async def next_command(update: Update, context):
    await end_command(update, context)
    await find_command(update, context)

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
        return await do_search(update, context)

async def set_gender_cb(update: Update, context):
    query = update.callback_query
    await query.answer()
    gender = query.data.split('_', 1)[1]
    context.user_data["search_filters"]["gender"] = gender
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

async def do_search(update: Update, context):
    query = update.callback_query
    filters = context.user_data.get("search_filters", {})
    from rooms import users_online
    from db import get_user

    candidates = []
    for uid in users_online:
        if uid == query.from_user.id:
            continue
        u = await get_user(uid)
        if not u:
            continue
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
    partner = random.choice(candidates)
    users_online.discard(query.from_user.id)
    users_online.discard(partner)
    room_id = await create_room(query.from_user.id, partner)
    await set_users_room_map(context, query.from_user.id, partner, room_id)
    await query.edit_message_text("🎉 Match found! Say hi to your partner.")
    await context.bot.send_message(partner, "🎉 Match found! Say hi to your partner.")
    return ConversationHandler.END

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
