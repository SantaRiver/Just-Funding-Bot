"""Тест только для MEXC - диагностика проблем."""
import asyncio
import logging

from exchanges.mexc_adapter import MexcAdapter

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG  # DEBUG уровень для детального логирования
)
logger = logging.getLogger(__name__)


async def test_mexc_contracts():
    """Тест получения контрактов."""
    print("\n" + "="*80)
    print("ТЕСТ 1: Получение контрактов от MEXC")
    print("="*80 + "\n")
    
    mexc = MexcAdapter()
    
    try:
        contracts = await mexc.get_top_contracts(limit=10)
        print(f"✅ Получено контрактов: {len(contracts)}\n")
        
        if contracts:
            print("Первые 5 контрактов:")
            for i, contract in enumerate(contracts[:5], 1):
                print(f"  {i}. {contract.symbol} ({contract.base_currency})")
        else:
            print("⚠️  Контракты не найдены")
            
        await mexc.close()
        return contracts
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        await mexc.close()
        return []


async def test_mexc_funding_rate(symbol='BTC_USDT'):
    """Тест получения funding rate для конкретного символа."""
    print("\n" + "="*80)
    print(f"ТЕСТ 2: Получение funding rate для {symbol}")
    print("="*80 + "\n")
    
    mexc = MexcAdapter()
    
    try:
        rate = await mexc.get_funding_rate(symbol)
        
        if rate:
            print(f"✅ Funding rate получен!")
            print(f"   Символ: {rate.symbol}")
            print(f"   Ставка: {rate.rate_percentage:+.4f}%")
            print(f"   Цена: ${rate.price:.2f}")
            print(f"   Следующий funding: {rate.next_funding_time}")
        else:
            print(f"⚠️  Funding rate не получен для {symbol}")
            
            # Пробуем другие варианты
            print("\nПробуем альтернативные форматы...")
            for alt_symbol in ['BTCUSDT', 'BTC-USDT', 'BTCUSD']:
                print(f"  Пробую: {alt_symbol}")
                alt_rate = await mexc.get_funding_rate(alt_symbol)
                if alt_rate:
                    print(f"  ✅ Успех с {alt_symbol}!")
                    rate = alt_rate
                    break
                    
        await mexc.close()
        return rate
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        await mexc.close()
        return None


async def test_mexc_all_rates():
    """Тест получения всех funding rates."""
    print("\n" + "="*80)
    print("ТЕСТ 3: Получение всех funding rates")
    print("="*80 + "\n")
    
    mexc = MexcAdapter()
    
    try:
        print("🔄 Получаю данные (может занять ~10-15 сек)...\n")
        rates = await mexc.get_all_funding_rates()
        
        print(f"✅ Получено ставок: {len(rates)}\n")
        
        if rates:
            # Сортируем по абсолютной ставке
            rates.sort(key=lambda x: x.abs_rate, reverse=True)
            
            print("Топ-5 по абсолютной ставке:")
            for i, rate in enumerate(rates[:5], 1):
                print(f"  {i}. {rate.symbol}: {rate.rate_percentage:+.4f}% (${rate.price:.2f})")
        else:
            print("⚠️  Не получено ни одной ставки")
            
        await mexc.close()
        return rates
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        await mexc.close()
        return []


async def test_mexc_api_direct():
    """Прямой тест MEXC API."""
    print("\n" + "="*80)
    print("ТЕСТ 4: Прямой запрос к MEXC API")
    print("="*80 + "\n")
    
    import httpx
    
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            # Тест 1: Contract detail
            print("1. Проверка /api/v1/contract/detail...")
            url1 = "https://contract.mexc.com/api/v1/contract/detail"
            resp1 = await client.get(url1)
            data1 = resp1.json()
            print(f"   Status: {resp1.status_code}")
            print(f"   Success: {data1.get('success')}")
            print(f"   Data items: {len(data1.get('data', []))}")
            
            # Тест 2: Ticker для BTC_USDT
            print("\n2. Проверка /api/v1/contract/ticker/BTC_USDT...")
            url2 = "https://contract.mexc.com/api/v1/contract/ticker/BTC_USDT"
            resp2 = await client.get(url2)
            data2 = resp2.json()
            print(f"   Status: {resp2.status_code}")
            print(f"   Success: {data2.get('success')}")
            if data2.get('success'):
                ticker_data = data2.get('data', {})
                print(f"   Funding rate: {ticker_data.get('fundingRate')}")
                print(f"   Last price: {ticker_data.get('lastPrice')}")
            
            # Тест 3: Funding rate
            print("\n3. Проверка /api/v1/contract/funding_rate/BTC_USDT...")
            url3 = "https://contract.mexc.com/api/v1/contract/funding_rate/BTC_USDT"
            resp3 = await client.get(url3)
            data3 = resp3.json()
            print(f"   Status: {resp3.status_code}")
            print(f"   Success: {data3.get('success')}")
            if data3.get('success'):
                print(f"   Funding rate: {data3.get('data', {}).get('fundingRate')}")
                
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """Запуск всех тестов."""
    print("\n" + "="*80)
    print(" ДИАГНОСТИКА MEXC АДАПТЕРА")
    print("="*80)
    
    # Тест прямых запросов к API
    await test_mexc_api_direct()
    
    # Тест контрактов
    contracts = await test_mexc_contracts()
    
    # Тест funding rate
    if contracts:
        # Берем первый контракт для теста
        test_symbol = contracts[0].symbol
        await test_mexc_funding_rate(test_symbol)
    else:
        await test_mexc_funding_rate('BTC_USDT')
    
    # Тест всех rates
    await test_mexc_all_rates()
    
    print("\n" + "="*80)
    print(" ДИАГНОСТИКА ЗАВЕРШЕНА")
    print("="*80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
