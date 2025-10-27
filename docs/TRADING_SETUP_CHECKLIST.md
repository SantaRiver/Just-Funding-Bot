# ✅ Чеклист для настройки автоматической торговли

## 🎯 Краткое резюме

**Сейчас у вас есть:**
- ✅ Система мониторинга funding rates
- ✅ Поиск возможностей для хеджирования (`/hedge`)
- ✅ Красивые отчеты и аналитику

**Чтобы реально торговать, нужно:**
1. Получить API ключи от бирж
2. Реализовать торговые методы в адаптерах
3. Создать торговый сервис
4. Добавить систему управления рисками
5. Протестировать на testnet
6. Запустить с минимальным капиталом

---

## 📋 Пошаговый план

### ШАГ 1: Получить API ключи (30 минут)

#### Bybit
1. Зарегистрироваться на https://testnet.bybit.com (для тестов)
2. Перейти в API Management
3. Создать новый API ключ:
   - ✅ Включить: `Read` + `Contract Trade`
   - ❌ НЕ включать: `Withdrawal`
   - Привязать к IP (опционально)
4. Скопировать **API Key** и **API Secret**

#### Binance
1. Зарегистрироваться на https://testnet.binancefuture.com
2. Создать API ключ:
   - ✅ Включить: `Enable Reading` + `Enable Futures`
   - ❌ НЕ включать: `Enable Withdrawals`
3. Скопировать ключи

#### Сохранить в `.env`:
```env
# Bybit Testnet
BYBIT_API_KEY=ваш_ключ
BYBIT_API_SECRET=ваш_секрет
BYBIT_TESTNET=true

# Binance Testnet
BINANCE_API_KEY=ваш_ключ
BINANCE_API_SECRET=ваш_секрет
BINANCE_TESTNET=true
```

⚠️ **НЕ коммитить .env в Git!**

---

### ШАГ 2: Реализовать торговые адаптеры (2-3 дня)

У вас уже есть шаблоны:
- ✅ `exchanges/base_trading.py` - базовый класс
- ✅ `exchanges/bybit_trading_adapter.py` - пример для Bybit

**Что делать:**

1. **Скопировать и адаптировать для каждой биржи**:
   ```
   exchanges/
   ├── bybit_trading_adapter.py    ✅ Готов
   ├── binance_trading_adapter.py  ⚠️ Нужно создать
   ├── mexc_trading_adapter.py     ⚠️ Нужно создать
   └── gateio_trading_adapter.py   ⚠️ Нужно создать
   ```

2. **Реализовать методы для каждой биржи**:
   - `get_account_balance()` - баланс
   - `get_position()` - текущая позиция
   - `set_leverage()` - установить плечо
   - `open_market_position()` - открыть позицию
   - `close_position()` - закрыть позицию
   - `get_order_book()` - стакан
   - `_generate_signature()` - подпись для API

3. **Изучить документацию API каждой биржи**:
   - Bybit: https://bybit-exchange.github.io/docs/v5/intro
   - Binance: https://binance-docs.github.io/apidocs/futures/en/
   - MEXC: https://mexcdevelop.github.io/apidocs/contract_v1_en/
   - Gate.io: https://www.gate.io/docs/developers/apiv4/

---

### ШАГ 3: Создать торговый сервис (1-2 дня)

**Файл**: `services/trading.py`

Уже есть шаблон в документации (`AUTO_TRADING_REQUIREMENTS.md`).

**Основные методы**:

```python
class TradingService:
    async def execute_hedge(
        opportunity: Dict,
        position_size_usd: float,
        leverage: int,
        dry_run: bool = True
    ) -> HedgePosition
    
    async def close_hedge(position: HedgePosition)
    
    async def monitor_positions() -> List[HedgePosition]
```

**Что он делает:**
1. Проверяет балансы на обеих биржах
2. Проверяет ликвидность
3. Открывает LONG на одной бирже
4. Открывает SHORT на другой бирже
5. Мониторит позиции
6. Закрывает при достижении условий

---

### ШАГ 4: Система управления рисками (1 день)

**Файл**: `services/risk_management.py`

