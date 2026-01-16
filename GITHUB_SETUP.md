# Инструкция по загрузке проекта на GitHub

## Шаг 1: Установка Git

Если Git не установлен на вашем компьютере:
1. Скачайте Git с официального сайта: https://git-scm.com/download/win
2. Установите Git, следуя инструкциям установщика
3. Перезапустите терминал/командную строку

## Шаг 2: Создание репозитория на GitHub

1. Войдите в свой аккаунт на GitHub (или создайте новый): https://github.com
2. Нажмите кнопку **"New"** или **"+"** в правом верхнем углу
3. Выберите **"New repository"**
4. Заполните форму:
   - **Repository name**: `auto-monitor-bot` (или любое другое имя)
   - **Description**: "Telegram-бот для мониторинга объявлений о продаже автомобилей"
   - Выберите **Public** или **Private** (рекомендуется Private, так как это бот)
   - **НЕ** ставьте галочки на "Initialize this repository with a README" (у нас уже есть файлы)
5. Нажмите **"Create repository"**

## Шаг 3: Инициализация Git в проекте

Откройте терминал/командную строку в папке проекта (`C:\bot`) и выполните следующие команды:

```bash
# Инициализация git репозитория
git init

# Добавление всех файлов (кроме тех, что в .gitignore)
git add .

# Создание первого коммита
git commit -m "Initial commit: Auto-monitor Telegram bot"

# Добавление удаленного репозитория (замените YOUR_USERNAME на ваш GitHub username)
git remote add origin https://github.com/YOUR_USERNAME/auto-monitor-bot.git

# Переименование основной ветки в main (если нужно)
git branch -M main

# Отправка кода на GitHub
git push -u origin main
```

## Шаг 4: Настройка переменных окружения

**ВАЖНО:** После клонирования репозитория на другой компьютер:

1. Создайте файл `.env` в корне проекта:
```bash
cp .env.example .env
```

2. Откройте `.env` и укажите ваш токен бота:
```
BOT_TOKEN=your_telegram_bot_token_here
```

3. **НЕ коммитьте файл `.env`** - он уже в `.gitignore` и не будет загружен на GitHub

## Шаг 5: Установка зависимостей

На новом компьютере после клонирования:

```bash
# Установка зависимостей
pip install -r requirements.txt

# Установка Playwright (для парсера onliner.by)
playwright install
```

## Безопасность

✅ **Что НЕ будет загружено на GitHub (благодаря .gitignore):**
- `.env` - файл с токеном бота
- `auto_monitor.db` - база данных
- `bot.log` - логи
- `__pycache__/` - кэш Python
- Все временные файлы

✅ **Что будет загружено:**
- Весь исходный код
- `requirements.txt` - зависимости
- `README.md`, `SETUP.md`, `BOT_STATUS.md` - документация
- `.env.example` - пример конфигурации (без реального токена)

## Дополнительные команды Git

```bash
# Проверить статус изменений
git status

# Посмотреть изменения в файлах
git diff

# Добавить конкретный файл
git add filename.py

# Создать новый коммит
git commit -m "Описание изменений"

# Отправить изменения на GitHub
git push

# Получить последние изменения с GitHub
git pull
```

## Если возникли проблемы

1. **Ошибка аутентификации:**
   - Используйте Personal Access Token вместо пароля
   - Создайте токен: GitHub → Settings → Developer settings → Personal access tokens → Generate new token
   - Используйте токен как пароль при `git push`

2. **Конфликты при push:**
   - Выполните `git pull` перед `git push`
   - Разрешите конфликты, если они возникнут

3. **Забыли добавить .env в .gitignore:**
   - Если случайно закоммитили `.env`, удалите его из истории:
   ```bash
   git rm --cached .env
   git commit -m "Remove .env from repository"
   git push
   ```
   - Затем **смените токен бота** в @BotFather, так как старый токен был скомпрометирован
