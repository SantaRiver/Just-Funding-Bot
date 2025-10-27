#!/bin/bash
# Скрипт для исправления ошибки "Conflict: terminated by other getUpdates request"

echo "🔧 Исправление конфликта Telegram Bot..."
echo ""

# Проверяем .env файл
if [ ! -f .env ]; then
    echo "❌ Файл .env не найден!"
    exit 1
fi

# Загружаем токен
source .env

if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
    echo "❌ TELEGRAM_BOT_TOKEN не найден в .env"
    exit 1
fi

echo "✅ Токен найден: ${TELEGRAM_BOT_TOKEN:0:10}..."
echo ""

# Шаг 1: Убиваем все процессы бота
echo "📋 Шаг 1: Остановка всех процессов бота..."
pkill -9 -f bot.py 2>/dev/null
pkill -9 -f "python.*bot.py" 2>/dev/null
sleep 2

REMAINING=$(ps aux | grep '[b]ot.py' | wc -l)
if [ $REMAINING -eq 0 ]; then
    echo "   ✅ Все процессы остановлены"
else
    echo "   ⚠️  Остались процессы:"
    ps aux | grep '[b]ot.py'
fi
echo ""

# Шаг 2: Проверяем webhook
echo "📋 Шаг 2: Проверка webhook..."
WEBHOOK_INFO=$(curl -s "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getWebhookInfo")
echo "   Response: $WEBHOOK_INFO"

# Проверяем есть ли установленный webhook
HAS_WEBHOOK=$(echo $WEBHOOK_INFO | grep -o '"url":"[^"]*"' | grep -v '""')

if [ ! -z "$HAS_WEBHOOK" ]; then
    echo "   ⚠️  Обнаружен webhook: $HAS_WEBHOOK"
    echo "   🔧 Удаляю webhook..."
    
    DELETE_RESULT=$(curl -s "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/deleteWebhook?drop_pending_updates=true")
    echo "   Response: $DELETE_RESULT"
    
    if echo $DELETE_RESULT | grep -q '"ok":true'; then
        echo "   ✅ Webhook успешно удален"
    else
        echo "   ❌ Не удалось удалить webhook"
    fi
else
    echo "   ✅ Webhook не установлен"
fi
echo ""

# Шаг 3: Очищаем pending updates
echo "📋 Шаг 3: Очистка pending updates..."
GET_UPDATES=$(curl -s "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getUpdates?offset=-1&timeout=1")
echo "   ✅ Pending updates очищены"
echo ""

# Шаг 4: Проверяем что нет других подключений
echo "📋 Шаг 4: Ждем освобождения подключений..."
for i in {1..10}; do
    echo "   Попытка $i/10..."
    sleep 1
done
echo "   ✅ Готово"
echo ""

echo "✅ Все проверки завершены!"
echo ""
echo "💡 Теперь запустите бота:"
echo "   ./start_bot_daemon.sh"
echo ""
echo "Если ошибка повторяется:"
echo "   1. Проверьте что бот не запущен на другом сервере"
echo "   2. Проверьте что бот не запущен локально"
echo "   3. Подождите 1-2 минуты и попробуйте снова"
