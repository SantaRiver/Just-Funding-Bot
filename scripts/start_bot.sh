#!/bin/bash
# Скрипт для безопасного запуска бота

# Переходим в корневую директорию проекта
cd "$(dirname "$0")/.." || exit 1

echo "🚀 Запуск Funding Bot..."

# Проверяем не запущен ли уже бот
if pgrep -f "bot.py" > /dev/null; then
    echo "⚠️  Бот уже запущен!"
    echo ""
    echo "📋 Запущенные процессы:"
    ps aux | grep '[b]ot.py'
    echo ""
    echo "Используйте 'scripts/stop_bot.sh' для остановки"
    exit 1
fi

# Проверяем наличие .env файла
if [ ! -f .env ]; then
    echo "❌ Файл .env не найден!"
    echo "Скопируйте .env.example в .env и заполните переменные"
    exit 1
fi

# Проверяем наличие виртуального окружения
if [ ! -d "venv" ]; then
    echo "⚠️  Виртуальное окружение не найдено"
    echo "Создаю venv..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# Создаем директорию для логов
mkdir -p logs

echo "✅ Запуск бота..."
echo ""

# Запускаем бота
python bot.py

# Если бот завершился с ошибкой
if [ $? -ne 0 ]; then
    echo ""
    echo "❌ Бот завершился с ошибкой"
    echo "📁 Проверьте логи в logs/errors.log"
    exit 1
fi
