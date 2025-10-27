# Как проверить почему MEXC не появляется в /top

## 1. Запустите бота с детальным логированием

В файле `bot.py` убедитесь что логирование установлено на INFO или DEBUG:

```python
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO  # или logging.DEBUG для еще большей детализации
)
```

## 2. Используйте команду /top

После запуска бота выполните команду `/top` в Telegram и смотрите в консоль.

## 3. Что искать в логах

### ✅ Успешное получение данных от MEXC:

```
INFO - Getting rates for BTC (Bybit rate: +0.5234%)...
DEBUG - MEXC: trying variants ['BTCUSDT', 'BTC_USDT', 'BTC-USDT', 'BTCUSDTM'] for BTC
DEBUG - MEXC: Getting rate for BTCUSDT -> BTC_USDT
DEBUG - MEXC: ✅ Got data from ticker for BTC_USDT: rate=0.0005, price=68234.5
INFO -   ✅ MEXC: BTC = +0.0500%
INFO -   -> Collected 3 rates for BTC
```

### ⚠️ MEXC не находит токен:

```
INFO - Getting rates for COAI (Bybit rate: +0.5068%)...
DEBUG - MEXC: trying variants ['COAIUSDT', 'COAI_USDT', 'COAI-USDT', 'COAIUSDTM'] for COAI
DEBUG - MEXC: Getting rate for COAIUSDT -> COAI_USDT
DEBUG - MEXC ticker failed for COAI_USDT: 404 Not Found
WARNING -   ⚠️  MEXC: No data for COAI (tried 4 variants)
```

**Это нормально!** MEXC может не иметь экзотических токенов которые есть у Bybit.

### ❌ Ошибка подключения к MEXC:

```
ERROR -   ❌ MEXC: Error for BTC: Connection timeout
```

**Решение:** Проверьте интернет или временно отключите MEXC.

## 4. Проверьте какие биржи активны

При команде `/top` бот должен написать:
```
🔄 Собираю данные от бирж: BYBIT, BINANCE, MEXC, GATE, KUCOIN...
```

Если MEXC нет в списке - проверьте `bot.py`, метод `_init_aggregator()`.

## 5. Тестирование MEXC отдельно

Запустите тест только для MEXC:

```bash
python test_mexc_only.py
```

Этот скрипт покажет:
- ✅ Работает ли MEXC API вообще
- ✅ Какие контракты доступны
- ✅ Получаются ли funding rates

## 6. Частые причины почему MEXC не появляется

### Причина 1: MEXC не имеет топовых токенов от Bybit

**Пример:** Bybit топ-5:
1. COAI - экзотический токен ❌ (MEXC не имеет)
2. SHELL - новый токен ❌ (MEXC не имеет)  
3. BTC - основной ✅ (MEXC имеет)
4. ETH - основной ✅ (MEXC имеет)
5. SOL - популярный ✅ (MEXC имеет)

**Результат:** MEXC появится только для BTC, ETH, SOL.

**Решение:** Это нормально! MEXC просто не торгует экзотическими токенами.

### Причина 2: MEXC API временно недоступен

**Проверка:**
```bash
curl "https://contract.mexc.com/api/v1/contract/detail"
```

Должен вернуть JSON с `"success": true`.

### Причина 3: Rate limiting

Если делаете много запросов подряд, MEXC может блокировать.

**Решение:** Подождите 1-2 минуты и попробуйте снова.

## 7. Что ожидать в идеальном случае

Для топового токена типа BTC, вы должны увидеть в таблице:

```
🔴 1. BTC 📈
💰 Цена: $68,234
┌──────────┬──────────┐
│Биржа     │ Rate     │
├──────────┼──────────┤
│BYBIT     │ +0.5234% │
│BINANCE   │ +0.5120% │
│MEXC      │ +0.4890% │ ← Вот он!
│GATE      │ +0.4567% │
│KUCOIN    │ +0.4234% │
└──────────┴──────────┘
```

## 8. Если MEXC все равно не появляется

1. ✅ Проверьте что MEXC в списке бирж (`bot.py`)
2. ✅ Запустите `python test_mexc_only.py`
3. ✅ Посмотрите логи при команде `/top`
4. ✅ Попробуйте команду `/token BTC` - должен показать MEXC
5. ✅ Проверьте что токен действительно есть на MEXC

Если все равно не работает - пришлите логи из консоли бота!

---

**💡 Совет:** MEXC обычно не имеет экзотических токенов. Если у Bybit в топе малоизвестные токены - это нормально что MEXC их не показывает.
