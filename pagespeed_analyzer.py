#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Модуль для взаємодії з Google PageSpeed Insights API
"""

import requests
import logging
import re
import json
# Імпортуємо всі необхідні бібліотеки на початку файлу
import colorsys
from bs4 import BeautifulSoup
from http.cookies import SimpleCookie

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
        self.session = requests.Session()  # Використовуємо сесію для запитів
        
        # Налаштування заголовків для запитів
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
    
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
                "url": url,
                "strategy": strategy,
                "key": self.api_key,
                "locale": "uk",  # Локалізація українською, якщо доступно
            }
            
            # Виконання запиту до API
            response = self.session.get(self.api_url, params=params, headers=self.headers, timeout=30)
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
            results = {
                "score": int(data["lighthouseResult"]["categories"]["performance"]["score"] * 100),
                "metrics": {},
                "recommendations": []
            }
            
            # Отримання основних метрик
            audits = data["lighthouseResult"]["audits"]
            
            # Додавання основних метрик до результатів
            for metric_id, display_name in KEY_METRICS.items():
                if metric_id in audits:
                    metric = audits[metric_id]
                    results["metrics"][display_name] = {
                        "value": metric.get("displayValue", "N/A"),
                        "rating": self._get_metric_rating(metric)
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
        """
        Аналізує SEO-показники сторінки.
        
        Args:
            url (str): URL для аналізу
            
        Returns:
            dict: Результати аналізу SEO
        """
        try:
            # Виконання запиту до сторінки
            response = self.session.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            # Парсинг HTML
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Аналіз заголовків
            title = soup.title.string if soup.title else None
            title_length = len(title) if title else 0
            
            # Метатеги
            meta_description = soup.find("meta", attrs={"name": "description"})
            description = meta_description.get("content") if meta_description else None
            description_length = len(description) if description else 0
            
            # H1-H6 заголовки
            headings = {f"h{i}": len(soup.find_all(f"h{i}")) for i in range(1, 7)}
            
            # Аналіз зображень без alt
            images = soup.find_all("img")
            images_without_alt = sum(1 for img in images if not img.get("alt"))
            images_total = len(images)
            
            # Підрахунок слів у контенті
            text_content = soup.get_text()
            word_count = len(text_content.split())
            
            # Формування результату
            seo_results = {
                "title": {
                    "present": title is not None,
                    "length": title_length,
                    "status": "good" if title and 10 <= title_length <= 60 else "poor"
                },
                "meta_description": {
                    "present": description is not None,
                    "length": description_length,
                    "status": "good" if description and 50 <= description_length <= 160 else "poor"
                },
                "headings": headings,
                "images_total": images_total,
                "images_without_alt": images_without_alt,
                "image_alt_ratio": 1 - (images_without_alt / images_total) if images_total else 1,
                "word_count": word_count,
                "recommendations": []
            }
            
            # Генерація рекомендацій
            if not title or title_length < 10 or title_length > 60:
                seo_results["recommendations"].append(
                    "Оптимізуйте заголовок сторінки (Title) - він має бути від 10 до 60 символів"
                )
            
            if not description or description_length < 50 or description_length > 160:
                seo_results["recommendations"].append(
                    "Додайте мета-опис сторінки довжиною від 50 до 160 символів"
                )
            
            if headings.get("h1", 0) != 1:
                seo_results["recommendations"].append(
                    "Сторінка повинна містити рівно один H1-заголовок"
                )
            
            if images_without_alt > 0:
                seo_results["recommendations"].append(
                    f"Додайте атрибут alt до {images_without_alt} зображень без опису"
                )
            
            return seo_results
            
        except Exception as e:
            logger.error(f"Помилка при аналізі SEO: {e}", exc_info=True)
            return {"error": f"Помилка при аналізі SEO: {str(e)}"}
    
    def analyze_accessibility(self, url):
        """
        Аналізує доступність сторінки для людей з обмеженими можливостями.
        
        Args:
            url (str): URL для аналізу
            
        Returns:
            dict: Результати аналізу доступності
        """
        try:
            # Виконання запиту до сторінки
            response = self.session.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            # Парсинг HTML
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Перевірка наявності ARIA атрибутів
            aria_elements = soup.find_all(
                lambda tag: any(attr for attr in tag.attrs if isinstance(attr, str) and attr.startswith("aria-"))
            )
            
            # Перевірка наявності alt тексту для зображень
            images = soup.find_all("img")
            images_with_alt = sum(1 for img in images if img.get("alt"))
            images_total = len(images)
            
            # Перевірка форм і полів вводу
            form_labels = soup.find_all("label")
            form_inputs = soup.find_all(["input", "select", "textarea"])
            
            # Спрощена перевірка контрасту для демонстрації
            # В реальному продукті потрібен більш складний аналіз з урахуванням CSS
            contrast_issues = self._check_contrast_issues(soup)
            
            # Формування результату
            results = {
                "aria_attributes_count": len(aria_elements),
                "images_with_alt_ratio": images_with_alt / images_total if images_total else 1,
                "potential_contrast_issues": contrast_issues,
                "form_labels": len(form_labels),
                "form_inputs": len(form_inputs),
                "recommendations": []
            }
            
            # Генерація рекомендацій
            if results["images_with_alt_ratio"] < 1:
                results["recommendations"].append(
                    f"Додайте атрибут alt до всіх зображень для покращення доступності"
                )
            
            if results["potential_contrast_issues"] > 0:
                results["recommendations"].append(
                    f"Перевірте контраст тексту - знайдено приблизно {results['potential_contrast_issues']} потенційних проблем"
                )
            
            if results["form_labels"] < results["form_inputs"]:
                results["recommendations"].append(
                    "Переконайтеся, що всі поля форм мають асоційовані <label> елементи"
                )
            
            if len(aria_elements) == 0:
                results["recommendations"].append(
                    "Розгляньте можливість використання ARIA атрибутів для покращення доступності"
                )
            
            return results
            
        except Exception as e:
            logger.error(f"Помилка при аналізі доступності: {e}", exc_info=True)
            return {"error": f"Помилка при аналізі доступності: {str(e)}"}

    def analyze_security(self, url):
        """
        Аналізує базові показники безпеки веб-сторінки.
        
        Args:
            url (str): URL для аналізу
            
        Returns:
            dict: Результати аналізу безпеки
        """
        try:
            # Виконання запиту до сторінки
            response = self.session.get(url, headers=self.headers, timeout=30, allow_redirects=True)
            response.raise_for_status()
            
            # Отримання заголовків відповіді
            headers = response.headers
            
            # Перевірка наявності важливих заголовків безпеки
            security_headers = {
                "Strict-Transport-Security": headers.get("Strict-Transport-Security"),
                "Content-Security-Policy": headers.get("Content-Security-Policy"),
                "X-Content-Type-Options": headers.get("X-Content-Type-Options"),
                "X-Frame-Options": headers.get("X-Frame-Options"),
                "X-XSS-Protection": headers.get("X-XSS-Protection"),
                "Referrer-Policy": headers.get("Referrer-Policy"),
                "Permissions-Policy": headers.get("Permissions-Policy") or headers.get("Feature-Policy"),
            }
            
            # Перевірка SSL/TLS
            is_https = url.startswith("https://")
            final_url = response.url
            is_redirected_to_https = final_url.startswith("https://") and url.startswith("http://")
            
            # Перевірка cookie параметрів
            cookies = self._analyze_cookies(response.cookies)
            
            # Формування результату
            results = {
                "uses_https": is_https or is_redirected_to_https,
                "security_headers": security_headers,
                "secure_cookies": cookies["secure"],
                "httponly_cookies": cookies["httponly"],
                "samesite_cookies": cookies["samesite"],
                "server": headers.get("Server"),
                "recommendations": []
            }
            
            # Генерація рекомендацій
            if not results["uses_https"]:
                results["recommendations"].append(
                    "Перейдіть на HTTPS для захисту даних користувачів"
                )
            
            for header, value in security_headers.items():
                if value is None:
                    results["recommendations"].append(
                        f"Додайте заголовок безпеки {header}"
                    )
            
            if cookies["count"] > 0:
                if not cookies["secure"]:
                    results["recommendations"].append(
                        "Додайте атрибут 'Secure' до всіх cookie для захисту передачі даних"
                    )
                
                if not cookies["httponly"]:
                    results["recommendations"].append(
                        "Додайте атрибут 'HttpOnly' до всіх cookie для захисту від XSS атак"
                    )
                    
                if not cookies["samesite"]:
                    results["recommendations"].append(
                        "Додайте атрибут 'SameSite' до cookie для захисту від CSRF атак"
                    )
            
            return results
            
        except Exception as e:
            logger.error(f"Помилка при аналізі безпеки: {e}", exc_info=True)
            return {"error": f"Помилка при аналізі безпеки: {str(e)}"}

    def analyze_with_all_metrics(self, url):
        """
        Виконує комплексний аналіз з усіма метриками.
        
        Args:
            url (str): URL для аналізу
            
        Returns:
            dict: Комплексні результати аналізу
        """
        try:
            results = {
                "pagespeed": {},
                "seo": {},
                "accessibility": {},
                "security": {}
            }
            
            # Аналіз PageSpeed для мобільних
            mobile_results = self.analyze(url, "mobile")
            if "error" not in mobile_results:
                results["pagespeed"]["mobile"] = mobile_results
            
            # Аналіз PageSpeed для десктопу
            desktop_results = self.analyze(url, "desktop")
            if "error" not in desktop_results:
                results["pagespeed"]["desktop"] = desktop_results
            
            # SEO аналіз
            seo_results = self.analyze_seo(url)
            if "error" not in seo_results:
                results["seo"] = seo_results
            
            # Аналіз доступності
            accessibility_results = self.analyze_accessibility(url)
            if "error" not in accessibility_results:
                results["accessibility"] = accessibility_results
            
            # Аналіз безпеки
            security_results = self.analyze_security(url)
            if "error" not in security_results:
                results["security"] = security_results
            
            return results
            
        except Exception as e:
            logger.error(f"Помилка при комплексному аналізі: {e}", exc_info=True)
            return {"error": f"Помилка при комплексному аналізі: {str(e)}"}

    def _get_metric_rating(self, metric):
        """
        Визначає рейтинг метрики на основі її оцінки.
        
        Args:
            metric (dict): Дані метрики з відповіді API
            
        Returns:
            str: Рейтинг метрики ("good", "average" або "poor")
        """
        if "score" in metric:
            score = metric["score"]
            if score >= 0.9:
                return "good"
            elif score >= 0.5:
                return "average"
            else:
                return "poor"
        else:
            # Якщо оцінка відсутня, використовуємо scoreDisplayMode
            return metric.get("scoreDisplayMode", "not_available")
    
    def _extract_recommendations(self, data, results):
        """
        Extracts and prioritizes optimization recommendations from API data.
        """
        try:
            audits = data["lighthouseResult"]["audits"]
            critical_recommendations = []
            important_recommendations = []
            other_recommendations = []
            
            for audit_id, audit in audits.items():
                # Skip if no title or already perfect score
                if "title" not in audit or audit.get("score") == 1:
                    continue
                    
                # Determine recommendation priority based on score and importance
                if ("details" in audit and audit.get("details", {}).get("type") == "opportunity"):
                    # Check if this is a critical issue
                    if audit.get("score", 1) == 0 or audit_id in ["render-blocking-resources", "largest-contentful-paint"]:
                        critical_recommendations.append(audit["title"])
                    # Important but not critical
                    elif audit.get("score", 1) <= 0.5:
                        important_recommendations.append(audit["title"])
                    # Other opportunities
                    else:
                        other_recommendations.append(audit["title"])
                # Add other audits with poor scores
                elif audit.get("score", 1) <= 0.5:
                    other_recommendations.append(audit["title"])
            
            # Add recommendations to results in priority order, limiting to avoid overwhelming
            results["recommendations"] = critical_recommendations + important_recommendations + other_recommendations[:10]
            results["recommendation_priorities"] = {
                "critical": len(critical_recommendations),
                "important": len(important_recommendations),
                "other": len(other_recommendations)
            }
                
        except Exception as e:
            logger.error(f"Помилка при витяганні рекомендацій: {e}", exc_info=True)

    def _check_contrast_issues(self, soup):
        """
        Виконує спрощену перевірку контрасту для елементів сторінки.
        
        Args:
            soup (BeautifulSoup): Об'єкт BeautifulSoup для аналізу
            
        Returns:
            int: Кількість потенційних проблем контрасту
        """
        contrast_issues = 0
        text_elements = soup.find_all(["p", "h1", "h2", "h3", "h4", "h5", "h6", "span", "a"])
        
        for element in text_elements[:50]:  # Обмежуємо для демонстрації
            style = element.get("style", "")
            
            # Спрощена перевірка - у реальному додатку потрібен більш складний аналіз
            if "color" in style and ("background" in style or "background-color" in style):
                contrast_issues += 1
                
        return contrast_issues

    def _parse_color(self, color_str):
        """
        Конвертує CSS колір у RGB.
        
        Args:
            color_str (str): CSS колір у форматі #RGB, #RRGGBB, rgb() або rgba()
            
        Returns:
            tuple: RGB кортеж (r, g, b)
        """
        try:
            if color_str.startswith("#"):
                if len(color_str) == 4:  # #RGB
                    r = int(color_str[1] + color_str[1], 16)
                    g = int(color_str[2] + color_str[2], 16)
                    b = int(color_str[3] + color_str[3], 16)
                else:  # #RRGGBB
                    r = int(color_str[1:3], 16)
                    g = int(color_str[3:5], 16)
                    b = int(color_str[5:7], 16)
                return (r, g, b)
            elif color_str.startswith("rgb"):
                # rgb(r, g, b) або rgba(r, g, b, a)
                match = re.search(r'rgb\((\d+),\s*(\d+),\s*(\d+)', color_str)
                if match:
                    return tuple(map(int, match.groups()))
            
            # За замовчуванням, якщо не вдалося розпізнати колір
            return (0, 0, 0)
        except Exception:
            return (0, 0, 0)  # За замовчуванням чорний
            
    def _calculate_contrast_ratio(self, color1, color2):
        """
        Розраховує відношення контрасту між двома кольорами за формулою WCAG.
        
        Args:
            color1 (tuple): Перший колір у форматі RGB
            color2 (tuple): Другий колір у форматі RGB
            
        Returns:
            float: Відношення контрасту
        """
        # Конвертація RGB у відносну яскравість
        def get_luminance(rgb):
            r, g, b = [x / 255 for x in rgb]
            r = r / 12.92 if r <= 0.03928 else ((r + 0.055) / 1.055) ** 2.4
            g = g / 12.92 if g <= 0.03928 else ((g + 0.055) / 1.055) ** 2.4
            b = b / 12.92 if b <= 0.03928 else ((b + 0.055) / 1.055) ** 2.4
            return 0.2126 * r + 0.7152 * g + 0.0722 * b
            
        l1 = get_luminance(color1)
        l2 = get_luminance(color2)
        
        # Розрахунок відношення контрасту
        lighter = max(l1, l2)
        darker = min(l1, l2)
        return (lighter + 0.05) / (darker + 0.05)

    def _analyze_cookies(self, cookies):
        """
        Аналізує безпеку cookie.
        
        Args:
            cookies: Об'єкт cookies з відповіді
            
        Returns:
            dict: Результати аналізу cookie
        """
        cookie_count = len(cookies)
        
        if cookie_count == 0:
            return {
                "count": 0,
                "secure": True,
                "httponly": True,
                "samesite": True
            }
        
        # Аналіз атрибутів cookie
        secure_count = 0
        httponly_count = 0
        samesite_count = 0
        
        for cookie in cookies:
            cookie_dict = {k.lower(): v for k, v in cookies[cookie].__dict__.items()}
            
            # Перевірка атрибутів безпеки
            if cookie_dict.get("secure"):
                secure_count += 1
                
            if cookie_dict.get("httponly"):
                httponly_count += 1
                
            # Перевірка атрибуту SameSite
            if "samesite" in cookie_dict and cookie_dict["samesite"] in ["lax", "strict"]:
                samesite_count += 1
        
        return {
            "count": cookie_count,
            "secure": secure_count == cookie_count,  # Всі cookies мають атрибут Secure
            "httponly": httponly_count == cookie_count,  # Всі cookies мають атрибут HttpOnly
            "samesite": samesite_count == cookie_count  # Всі cookies мають атрибут SameSite
        }