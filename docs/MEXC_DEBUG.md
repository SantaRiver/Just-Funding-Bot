# Диагностика проблем с MEXC

## Быстрая проверка

Запустите тестовый скрипт:

```bash
python test_mexc_only.py
```

Этот скрипт проверит:
1. ✅ Прямые запросы к MEXC API
2. ✅ Получение списка контрактов
3. ✅ Получение funding rate для конкретного символа
4. ✅ Получение всех funding rates

## Возможные проблемы и решения

### Проблема 1: API вернул пустой список контрактов

**Симптомы:**
- `Data items: 0` в тесте API
- Контракты не найдены

**Решение:**
- Возможно, MEXC изменил API endpoint
- Проверьте актуальную документацию: https://mxcdevelop.github.io/APIDoc/

### Проблема 2: Funding rate не найден для символа

**Симптомы:**
- `Success: False` в ответе API
- Funding rate не получен

**Возможные причины:**
1. Неправильный формат символа (попробуйте: `BTC_USDT`, `BTCUSDT`, `BTC-USDT`)
2. API требует аутентификации
3. Rate limiting

**Решение:**
```python
# В test_mexc_only.py будут автоматически проверены разные форматы
```

### Проблема 3: Таймауты или медленные запросы

**Симптомы:**
- Долгое выполнение `get_all_funding_rates`
- Timeout errors

**Решение:**
Уже исправлено в обновленном коде:
- ✅ Параллельные запросы через `asyncio.gather`
- ✅ Ограничение до 30 контрактов
- ✅ Timeout 5 секунд на запрос

### Проблема 4: "success": false в ответе

**Возможные причины:**
1. API endpoint изменился
2. Требуется API key
3. Геоблокировка

**Решение:**
Проверьте вывод `test_mexc_api_direct()` - он покажет точный ответ от API.

## Логирование

Для детального логирования установите уровень DEBUG в bot.py:

```python
logging.basicConfig(level=logging.DEBUG)
```

## Альтернативное решение

Если MEXC не работает, можно временно отключить его в `bot.py`:

```python
def _init_aggregator(self) -> FundingRateAggregator:
    exchanges = [
        BybitAdapter(),
        BinanceAdapter(),
        # MexcAdapter(),  # Временно отключено
        GateioAdapter(),
        KucoinAdapter(),
    ]
    return FundingRateAggregator(exchanges)
```

## Проверка текущего статуса MEXC API

```bash
curl -X GET "https://contract.mexc.com/api/v1/contract/detail"
```

Должен вернуть JSON с `"success": true` и списком контрактов.

## Известные особенности MEXC API

1. **Формат символов**: `BTC_USDT` (с подчеркиванием)
2. **Funding period**: Каждые 8 часов (00:00, 08:00, 16:00 UTC)
3. **Rate limiting**: ~120 запросов в минуту
4. **Требует User-Agent**: Уже настроено в адаптере

## Обновленные улучшения в адаптере

✅ **Версия 2.0** (25.10.2025):
- Параллельные запросы (asyncio.gather)
- Fallback механизм (ticker → funding_rate)
- Timeout handling (5 сек)
- Детальное логирование
- Обработка разных форматов символов

## Контакты для поддержки

Если проблема сохраняется после всех проверок:
1. Проверьте логи бота
2. Запустите `test_mexc_only.py`
3. Проверьте вывод прямых API запросов
4. Сообщите результаты для диагностики
