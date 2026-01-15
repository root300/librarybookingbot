import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID', 0))

# Настройки бронирования
MAX_BOOKING_HOURS = 2
MIN_BOOKING_HOURS = 1.5
BOOKING_HOURS_OPTIONS = [1.5, 2]  # Можно выбрать 1.5 или 2 часа
MAX_DAILY_HOURS_PER_GROUP = 4
BOOKING_ADVANCE_DAYS = 4  # Изменено с 14 на 4 дня
OPEN_TIME = 8.5  # 8:30 в десятичном формате
CLOSE_TIME = 20  # 20:00

# Обязательная подписка на канал
REQUIRED_CHANNEL = "@uzlibuz"
REQUIRED_CHANNEL_LINK = "https://t.me/uzlibuz"

# Комнаты
ROOMS = {
    1: "Discussion room - 1",
    2: "Discussion room - 2"
}

# Временные слоты (каждые 30 минут)
TIME_SLOTS = []
for hour in range(8, 20):  # с 8:00 до 20:00
    for minute in [0, 30]:
        if hour == 8 and minute == 0:  # пропускаем 8:00, начинаем с 8:30
            continue
        if hour == 20 and minute == 30:  # заканчиваем в 20:00
            break
        time_str = f"{hour:02d}:{minute:02d}"
        TIME_SLOTS.append(time_str)

# Языки
LANGUAGES = {
    'uz': "🇺🇿 O'zbekcha",
    'ru': "🇷🇺 Русский",
    'en': "🇬🇧 English"
}

DEFAULT_LANGUAGE = 'uz'