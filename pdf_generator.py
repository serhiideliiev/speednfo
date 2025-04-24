#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Модуль для генерації PDF-звітів з результатами аналізу PageSpeed
"""

import io
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.units import cm
from reportlab.graphics.shapes import Drawing, String
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.legends import Legend

from config import FONT_PATH, PDF_AUTHOR, PDF_TITLE, PDF_SUBJECT, logger
from utils import get_score_status


class PDFReportGenerator:
    """
    Клас для генерації PDF-звітів з результатами аналізу PageSpeed.
    """
    
    def __init__(self, font_path=None):
        """
        Ініціалізує генератор PDF-звітів.
        
        Args:
            font_path (str, optional): Шлях до українського шрифту.
                                      За замовчуванням використовується з config.py
        """
        self.font_path = font_path or FONT_PATH
        self._register_fonts()
        self._init_styles()
        self._init_colors()
    
    def _register_fonts(self):
        """Реєструє українські шрифти для використання в PDF."""
        self.use_ukrainian_font = False
        
        # Реєстрація стандартного шрифту як запасного варіанту
        try:
            pdfmetrics.registerFont(TTFont("DefaultFont", "Helvetica"))
        except Exception:
            pass
        
        if self.font_path:
            try:
                pdfmetrics.registerFont(TTFont("Ukrainian", self.font_path))
                self.use_ukrainian_font = True
                logger.info(f"Шрифт успішно зареєстровано: {self.font_path}")
            except Exception as e:
                logger.error(f"Помилка при реєстрації шрифту: {e}", exc_info=True)
                logger.warning("Використовую стандартний шрифт замість українського")
        else:
            logger.warning("Шлях до шрифту не вказано. Використовую стандартний шрифт")
    
    def _init_styles(self):
        """Ініціалізує стилі для PDF-документу."""
        self.styles = getSampleStyleSheet()
        
        # Вибір шрифту в залежності від успішності реєстрації українського шрифту
        font_name = "Ukrainian" if self.use_ukrainian_font else "Helvetica"
        
        # Створення стилів
        self.title_style = ParagraphStyle(
            "UkrainianTitle",
            parent=self.styles["Title"],
            fontName=font_name,
            fontSize=18,
            spaceAfter=12
        )
        
        self.heading_style = ParagraphStyle(
            "UkrainianHeading",
            parent=self.styles["Heading1"],
            fontName=font_name,
            fontSize=16,
            spaceAfter=10
        )
        
        self.subheading_style = ParagraphStyle(
            "UkrainianSubheading",
            parent=self.styles["Heading2"],
            fontName=font_name,
            fontSize=14,
            spaceAfter=8
        )
        
        self.normal_style = ParagraphStyle(
            "UkrainianNormal",
            parent=self.styles["Normal"],
            fontName=font_name,
            fontSize=12,
            spaceAfter=6
        )
        
        self.small_style = ParagraphStyle(
            "UkrainianSmall",
            parent=self.styles["Normal"],
            fontName=font_name,
            fontSize=10,
            spaceAfter=4
        )
    
    def _init_colors(self):
        """Ініціалізує кольори для використання в звіті."""
        # Кольори для заголовків
        self.header_bg_color = colors.HexColor("#1a365d")  # Темно-синій
        self.header_text_color = colors.white
        
        # Кольори для рейтингів
        self.good_bg_color = colors.HexColor("#d4edda")  # Світло-зелений
        self.good_text_color = colors.HexColor("#155724")  # Темно-зелений
        
        self.average_bg_color = colors.HexColor("#fff3cd")  # Світло-жовтий
        self.average_text_color = colors.HexColor("#856404")  # Темно-жовтий
        
        self.poor_bg_color = colors.HexColor("#f8d7da")  # Світло-червоний
        self.poor_text_color = colors.HexColor("#721c24")  # Темно-червоний
        
        # Кольори для діаграми
        self.mobile_color = colors.HexColor("#3182ce")  # Синій для мобільного
        self.desktop_color = colors.HexColor("#38a169")  # Зелений для десктопу
    
    def generate_report(self, url, mobile_results, desktop_results):
        """
        Створює PDF-звіт на основі результатів аналізу.
        
        Args:
            url (str): Проаналізований URL
            mobile_results (dict): Результати аналізу для мобільних пристроїв
            desktop_results (dict): Результати аналізу для десктопів
            
        Returns:
            BytesIO: PDF-файл у форматі байтів
        """
        buffer = io.BytesIO()
        
        # Створення документа
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm,
            title=PDF_TITLE,
            author=PDF_AUTHOR,
            subject=PDF_SUBJECT
        )
        
        # Елементи документа
        elements = []
        
        # Додавання заголовка і базової інформації
        self._add_header_and_info(elements, url)
        
        # Додавання оцінок продуктивності
        self._add_performance_scores(elements, mobile_results, desktop_results, doc.width)
        
        # Додавання візуальної діаграми порівняння продуктивності
        self._add_performance_chart(elements, mobile_results, desktop_results, doc.width)
        
        # Додавання детальних метрик для мобільної версії
        if mobile_results and "metrics" in mobile_results:
            self._add_metrics_section(
                elements,
                "Метрики для мобільних пристроїв",
                mobile_results["metrics"],
                doc.width
            )
        
        # Додавання детальних метрик для десктопної версії
        if desktop_results and "metrics" in desktop_results:
            self._add_metrics_section(
                elements,
                "Метрики для комп'ютерів",
                desktop_results["metrics"],
                doc.width
            )
        
        # Додавання рекомендацій
        if mobile_results and desktop_results:
            self._add_recommendations_section(
                elements,
                mobile_results.get("recommendations", []),
                desktop_results.get("recommendations", [])
            )
        
        # Створення PDF
        doc.build(elements)
        buffer.seek(0)
        
        return buffer

    def _add_header_and_info(self, elements, url):
        """
        Додає заголовок та інформацію про аналізований сайт.
        
        Args:
            elements (list): Список елементів PDF
            url (str): Проаналізований URL
        """
        elements.append(Paragraph(PDF_TITLE, self.title_style))
        elements.append(Spacer(1, 0.5*cm))
        
        # Інформація про сайт
        elements.append(Paragraph(f"URL: {url}", self.normal_style))
        elements.append(
            Paragraph(
                f"Дата аналізу: {datetime.now().strftime('%d.%m.%Y %H:%M')}",
                self.normal_style
            )
        )
        elements.append(Spacer(1, 1*cm))
    
    def _add_performance_scores(self, elements, mobile_results, desktop_results, width):
        """
        Додає секцію з загальними оцінками продуктивності.
        
        Args:
            elements (list): Список елементів PDF
            mobile_results (dict): Результати для мобільних пристроїв
            desktop_results (dict): Результати для десктопу
            width (float): Ширина документа
        """
        elements.append(Paragraph("Загальні оцінки продуктивності", self.heading_style))
        elements.append(Spacer(1, 0.3*cm))
        
        # Отримання оцінок з результатів, з перевіркою на наявність даних
        mobile_score = mobile_results.get("score", 0) if mobile_results else 0
        desktop_score = desktop_results.get("score", 0) if desktop_results else 0
        
        # Таблиця оцінок
        data = [
            ["Пристрій", "Оцінка", "Статус"],
            ["Мобільний", f"{mobile_score}/100", get_score_status(mobile_score)],
            ["Десктоп", f"{desktop_score}/100", get_score_status(desktop_score)]
        ]
        
        # Створення та стилізація таблиці
        table = Table(data, colWidths=[width/3.0]*3)
        
        # Визначення стилю таблиці
        font_name = "Ukrainian" if self.use_ukrainian_font else "Helvetica"
        
        # Базові стилі таблиці
        table_style = [
            ("BACKGROUND", (0, 0), (-1, 0), self.header_bg_color),
            ("TEXTCOLOR", (0, 0), (-1, 0), self.header_text_color),
            ("ALIGN", (0, 0), (-1, 0), "CENTER"),
            ("ALIGN", (0, 1), (-1, -1), "CENTER"),
            ("FONTNAME", (0, 0), (-1, -1), font_name),
            ("FONTSIZE", (0, 0), (-1, 0), 14),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
            ("TOPPADDING", (0, 0), (-1, 0), 8),
            ("GRID", (0, 0), (-1, -1), 1, colors.black)
        ]
        
        # Додавання кольорового кодування оцінок
        for i, row in enumerate(data[1:], 1):
            score = int(row[1].split("/")[0])
            if score >= 90:
                bg_color = self.good_bg_color
                text_color = self.good_text_color
            elif score >= 50:
                bg_color = self.average_bg_color
                text_color = self.average_text_color
            else:
                bg_color = self.poor_bg_color
                text_color = self.poor_text_color
                
            table_style.append(("BACKGROUND", (1, i), (2, i), bg_color))
            table_style.append(("TEXTCOLOR", (1, i), (2, i), text_color))
        
        table.setStyle(TableStyle(table_style))
        elements.append(table)
        elements.append(Spacer(1, 1*cm))

    def _add_performance_chart(self, elements, mobile_results, desktop_results, width):
        """
        Додає візуальну діаграму порівняння продуктивності.
        
        Args:
            elements (list): Список елементів PDF
            mobile_results (dict): Результати для мобільних пристроїв
            desktop_results (dict): Результати для десктопу
            width (float): Ширина документа
        """
        elements.append(Paragraph("Порівняння продуктивності", self.heading_style))
        elements.append(Spacer(1, 0.5*cm))
        
        # Отримання оцінок з результатів, з перевіркою на наявність даних
        mobile_score = mobile_results.get("score", 0) if mobile_results else 0
        desktop_score = desktop_results.get("score", 0) if desktop_results else 0
        
        # Створення базової діаграми з більшою висотою
        drawing = Drawing(width, 250)
        
        # Створення та налаштування вертикальної діаграми
        chart = VerticalBarChart()
        chart.x = 50
        chart.y = 50
        chart.height = 150
        chart.width = width - 110
        
        # Дані для діаграми
        chart.data = [[mobile_score], [desktop_score]]
        
        # Кольори стовпців
        chart.bars[0].fillColor = self.mobile_color
        chart.bars[1].fillColor = self.desktop_color
        
        # Налаштування осі значень (Y)
        chart.valueAxis.valueMin = 0
        chart.valueAxis.valueMax = 100
        chart.valueAxis.valueStep = 20
        chart.valueAxis.labels.fontSize = 10
        chart.valueAxis.labels.fontName = "Helvetica"
        chart.valueAxis.strokeWidth = 1
        chart.valueAxis.gridStrokeWidth = 0.5
        chart.valueAxis.visibleGrid = True
        
        # Налаштування осі категорій (X)
        chart.categoryAxis.labels.boxAnchor = "n"
        chart.categoryAxis.labels.dx = 0
        chart.categoryAxis.labels.dy = -10
        chart.categoryAxis.labels.fontName = "Helvetica"
        chart.categoryAxis.labels.fontSize = 10
        chart.categoryAxis.categoryNames = [""]
        
        # Додавання підпису для осі Y
        y_label = String(15, 125, "Оцінка", fontSize=10, fontName="Helvetica")
        y_label.textAnchor = "middle"
        drawing.add(y_label)
        
        # Додавання легенди
        legend = Legend()
        legend.x = width - 100
        legend.y = 160
        legend.colorNamePairs = [
            (self.mobile_color, "Мобільний"), 
            (self.desktop_color, "Десктоп")
        ]
        legend.fontName = "Helvetica"
        legend.fontSize = 10
        legend.alignment = "right"
        legend.columnMaximum = 1
        legend.strokeWidth = 0
        
        # Додавання елементів до діаграми
        drawing.add(chart)
        drawing.add(legend)
        
        # Додавання діаграми до документа
        elements.append(drawing)
        elements.append(Spacer(1, 0.8*cm))

    def _add_metrics_section(self, elements, title, metrics, width):
        """
        Додає секцію з детальними метриками з кольоровим кодуванням.
        
        Args:
            elements (list): Список елементів PDF
            title (str): Заголовок секції
            metrics (dict): Метрики для відображення
            width (float): Ширина документа
        """
        if not metrics:
            logger.warning(f"Немає метрик для секції: {title}")
            return
            
        elements.append(Paragraph(title, self.heading_style))
        elements.append(Spacer(1, 0.3*cm))
        
        # Підготовка даних для таблиці
        metrics_data = [["Метрика", "Значення", "Оцінка"]]
        
        for metric_name, metric_data in metrics.items():
            metrics_data.append([
                metric_name, 
                metric_data.get("value", "N/A"), 
                metric_data.get("rating", "N/A")
            ])
        
        # Створення таблиці з метриками
        font_name = "Ukrainian" if self.use_ukrainian_font else "Helvetica"
        metrics_table = Table(metrics_data, colWidths=[width*0.5, width*0.25, width*0.25])
        
        # Базові стилі таблиці
        table_style = [
            ("BACKGROUND", (0, 0), (-1, 0), self.header_bg_color),
            ("TEXTCOLOR", (0, 0), (-1, 0), self.header_text_color),
            ("ALIGN", (0, 0), (-1, 0), "CENTER"),
            ("ALIGN", (0, 1), (-1, -1), "LEFT"),
            ("FONTNAME", (0, 0), (-1, -1), font_name),
            ("FONTSIZE", (0, 0), (-1, 0), 12),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
            ("TOPPADDING", (0, 0), (-1, 0), 8),
            ("GRID", (0, 0), (-1, -1), 1, colors.black),
        ]
        
        # Додавання кольорового кодування для оцінок
        for i, row in enumerate(metrics_data[1:], 1):
            rating = row[2].lower()
            if rating == "good":
                bg_color = self.good_bg_color
                text_color = self.good_text_color
            elif rating == "average":
                bg_color = self.average_bg_color
                text_color = self.average_text_color
            else:  # poor or other
                bg_color = self.poor_bg_color
                text_color = self.poor_text_color
                
            table_style.append(("BACKGROUND", (2, i), (2, i), bg_color))
            table_style.append(("TEXTCOLOR", (2, i), (2, i), text_color))
        
        metrics_table.setStyle(TableStyle(table_style))
        elements.append(metrics_table)
        elements.append(Spacer(1, 0.7*cm))
    
    def _add_recommendations_section(self, elements, mobile_recs, desktop_recs):
        """
        Додає секцію з категоризованими та пріоритизованими рекомендаціями.
        
        Args:
            elements (list): Список елементів PDF
            mobile_recs (list): Рекомендації для мобільних пристроїв
            desktop_recs (list): Рекомендації для десктопу
        """
        # Об'єднуємо унікальні рекомендації з обох аналізів
        all_recommendations = list(set(mobile_recs + desktop_recs))
        
        if not all_recommendations:
            return
            
        elements.append(Paragraph("Рекомендації щодо оптимізації", self.heading_style))
        elements.append(Spacer(1, 0.3*cm))
        
        # Додаємо короткий опис
        elements.append(Paragraph(
            "Нижче наведені рекомендації для покращення продуктивності сайту. "
            "Виконання цих рекомендацій може значно підвищити швидкість завантаження.",
            self.normal_style
        ))
        elements.append(Spacer(1, 0.5*cm))
        
        # Ключові слова для визначення категорій та пріоритетів
        high_priority_keywords = [
            'великого контенту', 'LCP', 'FCP', 'Time to Interactive', 
            'блокують відображення', 'First Contentful Paint', 
            'Largest Contentful Paint', 'критично'
        ]
        
        # Категоризація та пріоритизація рекомендацій
        image_recs_high = []
        image_recs_normal = []
        code_recs_high = []
        code_recs_normal = []
        perf_recs_high = []
        perf_recs_normal = []
        other_recs = []
        
        for rec in all_recommendations:
            rec_lower = rec.lower()
            is_high_priority = any(kw.lower() in rec_lower for kw in high_priority_keywords)
            
            if any(kw in rec_lower for kw in ['зображен', 'картин', 'формат', 'picture']):
                if is_high_priority:
                    image_recs_high.append(rec)
                else:
                    image_recs_normal.append(rec)
            elif any(kw in rec_lower for kw in ['css', 'javascript', 'js', 'код', 'script']):
                if is_high_priority:
                    code_recs_high.append(rec)
                else:
                    code_recs_normal.append(rec)
            elif any(kw in rec_lower for kw in ['швидкість', 'кеш', 'час', 'завантаження']):
                if is_high_priority:
                    perf_recs_high.append(rec)
                else:
                    perf_recs_normal.append(rec)
            else:
                other_recs.append(rec)
        
        # Додавання рекомендацій по категоріях
        self._add_recommendation_category(elements, "Оптимізація зображень:", image_recs_high, image_recs_normal)
        self._add_recommendation_category(elements, "Оптимізація коду:", code_recs_high, code_recs_normal)
        self._add_recommendation_category(elements, "Загальна продуктивність:", perf_recs_high, perf_recs_normal)
        
        # Додавання інших рекомендацій
        if other_recs:
            elements.append(Paragraph("Інші рекомендації:", self.subheading_style))
            for rec in other_recs:
                elements.append(Paragraph(f"• {rec}", self.normal_style))
                
        # Додавання пояснення пріоритетів
        elements.append(Spacer(1, 0.7*cm))
        elements.append(Paragraph("Пріоритети рекомендацій:", self.subheading_style))
        elements.append(Paragraph("🔴 Високий пріоритет - критичні проблеми, що значно впливають на швидкість", self.small_style))
        elements.append(Paragraph("🟠 Середній пріоритет - важливі оптимізації з помірним впливом", self.small_style))
        elements.append(Paragraph("• Низький пріоритет - незначні покращення", self.small_style))
    
    def _add_recommendation_category(self, elements, title, high_priority_items, normal_priority_items):
        """
        Додає категорію рекомендацій з відповідними пріоритетами.
        
        Args:
            elements (list): Список елементів PDF
            title (str): Заголовок категорії
            high_priority_items (list): Рекомендації з високим пріоритетом
            normal_priority_items (list): Рекомендації з середнім пріоритетом
        """
        if not high_priority_items and not normal_priority_items:
            return
            
        elements.append(Paragraph(title, self.subheading_style))
        
        # Додавання рекомендацій з високим пріоритетом
        for rec in high_priority_items:
            elements.append(Paragraph(f"🔴 {rec}", self.normal_style))
            
        # Додавання рекомендацій з середнім пріоритетом
        for rec in normal_priority_items:
            elements.append(Paragraph(f"🟠 {rec}", self.normal_style))
            
        elements.append(Spacer(1, 0.3*cm))