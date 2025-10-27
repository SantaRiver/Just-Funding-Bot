# Скрипты управления ботом

Набор bash-скриптов для управления ботом на Linux сервере.

## 🚀 Быстрый старт

### 1. Сделать скрипты исполняемыми

```bash
chmod +x *.sh
```

### 2. Запустить бота

**Интерактивный режим** (видно логи в консоли):
```bash
./start_bot.sh
```

**Фоновый режим** (daemon):
```bash
./start_bot_daemon.sh
```

### 3. Проверить статус

```bash
./check_bot.sh
```

### 4. Остановить бота

```bash
./stop_bot.sh
```

## 📋 Описание скриптов

### start_bot.sh
Запуск бота в интерактивном режиме (с выводом логов в консоль).

**Что делает:**
- Проверяет что бот не запущен
- Проверяет наличие `.env` файла
- Активирует виртуальное окружение (создает если нужно)
- Запускает бота

**Использование:**
```bash
./start_bot.sh
```

**Остановка:** Ctrl+C

---

### start_bot_daemon.sh
Запуск бота в фоновом режиме (daemon).

**Что делает:**
- Проверяет что бот не запущен
- Проверяет наличие `.env` файла
- Активирует виртуальное окружение
- Запускает бота в фоне через `nohup`
- Создает `logs/daemon.log` для вывода daemon

**Использование:**
```bash
./start_bot_daemon.sh
```

**Вывод:**
```
✅ Бот успешно запущен!
📋 PID: 12345
📁 Логи: logs/bot.log
📁 Daemon лог: logs/daemon.log

Для остановки используйте: ./stop_bot.sh
Для просмотра логов: tail -f logs/bot.log
```

**Остановка:** `./stop_bot.sh`

---

### check_bot.sh
Проверка статуса бота.

**Что показывает:**
- Запущен ли бот
- PID процесса
- Время запуска
- Использование памяти и CPU
- Размер лог-файлов
- Количество ошибок

**Использование:**
```bash
./check_bot.sh
```

**Пример вывода:**
```
🔍 Проверка статуса Funding Bot...

✅ Бот запущен

📋 Процесс:
root     12345  0.5  2.1 256784 87632 ?   Sl   20:00   0:15 python bot.py

  PID: 12345
  Запущен: Sun Oct 27 20:00:00 2025
  Память: 2.1%
  CPU: 0.5%

📁 Размер bot.log: 2.3M
📁 Размер errors.log: 45K (123 строк)

💡 Команды:
  ./stop_bot.sh           - Остановить бота
  tail -f logs/bot.log    - Смотреть логи в реальном времени
  tail -f logs/errors.log - Смотреть ошибки в реальном времени
```

---

### stop_bot.sh
Остановка всех экземпляров бота.

**Что делает:**
- Ищет все процессы `bot.py`
- Останавливает их через `kill`
- Если процесс не останавливается, использует `kill -9`
- Проверяет что все процессы остановлены

**Использование:**
```bash
./stop_bot.sh
```

**Вывод:**
```
🔍 Поиск запущенных экземпляров бота...
📋 Найденные процессы:
root     12345  0.5  2.1 256784 87632 ?   Sl   20:00   0:15 python bot.py

🛑 Остановка процессов...
  Убиваю процесс 12345
✅ Все процессы остановлены
```

---

## 🔧 Решение проблем

### Ошибка: "Бот уже запущен"

Если при запуске видите:
```
⚠️  Бот уже запущен!
```

**Решение:**
```bash
# Остановите старые процессы
./stop_bot.sh

# Запустите снова
./start_bot_daemon.sh
```

---

### Ошибка: "Conflict: terminated by other getUpdates request"

Это означает что запущено несколько экземпляров бота одновременно.

**Решение:**
```bash
# 1. Остановите ВСЕ процессы
./stop_bot.sh

# 2. Проверьте что бот не запущен
./check_bot.sh

# 3. Если всё ещё показывает что запущен, убейте вручную
pkill -9 -f bot.py

# 4. Подождите 5 секунд
sleep 5

# 5. Запустите снова
./start_bot_daemon.sh
```

---

### Найти все процессы бота вручную

```bash
# Поиск
ps aux | grep bot.py

# Или
pgrep -af bot.py

# Убить конкретный процесс
kill <PID>

# Убить все процессы бота
pkill -f bot.py

# Убить принудительно
pkill -9 -f bot.py
```

---

### Смотреть логи в реальном времени

```bash
# Основной лог
tail -f logs/bot.log

# Только ошибки
tail -f logs/errors.log

# Daemon лог (если запущен через start_bot_daemon.sh)
tail -f logs/daemon.log

# Последние 100 строк
tail -100 logs/bot.log

# Поиск ошибок
grep "ERROR" logs/bot.log
grep "❌" logs/bot.log
```

---

## 🔄 Автозапуск при перезагрузке сервера

### Через systemd

Создайте файл `/etc/systemd/system/funding-bot.service`:

```ini
[Unit]
Description=Funding Rate Telegram Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/var/www/Just-Funding-Bot
ExecStart=/var/www/Just-Funding-Bot/venv/bin/python /var/www/Just-Funding-Bot/bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Активируйте:
```bash
sudo systemctl daemon-reload
sudo systemctl enable funding-bot
sudo systemctl start funding-bot

# Проверка статуса
sudo systemctl status funding-bot

# Логи
sudo journalctl -u funding-bot -f
```

---

### Через crontab

```bash
crontab -e
```

Добавьте:
```cron
@reboot cd /var/www/Just-Funding-Bot && ./start_bot_daemon.sh
```

---

## 💡 Рекомендации

1. **Используйте daemon режим на продакшене:**
   ```bash
   ./start_bot_daemon.sh
   ```

2. **Регулярно проверяйте статус:**
   ```bash
   ./check_bot.sh
   ```

3. **Мониторьте логи ошибок:**
   ```bash
   tail -f logs/errors.log
   ```

4. **Настройте автозапуск** через systemd или crontab

5. **Ротация логов настроена автоматически** (10 MB для bot.log, 5 MB для errors.log)
