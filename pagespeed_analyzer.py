#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Модуль для взаємодії з Google PageSpeed Insights API
"""

import requests
import logging
from config import PAGESPEED_API_KEY, PAGESPEED_API_URL, KEY_METRICS, logger

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
                - recommendations: список рекомендацій для оптимізації
                
                У разі помилки повертає словник з ключем "error"
        """
        try:
            # Параметри запиту
            params = {
                'url': url,
                'strategy': strategy,
                'key': self.api_key,
                'locale': 'uk',  # Локалізація українською, якщо доступно
            }
            
            # Виконання запиту до API
            response = requests.get(self.api_url, params=params)
            response.raise_for_status()
            
            # Обробка відповіді
            data = response.json()
            
            # Підготовка структурованих результатів
            results = {
                'score': int(data['lighthouseResult']['categories']['performance']['score'] * 100),
                'metrics': {},
                'recommendations': []
            }
            
            # Отримання основних метрик
            metrics = data['lighthouseResult']['audits']
            
            # Додавання основних метрик до результатів
            for metric_id, display_name in KEY_METRICS.items():
                if metric_id in metrics:
                    metric = metrics[metric_id]
                    results['metrics'][display_name] = {
                        'value': metric['displayValue'],
                        'rating': self._get_metric_rating(metric)
                    }
            
            # Збір рекомендацій щодо поліпшення швидкості
            self._extract_recommendations(data, results)
            
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
        Визначає рейтинг метрики на основі її оцінки.
        
        Args:
            metric (dict): Дані метрики з відповіді API
            
        Returns:
            str: Рейтинг метрики ("good", "average" або "poor")
        """
        if 'score' in metric:
            score = metric['score']
            if score >= 0.9:
                return 'good'
            elif score >= 0.5:
                return 'average'
            else:
                return 'poor'
        else:
            # Якщо оцінка відсутня, використовуємо scoreDisplayMode
            return metric.get('scoreDisplayMode', 'not_available')
    
    def _extract_recommendations(self, data, results):
        """
        Витягує рекомендації щодо оптимізації з даних API.
        
        Args:
            data (dict): Дані відповіді API
            results (dict): Словник результатів для заповнення
        """
        audits = data['lighthouseResult']['audits']
        
        for audit_id, audit in audits.items():
            # Перевіряємо, чи це "можливість оптимізації"
            if ('details' in audit and 
                'type' in audit['details'] and 
                audit['details']['type'] == 'opportunity'):
                
                # Додаємо рекомендацію, якщо оцінка нижче максимальної
                if 'score' in audit and audit['score'] < 1:
                    results['recommendations'].append(audit['title'])