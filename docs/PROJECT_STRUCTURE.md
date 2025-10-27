# Project Structure 📁

## Обзор архитектуры

Проект построен на принципах **Clean Architecture**, **SOLID**, **KISS**, и **DRY**.

```
funding_bot/
│
├── 📄 bot.py                          # Главный файл телеграм-бота
├── 📄 models.py                       # Модели данных (FundingRate, ContractInfo)
├── 📄 config.py                       # Конфигурация приложения
│
├── 📁 exchanges/                      # Адаптеры для работы с биржами
│   ├── 📄 __init__.py                # Инициализация модуля
│   ├── 📄 base.py                    # Абстрактный базовый класс ExchangeAdapter
│   ├── 📄 binance_adapter.py         # Адаптер для Binance
│   ├── 📄 bybit_adapter.py           # Адаптер для Bybit
│   ├── 📄 mexc_adapter.py            # Адаптер для MEXC
│   ├── 📄 gateio_adapter.py          # Адаптер для Gate.io
│   ├── 📄 kucoin_adapter.py          # Адаптер для KuCoin
│   ├── 📄 bitget_adapter.py          # Адаптер для BitGet
│   └── 📄 bingx_adapter.py           # Адаптер для BingX
│
├── 📁 services/                       # Бизнес-логика
│   ├── 📄 __init__.py                # Инициализация модуля
│   ├── 📄 aggregator.py              # Агрегация данных от бирж
│   └── 📄 formatter.py               # Форматирование сообщений для Telegram
│
├── 📄 example_usage.py                # Примеры использования API
├── 📄 test_exchanges.py               # Тестирование адаптеров бирж
│
├── 📄 funding_rate_bybit.py           # Устаревший скрипт (обратная совместимость)
├── 📄 funding_rate_history.py         # Устаревший скрипт (обратная совместимость)
├── 📄 funding_rate.py                 # Устаревший скрипт (обратная совместимость)
│
├── 📄 requirements.txt                # Зависимости Python
├── 📄 .env                           # Переменные окружения (не в git)
├── 📄 .gitignore                     # Игнорируемые файлы
│
├── 📄 README.md                      # Полная документация
├── 📄 QUICKSTART.md                  # Быстрый старт
└── 📄 PROJECT_STRUCTURE.md           # Этот файл
```

---

## Слои архитектуры

### 1. **Модели данных** (`models.py`)

Чистые data-классы без бизнес-логики:

- `FundingRate` - представление ставки финансирования
- `ContractInfo` - информация о контракте

**Принципы:** Single Responsibility, простота

### 2. **Адаптеры бирж** (`exchanges/`)

Каждый адаптер реализует интерфейс `ExchangeAdapter`:

```python
class ExchangeAdapter(ABC):
    @abstractmethod
    def get_top_contracts(limit: int) -> List[ContractInfo]
    
    @abstractmethod
    def get_funding_rate(symbol: str) -> Optional[FundingRate]
    
    @abstractmethod
    def get_all_funding_rates() -> List[FundingRate]
```

**Принципы:** 
- Open/Closed (легко добавлять новые биржи)
- Liskov Substitution (все адаптеры взаимозаменяемы)
- Interface Segregation (минимальный интерфейс)

### 3. **Сервисный слой** (`services/`)

#### `FundingRateAggregator`
- Агрегация данных от множества бирж
- Параллельные запросы через ThreadPoolExecutor
- Группировка данных по токенам
- Обработка ошибок

#### `MessageFormatter`
- Форматирование алертов
- Генерация таблиц
- Отображение статистики

**Принципы:** 
- Single Responsibility
- DRY (переиспользование логики)
- Dependency Inversion (зависимость от абстракций)

### 4. **Телеграм-бот** (`bot.py`)

- Обработка команд пользователя
- Управление мониторингом
- Отправка алертов
- Хранение пользовательских настроек

**Принципы:** 
- Separation of Concerns
- Single Responsibility

---

## Диаграмма взаимодействия

```
┌─────────────┐
│   Telegram  │
│     Bot     │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────┐
│  FundingRateAggregator      │
│  (services/aggregator.py)   │
└──────────┬──────────────────┘
           │
           ├─────────┬─────────┬─────────┬─────────┐
           ▼         ▼         ▼         ▼         ▼
      ┌─────┐   ┌─────┐   ┌─────┐   ┌─────┐   ┌─────┐
      │Bybit│   │Binance   │MEXC │   │Gate │   │ ... │
      └─────┘   └─────┘   └─────┘   └─────┘   └─────┘
       ExchangeAdapter implementations
```

