# ⚠️ Git не установлен

Git не установлен на вашем компьютере, поэтому автоматическая загрузка на GitHub невозможна.

## Решение:

### Вариант 1: Установить Git и запустить скрипт

1. **Установите Git:**
   - Скачайте: https://git-scm.com/download/win
   - Установите (можно оставить все настройки по умолчанию)
   - **ВАЖНО:** После установки перезапустите терминал/PowerShell

2. **Запустите скрипт:**
   - Двойной клик на `upload_to_github.bat`
   - Или в PowerShell: `.\upload_to_github.ps1`

### Вариант 2: Использовать GitHub Desktop

1. Скачайте GitHub Desktop: https://desktop.github.com/
2. Установите и войдите в свой аккаунт GitHub
3. File → Add Local Repository → выберите папку `C:\bot`
4. Нажмите "Publish repository"

### Вариант 3: Загрузить файлы вручную через веб-интерфейс

1. Зайдите на https://github.com/Pererenchina/auto-monitor-bot
2. Нажмите "uploading an existing file"
3. Перетащите файлы из папки `C:\bot` (кроме `.env`, `auto_monitor.db`, `bot.log`, `__pycache__`)

## Текущий статус:

✅ **Бот запущен и работает**  
❌ **Код не загружен на GitHub** (требуется Git)

## Что делать дальше:

После установки Git просто запустите `upload_to_github.bat` - все будет сделано автоматически!
