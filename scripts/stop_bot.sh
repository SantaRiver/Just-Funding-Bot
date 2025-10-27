#!/bin/bash
# Скрипт для остановки всех экземпляров бота

# Переходим в корневую директорию проекта
cd "$(dirname "$0")/.." || exit 1

echo "🔍 Поиск запущенных экземпляров бота..."

# Ищем процессы по разным паттернам
PIDS=$(ps aux | grep -E '[b]ot\.py|python.*bot\.py' | grep -v grep | awk '{print $2}')

if [ -z "$PIDS" ]; then
    echo "✅ Бот не запущен"
    
    # Дополнительная проверка через pgrep
    PGREP_PIDS=$(pgrep -f "bot.py" 2>/dev/null)
    if [ ! -z "$PGREP_PIDS" ]; then
        echo "⚠️  Но найдены процессы через pgrep:"
        ps -p $PGREP_PIDS
        PIDS=$PGREP_PIDS
    else
        exit 0
    fi
fi

echo "📋 Найденные процессы:"
ps aux | grep -E '[b]ot\.py|python.*bot\.py' | grep -v grep

echo ""
echo "🛑 Остановка процессов..."

for PID in $PIDS; do
    echo "  Убиваю процесс $PID"
    kill $PID 2>/dev/null
    sleep 1
    
    # Проверяем завершился ли процесс
    if ps -p $PID > /dev/null 2>&1; then
        echo "  ⚠️  Процесс $PID не завершился, использую kill -9"
        kill -9 $PID 2>/dev/null
    fi
done

# Дополнительно убиваем через pkill
echo "  🔨 Принудительная остановка через pkill..."
pkill -9 -f "bot.py" 2>/dev/null
pkill -9 -f "python.*bot.py" 2>/dev/null

sleep 2

# Проверяем что все процессы остановлены
REMAINING=$(ps aux | grep '[b]ot.py' | wc -l)

if [ $REMAINING -eq 0 ]; then
    echo "✅ Все процессы остановлены"
    echo ""
    echo "💡 Теперь можно запустить бота:"
    echo "   scripts/fix_telegram_conflict.sh  # Сначала исправить конфликт"
    echo "   scripts/start_bot_daemon.sh       # Затем запустить"
else
    echo "❌ Остались запущенные процессы:"
    ps aux | grep '[b]ot.py'
    echo ""
    echo "⚠️  Попробуйте вручную:"
    echo "   pkill -9 -f bot.py"
fi
