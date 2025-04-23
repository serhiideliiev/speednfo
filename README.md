# PageSpeed Insights Telegram Bot

Telegram бот для аналізу швидкості завантаження веб-сторінок за допомогою Google PageSpeed Insights API з генерацією PDF-звітів українською мовою.

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![Python](https://img.shields.io/badge/python-3.14-green)

## 📋 Опис проєкту

PageSpeed Insights Telegram Bot - це інструмент, який дозволяє швидко та зручно отримувати аналіз продуктивності веб-сторінок безпосередньо у Telegram. Бот використовує Google PageSpeed Insights API для аналізу URL, генерує детальний PDF-звіт з результатами та рекомендаціями щодо оптимізації, а також надає можливість отримати детальнішу інформацію про конкретні аспекти продуктивності сайту.

### Основні функції

- Аналіз URL за допомогою Google PageSpeed Insights API
- Перевірка як мобільної, так і десктопної версій сайту
- Генерація детальних PDF-звітів українською мовою
- Інтерактивні кнопки для отримання додаткової інформації
- Детальний аналіз основних метрик продуктивності
- Рекомендації щодо оптимізації

## 🔧 Вимоги

- Python 3.8+ (рекомендовано Python 3.14)
- Доступ до Telegram Bot API
- Доступ до Google PageSpeed Insights API
- Український шрифт для PDF-звітів

## 📦 Залежності

Основні бібліотеки, які використовуються в проєкті:

- `python-telegram-bot` (версія 20.4 або новіша) - для взаємодії з Telegram API
- `requests` - для виконання HTTP-запитів до Google PageSpeed API
- `reportlab` - для створення PDF-звітів українською мовою

## 🚀 Налаштування та запуск

### Крок 1: Клонування репозиторію

```bash
git clone https://github.com/yourusername/pagespeed-telegram-bot.git
cd pagespeed-telegram-bot
```

### Крок 2: Створення віртуального середовища

```bash
python -m venv venv
source venv/bin/activate  # для Linux/MacOS
# або
venv\Scripts\activate  # для Windows
```

### Крок 3: Встановлення залежностей

```bash
pip install -r requirements.txt
```

### Крок 4: Отримання Telegram Bot API токена

1. Відкрийте Telegram і знайдіть бота @BotFather
2. Надішліть команду `/newbot`
3. Дотримуйтесь інструкцій BotFather:
   - Вкажіть ім'я бота (наприклад, "PageSpeed Analysis Bot")
   - Вкажіть унікальне ім'я користувача, яке обов'язково має закінчуватися на "bot" (наприклад, "my_pagespeed_bot")
4. Після успішного створення бота BotFather надасть вам токен API
5. Збережіть цей токен — він буде потрібний для налаштування бота

### Крок 5: Налаштування Google PageSpeed Insights API

1. Перейдіть до [Google Cloud Console](https://console.cloud.google.com/)
2. Створіть новий проект або виберіть існуючий
3. У бічному меню перейдіть до "APIs & Services" > "Library"
4. Знайдіть "PageSpeed Insights API" і активуйте її
5. У бічному меню перейдіть до "APIs & Services" > "Credentials"
6. Натисніть "Create Credentials" > "API Key"
7. Скопіюйте створений API ключ — це ваш PAGESPEED_API_KEY

### Крок 6: Налаштування українського шрифту для PDF

1. Завантажте відповідний шрифт з підтримкою українських символів, наприклад:
   - [Google Fonts - Roboto](https://fonts.google.com/specimen/Roboto)
   - [Google Fonts - Noto Sans Ukrainian](https://fonts.google.com/noto/specimen/Noto+Sans+Ukrainian)
2. Створіть директорію `fonts` в корені проєкту (якщо її ще немає)
3. Скопіюйте завантажений файл шрифту (наприклад, Roboto-Regular.ttf) до директорії `fonts`

### Крок 7: Налаштування змінних середовища

Створіть файл `.env` в корені проєкту:

```env
TELEGRAM_BOT_TOKEN=ваш_телеграм_бот_токен
PAGESPEED_API_KEY=ваш_google_pagespeed_api_ключ
PDF_FONT_PATH=fonts/ваш_шрифт.ttf
```

Або ви можете встановити ці змінні безпосередньо у вашій системі:

```bash
# Linux/MacOS
export TELEGRAM_BOT_TOKEN=ваш_телеграм_бот_токен
export PAGESPEED_API_KEY=ваш_google_pagespeed_api_ключ
export PDF_FONT_PATH=fonts/ваш_шрифт.ttf

# Windows
set TELEGRAM_BOT_TOKEN=ваш_телеграм_бот_токен
set PAGESPEED_API_KEY=ваш_google_pagespeed_api_ключ
set PDF_FONT_PATH=fonts/ваш_шрифт.ttf
```

### Крок 8: Запуск бота

```bash
python main.py
```

## 📱 Використання бота

1. **Початок роботи**:
   - Відправте `/start` для отримання привітання та короткої інструкції
   - Відправте `/help` для отримання детальнішої інформації
   - Відправте `/about` для отримання інформації про бота

2. **Аналіз URL**:
   - Просто відправте боту повний URL, включаючи протокол (http:// або https://)
   - Наприклад: `https://example.com`
   - Бот почне аналіз і повідомить вас про прогрес
   - Після завершення аналізу ви отримаєте PDF-звіт та кнопки для детального аналізу

3. **Детальний аналіз**:
   - Після отримання основного звіту, натисніть на одну з кнопок:
     - "📱 Детальний аналіз для мобільних"
     - "🖥️ Детальний аналіз для десктопу"
   - Бот надішле вам текстове повідомлення з детальнішою інформацією

## 🚀 Розгортання на сервері

### Варіант 1: Розгортання на VPS (Virtual Private Server)

1. Орендуйте VPS у будь-якого провайдера (DigitalOcean, Linode, AWS, GCP та ін.)
2. Підключіться до сервера через SSH
3. Встановіть Python та необхідні залежності:
   ```bash
   sudo apt update
   sudo apt install python3 python3-pip python3-venv git
   ```
4. Клонуйте репозиторій та налаштуйте проєкт:
   ```bash
   git clone https://github.com/yourusername/pagespeed-telegram-bot.git
   cd pagespeed-telegram-bot
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
5. Створіть файл .env з налаштуваннями (як описано вище)
6. Налаштуйте systemd для автоматичного запуску:
   ```bash
   sudo nano /etc/systemd/system/pagespeed_bot.service
   ```

   Додайте такий вміст (замініть шляхи та користувача):
   ```
   [Unit]
   Description=Telegram PageSpeed Bot
   After=network.target

   [Service]
   User=your_username
   Group=your_username
   WorkingDirectory=/home/your_username/pagespeed-telegram-bot
   ExecStart=/home/your_username/pagespeed-telegram-bot/venv/bin/python main.py
   Restart=always
   RestartSec=10

   [Install]
   WantedBy=multi-user.target
   ```

7. Активуйте сервіс:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable pagespeed_bot
   sudo systemctl start pagespeed_bot
   ```

8. Перевірте статус:
   ```bash
   sudo systemctl status pagespeed_bot
   ```

### Варіант 2: Розгортання за допомогою Docker

1. Встановіть Docker на свій сервер
2. Створіть файл `Dockerfile` у корені проєкту:
   ```Dockerfile
   FROM python:3.11-slim

   WORKDIR /app

   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt

   COPY . .

   CMD ["python", "main.py"]
   ```

3. Створіть файл `.dockerignore`:
   ```
   venv/
   __pycache__/
   *.pyc
   *.pyo
   *.pyd
   .git/
   .env
   ```

4. Зберіть Docker-образ:
   ```bash
   docker build -t pagespeed-bot .
   ```

5. Запустіть контейнер:
   ```bash
   docker run -d --name pagespeed-bot \
       -e TELEGRAM_BOT_TOKEN=ваш_телеграм_бот_токен \
       -e PAGESPEED_API_KEY=ваш_google_pagespeed_api_ключ \
       -e PDF_FONT_PATH=fonts/ваш_шрифт.ttf \
       --restart unless-stopped \
       pagespeed-bot
   ```

## ⚙️ Додаткові налаштування

### Налаштування логування

Ви можете змінити рівень логування в файлі `config.py`, знайшовши рядок:

```python
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
```

Доступні рівні: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`.

### Налаштування мови інтерфейсу

Всі повідомлення бота містяться в словнику `BOT_MESSAGES` у файлі `config.py`. Ви можете змінити будь-які тексти відповідно до ваших потреб.

### Налаштування дизайну PDF-звітів

Дизайн PDF-звітів можна змінити в класі `PDFReportGenerator` у файлі `pdf_generator.py`. Ви можете налаштувати кольори, шрифти, розміри та інші аспекти відображення.

## 🚦 Усунення несправностей

### Проблеми з Telegram Bot API

Якщо бот не відповідає на повідомлення:
1. Перевірте, чи правильно вказано токен у змінній середовища
2. Перевірте, чи запущений бот через BotFather
3. Спробуйте перезапустити бота

### Проблеми з Google PageSpeed API

Якщо аналіз не працює:
1. Перевірте, чи правильно вказано API ключ
2. Перевірте, чи активована API в Google Cloud Console
3. Перевірте обмеження запитів для вашого API ключа

### Проблеми з генерацією PDF

Якщо виникають проблеми з українськими символами в PDF:
1. Перевірте, чи правильно вказано шлях до шрифту
2. Переконайтеся, що шрифт підтримує українські символи
3. Спробуйте використовувати інший шрифт

## 📝 Можливості для розширення

Ось кілька ідей, як можна розширити функціонал бота:

1. **Додавання нових метрик**: SEO аналіз, перевірка безпеки, аналіз доступності
2. **Збереження історії аналізів**: зберігання результатів для порівняння динаміки
3. **Планувальник регулярних перевірок**: автоматичні перевірки URL з повідомленнями про зміни
4. **Розширені звіти**: додавання графіків, скріншотів, пояснень для кожної метрики
5. **Масовий аналіз**: можливість аналізувати кілька URL одночасно

## 📄 Ліцензія

Цей проєкт розповсюджується під ліцензією MIT. Детальніше дивіться у файлі LICENSE.

## 📧 Контакти

Якщо у вас виникли питання або пропозиції щодо покращення проєкту, будь ласка, зв'яжіться з нами:

- Email: your.email@example.com
- Telegram: @your_username

---

Створено з ❤️ для покращення веб-продуктивності