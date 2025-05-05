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
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

from config import FONT_PATH, PDF_AUTHOR, PDF_TITLE, PDF_SUBJECT, logger
from utils import get_score_status
from pagespeed_analyzer import PRIORITIZATION_TERMS_UK, IMPACT_THRESHOLDS_MS, SCORE_MAPPING


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
            rightMargin=1.5*cm,
            leftMargin=1.5*cm,
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
        
        # Додавання пріоритезованих рекомендацій
        recommendations_data = mobile_results.get("prioritized_recommendations") if mobile_results else None
        if not recommendations_data and desktop_results:
            recommendations_data = desktop_results.get("prioritized_recommendations")

        if recommendations_data and recommendations_data.get("categories"):
            self._add_prioritized_recommendations_section(elements, recommendations_data, doc.width)
        else:
            logger.warning(f"Не знайдено даних пріоритезованих рекомендацій для URL: {url}")
            elements.append(Paragraph("Рекомендації щодо оптимізації відсутні або не вдалося їх отримати.", self.normal_style))
        
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
    
    def _add_prioritized_recommendations_section(self, elements, recommendations_data, width):
        """
        Додає секцію з пріоритезованими та категоризованими рекомендаціями.

        Args:
            elements (list): Список елементів PDF.
            recommendations_data (dict): Структурований словник з рекомендаціями.
            width (float): Ширина документа.
        """
        elements.append(Paragraph("Пріоритезовані Рекомендації", self.heading_style))
        elements.append(Spacer(1, 0.3*cm))

        elements.append(Paragraph(
            "Нижче наведено список рекомендацій, відсортованих за пріоритетом (найвищий спочатку) та згрупованих за категоріями. "
            "Пріоритет враховує потенційний вплив на швидкість та орієнтовну складність впровадження.",
            self.normal_style
        ))
        elements.append(Spacer(1, 0.5*cm))

        # Add summary table
        summary = recommendations_data.get("summary", {})
        if summary:
            self._add_recommendations_summary(elements, summary, width)

        # Iterate through categories and their recommendations
        categories = recommendations_data.get("categories", {})
        sorted_categories = sorted(categories.items())

        for category_name_uk, recs_in_category in sorted_categories:
            if not recs_in_category:
                continue

            elements.append(Paragraph(category_name_uk, self.subheading_style))
            elements.append(Spacer(1, 0.2*cm))

            # Prepare data for the table within this category
            table_data = [[
                Paragraph("Рекомендація", self.small_style),
                Paragraph(PRIORITIZATION_TERMS_UK["impact_label"], self.small_style),
                Paragraph(PRIORITIZATION_TERMS_UK["difficulty_label"], self.small_style),
                Paragraph(PRIORITIZATION_TERMS_UK["savings_label"], self.small_style)
            ]]

            font_name = "Ukrainian" if self.use_ukrainian_font else "Helvetica"

            for rec in recs_in_category:
                savings_text = f"{rec['potential_savings_ms']} мс" if rec['potential_savings_ms'] is not None else "-"
                title_paragraph = Paragraph(rec['title'], self.small_style)

                table_data.append([
                    title_paragraph,
                    Paragraph(rec['impact_level_uk'], self.small_style),
                    Paragraph(rec['difficulty_level_uk'], self.small_style),
                    Paragraph(savings_text, self.small_style)
                ])

            col_widths = [width * 0.55, width * 0.15, width * 0.15, width * 0.15]
            category_table = Table(table_data, colWidths=col_widths)

            style = TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), self.header_bg_color),
                ('TEXTCOLOR', (0, 0), (-1, 0), self.header_text_color),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), font_name),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
                ('TOPPADDING', (0, 0), (-1, 0), 4),

                ('FONTNAME', (0, 1), (-1, -1), font_name),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
                ('ALIGN', (0, 1), (0, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),

                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('BOX', (0, 0), (-1, -1), 1, colors.black),
            ])

            for i, rec in enumerate(recs_in_category, 1):
                if rec['impact_level'] == 'high':
                    style.add('BACKGROUND', (1, i), (1, i), self.poor_bg_color)
                    style.add('TEXTCOLOR', (1, i), (1, i), self.poor_text_color)
                elif rec['impact_level'] == 'medium':
                    style.add('BACKGROUND', (1, i), (1, i), self.average_bg_color)
                    style.add('TEXTCOLOR', (1, i), (1, i), self.average_text_color)
                else:
                    style.add('BACKGROUND', (1, i), (1, i), self.good_bg_color)
                    style.add('TEXTCOLOR', (1, i), (1, i), self.good_text_color)

                if rec['difficulty_level'] == 'hard':
                    style.add('BACKGROUND', (2, i), (2, i), self.poor_bg_color)
                    style.add('TEXTCOLOR', (2, i), (2, i), self.poor_text_color)
                elif rec['difficulty_level'] == 'medium':
                    style.add('BACKGROUND', (2, i), (2, i), self.average_bg_color)
                    style.add('TEXTCOLOR', (2, i), (2, i), self.average_text_color)
                else:
                    style.add('BACKGROUND', (2, i), (2, i), self.good_bg_color)
                    style.add('TEXTCOLOR', (2, i), (2, i), self.good_text_color)

            category_table.setStyle(style)
            elements.append(category_table)
            elements.append(Spacer(1, 0.5*cm))

    def _add_recommendations_summary(self, elements, summary, width):
        """Adds a small summary table for recommendations."""
        elements.append(Paragraph("Загальна статистика рекомендацій:", self.subheading_style))
        elements.append(Spacer(1, 0.2*cm))

        impact_h = summary.get("impact_counts", {}).get("high", 0)
        impact_m = summary.get("impact_counts", {}).get("medium", 0)
        impact_l = summary.get("impact_counts", {}).get("low", 0)
        diff_e = summary.get("difficulty_counts", {}).get("easy", 0)
        diff_m = summary.get("difficulty_counts", {}).get("medium", 0)
        diff_h = summary.get("difficulty_counts", {}).get("hard", 0)
        total = summary.get("total", 0)

        data = [
            ["Критерій", "Кількість"],
            [f"{PRIORITIZATION_TERMS_UK['impact_label']} ({PRIORITIZATION_TERMS_UK['impact']['high']})", str(impact_h)],
            [f"{PRIORITIZATION_TERMS_UK['impact_label']} ({PRIORITIZATION_TERMS_UK['impact']['medium']})", str(impact_m)],
            [f"{PRIORITIZATION_TERMS_UK['impact_label']} ({PRIORITIZATION_TERMS_UK['impact']['low']})", str(impact_l)],
            ["-", "-"],
            [f"{PRIORITIZATION_TERMS_UK['difficulty_label']} ({PRIORITIZATION_TERMS_UK['difficulty']['easy']})", str(diff_e)],
            [f"{PRIORITIZATION_TERMS_UK['difficulty_label']} ({PRIORITIZATION_TERMS_UK['difficulty']['medium']})", str(diff_m)],
            [f"{PRIORITIZATION_TERMS_UK['difficulty_label']} ({PRIORITIZATION_TERMS_UK['difficulty']['hard']})", str(diff_h)],
            ["-", "-"],
            ["Всього рекомендацій", str(total)]
        ]

        font_name = "Ukrainian" if self.use_ukrainian_font else "Helvetica"
        bold_font_name = font_name

        summary_table = Table(data, colWidths=[width * 0.7, width * 0.3])

        style = TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), font_name),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('FONTNAME', (0, 0), (-1, 0), bold_font_name),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('LINEABOVE', (0, 4), (-1, 4), 0.5, colors.white),
            ('LINEBELOW', (0, 4), (-1, 4), 0.5, colors.white),
            ('LINEABOVE', (0, 8), (-1, 8), 0.5, colors.white),
            ('LINEBELOW', (0, 8), (-1, 8), 0.5, colors.white),
            ('TEXTCOLOR', (0, 4), (-1, 4), colors.white),
            ('TEXTCOLOR', (0, 8), (-1, 8), colors.white),
            ('FONTNAME', (0, 9), (1, 9), bold_font_name),
        ])
        summary_table.setStyle(style)

        elements.append(summary_table)
        elements.append(Spacer(1, 0.7*cm))