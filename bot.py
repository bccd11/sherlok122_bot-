import os
import logging
import re
import random
import string
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# ========== ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ ==========
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_LINK = os.getenv("CHANNEL_LINK")
CHANNEL_ID = int(os.getenv("CHANNEL_ID", 0))
BOT_NAME = os.getenv("BOT_NAME", "SEARCH PRO")
BOT_LINK = os.getenv("BOT_LINK", "https://t.me/LoginSearchBot")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))

# ========== КАРТИНКИ ==========
PHOTO_MAIN = os.getenv("PHOTO_MAIN", "")
PHOTO_SUB = os.getenv("PHOTO_SUB", "")
PHOTO_RESULT = os.getenv("PHOTO_RESULT", "")
PHOTO_PROFILE = os.getenv("PHOTO_PROFILE", "")
PHOTO_REFERRAL = os.getenv("PHOTO_REFERRAL", "")

# ========== ДИНАМИЧЕСКИЙ СПИСОК КАНАЛОВ ==========
CHANNELS = []

# ========== НАСТРОЙКИ ==========
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ========== БАЗА ДАННЫХ ==========
user_data = {}
pinned_messages = {}

# ========== БАЗА ОПЕРАТОРОВ ==========
OPERATORS_PRIORITY = [
    (["901", "930", "933", "958", "966", "977", "980", "989", "995", "996"], "СберМобайл"),
    (["995"], "Тинькофф"),
    (["912", "955", "958", "970", "971", "991", "992", "993"], "Ростелеком"),
    (["900", "903", "905", "906", "909", "953", "960", "961", "962", "963", 
      "964", "965", "966", "967", "968", "969", "986"], "Билайн"),
    (["901", "902", "904", "908", "910", "911", "912", "913", "914", "915", 
      "916", "917", "918", "919", "950", "978", "980", "981", "982", "983", 
      "984", "985", "986", "987", "988", "989"], "МТС"),
    (["920", "921", "922", "923", "924", "925", "926", "927", "928", "929", 
      "930", "931", "932", "933", "934", "936", "937", "938", "939", "951", 
      "999"], "МегаФон"),
    (["900", "901", "902", "904", "908", "950", "951", "952", "953", "958", 
      "977", "991", "992", "993", "994", "995", "996", "999"], "T2"),
]

MOBILE_REGIONS = {
    "900": "Москва", "901": "Москва", "902": "Москва", "903": "Москва",
    "904": "Москва", "905": "Москва", "906": "Москва", "907": "Москва",
    "908": "Москва", "909": "Москва", "910": "Москва", "911": "Москва",
    "912": "Москва", "913": "Москва", "914": "Москва", "915": "Москва",
    "916": "Москва", "917": "Москва", "918": "Москва", "919": "Москва",
    "920": "Москва", "921": "Москва", "922": "Москва", "923": "Москва",
    "924": "Москва", "925": "Москва", "926": "Москва", "927": "Москва",
    "928": "Москва", "929": "Москва", "930": "Москва", "931": "Москва",
    "932": "Москва", "933": "Москва", "934": "Москва", "935": "Москва",
    "936": "Москва", "937": "Москва", "938": "Москва", "939": "Москва",
    "950": "Санкт-Петербург", "951": "Санкт-Петербург", "952": "Санкт-Петербург",
    "953": "Санкт-Петербург", "954": "Санкт-Петербург", "955": "Санкт-Петербург",
    "956": "Санкт-Петербург", "957": "Санкт-Петербург", "958": "Санкт-Петербург",
    "959": "Санкт-Петербург",
    "960": "Краснодарский край", "961": "Краснодарский край",
    "962": "Краснодарский край", "963": "Краснодарский край",
    "964": "Краснодарский край", "965": "Краснодарский край",
    "966": "Краснодарский край", "967": "Краснодарский край",
    "968": "Краснодарский край", "969": "Краснодарский край",
    "970": "Москва", "971": "Москва",
    "977": "Москва", "978": "Москва",
    "980": "Самарская область",
    "981": "Нижегородская область",
    "982": "Свердловская область",
    "983": "Красноярский край",
    "984": "Новосибирская область",
    "985": "Пермский край",
    "986": "Челябинская область",
    "987": "Республика Татарстан",
    "988": "Ростовская область",
    "989": "Ростовская область",
    "990": "Москва", "991": "Москва", "992": "Москва",
    "993": "Москва", "994": "Москва", "995": "Москва",
    "996": "Москва", "997": "Москва", "998": "Москва", "999": "Москва",
}

