"""Скрипт для тестирования работы адаптеров бирж."""
import logging
import time
from datetime import datetime

from exchanges import (
    BybitAdapter,
    BinanceAdapter,
    MexcAdapter,
    GateioAdapter,
    KucoinAdapter,
    BitgetAdapter,
    BingxAdapter
)

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def test_exchange(exchange, test_symbol='BTCUSDT'):
    """
    Тестирование одной биржи.
    
    Args:
        exchange: Экземпляр адаптера биржи
        test_symbol: Символ для тестирования
    """
    print(f"\n{'='*80}")
    print(f"Тестирование: {exchange.name}")
    print(f"{'='*80}")
    
    # Тест 1: Проверка доступности
    print("\n[1] Проверка доступности...")
    start = time.time()
    try:
        is_available = exchange.is_available()
        elapsed = time.time() - start
        if is_available:
            print(f"✅ Биржа доступна (время ответа: {elapsed:.2f}s)")
        else:
            print(f"❌ Биржа недоступна")
            return False
    except Exception as e:
        elapsed = time.time() - start
        print(f"❌ Ошибка при проверке доступности: {e} ({elapsed:.2f}s)")
        return False
    
    # Тест 2: Получение топ контрактов
    print("\n[2] Получение топ-5 контрактов...")
    start = time.time()
    try:
        contracts = exchange.get_top_contracts(limit=5)
        elapsed = time.time() - start
        if contracts:
            print(f"✅ Получено {len(contracts)} контрактов ({elapsed:.2f}s)")
            for i, contract in enumerate(contracts[:3], 1):
                print(f"   {i}. {contract.symbol} ({contract.base_currency}/{contract.quote_currency})")
        else:
            print(f"⚠️  Контракты не получены ({elapsed:.2f}s)")
    except Exception as e:
        elapsed = time.time() - start
        print(f"❌ Ошибка при получении контрактов: {e} ({elapsed:.2f}s)")
    
    # Тест 3: Получение funding rate для конкретного символа
    print(f"\n[3] Получение funding rate для {test_symbol}...")
    start = time.time()
    try:
        # Пробуем разные варианты символа
        test_variants = [
            test_symbol,
            test_symbol.replace('USDT', '_USDT'),
            test_symbol.replace('USDT', '-USDT'),
        ]
        
        rate = None
        for variant in test_variants:
            rate = exchange.get_funding_rate(variant)
            if rate:
                break
        
        elapsed = time.time() - start
        if rate:
            print(f"✅ Funding rate получен ({elapsed:.2f}s)")
            print(f"   Символ: {rate.symbol}")
            print(f"   Ставка: {rate.rate_percentage:+.4f}%")
            print(f"   Цена: ${rate.price:.2f}")
            print(f"   Следующий funding: {rate.next_funding_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        else:
            print(f"⚠️  Funding rate не получен ({elapsed:.2f}s)")
    except Exception as e:
        elapsed = time.time() - start
        print(f"❌ Ошибка при получении funding rate: {e} ({elapsed:.2f}s)")
    
    return True


def test_all_exchanges():
    """Тестирование всех бирж."""
    print("\n" + "="*80)
    print(" ТЕСТИРОВАНИЕ ВСЕХ АДАПТЕРОВ БИРЖ")
    print("="*80)
    print(f"Время начала: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    exchanges = [
        (BybitAdapter(), 'BTCUSDT'),
        (BinanceAdapter(), 'BTCUSDT'),
        (MexcAdapter(), 'BTC_USDT'),
        (GateioAdapter(), 'BTC_USDT'),
        (KucoinAdapter(), 'XBTUSDTM'),  # KuCoin использует другой формат
        (BitgetAdapter(), 'BTCUSDT'),
        (BingxAdapter(), 'BTC-USDT'),
    ]
    
    results = {}
    
    for exchange, test_symbol in exchanges:
        try:
            success = test_exchange(exchange, test_symbol)
            results[exchange.name] = success
        except Exception as e:
            logger.error(f"Критическая ошибка при тестировании {exchange.name}: {e}")
            results[exchange.name] = False
    
    # Итоговая статистика
    print("\n" + "="*80)
    print(" ИТОГОВАЯ СТАТИСТИКА")
    print("="*80 + "\n")
    
    successful = sum(1 for v in results.values() if v)
    total = len(results)
    
    print(f"Протестировано бирж: {total}")
    print(f"Успешно: {successful}")
    print(f"Ошибок: {total - successful}")
    print(f"\nПроцент успеха: {successful/total*100:.1f}%\n")
    
    print("Детали:")
    for exchange_name, success in results.items():
        status = "✅" if success else "❌"
        print(f"  {status} {exchange_name}")
    
    print("\n" + "="*80)
    print(f"Время окончания: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80 + "\n")


def quick_test():
    """Быстрый тест двух основных бирж."""
    print("\n" + "="*80)
    print(" БЫСТРЫЙ ТЕСТ (Binance и Bybit)")
    print("="*80)
    
    test_exchange(BinanceAdapter(), 'BTCUSDT')
    test_exchange(BybitAdapter(), 'BTCUSDT')
    
    print("\n" + "="*80)
    print(" БЫСТРЫЙ ТЕСТ ЗАВЕРШЕН")
    print("="*80 + "\n")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--quick':
        quick_test()
    else:
        test_all_exchanges()
        
    print("\nИспользование:")
    print(f"  python {sys.argv[0]}          - Полный тест всех бирж")
    print(f"  python {sys.argv[0]} --quick  - Быстрый тест (только Binance и Bybit)")
