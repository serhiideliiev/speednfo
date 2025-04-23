#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Основний модуль Telegram бота для аналізу URL з Google PageSpeed Insights
"""

import logging
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
        
        # Перевірка правильності URL
        if not is_valid_url(url):
            await update.message.reply_text(BOT_MESSAGES["invalid_url"])
            return
        
        # Повідомлення про початок аналізу
        status_message = await update.message.reply_text(BOT_MESSAGES["analysis_start"])
        
        try:
            # Аналіз для мобільної версії
            mobile_results = self.analyzer.analyze(url, "mobile")
            if "error" in mobile_results:
                await status_message.edit_text(
                    BOT_MESSAGES["error"].format(error=mobile_results["error"])
                )
                return
                
            # Аналіз для десктопної версії
            desktop_results = self.analyzer.analyze(url, "desktop")
            if "error" in desktop_results:
                await status_message.edit_text(
                    BOT_MESSAGES["error"].format(error=desktop_results["error"])
                )
                return
                
            # Оновлення статусу
            await status_message.edit_text(BOT_MESSAGES["analysis_complete"])
            
            # Створення PDF зі звітом
            pdf_bytes = self.pdf_generator.generate_report(url, mobile_results, desktop_results)
            pdf_bytes.seek(0)
            
            # Підготовка назви файлу
            filename = generate_filename(url)
            
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
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обробник натискань на кнопки."""
        query = update.callback_query
        await query.answer()
        
        # Розбір даних з кнопки
        data = query.data.split("_")
        if len(data) < 3:
            await query.edit_message_text("❌ Помилка: неправильний формат даних кнопки")
            return
            
        action = data[0]
        device = data[1]
        url = "_".join(data[2:])  # На випадок, якщо в URL є символ "_"
        
        if action == "detail":
            await query.edit_message_text(f"🔍 Отримую детальний аналіз для {device}...")
            
            try:
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
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обробник помилок."""
        logger.error(f"Виникла помилка при обробці оновлення: {context.error}", exc_info=True)
        
        # Спроба надіслати повідомлення користувачу про помилку
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "❌ Сталася помилка при обробці вашого запиту. "
                "Будь ласка, спробуйте ще раз пізніше."
            )