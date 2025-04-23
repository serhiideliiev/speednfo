#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Точка входу для запуску Telegram бота аналізу PageSpeed
"""

import logging
import os
from config import logger
from bot import PageSpeedBot


def check_environment():
    """
    Перевіряє наявність необхідних змінних середовища.
    Виводить попередження, якщо якісь налаштування відсутні.
    """
    # Перевірка наявності токену Telegram Bot API
    if "TELEGRAM_BOT_TOKEN" not in os.environ:
        logger.warning(
            "Змінна середовища TELEGRAM_BOT_TOKEN не встановлена. "
            "Буде використано значення за замовчуванням з config.py"
        )
    
    # Перевірка наявності API ключа Google PageSpeed
    if "PAGESPEED_API_KEY" not in os.environ:
        logger.warning(
            "Змінна середовища PAGESPEED_API_KEY не встановлена. "
            "Буде використано значення за замовчуванням з config.py"
        )
    
    # Перевірка наявності шляху до шрифту
    if "PDF_FONT_PATH" not in os.environ:
        logger.warning(
            "Змінна середовища PDF_FONT_PATH не встановлена. "
            "Буде використано значення за замовчуванням з config.py"
        )


def main():
    """
    Основна функція для запуску бота.
    
    Перевіряє налаштування середовища та запускає Telegram бота.
    """
    # Перевірка змінних середовища
    check_environment()
    
    # Створення та запуск бота
    logger.info("Ініціалізація бота...")
    bot = PageSpeedBot()
    logger.info("Запуск бота...")
    bot.run()


if __name__ == '__main__':
    main()