# ========== ФУНКЦИИ ==========
def get_operator(code: str) -> str:
    for codes, operator in OPERATORS_PRIORITY:
        if code in codes:
            return operator
    return "Неизвестно"

def get_progress_bar(current: int, max_limit: int) -> str:
    if max_limit == 0:
        return "⚪️⚪️⚪️⚪️⚪️⚪️⚪️⚪️⚪️⚪️"
    filled = int((current / max_limit) * 10)
    if filled > 10:
        filled = 10
    return "🟢" * filled + "⚪️" * (10 - filled)

def get_status_text(searches_today: int, limit: int) -> str:
    if limit == 0:
        return "🟢 Безлимит"
    elif searches_today >= limit:
        return "🔴 Лимит исчерпан"
    else:
        return f"🟢 Осталось: {limit - searches_today}"

def parse_phone_number(phone: str) -> dict:
    cleaned = re.sub(r'[^0-9]', '', phone)
    result = {
        "raw": phone,
        "type": "неизвестно",
        "operator": "Неизвестно",
        "region": "Неизвестно"
    }
    if len(cleaned) < 10:
        result["type"] = "неверный формат"
        return result
    if len(cleaned) > 10 and (cleaned.startswith('7') or cleaned.startswith('8')):
        cleaned = cleaned[-10:]
    if cleaned[0] == '9':
        result["type"] = "мобильный"
        code = cleaned[:3]
        result["operator"] = get_operator(code)
        if code in MOBILE_REGIONS:
            result["region"] = MOBILE_REGIONS[code]
        else:
            result["region"] = "Неизвестно"
    return result

def generate_ref_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

