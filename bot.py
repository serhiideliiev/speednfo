#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Основний модуль Telegram бота для аналізу URL з Google PageSpeed Insights
"""

import logging
import json
from datetime import datetime, timedelta
import uuid

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    filters, ContextTypes, ConversationHandler
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.memory import MemoryJobStore

from config import TOKEN, BOT_MESSAGES, logger
from pagespeed_analyzer import PageSpeedAnalyzer
from pdf_generator import PDFReportGenerator
from utils import is_valid_url, generate_filename

# Define states for ConversationHandler
ASK_URL, ASK_FREQUENCY = range(2)

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
        # Initialize scheduler
        self.scheduler = AsyncIOScheduler(jobstores={'default': MemoryJobStore()})
        # Dictionary to store job details {job_id: {'chat_id': ..., 'url': ..., 'frequency': ...}}
        self.scheduled_jobs = {} 
        self.application = None # To store the application instance
    
    async def scheduled_analysis_job(self, chat_id: int, url: str, application: Application):
        """
        Функція, що виконується за розкладом для аналізу URL.
        Надсилає звіт користувачу.
        """
        logger.info(f"Running scheduled job for chat_id {chat_id}, url: {url}")
        try:
            # Аналіз для мобільної та десктопної версій
            mobile_results = self.analyzer.analyze(url, "mobile")
            if "error" in mobile_results:
                await application.bot.send_message(chat_id, BOT_MESSAGES["scheduled_error"].format(url=url, error=mobile_results["error"]))
                return

            desktop_results = self.analyzer.analyze(url, "desktop")
            if "error" in desktop_results:
                await application.bot.send_message(chat_id, BOT_MESSAGES["scheduled_error"].format(url=url, error=desktop_results["error"]))
                return

            # Створення PDF зі звітом
            pdf_bytes = self.pdf_generator.generate_report(url, mobile_results, desktop_results)
            pdf_bytes.seek(0)
            filename = generate_filename(url, prefix="scheduled")

            # Відправка PDF файлу
            await application.bot.send_document(
                chat_id=chat_id,
                document=pdf_bytes,
                filename=filename,
                caption=BOT_MESSAGES["report_caption"].format(
                    url=url,
                    mobile_score=mobile_results.get('score', 'N/A'),
                    desktop_score=desktop_results.get('score', 'N/A')
                ) + "\n\n_(Це автоматичний звіт)_"
            )
            logger.info(f"Scheduled report sent for chat_id {chat_id}, url: {url}")

        except Exception as e:
            logger.error(f"Помилка у плановому завданні для chat_id {chat_id}, url {url}: {e}", exc_info=True)
            try:
                await application.bot.send_message(chat_id, BOT_MESSAGES["scheduled_error"].format(url=url, error=str(e)))
            except Exception as send_error:
                logger.error(f"Не вдалося надіслати повідомлення про помилку планового завдання для chat_id {chat_id}: {send_error}")


    def run(self):
        """Запускає бота та планувальник."""
        # Створення додатку
        self.application = Application.builder().token(self.token).build() # Store application instance

        # Додавання обробників команд
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("about", self.about_command))
        self.application.add_handler(CommandHandler("full", self.full_analysis))
        self.application.add_handler(CommandHandler("listschedules", self.list_schedules_command))

        # Conversation handler for scheduling
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler("schedule", self.schedule_start)],
            states={
                ASK_URL: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.schedule_ask_url)],
                ASK_FREQUENCY: [CallbackQueryHandler(self.schedule_set_frequency, pattern='^freq_')],
            },
            fallbacks=[CommandHandler("cancel", self.schedule_cancel)],
            conversation_timeout=300
        )
        self.application.add_handler(conv_handler)
        
        # Додавання обробника повідомлень (поза діалогом)
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.analyze_url)
        )
        
        # Додавання обробника кнопок (деталі та скасування розкладу)
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
        
        # Додавання обробника помилок
        self.application.add_error_handler(self.error_handler)

        # Запуск планувальника
        self.scheduler.start()
        logger.info("Планувальник запущено")

        # Запуск бота
        logger.info("Бот запущено")
        self.application.run_polling() # Use stored application instance

    # --- Scheduling Handlers ---

    async def schedule_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Починає діалог налаштування розкладу."""
        await update.message.reply_text(BOT_MESSAGES["schedule_ask_url"])
        return ASK_URL

    async def schedule_ask_url(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Отримує URL та запитує частоту."""
        url = update.message.text.strip()
        if not is_valid_url(url):
            await update.message.reply_text(BOT_MESSAGES["invalid_url"] + "\n" + BOT_MESSAGES["schedule_ask_url_again"])
            return ASK_URL

        context.user_data['schedule_url'] = url
        
        keyboard = [
            [InlineKeyboardButton("📅 Щотижня", callback_data='freq_weekly')],
            [InlineKeyboardButton("🌙 Щомісяця", callback_data='freq_monthly')],
            [InlineKeyboardButton("☀️ Щодня", callback_data='freq_daily')],
            [InlineKeyboardButton("⏰ Щогодини", callback_data='freq_hourly')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(BOT_MESSAGES["schedule_ask_frequency"], reply_markup=reply_markup)
        return ASK_FREQUENCY

    async def schedule_set_frequency(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Встановлює частоту та додає завдання до планувальника."""
        query = update.callback_query
        await query.answer()

        frequency = query.data.split('_')[1]
        url = context.user_data.get('schedule_url')
        chat_id = update.effective_chat.id

        if not url:
            await query.edit_message_text("❌ Помилка: URL не знайдено. Будь ласка, почніть з /schedule знову.")
            return ConversationHandler.END

        job_id = str(uuid.uuid4())

        trigger_args = {}
        freq_text = ""
        if frequency == 'weekly':
            trigger_args = {'week': 1, 'day_of_week': 'mon', 'hour': 9}
            freq_text = "щотижня"
        elif frequency == 'monthly':
            trigger_args = {'day': 1, 'hour': 9}
            freq_text = "щомісяця"
        elif frequency == 'daily':
            trigger_args = {'day': '*', 'hour': 9} # Run daily at 9 AM
            freq_text = "щодня"
        elif frequency == 'hourly':
            trigger_args = {'hour': '*'} # Run every hour
            freq_text = "щогодини"
        else:
             await query.edit_message_text("❌ Помилка: Невідома частота.")
             return ConversationHandler.END

        try:
            job = self.scheduler.add_job(
                self.scheduled_analysis_job,
                trigger='cron',
                args=[chat_id, url, self.application], # Pass application here
                id=job_id,
                name=f"Scheduled report for {chat_id} - {url}",
                replace_existing=True,
                misfire_grace_time=3600,
                **trigger_args
            )
            self.scheduled_jobs[job_id] = {'chat_id': chat_id, 'url': url, 'frequency': frequency}
            logger.info(f"Scheduled job added: {job_id} for chat {chat_id}, url {url}, freq {frequency}")
            
            await query.edit_message_text(
                BOT_MESSAGES["schedule_success"].format(url=url, frequency=freq_text)
            )
        except Exception as e:
            logger.error(f"Помилка при додаванні завдання до планувальника: {e}", exc_info=True)
            await query.edit_message_text(BOT_MESSAGES["schedule_error"].format(error=str(e)))

        if 'schedule_url' in context.user_data:
            del context.user_data['schedule_url']
            
        return ConversationHandler.END

    async def schedule_cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Скасовує процес налаштування розкладу."""
        if 'schedule_url' in context.user_data:
            del context.user_data['schedule_url']
        await update.message.reply_text(BOT_MESSAGES["schedule_cancelled"])
        return ConversationHandler.END

    async def list_schedules_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обробник команди /listschedules."""
        chat_id = update.effective_chat.id
        user_jobs = {job_id: details for job_id, details in self.scheduled_jobs.items() if details['chat_id'] == chat_id}

        if not user_jobs:
            await update.message.reply_text(BOT_MESSAGES["list_schedule_no_jobs"])
            return

        message = BOT_MESSAGES["list_schedule_header"]
        keyboard = []
        for job_id, details in user_jobs.items():
            freq_map = {'weekly': 'Щотижня', 'monthly': 'Щомісяця', 'daily': 'Щодня', 'hourly': 'Щогодини'}
            freq_text = freq_map.get(details['frequency'], details['frequency'])
            display_url = details['url'][:50] + '...' if len(details['url']) > 50 else details['url']
            message += f"• `{display_url}` ({freq_text})\n"
            keyboard.append([InlineKeyboardButton(f"❌ Скасувати для {display_url}", callback_data=f"cancel_job_{job_id}")])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(message, reply_markup=reply_markup, parse_mode="Markdown")

    # --- End Scheduling Handlers ---

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обробник команди /start."""
        user = update.effective_user
        message = BOT_MESSAGES["start"].format(user_name=user.first_name)
        await update.message.reply_text(message)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обробник команди /help."""
        help_text = BOT_MESSAGES["help"] + \
                    "\n*Планування звітів:*\n" \
                    "/schedule - Налаштувати автоматичний звіт\n" \
                    "/listschedules - Переглянути ваші заплановані звіти\n"
        await update.message.reply_text(help_text, parse_mode="Markdown")

    async def about_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обробник команди /about."""
        await update.message.reply_text(BOT_MESSAGES["about"])
    
    async def analyze_url(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обробник повідомлень з URL."""
        url = update.message.text.strip()
        logger.debug(f"Received URL for analysis: {url}")
        
        if not is_valid_url(url):
            await update.message.reply_text(BOT_MESSAGES["invalid_url"])
            return
        
        status_message = await update.message.reply_text(BOT_MESSAGES["analysis_start"])
        
        try:
            logger.debug("Starting mobile analysis...")
            mobile_results = self.analyzer.analyze(url, "mobile")
            logger.debug(f"Mobile analysis results: {mobile_results}")
            if "error" in mobile_results:
                await status_message.edit_text(
                    BOT_MESSAGES["error"].format(error=mobile_results["error"])
                )
                return
                
            logger.debug("Starting desktop analysis...")
            desktop_results = self.analyzer.analyze(url, "desktop")
            logger.debug(f"Desktop analysis results: {desktop_results}")
            if "error" in desktop_results:
                await status_message.edit_text(
                    BOT_MESSAGES["error"].format(error=desktop_results["error"])
                )
                return
                
            await status_message.edit_text(BOT_MESSAGES["analysis_complete"])
            
            logger.debug("Generating PDF report...")
            pdf_bytes = self.pdf_generator.generate_report(url, mobile_results, desktop_results)
            logger.debug(f"PDF generated, size: {pdf_bytes.getbuffer().nbytes} bytes")
            pdf_bytes.seek(0)
            
            filename = generate_filename(url)
            logger.debug(f"Sending PDF to user with filename: {filename}")
            
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
            
            await status_message.delete()
            
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
        
        if not is_valid_url(url):
            await update.message.reply_text(BOT_MESSAGES["invalid_url"])
            return
        
        status_message = await update.message.reply_text(
            "🔍 Починаю комплексний аналіз URL...\n"
            "Це може зайняти кілька хвилин. Будь ласка, зачекайте."
        )
        
        try:
            results = self.analyzer.analyze_with_all_metrics(url)
            
            if "error" in results:
                await status_message.edit_text(
                    BOT_MESSAGES["error"].format(error=results["error"])
                )
                return
            
            await status_message.edit_text("📊 Комплексний аналіз завершено. Генерую PDF-звіт...")
            
            mobile_score = results['pagespeed'].get('mobile', {}).get('score', 0)
            desktop_score = results['pagespeed'].get('desktop', {}).get('score', 0)
            
            seo_score = 100 if not results['seo'].get('recommendations') else 70
            accessibility_score = 100 if not results['accessibility'].get('recommendations') else 70
            security_score = 100 if not results['security'].get('recommendations') else 70
            
            pdf_bytes = self.pdf_generator.generate_report(
                url, 
                results['pagespeed'].get('mobile', {}), 
                results['pagespeed'].get('desktop', {})
            )
            pdf_bytes.seek(0)
            
            filename = generate_filename(url, prefix="full_analysis")
            
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
            
            await status_message.delete()
            
            recommendations_msg = "📌 **Основні рекомендації:**\n\n"
            
            if 'recommendations' in results['pagespeed'].get('mobile', {}):
                mobile_recs = results['pagespeed']['mobile']['recommendations'][:3]
                if mobile_recs:
                    recommendations_msg += "📱 **Мобільна версія:**\n"
                    for rec in mobile_recs:
                        recommendations_msg += f"• {rec}\n"
                    recommendations_msg += "\n"
            
            if 'recommendations' in results.get('seo', {}):
                seo_recs = results['seo']['recommendations'][:3]
                if seo_recs:
                    recommendations_msg += "🔍 **SEO:**\n"
                    for rec in seo_recs:
                        recommendations_msg += f"• {rec}\n"
                    recommendations_msg += "\n"
            
            if 'recommendations' in results.get('security', {}):
                security_recs = results['security']['recommendations'][:3]
                if security_recs:
                    recommendations_msg += "🔒 **Безпека:**\n"
                    for rec in security_recs:
                        recommendations_msg += f"• {rec}\n"
            
            await update.message.reply_text(recommendations_msg, parse_mode="Markdown")
            
        except Exception as e:
            logger.error(f"Помилка при комплексному аналізі: {e}", exc_info=True)
            await status_message.edit_text(
                BOT_MESSAGES["error"].format(error=str(e))
            )
        
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обробник натискань на кнопки (деталі та скасування розкладу)."""
        query = update.callback_query
        await query.answer()
        
        callback_data = query.data
        
        if not callback_data or "_" not in callback_data:
            await query.edit_message_text("❌ Помилка: неправильний формат даних кнопки")
            return

        action_parts = callback_data.split("_", 2)
        action_prefix = action_parts[0]

        if action_prefix == "detail":
            if len(action_parts) < 3:
                await query.edit_message_text("❌ Помилка: неправильний формат даних кнопки деталей")
                return
            
            device = action_parts[1]
            url = action_parts[2]
            
            if device not in ["mobile", "desktop"]:
                await query.edit_message_text("❌ Помилка: неправильний тип пристрою")
                return
                
            await query.edit_message_text(f"🔍 Отримую детальний аналіз для {device}...")
            
            try:
                if not is_valid_url(url):
                    await query.edit_message_text(BOT_MESSAGES["invalid_url"])
                    return
                    
                results = self.analyzer.analyze(url, device)
                if "error" in results:
                    await query.edit_message_text(f"❌ Помилка: {results['error']}")
                    return
                    
                device_name = "мобільних пристроїв" if device == "mobile" else "комп'ютерів"
                message = f"📊 *Детальний аналіз для {device_name}*\nURL: {url}\n\n"
                message += f"*Загальна оцінка:* {results.get('score', 'N/A')}/100\n\n"
                message += "*Основні метрики:*\n"
                for metric_name, metric_data in results.get('metrics', {}).items():
                    emoji = "✅" if metric_data.get('rating') == "good" else "⚠️" if metric_data.get('rating') == "average" else "❌"
                    message += f"{emoji} {metric_name}: {metric_data.get('value', 'N/A')} ({metric_data.get('rating', 'N/A')})\n"
                if results.get('recommendations'):
                    message += "\n*Рекомендації щодо оптимізації:*\n"
                    for rec in results['recommendations']:
                        message += f"• {rec}\n"
                await query.edit_message_text(message, parse_mode="Markdown")

            except Exception as e:
                logger.error(f"Помилка при отриманні детального аналізу: {e}", exc_info=True)
                await query.edit_message_text(
                    BOT_MESSAGES["error"].format(error=str(e))
                )
        
        elif action_prefix == "cancel" and action_parts[1] == "job":
            if len(action_parts) < 3:
                 await query.edit_message_text("❌ Помилка: Неправильний формат ID завдання для скасування.")
                 return
            
            job_id_to_cancel = action_parts[2]
            chat_id = update.effective_chat.id

            if job_id_to_cancel in self.scheduled_jobs and self.scheduled_jobs[job_id_to_cancel]['chat_id'] == chat_id:
                try:
                    self.scheduler.remove_job(job_id_to_cancel)
                    job_details = self.scheduled_jobs.pop(job_id_to_cancel)
                    logger.info(f"Removed scheduled job {job_id_to_cancel} for chat {chat_id}")
                    await query.edit_message_text(BOT_MESSAGES["schedule_cancel_success"].format(url=job_details['url']))
                except Exception as e:
                    logger.error(f"Помилка при видаленні завдання {job_id_to_cancel}: {e}", exc_info=True)
                    if job_id_to_cancel in self.scheduled_jobs:
                         await query.edit_message_text(BOT_MESSAGES["schedule_cancel_error"].format(error=str(e)))
                    else:
                         await query.edit_message_text("ℹ️ Це завдання вже було видалено.")

            else:
                logger.warning(f"Attempt to cancel non-existent or unauthorized job {job_id_to_cancel} by chat {chat_id}")
                await query.edit_message_text("❌ Помилка: Завдання не знайдено або у вас немає прав на його скасування.")

        else:
            logger.warning(f"Received unknown button callback prefix: {action_prefix} with data: {callback_data}")
            pass

    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обробник помилок."""
        logger.error(f"Виникла помилка при обробці оновлення: {context.error}", exc_info=True)
        
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "❌ Сталася помилка при обробці вашого запиту. "
                "Будь ласка, спробуйте ще раз пізніше."
            )