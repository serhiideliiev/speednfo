#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Модуль для взаємодії з Google PageSpeed Insights API
"""

import requests
import logging
import re
import json
import colorsys
from bs4 import BeautifulSoup
from http.cookies import SimpleCookie
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import asyncio  # For potential async implementation later
from concurrent.futures import ThreadPoolExecutor, as_completed
import math  # Add math import for calculations

from config import PAGESPEED_API_KEY, PAGESPEED_API_URL, KEY_METRICS, logger

# Add Ukrainian translations for prioritization
PRIORITIZATION_TERMS_UK = {
    "impact": {"high": "Високий", "medium": "Середній", "low": "Низький"},
    "difficulty": {"easy": "Легко", "medium": "Помірно", "hard": "Складно"},
    "categories": {
        "images": "Зображення",
        "javascript": "JavaScript",
        "css": "CSS",
        "server": "Сервер",
        "fonts": "Шрифти",
        "performance": "Загальна продуктивність",
        "other": "Інше",
    },
    "impact_label": "Вплив",
    "difficulty_label": "Складність",
    "savings_label": "Потенційна економія",
}

# Define heuristics for difficulty and category
AUDIT_HEURISTICS = {
    "modern-image-formats": {"difficulty": "medium", "category": "images"},
    "uses-optimized-images": {"difficulty": "medium", "category": "images"},
    "offscreen-images": {"difficulty": "medium", "category": "images"},
    "efficient-animated-content": {"difficulty": "medium", "category": "images"},
    "uses-responsive-images": {"difficulty": "hard", "category": "images"},
    "unminified-css": {"difficulty": "easy", "category": "css"},
    "unused-css-rules": {"difficulty": "hard", "category": "css"},
    "unminified-javascript": {"difficulty": "easy", "category": "javascript"},
    "unused-javascript": {"difficulty": "hard", "category": "javascript"},
    "uses-long-cache-ttl": {"difficulty": "medium", "category": "server"},
    "render-blocking-resources": {"difficulty": "hard", "category": "performance"},
    "total-blocking-time": {"difficulty": "hard", "category": "performance"},
    "server-response-time": {"difficulty": "medium", "category": "server"},
    "redirects": {"difficulty": "easy", "category": "server"},
    "uses-rel-preconnect": {"difficulty": "easy", "category": "server"},
    "uses-text-compression": {"difficulty": "easy", "category": "server"},
    "font-display": {"difficulty": "easy", "category": "fonts"},
    "default": {"difficulty": "medium", "category": "other"},
}

# Define impact thresholds (in milliseconds)
IMPACT_THRESHOLDS_MS = {
    "high": 1000,
    "medium": 250,
}

# Define score mapping for impact and difficulty
SCORE_MAPPING = {
    "impact": {"high": 3, "medium": 2, "low": 1},
    "difficulty": {"easy": 1, "medium": 2, "hard": 3},
}


class PageSpeedAnalyzer:
    """
    Клас для аналізу URL за допомогою Google PageSpeed Insights API.
    """
    
    def __init__(self, api_key=None, api_url=None):
        """
        Ініціалізує аналізатор PageSpeed.
        
        Args:
            api_key (str, optional): Ключ API Google PageSpeed. 
                                    За замовчуванням використовується з config.py
            api_url (str, optional): URL API Google PageSpeed.
                                    За замовчуванням використовується з config.py
        """
        self.api_key = api_key or PAGESPEED_API_KEY
        self.api_url = api_url or PAGESPEED_API_URL
        self.session = requests.Session()  # Використовуємо сесію для запитів
        
        # Налаштування заголовків для запитів
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        # Configure retries for transient errors (timeouts, 5xx)
        retry_strategy = Retry(
            total=3,  # Total number of retries
            backoff_factor=1,  # Exponential backoff factor (e.g., 1s, 2s, 4s)
            status_forcelist=[500, 502, 503, 504],  # Retry on these server errors
            allowed_methods=["GET"]  # Only retry GET requests
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
    
    def analyze(self, url, strategy="mobile"):
        """
        Аналізує URL за допомогою Google PageSpeed Insights API.
        
        Args:
            url (str): URL для аналізу
            strategy (str, optional): Стратегія аналізу ('mobile' або 'desktop').
                                     За замовчуванням "mobile"
                                     
        Returns:
            dict: Результати аналізу у форматі словника з ключами:
                - score: загальна оцінка продуктивності (0-100)
                - metrics: словник з основними метриками
                - prioritized_recommendations: структурований об'єкт з пріоритезованими рекомендаціями
                - raw_lighthouse_result: Повний результат Lighthouse (для можливого подальшого аналізу)
                
                У разі помилки повертає словник з ключем "error"
        """
        try:
            # Параметри запиту
            params = {
                "url": url,
                "strategy": strategy,
                "key": self.api_key,
                "locale": "uk",  # Локалізація українською, якщо доступно
                "category": "performance",  # Зосереджуємося на продуктивності
            }
            
            # Виконання запиту до API
            response = self.session.get(
                self.api_url,
                params=params,
                headers=self.headers,
                timeout=120  # Збільшений таймаут для великих сторінок
            )
            response.raise_for_status()
            
            # Обробка відповіді
            data = response.json()
            
            # Перевірка наявності помилки в результаті API
            if "error" in data:
                error_message = data["error"].get("message", "Невідома помилка API")
                return {"error": error_message}
                
            # Перевірка наявності результатів Lighthouse
            if "lighthouseResult" not in data:
                return {"error": "У відповіді API відсутні результати Lighthouse"}
                
            # Підготовка структурованих результатів
            lighthouse_result = data["lighthouseResult"]
            audits = lighthouse_result.get("audits", {})
            
            results = {
                "score": int(lighthouse_result["categories"]["performance"]["score"] * 100),
                "metrics": {},
                "prioritized_recommendations": {},  # Initialize as empty dict
                "raw_lighthouse_result": lighthouse_result  # Include raw result
            }
            
            # Отримання основних метрик
            for metric_id, display_name in KEY_METRICS.items():
                if metric_id in audits:
                    metric = audits[metric_id]
                    results["metrics"][display_name] = {
                        "value": metric.get("displayValue", "N/A"),
                        "rating": self._get_metric_rating(metric),
                        "score": metric.get("score", 0),
                    }
            
            # Збір та пріоритезація рекомендацій
            results["prioritized_recommendations"] = self._prioritize_and_categorize_recommendations(audits)
            
            return results
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Помилка під час запиту до API: {e}", exc_info=True)
            return {"error": f"Помилка під час запиту до API: {str(e)}"}
        except KeyError as e:
            logger.error(f"Помилка у структурі відповіді API: {e}", exc_info=True)
            return {"error": f"Помилка у структурі відповіді API: {str(e)}"}
        except Exception as e:
            logger.error(f"Невідома помилка: {e}", exc_info=True)
            return {"error": f"Невідома помилка: {str(e)}"}

    def _get_metric_rating(self, metric):
        """
        Визначає рейтинг метрики ('good', 'average', 'poor') на основі її оцінки.

        Args:
            metric (dict): Словник метрики з результату Lighthouse.

        Returns:
            str: Рейтинг метрики ('good', 'average', 'poor').
        """
        score = metric.get("score")
        if score is None:
            return "N/A"  # Або інше значення за замовчуванням

        # Стандартні пороги Lighthouse (0.9+ = good, 0.5-0.89 = average, <0.5 = poor)
        if score >= 0.9:
            return "good"
        elif score >= 0.5:
            return "average"
        else:
            return "poor"

    def _prioritize_and_categorize_recommendations(self, audits):
        """
        Пріоритезує та категоризує рекомендації з аудитів Lighthouse.

        Args:
            audits (dict): Словник аудитів з результату Lighthouse.

        Returns:
            dict: Структурований словник з пріоритезованими та категоризованими рекомендаціями.
                  Формат:
                  {
                      "categories": {
                          "Category Name UA": [ recommendation_object, ... ],
                          ...
                      },
                      "summary": { ... }
                  }
        """
        recommendations_list = []
        summary = {
            "total": 0,
            "impact_counts": { "high": 0, "medium": 0, "low": 0 },
            "difficulty_counts": { "easy": 0, "medium": 0, "hard": 0 },
        }

        for audit_id, audit in audits.items():
            # Consider only opportunities and diagnostics with potential savings
            display_mode = audit.get("scoreDisplayMode")
            if display_mode not in ["opportunity", "numeric", "binary"] or audit.get("score") == 1:
                continue

            if not audit.get("title") or not audit.get("description"):
                continue

            # Determine Impact
            potential_savings_ms = 0
            if display_mode == "opportunity" and "details" in audit and audit["details"].get("overallSavingsMs"):
                potential_savings_ms = audit["details"]["overallSavingsMs"]
            elif display_mode == "numeric" and "numericValue" in audit:
                if "ms" in audit.get("numericUnit", ""):
                     potential_savings_ms = audit.get("numericValue", 0)

            impact_level = "low"
            if potential_savings_ms >= IMPACT_THRESHOLDS_MS["high"]:
                impact_level = "high"
            elif potential_savings_ms >= IMPACT_THRESHOLDS_MS["medium"]:
                impact_level = "medium"

            # Determine Difficulty & Category
            heuristics = AUDIT_HEURISTICS.get(audit_id, AUDIT_HEURISTICS["default"])
            difficulty_level = heuristics["difficulty"]
            category_key = heuristics["category"]
            category_name_uk = PRIORITIZATION_TERMS_UK["categories"].get(category_key, PRIORITIZATION_TERMS_UK["categories"]["other"])

            # Calculate Priority Score
            impact_score_num = SCORE_MAPPING["impact"].get(impact_level, 1)
            difficulty_score_num = SCORE_MAPPING["difficulty"].get(difficulty_level, 2)
            priority_score = (impact_score_num / difficulty_score_num) + (impact_score_num * 0.01)

            # Create Recommendation Object
            recommendation = {
                "id": audit_id,
                "title": audit.get("title", "N/A"),
                "description": audit.get("description", ""),
                "impact_level": impact_level,
                "impact_level_uk": PRIORITIZATION_TERMS_UK["impact"].get(impact_level, impact_level),
                "difficulty_level": difficulty_level,
                "difficulty_level_uk": PRIORITIZATION_TERMS_UK["difficulty"].get(difficulty_level, difficulty_level),
                "category_key": category_key,
                "category_name_uk": category_name_uk,
                "potential_savings_ms": round(potential_savings_ms) if potential_savings_ms else None,
                "priority_score": round(priority_score, 2),
                "details": audit.get("details"),
            }
            recommendations_list.append(recommendation)

            # Update summary counts
            summary["total"] += 1
            summary["impact_counts"][impact_level] += 1
            summary["difficulty_counts"][difficulty_level] += 1

        # Sort Recommendations by Priority Score (Descending)
        recommendations_list.sort(key=lambda x: x["priority_score"], reverse=True)

        # Group by Category
        categorized_recommendations = {}
        for rec in recommendations_list:
            category = rec["category_name_uk"]
            if category not in categorized_recommendations:
                categorized_recommendations[category] = []
            categorized_recommendations[category].append(rec)

        return {
            "categories": categorized_recommendations,
            "summary": summary
        }