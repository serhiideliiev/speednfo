#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Конфігураційний модуль для Telegram бота аналізу PageSpeed
Містить константи, налаштування та конфігураційні параметри
"""

import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# Завантаження змінних середовища з .env файлу, якщо він існує
load_dotenv()

# Налаштування логування
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Шлях до директорії проекту
BASE_DIR = Path(__file__).resolve().parent

# Telegram Bot налаштування
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    logger.error("TELEGRAM_BOT_TOKEN environment variable is required")
    sys.exit(1)

# Google PageSpeed Insights API налаштування
PAGESPEED_API_KEY = os.environ.get("PAGESPEED_API_KEY")
if not PAGESPEED_API_KEY:
    logger.error("PAGESPEED_API_KEY environment variable is required")
    sys.exit(1)

PAGESPEED_API_URL = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"

# Шлях до українського шрифту для PDF та візуалізацій
DEFAULT_FONT_PATH = str(BASE_DIR / "fonts" / "Roboto-VariableFont_wdth,wght.ttf") # Correct path to Roboto
FONT_PATH = os.environ.get("PDF_FONT_PATH", DEFAULT_FONT_PATH)

# Перевірка наявності шрифту
if not Path(FONT_PATH).exists():
    logger.warning(f"Font file not found at {FONT_PATH}, visualizations might not use the correct font.")
    FONT_NAME = None # Indicate font is not available
else:
    # Extract font name for Matplotlib registration if needed
    try:
        from matplotlib.font_manager import FontProperties
        font_prop = FontProperties(fname=FONT_PATH)
        FONT_NAME = font_prop.get_name() # Get the actual font name
        logger.info(f"Using font: {FONT_NAME} from {FONT_PATH}")
    except ImportError:
        logger.warning("Matplotlib not installed, cannot determine font name.")
        FONT_NAME = "Roboto" # Assume name if matplotlib isn't available here
    except Exception as e:
        logger.warning(f"Could not determine font name from {FONT_PATH}: {e}. Using fallback name 'Roboto'.")
        FONT_NAME = "Roboto" # Fallback name

# Налаштування PDF
PDF_AUTHOR = "PageSpeed Telegram Bot"
PDF_TITLE = "Звіт аналізу швидкості сайту"
PDF_SUBJECT = "Google PageSpeed Insights"

# Рейтинги продуктивності
PERFORMANCE_RATINGS = {
    "good": {"min": 90, "status": "Відмінно", "emoji": "✅"},
    "average": {"min": 50, "status": "Задовільно", "emoji": "⚠️"},
    "poor": {"min": 0, "status": "Потребує покращення", "emoji": "❌"}
}

# Повідомлення бота
BOT_MESSAGES = {
    "start": (
        "Привіт, {user_name}! 👋\n\n"
        "Я бот для аналізу швидкості завантаження веб-сторінок за допомогою Google PageSpeed Insights.\n\n"
        "🔹 Просто надішліть мені URL веб-сторінки, і я проаналізую її.\n"
        "🔹 Я створю детальний PDF-звіт з результатами аналізу.\n\n"
        "Для отримання допомоги введіть /help."
    ),
    "help": (
        "📌 *Як користуватися ботом:*\n\n"
        "1. Надішліть URL веб-сторінки для аналізу.\n"
        "2. Використовуйте команди для додаткових функцій.\n\n"
        "📌 *Доступні команди:*\n\n"
        "/start - Привітання та початок роботи\n"
        "/help - Показати цю довідку\n"
        "/about - Інформація про бота та його можливості\n"
        "/full <URL> - Повний аналіз сторінки (включаючи PDF-звіт)\n"
        "/compare <URL1> <URL2> - Порівняння швидкості двох сторінок\n"
        "/schedule - Налаштувати автоматичний аналіз за розкладом\n"
        "/listschedules - Показати ваші заплановані аналізи\n\n"
        "⚠️ Переконайтеся, що URL містить префікс http:// або https://"
    ),
    "about": (
        "🤖 *PageSpeed Insights Telegram Bot*\n\n"
        "Цей бот аналізує швидкість завантаження веб-сторінок за допомогою Google PageSpeed Insights API та надає пріоритезовані рекомендації.\n\n"
        "**Основні можливості:**\n"
        "- Аналіз швидкості для мобільних та десктопних версій.\n"
        "- Генерація детального PDF-звіту з метриками та пріоритезованими рекомендаціями.\n"
        "- Порівняння швидкості двох сторінок (/compare).\n"
        "- Автоматичний аналіз за розкладом (/schedule, /listschedules).\n\n"
        "**Доступні команди:** /start, /help, /about, /full, /compare, /schedule, /listschedules\n\n"
        "Версія: 1.1.0\n"
        "Дата: 06.05.2025\n\n"
        "Розроблено з використанням:\n"
        "- Python\n"
        "- python-telegram-bot\n"
        "- Google PageSpeed Insights API\n"
        "- ReportLab"
    ),
    "analysis_started": (
        "🔍 Починаю аналіз URL...\n"
        "Це може зайняти кілька хвилин. Будь ласка, зачекайте."
    ),
    "analysis_complete": "📊 Аналіз завершено. Генерую PDF-звіт...",
    "invalid_url": (
        "⚠️ Це не схоже на правильний URL. Будь ласка, перевірте формат і спробуйте ще раз.\n\n"
        "URL повинен починатися з http:// або https:// та містити домен."
    ),
    "error": (
        "❌ Сталася помилка під час аналізу: {error}\n"
        "Будь ласка, спробуйте ще раз пізніше або перевірте URL."
    ),
    "detail_options": "Бажаєте переглянути детальніший аналіз?",
    "report_caption": (
        "📑 Звіт аналізу для {url}\n\n"
        "📱 Мобільний: {mobile_score}/100\n"
        "🖥️ Десктоп: {desktop_score}/100"
    ),
    "full_analysis_complete": (
        "📊 Комплексний аналіз завершено.\n\n"
        "📱 Mobile Performance: {mobile_score}/100\n"
        "🖥️ Desktop Performance: {desktop_score}/100\n"
        "🔍 SEO Score: {seo_score}/100\n"
        "♿ Accessibility Score: {accessibility_score}/100\n"
        "🔒 Security Score: {security_score}/100"
    ),
    # --- New messages for scheduling ---
    "schedule_ask_url": "Введіть URL, для якого ви хочете налаштувати автоматичний звіт:",
    "schedule_ask_url_again": "Будь ласка, спробуйте ввести URL ще раз.",
    "schedule_ask_frequency": "Оберіть частоту автоматичного генерування звіту:",
    "schedule_success": "✅ Добре! Автоматичний звіт для {url} буде генеруватися {frequency}.",
    "schedule_error": "❌ Помилка при налаштуванні розкладу: {error}",
    "schedule_cancelled": "❌ Налаштування розкладу скасовано.",
    "list_schedule_header": "📅 *Ваші заплановані звіти:*\n",
    "list_schedule_no_jobs": "У вас немає запланованих звітів. Використовуйте /schedule, щоб додати.",
    "schedule_cancel_prompt": "Оберіть звіт, який хочете скасувати:", # Not used currently, cancellation via buttons in list
    "schedule_cancel_success": "✅ Автоматичний звіт для {url} скасовано.",
    "schedule_cancel_error": "❌ Помилка при скасуванні звіту: {error}",
    "schedule_cancel_not_found": "❌ Запланований звіт не знайдено.",
    "scheduled_error": "❌ Помилка під час планового аналізу для {url}: {error}", # Error message sent by the scheduled job
    # --- New messages for compare feature ---
    "compare_usage": (
        "⚠️ Неправильне використання команди. Формат: /compare <ваш_URL> <URL_конкурента_1> [URL_конкурента_2] [URL_конкурента_3]\n\n"
        "Приклад: /compare https://my-site.com https://competitor1.com https://competitor2.com"
    ),
    "compare_start": "🔍 Починаю порівняльний аналіз URL...",
    "compare_error": "❌ Сталася помилка під час порівняльного аналізу: {error}",
    "compare_partial_error": "⚠️ Деякі URL не вдалося проаналізувати. Результати можуть бути неповними.",
    "compare_complete": "📊 Порівняльний аналіз завершено.",
    "compare_result_header": "📊 *Результати порівняльного аналізу PageSpeed*\n",
    "compare_site_header": "\n*{rank}. {url}*",
    "compare_score": "  Загальна оцінка: {score}/100 {emoji}",
    "compare_metric": "  {metric_name}: {value} ({rating})",
    "compare_no_data": "  (Немає даних)",
    "compare_rank_note": "\n_(Ранжування базується лише на наданих URL)_"
}

# Ключові метрики для включення до звіту
KEY_METRICS = {
    'first-contentful-paint': 'Перший вміст',
    'speed-index': 'Індекс швидкості',
    'largest-contentful-paint': 'Найбільший вміст',
    'interactive': 'Час до інтерактивності',
    'total-blocking-time': 'Загальний час блокування',
    'cumulative-layout-shift': 'Сукупне зміщення макета'
}