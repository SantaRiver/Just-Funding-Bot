"""Тестовый скрипт для проверки async адаптеров бирж."""
import asyncio
import logging

from exchanges import (
    BybitAdapter,
    BinanceAdapter,
    MexcAdapter,
    GateioAdapter,
    KucoinAdapter,
)
from services.aggregator import FundingRateAggregator


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def test_single_exchange(exchange, symbol='BTCUSDT'):
    """Тест одной биржи."""
    print(f"\n{'='*80}")
    print(f"Тестирование: {exchange.name}")
    print(f"{'='*80}")
    
    try:
        # Тест 1: Получение funding rate для BTC
        print(f"\n[1] Получение funding rate для {symbol}...")
        rate = await exchange.get_funding_rate(symbol)
        
        if rate:
            print(f"✅ Успешно!")
            print(f"   Символ: {rate.symbol}")
            print(f"   Ставка: {rate.rate_percentage:+.4f}%")
            print(f"   Цена: ${rate.price:.2f}")
            print(f"   Следующий funding: {rate.next_funding_time}")
        else:
            print(f"⚠️  Не удалось получить данные")
        
        # Закрываем клиент
        await exchange.close()
        
        return rate is not None
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        await exchange.close()
        return False


async def test_aggregator():
    """Тест агрегатора с группировкой по токенам."""
    print(f"\n{'='*80}")
    print("ТЕСТ АГРЕГАТОРА - Топ-5 токенов с ближайшим funding")
    print(f"{'='*80}\n")
    
    exchanges = [
        BybitAdapter(),
        BinanceAdapter(),
        MexcAdapter(),
        GateioAdapter(),
        KucoinAdapter(),
    ]
    
    aggregator = FundingRateAggregator(exchanges)
    
    try:
        # Получаем топ-5 токенов
        print("🔄 Получаю данные от всех бирж...\n")
        grouped = await aggregator.get_grouped_by_token(top_contracts_limit=5)
        
        if not grouped:
            print("❌ Не удалось получить данные")
            return
        
        print(f"✅ Получено {len(grouped)} токенов\n")
        
        # Выводим результаты
        for i, (token, rates) in enumerate(grouped.items(), 1):
            if not rates:
                continue
            
            print(f"{i}. {token}")
            print(f"   Топ ставка: {rates[0].exchange} = {rates[0].rate_percentage:+.4f}%")
            print(f"   Цена: ${rates[0].price:.2f}")
            print(f"   Funding через: {(rates[0].next_funding_time - rates[0].next_funding_time.replace(microsecond=0)).total_seconds() / 60:.0f} мин")
            print(f"   Бирж собрано: {len(rates)}")
            
            # Показываем топ-3 биржи
            for rate in rates[:3]:
                print(f"      - {rate.exchange}: {rate.rate_percentage:+.4f}%")
            print()
        
        # Закрываем все клиенты
        for exchange in exchanges:
            await exchange.close()
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        
        # Закрываем клиенты даже при ошибке
        for exchange in exchanges:
            try:
                await exchange.close()
            except:
                pass


async def quick_test():
    """Быстрый тест основных бирж."""
    print("\n" + "="*80)
    print(" БЫСТРЫЙ ТЕСТ ASYNC АДАПТЕРОВ")
    print("="*80)
    
    # Тестируем Bybit и Binance
    exchanges = [
        (BybitAdapter(), 'BTCUSDT'),
        (BinanceAdapter(), 'BTCUSDT'),
    ]
    
    results = {}
    for exchange, symbol in exchanges:
        success = await test_single_exchange(exchange, symbol)
        results[exchange.name] = success
    
    # Статистика
    print(f"\n{'='*80}")
    print(" РЕЗУЛЬТАТЫ")
    print(f"{'='*80}\n")
    
    for name, success in results.items():
        status = "✅" if success else "❌"
        print(f"{status} {name}")
    
    success_count = sum(1 for s in results.values() if s)
    total = len(results)
    print(f"\nУспешно: {success_count}/{total}")


async def full_test():
    """Полный тест всех бирж."""
    print("\n" + "="*80)
    print(" ПОЛНЫЙ ТЕСТ ВСЕХ ASYNC АДАПТЕРОВ")
    print("="*80)
    
    exchanges = [
        (BybitAdapter(), 'BTCUSDT'),
        (BinanceAdapter(), 'BTCUSDT'),
        (MexcAdapter(), 'BTC_USDT'),
        (GateioAdapter(), 'BTC_USDT'),
        (KucoinAdapter(), 'XBTUSDTM'),
    ]
    
    results = {}
    for exchange, symbol in exchanges:
        success = await test_single_exchange(exchange, symbol)
        results[exchange.name] = success
    
    # Статистика
    print(f"\n{'='*80}")
    print(" РЕЗУЛЬТАТЫ")
    print(f"{'='*80}\n")
    
    for name, success in results.items():
        status = "✅" if success else "❌"
        print(f"{status} {name}")
    
    success_count = sum(1 for s in results.values() if s)
    total = len(results)
    print(f"\nУспешно: {success_count}/{total}")
    
    # Тест агрегатора
    await test_aggregator()


def main():
    """Главная функция."""
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--quick':
        asyncio.run(quick_test())
    elif len(sys.argv) > 1 and sys.argv[1] == '--aggregator':
        asyncio.run(test_aggregator())
    else:
        asyncio.run(full_test())
    
    print("\n" + "="*80)
    print("Использование:")
    print(f"  python {sys.argv[0]}              - Полный тест")
    print(f"  python {sys.argv[0]} --quick      - Быстрый тест (Bybit + Binance)")
    print(f"  python {sys.argv[0]} --aggregator - Только тест агрегатора")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
