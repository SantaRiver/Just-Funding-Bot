#!/bin/bash
# Скрипт для проверки статуса бота

# Переходим в корневую директорию проекта
cd "$(dirname "$0")/.." || exit 1

echo "🔍 Проверка статуса Funding Bot..."
echo ""

# Проверяем запущен ли бот
PIDS=$(ps aux | grep '[b]ot.py' | awk '{print $2}')

if [ -z "$PIDS" ]; then
    echo "❌ Бот НЕ запущен"
    echo ""
    
    # Проверяем последние ошибки
    if [ -f "logs/errors.log" ]; then
        echo "📁 Последние ошибки (logs/errors.log):"
        tail -10 logs/errors.log
    fi
    
    exit 1
fi

echo "✅ Бот запущен"
echo ""

# Показываем информацию о процессе
echo "📋 Процесс:"
ps aux | grep '[b]ot.py' | head -1
echo ""

for PID in $PIDS; do
    echo "  PID: $PID"
    
    # Время работы
    START_TIME=$(ps -p $PID -o lstart=)
    echo "  Запущен: $START_TIME"
    
    # Использование памяти
    MEM=$(ps -p $PID -o %mem= | xargs)
    echo "  Память: ${MEM}%"
    
    # Использование CPU
    CPU=$(ps -p $PID -o %cpu= | xargs)
    echo "  CPU: ${CPU}%"
    echo ""
done

# Показываем размер логов
if [ -f "logs/bot.log" ]; then
    LOG_SIZE=$(du -h logs/bot.log | cut -f1)
    echo "📁 Размер bot.log: $LOG_SIZE"
fi

if [ -f "logs/errors.log" ]; then
    ERROR_SIZE=$(du -h logs/errors.log | cut -f1)
    ERROR_LINES=$(wc -l < logs/errors.log)
    echo "📁 Размер errors.log: $ERROR_SIZE ($ERROR_LINES строк)"
fi

echo ""
echo "💡 Команды:"
echo "  scripts/stop_bot.sh     - Остановить бота"
echo "  tail -f logs/bot.log    - Смотреть логи в реальном времени"
echo "  tail -f logs/errors.log - Смотреть ошибки в реальном времени"
