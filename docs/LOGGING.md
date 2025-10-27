# Система логирования

## Обзор

Бот использует детальную систему логирования для отслеживания всех запросов к биржам и их ответов.

## Уровни логирования

### INFO (по умолчанию)
Показывает основную информацию о работе бота:
- Запуск команд пользователями
- Начало/завершение сбора данных
- Успешные ответы от бирж
- Сводную статистику по токенам
- Общий процент успеха

**Пример вывода:**
```
================================================================================
🔥 /top command from user 123456 in chat 123456
================================================================================
📡 Активных бирж: 9
📋 Список бирж: BYBIT, BINANCE, MEXC, GATE, KUCOIN, BITGET, BINGX, BITMART, OKX
🚀 Начинаю сбор данных...

============================================================
📊 Getting rates for BTC (Bybit rate: +0.0234%)
============================================================
🚀 Запрашиваю данные от 8 бирж: BINANCE, MEXC, GATE, KUCOIN, BITGET, BINGX, BITMART, OKX
  ✅ BINANCE: BTC = +0.0230% (symbol: BTCUSDT, 0.34s)
  ✅ MEXC: BTC = +0.0228% (symbol: BTC_USDT, 0.45s)
  ⚠️  GATE: No data for BTC after trying 4 variants (0.67s)
  ✅ KUCOIN: BTC = +0.0231% (symbol: BTCUSDTM, 0.52s)

📈 СВОДКА по BTC:
  ✅ Успешно: 7 бирж (включая BYBIT)
  ⚠️  Нет данных: 2 бирж
  ❌ Ошибки: 0 бирж
  📊 Всего собрано: 7 из 9 бирж
  🏆 Топ-3 ставки:
     1. BYBIT: +0.0234%
     2. BINANCE: +0.0230%
     3. KUCOIN: +0.0231%

⏱️  ИТОГО: Сбор данных завершен за 2.34s
✅ Общий успех: 35/45 (77.8%)
```

### DEBUG (детальное логирование)
Показывает всю техническую информацию:
- Все HTTP запросы и ответы
- Попытки подбора формата символов
- Трассировки стека при ошибках
- Детали кэширования

**Использование:**
```python
# В bot.py измените:
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG  # Было: logging.INFO
)
```

**Дополнительный вывод:**
```
[BINANCE] → GET https://fapi.binance.com/fapi/v1/premiumIndex?symbol=BTCUSDT
[BINANCE] ← 200 https://fapi.binance.com/fapi/v1/premiumIndex?symbol=BTCUSDT
🔍 MEXC: trying variants ['BTCUSDT', 'BTC_USDT', 'BTC-USDT', 'BTCUSDTM'] for BTC
  ⚪ MEXC: No data for BTCUSDT (attempt 1/4)
  ⚪ MEXC: No data for BTC-USDT (attempt 3/4)
[GATE] ← 404 https://api.gateio.ws/api/v4/futures/usdt/contracts/BTC_USDT - Client error
[GATE] Response body: {"error":"contract not found"}...
```

### WARNING
Показывает предупреждения:
- Биржи без данных
- Истекшие кэши
- Некорректные конфигурации

### ERROR
Показывает только ошибки:
- Исключения при запросах
- HTTP ошибки 4xx/5xx
- Проблемы с подключением

## Что логируется

### 1. HTTP запросы (DEBUG)
```
[BYBIT] → GET https://api.bybit.com/v5/market/tickers?category=linear
[BYBIT] ← 200 https://api.bybit.com/v5/market/tickers?category=linear
```

### 2. Успешные ответы (INFO)
```
✅ BINANCE: BTC = +0.0230% (symbol: BTCUSDT, 0.34s)
```
- Биржа
- Токен
- Ставка финансирования
- Использованный формат символа
- Время выполнения

### 3. Отсутствие данных (WARNING)
```
⚠️  GATE: No data for BTC after trying 4 variants (0.67s)
```
- Биржа не имеет этого токена
- Все варианты символов были опробованы

### 4. Ошибки (ERROR)
```
❌ BITGET: Error for BTC: HTTPStatusError: 404 Not Found (0.89s)
  Stack trace:
  ...
```
- Тип исключения
- Сообщение об ошибке
- Трассировка стека (в DEBUG режиме)

### 5. Сводная статистика (INFO)
```
📈 СВОДКА по BTC:
  ✅ Успешно: 7 бирж
  ⚠️  Нет данных: 2 бирж
  ❌ Ошибки: 0 бирж
  📊 Всего собрано: 7 из 9 бирж
```

### 6. Итоговая статистика (INFO)
```
📊 Статистика по токенам:
   • BTC: 7/9 бирж ответили
   • ETH: 8/9 бирж ответили
   • SOL: 6/9 бирж ответили

✅ Общий успех: 35/45 (77.8%)
⏱️  ИТОГО: Сбор данных завершен за 2.34s
```

## Настройка логирования

### Лог-файлы

Бот автоматически записывает логи в директорию `logs/`:

