from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, ReplyKeyboardMarkup
from db import get_user, update_user
from models import default_user

ASK_GENDER, ASK_REGION, ASK_COUNTRY, PROFILE_MENU = range(4)

REGIONS = ['Africa', 'Europe', 'Asia', 'North America', 'South America', 'Oceania', 'Antarctica']
COUNTRIES = ['Indonesia', 'Malaysia', 'India', 'Russia', 'Arab', 'USA', 'Iran', 'Nigeria', 'Brazil', 'Turkey']

def get_reply_keyboard(lang):
    from bot import load_locale
    locale = load_locale(lang)
    return [
        [locale.get("profile", "Profile"), locale.get("find", "Find"), locale.get("end_chat", "End Chat")],
        [locale.get("edit_profile", "Edit Profile"), locale.get("report_sent", "Report"), locale.get("upgrade_tip", "Upgrade")],
        ["Filters", locale.get("menu_back", "Back")]
    ]

async def start_profile(update: Update, context):
    user = update.effective_user
    admin_group = context.bot_data.get("ADMIN_GROUP_ID")
    lang = "en"
    existing = await get_user(user.id)
    if existing:
        prof = existing
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("Edit Profile", callback_data="menu_edit_profile")],
            [InlineKeyboardButton("Find", callback_data="menu_find")],
            [InlineKeyboardButton("Upgrade", callback_data="menu_upgrade")],
            [InlineKeyboardButton("Filters", callback_data="menu_filter")],
            [InlineKeyboardButton("Back", callback_data="menu_back")]
        ])
        txt = f"Your Profile:\nGender: {prof.get('gender','')}\nRegion: {prof.get('region','')}\nCountry: {prof.get('country','')}"
        await update.message.reply_text(txt, reply_markup=kb)
        await update.message.reply_text("Main menu:", reply_markup=ReplyKeyboardMarkup(get_reply_keyboard(lang), resize_keyboard=True))
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
        [InlineKeyboardButton('Male', callback_data='gender_male'), InlineKeyboardButton('Female', callback_data='gender_female')],
        [InlineKeyboardButton('Other', callback_data='gender_other'), InlineKeyboardButton('Skip', callback_data='gender_skip')],
        [InlineKeyboardButton("Back", callback_data="menu_back")]
    ])
    await update.message.reply_text('Select your gender:', reply_markup=kb)
    await update.message.reply_text("Main menu:", reply_markup=ReplyKeyboardMarkup(get_reply_keyboard(lang), resize_keyboard=True))
    return ASK_GENDER

async def profile_menu(update: Update, context):
    query = update.callback_query
    await query.answer()
    user = await get_user(query.from_user.id)
    lang = user.get("language", "en") if user else "en"
    if query.data == "menu_edit_profile":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton('Male', callback_data='gender_male'), InlineKeyboardButton('Female', callback_data='gender_female')],
            [InlineKeyboardButton('Other', callback_data='gender_other'), InlineKeyboardButton('Skip', callback_data='gender_skip')],
            [InlineKeyboardButton("Back", callback_data="menu_back")]
        ])
        await query.edit_message_text('Select your gender:', reply_markup=kb)
        await query.edit_message_text("Main menu:", reply_markup=ReplyKeyboardMarkup(get_reply_keyboard(lang), resize_keyboard=True))
        return ASK_GENDER
    if query.data == "menu_find":
        from handlers.match import find_command
        await find_command(update, context)
        return
    if query.data == "menu_upgrade":
        from handlers.premium import start_upgrade
        await start_upgrade(update, context)
        return
    if query.data == "menu_filter":
        from handlers.match import open_filter_menu
        await open_filter_menu(update, context)
        return
    if query.data == "menu_back":
        from bot import main_menu
        await main_menu(update, context)
        return

async def gender_cb(update: Update, context):
    query = update.callback_query
    await query.answer()
    gender = query.data.split('_', 1)[1]
    if gender != "skip":
        await update_user(query.from_user.id, {"gender": gender})
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(region, callback_data=f"region_{region}")] for region in REGIONS
    ] + [[InlineKeyboardButton("Back", callback_data="menu_back")]])
    await query.edit_message_text('Gender saved. Now select your region:', reply_markup=kb)
    return ASK_REGION

async def region_cb(update: Update, context):
    query = update.callback_query
    await query.answer()
    region = query.data.split('_', 1)[1]
    await update_user(query.from_user.id, {"region": region})
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(country, callback_data=f"country_{country}")] for country in COUNTRIES
    ] + [[InlineKeyboardButton("Back", callback_data="menu_back")]])
    await query.edit_message_text('Region saved. Now select your country:', reply_markup=kb)
    return ASK_COUNTRY

async def country_cb(update: Update, context):
    query = update.callback_query
    await query.answer()
    country = query.data.split('_', 1)[1]
    await update_user(query.from_user.id, {"country": country})
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
        for file_id in user.get('profile_photos', []):
            await context.bot.send_photo(chat_id=admin_group, photo=file_id)
    from bot import main_menu
    await main_menu(update, context)
    return
