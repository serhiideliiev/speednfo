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

# Шлях до українського шрифту для PDF
DEFAULT_FONT_PATH = str(BASE_DIR / "fonts" / "ukrainian_font.ttf")
FONT_PATH = os.environ.get("PDF_FONT_PATH", DEFAULT_FONT_PATH)

# Перевірка наявності шрифту
if not Path(FONT_PATH).exists():
    logger.warning(f"Font file not found at {FONT_PATH}, will use fallback font")
    FONT_PATH = None

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
        "1. Просто надішліть мені URL веб-сторінки, яку хочете проаналізувати\n"
        "2. Дочекайтеся завершення аналізу\n"
        "3. Отримайте PDF-звіт з результатами\n\n"
        "📌 *Доступні команди:*\n\n"
        "/start - Запустити бота\n"
        "/help - Показати цю довідку\n"
        "/about - Інформація про бота\n\n"
        "⚠️ Переконайтеся, що URL містить префікс http:// або https://"
    ),
    "about": (
        "🤖 *PageSpeed Insights Telegram Bot*\n\n"
        "Цей бот допомагає аналізувати швидкість завантаження веб-сторінок за допомогою Google PageSpeed Insights API.\n\n"
        "Версія: 1.0.0\n"
        "Дата: 22.04.2025\n\n"
        "Розроблено з використанням:\n"
        "- Python 3.14\n"
        "- python-telegram-bot\n"
        "- Google PageSpeed Insights API\n"
        "- ReportLab"
    ),
    "analysis_start": (
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
    )
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