#!/bin/bash
# Скрипт для запуска бота в фоновом режиме (daemon)

echo "🚀 Запуск Funding Bot в фоновом режиме..."

# Проверяем не запущен ли уже бот
if pgrep -f "bot.py" > /dev/null; then
    echo "⚠️  Бот уже запущен!"
    echo ""
    echo "📋 Запущенные процессы:"
    ps aux | grep '[b]ot.py'
    echo ""
    echo "Используйте './stop_bot.sh' для остановки"
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

echo "✅ Запуск бота в фоновом режиме..."

# Запускаем бота в фоне с nohup
nohup python bot.py > logs/daemon.log 2>&1 &

# Получаем PID
BOT_PID=$!

# Ждем секунду и проверяем что процесс запустился
sleep 2

if ps -p $BOT_PID > /dev/null 2>&1; then
    echo "✅ Бот успешно запущен!"
    echo "📋 PID: $BOT_PID"
    echo "📁 Логи: logs/bot.log"
    echo "📁 Daemon лог: logs/daemon.log"
    echo ""
    echo "Для остановки используйте: ./stop_bot.sh"
    echo "Для просмотра логов: tail -f logs/bot.log"
else
    echo "❌ Не удалось запустить бота"
    echo "📁 Проверьте логи в logs/daemon.log"
    exit 1
fi
