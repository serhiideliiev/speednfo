#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Основний модуль Telegram бота для аналізу URL з Google PageSpeed Insights
"""

import uuid
import matplotlib
matplotlib.use('Agg') # Use Agg backend for non-interactive plotting
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import socketserver

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    filters, ContextTypes, ConversationHandler
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.memory import MemoryJobStore

from config import TOKEN, BOT_MESSAGES, logger, FONT_PATH, FONT_NAME
from pagespeed_analyzer import PageSpeedAnalyzer
from pdf_generator import PDFReportGenerator
from utils import is_valid_url, generate_filename

# Register the font for Matplotlib if available
if FONT_PATH and FONT_NAME:
    try:
        # Check if font is already registered
        if not any(FONT_PATH in f.fname for f in fm.fontManager.ttflist):
            fm.fontManager.addfont(FONT_PATH)
            logger.info(f"Successfully registered font {FONT_NAME} from {FONT_PATH} with Matplotlib.")
        # Set default font
        plt.rcParams['font.family'] = FONT_NAME
        plt.rcParams['axes.unicode_minus'] = False # Handle minus sign correctly
    except Exception as e:
        logger.error(f"Failed to register or set font {FONT_NAME} for Matplotlib: {e}", exc_info=True)
        # Fallback to default sans-serif font if Roboto fails
        plt.rcParams['font.family'] = 'sans-serif'
elif FONT_PATH:
    logger.warning("Font path found but font name is missing. Matplotlib might not use the correct font.")
    plt.rcParams['font.family'] = 'sans-serif'
else:
    logger.warning("Font path not found. Matplotlib will use default fonts.")
    plt.rcParams['font.family'] = 'sans-serif'

# Define states for ConversationHandler
ASK_URL, ASK_FREQUENCY = range(2)

# Health Check Server for Koyeb
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b"OK")
        else:
            self.send_response(404)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b"Not Found")

def start_health_server():
    port = int(os.environ.get("PORT", 8000))
    try:
        with socketserver.TCPServer(("", port), HealthCheckHandler) as httpd:
            logger.info(f"Health check server listening on port {port}")
            httpd.serve_forever()
    except Exception as e:
        logger.error(f"Could not start health check server on port {port}: {e}", exc_info=True)

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
        # Start health check server in a new thread for Koyeb
        health_thread = threading.Thread(target=start_health_server, daemon=True)
        health_thread.start()

        # Створення додатку
        self.application = Application.builder().token(self.token).build() # Store application instance

        # Додавання обробників команд
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("about", self.about_command))
        self.application.add_handler(CommandHandler("full", self.full_analysis))
        self.application.add_handler(CommandHandler("listschedules", self.list_schedules_command))
        self.application.add_handler(CommandHandler("compare", self.compare_urls))

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

    # --- Command Handlers ---

    async def start(self, update: Update, _context: ContextTypes.DEFAULT_TYPE): # pylint: disable=unused-argument
        """Обробник команди /start."""
        await update.message.reply_text(BOT_MESSAGES.get("start", "Вітаю! Надішліть мені URL для аналізу або використайте /help для отримання списку команд."))

    async def help_command(self, update: Update, _context: ContextTypes.DEFAULT_TYPE): # pylint: disable=unused-argument
        """Обробник команди /help."""
        await update.message.reply_text(BOT_MESSAGES["help"])

    async def about_command(self, update: Update, _context: ContextTypes.DEFAULT_TYPE): # pylint: disable=unused-argument
        """Обробник команди /about."""
        await update.message.reply_text(BOT_MESSAGES.get("about", "Цей бот аналізує швидкість сторінок за допомогою Google PageSpeed Insights."))

    async def full_analysis(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обробник команди /full. Виконує повний аналіз URL."""
        # Check if a URL was provided with the command
        if not context.args:
            await update.message.reply_text(BOT_MESSAGES.get("full_analysis_no_url", "Будь ласка, вкажіть URL після команди /full. Наприклад: /full https://example.com"))
            return

        url = context.args[0]
        if not is_valid_url(url):
            await update.message.reply_text(BOT_MESSAGES["invalid_url"])
            return

        chat_id = update.effective_chat.id
        await update.message.reply_text(BOT_MESSAGES["analysis_started"].format(url=url))

        try:
            # Perform analysis for both mobile and desktop
            mobile_results = self.analyzer.analyze(url, "mobile")
            desktop_results = self.analyzer.analyze(url, "desktop")

            # Check for errors during analysis
            if "error" in mobile_results or "error" in desktop_results:
                error_msg = mobile_results.get("error", "") or desktop_results.get("error", "")
                await update.message.reply_text(BOT_MESSAGES["analysis_error"].format(url=url, error=error_msg))
                return

            # Generate PDF report
            pdf_bytes = self.pdf_generator.generate_report(url, mobile_results, desktop_results)
            pdf_bytes.seek(0)
            filename = generate_filename(url, prefix="full_report")

            # Send the PDF report
            await update.message.reply_document(
                document=pdf_bytes,
                filename=filename,
                caption=BOT_MESSAGES["report_caption"].format(
                    url=url,
                    mobile_score=mobile_results.get('score', 'N/A'),
                    desktop_score=desktop_results.get('score', 'N/A')
                )
            )
            logger.info(f"Full analysis report sent for {url} to chat_id {chat_id}")

        except Exception as e:
            logger.error(f"Помилка під час повного аналізу для {url}: {e}", exc_info=True)
            await update.message.reply_text(BOT_MESSAGES["analysis_error"].format(url=url, error=str(e)))

    async def compare_urls(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обробник команди /compare. Порівнює два URL."""
        if len(context.args) != 2:
            await update.message.reply_text(BOT_MESSAGES.get("compare_usage", "Будь ласка, вкажіть два URL для порівняння. Наприклад: /compare https://example.com https://anotherexample.com"))
            return

        url1, url2 = context.args
        if not is_valid_url(url1) or not is_valid_url(url2):
            await update.message.reply_text(BOT_MESSAGES["invalid_url"] + " Перевірте обидва URL.")
            return

        chat_id = update.effective_chat.id
        await update.message.reply_text(BOT_MESSAGES.get("compare_started", "Починаю порівняльний аналіз для:").format(url1=url1, url2=url2))

        try:
            # Analyze first URL
            await update.message.reply_text(f"Аналізую {url1}...")
            mobile1 = self.analyzer.analyze(url1, "mobile")
            desktop1 = self.analyzer.analyze(url1, "desktop")
            if "error" in mobile1 or "error" in desktop1:
                error_msg = mobile1.get("error", "") or desktop1.get("error", "")
                await update.message.reply_text(BOT_MESSAGES["analysis_error"].format(url=url1, error=error_msg))
                # Optionally continue with the second URL or stop
                # return # Uncomment to stop if first URL fails

            # Analyze second URL
            await update.message.reply_text(f"Аналізую {url2}...")
            mobile2 = self.analyzer.analyze(url2, "mobile")
            desktop2 = self.analyzer.analyze(url2, "desktop")
            if "error" in mobile2 or "error" in desktop2:
                error_msg = mobile2.get("error", "") or desktop2.get("error", "")
                await update.message.reply_text(BOT_MESSAGES["analysis_error"].format(url=url2, error=error_msg))
                # Optionally proceed with comparison using available data or stop
                # return # Uncomment to stop if second URL fails

            # --- Generate Comparison Summary (Example) ---
            # This part needs more detailed implementation based on how you want to compare.
            # For now, just sending individual scores.

            summary = f"*Порівняння {url1} та {url2}:*\n\n"

            summary += f"*{url1}:*\n"
            summary += f"  📱 Mobile Score: {mobile1.get('score', 'N/A')}\n"
            summary += f"  💻 Desktop Score: {desktop1.get('score', 'N/A')}\n\n"

            summary += f"*{url2}:*\n"
            summary += f"  📱 Mobile Score: {mobile2.get('score', 'N/A')}\n"
            summary += f"  💻 Desktop Score: {desktop2.get('score', 'N/A')}\n"
            
            # You might want to generate a comparison chart or a more detailed text report here.
            # Example: Compare specific metrics like LCP, FCP, CLS etc.

            await update.message.reply_text(summary, parse_mode="Markdown")
            logger.info(f"Comparison analysis sent for {url1} and {url2} to chat_id {chat_id}")

            # Optionally, generate a combined PDF or separate reports
            # pdf_bytes1 = self.pdf_generator.generate_report(url1, mobile1, desktop1)
            # pdf_bytes2 = self.pdf_generator.generate_report(url2, mobile2, desktop2)
            # ... send reports ...

        except Exception as e:
            logger.error(f"Помилка під час порівняльного аналізу для {url1} та {url2}: {e}", exc_info=True)
            await update.message.reply_text(BOT_MESSAGES["analysis_error"].format(url=f'{url1} та {url2}', error=str(e)))

    # --- Scheduling Handlers ---

    async def schedule_start(self, update: Update, _context: ContextTypes.DEFAULT_TYPE) -> int: # pylint: disable=unused-argument
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
            _ = self.scheduler.add_job( # Assign to _ as job variable is unused
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

    async def list_schedules_command(self, update: Update, _context: ContextTypes.DEFAULT_TYPE): # pylint: disable=unused-argument
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

    # --- Message Handlers ---

    async def analyze_url(self, update: Update, _context: ContextTypes.DEFAULT_TYPE): # pylint: disable=unused-argument
        """Обробляє текстові повідомлення, що містять URL."""
        url = update.message.text.strip()
        if not is_valid_url(url):
            # Send a specific message if it looks like a command was intended but misspelled
            if url.startswith('/'):
                 await update.message.reply_text(BOT_MESSAGES.get("unknown_command", "Невідома команда. Використайте /help для списку команд."))
            else:
                await update.message.reply_text(BOT_MESSAGES["invalid_url_prompt"])
            return

        chat_id = update.effective_chat.id
        await update.message.reply_text(BOT_MESSAGES["analysis_started"].format(url=url))

        try:
            # Perform analysis for both mobile and desktop
            mobile_results = self.analyzer.analyze(url, "mobile")
            desktop_results = self.analyzer.analyze(url, "desktop")

            # Check for errors
            if "error" in mobile_results or "error" in desktop_results:
                error_msg = mobile_results.get("error", "") or desktop_results.get("error", "")
                await update.message.reply_text(BOT_MESSAGES["analysis_error"].format(url=url, error=error_msg))
                return

            # Generate PDF report
            pdf_bytes = self.pdf_generator.generate_report(url, mobile_results, desktop_results)
            pdf_bytes.seek(0)
            filename = generate_filename(url, prefix="report")

            # Send the PDF report
            await update.message.reply_document(
                document=pdf_bytes,
                filename=filename,
                caption=BOT_MESSAGES["report_caption"].format(
                    url=url,
                    mobile_score=mobile_results.get('score', 'N/A'),
                    desktop_score=desktop_results.get('score', 'N/A')
                )
                # Add buttons for details if needed
                # reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📊 Деталі", callback_data=f"details_{url}")]])
            )
            logger.info(f"Analysis report sent for {url} to chat_id {chat_id}")

        except Exception as e:
            logger.error(f"Помилка під час аналізу URL {url}: {e}", exc_info=True)
            await update.message.reply_text(BOT_MESSAGES["analysis_error"].format(url=url, error=str(e)))

    # --- Callback Query Handlers ---

    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обробляє натискання на inline кнопки."""
        query = update.callback_query
        await query.answer() # Acknowledge the button press

        data = query.data
        chat_id = update.effective_chat.id

        if data.startswith("cancel_job_"):
            job_id = data.split("cancel_job_")[1]
            if job_id in self.scheduled_jobs and self.scheduled_jobs[job_id]['chat_id'] == chat_id:
                try:
                    self.scheduler.remove_job(job_id)
                    url = self.scheduled_jobs[job_id]['url']
                    del self.scheduled_jobs[job_id]
                    await query.edit_message_text(BOT_MESSAGES["schedule_cancelled_job"].format(url=url))
                    logger.info(f"Scheduled job {job_id} cancelled by user {chat_id} for url {url}")
                    # Refresh the list message if possible (or just remove buttons)
                    # This might require storing the original message ID or resending the list
                    await self.list_schedules_command(update.callback_query, context) # Try refreshing the list
                except Exception as e:
                    logger.error(f"Помилка при скасуванні завдання {job_id}: {e}", exc_info=True)
                    await query.edit_message_text(BOT_MESSAGES["schedule_cancel_error"].format(error=str(e)))
            else:
                await query.edit_message_text("❌ Помилка: Завдання не знайдено або належить іншому користувачу.")
        
        # Add other callback data handling here if needed (e.g., "details_...")
        # elif data.startswith("details_"):
        #     url = data.split("details_")[1]
        #     # Fetch details and send them
        #     await query.message.reply_text(f"Деталі для {url} (ще не реалізовано).")
        else:
            logger.warning(f"Unhandled callback data received: {data}")
            # Optionally inform the user
            # await query.edit_message_text("Невідома дія.")

    # --- Error Handler ---

    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE):
        """Log Errors caused by Updates."""
        logger.error(f'Update "{update}" caused error "{context.error}"', exc_info=context.error)
        # Optionally, notify the user about the error
        if isinstance(update, Update) and update.effective_chat:
            try:
                # Ensure context.bot is available and valid
                if hasattr(context, 'bot') and context.bot:
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=BOT_MESSAGES.get("generic_error", "Виникла внутрішня помилка. Будь ласка, спробуйте пізніше.")
                    )
                else:
                    logger.warning("context.bot is not available in error_handler, cannot send message to user.")
            except Exception as e:
                logger.error(f"Failed to send error message to chat {update.effective_chat.id}: {e}")