#### **logs/bot.log**
- Основной лог-файл (уровень INFO и выше)
- Максимальный размер: 10 MB
- Автоматическая ротация (сохраняется 5 последних файлов)
- Содержит: все операции, HTTP-запросы, статистику

#### **logs/errors.log**
- Только ошибки (уровень ERROR)
- Максимальный размер: 5 MB
- Автоматическая ротация (сохраняется 3 последних файла)
- Содержит: исключения, HTTP ошибки, stack traces

### Ротация логов

При достижении максимального размера:
```
bot.log        → bot.log.1
bot.log.1      → bot.log.2
bot.log.2      → bot.log.3
bot.log.3      → bot.log.4
bot.log.4      → bot.log.5
bot.log.5      → удаляется
```

### Изменение уровня логирования
В `bot.py` (строка 71-73):
```python
logging.basicConfig(
    level=logging.INFO,  # Измените на DEBUG для детального логирования
    handlers=[main_handler, error_handler, console_handler]
)
```

### Изменение размера файлов
В `bot.py` (строка 46-50):
```python
main_handler = RotatingFileHandler(
    logs_dir / "bot.log",
    maxBytes=10*1024*1024,  # Измените на нужный размер
    backupCount=5,          # Количество резервных копий
    encoding='utf-8'
)
```

### Отключение логов от сторонних библиотек
```python
# После basicConfig добавьте:
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)
```

## Анализ логов

### Структура директории logs/
```
logs/
├── bot.log          # Текущий основной лог
├── bot.log.1        # Предыдущий лог (после ротации)
├── bot.log.2
├── bot.log.3
├── bot.log.4
├── bot.log.5
├── errors.log       # Текущий лог ошибок
├── errors.log.1
├── errors.log.2
└── errors.log.3
```

### Найти проблемные биржи
```powershell
# Windows PowerShell
Select-String "❌" logs\bot.log | Select-Object -Last 20

# Или в errors.log
Get-Content logs\errors.log -Tail 50
```

```bash
# Linux/Mac
grep "❌" logs/bot.log | tail -20

# Или в errors.log
tail -50 logs/errors.log
```

### Посмотреть статистику успеха
```powershell
# Windows PowerShell
Select-String "Общий успех" logs\bot.log

# Последние 10 результатов
Select-String "Общий успех" logs\bot.log | Select-Object -Last 10
```

```bash
# Linux/Mac
grep "Общий успех" logs/bot.log

# Последние 10 результатов
grep "Общий успех" logs/bot.log | tail -10
```

### Найти медленные биржи (>2s)
```powershell
# Windows PowerShell
Select-String "✅" logs\bot.log | Select-String "[2-9]\.\d+s\)"
```

```bash
# Linux/Mac
grep "✅" logs/bot.log | grep -E "[2-9]\.[0-9]+s\)"
```

### Мониторинг логов в реальном времени
```powershell
# Windows PowerShell
Get-Content logs\bot.log -Wait -Tail 50
```

```bash
# Linux/Mac
tail -f logs/bot.log
```

### Анализ только ошибок
```powershell
# Windows PowerShell
Get-Content logs\errors.log

# Группировать по типу ошибки
Select-String "Error for" logs\errors.log | Group-Object Line
```

```bash
# Linux/Mac
cat logs/errors.log

# Группировать по типу ошибки
grep "Error for" logs/errors.log | sort | uniq -c
```

### Поиск по дате/времени
```powershell
# Windows PowerShell - логи за сегодня после 20:00
$today = Get-Date -Format "yyyy-MM-dd"
Select-String "$today 2[0-9]:" logs\bot.log
```

```bash
# Linux/Mac - логи за сегодня после 20:00
TODAY=$(date +%Y-%m-%d)
grep "$TODAY 2[0-9]:" logs/bot.log
```

## Интерпретация результатов

### ✅ Биржа работает отлично
```
✅ BINANCE: BTC = +0.0230% (symbol: BTCUSDT, 0.34s)
```
- Быстрый ответ (<1s)
- Корректные данные

### ⚠️  Биржа не имеет токена (нормально)
```
⚠️  MEXC: No data for OBSCURETOKEN after trying 4 variants (0.45s)
```
- Экзотические токены могут отсутствовать на малых биржах

### ❌ Проблема с биржей (требует внимания)
```
❌ BITGET: Error for BTC: ConnectionTimeout (10.00s)
```
- Биржа недоступна
- Превышен таймаут
- Проблемы с API

### 404 Not Found (проверить адаптер)
```
[GATE] ← 404 https://api.gateio.ws/api/v4/futures/usdt/contracts/BTC - Client error
```
- Неправильный формат символа
- Устаревший endpoint
- Требуется обновление адаптера

## Troubleshooting

### Слишком много логов
Уменьшите уровень до WARNING или ERROR

### Не вижу детали ошибок
Увеличьте уровень до DEBUG

### Логи не пишутся в файл
Проверьте права доступа к директории

### Хочу логировать только определенные биржи
```python
# После basicConfig:
logging.getLogger("exchanges.bitget_adapter").setLevel(logging.DEBUG)
logging.getLogger("exchanges.okx_adapter").setLevel(logging.DEBUG)
```
