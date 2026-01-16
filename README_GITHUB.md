# Инструкция по загрузке на GitHub

## ⚠️ ВАЖНО: Git не установлен на вашем компьютере

Для загрузки проекта на GitHub необходимо установить Git.

## Быстрое решение:

### Вариант 1: Установить Git и запустить скрипт

1. **Установите Git:**
   - Скачайте с https://git-scm.com/download/win
   - Установите, следуя инструкциям
   - Перезапустите терминал

2. **Запустите скрипт:**
   - Двойной клик на `upload_to_github.bat` (для Windows)
   - Или выполните в PowerShell: `.\upload_to_github.ps1`

### Вариант 2: Выполнить команды вручную

После установки Git, откройте PowerShell в папке `C:\bot` и выполните:

```powershell
git init
git config user.name "Pererenchina"
git config user.email "pererenchina@users.noreply.github.com"
git add .
git commit -m "Initial commit: Auto-monitor Telegram bot"
git branch -M main
git remote add origin https://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@github.com/Pererenchina/auto-monitor-bot.git
git push -u origin main
```

## Что будет загружено:

✅ Весь исходный код  
✅ Документация (README.md, SETUP.md, BOT_STATUS.md)  
✅ requirements.txt  
✅ .gitignore  
✅ .env.example (шаблон конфигурации)

## Что НЕ будет загружено (благодаря .gitignore):

❌ `.env` - файл с токеном бота  
❌ `auto_monitor.db` - база данных  
❌ `bot.log` - логи  
❌ `__pycache__/` - кэш Python

## После загрузки:

1. Проверьте репозиторий: https://github.com/Pererenchina/auto-monitor-bot
2. Убедитесь, что файл `.env` НЕ загружен (он должен быть в .gitignore)
3. Если `.env` случайно загружен, **немедленно смените токен бота** в @BotFather

## Безопасность токена:

Токен GitHub, который вы предоставили, будет использован только для загрузки кода.  
После успешной загрузки рекомендуется:
1. Удалить токен из скриптов (если планируете их хранить)
2. Или использовать SSH ключи вместо токена для дальнейшей работы
