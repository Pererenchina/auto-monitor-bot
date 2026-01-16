@echo off
chcp 65001 >nul
echo ========================================
echo Загрузка проекта на GitHub
echo ========================================
echo.

REM Проверка наличия Git
git --version >nul 2>&1
if errorlevel 1 (
    echo [ОШИБКА] Git не установлен!
    echo.
    echo Пожалуйста, установите Git:
    echo 1. Скачайте с https://git-scm.com/download/win
    echo 2. Установите Git
    echo 3. Перезапустите этот скрипт
    echo.
    pause
    exit /b 1
)

echo [OK] Git установлен
echo.

REM Инициализация репозитория
echo [1/6] Инициализация Git репозитория...
if exist .git (
    echo [INFO] Git репозиторий уже инициализирован
) else (
    git init
    if errorlevel 1 (
        echo [ОШИБКА] Не удалось инициализировать репозиторий
        pause
        exit /b 1
    )
    echo [OK] Репозиторий инициализирован
)
echo.

REM Настройка пользователя
echo [2/6] Настройка Git пользователя...
git config user.name "Pererenchina"
git config user.email "pererenchina@users.noreply.github.com"
echo [OK] Пользователь настроен
echo.

REM Добавление файлов
echo [3/6] Добавление файлов в индекс...
git add .
if errorlevel 1 (
    echo [ОШИБКА] Не удалось добавить файлы
    pause
    exit /b 1
)
echo [OK] Файлы добавлены
echo.

REM Проверка статуса
echo [4/6] Проверка статуса...
git status --short
echo.

REM Создание коммита
echo [5/6] Создание коммита...
git commit -m "Initial commit: Auto-monitor Telegram bot"
if errorlevel 1 (
    echo [ПРЕДУПРЕЖДЕНИЕ] Возможно, нет изменений для коммита
)
echo.

REM Переименование ветки
echo [6/6] Настройка ветки main...
git branch -M main
echo.

REM Добавление remote
echo [7/7] Добавление удаленного репозитория...
git remote remove origin 2>nul
git remote add origin https://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@github.com/Pererenchina/auto-monitor-bot.git
if errorlevel 1 (
    echo [ОШИБКА] Не удалось добавить remote
    pause
    exit /b 1
)
echo [OK] Remote добавлен
echo.

REM Отправка на GitHub
echo [8/8] Отправка кода на GitHub...
git push -u origin main
if errorlevel 1 (
    echo.
    echo [ОШИБКА] Не удалось отправить код на GitHub
    echo.
    echo Возможные причины:
    echo 1. Репозиторий не создан на GitHub
    echo 2. Неверный токен доступа
    echo 3. Проблемы с сетью
    echo.
    pause
    exit /b 1
)

echo.
echo ========================================
echo [УСПЕХ] Проект успешно загружен на GitHub!
echo ========================================
echo.
echo Репозиторий: https://github.com/Pererenchina/auto-monitor-bot
echo.
pause
