#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Утилітарні функції для Telegram бота аналізу PageSpeed
"""

import re
from urllib.parse import urlparse
from datetime import datetime
from config import PERFORMANCE_RATINGS, logger


def is_valid_url(url):
    """
    Перевіряє, чи є рядок коректним URL.
    
    Args:
        url (str): URL для перевірки
        
    Returns:
        bool: True, якщо URL коректний, False в іншому випадку
    """
    if not url:
        return False
        
    # Базова перевірка формату
    url_regex = re.compile(
        r"^(?:http|https)://"  # http:// або https://
        r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|"  # домен
        r"localhost|"  # localhost
        r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # IP
        r"(?::\d+)?"  # опціональний порт
        r"(?:/?|[/?]\S+)$", re.IGNORECASE)
        
    if not url_regex.match(url):
        return False
        
    # Додаткова перевірка через urlparse
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except ValueError:
        return False


def get_domain_from_url(url):
    """
    Витягує домен з URL.
    
    Args:
        url (str): URL для обробки
        
    Returns:
        str: Домен з URL або порожній рядок, якщо URL некоректний
    """
    try:
        parsed_url = urlparse(url)
        return parsed_url.netloc
    except (ValueError, AttributeError):
        logger.warning(f"Не вдалося витягти домен з URL: {url}")
        return ""


def sanitize_filename(filename):
    """
    Очищує ім'я файлу від неприпустимих символів.
    
    Args:
        filename (str): Ім'я файлу для очищення
        
    Returns:
        str: Очищене ім'я файлу
    """
    # Видалення неприпустимих символів
    sanitized = re.sub(r'[\\/*?:"<>|]', "", filename)
    # Заміна пробілів на підкреслення
    sanitized = sanitized.replace(" ", "_")
    # Обмеження довжини
    if len(sanitized) > 200:
        sanitized = sanitized[:190] + "..." + sanitized[-7:]
        
    return sanitized


def generate_filename(url, prefix="pagespeed", extension="pdf"):
    """
    Генерує унікальне ім'я файлу на основі URL та поточного часу.
    
    Args:
        url (str): URL для включення в ім'я файлу
        prefix (str, optional): Префікс для імені файлу. Типово "pagespeed"
        extension (str, optional): Розширення файлу. Типово "pdf"
        
    Returns:
        str: Унікальне ім'я файлу
    """
    domain = get_domain_from_url(url)
    domain = sanitize_filename(domain)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Якщо домен порожній, використовуємо тільки часову мітку
    if not domain:
        return f"{prefix}_{timestamp}.{extension}"
        
    return f"{prefix}_{domain}_{timestamp}.{extension}"


def get_score_status(score):
    """
    Повертає статус на основі оцінки продуктивності.
    
    Args:
        score (int): Оцінка продуктивності (0-100)
        
    Returns:
        str: Опис статусу продуктивності
    """
    # Валідація вхідних даних
    try:
        score = int(score)
    except (ValueError, TypeError):
        logger.warning(f"Неправильний формат оцінки: {score}, використовую 0")
        score = 0
        
    # Пошук відповідного статусу
    for rating, data in sorted(
        PERFORMANCE_RATINGS.items(), 
        key=lambda x: x[1]["min"], 
        reverse=True
    ):
        if score >= data["min"]:
            return data["status"]
    
    # За замовчуванням - найгірший рейтинг
    return PERFORMANCE_RATINGS["poor"]["status"]


def get_score_emoji(score):
    """
    Повертає емодзі на основі оцінки продуктивності.
    
    Args:
        score (int): Оцінка продуктивності (0-100)
        
    Returns:
        str: Емодзі, що відповідає рейтингу
    """
    # Валідація вхідних даних
    try:
        score = int(score)
    except (ValueError, TypeError):
        logger.warning(f"Неправильний формат оцінки: {score}, використовую 0")
        score = 0
        
    # Пошук відповідного емодзі
    for rating, data in sorted(
        PERFORMANCE_RATINGS.items(), 
        key=lambda x: x[1]["min"], 
        reverse=True
    ):
        if score >= data["min"]:
            return data["emoji"]
    
    # За замовчуванням - найгірший рейтинг
    return PERFORMANCE_RATINGS["poor"]["emoji"]


def format_metric_rating(metric_data):
    """
    Форматує рейтинг метрики для відображення у повідомленні.
    
    Args:
        metric_data (dict): Дані метрики з результатів аналізу
        
    Returns:
        str: Відформатований рейтинг з емодзі
    """
    if not metric_data or not isinstance(metric_data, dict):
        return "❌ Дані відсутні"
        
    rating = metric_data.get("rating", "poor")
    value = metric_data.get("value", "N/A")
    
    emoji = "✅" if rating == "good" else "⚠️" if rating == "average" else "❌"
    return f"{emoji} {value} ({rating})"