# Funding Rate Bot 🚀

Асинхронный телеграм-бот для мониторинга ставок финансирования (funding rates) на различных криптовалютных биржах.

## ⚡ Особенности v2.0 (Async)

- ✅ **Асинхронная архитектура** - максимальная скорость и производительность
- ✅ **Параллельные запросы** - данные от всех бирж одновременно
- ✅ **5 активных бирж**: Binance, Bybit, MEXC, Gate.io, KuCoin
- ✅ **Умная логика** - группировка по времени funding, топ-5 с ближайшим funding
- ✅ **Чистая архитектура** - SOLID, KISS, DRY принципы
- ✅ **Автоматические алерты** - уведомления при превышении порога
- ✅ **Красивое форматирование** - таблицы с данными от всех бирж

## Архитектура

Проект следует принципам чистой архитектуры:

```
funding_bot/
├── models.py                    # Модели данных (FundingRate, ContractInfo)
├── exchanges/                   # Адаптеры бирж
│   ├── base.py                 # Абстрактный базовый класс
│   ├── bybit_adapter.py        # Bybit
│   ├── binance_adapter.py      # Binance
│   ├── mexc_adapter.py         # MEXC
│   ├── gateio_adapter.py       # Gate.io
│   ├── kucoin_adapter.py       # KuCoin
│   ├── bitget_adapter.py       # BitGet
│   └── bingx_adapter.py        # BingX
├── services/                    # Бизнес-логика
│   ├── aggregator.py           # Агрегация данных от бирж
│   └── formatter.py            # Форматирование сообщений
├── bot.py                      # Телеграм-бот
└── config.py                   # Конфигурация

```

## Установка

1. Клонируйте репозиторий:
```bash
git clone <repository-url>
cd funding_bot
```

2. Создайте виртуальное окружение:
```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac
```

3. Установите зависимости:
```bash
pip install -r requirements.txt
```

4. Настройте `.env` файл:
```env
# Telegram Bot
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here

# Binance (опционально, для аутентифицированных запросов)
API_KEY=your_binance_api_key
API_SECRET=your_binance_api_secret
BASE_PATH=https://fapi.binance.com

# Настройки (опционально)
LOG_LEVEL=INFO
```

## Использование

### Запуск бота

```bash
python bot.py
```

### Команды бота

- `/start` - Начать работу с ботом
- `/help` - Показать справку
- `/top` - Показать топ токенов по funding rate
- `/token <SYMBOL>` - Получить данные по конкретному токену (например: `/token BTC`)
- `/set_threshold <VALUE>` - Установить порог алерта (например: `/set_threshold 0.5`)
- `/start_monitoring` - Начать мониторинг (алерты каждые 10 минут)
- `/stop_monitoring` - Остановить мониторинг
- `/status` - Показать текущие настройки

### Примеры использования

1. **Получить топ токенов:**
   ```
   /top
   ```
   Показывает топ-10 токенов с наибольшими ставками финансирования

2. **Получить данные по конкретному токену:**
   ```
   /token BTC
   ```
   Показывает данные по BTC от всех бирж

3. **Настроить алерты:**
   ```
   /set_threshold 0.5
   /start_monitoring
   ```
   Бот будет отправлять алерты когда funding rate превысит 0.5%

## Формат алертов

```
🚨**Алерт (Осталось ~10 мин): COAI на ASTER** (Ваш порог: 0.5%, Время: 10 мин)🚨
Token: COAI (Source: ASTER) | Date (UTC+3): 25-10-2025 15:02

Exc.      | Price      | Funding   | Countd.
ASTER    | 8.21       | -0.5068%  | 00:03:00
BITMART  | 8.22       | -0.4733%  | 00:03:00
BITGET   | 8.23       | -0.4490%  | 00:03:00
BINANCE  | 8.18       | -0.4351%  | 00:03:00
...
```

## Добавление новой биржи

Для добавления поддержки новой биржи:

1. Создайте новый адаптер в `exchanges/`, наследуясь от `ExchangeAdapter`
2. Реализуйте абстрактные методы:
   - `get_top_contracts(limit)` - получить топ контрактов
   - `get_funding_rate(symbol)` - получить ставку для конкретного символа
   - `get_all_funding_rates()` - получить все ставки
3. Добавьте адаптер в `exchanges/__init__.py`
4. Добавьте инициализацию в `bot.py` в метод `_init_aggregator()`

Пример:
```python
# exchanges/newexchange_adapter.py
from exchanges.base import ExchangeAdapter
from models import FundingRate, ContractInfo

class NewExchangeAdapter(ExchangeAdapter):
    def __init__(self):
        super().__init__("NEWEXCHANGE")
        # ... инициализация
    
    def get_funding_rate(self, symbol: str) -> Optional[FundingRate]:
        # ... реализация
        pass
```

## Принципы дизайна

### SOLID

- **S**ingle Responsibility: Каждый класс имеет одну ответственность
  - `ExchangeAdapter` - работа с API биржи
  - `FundingRateAggregator` - агрегация данных
  - `MessageFormatter` - форматирование сообщений
  
- **O**pen/Closed: Легко добавлять новые биржи без изменения существующего кода

- **L**iskov Substitution: Все адаптеры бирж взаимозаменяемы

- **I**nterface Segregation: Минимальные интерфейсы без лишних зависимостей

- **D**ependency Inversion: Зависимость от абстракций (`ExchangeAdapter`), не от конкретных реализаций

### KISS (Keep It Simple, Stupid)

- Простые, понятные методы
- Минимум вложенности
- Ясные имена переменных и функций

### DRY (Don't Repeat Yourself)

- Переиспользование кода через наследование
- Общие утилиты в базовых классах
- Единый источник истины для конфигурации

## Разработка

### Структура моделей данных

```python
@dataclass
class FundingRate:
    exchange: str              # Название биржи
    symbol: str               # Символ контракта
    rate: float              # Ставка (например, 0.0001 = 0.01%)
    price: float             # Текущая цена
    next_funding_time: datetime  # Время следующего funding
    quote_currency: str      # Котируемая валюта
```

### Логирование

Логи выводятся с уровнем `INFO` по умолчанию. Для изменения установите `LOG_LEVEL` в `.env`:
```env
LOG_LEVEL=DEBUG  # для детального логирования
```

## Troubleshooting

### Ошибка "TELEGRAM_BOT_TOKEN not found"

Убедитесь, что вы создали `.env` файл и добавили в него токен бота:
```env
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
```

### Бот не отвечает

1. Проверьте, что бот запущен и нет ошибок в консоли
2. Убедитесь, что токен бота корректный
3. Проверьте интернет-соединение

### Нет данных от биржи

Некоторые биржи могут быть временно недоступны. Бот продолжит работать с остальными биржами.

## License

MIT

## Автор

Создано с ❤️ для трейдеров
