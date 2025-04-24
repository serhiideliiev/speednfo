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
from reportlab.graphics.shapes import Drawing, String  # Import String
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
    
    def _register_fonts(self):
        """Реєструє українські шрифти для використання в PDF."""
        self.use_ukrainian_font = False
        
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
        
        self.normal_style = ParagraphStyle(
            "UkrainianNormal",
            parent=self.styles["Normal"],
            fontName=font_name,
            fontSize=12,
            spaceAfter=6
        )
    
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

        # Додавання графіка порівняння продуктивності
        self._add_performance_chart(elements, mobile_results, desktop_results, doc.width)
        
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
        table_style = TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("FONTNAME", (0, 0), (-1, 0), font_name),
            ("FONTNAME", (0, 1), (-1, -1), font_name),
            ("FONTSIZE", (0, 0), (-1, 0), 14),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
            ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
            ("GRID", (0, 0), (-1, -1), 1, colors.black)
        ])
        
        table.setStyle(table_style)
        elements.append(table)
        elements.append(Spacer(1, 1*cm))

    def _add_performance_chart(self, elements, mobile_results, desktop_results, width):
        """
        Adds a visual chart comparing performance metrics.
        """
        # Create a proper drawing with defined dimensions
        drawing = Drawing(width, 250)  # Increase height for better visibility
        
        # Create the bar chart
        chart = VerticalBarChart()
        chart.x = 50
        chart.y = 50
        chart.height = 150  # Increase height
        chart.width = width - 120  # Adjust width to leave room for labels
        
        # Set up data - make sure we're handling potential None values
        mobile_score = mobile_results.get('score', 0) if mobile_results else 0
        desktop_score = desktop_results.get('score', 0) if desktop_results else 0
        data = [[mobile_score], [desktop_score]]
        chart.data = data
        
        # Improve visual appearance with better colors and spacing
        chart.bars[0].fillColor = colors.blue
        chart.bars[1].fillColor = colors.green
        chart.valueAxis.valueMin = 0
        chart.valueAxis.valueMax = 100
        chart.valueAxis.valueStep = 20  # Use fewer steps for cleaner look
        
        # Add proper labels
        chart.categoryAxis.labels.boxAnchor = 'n'
        chart.categoryAxis.labels.dy = -10
        chart.categoryAxis.categoryNames = ['Показники продуктивності']
        
        # Add axis labels
        # Determine font name based on availability
        font_name = "Ukrainian" if self.use_ukrainian_font else "Helvetica"
        y_axis_label = String(10, 85, 'Оцінка (0-100)', fontSize=10, fontName=font_name)
        y_axis_label.textAnchor = 'middle'
        y_axis_label.angle = 90
        drawing.add(y_axis_label)
        
        # Add a clear legend with better positioning
        legend = Legend()
        legend.alignment = 'right'
        legend.x = width - 100
        legend.y = 180
        legend.fontName = font_name
        legend.columnMaximum = 1
        legend.colorNamePairs = [(colors.blue, 'Мобільний'), (colors.green, 'Десктоп')]
        
        drawing.add(chart)
        drawing.add(legend)
        
        elements.append(Paragraph("Порівняння продуктивності", self.heading_style))
        elements.append(drawing)
        elements.append(Spacer(1, 0.7*cm))  # Increase spacing after chart

    def _add_metrics_section(self, elements, title, metrics, width):
        """
        Adds a section with detailed metrics including color coding for ratings.
        """
        if not metrics:
            logger.warning(f"Немає метрик для секції: {title}")
            return
            
        elements.append(Paragraph(title, self.heading_style))
        elements.append(Spacer(1, 0.3*cm))
        
        # Prepare table data
        metrics_data = [["Метрика", "Значення", "Оцінка"]]
        
        for metric_name, metric_data in metrics.items():
            metrics_data.append([
                metric_name, 
                metric_data.get("value", "N/A"), 
                metric_data.get("rating", "N/A")
            ])
        
        # Create table with metrics
        font_name = "Ukrainian" if self.use_ukrainian_font else "Helvetica"
        metrics_table = Table(metrics_data, colWidths=[width*0.5, width*0.25, width*0.25])
        
        # Base styles
        table_style = [
            ("BACKGROUND", (0, 0), (-1, 0), colors.darkblue),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("FONTNAME", (0, 0), (-1, 0), font_name),
            ("FONTNAME", (0, 1), (-1, -1), font_name),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 1, colors.black),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
            ("TOPPADDING", (0, 0), (-1, 0), 8),
        ]
        
        # Add color coding for ratings
        for i, row in enumerate(metrics_data[1:], 1):
            rating = row[2]
            if rating == "good":
                table_style.append(("BACKGROUND", (2, i), (2, i), colors.lightgreen))
                table_style.append(("TEXTCOLOR", (2, i), (2, i), colors.darkgreen))
            elif rating == "average":
                table_style.append(("BACKGROUND", (2, i), (2, i), colors.lightyellow))
                table_style.append(("TEXTCOLOR", (2, i), (2, i), colors.brown))
            elif rating == "poor":
                table_style.append(("BACKGROUND", (2, i), (2, i), colors.mistyrose))
                table_style.append(("TEXTCOLOR", (2, i), (2, i), colors.darkred))
        
        metrics_table.setStyle(TableStyle(table_style))
        elements.append(metrics_table)
        elements.append(Spacer(1, 0.7*cm))

    def _add_metrics_heatmap(self, elements, metrics, width):
        """
        Додає теплову карту для метрик.
        
        Args:
            elements (list): Список елементів PDF
            metrics (dict): Метрики для відображення
            width (float): Ширина документа
        """
        if not metrics:
            return
            
        data = [["Метрика", "Значення", "Статус"]]
        
        for name, metric_data in metrics.items():
            rating = metric_data.get("rating", "N/A")
            data.append([name, metric_data.get("value", "N/A"), rating])
        
        font_name = "Ukrainian" if self.use_ukrainian_font else "Helvetica"
        table = Table(data, colWidths=[width*0.5, width*0.25, width*0.25])
        
        # Базові стилі
        style = [
            ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("FONTNAME", (0, 0), (-1, -1), font_name),
            ("GRID", (0, 0), (-1, -1), 1, colors.black),
        ]
        
        # Додаємо кольори для кожного рядка на основі рейтингу
        for i, row in enumerate(data[1:], 1):
            rating = row[2]
            color = colors.lightgreen if rating == "good" else \
                    colors.lightyellow if rating == "average" else colors.lightcoral
            style.append(("BACKGROUND", (2, i), (2, i), color))
        
        table.setStyle(TableStyle(style))
        elements.append(table)
        elements.append(Spacer(1, 0.5*cm))
    
    def _add_recommendations_section(self, elements, mobile_recs, desktop_recs):
        """
        Adds a section with optimization recommendations with categorization.
        """
        all_recommendations = set(mobile_recs + desktop_recs)
        
        if not all_recommendations:
            return
            
        elements.append(Paragraph("Рекомендації щодо оптимізації", self.heading_style))
        elements.append(Spacer(1, 0.3*cm))
        
        # Add a subheading explaining recommendations
        elements.append(Paragraph(
            "Нижче наведені рекомендації для покращення продуктивності сайту. "
            "Виконання цих рекомендацій може значно підвищити швидкість завантаження.", 
            self.normal_style
        ))
        elements.append(Spacer(1, 0.5*cm))
        
        # Categorize recommendations (simple approach)
        performance_recs = []
        image_recs = []
        code_recs = []
        other_recs = []
        
        for rec in all_recommendations:
            if any(kw in rec.lower() for kw in ['зображення', 'картинки', 'формат']):
                image_recs.append(rec)
            elif any(kw in rec.lower() for kw in ['css', 'javascript', 'js', 'код']):
                code_recs.append(rec)
            elif any(kw in rec.lower() for kw in ['швидкість', 'кеш', 'час', 'завантаження']):
                performance_recs.append(rec)
            else:
                other_recs.append(rec)
        
        # Add categorized recommendations
        if image_recs:
            elements.append(Paragraph("Оптимізація зображень:", self.heading_style))
            for rec in image_recs:
                elements.append(Paragraph(f"• {rec}", self.normal_style))
            elements.append(Spacer(1, 0.3*cm))
        
        if code_recs:
            elements.append(Paragraph("Оптимізація коду:", self.heading_style))
            for rec in code_recs:
                elements.append(Paragraph(f"• {rec}", self.normal_style))
            elements.append(Spacer(1, 0.3*cm))
        
        if performance_recs:
            elements.append(Paragraph("Загальна продуктивність:", self.heading_style))
            for rec in performance_recs:
                elements.append(Paragraph(f"• {rec}", self.normal_style))
            elements.append(Spacer(1, 0.3*cm))
        
        if other_recs:
            elements.append(Paragraph("Інші рекомендації:", self.heading_style))
            for rec in other_recs:
                elements.append(Paragraph(f"• {rec}", self.normal_style))

    def _add_recommendations_with_priority(self, elements, recommendations, priorities=None):
        """
        Adds recommendations with priority indicators.
        """
        if not recommendations:
            return
            
        elements.append(Paragraph("Рекомендації щодо оптимізації", self.heading_style))
        
        # Add a brief explanation
        elements.append(Paragraph(
            "Нижче наведені рекомендації для покращення продуктивності сайту, "
            "відсортовані за пріоритетом.", 
            self.normal_style
        ))
        elements.append(Spacer(1, 0.5*cm))
        
        # Add priority indicators
        critical_count = priorities.get("critical", 0) if priorities else 0
        important_count = priorities.get("important", 0) if priorities else 0
        
        # Add each recommendation with an appropriate icon
        for i, rec in enumerate(recommendations):
            if i < critical_count:
                indicator = "🔴"  # Critical
            elif i < critical_count + important_count:
                indicator = "🟠"  # Important
            else:
                indicator = "🟡"  # Other
                
            elements.append(Paragraph(f"{indicator} {rec}", self.normal_style))
            
        elements.append(Spacer(1, 0.5*cm))