#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Утилітарні функції для Telegram бота аналізу PageSpeed
"""

from urllib.parse import urlparse
from datetime import datetime
from config import PERFORMANCE_RATINGS


def is_valid_url(url):
    """
    Перевіряє, чи є рядок коректним URL.
    
    Args:
        url (str): URL для перевірки
        
    Returns:
        bool: True, якщо URL коректний, False в іншому випадку
    """
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
        str: Домен з URL
    """
    return urlparse(url).netloc


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
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{domain}_{timestamp}.{extension}"


def get_score_status(score):
    """
    Повертає статус на основі оцінки продуктивності.
    
    Args:
        score (int): Оцінка продуктивності (0-100)
        
    Returns:
        str: Опис статусу продуктивності
    """
    for rating, data in sorted(
        PERFORMANCE_RATINGS.items(), 
        key=lambda x: x[1]['min'], 
        reverse=True
    ):
        if score >= data['min']:
            return data['status']
    
    return PERFORMANCE_RATINGS['poor']['status']  # За замовчуванням - найгірший рейтинг


def get_score_emoji(score):
    """
    Повертає емодзі на основі оцінки продуктивності.
    
    Args:
        score (int): Оцінка продуктивності (0-100)
        
    Returns:
        str: Емодзі, що відповідає рейтингу
    """
    for rating, data in sorted(
        PERFORMANCE_RATINGS.items(), 
        key=lambda x: x[1]['min'], 
        reverse=True
    ):
        if score >= data['min']:
            return data['emoji']
    
    return PERFORMANCE_RATINGS['poor']['emoji']  # За замовчуванням - найгірший рейтинг


def format_metric_rating(metric_data):
    """
    Форматує рейтинг метрики для відображення у повідомленні.
    
    Args:
        metric_data (dict): Дані метрики з результатів аналізу
        
    Returns:
        str: Відформатований рейтинг з емодзі
    """
    rating = metric_data['rating']
    emoji = "✅" if rating == "good" else "⚠️" if rating == "average" else "❌"
    return f"{emoji} {metric_data['value']} ({rating})"