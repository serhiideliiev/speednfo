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
    
    def analyze_seo(self, url):
        """Аналізує SEO-показники сторінки."""
        try:
            import requests
            from bs4 import BeautifulSoup
            
            response = requests.get(url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Аналіз заголовків
            title = soup.title.string if soup.title else None
            title_length = len(title) if title else 0
            
            # Метатеги
            meta_description = soup.find('meta', attrs={'name': 'description'})
            description = meta_description.get('content') if meta_description else None
            description_length = len(description) if description else 0
            
            # H1-H6 заголовки
            headings = {f'h{i}': len(soup.find_all(f'h{i}')) for i in range(1, 7)}
            
            # Аналіз зображень без alt
            images = soup.find_all('img')
            images_without_alt = sum(1 for img in images if not img.get('alt'))
            
            # Підрахунок слів у контенті
            text_content = soup.get_text()
            word_count = len(text_content.split())
            
            # Формування результату
            seo_results = {
                'title': {
                    'present': title is not None,
                    'length': title_length,
                    'status': 'good' if title and 10 <= title_length <= 60 else 'poor'
                },
                'meta_description': {
                    'present': description is not None,
                    'length': description_length,
                    'status': 'good' if description and 50 <= description_length <= 160 else 'poor'
                },
                'headings': headings,
                'images_total': len(images),
                'images_without_alt': images_without_alt,
                'image_alt_ratio': 1 - (images_without_alt / len(images)) if images else 1,
                'word_count': word_count,
                'recommendations': []
            }
            
            # Генерація рекомендацій
            if not title or title_length < 10 or title_length > 60:
                seo_results['recommendations'].append(
                    "Оптимізуйте заголовок сторінки (Title) - він має бути від 10 до 60 символів"
                )
            
            if not description or description_length < 50 or description_length > 160:
                seo_results['recommendations'].append(
                    "Додайте мета-опис сторінки довжиною від 50 до 160 символів"
                )
            
            if headings.get('h1', 0) != 1:
                seo_results['recommendations'].append(
                    "Сторінка повинна містити рівно один H1-заголовок"
                )
            
            if images_without_alt > 0:
                seo_results['recommendations'].append(
                    f"Додайте атрибут alt до {images_without_alt} зображень без опису"
                )
            
            return seo_results
            
        except Exception as e:
            logger.error(f"Помилка при аналізі SEO: {e}", exc_info=True)
            return {"error": f"Помилка при аналізі SEO: {str(e)}"}
    
    def analyze_accessibility(self, url):
        """Аналізує доступність сторінки для людей з обмеженими можливостями."""
        try:
            import requests
            from bs4 import BeautifulSoup
            import re
            import colorsys
            
            response = requests.get(url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Перевірка наявності ARIA атрибутів
            aria_elements = soup.find_all(attrs=lambda attr: any(a.startswith('aria-') for a in attr if isinstance(a, str)))
            
            # Перевірка наявності alt тексту для зображень
            images = soup.find_all('img')
            images_with_alt = sum(1 for img in images if img.get('alt'))
            
            # Перевірка контрасту (спрощена)
            def parse_color(color_str):
                # Конвертує CSS колір у RGB
                if color_str.startswith('#'):
                    if len(color_str) == 4:  # #RGB
                        r = int(color_str[1] + color_str[1], 16)
                        g = int(color_str[2] + color_str[2], 16)
                        b = int(color_str[3] + color_str[3], 16)
                    else:  # #RRGGBB
                        r = int(color_str[1:3], 16)
                        g = int(color_str[3:5], 16)
                        b = int(color_str[5:7], 16)
                    return (r, g, b)
                elif color_str.startswith('rgb'):
                    # rgb(r, g, b) або rgba(r, g, b, a)
                    match = re.search(r'rgb\((\d+),\s*(\d+),\s*(\d+)', color_str)
                    if match:
                        return tuple(map(int, match.groups()))
                return (0, 0, 0)  # За замовчуванням чорний
            
            def calculate_luminance(rgb):
                # Розрахунок відносної яскравості
                r, g, b = [x / 255 for x in rgb]
                r = r / 12.92 if r <= 0.03928 else ((r + 0.055) / 1.055) ** 2.4
                g = g / 12.92 if g <= 0.03928 else ((g + 0.055) / 1.055) ** 2.4
                b = b / 12.92 if b <= 0.03928 else ((b + 0.055) / 1.055) ** 2.4
                return 0.2126 * r + 0.7152 * g + 0.0722 * b
            
            def calculate_contrast(lum1, lum2):
                # Розрахунок контрасту між двома яскравостями
                lighter = max(lum1, lum2)
                darker = min(lum1, lum2)
                return (lighter + 0.05) / (darker + 0.05)
            
            # Спрощена перевірка контрасту для демонстрації
            # В реальному продукті потрібен більш складний аналіз з урахуванням CSS
            contrast_issues = 0
            text_elements = soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'span', 'a'])
            for element in text_elements[:50]:  # Обмежуємо для демонстрації
                style = element.get('style', '')
                if 'color' in style and 'background' in style:
                    # Дуже спрощений аналіз, в реальному проєкті потрібна більш складна логіка
                    fg_match = re.search(r'color:\s*([^;]+)', style)
                    bg_match = re.search(r'background(?:-color)?:\s*([^;]+)', style)
                    
                    if fg_match and bg_match:
                        fg_color = parse_color(fg_match.group(1))
                        bg_color = parse_color(bg_match.group(1))
                        
                        fg_luminance = calculate_luminance(fg_color)
                        bg_luminance = calculate_luminance(bg_color)
                        
                        contrast = calculate_contrast(fg_luminance, bg_luminance)
                        if contrast < 4.5:  # Мінімальний рекомендований контраст для тексту
                            contrast_issues += 1
            
            # Формування результату
            results = {
                'aria_attributes_count': len(aria_elements),
                'images_with_alt_ratio': images_with_alt / len(images) if images else 1,
                'potential_contrast_issues': contrast_issues,
                'form_labels': len(soup.find_all('label')),
                'form_inputs': len(soup.find_all(['input', 'select', 'textarea'])),
                'recommendations': []
            }
            
            # Генерація рекомендацій
            if results['images_with_alt_ratio'] < 1:
                results['recommendations'].append(
                    f"Додайте атрибут alt до всіх зображень для покращення доступності"
                )
            
            if results['potential_contrast_issues'] > 0:
                results['recommendations'].append(
                    f"Перевірте контраст тексту - знайдено приблизно {results['potential_contrast_issues']} потенційних проблем"
                )
            
            if results['form_labels'] < results['form_inputs']:
                results['recommendations'].append(
                    "Переконайтеся, що всі поля форм мають асоційовані <label> елементи"
                )
            
            if len(aria_elements) == 0:
                results['recommendations'].append(
                    "Розгляньте можливість використання ARIA атрибутів для покращення доступності"
                )
            
            return results
            
        except Exception as e:
            logger.error(f"Помилка при аналізі доступності: {e}", exc_info=True)
            return {"error": f"Помилка при аналізі доступності: {str(e)}"}

    def analyze_security(self, url):
        """Аналізує базові показники безпеки веб-сторінки."""
        try:
            import requests
            
            response = requests.get(url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            
            headers = response.headers
            
            # Перевірка наявності важливих заголовків безпеки
            security_headers = {
                'Strict-Transport-Security': headers.get('Strict-Transport-Security'),
                'Content-Security-Policy': headers.get('Content-Security-Policy'),
                'X-Content-Type-Options': headers.get('X-Content-Type-Options'),
                'X-Frame-Options': headers.get('X-Frame-Options'),
                'X-XSS-Protection': headers.get('X-XSS-Protection'),
                'Referrer-Policy': headers.get('Referrer-Policy'),
                'Permissions-Policy': headers.get('Permissions-Policy') or headers.get('Feature-Policy'),
            }
            
            # Перевірка SSL/TLS
            is_https = url.startswith('https://')
            
            # Перевірка наявності cookie параметрів безпеки
            cookies = response.cookies
            secure_cookies = all('secure' in cookie.__dict__ for cookie in cookies)
            httponly_cookies = all('httponly' in cookie.__dict__ for cookie in cookies)
            
            # Формування результату
            results = {
                'uses_https': is_https,
                'security_headers': security_headers,
                'secure_cookies': secure_cookies if cookies else None,
                'httponly_cookies': httponly_cookies if cookies else None,
                'server': headers.get('Server'),
                'recommendations': []
            }
            
            # Генерація рекомендацій
            if not is_https:
                results['recommendations'].append(
                    "Перейдіть на HTTPS для захисту даних користувачів"
                )
            
            for header, value in security_headers.items():
                if value is None:
                    results['recommendations'].append(
                        f"Додайте заголовок безпеки {header}"
                    )
            
            if cookies and not secure_cookies:
                results['recommendations'].append(
                    "Додайте атрибут 'Secure' до всіх cookie для захисту передачі даних"
                )
            
            if cookies and not httponly_cookies:
                results['recommendations'].append(
                    "Додайте атрибут 'HttpOnly' до всіх cookie для захисту від XSS атак"
                )
            
            return results
            
        except Exception as e:
            logger.error(f"Помилка при аналізі безпеки: {e}", exc_info=True)
            return {"error": f"Помилка при аналізі безпеки: {str(e)}"}

    def analyze_with_all_metrics(self, url):
        """Виконує комплексний аналіз з усіма метриками."""
        results = {
            'pagespeed': {},
            'seo': {},
            'accessibility': {},
            'security': {}
        }
        
        # Аналіз PageSpeed для мобільних
        mobile_results = self.analyze(url, "mobile")
        if "error" not in mobile_results:
            results['pagespeed']['mobile'] = mobile_results
        
        # Аналіз PageSpeed для десктопу
        desktop_results = self.analyze(url, "desktop")
        if "error" not in desktop_results:
            results['pagespeed']['desktop'] = desktop_results
        
        # SEO аналіз
        seo_results = self.analyze_seo(url)
        if "error" not in seo_results:
            results['seo'] = seo_results
        
        # Аналіз доступності
        accessibility_results = self.analyze_accessibility(url)
        if "error" not in accessibility_results:
            results['accessibility'] = accessibility_results
        
        # Аналіз безпеки
        security_results = self.analyze_security(url)
        if "error" not in security_results:
            results['security'] = security_results
        
        return results

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