**Лимиты для начала**:
```python
RiskLimits(
    max_position_size_usd=100,      # Макс $100 на позицию
    max_leverage=2,                  # Макс 2x плечо
    max_total_exposure_usd=500,      # Макс $500 всего
    min_spread_pct=0.5,              # Мин 0.5% спред
    max_positions=3                  # Макс 3 позиции одновременно
)
```

**Проверки перед открытием**:
- ✅ Достаточно баланса?
- ✅ Плечо в пределах лимита?
- ✅ Не превышена общая экспозиция?
- ✅ Спред достаточно большой?
- ✅ Достаточно ликвидности?

---

### ШАГ 5: Добавить команды в бота (полдня)

**В `bot.py`**:

```python
# Команды для торговли (только для админа!)

@admin_only
async def execute_hedge_command():
    """Выполнить хедж: /execute_hedge BTC 100 2 true"""
    # token, size_usd, leverage, dry_run
    pass

@admin_only
async def list_positions_command():
    """Показать открытые позиции: /positions"""
    pass

@admin_only
async def close_position_command():
    """Закрыть позицию: /close_position BTC"""
    pass

@admin_only
async def account_status_command():
    """Баланс на биржах: /account_status"""
    pass
```

---

### ШАГ 6: Тестирование на Testnet (2-4 недели)

**КРИТИЧЕСКИ ВАЖНО**: НЕ пропускайте этот шаг!

#### План тестирования:

**Неделя 1: Базовые функции**
- [ ] Проверить баланс через API
- [ ] Установить плечо
- [ ] Открыть LONG позицию (малый размер)
- [ ] Закрыть позицию
- [ ] Открыть SHORT позицию
- [ ] Проверить расчет PnL

**Неделя 2: Хедж стратегия**
- [ ] Найти возможность через `/hedge`
- [ ] Открыть хедж вручную (малый размер)
- [ ] Подождать funding time
- [ ] Проверить получение funding
- [ ] Закрыть хедж
- [ ] Рассчитать реальную прибыль

**Неделя 3: Автоматизация**
- [ ] Автоматическое открытие хеджа
- [ ] Мониторинг позиций
- [ ] Автоматическое закрытие
- [ ] Обработка ошибок
- [ ] Логирование всех операций

**Неделя 4: Стресс-тесты**
- [ ] Высокая волатильность
- [ ] Низкая ликвидность
- [ ] Сбои API
- [ ] Одновременно несколько позиций
- [ ] Граничные случаи

**Метрики успеха**:
- ✅ Все тесты пройдены без критических ошибок
- ✅ Funding получается корректно
- ✅ PnL соответствует ожиданиям
- ✅ Логи понятны и полезны

---

### ШАГ 7: Mainnet с минимальным капиталом (1 месяц+)

**ТОЛЬКО после успешного testnet!**

#### Первый запуск:

**Капитал**: $100-500 (что можете позволить потерять)

**Настройки**:
```env
BYBIT_TESTNET=false  # ВНИМАНИЕ: реальные деньги!
BINANCE_TESTNET=false

MAX_POSITION_SIZE_USD=50    # Начинайте с малого
MAX_LEVERAGE=1              # Без плеча!
MAX_TOTAL_EXPOSURE_USD=200
MIN_SPREAD_PCT=0.8          # Только очень выгодные
```

**Первая неделя**:
- Ручное открытие каждого хеджа
- Проверка каждые 2 часа
- Детальный анализ каждой сделки

**Если все ОК, постепенно**:
- Увеличить размер позиций
- Добавить автоматизацию
- Увеличить количество позиций

**Никогда не**:
- ❌ Использовать все деньги сразу
- ❌ Ставить плечо >3x для хеджа
- ❌ Оставлять без присмотра надолго
- ❌ Игнорировать предупреждения системы

---

## 🔧 Технические требования

### Зависимости

Добавить в `requirements.txt`:
```
# Уже есть
python-telegram-bot>=20.0
httpx>=0.24.0
python-dotenv>=1.0.0

# Нужно добавить для торговли
cryptography>=41.0.0  # Для шифрования API ключей
```

### Структура файлов

