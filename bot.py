#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Основний модуль Telegram бота для аналізу URL з Google PageSpeed Insights
"""

import logging
import json
from datetime import datetime

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    filters, ContextTypes
)

from config import TOKEN, BOT_MESSAGES, logger
from pagespeed_analyzer import PageSpeedAnalyzer
from pdf_generator import PDFReportGenerator
from utils import is_valid_url, generate_filename


class PageSpeedBot:
    """
    Клас для обробки взаємодій з користувачем через Telegram.
    """
    
    def __init__(self, token=None):
        """
        Ініціалізує Telegram бота.
        
        Args:
            token (str, optional): Telegram Bot API токен.
                                  За замовчуванням використовується з config.py
        """
        self.token = token or TOKEN
        self.analyzer = PageSpeedAnalyzer()
        self.pdf_generator = PDFReportGenerator()
    
    def run(self):
        """Запускає бота."""
        # Створення додатку
        application = Application.builder().token(self.token).build()

        # Додавання обробників команд
        application.add_handler(CommandHandler("start", self.start))
        application.add_handler(CommandHandler("help", self.help_command))
        application.add_handler(CommandHandler("about", self.about_command))
        application.add_handler(CommandHandler("full", self.full_analysis))
        
        # Додавання обробника повідомлень
        application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.analyze_url)
        )
        
        # Додавання обробника кнопок
        application.add_handler(CallbackQueryHandler(self.button_callback))
        
        # Додавання обробника помилок
        application.add_error_handler(self.error_handler)

        # Запуск бота
        logger.info("Бот запущено")
        application.run_polling()
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обробник команди /start."""
        user = update.effective_user
        message = BOT_MESSAGES["start"].format(user_name=user.first_name)
        await update.message.reply_text(message)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обробник команди /help."""
        await update.message.reply_text(BOT_MESSAGES["help"], parse_mode="Markdown")
    
    async def about_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обробник команди /about."""
        await update.message.reply_text(BOT_MESSAGES["about"], parse_mode="Markdown")
    
    async def analyze_url(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обробник повідомлень з URL."""
        url = update.message.text.strip()
        logger.debug(f"Received URL for analysis: {url}")
        
        # Перевірка правильності URL
        if not is_valid_url(url):
            await update.message.reply_text(BOT_MESSAGES["invalid_url"])
            return
        
        # Повідомлення про початок аналізу
        status_message = await update.message.reply_text(BOT_MESSAGES["analysis_start"])
        
        try:
            logger.debug("Starting mobile analysis...")
            # Аналіз для мобільної версії
            mobile_results = self.analyzer.analyze(url, "mobile")
            logger.debug(f"Mobile analysis results: {mobile_results}")
            if "error" in mobile_results:
                await status_message.edit_text(
                    BOT_MESSAGES["error"].format(error=mobile_results["error"])
                )
                return
                
            logger.debug("Starting desktop analysis...")
            # Аналіз для десктопної версії
            desktop_results = self.analyzer.analyze(url, "desktop")
            logger.debug(f"Desktop analysis results: {desktop_results}")
            if "error" in desktop_results:
                await status_message.edit_text(
                    BOT_MESSAGES["error"].format(error=desktop_results["error"])
                )
                return
                
            # Оновлення статусу
            await status_message.edit_text(BOT_MESSAGES["analysis_complete"])
            
            logger.debug("Generating PDF report...")
            # Створення PDF зі звітом
            pdf_bytes = self.pdf_generator.generate_report(url, mobile_results, desktop_results)
            logger.debug(f"PDF generated, size: {pdf_bytes.getbuffer().nbytes} bytes")
            pdf_bytes.seek(0)
            
            # Підготовка назви файлу
            filename = generate_filename(url)
            logger.debug(f"Sending PDF to user with filename: {filename}")
            
            # Відправка PDF файлу
            await update.message.reply_document(
                document=pdf_bytes,
                filename=filename,
                caption=BOT_MESSAGES["report_caption"].format(
                    url=url,
                    mobile_score=mobile_results['score'],
                    desktop_score=desktop_results['score']
                )
            )
            logger.debug("PDF sent to user successfully.")
            
            # Видалення статусного повідомлення
            await status_message.delete()
            
            # Відправка кнопок для детального аналізу
            keyboard = [
                [
                    InlineKeyboardButton("📱 Детальний аналіз для мобільних", 
                                        callback_data=f"detail_mobile_{url}"),
                    InlineKeyboardButton("🖥️ Детальний аналіз для десктопу", 
                                        callback_data=f"detail_desktop_{url}")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                BOT_MESSAGES["detail_options"],
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"Помилка при аналізі URL: {e}", exc_info=True)
            await status_message.edit_text(
                BOT_MESSAGES["error"].format(error=str(e))
            )

    async def full_analysis(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Виконує повний комплексний аналіз URL."""
        args = context.args
        
        if not args:
            await update.message.reply_text(
                "Будь ласка, надайте URL для аналізу після команди.\n"
                "Наприклад: /full https://example.com"
            )
            return
        
        url = args[0]
        
        # Перевірка правильності URL
        if not is_valid_url(url):
            await update.message.reply_text(BOT_MESSAGES["invalid_url"])
            return
        
        # Повідомлення про початок аналізу
        status_message = await update.message.reply_text(
            "🔍 Починаю комплексний аналіз URL...\n"
            "Це може зайняти кілька хвилин. Будь ласка, зачекайте."
        )
        
        try:
            # Виконання повного аналізу
            results = self.analyzer.analyze_with_all_metrics(url)
            
            # Перевірка на наявність помилок
            if "error" in results:
                await status_message.edit_text(
                    BOT_MESSAGES["error"].format(error=results["error"])
                )
                return
            
            # Оновлення статусу
            await status_message.edit_text("📊 Комплексний аналіз завершено. Генерую PDF-звіт...")
            
            # Розрахунок оцінок
            mobile_score = results['pagespeed'].get('mobile', {}).get('score', 0)
            desktop_score = results['pagespeed'].get('desktop', {}).get('score', 0)
            
            # Спрощені оцінки для SEO, доступності та безпеки
            seo_score = 100 if not results['seo'].get('recommendations') else 70
            accessibility_score = 100 if not results['accessibility'].get('recommendations') else 70
            security_score = 100 if not results['security'].get('recommendations') else 70
            
            # Створення PDF зі звітом
            # Використовуємо існуючу функцію для простоти, але в реальному проекті 
            # варто створити окрему функцію для комплексного звіту
            pdf_bytes = self.pdf_generator.generate_report(
                url, 
                results['pagespeed'].get('mobile', {}), 
                results['pagespeed'].get('desktop', {})
            )
            pdf_bytes.seek(0)
            
            # Підготовка назви файлу для повного аналізу
            filename = generate_filename(url, prefix="full_analysis")
            
            # Відправка PDF файлу
            await update.message.reply_document(
                document=pdf_bytes,
                filename=filename,
                caption=BOT_MESSAGES["full_analysis_complete"].format(
                    url=url,
                    mobile_score=mobile_score,
                    desktop_score=desktop_score,
                    seo_score=seo_score,
                    accessibility_score=accessibility_score,
                    security_score=security_score
                )
            )
            
            # Видалення статусного повідомлення
            await status_message.delete()
            
            # Додаткове повідомлення з рекомендаціями
            recommendations_msg = "📌 **Основні рекомендації:**\n\n"
            
            # Додаємо рекомендації з різних аналізів
            if 'recommendations' in results['pagespeed'].get('mobile', {}):
                mobile_recs = results['pagespeed']['mobile']['recommendations'][:3]  # Обмежуємо до 3
                if mobile_recs:
                    recommendations_msg += "📱 **Мобільна версія:**\n"
                    for rec in mobile_recs:
                        recommendations_msg += f"• {rec}\n"
                    recommendations_msg += "\n"
            
            if 'recommendations' in results.get('seo', {}):
                seo_recs = results['seo']['recommendations'][:3]  # Обмежуємо до 3
                if seo_recs:
                    recommendations_msg += "🔍 **SEO:**\n"
                    for rec in seo_recs:
                        recommendations_msg += f"• {rec}\n"
                    recommendations_msg += "\n"
            
            if 'recommendations' in results.get('security', {}):
                security_recs = results['security']['recommendations'][:3]  # Обмежуємо до 3
                if security_recs:
                    recommendations_msg += "🔒 **Безпека:**\n"
                    for rec in security_recs:
                        recommendations_msg += f"• {rec}\n"
            
            # Відправляємо рекомендації
            await update.message.reply_text(recommendations_msg, parse_mode="Markdown")
            
        except Exception as e:
            logger.error(f"Помилка при комплексному аналізі: {e}", exc_info=True)
            await status_message.edit_text(
                BOT_MESSAGES["error"].format(error=str(e))
            )
        
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обробник натискань на кнопки."""
        query = update.callback_query
        await query.answer()
        
        # Розбір даних з кнопки
        callback_data = query.data
        
        # Перевірка формату callback_data
        if not callback_data or "_" not in callback_data:
            await query.edit_message_text("❌ Помилка: неправильний формат даних кнопки")
            return
            
        # Безпечний парсинг callback_data
        parts = callback_data.split("_", 2)  # Розділяємо тільки на перші 2 підкреслення
        if len(parts) < 3:
            await query.edit_message_text("❌ Помилка: неправильний формат даних кнопки")
            return
            
        action = parts[0]
        device = parts[1]
        url = parts[2]  # Все після другого підкреслення вважаємо URL
        
        if action == "detail":
            # Валідація пристрою
            if device not in ["mobile", "desktop"]:
                await query.edit_message_text("❌ Помилка: неправильний тип пристрою")
                return
                
            # Повідомлення про початок аналізу
            await query.edit_message_text(f"🔍 Отримую детальний аналіз для {device}...")
            
            try:
                # Перевірка правильності URL
                if not is_valid_url(url):
                    await query.edit_message_text(BOT_MESSAGES["invalid_url"])
                    return
                    
                # Отримання результатів аналізу
                results = self.analyzer.analyze(url, device)
                if "error" in results:
                    await query.edit_message_text(f"❌ Помилка: {results['error']}")
                    return
                    
                # Форматування детального звіту
                device_name = "мобільних пристроїв" if device == "mobile" else "комп'ютерів"
                message = f"📊 *Детальний аналіз для {device_name}*\nURL: {url}\n\n"
                
                # Основна оцінка
                message += f"*Загальна оцінка:* {results['score']}/100\n\n"
                
                # Основні метрики
                message += "*Основні метрики:*\n"
                for metric_name, metric_data in results['metrics'].items():
                    emoji = "✅" if metric_data['rating'] == "good" else "⚠️" if metric_data['rating'] == "average" else "❌"
                    message += f"{emoji} {metric_name}: {metric_data['value']} ({metric_data['rating']})\n"
                
                # Рекомендації
                if results['recommendations']:
                    message += "\n*Рекомендації щодо оптимізації:*\n"
                    for rec in results['recommendations']:
                        message += f"• {rec}\n"
                
                await query.edit_message_text(message, parse_mode="Markdown")
                
            except Exception as e:
                logger.error(f"Помилка при отриманні детального аналізу: {e}", exc_info=True)
                await query.edit_message_text(
                    BOT_MESSAGES["error"].format(error=str(e))
                )
        else:
            await query.edit_message_text("❌ Непідтримувана дія")
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обробник помилок."""
        logger.error(f"Виникла помилка при обробці оновлення: {context.error}", exc_info=True)
        
        # Спроба надіслати повідомлення користувачу про помилку
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "❌ Сталася помилка при обробці вашого запиту. "
                "Будь ласка, спробуйте ще раз пізніше."
            )