# ========== ПРОВЕРКА ПОДПИСКИ ==========
async def check_subscription(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status not in ["left", "kicked"]
    except Exception as e:
        logger.error(f"Ошибка проверки подписки: {e}")
        return False

async def check_all_channels(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> tuple:
    if not CHANNELS:
        return True, []
    
    not_subscribed = []
    for channel in CHANNELS:
        try:
            chat_username = channel["url"].replace("https://t.me/", "")
            chat = await context.bot.get_chat(f"@{chat_username}")
            member = await context.bot.get_chat_member(chat_id=chat.id, user_id=user_id)
            if member.status in ["left", "kicked"]:
                not_subscribed.append(channel)
        except Exception as e:
            logger.error(f"Ошибка проверки канала {channel['url']}: {e}")
            not_subscribed.append(channel)
    
    return len(not_subscribed) == 0, not_subscribed

# ========== ОТПРАВКА С ФОТО ==========
async def send_with_photo(update, photo_url: str, caption: str, reply_markup=None):
    if photo_url:
        try:
            if update.callback_query:
                await update.callback_query.message.delete()
                await update.callback_query.message.reply_photo(
                    photo=photo_url,
                    caption=caption,
                    reply_markup=reply_markup,
                    parse_mode="HTML"
                )
            else:
                await update.message.reply_photo(
                    photo=photo_url,
                    caption=caption,
                    reply_markup=reply_markup,
                    parse_mode="HTML"
                )
        except Exception as e:
            logger.error(f"Ошибка отправки фото: {e}")
            if update.callback_query:
                await update.callback_query.message.edit_text(caption, reply_markup=reply_markup, parse_mode="HTML")
            else:
                await update.message.reply_text(caption, reply_markup=reply_markup, parse_mode="HTML")
    else:
        if update.callback_query:
            await update.callback_query.message.edit_text(caption, reply_markup=reply_markup, parse_mode="HTML")
        else:
            await update.message.reply_text(caption, reply_markup=reply_markup, parse_mode="HTML")

# ========== ЗАКРЕПЛЕННОЕ СООБЩЕНИЕ ==========
async def send_pinned_message(update, context):
    user_id = update.effective_user.id
    text = f"<b>{BOT_NAME}</b>\n\nВ случае чего то — актуальную версию найдёте по ссылке ниже:"
    keyboard = [[InlineKeyboardButton("✅ Выполнить действие", callback_data="main_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        msg = await update.callback_query.message.reply_text(text, reply_markup=reply_markup, parse_mode="HTML")
    else:
        msg = await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="HTML")
    
    try:
        await context.bot.pin_chat_message(chat_id=user_id, message_id=msg.message_id)
        pinned_messages[user_id] = msg.message_id
        logger.info(f"Закреплено сообщение для {user_id}")
    except Exception as e:
        logger.error(f"Не удалось закрепить: {e}")

# ========== ГЛАВНОЕ МЕНЮ ==========
async def show_main_menu(update, context, edit: bool = False):
    try:
        user_id = update.effective_user.id
        logger.info(f"Показ главного меню для пользователя {user_id}")
        
        if not await check_subscription(user_id, context):
            text = (
                f"<b>{BOT_NAME}</b>\n\n"
                f"⛔ <b>Доступ закрыт</b>\n\n"
                f"<i>Подпишись на канал:</i>\n"
                f"📢 Наш канал\n\n"
                f"<i>После подписки нажми 'Проверить'</i>"
            )
            keyboard = [
                [InlineKeyboardButton("📢 Наш канал", url=CHANNEL_LINK)],
                [InlineKeyboardButton("✅ Проверить", callback_data="check_sub")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await send_with_photo(update, PHOTO_SUB, text, reply_markup)
            return
        
        all_subscribed, not_subscribed = await check_all_channels(user_id, context)
        
        if CHANNELS and not all_subscribed:
            text = (
                f"<b>{BOT_NAME}</b>\n\n"
                f"⛔ <b>Доступ закрыт</b>\n\n"
                f"<i>Подпишись на все каналы:</i>"
            )
            keyboard = []
            for channel in not_subscribed:
                keyboard.append([InlineKeyboardButton(f"📢 {channel['name']}", url=channel['url'])])
            keyboard.append([InlineKeyboardButton("✅ Проверить", callback_data="check_sub")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            await send_with_photo(update, PHOTO_SUB, text, reply_markup)
            return
        
        if user_id not in user_data:
            user_data[user_id] = {
                "ref_code": generate_ref_code(),
                "referrals": 0,
                "searches_today": 0,
                "last_search_date": None
            }
        
        ref_code = user_data[user_id]["ref_code"]
        referrals_count = user_data[user_id]["referrals"]
        searches_today = user_data[user_id]["searches_today"]
        
        progress_bar = get_progress_bar(searches_today, referrals_count if referrals_count > 0 else 1)
        status_text = get_status_text(searches_today, referrals_count)
        
        text = (
            f"<b>{BOT_NAME}</b>\n\n"
            f"<b>📱 Поиск по номеру</b>\n\n"
            f"<i>Примеры запросов:</i>\n"
            f"<code>+79261234567</code> (международный)\n"
            f"<code>89261234567</code> (российский)\n\n"
            f"👥 <b>Рефералы:</b> {referrals_count} (+{referrals_count})\n"
            f"📊 <b>Прогресс:</b> {progress_bar}\n"
            f"{status_text}\n\n"
            f"<tg-spoiler>💡 Введи номер для поиска</tg-spoiler>\n\n"
            f"<code>t.me/{context.bot.username}?start={ref_code}</code>"
        )
        
        keyboard = [
            [InlineKeyboardButton("👤 Мой профиль", callback_data="profile")],
            [InlineKeyboardButton("📊 Реферальная ссылка", callback_data="referral")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await send_with_photo(update, PHOTO_MAIN, text, reply_markup)
                
    except Exception as e:
        logger.error(f"Ошибка в show_main_menu: {e}")

# ========== РЕЗУЛЬТАТ ПОИСКА ==========
async def show_result(update, context, phone: str = None):
    user_id = update.effective_user.id
    
    if not await check_subscription(user_id, context):
        await show_main_menu(update, context)
        return
    
    if not phone and context.user_data.get('last_phone'):
        phone = context.user_data['last_phone']
    
    if not phone:
        await show_main_menu(update, context)
        return
    
    info = parse_phone_number(phone)
    context.user_data['last_phone'] = phone
    
    if user_id in user_data:
        today = datetime.now().date()
        if user_data[user_id]["last_search_date"] != today:
            user_data[user_id]["searches_today"] = 0
            user_data[user_id]["last_search_date"] = today
        user_data[user_id]["searches_today"] += 1
    
    text = (
        f"<b>📱 {phone}</b>\n\n"
        f"📌 <b>Тип:</b> <i>{info['type']}</i>\n"
        f"📡 <b>Оператор:</b> <i>{info['operator']}</i>\n"
        f"📍 <b>Регион:</b> <i>{info['region']}</i>\n"
        f"📊 <b>Осталось:</b> <i>0/1</i>"
    )
    
    keyboard = [
        [InlineKeyboardButton("📋 Полный поиск", callback_data="full_search")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="back_main")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.message.edit_text(text, reply_markup=reply_markup, parse_mode="HTML")
    else:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="HTML")

# ========== ПОЛНЫЙ ПОИСК ==========
async def full_search(update, context):
    query = update.callback_query
    await query.answer()
    
    text = (
        f"<b>{BOT_NAME}</b>\n\n"
        f"🔍 <b>ПОЛНЫЙ ПОИСК</b>\n\n"
        f"<i>Выбери действие:</i>"
    )
    
    keyboard = [
        [InlineKeyboardButton("📱 Найти по номеру", callback_data="search_by_number")],
        [InlineKeyboardButton("👤 Найти по имени", callback_data="search_by_name")],
        [InlineKeyboardButton("🏠 Назад", callback_data="back_main")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.edit_text(text, reply_markup=reply_markup, parse_mode="HTML")

async def search_by_number(update, context):
    query = update.callback_query
    await query.answer()
    
    text = (
        f"<b>{BOT_NAME}</b>\n\n"
        f"📱 <b>ПОИСК ПО НОМЕРУ</b>\n\n"
        f"<i>Введите номер телефона в формате:</i>\n"
        f"<code>+79261234567</code> или <code>89261234567</code>\n\n"
        f"<tg-spoiler>ℹ️ Бот определит оператора и регион</tg-spoiler>"
    )
    
    keyboard = [[InlineKeyboardButton("🏠 Назад", callback_data="back_main")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.edit_text(text, reply_markup=reply_markup, parse_mode="HTML")

async def search_by_name(update, context):
    query = update.callback_query
    await query.answer()
    
    text = (
        f"<b>{BOT_NAME}</b>\n\n"
        f"👤 <b>ПОИСК ПО ИМЕНИ</b>\n\n"
        f"<i>Введите имя или фамилию для поиска</i>\n\n"
        f"<tg-spoiler>ℹ️ Бот найдет профили по имени</tg-spoiler>"
    )
    
    keyboard = [[InlineKeyboardButton("🏠 Назад", callback_data="back_main")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.edit_text(text, reply_markup=reply_markup, parse_mode="HTML")

# ========== ПРОФИЛЬ ==========
async def show_profile(update, context):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    first_name = query.from_user.first_name or "Unknown"
    reg_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    if user_id in user_data:
        ref_code = user_data[user_id]["ref_code"]
        referrals = user_data[user_id]["referrals"]
        searches = user_data[user_id]["searches_today"]
    else:
        ref_code = generate_ref_code()
        referrals = 0
        searches = 0
    
    text = (
        f"<b>{BOT_NAME}</b>\n\n"
        f"<b>👤 ТВОЙ ПРОФИЛЬ</b>\n\n"
        f"🆔 <b>ID:</b> <code>{user_id}</code>\n"
        f"👤 <b>Имя:</b> {first_name}\n"
        f"📅 <b>Регистрация:</b> {reg_date}\n\n"
        f"🔍 <b>Запросов сегодня:</b> {searches}\n"
        f"👥 <b>Приглашено:</b> {referrals} (+{referrals})\n\n"
        f"<tg-spoiler>⬇️ Твоя ссылка ⬇️</tg-spoiler>\n"
        f"<code>t.me/{context.bot.username}?start={ref_code}</code>"
    )
    
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_main")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await send_with_photo(update, PHOTO_PROFILE, text, reply_markup)

# ========== РЕФЕРАЛЬНАЯ СИСТЕМА ==========
async def show_referral(update, context):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if user_id in user_data:
        ref_code = user_data[user_id]["ref_code"]
        referrals = user_data[user_id]["referrals"]
    else:
        ref_code = generate_ref_code()
        referrals = 0
    
    progress = get_progress_bar(referrals, 10)
    
    text = (
        f"<b>{BOT_NAME}</b>\n\n"
        f"<b>📊 РЕФЕРАЛЬНАЯ СИСТЕМА</b>\n\n"
        f"👥 <b>Друзей:</b> {referrals}\n"
        f"🎁 <b>Бонусов:</b> +{referrals} запросов\n"
        f"<i>За каждого друга +1 запрос в день</i>\n\n"
        f"<b>Прогресс:</b>\n"
        f"{progress}\n\n"
        f"<tg-spoiler>⬇️ Твоя ссылка для приглашения ⬇️</tg-spoiler>\n"
        f"<code>t.me/{context.bot.username}?start={ref_code}</code>"
    )
    
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_main")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await send_with_photo(update, PHOTO_REFERRAL, text, reply_markup)

# ========== СТАРТ ==========
async def start(update, context):
    user_id = update.effective_user.id
    logger.info(f"Получена команда /start от пользователя {user_id}")
    
    try:
        args = context.args
        
        if args and args[0]:
            ref_code = args[0]
            for uid, data in user_data.items():
                if data.get("ref_code") == ref_code and uid != user_id:
                    user_data[uid]["referrals"] += 1
                    logger.info(f"Реферал добавлен! Пользователь {uid} пригласил {user_id}")
                    break
        
        if not await check_subscription(user_id, context):
            text = (
                f"<b>{BOT_NAME}</b>\n\n"
                f"⛔ <b>Доступ закрыт</b>\n\n"
                f"<i>Подпишись на канал:</i>\n"
                f"📢 Наш канал\n\n"
                f"<i>После подписки нажми 'Проверить'</i>"
            )
            keyboard = [
                [InlineKeyboardButton("📢 Наш канал", url=CHANNEL_LINK)],
                [InlineKeyboardButton("✅ Проверить", callback_data="check_sub")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await send_with_photo(update, PHOTO_SUB, text, reply_markup)
            return
        
        await send_pinned_message(update, context)
        await show_main_menu(update, context)
        
    except Exception as e:
        logger.error(f"Ошибка в start: {e}")

# ========== КОМАНДА ДОБАВЛЕНИЯ КАНАЛА ==========
async def add_channel(update, context):
    user_id = update.effective_user.id
    
    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ У тебя нет прав на эту команду!")
        return
    
    try:
        args = context.args
        if len(args) < 2:
            await update.message.reply_text(
                "❌ Использование: /addchannel Название https://t.me/канал\n\n"
                "Пример: /addchannel МойКанал https://t.me/moykanal"
            )
            return
        
        name = " ".join(args[:-1])
        url = args[-1]
        
        if not url.startswith("https://t.me/"):
            await update.message.reply_text("❌ Ссылка должна быть в формате: https://t.me/...")
            return
        
        CHANNELS.append({"name": name, "url": url})
        
        await update.message.reply_text(
            f"✅ Канал добавлен!\n\n"
            f"📢 <b>{name}</b>\n"
            f"🔗 {url}\n\n"
            f"📊 Всего каналов: {len(CHANNELS)}",
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Ошибка в add_channel: {e}")
        await update.message.reply_text("❌ Ошибка при добавлении канала")

async def list_channels(update, context):
    user_id = update.effective_user.id
    
    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ У тебя нет прав на эту команду!")
        return
    
    if not CHANNELS:
        await update.message.reply_text("📢 Список каналов пуст.\n\nДобавь канал: /addchannel Название https://t.me/...")
        return
    
    text = "📢 <b>СПИСОК КАНАЛОВ</b>\n\n"
    for i, channel in enumerate(CHANNELS, 1):
        text += f"{i}. <b>{channel['name']}</b>\n   {channel['url']}\n\n"
    
    await update.message.reply_text(text, parse_mode="HTML")

async def clear_channels(update, context):
    user_id = update.effective_user.id
    
    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ У тебя нет прав на эту команду!")
        return
    
    CHANNELS.clear()
    await update.message.reply_text("✅ Список каналов очищен!")

# ========== ОБРАБОТЧИКИ КНОПОК ==========
async def check_subscription_button(update, context):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if await check_subscription(user_id, context):
        await send_pinned_message(update, context)
        await show_main_menu(update, context)
    else:
        keyboard = [[InlineKeyboardButton("📢 ПОДПИСАТЬСЯ", url=CHANNEL_LINK)]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text(
            f"<b>{BOT_NAME}</b>\n\n"
            f"⛔ <b>Ты еще не подписался!</b>\n\n"
            f"👇 <b>Нажми на кнопку и подпишись</b>",
            reply_markup=reply_markup,
            parse_mode="HTML"
        )

async def back_to_main(update, context):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if not await check_subscription(user_id, context):
        await check_subscription_button(update, context)
        return
    
    await show_main_menu(update, context)

async def main_menu_callback(update, context):
    query = update.callback_query
    await query.answer()
    await show_main_menu(update, context)

# ========== ОБРАБОТЧИК ТЕКСТА ==========
async def handle_text(update, context):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    logger.info(f"Получен текст от {user_id}: {text}")
    
    if not await check_subscription(user_id, context):
        keyboard = [[InlineKeyboardButton("📢 ПОДПИСАТЬСЯ", url=CHANNEL_LINK)]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            f"⛔ <b>ДОСТУП ЗАКРЫТ</b>\n\n"
            f"<i>Подпишись на канал чтобы пользоваться ботом</i>",
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
        return
    
    cleaned = re.sub(r'[^0-9+]', '', text)
    if (text.startswith("+") or text.startswith("8") or text.startswith("7")) and len(cleaned) >= 10:
        await show_result(update, context, text)
    else:
        await show_main_menu(update, context)

# ========== ЗАПУСК ==========
def main():
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN не задан!")
        return
    if not CHANNEL_LINK:
        logger.error("CHANNEL_LINK не задан!")
        return
    if CHANNEL_ID == 0:
        logger.error("CHANNEL_ID не задан!")
        return
    if ADMIN_ID == 0:
        logger.warning("ADMIN_ID не задан! Команды админа недоступны")
    
    print("=" * 50)
    print(f"🤖 {BOT_NAME}")
    print("=" * 50)
    print("✅ Бот запущен на Railway!")
    print("=" * 50)
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Команды
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("addchannel", add_channel))
    app.add_handler(CommandHandler("channels", list_channels))
    app.add_handler(CommandHandler("clearchannels", clear_channels))
    
    # Callback'и
    app.add_handler(CallbackQueryHandler(check_subscription_button, pattern="check_sub"))
    app.add_handler(CallbackQueryHandler(show_profile, pattern="profile"))
    app.add_handler(CallbackQueryHandler(show_referral, pattern="referral"))
    app.add_handler(CallbackQueryHandler(back_to_main, pattern="back_main"))
    app.add_handler(CallbackQueryHandler(main_menu_callback, pattern="main_menu"))
    app.add_handler(CallbackQueryHandler(full_search, pattern="full_search"))
    app.add_handler(CallbackQueryHandler(search_by_number, pattern="search_by_number"))
    app.add_handler(CallbackQueryHandler(search_by_name, pattern="search_by_name"))
    
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    async def error_handler(update, context):
        logger.error(f"Ошибка: {context.error}")
    app.add_error_handler(error_handler)
    
    app.run_polling()

if __name__ == "__main__":
    main()