import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)
import datetime
import qrcode
import os
from io import BytesIO
from telegram.error import BadRequest

from config import *
from database import db

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Состояния для ConversationHandler
(
    SELECTING_LANGUAGE, SELECTING_ACTION, SELECTING_DATE,
    SELECTING_ROOM, SELECTING_DURATION, SELECTING_TIME,
    ENTERING_GROUP, CONFIRMING_BOOKING, SELECTING_BOOKING_TO_CANCEL
) = range(9)

user_data = {}
user_language = {}  # Хранит язык для каждого пользователя

# Тексты на разных языках
TEXTS = {
    'uz': {
        'welcome': "👋 Assalomu alaykum, {name}!\n\nUniversitet kutubxonasining munozara xonalarini bron qilish botiga xush kelibsiz.",
        'rules': "📌 **Bron qilish qoidalari:**\n• Maksimum {max_hours} soat bir martada\n• Bir guruh uchun kuniga maksimum {max_daily} soat\n• Bron {advance_days} kun oldin mavjud\n• Boshlanishidan 5 daqiqa oldin kelishingizni so'raymiz",
        'choose_action': "Quyidagilardan birini tanlang:",
        'main_menu': "Asosiy menyu:",
        'choose_date': "Bron qilish uchun sanani tanlang:",
        'choose_room': "Xonani tanlang:",
        'choose_duration': "Bron muddatini tanlang:",
        'choose_time': "{room_name} uchun vaqtni tanlang:\n\nSana: {date}\nYashil rangda bo'sh vaqtlar ({hours} soat)",
        'enter_group': "Guruh nomingizni kiriting (masalan, IKT-401):\n\nSana: {date}\nXona: {room_name}\nVaqt: {time_range}",
        'group_limit': "❌ '{group_name}' guruhi {date} sanasida {max_hours} soat chegarasidan oshib ketdi.\nHozirda mavjud: {available_hours} soat\n\nIltimos, boshqa guruh nomini kiriting yoki menyuga qayting.",
        'confirm_booking': "✅ Bronni tasdiqlang:\n\n📅 Sana: {date}\n🚪 Xona: {room_name}\n⏰ Vaqt: {time_range}\n👥 Guruh: {group_name}\n\nRozimisiz?",
        'booking_success': "🎉 Bron muvaffaqiyatli yaratildi!\n\n📋 Tafsilotlar:\n• Bron ID: #{booking_id}\n• Sana: {date}\n• Xona: {room_name}\n• Vaqt: {time_range}\n• Guruh: {group_name}\n\n⚠️ **Muhim:**\n1. QR-kodni saqlang\n2. Boshlanishidan 5 daqiqa oldin keling\n3. QR-kodni kutubxonachiga ko'rsating\n4. 15 daqiqadan ko'p kechikilsa, bron bekor qilinadi",
        'qr_caption': "Sizning QR-kodingiz",
        'no_bookings': "Sizda faol bronlar mavjud emas.",
        'my_bookings': "📋 Sizning faol bronlaringiz:\n\n",
        'booking_details': "• Bron #{id}\n  Sana: {date}\n  Vaqt: {start_time}-{end_time}\n  Xona: {room_name}\n  Guruh: {group_name}\n",
        'cancel_success': "✅ Bron #{booking_id} muvaffaqiyatli bekor qilindi.",
        'today_schedule': "📊 Bugungi jadval:\n\n",
        'room_free': "   Kun bo'yi bo'sh",
        'room_occupied': "   🟡 {start_time}-{end_time} - {group_name}",
        'help_text': """ℹ️ **Botdan foydalanish bo'yicha yordam**

**Asosiy buyruqlar:**
• /start - Asosiy menyu
• /help - Bu yordam
• /language - Tilni o'zgartirish

**Bron qanday qilish:**
1. "Xonani bron qilish" ni bosing
2. Sana, xona, muddat va vaqtni tanlang
3. Guruh nomini kiriting
4. Bronni tasdiqlang
5. QR-kodni saqlang

**Qoidalar:**
• Faqat {max_hours} soatgacha bron qilish mumkin
• Bir guruh uchun kuniga {max_daily} soatdan ko'p emas
• 15+ daqiqa kechikilsa bron bekor qilinadi
• Kirish uchun QR-kod majburiy

**Muammolar bo'lsa?**
Kutubxonachi yoki administratorga murojaat qiling.""",
        'back_to_menu': "🏠 Asosiy menyuga qaytish",
        'back': "◀️ Orqaga",
        'cancel': "❌ Bekor qilish",
        'confirm': "✅ Tasdiqlash",
        'book': "📅 Xonani bron qilish",
        'my_bookings_btn': "📋 Mening bronlarim",
        'schedule': "📊 Bugungi jadval",
        'help_btn': "ℹ️ Yordam",
        'select_language': "Iltimos, tilni tanlang:",
        'language_changed': "✅ Til muvaffaqiyatli o'zgartirildi!",
        'today': "Bugun",
        'tomorrow': "Ertaga",
        'hours': "soat",
        'free': "bo'sh",
        'occupied': "band",
        'choose': "Tanlash",
        'select': "Tanlang",
        'not_subscribed': "❌ Botdan foydalanish uchun kanalimizga obuna bo'lishingiz kerak!\n\n📢 Kanal: {channel}\n\nObuna bo'lgandan keyin /start tugmasini bosing.",
        'subscribe_button': "📢 Kanalga obuna bo'lish"
    },
    'ru': {
        'welcome': "👋 Привет, {name}!\n\nДобро пожаловать в бота для бронирования комнат дискуссий университетской библиотеки.",
        'rules': "📌 **Правила бронирования:**\n• Максимум {max_hours} часа за один раз\n• Максимум {max_daily} часов в день на одну группу\n• Бронь доступна на {advance_days} дней вперед\n• Приходите за 5 минут до начала",
        'choose_action': "Выберите действие:",
        'main_menu': "Главное меню:",
        'choose_date': "Выберите дату для бронирования:",
        'choose_room': "Выберите комнату:",
        'choose_duration': "Выберите продолжительность брони:",
        'choose_time': "Выберите время для {room_name}:\n\nДата: {date}\nЗеленым отмечены свободные слоты ({hours} часа)",
        'enter_group': "Введите название вашей группы (например, ИВТ-401):\n\nДата: {date}\nКомната: {room_name}\nВремя: {time_range}",
        'group_limit': "❌ Группа '{group_name}' уже исчерпала лимит {max_hours} часов на {date}.\nДоступно еще: {available_hours} часа\n\nПожалуйста, введите другую группу или вернитесь в меню.",
        'confirm_booking': "✅ Подтвердите бронирование:\n\n📅 Дата: {date}\n🚪 Комната: {room_name}\n⏰ Время: {time_range}\n👥 Группа: {group_name}\n\nВы согласны?",
        'booking_success': "🎉 Бронирование успешно создано!\n\n📋 Детали:\n• ID брони: #{booking_id}\n• Дата: {date}\n• Комната: {room_name}\n• Время: {time_range}\n• Группа: {group_name}\n\n⚠️ **Важно:**\n1. Сохраните QR-код\n2. Придите за 5 минут до начала\n3. Покажите QR-код библиотекарю\n4. При опоздании >15 минут бронь сгорает",
        'qr_caption': "Ваш QR-код для предъявления",
        'no_bookings': "У вас нет активных бронирований.",
        'my_bookings': "📋 Ваши активные бронирования:\n\n",
        'booking_details': "• Бронь #{id}\n  Дата: {date}\n  Время: {start_time}-{end_time}\n  Комната: {room_name}\n  Группа: {group_name}\n",
        'cancel_success': "✅ Бронирование #{booking_id} успешно отменено.",
        'today_schedule': "📊 Расписание на сегодня:\n\n",
        'room_free': "   Свободно весь день",
        'room_occupied': "   🟡 {start_time}-{end_time} - {group_name}",
        'help_text': """ℹ️ **Помощь по использованию бота**

**Основные команды:**
• /start - Главное меню
• /help - Эта справка
• /language - Изменить язык

**Как забронировать:**
1. Нажмите "Забронировать комнату"
2. Выберите дату, комнату, продолжительность и время
3. Введите название группы
4. Подтвердите бронирование
5. Сохраните QR-код

**Правила:**
• Бронь только на {max_hours} часа
• Не более {max_daily} часов в день на группу
• Бронь за 15+ минут аннулируется
• QR-код обязателен для входа

**Проблемы?**
Обратитесь к библиотекарю или администратору.""",
        'back_to_menu': "🏠 Главное меню",
        'back': "◀️ Назад",
        'cancel': "❌ Отмена",
        'confirm': "✅ Подтвердить",
        'book': "📅 Забронировать комнату",
        'my_bookings_btn': "📋 Мои бронирования",
        'schedule': "📊 Расписание на сегодня",
        'help_btn': "ℹ️ Помощь",
        'select_language': "Пожалуйста, выберите язык:",
        'language_changed': "✅ Язык успешно изменен!",
        'today': "Сегодня",
        'tomorrow': "Завтра",
        'hours': "часа",
        'free': "свободно",
        'occupied': "занято",
        'choose': "Выбрать",
        'select': "Выберите",
        'not_subscribed': "❌ Для использования бота необходимо подписаться на наш канал!\n\n📢 Канал: {channel}\n\nПосле подписки нажмите /start",
        'subscribe_button': "📢 Подписаться на канал"
    },
    'en': {
        'welcome': "👋 Hello, {name}!\n\nWelcome to the university library discussion rooms booking bot.",
        'rules': "📌 **Booking rules:**\n• Maximum {max_hours} hours at a time\n• Maximum {max_daily} hours per day per group\n• Booking available {advance_days} days in advance\n• Arrive 5 minutes before start",
        'choose_action': "Choose an action:",
        'main_menu': "Main menu:",
        'choose_date': "Select date for booking:",
        'choose_room': "Select room:",
        'choose_duration': "Select booking duration:",
        'choose_time': "Select time for {room_name}:\n\nDate: {date}\nGreen slots are available ({hours} hours)",
        'enter_group': "Enter your group name (e.g., ICT-401):\n\nDate: {date}\nRoom: {room_name}\nTime: {time_range}",
        'group_limit': "❌ Group '{group_name}' has exceeded the {max_hours} hour limit on {date}.\nAvailable: {available_hours} hours\n\nPlease enter another group or return to menu.",
        'confirm_booking': "✅ Confirm booking:\n\n📅 Date: {date}\n🚪 Room: {room_name}\n⏰ Time: {time_range}\n👥 Group: {group_name}\n\nDo you agree?",
        'booking_success': "🎉 Booking successfully created!\n\n📋 Details:\n• Booking ID: #{booking_id}\n• Date: {date}\n• Room: {room_name}\n• Time: {time_range}\n• Group: {group_name}\n\n⚠️ **Important:**\n1. Save the QR code\n2. Arrive 5 minutes before start\n3. Show QR code to librarian\n4. If late >15 minutes, booking is cancelled",
        'qr_caption': "Your QR code for presentation",
        'no_bookings': "You have no active bookings.",
        'my_bookings': "📋 Your active bookings:\n\n",
        'booking_details': "• Booking #{id}\n  Date: {date}\n  Time: {start_time}-{end_time}\n  Room: {room_name}\n  Group: {group_name}\n",
        'cancel_success': "✅ Booking #{booking_id} successfully cancelled.",
        'today_schedule': "📊 Schedule for today:\n\n",
        'room_free': "   Free all day",
        'room_occupied': "   🟡 {start_time}-{end_time} - {group_name}",
        'help_text': """ℹ️ **Help on using the bot**

**Main commands:**
• /start - Main menu
• /help - This help
• /language - Change language

**How to book:**
1. Click "Book a room"
2. Select date, room, duration and time
3. Enter group name
4. Confirm booking
5. Save QR code

**Rules:**
• Booking only for {max_hours} hours
• No more than {max_daily} hours per day per group
• Booking cancelled if 15+ minutes late
• QR code required for entry

**Problems?**
Contact the librarian or administrator.""",
        'back_to_menu': "🏠 Main menu",
        'back': "◀️ Back",
        'cancel': "❌ Cancel",
        'confirm': "✅ Confirm",
        'book': "📅 Book a room",
        'my_bookings_btn': "📋 My bookings",
        'schedule': "📊 Today's schedule",
        'help_btn': "ℹ️ Help",
        'select_language': "Please select language:",
        'language_changed': "✅ Language successfully changed!",
        'today': "Today",
        'tomorrow': "Tomorrow",
        'hours': "hours",
        'free': "free",
        'occupied': "occupied",
        'choose': "Choose",
        'select': "Select",
        'not_subscribed': "❌ To use the bot, you must subscribe to our channel!\n\n📢 Channel: {channel}\n\nAfter subscribing, press /start",
        'subscribe_button': "📢 Subscribe to channel"
    }
}


