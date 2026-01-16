# Скрипт для загрузки проекта на GitHub
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Загрузка проекта на GitHub" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Проверка наличия Git
try {
    $gitVersion = git --version 2>&1
    Write-Host "[OK] Git установлен: $gitVersion" -ForegroundColor Green
} catch {
    Write-Host "[ОШИБКА] Git не установлен!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Пожалуйста, установите Git:" -ForegroundColor Yellow
    Write-Host "1. Скачайте с https://git-scm.com/download/win" -ForegroundColor Yellow
    Write-Host "2. Установите Git" -ForegroundColor Yellow
    Write-Host "3. Перезапустите этот скрипт" -ForegroundColor Yellow
    Write-Host ""
    Read-Host "Нажмите Enter для выхода"
    exit 1
}

Write-Host ""

# Инициализация репозитория
Write-Host "[1/8] Инициализация Git репозитория..." -ForegroundColor Yellow
if (Test-Path .git) {
    Write-Host "[INFO] Git репозиторий уже инициализирован" -ForegroundColor Gray
} else {
    git init
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ОШИБКА] Не удалось инициализировать репозиторий" -ForegroundColor Red
        Read-Host "Нажмите Enter для выхода"
        exit 1
    }
    Write-Host "[OK] Репозиторий инициализирован" -ForegroundColor Green
}
Write-Host ""

# Настройка пользователя
Write-Host "[2/8] Настройка Git пользователя..." -ForegroundColor Yellow
git config user.name "Pererenchina"
git config user.email "pererenchina@users.noreply.github.com"
Write-Host "[OK] Пользователь настроен" -ForegroundColor Green
Write-Host ""

# Добавление файлов
Write-Host "[3/8] Добавление файлов в индекс..." -ForegroundColor Yellow
git add .
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ОШИБКА] Не удалось добавить файлы" -ForegroundColor Red
    Read-Host "Нажмите Enter для выхода"
    exit 1
}
Write-Host "[OK] Файлы добавлены" -ForegroundColor Green
Write-Host ""

# Проверка статуса
Write-Host "[4/8] Проверка статуса..." -ForegroundColor Yellow
git status --short
Write-Host ""

# Создание коммита
Write-Host "[5/8] Создание коммита..." -ForegroundColor Yellow
git commit -m "Initial commit: Auto-monitor Telegram bot"
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ПРЕДУПРЕЖДЕНИЕ] Возможно, нет изменений для коммита" -ForegroundColor Yellow
}
Write-Host ""

# Переименование ветки
Write-Host "[6/8] Настройка ветки main..." -ForegroundColor Yellow
git branch -M main
Write-Host ""

# Добавление remote
Write-Host "[7/8] Добавление удаленного репозитория..." -ForegroundColor Yellow
git remote remove origin 2>$null
git remote add origin https://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@github.com/Pererenchina/auto-monitor-bot.git
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ОШИБКА] Не удалось добавить remote" -ForegroundColor Red
    Read-Host "Нажмите Enter для выхода"
    exit 1
}
Write-Host "[OK] Remote добавлен" -ForegroundColor Green
Write-Host ""

# Отправка на GitHub
Write-Host "[8/8] Отправка кода на GitHub..." -ForegroundColor Yellow
git push -u origin main
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "[ОШИБКА] Не удалось отправить код на GitHub" -ForegroundColor Red
    Write-Host ""
    Write-Host "Возможные причины:" -ForegroundColor Yellow
    Write-Host "1. Репозиторий не создан на GitHub" -ForegroundColor Yellow
    Write-Host "2. Неверный токен доступа" -ForegroundColor Yellow
    Write-Host "3. Проблемы с сетью" -ForegroundColor Yellow
    Write-Host ""
    Read-Host "Нажмите Enter для выхода"
    exit 1
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "[УСПЕХ] Проект успешно загружен на GitHub!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Репозиторий: https://github.com/Pererenchina/auto-monitor-bot" -ForegroundColor Cyan
Write-Host ""
Read-Host "Нажмите Enter для выхода"
