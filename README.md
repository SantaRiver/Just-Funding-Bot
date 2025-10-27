# Funding Rate Bot 🚀

Асинхронный Telegram бот для мониторинга ставок финансирования (funding rates) на криптовалютных биржах.

## ⚡ Возможности

- 🔄 **Асинхронная архитектура** - быстрый сбор данных от 9 бирж одновременно
- 💾 **Кэширование с TTL** - защита от rate limiting (экономия до 80% запросов)
- 🛡️ **Thundering Herd Protection** - одновременные запросы не создают нагрузку
- 📊 **Красивое форматирование** - таблицы, эмодзи, ссылки на контракты
- ⏰ **Умная группировка** - показывает токены с ближайшим funding
- 🔔 **Система алертов** - автоматические уведомления о высоких ставках
- 💎 **Поиск возможностей для хеджирования** - автоматический поиск арбитражных возможностей между биржами
- 🔐 **Админ панель** - управление кэшем только для администратора

## 🏦 Поддерживаемые биржи

- ✅ Bybit
- ✅ Binance Futures
- ✅ MEXC
- ✅ Gate.io
- ✅ KuCoin
- ✅ Bitget
- ✅ BingX
- ✅ BitMart
- ✅ OKX

## 📋 Требования

- Python 3.8+
- Telegram Bot Token
- pip (для установки зависимостей)

## 🚀 Быстрый старт

### 1. Клонирование репозитория

```bash
git clone <repository-url>
cd funding_bot
```

### 2. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 3. Настройка .env

Создайте файл `.env` в корне проекта:

```bash
cp .env.example .env
```

Заполните переменные:

```env
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your_bot_token_here

# Cache Configuration
CACHE_TTL=30  # Время жизни кэша в секундах (default: 30)

# Admin Configuration
ADMIN_USER_ID=your_telegram_user_id  # Только этот пользователь может управлять кэшем
```