# Вспомогательные функции
def get_user_language(user_id):
    """Получить язык пользователя"""
    return user_language.get(user_id, DEFAULT_LANGUAGE)


def t(user_id, key, **kwargs):
    """Получить текст на языке пользователя"""
    lang = get_user_language(user_id)
    text = TEXTS[lang].get(key, TEXTS[DEFAULT_LANGUAGE].get(key, key))

    # Заменяем переменные
    if kwargs:
        text = text.format(**kwargs)

    return text


async def check_subscription(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Проверка подписки на канал"""
    try:
        member = await context.bot.get_chat_member(chat_id=REQUIRED_CHANNEL, user_id=user_id)
        return member.status in ['creator', 'administrator', 'member']
    except Exception as e:
        logger.error(f"Error checking subscription: {e}")
        return False


def generate_qr_code(booking_id, user_id, room_id, date, time_slot, group_name, lang='uz'):
    """Генерация QR-кода для бронирования"""
    captions = {
        'uz': "Universitet kutubxonasi\nMuhokama xonalarini bron qilish",
        'ru': "Университетская библиотека\nБронирование комнат для дискуссий",
        'en': "University Library\nDiscussion Rooms Booking"
    }

    caption = captions.get(lang, captions['uz'])

    data = f"""{caption}

ID: {booking_id}
Xona/Комната/Room: {room_id}
Sana/Дата/Date: {date}
Vaqt/Время/Time: {time_slot}
Guruh/Группа/Group: {group_name}
Foydalanuvchi ID: {user_id}

Kutubxonachiga ko'rsating/Покажите библиотекарю/Show to librarian
"""

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    bio = BytesIO()
    img.save(bio, 'PNG')
    bio.seek(0)

    return bio


def get_language_keyboard():
    """Клавиатура выбора языка"""
    keyboard = []
    for lang_code, lang_name in LANGUAGES.items():
        keyboard.append([InlineKeyboardButton(lang_name, callback_data=f"lang_{lang_code}")])
    return InlineKeyboardMarkup(keyboard)


def get_dates_keyboard(user_id):
    """Клавиатура для выбора даты (без субботы и воскресенья)"""
    keyboard = []
    today = datetime.date.today()

    days_added = 0
    i = 0

    while days_added < BOOKING_ADVANCE_DAYS:
        date = today + datetime.timedelta(days=i)
        i += 1

        # Пропускаем субботу (5) и воскресенье (6)
        if date.weekday() in [5, 6]:
            continue

        date_str = date.strftime("%d.%m.%Y")

        if days_added == 0:
            label = f"{t(user_id, 'today')} ({date_str})"
        elif days_added == 1:
            label = f"{t(user_id, 'tomorrow')} ({date_str})"
        else:
            weekday_names = {
                'uz': ["Du", "Se", "Ch", "Pa", "Ju"],
                'ru': ["Пн", "Вт", "Ср", "Чт", "Пт"],
                'en': ["Mon", "Tue", "Wed", "Thu", "Fri"]
            }
            lang = get_user_language(user_id)
            weekday = weekday_names.get(lang, weekday_names['uz'])[date.weekday()]
            label = f"{weekday} {date_str}"

        keyboard.append([InlineKeyboardButton(label, callback_data=f"date_{date}")])
        days_added += 1

    keyboard.append([InlineKeyboardButton(t(user_id, 'back_to_menu'), callback_data="back_to_menu")])
    return InlineKeyboardMarkup(keyboard)


def get_rooms_keyboard(user_id):
    """Клавиатура для выбора комнаты"""
    keyboard = []

    for room_id, room_name in ROOMS.items():
        keyboard.append([InlineKeyboardButton(room_name, callback_data=f"room_{room_id}")])

    keyboard.append([
        InlineKeyboardButton(t(user_id, 'back'), callback_data="back_to_date"),
        InlineKeyboardButton(t(user_id, 'back_to_menu'), callback_data="back_to_menu")
    ])
    return InlineKeyboardMarkup(keyboard)


def get_duration_keyboard(user_id):
    """Клавиатура выбора продолжительности"""
    keyboard = []
    for hours in BOOKING_HOURS_OPTIONS:
        if hours == 1.5:
            label = f"1.5 {t(user_id, 'hours')}"
        else:
            label = f"{int(hours)} {t(user_id, 'hours')}"
        keyboard.append([InlineKeyboardButton(label, callback_data=f"duration_{hours}")])

    keyboard.append([
        InlineKeyboardButton(t(user_id, 'back'), callback_data="back_to_room"),
        InlineKeyboardButton(t(user_id, 'back_to_menu'), callback_data="back_to_menu")
    ])
    return InlineKeyboardMarkup(keyboard)


def get_time_slots_keyboard(user_id, available_slots, duration_hours):
    """Клавиатура для выбора времени"""
    keyboard = []
    occupied = [(slot['start_time'], slot['end_time']) for slot in available_slots]

    # Конвертируем TIME_SLOTS в datetime для удобства
    time_objects = []
    for time_str in TIME_SLOTS:
        hour, minute = map(int, time_str.split(':'))
        time_objects.append(datetime.time(hour, minute))

    for i in range(len(time_objects)):
        start_time = time_objects[i]

        # Вычисляем конечное время с учетом продолжительности
        total_minutes = start_time.hour * 60 + start_time.minute + int(duration_hours * 60)
        end_hour = total_minutes // 60
        end_minute = total_minutes % 60

        # Проверяем, не выходит ли за пределы рабочего времени
        if end_hour > CLOSE_TIME or (end_hour == CLOSE_TIME and end_minute > 0):
            continue

        # Форматируем время
        start_str = start_time.strftime("%H:%M")
        end_time_obj = datetime.time(end_hour, end_minute)
        end_str = end_time_obj.strftime("%H:%M")
        time_range = f"{start_str}-{end_str}"

        # Проверяем, свободен ли интервал
        is_available = True
        for occ_start, occ_end in occupied:
            # Проверяем пересечение временных интервалов
            if not (end_str <= occ_start or start_str >= occ_end):
                is_available = False
                break

        if is_available:
            if duration_hours == 1.5:
                label = f"🟢 {time_range} (1.5 {t(user_id, 'hours')})"
            else:
                label = f"🟢 {time_range} (2 {t(user_id, 'hours')})"
            callback_data = f"time_{time_range}"
        else:
            label = f"🔴 {time_range} ({t(user_id, 'occupied')})"
            callback_data = "occupied"

        button = InlineKeyboardButton(label, callback_data=callback_data)
        if is_available:
            keyboard.append([button])

    keyboard.append([
        InlineKeyboardButton(t(user_id, 'back'), callback_data="back_to_duration"),
        InlineKeyboardButton(t(user_id, 'back_to_menu'), callback_data="back_to_menu")
    ])
    return InlineKeyboardMarkup(keyboard)


def get_main_menu_keyboard(user_id):
    """Главное меню"""
    keyboard = [
        [InlineKeyboardButton(t(user_id, 'book'), callback_data="book")],
        [InlineKeyboardButton(t(user_id, 'my_bookings_btn'), callback_data="my_bookings")],
        [InlineKeyboardButton(t(user_id, 'schedule'), callback_data="today_schedule")],
        [InlineKeyboardButton(t(user_id, 'help_btn'), callback_data="help")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_back_to_menu_keyboard(user_id):
    """Просто кнопка вернуться в меню"""
    keyboard = [[InlineKeyboardButton(t(user_id, 'back_to_menu'), callback_data="back_to_menu")]]
    return InlineKeyboardMarkup(keyboard)


# Основные функции бота
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id

    # Проверяем подписку на канал
    is_subscribed = await check_subscription(user_id, context)

    if not is_subscribed:
        keyboard = [[InlineKeyboardButton(
            t(user_id, 'subscribe_button'),
            url=REQUIRED_CHANNEL_LINK
        )]]
        await update.message.reply_text(
            text=t(user_id, 'not_subscribed', channel=REQUIRED_CHANNEL),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return ConversationHandler.END

    # Регистрируем пользователя
    db.add_user(
        user_id=user_id,
        username=user.username,
        full_name=user.full_name,
        group_name=None
    )

    # Если язык уже выбран, показываем главное меню
    if user_id in user_language:
        welcome_text = t(user_id, 'welcome', name=user.first_name)
        rules_text = t(user_id, 'rules',
                       max_hours=MAX_BOOKING_HOURS,
                       max_daily=MAX_DAILY_HOURS_PER_GROUP,
                       advance_days=BOOKING_ADVANCE_DAYS)

        await update.message.reply_text(
            text=f"{welcome_text}\n\n{rules_text}\n\n{t(user_id, 'choose_action')}",
            reply_markup=get_main_menu_keyboard(user_id)
        )
        return SELECTING_ACTION
    else:
        # Показываем выбор языка
        await update.message.reply_text(
            text=t(user_id, 'select_language'),
            reply_markup=get_language_keyboard()
        )
        return SELECTING_LANGUAGE


async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора языка"""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    lang_code = query.data.replace("lang_", "")

    if lang_code in LANGUAGES:
        user_language[user_id] = lang_code

        welcome_text = t(user_id, 'welcome', name=query.from_user.first_name)
        rules_text = t(user_id, 'rules',
                       max_hours=MAX_BOOKING_HOURS,
                       max_daily=MAX_DAILY_HOURS_PER_GROUP,
                       advance_days=BOOKING_ADVANCE_DAYS)

        await query.edit_message_text(
            text=f"{welcome_text}\n\n{rules_text}\n\n{t(user_id, 'choose_action')}",
            reply_markup=get_main_menu_keyboard(user_id)
        )

        return SELECTING_ACTION

    return SELECTING_LANGUAGE


async def language_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для смены языка"""
    user_id = update.effective_user.id

    await update.message.reply_text(
        text=t(user_id, 'select_language'),
        reply_markup=get_language_keyboard()
    )

    return SELECTING_LANGUAGE


async def go_to_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Возврат в главное меню"""
    query = update.callback_query
    user_id = query.from_user.id

    await query.answer()

    await context.bot.send_message(
        chat_id=user_id,
        text=t(user_id, 'main_menu'),
        reply_markup=get_main_menu_keyboard(user_id)
    )

    return SELECTING_ACTION


async def start_booking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    await query.edit_message_text(
        text=t(user_id, 'choose_date'),
        reply_markup=get_dates_keyboard(user_id)
    )

    return SELECTING_DATE


async def select_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    if query.data.startswith("date_"):
        date_str = query.data.replace("date_", "")
        if user_id not in user_data:
            user_data[user_id] = {}
        user_data[user_id]["date"] = date_str

        await query.edit_message_text(
            text=t(user_id, 'choose_room'),
            reply_markup=get_rooms_keyboard(user_id)
        )

        return SELECTING_ROOM
    elif query.data == "back_to_menu":
        return await go_to_main_menu(update, context)


async def select_room(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    if query.data.startswith("room_"):
        room_id = int(query.data.replace("room_", ""))
        user_data[user_id]["room_id"] = room_id

        await query.edit_message_text(
            text=t(user_id, 'choose_duration'),
            reply_markup=get_duration_keyboard(user_id)
        )

        return SELECTING_DURATION
    elif query.data == "back_to_date":
        await query.edit_message_text(
            text=t(user_id, 'choose_date'),
            reply_markup=get_dates_keyboard(user_id)
        )
        return SELECTING_DATE
    elif query.data == "back_to_menu":
        return await go_to_main_menu(update, context)


async def select_duration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    if query.data.startswith("duration_"):
        duration = float(query.data.replace("duration_", ""))
        user_data[user_id]["duration"] = duration

        room_id = user_data[user_id]["room_id"]
        date = user_data[user_id]["date"]

        occupied = db.get_available_slots(room_id, date)

        await query.edit_message_text(
            text=t(user_id, 'choose_time',
                   room_name=ROOMS[room_id],
                   date=date,
                   hours=duration),
            reply_markup=get_time_slots_keyboard(user_id, occupied, duration)
        )

        return SELECTING_TIME
    elif query.data == "back_to_room":
        await query.edit_message_text(
            text=t(user_id, 'choose_room'),
            reply_markup=get_rooms_keyboard(user_id)
        )
        return SELECTING_ROOM
    elif query.data == "back_to_menu":
        return await go_to_main_menu(update, context)


async def select_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    if query.data.startswith("time_"):
        time_range = query.data.replace("time_", "")
        user_data[user_id]["time_range"] = time_range

        await query.edit_message_text(
            text=t(user_id, 'enter_group',
                   date=user_data[user_id]['date'],
                   room_name=ROOMS[user_data[user_id]['room_id']],
                   time_range=time_range)
        )

        return ENTERING_GROUP
    elif query.data == "back_to_duration":
        await query.edit_message_text(
            text=t(user_id, 'choose_duration'),
            reply_markup=get_duration_keyboard(user_id)
        )
        return SELECTING_DURATION
    elif query.data == "back_to_menu":
        return await go_to_main_menu(update, context)


async def enter_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    group_name = update.message.text.strip()

    date = user_data[user_id]["date"]
    duration = user_data[user_id]["duration"]

    # Проверяем лимит группы
    current_hours = db.check_group_limit(group_name, date)
    if current_hours + duration > MAX_DAILY_HOURS_PER_GROUP:
        available_hours = MAX_DAILY_HOURS_PER_GROUP - current_hours
        await update.message.reply_text(
            text=t(user_id, 'group_limit',
                   group_name=group_name,
                   date=date,
                   max_hours=MAX_DAILY_HOURS_PER_GROUP,
                   available_hours=available_hours),
            reply_markup=get_main_menu_keyboard(user_id)
        )
        return SELECTING_ACTION

    user_data[user_id]["group_name"] = group_name

    room_id = user_data[user_id]["room_id"]
    time_range = user_data[user_id]["time_range"]

    confirm_text = t(user_id, 'confirm_booking',
                     date=date,
                     room_name=ROOMS[room_id],
                     time_range=time_range,
                     group_name=group_name)

    keyboard = [
        [
            InlineKeyboardButton(t(user_id, 'confirm'), callback_data="confirm_booking"),
            InlineKeyboardButton(t(user_id, 'cancel'), callback_data="cancel_booking_process")
        ],
        [InlineKeyboardButton(t(user_id, 'back_to_menu'), callback_data="back_to_menu")]
    ]

    await update.message.reply_text(
        text=confirm_text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    return CONFIRMING_BOOKING


async def confirm_booking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    lang = get_user_language(user_id)
    await query.answer()

    if query.data == "confirm_booking":
        data = user_data[user_id]
        start_time, end_time = data["time_range"].split("-")

        booking_id = db.create_booking(
            user_id=user_id,
            room_id=data["room_id"],
            date=data["date"],
            start_time=start_time,
            end_time=end_time,
            group_name=data["group_name"]
        )

        qr_code = generate_qr_code(
            booking_id=booking_id,
            user_id=user_id,
            room_id=data["room_id"],
            date=data["date"],
            time_slot=data["time_range"],
            group_name=data["group_name"],
            lang=lang
        )

        success_text = t(user_id, 'booking_success',
                         booking_id=booking_id,
                         date=data['date'],
                         room_name=ROOMS[data['room_id']],
                         time_range=data['time_range'],
                         group_name=data['group_name'])

        await query.edit_message_text(
            text=success_text,
            reply_markup=get_back_to_menu_keyboard(user_id)
        )

        await context.bot.send_photo(
            chat_id=user_id,
            photo=qr_code,
            caption=t(user_id, 'qr_caption'),
            reply_markup=get_back_to_menu_keyboard(user_id)
        )

        if user_id in user_data:
            del user_data[user_id]

    elif query.data == "cancel_booking_process":
        await query.edit_message_text(
            text=t(user_id, 'cancel'),
            reply_markup=get_main_menu_keyboard(user_id)
        )
        if user_id in user_data:
            del user_data[user_id]

    elif query.data == "back_to_menu":
        return await go_to_main_menu(update, context)

    return SELECTING_ACTION


async def show_my_bookings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    bookings = db.get_user_bookings(user_id)

    if not bookings:
        await query.edit_message_text(
            text=t(user_id, 'no_bookings'),
            reply_markup=get_main_menu_keyboard(user_id)
        )
        return SELECTING_ACTION

    text = t(user_id, 'my_bookings')
    keyboard = []

    for booking in bookings:
        booking_text = t(user_id, 'booking_details',
                         id=booking['id'],
                         date=booking['date'],
                         start_time=booking['start_time'],
                         end_time=booking['end_time'],
                         room_name=ROOMS[booking['room_id']],
                         group_name=booking['group_name'])
        text += booking_text + "\n"

        keyboard.append([
            InlineKeyboardButton(
                f"❌ {t(user_id, 'cancel')} #{booking['id']}",
                callback_data=f"cancel_booking_{booking['id']}"
            )
        ])

    keyboard.append([InlineKeyboardButton(t(user_id, 'back_to_menu'), callback_data="back_to_menu")])

    await query.edit_message_text(
        text=text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    return SELECTING_BOOKING_TO_CANCEL


async def cancel_booking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    if query.data.startswith("cancel_booking_"):
        booking_id = int(query.data.replace("cancel_booking_", ""))

        db.cancel_booking(booking_id, user_id)

        await query.edit_message_text(
            text=t(user_id, 'cancel_success', booking_id=booking_id),
            reply_markup=get_main_menu_keyboard(user_id)
        )

    elif query.data == "back_to_menu":
        return await go_to_main_menu(update, context)

    return SELECTING_ACTION


async def today_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    today = datetime.date.today().isoformat()

    text = t(user_id, 'today_schedule')

    for room_id, room_name in ROOMS.items():
        text += f"**{room_name}**\n"

        occupied = db.get_available_slots(room_id, today)

        if not occupied:
            text += f"   {t(user_id, 'room_free')}\n"
        else:
            for booking in occupied:
                group_name = booking['group_name']
                text += t(user_id, 'room_occupied',
                          start_time=booking['start_time'],
                          end_time=booking['end_time'],
                          group_name=group_name) + "\n"

        text += "\n"

    text += f"\n{t(user_id, 'back_to_menu')}"

    await query.edit_message_text(
        text=text,
        reply_markup=get_back_to_menu_keyboard(user_id),
        parse_mode='Markdown'
    )

    return SELECTING_ACTION


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    help_text = t(user_id, 'help_text',
                  max_hours=MAX_BOOKING_HOURS,
                  max_daily=MAX_DAILY_HOURS_PER_GROUP)

    await query.edit_message_text(
        text=help_text,
        reply_markup=get_main_menu_keyboard(user_id),
        parse_mode='Markdown'
    )

    return SELECTING_ACTION


async def cancel_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in user_data:
        del user_data[user_id]

    await update.message.reply_text(
        text=t(user_id, 'cancel'),
        reply_markup=get_main_menu_keyboard(user_id)
    )

    return SELECTING_ACTION


def main():
    """Запуск бота"""
    os.makedirs("qr_codes", exist_ok=True)

    application = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            SELECTING_LANGUAGE: [
                CallbackQueryHandler(set_language, pattern="^lang_"),
            ],
            SELECTING_ACTION: [
                CallbackQueryHandler(start_booking, pattern="^book$"),
                CallbackQueryHandler(show_my_bookings, pattern="^my_bookings$"),
                CallbackQueryHandler(today_schedule, pattern="^today_schedule$"),
                CallbackQueryHandler(help_command, pattern="^help$"),
                CallbackQueryHandler(go_to_main_menu, pattern="^back_to_menu$"),
            ],
            SELECTING_DATE: [
                CallbackQueryHandler(select_date),
                CallbackQueryHandler(go_to_main_menu, pattern="^back_to_menu$"),
            ],
            SELECTING_ROOM: [
                CallbackQueryHandler(select_room),
                CallbackQueryHandler(go_to_main_menu, pattern="^back_to_menu$"),
            ],
            SELECTING_DURATION: [
                CallbackQueryHandler(select_duration),
                CallbackQueryHandler(go_to_main_menu, pattern="^back_to_menu$"),
            ],
            SELECTING_TIME: [
                CallbackQueryHandler(select_time),
                CallbackQueryHandler(go_to_main_menu, pattern="^back_to_menu$"),
            ],
            ENTERING_GROUP: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, enter_group),
            ],
            CONFIRMING_BOOKING: [
                CallbackQueryHandler(confirm_booking),
                CallbackQueryHandler(go_to_main_menu, pattern="^back_to_menu$"),
            ],
            SELECTING_BOOKING_TO_CANCEL: [
                CallbackQueryHandler(cancel_booking, pattern="^cancel_booking_"),
                CallbackQueryHandler(go_to_main_menu, pattern="^back_to_menu$"),
            ],
        },
        fallbacks=[
            CommandHandler('start', start),
            CommandHandler('help', help_command),
            CommandHandler('language', language_command),
            MessageHandler(filters.TEXT & ~filters.COMMAND, cancel_action),
        ],
    )

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("language", language_command))

    print("🤖 Бот запущен! Нажмите Ctrl+C для остановки.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()