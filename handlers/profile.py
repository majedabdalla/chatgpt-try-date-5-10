
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ConversationHandler, CallbackQueryHandler, MessageHandler, filters
from storage import load_users, save_users

ASK_GENDER, ASK_REGION, ASK_COUNTRY = range(3)

async def start_profile(update: Update, context):
    user = update.effective_user
    users = load_users()
    p = users.get(str(user.id), {'user_id': user.id, 'username': user.username or '', 'language': 'en'})
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton('Male', callback_data='gender_male'), InlineKeyboardButton('Female', callback_data='gender_female')],
        [InlineKeyboardButton('Other', callback_data='gender_other'), InlineKeyboardButton('Back', callback_data='back')]
    ])
    await update.message.reply_text('Choose gender:', reply_markup=kb)
    return ASK_GENDER

async def gender_cb(update: Update, context):
    query = update.callback_query
    await query.answer()
    if query.data == 'back':
        await query.edit_message_text('Cancelled')
        return ConversationHandler.END
    gender = query.data.split('_', 1)[1]
    users = load_users()
    p = users.get(str(query.from_user.id), {})
    p['gender'] = gender
    users[str(query.from_user.id)] = p
    save_users(users)
    await query.edit_message_text('Gender saved. Send your region name (text):')
    return ASK_REGION

async def region_text(update: Update, context):
    users = load_users()
    p = users.get(str(update.effective_user.id), {})
    p['region'] = update.message.text
    users[str(update.effective_user.id)] = p
    save_users(users)
    await update.message.reply_text('Region saved. Now send your country:')
    return ASK_COUNTRY

async def country_text(update: Update, context):
    users = load_users()
    p = users.get(str(update.effective_user.id), {})
    p['country'] = update.message.text
    users[str(update.effective_user.id)] = p
    save_users(users)
    await update.message.reply_text('Profile saved!')
    return ConversationHandler.END