---

## Паттерны проектирования

### 1. **Adapter Pattern**
Каждая биржа имеет свой адаптер, приводящий API к единому интерфейсу.

### 2. **Strategy Pattern**
Разные стратегии получения данных для разных бирж.

### 3. **Factory Pattern** (неявный)
Создание адаптеров бирж в `bot.py` и `example_usage.py`.

### 4. **Template Method** (в `base.py`)
Базовая реализация `is_available()` с возможностью переопределения.

---

## Принципы SOLID

### ✅ Single Responsibility
- `ExchangeAdapter` - только работа с API биржи
- `FundingRateAggregator` - только агрегация данных
- `MessageFormatter` - только форматирование
- `FundingBot` - только Telegram логика

### ✅ Open/Closed
- Легко добавить новую биржу без изменения существующего кода
- Просто расширить функциональность через наследование

### ✅ Liskov Substitution
- Любой `ExchangeAdapter` может заменить другой
- Все адаптеры работают одинаково для агрегатора

### ✅ Interface Segregation
- Минимальный интерфейс `ExchangeAdapter`
- Клиенты не зависят от неиспользуемых методов

### ✅ Dependency Inversion
- `FundingRateAggregator` зависит от абстракции `ExchangeAdapter`
- Не зависит от конкретных реализаций бирж

---

## Принципы KISS и DRY

### KISS (Keep It Simple, Stupid)
- Простые, понятные имена функций
- Минимум вложенности
- Прямолинейная логика
- Ясная структура

### DRY (Don't Repeat Yourself)
- Базовый класс `ExchangeAdapter` с общей логикой
- Переиспользование `_get_symbol_variants()`
- Единая конфигурация в `config.py`
- Общие утилиты в сервисном слое

---

## Расширяемость

### Добавление новой биржи

1. Создайте файл `exchanges/newexchange_adapter.py`
2. Наследуйтесь от `ExchangeAdapter`
3. Реализуйте 3 метода
4. Добавьте в `exchanges/__init__.py`
5. Добавьте в `bot.py` в список бирж

**Время: ~30 минут**

### Добавление новой команды бота

1. Создайте метод в `FundingBot`
2. Зарегистрируйте CommandHandler в `run()`

**Время: ~10 минут**

### Добавление нового формата сообщений

1. Добавьте метод в `MessageFormatter`
2. Используйте в боте или примерах

**Время: ~15 минут**

---

## Тестирование

### Ручное тестирование

```bash
# Тест всех бирж
python test_exchanges.py

# Быстрый тест
python test_exchanges.py --quick

# Примеры использования
python example_usage.py
```

### Автоматическое тестирование

Для production рекомендуется добавить:
- Unit тесты для каждого адаптера
- Integration тесты для агрегатора
- Mock тесты для Telegram бота

---

## Безопасность

### ✅ Реализовано
- Переменные окружения для токенов
- `.gitignore` для `.env`
- Обработка ошибок API

### 🔄 Рекомендации
- Rate limiting для API запросов
- Validation входных данных пользователя
- Logging чувствительных операций

---

## Производительность

### Оптимизации
- ✅ Параллельные запросы к биржам (ThreadPoolExecutor)
- ✅ Настраиваемое количество воркеров
- ✅ Timeout для HTTP запросов
- ✅ Cooldown для алертов

### Метрики
- ~2-3 секунды для получения данных от одной биржи
- ~5-10 секунд для агрегации от всех бирж (параллельно)
- Мониторинг каждые 10 минут (настраивается)

---

## Логирование

Структурированное логирование на всех уровнях:
- `INFO` - основные события
- `WARNING` - неожиданные ситуации
- `ERROR` - ошибки API и обработка
- `DEBUG` - детальная информация (в разработке)

---

## Roadmap

### Версия 1.0 ✅ (текущая)
- Поддержка 7 бирж
- Телеграм-бот с алертами
- Группировка по токенам
- Настраиваемые пороги

### Версия 1.1 (планируется)
- [ ] Веб-интерфейс для настройки
- [ ] База данных для истории
- [ ] Графики изменения ставок
- [ ] Множественные пороги для разных токенов

### Версия 2.0 (в планах)
- [ ] Арбитражные сигналы
- [ ] Machine Learning для предсказаний
- [ ] Интеграция с торговыми ботами
- [ ] Multi-user support

---

**Разработано с ❤️ для трейдеров**
