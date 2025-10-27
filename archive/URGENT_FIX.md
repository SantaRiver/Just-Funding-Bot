# 🚨 СРОЧНОЕ ИСПРАВЛЕНИЕ: Conflict Error

## Проблема
```
telegram.error.Conflict: Conflict: terminated by other getUpdates request; 
make sure that only one bot instance is running
```

## Причины
1. ✅ Запущено несколько экземпляров бота
2. ✅ Установлен webhook (вместо polling)
3. ✅ Бот запущен на другом сервере/компьютере
4. ✅ Не очищены pending updates

## 🔥 СРОЧНОЕ РЕШЕНИЕ

### Шаг 1: Остановить ВСЕ процессы

На вашем сервере (`/var/www/Just-Funding-Bot/`):

```bash
cd /var/www/Just-Funding-Bot

# Сделать скрипты исполняемыми
chmod +x *.sh

# Остановить все процессы
./stop_bot.sh

# Убить принудительно ВСЕ Python процессы бота
pkill -9 -f bot.py
pkill -9 -f "python.*funding"
pkill -9 -f "python3.*funding"

# Проверить что процессов нет
ps aux | grep bot.py
pgrep -af bot.py
```

Если **все еще видите процессы** - убейте их по PID:
```bash
kill -9 <PID>
```

---

### Шаг 2: Удалить webhook и очистить updates

**Вариант A: Через bash скрипт**
```bash
chmod +x fix_telegram_conflict.sh
./fix_telegram_conflict.sh
```

**Вариант B: Через Python скрипт**
```bash
python3 fix_telegram_conflict.py
```

**Вариант C: Вручную через curl**
```bash
# Замените YOUR_BOT_TOKEN на ваш токен из .env
TOKEN="YOUR_BOT_TOKEN"

# Проверить webhook
curl "https://api.telegram.org/bot${TOKEN}/getWebhookInfo"

# Удалить webhook
curl "https://api.telegram.org/bot${TOKEN}/deleteWebhook?drop_pending_updates=true"

# Очистить updates
curl "https://api.telegram.org/bot${TOKEN}/getUpdates?offset=-1"
```

---

### Шаг 3: Подождать освобождения

```bash
# ВАЖНО: Подождите минимум 30 секунд!
sleep 30
```

---

### Шаг 4: Запустить заново

```bash
./start_bot_daemon.sh
```

---

## ⚠️ ЕСЛИ НЕ ПОМОГЛО

### Проверка 1: Нет ли бота на другом сервере?

Проверьте **все** ваши серверы, компьютеры, VPS где может быть запущен бот:
- Локальный компьютер (Windows/Mac/Linux)
- Другой VPS
- Heroku / Railway / другой хостинг
- Docker контейнер
- Screen/tmux сессия

**Найти все:**
```bash
# На Linux
ps aux | grep -i funding
ps aux | grep -i bot.py
pgrep -af python

# Убить все
pkill -9 -f bot.py
```

---

### Проверка 2: Webhook на хостинге?

Если вы когда-либо деплоили бота на **Heroku, Railway, Render, Vercel** или другой хостинг с webhook:

```bash
TOKEN="YOUR_BOT_TOKEN"

# Проверить webhook
curl "https://api.telegram.org/bot${TOKEN}/getWebhookInfo"

# Если видите URL (например, https://your-app.herokuapp.com/) - удалите:
curl "https://api.telegram.org/bot${TOKEN}/deleteWebhook?drop_pending_updates=true"
```

---

### Проверка 3: Логи других процессов

```bash
# Найти ВСЕ Python процессы
ps aux | grep python

# Показать открытые файлы bot.py
lsof | grep bot.py

# Проверить systemd сервисы
systemctl list-units | grep -i bot
systemctl list-units | grep -i funding
```

---

## 🔧 РАДИКАЛЬНОЕ РЕШЕНИЕ

Если ничего не помогает:

### Вариант 1: Полная очистка процессов

```bash
# Остановить ВСЕ Python процессы (ОПАСНО, если есть другие приложения!)
pkill -9 python
pkill -9 python3

# Перезагрузить сервер (если возможно)
sudo reboot
```

---

### Вариант 2: Сменить режим на webhook временно

Иногда помогает переключение режима и обратно:

```bash
TOKEN="YOUR_BOT_TOKEN"

# Установить временный webhook (замените URL)
curl "https://api.telegram.org/bot${TOKEN}/setWebhook?url=https://example.com/webhook"

# Сразу удалить
curl "https://api.telegram.org/bot${TOKEN}/deleteWebhook?drop_pending_updates=true"

# Подождать
sleep 10

# Запустить polling
./start_bot_daemon.sh
```

---

### Вариант 3: Создать нового бота

**Последнее средство** - создать нового бота через @BotFather:

1. Напишите @BotFather в Telegram
2. `/newbot`
3. Придумайте имя и username
4. Получите новый токен
5. Замените `TELEGRAM_BOT_TOKEN` в `.env`
6. Запустите: `./start_bot_daemon.sh`

---

## 📋 Чеклист перед запуском

- [ ] ✅ Остановлены ВСЕ процессы bot.py (проверено через `ps aux | grep bot.py`)
- [ ] ✅ Webhook удален (проверено через getWebhookInfo)
- [ ] ✅ Pending updates очищены
- [ ] ✅ Прошло минимум 30 секунд после остановки
- [ ] ✅ Нет других экземпляров на других серверах
- [ ] ✅ Нет webhook на хостинге (Heroku и т.д.)
- [ ] ✅ Готов запустить через `./start_bot_daemon.sh`

---

## 💡 Как избежать в будущем

1. **Всегда используйте скрипты:**
   ```bash
   ./stop_bot.sh      # Перед остановкой
   ./start_bot_daemon.sh  # Для запуска
   ./check_bot.sh     # Для проверки
   ```

2. **Не запускайте бота вручную** через `python bot.py` на продакшене

3. **Используйте systemd** для автозапуска (см. SCRIPTS_README.md)

4. **Никогда не используйте одновременно:**
   - Polling на одном сервере
   - Webhook на другом сервере
   - Несколько экземпляров

---

## 🆘 Нужна помощь?

Если ничего не помогло, соберите диагностику:

```bash
# Создать файл с диагностикой
{
    echo "=== Date ==="
    date
    echo ""
    echo "=== Running processes ==="
    ps aux | grep -i python
    echo ""
    echo "=== Bot processes ==="
    ps aux | grep bot.py
    pgrep -af bot
    echo ""
    echo "=== Webhook info ==="
    curl "https://api.telegram.org/bot$(grep TELEGRAM_BOT_TOKEN .env | cut -d= -f2)/getWebhookInfo"
    echo ""
    echo "=== Recent errors ==="
    tail -50 logs/errors.log
} > diagnostic.txt

cat diagnostic.txt
```

Отправьте содержимое `diagnostic.txt` для анализа.