**Как узнать свой Telegram User ID:**
- Найдите бота [@userinfobot](https://t.me/userinfobot)
- Отправьте ему любое сообщение
- Скопируйте ваш ID

### 4. Запуск бота

#### На Linux сервере (рекомендуется)

Используйте предоставленные скрипты:

```bash
# Сделать скрипты исполняемыми (один раз)
chmod +x scripts/*.sh

# Запуск в фоновом режиме (daemon)
scripts/start_bot_daemon.sh

# Проверка статуса
scripts/check_bot.sh

# Остановка
scripts/stop_bot.sh
```

**Подробнее:** [scripts/README.md](scripts/README.md)

#### Ручной запуск

```bash
python bot.py
```

Вы увидите:
```
INFO - 📁 Логи сохраняются в: /path/to/logs
INFO - Cache TTL set to: 30 seconds
INFO - Admin user ID set to: 123456789
INFO - Initializing aggregator with cache TTL: 30s
INFO - Bot started
```

## 📱 Команды бота

### Основные команды

| Команда | Описание |
|---------|----------|
| `/start` | Приветствие и список команд |
| `/top` | Топ-5 токенов с ближайшим funding |
| `/token BTC` | Данные по конкретному токену |
| `/hedge [MIN_SPREAD]` | Найти возможности для хеджирования (арбитраж funding rates) |
| `/set_threshold 0.5` | Установить порог алерта (%) |
| `/start_monitoring` | Включить автоматические алерты |
| `/stop_monitoring` | Выключить алерты |
| `/status` | Показать текущие настройки |

### Админские команды (только для ADMIN_USER_ID)

| Команда | Описание |
|---------|----------|
| `/cache_stats` | Статистика кэша (HIT/MISS, возраст записей) |
| `/clear_cache` | Принудительная очистка кэша |

## 📊 Примеры вывода

### Команда `/top`

```
🏆 ТОП-5 ТОКЕНОВ
⏰ Bybit funding: 18:00 (25.10, UTC+3)
Другие биржи могут иметь другое время ⬇️
─────────────────────────────────────────────

🔴 1. BTC 📈 (⏰ 18:00)
💰 Цена: $68,234

┌──────────┬───────────┬────────┐
│Биржа     │ Rate      │ Время  │
├──────────┼───────────┼────────┤
│BYBIT     │ +0.5234%  │ 18:00  │
│BINANCE   │ +0.5120%  │ 18:00  │
│MEXC      │ +0.4890%  │ 20:00  │
└──────────┴───────────┴────────┘

📊 Ссылки на контракты:
  • BYBIT: Открыть ↗
  • BINANCE: Открыть ↗
  • MEXC: Открыть ↗

💡 🔴 Очень высокая | 🟠 Высокая | 🟡 Средняя | 🟢 Низкая
📈 Long→Short | 📉 Short→Long
⏰ Все времена в UTC+3 (МСК). Разные биржи = разное время funding
```

### Команда `/hedge` (Поиск возможностей для хеджирования)

```
💎 ВОЗМОЖНОСТИ ДЛЯ ХЕДЖИРОВАНИЯ
Найдено: 3 | Показано топ-3
─────────────────────────────────────────────

🔥 1. BTC
📊 Спред: 1.2500%
💰 Цена: $68,234

🎯 Стратегия:
📈 LONG на BINANCE: -0.0500%
📉 SHORT на MEXC: +1.2000%

💵 Прибыль за цикл: ~1.2500%
⏰ До funding: 2ч 15мин

Биржа     │ Rate
──────────┼──────────
BINANCE   │ -0.0500% 📈
BYBIT     │ +0.5234%
MEXC      │ +1.2000% 📉

📊 Ссылки:
  • BINANCE (LONG): Открыть ↗
  • MEXC (SHORT): Открыть ↗
```

**Использование:**
- `/hedge` - Поиск с минимальным спредом 0.3% (по умолчанию)
- `/hedge 0.5` - Поиск с минимальным спредом 0.5%
- `/hedge 1.0` - Поиск только очень выгодных возможностей (спред ≥1%)

### Команда `/cache_stats` (только для админа)

```
📊 Статистика кэша
──────────────────────────────

⚙️ Cache TTL: 30с
📦 Всего записей: 1
✅ Валидных: 1
❌ Истекших: 0

Записи в кэше:
✅ grouped_by_token:5
   Возраст: 15.3с / TTL: 30с
```

## ⚙️ Конфигурация

### Cache TTL (время жизни кэша)

Рекомендуемые значения в зависимости от нагрузки:

| Сценарий | TTL | Описание |
|----------|-----|----------|
| Dev/Testing | 10-15 сек | Быстрое тестирование |
| Мало пользователей (<10) | 30 сек | Баланс свежести и нагрузки |
| Средне (10-100) | 30-60 сек | Защита от burst requests |
| Много (>100) | 60-120 сек | Минимизация запросов |
| Очень много (>1000) | 120-300 сек | Максимальная защита |

**Изменить TTL:**
1. Откройте `.env`
2. Измените `CACHE_TTL=30` на нужное значение
3. Перезапустите бота

### Администратор

Только пользователь с указанным `ADMIN_USER_ID` может:
- Просматривать статистику кэша (`/cache_stats`)
- Очищать кэш (`/clear_cache`)

**Безопасность:**
- ✅ Все попытки доступа логируются
- ✅ `.env` должен быть в `.gitignore`
- ✅ Не публикуйте свой User ID

## 🏗️ Архитектура

```
funding_bot/
├── bot.py                 # Основной файл бота
├── models.py             # Модели данных (FundingRate, ContractInfo)
├── config.py             # Конфигурация
├── exchanges/            # Адаптеры для бирж
│   ├── base.py          # Базовый класс ExchangeAdapter
│   ├── bybit_adapter.py
│   ├── binance_adapter.py
│   ├── mexc_adapter.py
│   ├── gateio_adapter.py
│   └── kucoin_adapter.py
├── services/            # Бизнес-логика
│   ├── aggregator.py   # Агрегация данных от бирж
│   ├── cache.py        # Система кэширования
│   └── formatter.py    # Форматирование сообщений
├── scripts/             # Shell-скрипты
│   ├── start_bot.sh
│   ├── stop_bot.sh
│   └── check_bot.sh
├── tests/               # Тесты
│   ├── test_async.py
│   └── test_exchanges.py
└── docs/               # Документация
    ├── CACHE_SYSTEM.md
    ├── ADMIN_SETUP.md
    └── CHANGELOG.md
```

## 📈 Производительность

### Без кэша
```
10 пользователей × 5 бирж = 50 запросов/минуту
Risk: ❌ HIGH (rate limit)
```

### С кэшем (TTL 30с)
```
10 пользователей → ~10 запросов/минуту
Risk: ✅ LOW (80% экономия)
```

## 🐛 Troubleshooting

### Проблема: Rate limit от биржи

**Решение:**
1. Увеличьте `CACHE_TTL` в `.env`
2. Проверьте `/cache_stats` - должен быть высокий HIT rate
3. Рекомендуется TTL >= 30 секунд

### Проблема: "У вас нет прав для выполнения этой команды"

**Решение:**
1. Узнайте свой User ID через @userinfobot
2. Убедитесь что он совпадает с `ADMIN_USER_ID` в `.env`
3. Перезапустите бота

### Проблема: Данные не обновляются

**Решение:**
1. Используйте `/clear_cache` (если вы админ)
2. Или подождите истечения TTL
3. Перезапустите бота

### Проблема: "Conflict: terminated by other getUpdates request"

Эта ошибка означает, что запущено **несколько экземпляров бота** одновременно.

**Решение на Linux:**
```bash
# Остановите все процессы
scripts/stop_bot.sh

# Проверьте что бот не запущен
scripts/check_bot.sh

# Если процессы остались, убейте принудительно
pkill -9 -f bot.py

# Подождите 5 секунд
sleep 5

# Запустите снова
scripts/start_bot_daemon.sh
```

**Решение вручную:**
```bash
# Найти все процессы
ps aux | grep bot.py

# Убить конкретный процесс
kill <PID>

# Или убить все сразу
pkill -f bot.py
```

**На Windows:**
```powershell
# Найти процессы
Get-Process python | Where-Object {$_.Path -like "*bot.py*"}

# Убить процесс
Stop-Process -Id <PID>
```

**Подробнее:** [scripts/README.md](scripts/README.md#ошибка-conflict-terminated-by-other-getupdates-request)

## 📊 Логирование

Бот автоматически записывает подробные логи в директорию `logs/`:

- **logs/bot.log** - Основной лог (INFO и выше, до 10 MB, 5 файлов ротации)
- **logs/errors.log** - Только ошибки (ERROR, до 5 MB, 3 файла ротации)

### Просмотр логов в реальном времени

```powershell
# Windows PowerShell
Get-Content logs\bot.log -Wait -Tail 50
```

```bash
# Linux/Mac
tail -f logs/bot.log
```

**Подробнее:** [LOGGING.md](docs/LOGGING.md)

## 📚 Документация

- [scripts/README.md](scripts/README.md) - Управление ботом на сервере 🔧
- [docs/LOGGING.md](docs/LOGGING.md) - Система логирования ⭐
- [docs/HEDGING_GUIDE.md](docs/HEDGING_GUIDE.md) - Руководство по хеджированию 💎
- [docs/CACHE_SYSTEM.md](docs/CACHE_SYSTEM.md) - Подробная документация по кэшу
- [docs/ADMIN_SETUP.md](docs/ADMIN_SETUP.md) - Настройка администратора
- [docs/CHANGELOG.md](docs/CHANGELOG.md) - История изменений

## 🔧 Разработка

### Добавить новую биржу

1. Создайте файл `exchanges/new_exchange_adapter.py`
2. Наследуйтесь от `ExchangeAdapter`
3. Реализуйте методы `get_funding_rate()` и `get_all_funding_rates()`
4. Добавьте в `bot.py`:
```python
from exchanges.new_exchange_adapter import NewExchangeAdapter

exchanges = [
    # ...
    NewExchangeAdapter(),
]
```

### Запустить тесты

```bash
# Тест только MEXC
python tests/test_mexc_only.py

# Общий async тест
python tests/test_async.py
```

## 📄 Лицензия

MIT License

## 🤝 Contributing

Pull requests are welcome!

## 📧 Контакты

Если у вас есть вопросы или предложения, создайте Issue.

---

**⚠️ Важно:** Этот бот предназначен только для информационных целей. Всегда проверяйте данные на официальных сайтах бирж перед принятием торговых решений.