```
funding_bot/
├── exchanges/
│   ├── base.py                      # ✅ Есть (read-only)
│   ├── base_trading.py              # ✅ Создан (для торговли)
│   ├── bybit_adapter.py             # ✅ Есть (read-only)
│   ├── bybit_trading_adapter.py     # ✅ Создан (с торговлей)
│   ├── binance_trading_adapter.py   # ⚠️ НУЖНО СОЗДАТЬ
│   ├── mexc_trading_adapter.py      # ⚠️ НУЖНО СОЗДАТЬ
│   └── ...
├── services/
│   ├── aggregator.py                # ✅ Есть
│   ├── formatter.py                 # ✅ Есть
│   ├── trading.py                   # ⚠️ НУЖНО СОЗДАТЬ
│   └── risk_management.py           # ⚠️ НУЖНО СОЗДАТЬ
├── docs/
│   ├── AUTO_TRADING_REQUIREMENTS.md # ✅ Создан (детальная документация)
│   ├── HEDGING_GUIDE.md             # ✅ Есть
│   └── ...
├── bot.py                           # ⚠️ Добавить торговые команды
├── .env                             # ⚠️ Добавить API ключи
└── requirements.txt                 # ⚠️ Добавить зависимости
```

---

## ⏱️ Оценка времени

| Этап | Время | Сложность |
|------|-------|-----------|
| Получить API ключи | 30 мин | ⭐ |
| Реализовать Bybit adapter | 1 день | ⭐⭐⭐ |
| Реализовать Binance adapter | 1 день | ⭐⭐⭐ |
| Создать торговый сервис | 2 дня | ⭐⭐⭐⭐ |
| Система рисков | 1 день | ⭐⭐ |
| Добавить команды в бота | 0.5 дня | ⭐ |
| Тестирование testnet | 2-4 недели | ⭐⭐⭐⭐⭐ |
| **ИТОГО до mainnet** | **~1 месяц** | |

---

## 📚 Полезные ресурсы

### Документация API

- **Bybit**: https://bybit-exchange.github.io/docs/v5/intro
- **Binance Futures**: https://binance-docs.github.io/apidocs/futures/en/
- **MEXC**: https://mexcdevelop.github.io/apidocs/contract_v1_en/
- **Gate.io**: https://www.gate.io/docs/developers/apiv4/

### Testnet биржи

- **Bybit Testnet**: https://testnet.bybit.com
- **Binance Futures Testnet**: https://testnet.binancefuture.com

### Внутренняя документация

- `docs/AUTO_TRADING_REQUIREMENTS.md` - детальные требования
- `docs/HEDGING_GUIDE.md` - руководство по хеджированию
- `exchanges/base_trading.py` - базовый торговый класс
- `exchanges/bybit_trading_adapter.py` - пример реализации

---

## ⚠️ ВАЖНЫЕ НАПОМИНАНИЯ

### ДО начала торговли:

1. ✅ **Протестировать ВСЕ на testnet минимум 2 недели**
2. ✅ **Начинать с минимального капитала ($100-500)**
3. ✅ **Использовать низкое плечо (1x-2x) или без плеча**
4. ✅ **Настроить систему рисков и лимиты**
5. ✅ **Проверить все расчеты вручную**
6. ✅ **Убедиться в наличии логирования**

### НИКОГДА не делайте:

1. ❌ **НЕ использовать mainnet без тестов на testnet**
2. ❌ **НЕ ставить высокое плечо (>5x) для хеджа**
3. ❌ **НЕ вкладывать деньги, которые не можете потерять**
4. ❌ **НЕ коммитить API ключи в Git**
5. ❌ **НЕ включать разрешение Withdrawal для API**
6. ❌ **НЕ оставлять без мониторинга надолго**

---

## 🆘 Нужна помощь?

Если застряли на каком-то этапе:

1. **Проверьте логи**: `logs/bot.log` и `logs/trades.log`
2. **Читайте документацию API** биржи
3. **Тестируйте на testnet**, не спешите на mainnet
4. **Начинайте с малого**, увеличивайте постепенно

---

**Удачи! Торгуйте безопасно! 🚀💎**
